from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class CheckResult:
    name: str
    status: str
    detail: str


REQUIRED_RESPONSE_FIELDS = [
    "transaction_id",
    "event_id",
    "decision",
    "fraud_probability",
    "risk_level",
]


def main() -> int:
    load_env_file()
    results: list[CheckResult] = []
    transaction_id: str | None = None

    try:
        response = send_transaction()
        transaction_id = str(response.get("transaction_id", ""))
        missing_fields = [field for field in REQUIRED_RESPONSE_FIELDS if field not in response]
        if missing_fields:
            results.append(CheckResult("banking-core response", "FAIL", f"missing fields: {missing_fields}"))
        else:
            results.append(
                CheckResult(
                    "banking-core response",
                    "PASS",
                    "transaction_id={transaction_id} decision={decision} risk_level={risk_level} "
                    "fraud_probability={fraud_probability} reason_codes={reason_codes}".format(
                        transaction_id=response["transaction_id"],
                        decision=response["decision"],
                        risk_level=response["risk_level"],
                        fraud_probability=response["fraud_probability"],
                        reason_codes=response.get("reason_codes", []),
                    ),
                )
            )
            reason_codes = [str(reason).lower() for reason in response.get("reason_codes", [])]
            if "fraud service unavailable" in reason_codes:
                results.append(
                    CheckResult(
                        "fraud API integration",
                        "FAIL",
                        "banking-core used fallback REVIEW; start fraud-decision-api and restart banking-core",
                    )
                )
            else:
                results.append(CheckResult("fraud API integration", "PASS", "banking-core received fraud API decision"))
    except Exception as exc:
        results.append(CheckResult("banking-core response", "FAIL", str(exc)))

    if transaction_id:
        results.append(check_kafka_event(transaction_id))
        results.extend(check_data_lake_paths())
        results.append(check_postgres_cleaned_transaction(transaction_id))
        results.append(check_postgres_prediction_log(transaction_id))
    else:
        results.append(CheckResult("kafka transaction event", "SKIP", "no transaction_id from banking-core"))
        results.extend(check_data_lake_paths())
        results.append(CheckResult("postgres core transaction", "SKIP", "no transaction_id from banking-core"))
        results.append(CheckResult("postgres prediction log", "SKIP", "no transaction_id from banking-core"))

    print_report(results)
    return 1 if any(result.status == "FAIL" for result in results) else 0


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


def send_transaction() -> dict[str, Any]:
    base_url = os.getenv("BANKING_CORE_BASE_URL", "http://localhost:8084").rstrip("/")
    payload = {
        "user_id": os.getenv("E2E_USER_ID", "user_001"),
        "account_id": os.getenv("E2E_ACCOUNT_ID", "acc_e2e_001"),
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
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url}/internal/transactions",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    timeout_seconds = float(os.getenv("E2E_HTTP_TIMEOUT_SECONDS", "10"))
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {body}") from exc


def check_kafka_event(transaction_id: str) -> CheckResult:
    if os.getenv("E2E_SKIP_KAFKA_CHECK", "").lower() in {"1", "true", "yes"}:
        return CheckResult("kafka transaction event", "SKIP", "disabled by E2E_SKIP_KAFKA_CHECK")

    try:
        from kafka import KafkaConsumer
    except ImportError:
        return CheckResult(
            "kafka transaction event",
            "SKIP",
            "kafka-python is not installed; install it or inspect Kafka UI manually",
        )

    bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    topic = os.getenv("TRANSACTION_EVENTS_TOPIC", "transaction_events")
    timeout_ms = int(float(os.getenv("E2E_KAFKA_TIMEOUT_SECONDS", "15")) * 1000)
    deadline = time.time() + timeout_ms / 1000

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap_servers,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        consumer_timeout_ms=1000,
        value_deserializer=lambda value: json.loads(value.decode("utf-8")),
    )
    try:
        while time.time() < deadline:
            for message in consumer:
                value = message.value
                if value.get("transaction_id") == transaction_id:
                    return CheckResult("kafka transaction event", "PASS", f"observed in topic {topic}")
    finally:
        consumer.close()

    return CheckResult("kafka transaction event", "WARN", f"not observed within {timeout_ms} ms")


def check_data_lake_paths() -> list[CheckResult]:
    root = Path(os.getenv("DATA_LAKE_ROOT", "data-lake"))
    bronze = root / "bronze"
    silver = root / "silver"
    return [
        check_path_has_generated_data("data lake bronze", bronze),
        check_path_has_generated_data("data lake silver", silver),
    ]


def check_path_has_generated_data(name: str, path: Path) -> CheckResult:
    if not path.exists():
        return CheckResult(name, "SKIP", f"{path} does not exist")

    generated_files = [
        item
        for item in path.rglob("*")
        if item.is_file() and item.name != ".gitkeep" and not item.name.endswith(".crc")
    ]
    if generated_files:
        return CheckResult(name, "PASS", f"found {len(generated_files)} generated file(s)")
    return CheckResult(name, "WARN", f"no generated files under {path}; run Spark pipeline first")


def check_postgres_cleaned_transaction(transaction_id: str) -> CheckResult:
    query = "SELECT COUNT(*) FROM core.cleaned_transactions WHERE transaction_id = %s"
    return check_postgres_count(
        "postgres core transaction",
        query,
        (transaction_id,),
        empty_detail="not found; run Spark and Airflow lake-to-postgres pipeline after this transaction",
        empty_status="WARN",
    )


def check_postgres_prediction_log(transaction_id: str) -> CheckResult:
    query = "SELECT COUNT(*) FROM mlops.prediction_logs WHERE transaction_id = %s"
    return check_postgres_count(
        "postgres prediction log",
        query,
        (transaction_id,),
        empty_detail="not found in mlops.prediction_logs",
        empty_status="FAIL",
    )


def check_postgres_count(
    name: str,
    query: str,
    params: tuple[Any, ...],
    empty_detail: str,
    empty_status: str,
) -> CheckResult:
    try:
        import psycopg2
    except ImportError:
        return CheckResult(name, "SKIP", "psycopg2-binary is not installed")

    try:
        with psycopg2.connect(
            host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
            port=int(os.getenv("POSTGRES_PORT", "55432")),
            dbname=os.getenv("POSTGRES_DB", "transaction_risk"),
            user=os.getenv("POSTGRES_USER", "risk_user"),
            password=os.getenv("POSTGRES_PASSWORD", ""),
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                count = cursor.fetchone()[0]
    except Exception as exc:
        return CheckResult(name, "WARN", f"query failed: {exc}")

    if count > 0:
        return CheckResult(name, "PASS", f"found {count} row(s)")
    return CheckResult(name, empty_status, empty_detail)


def print_report(results: list[CheckResult]) -> None:
    print("\nLocal fraud detection e2e report")
    print("=" * 37)
    for result in results:
        print(f"[{result.status}] {result.name}: {result.detail}")

    summary = {
        "PASS": sum(1 for result in results if result.status == "PASS"),
        "WARN": sum(1 for result in results if result.status == "WARN"),
        "SKIP": sum(1 for result in results if result.status == "SKIP"),
        "FAIL": sum(1 for result in results if result.status == "FAIL"),
    }
    print("-" * 37)
    print(
        f"PASS={summary['PASS']} WARN={summary['WARN']} "
        f"SKIP={summary['SKIP']} FAIL={summary['FAIL']}"
    )


if __name__ == "__main__":
    sys.exit(main())
