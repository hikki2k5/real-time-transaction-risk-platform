# Fraud Model Training

Local fraud model training pipeline using Postgres feature tables, LightGBM, XGBoost, and local MLflow.

## Why PR-AUC And Fraud Recall Matter

Fraud detection is imbalanced: most transactions are legitimate, and fraudulent examples are rare. Accuracy can look high even when a model misses nearly all fraud. PR-AUC focuses on the positive fraud class, and recall measures how many fraudulent transactions are caught. For this local project, use these metrics to compare pipeline behavior, not to claim real-world model quality.

Synthetic labels are generated only when no labels exist. They are useful for testing the end-to-end training and MLflow workflow, not for production accuracy.

## Environment

```text
POSTGRES_HOST=localhost
POSTGRES_PORT=55432
POSTGRES_DB=transaction_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=risk_password
MLFLOW_TRACKING_URI=http://localhost:5000
```

## Install

```sh
cd pipelines/training
py -m pip install -r requirements.txt
```

## Run

Make sure these upstream steps have already succeeded:

1. `local_lake_to_postgres_transactions`
2. `postgres_customer_transaction_features`

Generate synthetic labels:

```sh
py generate_synthetic_fraud_labels.py
```

Train and register the best model:

```sh
py train_fraud_model.py
```

Outputs:

- MLflow experiment: `fraud-risk-training`
- Registered model: `fraud-risk-model`
- Local fallback artifact: `model-artifacts/fraud-risk-model/model.joblib`

Model candidates:

- LightGBM binary classifier with fraud class weighting.
- XGBoost binary classifier with fraud class weighting.

Open MLflow:

```text
http://localhost:5000
```

## Tests

```sh
py -m unittest discover -s tests
```

## TODO

- TODO Phase 7: Replace synthetic labels with real adjudicated fraud labels.
- TODO Phase 7: Add model promotion criteria and manual approval workflow.
- TODO Phase 8: Wire the fallback artifact into `fraud-decision-api`.
