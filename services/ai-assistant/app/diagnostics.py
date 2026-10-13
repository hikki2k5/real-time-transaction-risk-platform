"""Emit error types/codes only; provider exception messages can contain secrets."""
import json
import logging
import re

logger = logging.getLogger(__name__)


def log_failure(stage: str, error: Exception):
    chain = []
    current = error
    seen = set()
    while current is not None and id(current) not in seen and len(chain) < 8:
        seen.add(id(current))
        entry = {"type": type(current).__name__}
        sqlstate = getattr(current, "pgcode", None)
        if isinstance(sqlstate, str) and re.fullmatch(r"[0-9A-Z]{5}", sqlstate):
            entry["sqlstate"] = sqlstate
        code = getattr(current, "code", None)
        if isinstance(code, int) and 100 <= code <= 599:
            entry["http_status"] = code
        chain.append(entry)
        current = current.__cause__ or current.__context__
    logger.error("assistant_failure %s", json.dumps({"stage": stage, "errors": chain}))
