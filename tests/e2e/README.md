# Local End-to-End Fraud Detection Flow

This smoke test sends one transaction through `banking-core` and verifies the local fraud flow as far as the currently running services allow.

## Prerequisites

- Docker Compose infrastructure is running.
- `fraud-decision-api` is running.
- `banking-core` is running.
- Postgres credentials are available through environment variables.
- Optional: install `kafka-python` if you want the script to inspect Kafka directly.

## Run

From the repository root:

```sh
make e2e
```

Or directly:

```sh
py tests/e2e/run_fraud_detection_flow.py
```

The script reads `.env` by default. If `.env` does not exist, it reads `.env.example`. Set `ENV_FILE` to point at another local env file.

## Environment

```text
BANKING_CORE_BASE_URL=http://localhost:8084
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
TRANSACTION_EVENTS_TOPIC=transaction_events
DATA_LAKE_ROOT=data-lake
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
POSTGRES_DB=transaction_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=local-only-password
```

Transaction payload fields can be overridden with:

```text
E2E_USER_ID
E2E_ACCOUNT_ID
E2E_AMOUNT
E2E_CURRENCY
E2E_MERCHANT_CATEGORY
E2E_TRANSACTION_TYPE
E2E_CHANNEL
E2E_COUNTRY
E2E_CITY
E2E_STATUS
E2E_EVENT_TIMESTAMP
```

## Notes

- Kafka checking is skipped if `kafka-python` is not installed.
- Bronze and silver checks warn instead of failing when Spark has not run yet.
- `core.cleaned_transactions` warns instead of failing when Spark/Airflow has not loaded the newly submitted transaction yet.
- `mlops.prediction_logs` should pass when `fraud-decision-api` is reachable from `banking-core`.
