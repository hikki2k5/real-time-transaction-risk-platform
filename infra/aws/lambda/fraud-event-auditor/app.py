import json
import os
from datetime import datetime, timezone
from typing import Any


DEFAULT_REVIEW_THRESHOLD = 0.40
DEFAULT_BLOCK_THRESHOLD = 0.80
DEFAULT_TARGET_TOPIC = "transaction_risk_events"
REQUIRED_EVENT_FIELDS = ("event_id", "transaction_id", "user_id", "fraud_probability")


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    """AWS Lambda entry point for transaction fraud audit events.

    The handler is intentionally side-effect free for the portfolio project:
    it parses API Gateway, EventBridge, direct invoke, or SQS-style events,
    validates transaction-risk payloads, and returns Kafka-ready stream events
    that can later be published to MSK/Kafka, Kinesis, EventBridge, or SQS.
    """
    records = extract_records(event)
    ingestion_records = [build_ingestion_record(record) for record in records]
    audits = [record["audit"] for record in ingestion_records]
    stream_events = [record["stream_event"] for record in ingestion_records if record["valid"]]
    invalid_records = [
        {"transaction_id": record["audit"]["transaction_id"], "errors": record["errors"]}
        for record in ingestion_records
        if not record["valid"]
    ]

    if is_api_gateway_event(event):
        status_code = 200 if not invalid_records else 400
        return {
            "statusCode": status_code,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(
                {
                    "audits": audits,
                    "stream_events": stream_events,
                    "invalid_records": invalid_records,
                }
            ),
        }

    return {"audits": audits, "stream_events": stream_events, "invalid_records": invalid_records}


def extract_records(event: dict[str, Any]) -> list[dict[str, Any]]:
    if "Records" in event:
        return [parse_record(record) for record in event["Records"]]

    if "detail" in event and isinstance(event["detail"], dict):
        return [event["detail"]]

    if is_api_gateway_event(event):
        body = event.get("body") or "{}"
        payload = json.loads(body) if isinstance(body, str) else body
        return [payload]

    return [event]


def parse_record(record: dict[str, Any]) -> dict[str, Any]:
    body = record.get("body", record)
    if isinstance(body, str):
        return json.loads(body)
    return body


def build_ingestion_record(payload: dict[str, Any]) -> dict[str, Any]:
    errors = validate_transaction_risk_event(payload)
    audit = build_audit_record(payload)

    return {
        "valid": not errors,
        "errors": errors,
        "audit": audit,
        "stream_event": build_stream_event(payload, audit),
    }


def validate_transaction_risk_event(payload: dict[str, Any]) -> list[str]:
    errors = [f"{field} is required" for field in REQUIRED_EVENT_FIELDS if payload.get(field) in (None, "")]
    probability = coerce_float(payload.get("fraud_probability"), -1.0)

    if "fraud_probability" in payload and not 0.0 <= probability <= 1.0:
        errors.append("fraud_probability must be between 0 and 1")

    return errors


def build_stream_event(payload: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_topic": os.getenv("TARGET_STREAM_TOPIC", DEFAULT_TARGET_TOPIC),
        "stream_key": audit["transaction_id"],
        "payload": {
            "event_id": str(payload.get("event_id", "")),
            "transaction_id": audit["transaction_id"],
            "user_id": audit["user_id"],
            "decision": audit["decision"],
            "risk_level": audit["risk_level"],
            "fraud_probability": audit["fraud_probability"],
            "requires_manual_review": audit["requires_manual_review"],
            "source_component": audit["serverless_component"],
            "ingested_at": audit["created_at"],
        },
    }


def build_audit_record(payload: dict[str, Any]) -> dict[str, Any]:
    probability = coerce_float(payload.get("fraud_probability"), 0.0)
    decision = str(payload.get("decision") or decision_from_probability(probability))
    risk_level = str(payload.get("risk_level") or risk_level_from_probability(probability))

    return {
        "audit_id": make_audit_id(payload),
        "transaction_id": str(payload.get("transaction_id", "")),
        "user_id": str(payload.get("user_id", "")),
        "decision": decision,
        "risk_level": risk_level,
        "fraud_probability": probability,
        "requires_manual_review": decision.upper() == "REVIEW",
        "serverless_component": os.getenv("AWS_LAMBDA_FUNCTION_NAME", "local-fraud-event-auditor"),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def make_audit_id(payload: dict[str, Any]) -> str:
    transaction_id = str(payload.get("transaction_id") or "unknown")
    event_id = str(payload.get("event_id") or "no-event")
    return f"audit-{transaction_id}-{event_id}"


def decision_from_probability(probability: float) -> str:
    if probability >= coerce_float(os.getenv("FRAUD_BLOCK_THRESHOLD"), DEFAULT_BLOCK_THRESHOLD):
        return "BLOCK"
    if probability >= coerce_float(os.getenv("FRAUD_REVIEW_THRESHOLD"), DEFAULT_REVIEW_THRESHOLD):
        return "REVIEW"
    return "APPROVE"


def risk_level_from_probability(probability: float) -> str:
    if probability >= coerce_float(os.getenv("FRAUD_BLOCK_THRESHOLD"), DEFAULT_BLOCK_THRESHOLD):
        return "HIGH"
    if probability >= coerce_float(os.getenv("FRAUD_REVIEW_THRESHOLD"), DEFAULT_REVIEW_THRESHOLD):
        return "MEDIUM"
    return "LOW"


def coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def is_api_gateway_event(event: dict[str, Any]) -> bool:
    return "requestContext" in event and "body" in event
