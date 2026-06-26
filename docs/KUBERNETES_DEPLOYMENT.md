# Kubernetes Deployment

## Scope

Kubernetes with kind deploys only stateless services:

- `banking-core`
- `fraud-decision-api`

Kafka, Spark, Postgres, Airflow, MLflow, and the local data lake remain in Docker Compose for local development. Do not deploy those stateful services into kind for this project phase.

## Local Topology

```text
kind:
  banking-core
  fraud-decision-api

Docker Compose:
  Kafka
  Spark
  Airflow
  Postgres
  MLflow
  local data lake bind mount
```

The kind services reach Docker Compose services through `host.docker.internal` on Docker Desktop.

## Files

```text
infra/k8s/kind/kind-config.yaml
infra/k8s/namespace.yaml
infra/k8s/banking-core/
infra/k8s/fraud-decision-api/
```

Each service has:

- `deployment.yaml`
- `service.yaml`
- `configmap.yaml`
- `secret.yaml`
- `hpa.yaml`

## Ports

Kubernetes services expose the app ports through NodePorts, and kind maps those NodePorts to local host ports that avoid conflicts with local dev processes:

```text
banking-core:       localhost:18084 -> NodePort 30084 -> Service port 8084
fraud-decision-api: localhost:18080 -> NodePort 30080 -> Service port 8000
```

## Prerequisites

Install and verify:

```sh
docker --version
kind --version
kubectl version --client
```

Start local infrastructure first:

```sh
make up
```

## Create Cluster

```sh
make k8s-create
```

## Build And Load Images

```sh
make k8s-build-images
make k8s-load-images
```

Images:

```text
banking-core:local
fraud-decision-api:local
```

The local `fraud-decision-api:local` image bundles the fallback model artifact from:

```text
pipelines/training/model-artifacts/fraud-risk-model
```

## Deploy

```sh
make k8s-deploy
```

Deployment order:

1. Namespace
2. `fraud-decision-api`
3. `banking-core`

## Configure Secrets

The committed Secret manifests contain placeholders only. Do not commit real secrets.

After `make k8s-deploy`, replace the placeholder secret in the cluster before scoring against local Postgres:

```sh
kubectl create secret generic fraud-decision-api-secret \
  --namespace risk-platform \
  --from-literal=POSTGRES_PASSWORD=risk_password \
  --dry-run=client -o yaml | kubectl apply -f -

kubectl rollout restart deployment/fraud-decision-api -n risk-platform
```

`banking-core-secret` is currently a placeholder for future sensitive settings.

## Status

```sh
make k8s-status
```

Check pods:

```sh
kubectl get pods -n risk-platform
```

Check logs:

```sh
make k8s-logs
```

## Smoke Test

Check health endpoints:

```sh
curl http://localhost:18080/health
curl http://localhost:18084/health
```

Send a transaction through `banking-core`:

```sh
curl -X POST http://localhost:18084/internal/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_001",
    "account_id": "acc_001",
    "amount": 125.5,
    "currency": "AUD",
    "merchant_category": "GROCERY",
    "transaction_type": "CARD_PAYMENT",
    "channel": "MOBILE",
    "country": "AU",
    "city": "Sydney",
    "status": "APPROVED",
    "event_timestamp": "2026-06-26T01:30:00Z"
  }'
```

Expected response includes:

```text
transaction_id
event_id
decision
fraud_probability
risk_level
reason_codes
```

## Delete Cluster

```sh
make k8s-delete
```

## Notes

- HPA manifests require a metrics server to report CPU utilization. Without metrics server, the HPA object can exist but may show unknown metrics.
- `imagePullPolicy: Never` is intentional for kind-loaded local images.
- `host.docker.internal` is intended for Docker Desktop local development.
- TODO Phase 11: Add ingress manifests after local routing requirements are finalized.
- TODO Phase 12: Add Kubernetes smoke tests and CI validation.
