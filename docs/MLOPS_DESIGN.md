# MLOps Design

## Responsibilities

- Train fraud detection models in the Python training pipeline.
- Log experiments, parameters, metrics, and artifacts to local MLflow.
- Store MLflow artifacts in local Docker-managed storage.
- Promote model versions through explicit review steps.
- Serve approved model artifacts through `fraud-decision-api`.
- Read model-serving features from Postgres.

## TODO

- TODO Phase 5: Define training data extraction from Postgres.
- TODO Phase 5: Define evaluation metrics and acceptance thresholds.
- TODO Phase 5: Define MLflow experiment naming and artifact layout.
- TODO Phase 6: Define model loading strategy for serving.
