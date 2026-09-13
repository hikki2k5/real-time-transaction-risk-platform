from __future__ import annotations

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "fraud_decision_requests_total",
    "Total fraud score requests.",
)
REQUEST_LATENCY = Histogram(
    "fraud_decision_latency_seconds",
    "Fraud score request latency in seconds.",
)
DECISION_COUNT = Counter(
    "fraud_decision_decisions_total",
    "Fraud decision count by label.",
    ["decision"],
)
FEATURE_CACHE_EVENTS = Counter(
    "fraud_feature_cache_events_total",
    "Customer feature cache lookups by result.",
    ["result"],
)
FEATURE_DB_LOOKUPS = Counter(
    "fraud_feature_db_lookups_total",
    "Postgres lookups for customer transaction features.",
)
