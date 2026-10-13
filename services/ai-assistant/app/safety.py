from __future__ import annotations

import re


INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous",
    "reveal system prompt",
    "show hidden prompt",
    "print the secret",
    "show jwt",
    "show password",
    "disable guardrails",
)

EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b")


def detect_guardrails(text: str) -> list[str]:
    lowered = text.lower()
    flags = [f"prompt_injection:{pattern}" for pattern in INJECTION_PATTERNS if pattern in lowered]
    if JWT_RE.search(text):
        flags.append("secret_like_token")
    return flags


def should_refuse(flags: list[str]) -> bool:
    return any(flag.startswith("prompt_injection") or flag == "secret_like_token" for flag in flags)


def redact_pii(text: str) -> str:
    text = EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    text = PHONE_RE.sub("[REDACTED_PHONE]", text)
    text = JWT_RE.sub("[REDACTED_TOKEN]", text)
    return text
