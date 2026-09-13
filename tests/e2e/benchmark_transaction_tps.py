from __future__ import annotations

import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


def main() -> int:
    load_env_file()
    request_count = int(os.getenv("BENCHMARK_REQUESTS", "50"))
    concurrency = int(os.getenv("BENCHMARK_CONCURRENCY", "5"))
    base_url = os.getenv("BANKING_CORE_BASE_URL", "http://localhost:8084").rstrip("/")

    print("\nLocal transaction API throughput benchmark")
    print("=" * 46)
    print(f"target={base_url}/internal/transactions")
    print(f"requests={request_count}")
    print(f"concurrency={concurrency}")

    started_at = time.perf_counter()
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_transaction, base_url, index) for index in range(request_count)]
        for future in as_completed(futures):
            results.append(future.result())
    duration_seconds = time.perf_counter() - started_at

    print_report(results, duration_seconds)
    return 1 if any(not result["ok"] for result in results) else 0


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


def send_transaction(base_url: str, index: int) -> dict[str, Any]:
    token = os.getenv("BANKING_CORE_ACCESS_TOKEN", "").strip()
    run_id = os.getenv("BENCHMARK_RUN_ID", str(int(time.time())))
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
    headers = {
        "Content-Type": "application/json",
        "Idempotency-Key": f"benchmark-{run_id}-{index}",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(
        f"{base_url}/internal/transactions",
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    started_at = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            latency_ms = (time.perf_counter() - started_at) * 1000
            body = json.loads(response.read().decode("utf-8"))
            return {
                "ok": 200 <= response.status < 300,
                "status": response.status,
                "latency_ms": round(latency_ms, 2),
                "decision": body.get("decision"),
            }
    except urllib.error.HTTPError as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000
        return {
            "ok": False,
            "status": exc.code,
            "latency_ms": round(latency_ms, 2),
            "error": exc.read().decode("utf-8", errors="replace")[:200],
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - started_at) * 1000
        return {
            "ok": False,
            "status": "ERROR",
            "latency_ms": round(latency_ms, 2),
            "error": str(exc),
        }


def print_report(results: list[dict[str, Any]], duration_seconds: float) -> None:
    success = [result for result in results if result["ok"]]
    failures = [result for result in results if not result["ok"]]
    latencies = [result["latency_ms"] for result in success]
    throughput = len(success) / duration_seconds if duration_seconds > 0 else 0

    print("\nResult")
    print("-" * 46)
    print(f"success={len(success)}")
    print(f"failed={len(failures)}")
    print(f"duration_seconds={duration_seconds:.2f}")
    print(f"throughput_tps={throughput:.2f}")
    if latencies:
        print(f"avg_latency_ms={statistics.fmean(latencies):.2f}")
        print(f"p50_latency_ms={percentile(latencies, 50):.2f}")
        print(f"p95_latency_ms={percentile(latencies, 95):.2f}")
        print(f"min_latency_ms={min(latencies):.2f}")
        print(f"max_latency_ms={max(latencies):.2f}")

    decisions: dict[str, int] = {}
    for result in success:
        decision = str(result.get("decision", "UNKNOWN"))
        decisions[decision] = decisions.get(decision, 0) + 1
    if decisions:
        print(f"decisions={decisions}")

    if failures:
        print("\nSample failures")
        for failure in failures[:3]:
            print(f"- status={failure['status']} latency_ms={failure['latency_ms']} error={failure.get('error')}")

    print("\nNote: this is a local benchmark for comparison, not a production load test.")


def percentile(values: list[float], percentile_value: int) -> float:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((percentile_value / 100) * (len(ordered) - 1))
    return ordered[index]


if __name__ == "__main__":
    sys.exit(main())
