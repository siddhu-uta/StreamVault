import json
import os
import uuid
import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import ClientError
from pythonjsonlogger import jsonlogger

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
sqs = boto3.client("sqs")

QUEUE_URL = os.environ.get("QUEUE_URL", "")
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")

REQUIRED_FIELDS = {"event_type", "user_id", "payload"}


# ── Helpers ──────────────────────────────────────────────────────────────────

def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Environment": ENVIRONMENT,
        },
        "body": json.dumps(body),
    }


def _get_source_ip(event: dict) -> str:
    try:
        return event["requestContext"]["identity"]["sourceIp"]
    except (KeyError, TypeError):
        return "unknown"


def _enrich_event(raw: dict, source_ip: str) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        **raw,
        "event_id": str(uuid.uuid4()),
        "ingested_at": now,
        "source_ip": source_ip,
        "environment": ENVIRONMENT,
    }


def _validate(raw: dict) -> str | None:
    """Return an error message string if validation fails, else None."""
    missing = REQUIRED_FIELDS - raw.keys()
    if missing:
        return f"Missing required fields: {sorted(missing)}"
    if not isinstance(raw.get("payload"), dict):
        return "'payload' must be a JSON object"
    if not isinstance(raw.get("event_type"), str) or not raw["event_type"].strip():
        return "'event_type' must be a non-empty string"
    if not isinstance(raw.get("user_id"), str) or not raw["user_id"].strip():
        return "'user_id' must be a non-empty string"
    return None


def _send_to_sqs(enriched: dict, request_id: str) -> None:
    sqs.send_message(
        QueueUrl=QUEUE_URL,
        MessageBody=json.dumps(enriched),
        MessageAttributes={
            "RequestId": {"DataType": "String", "StringValue": request_id},
            "EventType": {"DataType": "String", "StringValue": enriched["event_type"]},
        },
    )


# ── Single-event handler ──────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    request_id = context.aws_request_id if context else str(uuid.uuid4())

    logger.info(
        "Ingest request received",
        extra={
            "request_id": request_id,
            "function": context.function_name if context else "local",
            "environment": ENVIRONMENT,
        },
    )

    # Parse body
    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError as exc:
        logger.warning("Invalid JSON body", extra={"error": str(exc)})
        return _response(400, {"error": "Request body must be valid JSON"})

    # Validate
    error_msg = _validate(body)
    if error_msg:
        logger.warning("Validation failed", extra={"reason": error_msg})
        return _response(400, {"error": error_msg})

    source_ip = _get_source_ip(event)
    enriched = _enrich_event(body, source_ip)

    # Send to SQS
    try:
        _send_to_sqs(enriched, request_id)
    except ClientError as exc:
        logger.error(
            "SQS send failed",
            extra={"error": str(exc), "request_id": request_id},
        )
        return _response(500, {"error": "Failed to queue event. Please retry."})

    logger.info(
        "Event queued successfully",
        extra={
            "event_id": enriched["event_id"],
            "event_type": enriched["event_type"],
            "request_id": request_id,
        },
    )

    return _response(202, {
        "message": "Event accepted",
        "event_id": enriched["event_id"],
    })


# ── Batch handler ─────────────────────────────────────────────────────────────

def batch_handler(event: dict, context) -> dict:
    """Handles POST /events/batch — up to 100 events per call."""
    request_id = context.aws_request_id if context else str(uuid.uuid4())

    logger.info(
        "Batch ingest request received",
        extra={"request_id": request_id, "environment": ENVIRONMENT},
    )

    try:
        body = json.loads(event.get("body") or "{}")
    except json.JSONDecodeError:
        return _response(400, {"error": "Request body must be valid JSON"})

    events_raw = body.get("events")
    if not isinstance(events_raw, list) or len(events_raw) == 0:
        return _response(400, {"error": "'events' must be a non-empty array"})

    if len(events_raw) > 100:
        return _response(400, {"error": "Batch size cannot exceed 100 events"})

    source_ip = _get_source_ip(event)
    enriched_events = []
    validation_errors = []

    for idx, raw in enumerate(events_raw):
        error_msg = _validate(raw)
        if error_msg:
            validation_errors.append({"index": idx, "error": error_msg})
        else:
            enriched_events.append(_enrich_event(raw, source_ip))

    # SQS batch send — chunked into groups of 10 (SQS limit)
    succeeded = 0
    failed_ids = []

    chunks = [enriched_events[i : i + 10] for i in range(0, len(enriched_events), 10)]
    for chunk in chunks:
        entries = [
            {
                "Id": str(idx),
                "MessageBody": json.dumps(e),
                "MessageAttributes": {
                    "EventType": {"DataType": "String", "StringValue": e["event_type"]},
                },
            }
            for idx, e in enumerate(chunk)
        ]
        try:
            resp = sqs.send_message_batch(QueueUrl=QUEUE_URL, Entries=entries)
            succeeded += len(resp.get("Successful", []))
            for fail in resp.get("Failed", []):
                failed_ids.append(chunk[int(fail["Id"])]["event_id"])
                logger.error("SQS batch item failed", extra={"fail": fail})
        except ClientError as exc:
            logger.error("SQS batch send failed", extra={"error": str(exc)})
            for e in chunk:
                failed_ids.append(e["event_id"])

    logger.info(
        "Batch processed",
        extra={
            "total": len(events_raw),
            "succeeded": succeeded,
            "failed": len(failed_ids),
            "validation_errors": len(validation_errors),
        },
    )

    return _response(202, {
        "message": "Batch accepted",
        "total": len(events_raw),
        "queued": succeeded,
        "failed": len(failed_ids) + len(validation_errors),
        "validation_errors": validation_errors,
        "failed_event_ids": failed_ids,
    })


# ── Health check handler ──────────────────────────────────────────────────────

def health_handler(event: dict, context) -> dict:
    return _response(200, {"status": "healthy", "environment": ENVIRONMENT})
