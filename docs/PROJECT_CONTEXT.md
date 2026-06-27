# Project Context

## Purpose

Build a free local-first banking-style real-time transaction fraud detection platform that supports streaming ingestion, local data lake storage, local warehouse feature engineering, model training, and online fraud decisions.

## Scope

This repository contains a local-first implementation of the main platform pieces: Spring Boot auth and transaction ingestion, Kafka publishing, Spark lake ingestion, Airflow/Postgres transforms, model training, FastAPI model serving, local e2e checks, and kind manifests for stateless services.

The project does not use AWS, Snowflake, MinIO, or paid cloud services.

## TODO

- TODO Phase 1: Document business use cases, fraud decision workflow, and non-functional requirements.
- TODO Phase 1: Define the first version of transaction, feature, and prediction contracts.
- TODO Future: Replace synthetic fraud labels with adjudicated labels.
- TODO Future: Add production-grade OAuth2/OIDC integration.
- TODO Future: Add cloud deployment modules after local architecture is stable.
