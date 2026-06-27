# Architecture

## Target Flow

1. Spring Boot `auth-service` can register local users and issue JWT access tokens for demos.
2. Spring Boot `banking-core` receives transaction requests.
3. `banking-core` publishes transaction events to Kafka.
4. Spark Structured Streaming reads Kafka events.
5. Spark writes raw and cleaned transaction data to the local `data-lake/` folder.
6. Postgres stores curated warehouse tables and fraud feature tables.
7. Airflow orchestrates warehouse loading, feature engineering, data quality checks, and model training.
8. Python training pipeline trains fraud models and logs experiments to local MLflow.
9. FastAPI `fraud-decision-api` serves predictions using features from Postgres.
10. `banking-core` records best-effort transaction request and response audit records in Postgres.
11. `banking-core` supports account status validation, idempotent transaction retries, and local outbox tracking for Kafka publication.

## Local Infrastructure

Docker Compose runs Kafka, Kafka UI, Spark master, Spark worker, Airflow webserver, Airflow scheduler, Postgres, and MLflow.

## Deployment Boundary

Kubernetes with kind deploys only stateless services:

- `banking-core`
- `auth-service`
- `fraud-decision-api`

Stateful local infrastructure such as Kafka, Postgres, Airflow, Spark, MLflow, and the local data lake is not deployed by the Kubernetes app manifests.

## TODO

- TODO Future: Add architecture diagrams.
- TODO Future: Add production deployment topology after cloud target is selected.
