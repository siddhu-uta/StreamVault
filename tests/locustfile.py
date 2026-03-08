"""
Locust load test for StreamVault.

Run locally (do NOT run in CI — this hits real AWS):
    locust -f tests/locustfile.py --host=$API_URL \
           --users=10 --spawn-rate=2 --run-time=60s --headless

Set COGNITO_TOKEN before running:
    export COGNITO_TOKEN=<your_token>
"""
import json
import os
import uuid

from locust import HttpUser, between, task

TOKEN = os.environ.get("COGNITO_TOKEN", "")
AUTH_HEADER = {"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json"}


class StreamVaultUser(HttpUser):
    wait_time = between(0.5, 2)

    @task(5)
    def send_single_event(self):
        payload = {
            "event_type": "page_view",
            "user_id": f"load-user-{uuid.uuid4()}",
            "payload": {"page": "/load-test", "duration_ms": 120},
        }
        with self.client.post(
            "/events",
            data=json.dumps(payload),
            headers=AUTH_HEADER,
            catch_response=True,
            name="POST /events",
        ) as resp:
            if resp.status_code == 202:
                resp.success()
            else:
                resp.failure(f"Expected 202, got {resp.status_code}")

    @task(2)
    def send_batch_events(self):
        events = [
            {
                "event_type": "button_click",
                "user_id": f"load-user-{i}",
                "payload": {"button": "cta"},
            }
            for i in range(10)
        ]
        with self.client.post(
            "/events/batch",
            data=json.dumps({"events": events}),
            headers=AUTH_HEADER,
            catch_response=True,
            name="POST /events/batch",
        ) as resp:
            if resp.status_code == 202:
                resp.success()
            else:
                resp.failure(f"Expected 202, got {resp.status_code}")

    @task(1)
    def check_health(self):
        self.client.get("/health", name="GET /health")

    @task(1)
    def query_analytics_summary(self):
        with self.client.get(
            "/analytics/summary?type=page_view",
            headers=AUTH_HEADER,
            catch_response=True,
            name="GET /analytics/summary",
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Got {resp.status_code}")
