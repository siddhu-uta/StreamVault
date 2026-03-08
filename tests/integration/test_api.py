"""
Integration tests for StreamVault.

These tests run against the REAL deployed dev environment.
Set the API_URL environment variable before running:

    API_URL=https://xxx.execute-api.us-east-1.amazonaws.com/dev \
    COGNITO_TOKEN=<bearer_token> \
    pytest tests/integration/ -v

Get a Cognito token with:
    aws cognito-idp initiate-auth \
        --auth-flow USER_PASSWORD_AUTH \
        --auth-parameters USERNAME=<email>,PASSWORD=<password> \
        --client-id <UserPoolClientId>
"""
import json
import os
import time
import uuid

import pytest
import urllib.request
import urllib.error

API_URL = os.environ.get("API_URL", "").rstrip("/")
TOKEN = os.environ.get("COGNITO_TOKEN", "")

SKIP_REASON = "API_URL and COGNITO_TOKEN must be set for integration tests"
requires_env = pytest.mark.skipif(not API_URL or not TOKEN, reason=SKIP_REASON)


def _request(method: str, path: str, body: dict = None, auth: bool = True) -> tuple[int, dict]:
    url = f"{API_URL}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {"Content-Type": "application/json"}
    if auth:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


@requires_env
class TestIntegration:

    def test_health_check_no_auth(self):
        status, body = _request("GET", "/health", auth=False)
        assert status == 200
        assert body["status"] == "healthy"

    def test_no_auth_token_returns_401(self):
        status, _ = _request("POST", "/events", body={
            "event_type": "page_view",
            "user_id": "u1",
            "payload": {},
        }, auth=False)
        assert status == 401

    def test_malformed_body_returns_400(self):
        # Send empty body
        status, body = _request("POST", "/events", body={})
        assert status == 400

    def test_single_event_end_to_end(self):
        """Send event, wait, verify it appears in analytics."""
        user_id = f"integration-{uuid.uuid4()}"
        event_type = "integration_test"

        status, body = _request("POST", "/events", body={
            "event_type": event_type,
            "user_id": user_id,
            "payload": {"test_run": True},
        })
        assert status == 202
        event_id = body["event_id"]
        from datetime import datetime, timezone, timedelta
        import urllib.parse
        ingest_time = datetime.now(timezone.utc)

        # Wait for SQS → Processor → DynamoDB round-trip (allow up to 25s cold start)
        time.sleep(25)

        # Capture to_ts AFTER sleep so processed events fall within window
        now = datetime.now(timezone.utc)
        from_ts = (ingest_time - timedelta(minutes=2)).isoformat()
        to_ts = now.isoformat()

        query = urllib.parse.urlencode({
            "type": event_type,
            "from": from_ts,
            "to": to_ts,
        })
        status, analytics = _request(
            "GET",
            f"/analytics/events?{query}",
        )
        assert status == 200
        event_ids = [item["event_id"] for item in analytics["items"]]
        assert event_id in event_ids

    def test_user_events_via_gsi(self):
        user_id = f"gsi-user-{uuid.uuid4()}"
        for et in ["click", "scroll", "page_view"]:
            _request("POST", "/events", body={
                "event_type": et,
                "user_id": user_id,
                "payload": {},
            })
        # Wait for SQS → Processor → DynamoDB round-trip
        time.sleep(25)

        status, body = _request("GET", f"/analytics/user/{user_id}")
        assert status == 200
        assert body["count"] >= 3

    def test_batch_100_events(self):
        events = [
            {
                "event_type": "batch_test",
                "user_id": f"batch-user-{i}",
                "payload": {"index": i},
            }
            for i in range(100)
        ]
        status, body = _request("POST", "/events/batch", body={"events": events})
        assert status == 202
        assert body["queued"] == 100
        assert body["failed"] == 0
