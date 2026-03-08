# `tests/` — StreamVault Test Suite

## Structure

```
tests/
├── unit/
│   ├── test_ingest.py       ← Ingest Lambda (single + batch + health)
│   ├── test_processor.py    ← Processor Lambda (DynamoDB + S3 + idempotency)
│   └── test_analytics.py    ← Analytics Lambda (type query + summary + user GSI)
├── integration/
│   └── test_api.py          ← End-to-end tests against deployed dev stack
└── locustfile.py            ← Load test (run locally only)
```

## Running Unit Tests

All unit tests use **moto** to mock AWS services. No real AWS account needed.

```bash
# Install test dependencies
pip install pytest pytest-cov moto[sqs,dynamodb,s3] boto3 python-json-logger aws-xray-sdk

# Run all unit tests
pytest tests/unit/ -v

# Run with coverage report
pytest tests/unit/ -v --cov=src --cov-report=term-missing
```

**Expected output:** All tests pass. Coverage > 90%.

## Running Integration Tests

> ⚠️ Requires the dev stack to be deployed. Hits real AWS. Run after `sam deploy --config-env dev`.

```bash
# Get your Cognito token first (see README.md "Create a test user")
export API_URL=https://xxxx.execute-api.us-east-1.amazonaws.com/dev
export COGNITO_TOKEN=<your_access_token>

pytest tests/integration/ -v
```

Integration tests do **not** run in CI on every push — only after a successful `deploy-dev` job.

## Running Load Tests

> ⚠️ Run locally only. Never in CI — this generates real traffic against your deployed stack
> and will eat into your free tier limits if left running.

```bash
pip install locust
locust -f tests/locustfile.py \
  --host=$API_URL \
  --users=10 \
  --spawn-rate=2 \
  --run-time=60s \
  --headless
```

A 60-second run with 10 users generates useful CloudWatch metrics for your dashboard.

## Environment Variables for Unit Tests

Unit tests set dummy values automatically. You do **not** need real credentials.

| Variable | Default in tests | Description |
|----------|-----------------|-------------|
| `QUEUE_URL` | `https://sqs.../test-queue` | Overridden by moto fixture |
| `TABLE_NAME` | `test-events-table` | Overridden by moto fixture |
| `BUCKET_NAME` | `test-events-bucket` | Overridden by moto fixture |
| `ENVIRONMENT` | `test` | Set in test file |
| `AWS_XRAY_SDK_ENABLED` | `false` | Disables X-Ray in unit tests |
