# Real-time Transaction Fraud Detection Platform

Free local-first project skeleton for a banking-style, real-time transaction fraud detection platform.

No AWS, Snowflake, MinIO, or paid cloud services are used in this local development setup.

## Architecture

The target local flow is:

```text
Kafka -> Spark -> local data lake -> Postgres warehouse -> Airflow -> MLflow -> FastAPI
```

- `banking-core`: Spring Boot service that receives transaction requests and publishes accepted transaction events to Kafka.
- `spark-streaming`: Future Spark Structured Streaming jobs that read Kafka events and write raw and cleaned data to the local `data-lake/` folder.
- `data-lake`: Local filesystem data lake with bronze, silver, quarantine, features, and labels zones.
- `postgres`: Local Postgres data warehouse for curated tables, feature tables, and model-serving features.
- `airflow`: Local Airflow orchestration for warehouse loading, feature engineering, data quality checks, and model training.
- `training`: Python model training pipeline that trains fraud detection baselines and logs experiments to local MLflow.
- `fraud-decision-api`: FastAPI service that serves fraud predictions using features from Postgres and models from MLflow or local fallback artifacts.
- `infra/docker-compose.yml`: Local development infrastructure.
- `infra/k8s`: Future kind/Kubernetes manifests for stateless services only: `banking-core` and `fraud-decision-api`.

## Repository Layout

```text
docs/
services/
pipelines/
infra/
data-lake/
tests/
.github/workflows/
```

## Current State

This repository contains the local development infrastructure, transaction ingestion, lake-to-warehouse pipelines, feature engineering, training, and fraud decision API scaffolding.

## Local Infrastructure

Create a local environment file before starting services:

```sh
cp .env.example .env
```

Start the local free infrastructure:

```sh
make up
```

Useful commands:

```sh
make ps
make logs
make down
make e2e
```

Local service URLs:

- Kafka UI: http://localhost:8080
- Spark master UI: http://localhost:8081
- Spark worker UI: http://localhost:8082
- Airflow UI: http://localhost:8083
- MLflow UI: http://localhost:5000
- Postgres: `localhost:55432`

This phase uses only local free infrastructure. Keep local credentials in `.env` and never commit real secrets.

## banking-core

`services/banking-core` is a Spring Boot service for transaction ingestion.

Endpoints:

- `GET /health`
- `POST /internal/transactions`

Run tests:

```sh
cd services/banking-core
.\gradlew.cmd test
```

Run locally after starting Kafka:

```sh
cd services/banking-core
.\gradlew.cmd run
```

Build the service image:

```sh
docker build -t banking-core:local services/banking-core
```

Accepted transactions are published to the Kafka topic configured by `TRANSACTION_EVENTS_TOPIC`, which defaults to `transaction_events`.

Before returning the transaction response, `banking-core` calls `fraud-decision-api` at `FRAUD_API_BASE_URL` and includes:

- `decision`
- `fraud_probability`
- `risk_level`
- `reason_codes`

If the fraud API is unavailable or times out, `banking-core` still publishes the Kafka event and returns:

```json
{
  "decision": "REVIEW",
  "fraud_probability": 0,
  "risk_level": "MEDIUM",
  "reason_codes": ["fraud service unavailable"]
}
```

## Postgres Warehouse

Postgres runs as the local data warehouse. Init scripts in `pipelines/postgres/ddl/` are mounted into the Postgres container and run automatically when the `postgres_data` volume is first created.

Connection defaults from `.env.example`:

```text
Host: localhost
Host port: 55432
Container port: 5432
Docker host port variable: POSTGRES_HOST_PORT=55432
Local script port variable: POSTGRES_PORT=55432
Database: transaction_risk
User: risk_user
Password: risk_password
```

Connect with `psql`:

```sh
psql "postgresql://risk_user:risk_password@localhost:55432/transaction_risk"
```

Or connect through Docker:

```sh
docker exec -it fraud-platform-postgres psql -U risk_user -d transaction_risk
```

Verify schemas and tables:

```sql
SELECT schema_name
FROM information_schema.schemata
WHERE schema_name IN ('raw', 'core', 'features', 'mlops')
ORDER BY schema_name;

SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema IN ('raw', 'core', 'features', 'mlops')
ORDER BY table_schema, table_name;
```

Expected warehouse tables:

- `raw.transactions_raw`
- `core.cleaned_transactions`
- `features.customer_transaction_features`
- `mlops.prediction_logs`

## Spark Streaming

`pipelines/spark-streaming/transaction_streaming_job.py` reads Kafka topic `transaction_events` and writes to the local data lake:

- Bronze raw JSON: `data-lake/bronze/transactions/`
- Silver cleaned Parquet: `data-lake/silver/transactions_cleaned/`
- Quarantine JSON with `error_reason`: `data-lake/quarantine/bad_transactions/`
- Checkpoints: `data-lake/checkpoints/transaction_streaming/`

Run validation tests:

```sh
cd pipelines/spark-streaming
py -m unittest discover -s tests
```

## Airflow Lake To Postgres

`pipelines/airflow/dags/local_lake_to_postgres_dag.py` loads silver transaction Parquet files into Postgres.

DAG:

```text
local_lake_to_postgres_transactions
```

What it does:

- Checks for Parquet files under `data-lake/silver/transactions_cleaned`
- Loads rows into `raw.transactions_raw`
- Runs `pipelines/postgres/transforms/raw_to_core_cleaned_transactions.sql`
- Deduplicates core records by `event_id`
- Logs raw rows loaded and total core rows after transform

Restart local infrastructure after changing Airflow dependencies or DAG mounts:

```sh
make down
make up
```

Open Airflow:

```text
http://localhost:8083
```

Default local login from `.env.example`:

```text
Username: admin
Password: change-me-local-only
```

In the Airflow UI, enable and trigger:

```text
local_lake_to_postgres_transactions
```

Or trigger from the Airflow container:

```sh
docker exec -it fraud-platform-airflow-webserver airflow dags trigger local_lake_to_postgres_transactions
```

Verify rows in Postgres:

```sh
docker exec -it fraud-platform-postgres psql -U risk_user -d transaction_risk
```

Then run:

```sql
SELECT COUNT(*) FROM raw.transactions_raw;
SELECT COUNT(*) FROM core.cleaned_transactions;
```

## Postgres Feature Engineering

`pipelines/airflow/dags/postgres_feature_dag.py` builds customer transaction features from `core.cleaned_transactions`.

DAG:

```text
postgres_customer_transaction_features
```

What it does:

- Checks `core.cleaned_transactions` exists and has rows
- Runs `pipelines/postgres/transforms/customer_transaction_features.sql`
- Upserts `features.customer_transaction_features`
- Runs data quality checks from `pipelines/data-quality/check_feature_tables.py`
- Logs feature row count

After `local_lake_to_postgres_transactions` succeeds, trigger this DAG in Airflow:

```text
postgres_customer_transaction_features
```

Verify feature rows:

```sh
docker exec -it fraud-platform-postgres psql -U risk_user -d transaction_risk
```

Then run:

```sql
SELECT COUNT(*) FROM features.customer_transaction_features;

SELECT user_id,
       tx_count_5min,
       tx_count_1h,
       tx_count_24h,
       spend_24h,
       feature_snapshot_at
FROM features.customer_transaction_features
ORDER BY feature_snapshot_at DESC
LIMIT 5;
```

## Fraud Model Training

`pipelines/training` trains local baseline fraud models from Postgres data and logs experiments to local MLflow.

Inputs:

- `core.cleaned_transactions`
- `features.customer_transaction_features`
- `core.fraud_labels`

If labels do not exist, the pipeline creates `core.fraud_labels` and generates synthetic labels for local workflow testing.

Run after the feature DAG succeeds:

```sh
cd pipelines/training
py -m pip install -r requirements.txt
py generate_synthetic_fraud_labels.py
py train_fraud_model.py
```

Outputs:

- MLflow experiment: `fraud-risk-training`
- Registered model: `fraud-risk-model`
- Local fallback artifact: `model-artifacts/fraud-risk-model/`

Open MLflow:

```text
http://localhost:5000
```

## Fraud Decision API

`services/fraud-decision-api` serves local fraud predictions with FastAPI.

Endpoints:

- `GET /health`
- `GET /v1/model-info`
- `POST /v1/fraud-score`
- `GET /metrics`

The service loads `fraud-risk-model` from local MLflow when available. If MLflow is unavailable, it loads the fallback artifact from `FALLBACK_MODEL_DIR`.

Run after phase 7 has produced `pipelines/training/model-artifacts/fraud-risk-model/model.joblib`:

```sh
cd services/fraud-decision-api
py -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Example request:

```sh
curl -X POST http://localhost:8000/v1/fraud-score \
  -H "Content-Type: application/json" \
  -d '{
    "transaction_id": "tx_demo_001",
    "user_id": "user_001",
    "amount": 125.5,
    "merchant_category": "GROCERY",
    "country": "AU",
    "channel": "MOBILE",
    "event_timestamp": "2026-06-26T01:30:00Z"
  }'
```

Run tests:

```sh
cd services/fraud-decision-api
py -m pytest
```

## Local Kubernetes With kind

Kubernetes deploys only stateless services:

- `banking-core`
- `fraud-decision-api`

Kafka, Spark, Airflow, Postgres, MLflow, and the local data lake stay in Docker Compose.

Create the kind cluster, build images, load images, and deploy:

```sh
make k8s-create
make k8s-build-images
make k8s-load-images
make k8s-deploy
make k8s-status
```

Delete the cluster:

```sh
make k8s-delete
```

See `docs/KUBERNETES_DEPLOYMENT.md` for secret placeholders, local port mappings, and smoke-test steps.

kind exposes Kubernetes services on separate host ports to avoid conflicts with local app processes:

- `banking-core`: http://localhost:18084
- `fraud-decision-api`: http://localhost:18080

## Tests And CI

Local-only checks can use Docker Compose, kind, and long-running services:

```sh
make up
make e2e
make k8s-create
make k8s-build-images
make k8s-load-images
make k8s-deploy
```

GitHub Actions CI does not require Docker Compose, AWS, Snowflake, or cloud credentials. The CI workflow runs:

- `banking-core` Java tests
- `fraud-decision-api` Python tests
- training Python tests when present
- spark-streaming Python tests when present
- Docker image builds without pushing to a registry
- Kubernetes YAML validation

## TODO

- TODO Phase 1: Define transaction event contracts and API request/response contracts.
- TODO Phase 2: Extend `banking-core` contract tests after data contracts are finalized.
- TODO Phase 3: Implement Spark streaming ingestion to the local data lake.
- TODO Phase 4: Implement Airflow DAGs, Postgres DDL/transforms, data quality checks, and feature engineering.
- TODO Phase 5: Implement model training and local MLflow experiment tracking.
- TODO Phase 9: Add kind/Kubernetes manifests for stateless services.
- TODO Phase 10: Add contract, integration, and end-to-end tests.
