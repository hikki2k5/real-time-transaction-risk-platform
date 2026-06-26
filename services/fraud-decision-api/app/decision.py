from __future__ import annotations

from typing import Any


LOW_RISK_THRESHOLD = 0.40
HIGH_RISK_THRESHOLD = 0.80


def classify_decision(fraud_probability: float) -> tuple[str, str]:
    if fraud_probability >= HIGH_RISK_THRESHOLD:
        return "HIGH", "BLOCK"
    if fraud_probability >= LOW_RISK_THRESHOLD:
        return "MEDIUM", "REVIEW"
    return "LOW", "APPROVE"


def build_reason_codes(
    fraud_probability: float,
    request_data: dict[str, Any],
    features_found: bool,
) -> list[str]:
    reason_codes: list[str] = []

    if fraud_probability >= HIGH_RISK_THRESHOLD:
        reason_codes.append("HIGH_MODEL_SCORE")
    elif fraud_probability >= LOW_RISK_THRESHOLD:
        reason_codes.append("MEDIUM_MODEL_SCORE")
    else:
        reason_codes.append("LOW_MODEL_SCORE")

    if not features_found:
        reason_codes.append("USER_FEATURES_MISSING")
    if float(request_data.get("amount", 0)) >= 1000:
        reason_codes.append("HIGH_AMOUNT")
    if str(request_data.get("country", "")).upper() not in {"AU", "AUS", "AUSTRALIA"}:
        reason_codes.append("OVERSEAS_TRANSACTION")

    return reason_codes
