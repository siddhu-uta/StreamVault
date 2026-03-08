# StreamVault

> **Serverless event ingestion pipeline on AWS.** Accepts events from any client, reliably
> queues and processes them, and serves analytics on top — all built on fully managed services
> with zero operational overhead and $0 cost within the AWS Free Tier.

---

## Architecture

```
                    ┌─────────────┐
          HTTPS     │  API Gateway│  (REST + Cognito JWT Auth + Throttling)
  Clients ────────► │  us-east-1  │
                    └──────┬──────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
     POST /events    POST /events    GET /analytics
     POST /events/   /batch          /*
     batch
           │               │               │
     ┌─────▼─────┐  ┌──────▼──────┐  ┌────▼─────────┐
     │  Ingest   │  │   Ingest    │  │  Analytics   │
     │  Lambda   │  │   Batch     │  │   Lambda     │
     │  (Python) │  │   Lambda    │  │  (Python)    │
     └─────┬─────┘  └──────┬──────┘  └──────┬───────┘
           │               │                  │
           └───────┬────────┘                 │
                   │                          │
           ┌───────▼───────┐                  │
           │  SQS Standard │                  │
           │     Queue     │                  │
           │  (max 3 fails │                  │
           │   → DLQ)      │                  │
           └───────┬───────┘                  │
                   │                          │
           ┌───────▼───────┐        ┌─────────▼──────────┐
           │  Processor    │        │   DynamoDB Table    │
           │  Lambda       ├───────►│  PK: event_type     │◄──┘
           │  (batch 10)   │        │  SK: ingested_at    │
           └───────┬───────┘        │  GSI: user_id       │
                   │                │  TTL: 7 days        │
                   │                └─────────────────────┘
                   │
           ┌───────▼───────┐
           │  S3 Bucket    │  events/YYYY/MM/DD/HH/batch-{uuid}.jsonl
           │  (30-day TTL) │  (JSON Lines, Athena-ready)
           └───────────────┘

Observability: X-Ray traces | CloudWatch Logs (JSON) | CloudWatch Alarms → SNS → Email
```

---

## AWS Services Used

| Service | Why |
|---------|-----|
| **API Gateway (REST)** | Request validation, Cognito JWT auth, throttling at the edge |
| **Cognito User Pool** | JWT-based auth — no auth code in Lambda |
| **Lambda (Python 3.12)** | Serverless compute, scales to zero, pay-per-invocation |
| **SQS Standard** | Durable message buffer between ingest and processing |
| **DynamoDB (on-demand)** | Millisecond query latency, TTL, GSI for user lookups |
| **S3** | Cheap long-term archival, Athena-ready JSONL format |
| **CloudWatch** | Structured logs, custom metrics (EMF), alarms |
| **X-Ray** | Distributed tracing across all Lambda + AWS SDK calls |
| **SNS** | Routes alarm notifications to email |
| **SAM** | Infrastructure as Code — entire stack in `template.yaml` |

---

## Quick Start

### Prerequisites
- AWS CLI configured (`aws configure`)
- AWS SAM CLI (`brew install aws-sam-cli`)
- Docker Desktop running
- Python 3.12 (`python3 --version`)

### 1. Clone & install
```bash
git clone https://github.com/your-username/streamvault.git
cd streamvault
pip install pytest moto boto3 python-json-logger aws-xray-sdk
```

### 2. Run unit tests
```bash
pytest tests/unit/ -v
```

### 3. Deploy to dev
```bash
# Edit samconfig.toml — update AlertEmail
sam build
sam deploy --config-env dev
```

SAM will print the API endpoint URL when done.

### 4. Create a test user
```bash
# Replace USER_POOL_ID and CLIENT_ID with SAM stack outputs
aws cognito-idp admin-create-user \
  --user-pool-id <UserPoolId> \
  --username test@example.com

aws cognito-idp admin-set-user-password \
  --user-pool-id <UserPoolId> \
  --username test@example.com \
  --password 'MyP@ssw0rd123!' \
  --permanent

TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --auth-parameters USERNAME=test@example.com,PASSWORD='MyP@ssw0rd123!' \
  --client-id <UserPoolClientId> \
  --query "AuthenticationResult.AccessToken" \
  --output text)
```

### 5. Send your first event
```bash
API="https://xxxx.execute-api.us-east-1.amazonaws.com/dev"

curl -X POST "$API/events" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "page_view",
    "user_id": "user-123",
    "payload": {"page": "/home", "duration_ms": 250}
  }'
```

Expected response (`202 Accepted`):
```json
{
  "message": "Event accepted",
  "event_id": "a1b2c3d4-..."
}
```

### 6. Tear down (important — avoid charges)
```bash
sam delete --stack-name streamvault-dev
```

---

## API Reference

### Authentication
All endpoints except `GET /health` require a Bearer token:
```
Authorization: Bearer <Cognito AccessToken>
```

### Endpoints

#### `GET /health`
Health check. No auth required.

**Response `200`:**
```json
{ "status": "healthy", "environment": "dev" }
```

---

#### `POST /events`
Ingest a single event.

**Request body:**
```json
{
  "event_type": "page_view",
  "user_id": "user-123",
  "payload": { "page": "/home", "duration_ms": 250 }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_type` | string | ✅ | Category of event |
| `user_id` | string | ✅ | User who triggered the event |
| `payload` | object | ✅ | Arbitrary event-specific data |

**Response `202`:**
```json
{ "message": "Event accepted", "event_id": "uuid-here" }
```

**Response `400`:**
```json
{ "error": "Missing required fields: ['event_type']" }
```

---

#### `POST /events/batch`
Ingest up to 100 events in a single call.

**Request body:**
```json
{
  "events": [
    { "event_type": "click", "user_id": "u1", "payload": { "button": "cta" } },
    { "event_type": "scroll", "user_id": "u2", "payload": { "depth_pct": 75 } }
  ]
}
```

**Response `202`:**
```json
{
  "message": "Batch accepted",
  "total": 2,
  "queued": 2,
  "failed": 0,
  "validation_errors": [],
  "failed_event_ids": []
}
```

---

#### `GET /analytics/events`
Query events by type and time range.

**Query parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `type` | ✅ | Event type to query |
| `from` | ✅ | ISO 8601 start timestamp |
| `to` | ✅ | ISO 8601 end timestamp |
| `nextToken` | ❌ | Pagination token from previous response |

**Example:**
```bash
curl "$API/analytics/events?type=page_view&from=2026-03-04T00:00:00Z&to=2026-03-04T23:59:59Z" \
  -H "Authorization: Bearer $TOKEN"
```

**Response `200`:**
```json
{
  "items": [ { "event_type": "page_view", "event_id": "...", ... } ],
  "count": 1,
  "nextToken": "..."
}
```

---

#### `GET /analytics/summary`
Count of events by type in the last 24 hours.

**Query parameters:** `type` (required)

```bash
curl "$API/analytics/summary?type=purchase" -H "Authorization: Bearer $TOKEN"
```

**Response `200`:**
```json
{
  "event_type": "purchase",
  "count_last_24h": 42,
  "from": "2026-03-03T14:00:00+00:00",
  "to": "2026-03-04T14:00:00+00:00"
}
```

---

#### `GET /analytics/user/{user_id}`
All events for a specific user (via DynamoDB GSI).

```bash
curl "$API/analytics/user/user-123" -H "Authorization: Bearer $TOKEN"
```

**Response `200`:**
```json
{
  "user_id": "user-123",
  "items": [ ... ],
  "count": 7
}
```

---

## Running Tests

### Unit tests
```bash
pytest tests/unit/ -v --cov=src --cov-report=term-missing
```

### Integration tests (requires deployed dev stack)
```bash
API_URL=https://xxx.execute-api.us-east-1.amazonaws.com/dev \
COGNITO_TOKEN=$TOKEN \
pytest tests/integration/ -v
```

### Load test (run locally, not in CI)
```bash
pip install locust
locust -f tests/locustfile.py --host=$API_URL \
  --users=10 --spawn-rate=2 --run-time=60s --headless
```

---

## CI/CD

GitHub Actions pipeline defined in `.github/workflows/deploy.yml`:

| Trigger | Job |
|---------|-----|
| Any push | `test` — runs all unit tests |
| Push to `main` | `deploy-dev` — auto-deploys to dev stack |
| Manual `workflow_dispatch` | `deploy-prod` — deploys to prod stack |

**Required GitHub Secrets:**
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `ALERT_EMAIL`

---

## Design Decisions

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed rationale on every major design
decision: SQS vs Kafka, DynamoDB schema design, idempotency strategy, IAM least-privilege,
partial batch failures, and scaling plan to 10x.

---

## Free Tier Safety

- **Always tear down dev** with `sam delete` when not actively developing
- DynamoDB TTL is set to 7 days — no runaway storage costs
- S3 lifecycle rule deletes objects after 30 days
- Lambda memory is 128 MB (minimum)
- API Gateway caching is disabled in dev
- Billing alarm is set to $1 threshold (see AWS Account Setup in guide)
