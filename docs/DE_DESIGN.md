# Data Engineering Design

## Responsibilities

- Spark Structured Streaming reads Kafka transaction events.
- Spark writes bronze, silver, and quarantine datasets to the local `data-lake/` folder.
- Airflow loads local data lake outputs into Postgres.
- Postgres transforms build feature tables for fraud detection.
- Airflow runs data quality checks before model training.

## TODO

- TODO Phase 3: Define Spark checkpointing and output partition strategy.
- TODO Phase 3: Define bronze, silver, and quarantine local data lake paths.
- TODO Phase 4: Define Airflow DAG ownership and schedules.
- TODO Phase 4: Define Postgres DDL and transform conventions.
- TODO Phase 4: Add data quality checks.
