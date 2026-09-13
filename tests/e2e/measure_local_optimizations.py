from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def main() -> int:
    load_env_file()
    print("\nLocal optimization measurement")
    print("=" * 34)

    measure_fraud_cache_latency()
    submit_measurement_transactions()
    print_fraud_cache_metrics()
    print_idempotency_metrics()
    print_pipeline_metrics()
    return 0


def load_env_file() -> None:
    env_file = Path(os.getenv("ENV_FILE", ".env"))
    if not env_file.exists():
        env_file = Path(".env.example")
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def submit_measurement_transactions() -> None:
    base_url = os.getenv("BANKING_CORE_BASE_URL", "http://localhost:8084").rstrip("/")
    token = os.getenv("BANKING_CORE_ACCESS_TOKEN", "").strip()
    payload = {
        "user_id": os.getenv("E2E_USER_ID", "user_001"),
        "account_id": os.getenv("E2E_ACCOUNT_ID", "acct_001"),
        "amount": float(os.getenv("E2E_AMOUNT", "125.50")),
        "currency": os.getenv("E2E_CURRENCY", "AUD"),
        "merchant_category": os.getenv("E2E_MERCHANT_CATEGORY", "GROCERY"),
        "transaction_type": os.getenv("E2E_TRANSACTION_TYPE", "CARD_PAYMENT"),
        "channel": os.getenv("E2E_CHANNEL", "MOBILE"),
        "country": os.getenv("E2E_COUNTRY", "AU"),
        "city": os.getenv("E2E_CITY", "Sydney"),
        "status": os.getenv("E2E_STATUS", "APPROVED"),
        "event_timestamp": os.getenv("E2E_EVENT_TIMESTAMP", "2026-06-26T01:30:00Z"),
    }
    idempotency_key = f"measure-{int(time.time())}"

    print("\n2. Banking idempotency latency sample")
    first = post_json(f"{base_url}/internal/transactions", payload, token, idempotency_key)
    second = post_json(f"{base_url}/internal/transactions", payload, token, idempotency_key)
    third = post_json(f"{base_url}/internal/transactions", payload, token, f"{idempotency_key}-new")

    print(f"- First request: {status_label(first)} latency_ms={first['latency_ms']}")
    print(f"- Duplicate same-key retry: {status_label(second)} latency_ms={second['latency_ms']}")
    print(f"- Same user new key: {status_label(third)} latency_ms={third['latency_ms']}")
    print_latency_delta(
        label="- Idempotency retry latency reduction",
        baseline_ms=first["latency_ms"],
        optimized_ms=second["latency_ms"],
    )


def measure_fraud_cache_latency() -> None:
    base_url = os.getenv("FRAUD_API_BASE_URL", "http://localhost:8000").rstrip("/")
    user_id = os.getenv("E2E_USER_ID", "user_001")
    clear_feature_cache(user_id)

    payload = {
        "transaction_id": f"measure-cache-miss-{int(time.time())}",
        "user_id": user_id,
        "amount": float(os.getenv("E2E_AMOUNT", "125.50")),
        "merchant_category": os.getenv("E2E_MERCHANT_CATEGORY", "GROCERY"),
        "country": os.getenv("E2E_COUNTRY", "AU"),
        "channel": os.getenv("E2E_CHANNEL", "MOBILE"),
        "event_timestamp": os.getenv("E2E_EVENT_TIMESTAMP", "2026-06-26T01:30:00Z"),
    }

    print("\n1. Fraud cache latency sample")
    miss = post_json(f"{base_url}/v1/fraud-score", payload, token="", idempotency_key="")
    hits = []
    for index in range(3):
        hit_payload = dict(payload)
        hit_payload["transaction_id"] = f"measure-cache-hit-{int(time.time())}-{index}"
        hits.append(post_json(f"{base_url}/v1/fraud-score", hit_payload, token="", idempotency_key=""))

    hit_latencies = [result["latency_ms"] for result in hits if result["ok"]]
    print(f"- First score after cache clear: {status_label(miss)} latency_ms={miss['latency_ms']}")
    for index, result in enumerate(hits, start=1):
        print(f"- Warm-cache score {index}: {status_label(result)} latency_ms={result['latency_ms']}")
    if miss["ok"] and hit_latencies:
        avg_hit_ms = round(sum(hit_latencies) / len(hit_latencies), 2)
        print_latency_delta(
            label="- Redis cache latency reduction",
            baseline_ms=miss["latency_ms"],
            optimized_ms=avg_hit_ms,
        )


def clear_feature_cache(user_id: str) -> None:
    try:
        import redis
    except ImportError:
        print("- Redis package not installed locally; cache latency sample will use current cache state.")
        return

    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=int(os.getenv("REDIS_DB", "0")),
            socket_connect_timeout=1,
            socket_timeout=1,
            decode_responses=True,
        )
        client.delete(f"customer_features:{user_id}")
    except Exception as exc:
        print(f"- Could not clear Redis feature cache first: {exc}")


def print_latency_delta(label: str, baseline_ms: float, optimized_ms: float) -> None:
    saved_ms = round(baseline_ms - optimized_ms, 2)
    if baseline_ms <= 0:
        print(f"{label}: unavailable")
        return
    saved_pct = round((saved_ms / baseline_ms) * 100, 1)
    print(
        f"{label}: baseline_ms={baseline_ms} optimized_ms={optimized_ms} "
        f"saved_ms={saved_ms} saved_pct={saved_pct}%"
    )


def post_json(url: str, payload: dict[str, Any], token: str, idempotency_key: str) -> dict[str, Any]:
    headers = {"Content-Type": "application/json"}
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    start_time = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "ok": True,
                "status": response.status,
                "latency_ms": latency_ms,
                "body": json.loads(response.read().decode("utf-8")),
            }
    except urllib.error.HTTPError as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "ok": False,
            "status": exc.code,
            "latency_ms": latency_ms,
            "body": exc.read().decode("utf-8", errors="replace"),
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {"ok": False, "status": "ERROR", "latency_ms": latency_ms, "body": str(exc)}


def status_label(result: dict[str, Any]) -> str:
    if result["ok"]:
        body = result["body"]
        return f"HTTP {result['status']} decision={body.get('decision')} transaction_id={body.get('transaction_id')}"
    return f"HTTP {result['status']} {result['body']}"


def print_fraud_cache_metrics() -> None:
    base_url = os.getenv("FRAUD_API_BASE_URL", "http://localhost:8000").rstrip("/")
    print("\n3. Fraud feature cache metrics")
    try:
        metrics = get_text(f"{base_url}/metrics")
    except Exception as exc:
        print(f"- SKIP: cannot read fraud metrics: {exc}")
        return

    wanted = [
        "fraud_feature_cache_events_total",
        "fraud_feature_db_lookups_total",
    ]
    found = [line for line in metrics.splitlines() if any(line.startswith(name) for name in wanted)]
    if not found:
        print("- No fraud feature metrics found yet. Send a fraud-score request first.")
        return
    for line in found:
        print(f"- {line}")


def print_idempotency_metrics() -> None:
    base_url = os.getenv("BANKING_CORE_BASE_URL", "http://localhost:8084").rstrip("/")
    print("\n4. Banking idempotency metrics")
    try:
        payload = get_json(f"{base_url}/actuator/metrics/banking.idempotency.requests")
    except Exception as exc:
        print(f"- SKIP: cannot read banking metrics: {exc}")
        return

    for tag in payload.get("availableTags", []):
        if tag.get("tag") == "result":
            print(f"- Available result tags: {', '.join(tag.get('values', []))}")
    for result in ("miss", "hit", "conflict"):
        try:
            tagged = get_json(f"{base_url}/actuator/metrics/banking.idempotency.requests?tag=result:{result}")
            count = tagged.get("measurements", [{}])[0].get("value", 0)
            print(f"- result={result}: {count}")
        except Exception as exc:
            print(f"- result={result}: unavailable ({exc})")


def print_pipeline_metrics() -> None:
    root = Path(os.getenv("DATA_LAKE_ROOT", "data-lake"))
    report_path = root / "metrics" / "lake_to_postgres_transactions" / "latest.json"
    print("\n5. Lake-to-warehouse report")
    if not report_path.exists():
        print(f"- SKIP: {report_path} does not exist yet. Run the Airflow DAG first.")
        return
    report = json.loads(report_path.read_text(encoding="utf-8"))
    print(f"- source_file_count={report.get('source_file_count')}")
    print(f"- raw_rows_loaded={report.get('raw_rows_loaded')}")
    print(f"- load_duration_ms={report.get('load_duration_ms')}")
    print(f"- core_rows_after_transform={report.get('core_rows_after_transform')}")
    print(f"- transform_duration_ms={report.get('transform_duration_ms')}")
    print(f"- created_at={report.get('created_at')}")


def get_text(url: str) -> str:
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.read().decode("utf-8")


def get_json(url: str) -> dict[str, Any]:
    return json.loads(get_text(url))


if __name__ == "__main__":
    sys.exit(main())
