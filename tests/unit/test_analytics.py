"""
Unit tests for the Analytics Lambda handler.
"""
import json
import uuid
import pytest
from datetime import datetime, timezone, timedelta

import boto3
from moto import mock_aws


class FakeLambdaContext:
    aws_request_id = "test-analytics-id"
    function_name = "streamvault-analytics-test"


def _make_api_event(path: str, params: dict = None, path_params: dict = None) -> dict:
    return {
        "path": path,
        "httpMethod": "GET",
        "queryStringParameters": params or {},
        "pathParameters": path_params or {},
    }


@pytest.fixture
def table_with_data():
    with mock_aws():
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

        # Seed some data
        now = datetime.now(timezone.utc)
        for i in range(5):
            table.put_item(Item={
                "event_type": "page_view",
                "ingested_at": (now - timedelta(hours=i)).isoformat(),
                "event_id": str(uuid.uuid4()),
                "user_id": "user-A",
                "payload": {"page": f"/page{i}"},
            })
        for i in range(3):
            table.put_item(Item={
                "event_type": "purchase",
                "ingested_at": (now - timedelta(hours=i)).isoformat(),
                "event_id": str(uuid.uuid4()),
                "user_id": "user-B",
                "payload": {"amount": 100 * i},
            })

        import src.analytics.handler as analytics_module
        analytics_module.dynamodb = ddb

        yield table


class TestAnalyticsHandler:

    def test_events_by_type_and_range(self, table_with_data):
        from src.analytics.handler import handler
        now = datetime.now(timezone.utc)
        from_ts = (now - timedelta(hours=24)).isoformat()
        to_ts = now.isoformat()

        event = _make_api_event(
            "/analytics/events",
            params={"type": "page_view", "from": from_ts, "to": to_ts},
        )
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["count"] == 5
        assert len(body["items"]) == 5

    def test_events_missing_params_returns_400(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/events", params={"type": "page_view"})
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_summary_returns_count(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/summary", params={"type": "page_view"})
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["count_last_24h"] == 5
        assert body["event_type"] == "page_view"

    def test_summary_missing_type_returns_400(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/summary", params={})
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 400

    def test_user_events_uses_gsi(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/user/user-A", path_params={"user_id": "user-A"})
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["count"] == 5

    def test_unknown_user_returns_empty(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/user/ghost", path_params={"user_id": "ghost"})
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 200
        body = json.loads(result["body"])
        assert body["count"] == 0

    def test_unknown_path_returns_404(self, table_with_data):
        from src.analytics.handler import handler
        event = _make_api_event("/analytics/nonexistent")
        result = handler(event, FakeLambdaContext())
        assert result["statusCode"] == 404
