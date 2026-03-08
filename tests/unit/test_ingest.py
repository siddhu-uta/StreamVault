"""
Unit tests for the Ingest Lambda handler.
All AWS calls are mocked via moto — no real AWS account needed.
"""
import json
import pytest

import boto3
from moto import mock_aws

# ── Fixtures ─────────────────────────────────────────────────────────────────

class FakeLambdaContext:
    aws_request_id = "test-request-id"
    function_name = "streamvault-ingest-test"


def _make_api_event(body: dict | str | None = None, source_ip: str = "1.2.3.4") -> dict:
    if body is None:
        raw_body = None
    elif isinstance(body, dict):
        raw_body = json.dumps(body)
    else:
        raw_body = body
    return {
        "body": raw_body,
        "requestContext": {
            "identity": {"sourceIp": source_ip}
        },
    }


@pytest.fixture
def sqs_queue():
    """Provides a real mocked SQS queue and patches the handler's QUEUE_URL."""
    with mock_aws():
        client = boto3.client("sqs", region_name="us-east-1")
        resp = client.create_queue(QueueName="test-queue")
        queue_url = resp["QueueUrl"]

        import importlib
        import src.ingest.handler as handler_module
        original_url = handler_module.QUEUE_URL
        handler_module.QUEUE_URL = queue_url
        handler_module.sqs = client

        yield client, queue_url

        handler_module.QUEUE_URL = original_url


# ── Single event handler tests ────────────────────────────────────────────────

class TestIngestHandler:

    def test_valid_event_returns_202(self, sqs_queue):
        from src.ingest.handler import handler
        client, queue_url = sqs_queue

        event = _make_api_event({
            "event_type": "page_view",
            "user_id": "user-123",
            "payload": {"page": "/home"},
        })
        result = handler(event, FakeLambdaContext())

        assert result["statusCode"] == 202
        body = json.loads(result["body"])
        assert body["message"] == "Event accepted"
        assert "event_id" in body

    def test_missing_event_type_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event({
            "user_id": "user-123",
            "payload": {"page": "/home"},
        })
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400
        body = json.loads(result["body"])
        assert "error" in body
        assert "event_type" in body["error"]

    def test_missing_user_id_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event({
            "event_type": "page_view",
            "payload": {"page": "/home"},
        })
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_missing_payload_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event({
            "event_type": "page_view",
            "user_id": "user-123",
        })
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_payload_must_be_object_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event({
            "event_type": "page_view",
            "user_id": "user-123",
            "payload": "not a dict",
        })
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_invalid_json_body_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event("{not json}")
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_empty_body_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event(None)
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_empty_event_type_returns_400(self, sqs_queue):
        from src.ingest.handler import handler
        event = _make_api_event({
            "event_type": "   ",
            "user_id": "user-123",
            "payload": {},
        })
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_message_arrives_in_sqs(self, sqs_queue):
        from src.ingest.handler import handler
        client, queue_url = sqs_queue

        event = _make_api_event({
            "event_type": "purchase",
            "user_id": "user-456",
            "payload": {"amount": 99.99, "currency": "USD"},
        })
        handler(event, FakeLambdaContext())

        msgs = client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        assert len(msgs.get("Messages", [])) == 1
        body = json.loads(msgs["Messages"][0]["Body"])
        assert body["event_type"] == "purchase"
        assert body["user_id"] == "user-456"
        assert "event_id" in body
        assert "ingested_at" in body
        assert body["source_ip"] == "1.2.3.4"

    def test_source_ip_enrichment(self, sqs_queue):
        from src.ingest.handler import handler
        client, queue_url = sqs_queue

        event = _make_api_event(
            {"event_type": "click", "user_id": "u1", "payload": {}},
            source_ip="9.8.7.6",
        )
        handler(event, FakeLambdaContext())
        msgs = client.receive_message(QueueUrl=queue_url, MaxNumberOfMessages=1)
        body = json.loads(msgs["Messages"][0]["Body"])
        assert body["source_ip"] == "9.8.7.6"


# ── Batch handler tests ────────────────────────────────────────────────────────

class TestBatchHandler:

    def test_valid_batch_returns_202(self, sqs_queue):
        from src.ingest.handler import batch_handler
        events = [
            {"event_type": "page_view", "user_id": f"user-{i}", "payload": {}}
            for i in range(5)
        ]
        event = _make_api_event({"events": events})
        result = batch_handler(event, FakeLambdaContext())
        assert result["statusCode"] == 202
        body = json.loads(result["body"])
        assert body["queued"] == 5

    def test_batch_over_100_returns_400(self, sqs_queue):
        from src.ingest.handler import batch_handler
        events = [
            {"event_type": "t", "user_id": f"u{i}", "payload": {}}
            for i in range(101)
        ]
        event = _make_api_event({"events": events})
        result = batch_handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_empty_batch_returns_400(self, sqs_queue):
        from src.ingest.handler import batch_handler
        event = _make_api_event({"events": []})
        result = batch_handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_partial_validation_errors_reported(self, sqs_queue):
        from src.ingest.handler import batch_handler
        events = [
            {"event_type": "page_view", "user_id": "u1", "payload": {}},  # valid
            {"user_id": "u2", "payload": {}},                              # missing event_type
        ]
        event = _make_api_event({"events": events})
        result = batch_handler(event, FakeLambdaContext())
        body = json.loads(result["body"])
        assert body["queued"] == 1
        assert body["failed"] == 1
        assert len(body["validation_errors"]) == 1

    def test_missing_events_key_returns_400(self, sqs_queue):
        from src.ingest.handler import batch_handler
        event = _make_api_event({"something_else": []})
        result = batch_handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400


# ── Health check handler tests ────────────────────────────────────────────────

class TestHealthHandler:

    def test_health_returns_200(self):
        from src.ingest.handler import health_handler
        result = health_handler({}, FakeLambdaContext())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["status"] == "healthy"
