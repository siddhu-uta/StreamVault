"""
Unit tests for the Processor Lambda handler.
"""
import json
import uuid
import pytest
from datetime import datetime, timezone

import boto3
from moto import mock_aws


class FakeLambdaContext:
    aws_request_id = "test-request-id"
    function_name = "streamvault-processor-test"


def _make_sqs_event(events: list[dict]) -> dict:
    return {
        "Records": [
            {
                "messageId": str(uuid.uuid4()),
                "body": json.dumps(ev),
                "receiptHandle": "fake-receipt",
            }
            for ev in events
        ]
    }


def _make_valid_event(**overrides) -> dict:
    base = {
        "event_id": str(uuid.uuid4()),
        "event_type": "page_view",
        "user_id": "user-1",
        "payload": {"page": "/home"},
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "source_ip": "1.2.3.4",
    }
    return {**base, **overrides}


@pytest.fixture
def aws_resources():
    with mock_aws():
        # Create DynamoDB table
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.create_table(
            TableName="test-events-table",
            KeySchema=[
                {"AttributeName": "event_type", "KeyType": "HASH"},
                {"AttributeName": "ingested_at", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "event_type", "AttributeType": "S"},
                {"AttributeName": "ingested_at", "AttributeType": "S"},
                {"AttributeName": "user_id", "AttributeType": "S"},
            ],
            GlobalSecondaryIndexes=[
                {
                    "IndexName": "user-id-index",
                    "KeySchema": [
                        {"AttributeName": "user_id", "KeyType": "HASH"},
                        {"AttributeName": "ingested_at", "KeyType": "RANGE"},
                    ],
                    "Projection": {"ProjectionType": "ALL"},
                }
            ],
            BillingMode="PAY_PER_REQUEST",
        )

        # Create S3 bucket
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="test-events-bucket")

        # Patch the handler module
        import importlib
        import src.processor.handler as proc_module
        proc_module.dynamodb = ddb
        proc_module.s3 = s3

        yield table, s3


class TestProcessorHandler:

    def test_single_valid_event_writes_to_dynamo(self, aws_resources):
        from src.processor.handler import handler
        table, _ = aws_resources
        ev = _make_valid_event()
        sqs_event = _make_sqs_event([ev])

        result = handler(sqs_event, FakeLambdaContext())

        assert result == {"batchItemFailures": []}
        resp = table.get_item(Key={"event_type": ev["event_type"], "ingested_at": ev["ingested_at"]})
        assert "Item" in resp
        assert resp["Item"]["event_id"] == ev["event_id"]

    def test_ttl_is_set(self, aws_resources):
        from src.processor.handler import handler
        table, _ = aws_resources
        ev = _make_valid_event()
        handler(_make_sqs_event([ev]), FakeLambdaContext())

        resp = table.get_item(Key={"event_type": ev["event_type"], "ingested_at": ev["ingested_at"]})
        item = resp["Item"]
        assert "expires_at" in item
        # TTL should be roughly 7 days from now
        expected_min = int(datetime.now(timezone.utc).timestamp()) + (6 * 24 * 60 * 60)
        assert int(item["expires_at"]) > expected_min

    def test_duplicate_event_is_skipped_idempotently(self, aws_resources):
        from src.processor.handler import handler
        table, _ = aws_resources
        ev = _make_valid_event()

        # Process same event twice
        result1 = handler(_make_sqs_event([ev]), FakeLambdaContext())
        result2 = handler(_make_sqs_event([ev]), FakeLambdaContext())

        assert result1 == {"batchItemFailures": []}
        assert result2 == {"batchItemFailures": []}  # Should NOT fail — idempotent skip

    def test_bad_json_message_reported_as_failure(self, aws_resources):
        from src.processor.handler import handler
        message_id = "bad-message-id"
        sqs_event = {
            "Records": [{
                "messageId": message_id,
                "body": "not valid json",
                "receiptHandle": "fake",
            }]
        }
        result = handler(sqs_event, FakeLambdaContext())
        assert len(result["batchItemFailures"]) == 1
        assert result["batchItemFailures"][0]["itemIdentifier"] == message_id

    def test_partial_batch_failures(self, aws_resources):
        from src.processor.handler import handler
        good_ev = _make_valid_event()
        bad_message_id = "bad-id"

        sqs_event = {
            "Records": [
                {
                    "messageId": str(uuid.uuid4()),
                    "body": json.dumps(good_ev),
                    "receiptHandle": "r1",
                },
                {
                    "messageId": bad_message_id,
                    "body": "{{invalid",
                    "receiptHandle": "r2",
                },
            ]
        }
        result = handler(sqs_event, FakeLambdaContext())

        # Only the bad message should be in failures
        assert len(result["batchItemFailures"]) == 1
        assert result["batchItemFailures"][0]["itemIdentifier"] == bad_message_id

    def test_event_missing_required_fields_reported_as_failure(self, aws_resources):
        from src.processor.handler import handler
        incomplete_ev = {"event_type": "page_view"}  # missing user_id, payload, event_id, ingested_at
        message_id = "incomplete-id"
        sqs_event = {
            "Records": [{
                "messageId": message_id,
                "body": json.dumps(incomplete_ev),
                "receiptHandle": "fake",
            }]
        }
        result = handler(sqs_event, FakeLambdaContext())
        assert len(result["batchItemFailures"]) == 1

    def test_s3_batch_written(self, aws_resources):
        from src.processor.handler import handler
        _, s3 = aws_resources
        events = [_make_valid_event(user_id=f"u{i}") for i in range(3)]
        handler(_make_sqs_event(events), FakeLambdaContext())

        # There should be exactly one object in the bucket
        objects = s3.list_objects(Bucket="test-events-bucket").get("Contents", [])
        assert len(objects) == 1
        assert objects[0]["Key"].endswith(".jsonl")
