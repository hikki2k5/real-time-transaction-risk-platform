# Fraud Decision API

FastAPI model serving service for local fraud scoring.

## Endpoints

- `GET /health`
- `GET /v1/model-info`
- `POST /v1/fraud-score`
- `GET /metrics`

## Configuration

```text
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=55432
POSTGRES_DB=transaction_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=risk_password
MLFLOW_TRACKING_URI=http://localhost:5000
MODEL_NAME=fraud-risk-model
FALLBACK_MODEL_DIR=pipelines/training/model-artifacts/fraud-risk-model
```

The service first tries to load `fraud-risk-model` from local MLflow. If MLflow is unavailable, it loads the local fallback artifact from `FALLBACK_MODEL_DIR`.

## Run Locally

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

## Tests

```sh
pytest
```

## TODO

- TODO Phase 8: Add authentication once API gateway design is defined.
- TODO Phase 8: Add model promotion controls before production-style serving.
- TODO Phase 9: Add Kubernetes manifests for stateless deployment.
