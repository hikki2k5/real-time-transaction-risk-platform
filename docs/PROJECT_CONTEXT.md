# Project Context

## Purpose

Build a free local-first banking-style real-time transaction fraud detection platform that supports streaming ingestion, local data lake storage, local warehouse feature engineering, model training, and online fraud decisions.

## Scope

This repository starts with skeleton docs, folders, and local infrastructure only. No application code is implemented yet.

The project does not use AWS, Snowflake, MinIO, or paid cloud services.

## TODO

- TODO Phase 1: Document business use cases, fraud decision workflow, and non-functional requirements.
- TODO Phase 1: Define the first version of transaction, feature, and prediction contracts.
- TODO Phase 2: Implement Spring Boot transaction ingestion and Kafka publishing.
- TODO Phase 3: Implement Spark streaming from Kafka to the local data lake.
- TODO Phase 4: Implement Airflow orchestration, Postgres loading, transforms, and data quality checks.
- TODO Phase 5: Implement model training with local MLflow tracking.
- TODO Phase 6: Implement FastAPI fraud prediction serving from Postgres features.
