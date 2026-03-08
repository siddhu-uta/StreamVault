import json
import os
import uuid
import logging
from datetime import datetime, timezone
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from pythonjsonlogger import jsonlogger
from aws_xray_sdk.core import xray_recorder, patch_all

# Patch boto3 clients so X-Ray traces DynamoDB and S3 calls
patch_all()

# ── Structured JSON logging ──────────────────────────────────────────────────
logger = logging.getLogger()
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = jsonlogger.JsonFormatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# ── AWS clients ──────────────────────────────────────────────────────────────
dynamodb = boto3.resource("dynamodb")
s3 = boto3.client("s3")

TABLE_NAME = os.environ["TABLE_NAME"]
BUCKET_NAME = os.environ["BUCKET_NAME"]
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

# TTL = 7 days in seconds
TTL_SECONDS = 7 * 24 * 60 * 60

REQUIRED_FIELDS = {"event_type", "user_id", "payload", "event_id", "ingested_at"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _table():
    return dynamodb.Table(TABLE_NAME)


def _compute_ttl() -> int:
    return int(datetime.now(timezone.utc).timestamp()) + TTL_SECONDS


def _write_to_dynamo(event: dict) -> None:
    """
    Idempotent write: only puts the item if event_id doesn't already exist.
    Raises ClientError with ConditionalCheckFailedException if duplicate.
    """
    item = {
        **event,
        "expires_at": _compute_ttl(),
    }
    _table().put_item(
        Item=item,
        ConditionExpression="attribute_not_exists(event_id)",
    )


def _write_batch_to_s3(events: list[dict], batch_id: str) -> None:
    """Writes all events in the batch as JSON Lines to S3."""
    now = datetime.now(timezone.utc)
    key = f"events/{now.year}/{now.month:02d}/{now.day:02d}/{now.hour:02d}/batch-{batch_id}.jsonl"
    body = "\n".join(json.dumps(e) for e in events)
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=body.encode("utf-8"),
        ContentType="application/x-ndjson",
    )
    logger.info("S3 batch written", extra={"key": key, "event_count": len(events)})


def _validate_event(event: dict) -> str | None:
    missing = REQUIRED_FIELDS - event.keys()
    if missing:
        return f"Missing fields: {sorted(missing)}"
    return None


# ── Main handler ──────────────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    """
    SQS-triggered processor Lambda.
    Returns failed message IDs so SQS only retries those (ReportBatchItemFailures).
    """
    request_id = context.aws_request_id if context else str(uuid.uuid4())
    records = event.get("Records", [])

    logger.info(
        "Processor batch received",
        extra={
            "request_id": request_id,
            "batch_size": len(records),
            "environment": ENVIRONMENT,
        },
    )

    successful_events: list[dict] = []
    batch_item_failures: list[dict] = []

    for record in records:
        message_id = record["messageId"]
        try:
            parsed = json.loads(record["body"])
        except (json.JSONDecodeError, KeyError) as exc:
            logger.error(
                "Failed to parse SQS message",
                extra={"message_id": message_id, "error": str(exc)},
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        err = _validate_event(parsed)
        if err:
            logger.error(
                "Event validation failed in processor",
                extra={"message_id": message_id, "reason": err},
            )
            batch_item_failures.append({"itemIdentifier": message_id})
            continue

        try:
            _write_to_dynamo(parsed)
            successful_events.append(parsed)
            logger.info(
                "Event written to DynamoDB",
                extra={
                    "event_id": parsed["event_id"],
                    "event_type": parsed["event_type"],
                },
            )
        except ClientError as exc:
            error_code = exc.response["Error"]["Code"]
            if error_code == "ConditionalCheckFailedException":
                # Duplicate event — idempotent skip
                logger.warning(
                    "Duplicate event skipped (idempotent)",
                    extra={"event_id": parsed.get("event_id")},
                )
                successful_events.append(parsed)  # Still mark as "processed"
            else:
                logger.error(
                    "DynamoDB write failed",
                    extra={"message_id": message_id, "error": str(exc)},
                )
                batch_item_failures.append({"itemIdentifier": message_id})

    # Write successful batch to S3 as JSON Lines
    if successful_events:
        batch_id = str(uuid.uuid4())
        try:
            _write_batch_to_s3(successful_events, batch_id)
        except ClientError as exc:
            logger.error("S3 batch write failed", extra={"error": str(exc)})
            # S3 failure is non-fatal for the SQS acknowledgement
            # The data is already in DynamoDB; S3 is for archival only.

    logger.info(
        "Processor batch complete",
        extra={
            "processed": len(successful_events),
            "failed": len(batch_item_failures),
        },
    )

    return {"batchItemFailures": batch_item_failures}
