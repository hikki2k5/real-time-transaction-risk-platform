"""Emit error types/codes only; provider exception messages can contain secrets."""
import json
import logging
import re

logger = logging.getLogger(__name__)


def database_reason(error):
    if type(error).__name__ != "OperationalError":
        return None
    # Inspect libpq text locally but log only these fixed categories.
    message = str(error).lower()
    categories = (
        ("unsupported startup parameter", "unsupported_startup_parameter"),
        ("password authentication failed", "database_authentication_failed"),
        ("could not translate host name", "database_dns_failed"),
        ("name or service not known", "database_dns_failed"),
        ("connection refused", "database_connection_refused"),
        ("timeout expired", "database_connection_timeout"),
        ("connection timed out", "database_connection_timeout"),
        ("ssl", "database_tls_error"),
        ("channel binding", "database_tls_error"),
    )
    for phrase, reason in categories:
        if phrase in message:
            return reason
    return "database_operational_error"


def log_failure(stage: str, error: Exception):
    chain = []
    current = error
    seen = set()
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        entry = {"type": type(current).__name__}
        reason = database_reason(current)
        if reason:
            entry["reason"] = reason
        sqlstate = getattr(current, "pgcode", None)
        if isinstance(sqlstate, str) and re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            entry["sqlstate"] = sqlstate
        code = getattr(current, "code", None)
        if isinstance(code, int) and 100 <= code <= 599:
            entry["http_status"] = code
        chain.append(entry)
        current = current.__cause__ or current.__context__
    logger.error("assistant_failure %s", json.dumps({"stage": stage, "errors": chain}))
