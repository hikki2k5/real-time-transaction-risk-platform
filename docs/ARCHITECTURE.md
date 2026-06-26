# Architecture

## Target Flow

1. Spring Boot `banking-core` receives transaction requests.
2. `banking-core` publishes transaction events to Kafka.
3. Spark Structured Streaming reads Kafka events.
4. Spark writes raw and cleaned transaction data to the local `data-lake/` folder.
5. Postgres stores curated warehouse tables and fraud feature tables.
6. Airflow orchestrates warehouse loading, feature engineering, data quality checks, and model training.
7. Python training pipeline trains fraud models and logs experiments to local MLflow.
8. FastAPI `fraud-decision-api` serves predictions using features from Postgres.

## Local Infrastructure

Docker Compose runs Kafka, Kafka UI, Spark master, Spark worker, Airflow webserver, Airflow scheduler, Postgres, and MLflow.

## Deployment Boundary

Kubernetes with kind deploys only stateless services:

- `banking-core`
- `fraud-decision-api`

Stateful local infrastructure such as Kafka, Postgres, Airflow, Spark, MLflow, and the local data lake is not deployed by the Kubernetes app manifests.

## TODO

- TODO Phase 1: Add architecture diagrams.
- TODO Phase 2: Define local development topology.
- TODO Phase 7: Document kind deployment flow.
