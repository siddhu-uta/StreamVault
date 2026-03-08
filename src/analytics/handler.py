import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from pythonjsonlogger import jsonlogger
from aws_xray_sdk.core import patch_all

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

TABLE_NAME = os.environ["TABLE_NAME"]
ENVIRONMENT = os.environ.get("ENVIRONMENT", "dev")
MAX_ITEMS = 1000


def _table():
    return dynamodb.Table(TABLE_NAME)


def _response(status_code: int, body: dict) -> dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "X-Environment": ENVIRONMENT,
        },
        "body": json.dumps(body, default=str),
    }


# ── /analytics/events ─────────────────────────────────────────────────────────

def _query_events_by_type(event_type: str, from_ts: str, to_ts: str, next_token: str | None) -> dict:
    kwargs: dict[str, Any] = {
        "KeyConditionExpression": (
            Key("event_type").eq(event_type)
            & Key("ingested_at").between(from_ts, to_ts)
        ),
        "Limit": MAX_ITEMS,
        "ScanIndexForward": False,  # newest first
    }
    if next_token:
        try:
            kwargs["ExclusiveStartKey"] = json.loads(next_token)
        except (json.JSONDecodeError, TypeError):
            pass

    response = _table().query(**kwargs)
    result = {
        "items": response.get("Items", []),
        "count": response.get("Count", 0),
    }
    if "LastEvaluatedKey" in response:
        result["nextToken"] = json.dumps(response["LastEvaluatedKey"])
    return result


# ── /analytics/summary ────────────────────────────────────────────────────────

def _query_summary(event_type: str) -> dict:
    now = datetime.now(timezone.utc)
    from_ts = (now - timedelta(hours=24)).isoformat()
    to_ts = now.isoformat()

    response = _table().query(
        KeyConditionExpression=(
            Key("event_type").eq(event_type)
            & Key("ingested_at").between(from_ts, to_ts)
        ),
        Select="COUNT",
    )
    return {
        "event_type": event_type,
        "count_last_24h": response.get("Count", 0),
        "from": from_ts,
        "to": to_ts,
    }


# ── /analytics/user/{user_id} ─────────────────────────────────────────────────

def _query_user_events(user_id: str, next_token: str | None) -> dict:
    kwargs: dict[str, Any] = {
        "IndexName": "user-id-index",
        "KeyConditionExpression": Key("user_id").eq(user_id),
        "Limit": MAX_ITEMS,
        "ScanIndexForward": False,
    }
    if next_token:
        try:
            kwargs["ExclusiveStartKey"] = json.loads(next_token)
        except (json.JSONDecodeError, TypeError):
            pass

    response = _table().query(**kwargs)
    result = {
        "user_id": user_id,
        "items": response.get("Items", []),
        "count": response.get("Count", 0),
    }
    if "LastEvaluatedKey" in response:
        result["nextToken"] = json.dumps(response["LastEvaluatedKey"])
    return result


# ── Router ────────────────────────────────────────────────────────────────────

def handler(event: dict, context) -> dict:
    path = event.get("path", "")
    method = event.get("httpMethod", "GET")
    params = event.get("queryStringParameters") or {}
    path_params = event.get("pathParameters") or {}

    logger.info(
        "Analytics request",
        extra={"path": path, "method": method, "params": params},
    )

    try:
        # GET /analytics/events
        if path == "/analytics/events":
            event_type = params.get("type")
            from_ts = params.get("from")
            to_ts = params.get("to")
            if not event_type or not from_ts or not to_ts:
                return _response(400, {"error": "Parameters 'type', 'from', and 'to' are required"})
            result = _query_events_by_type(
                event_type, from_ts, to_ts, params.get("nextToken")
            )
            return _response(200, result)

        # GET /analytics/summary
        elif path == "/analytics/summary":
            event_type = params.get("type")
            if not event_type:
                return _response(400, {"error": "Parameter 'type' is required"})
            result = _query_summary(event_type)
            return _response(200, result)

        # GET /analytics/user/{user_id}
        elif path.startswith("/analytics/user/"):
            user_id = path_params.get("user_id") or path.split("/analytics/user/", 1)[-1]
            if not user_id:
                return _response(400, {"error": "user_id is required"})
            result = _query_user_events(user_id, params.get("nextToken"))
            return _response(200, result)

        else:
            return _response(404, {"error": "Not found"})

    except ClientError as exc:
        logger.error("DynamoDB error", extra={"error": str(exc)})
        return _response(500, {"error": "Internal server error"})
