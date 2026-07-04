# Real-time Transaction Fraud Detection Platform

Free local-first banking-style fraud detection platform for demonstrating data engineering, MLOps, backend, and local Kubernetes skills.

This project simulates a transaction risk workflow end to end: a Spring Boot banking API receives transactions, calls a FastAPI fraud scoring service, publishes events to Kafka, streams data into a local data lake, loads curated data into Postgres, builds feature tables, trains fraud models, logs experiments to MLflow, and records prediction decisions. It also includes a small AWS SAM/Lambda serverless prototype for fraud audit events that can be tested locally without deploying cloud resources.

It is a portfolio and learning project, not a production-ready banking system.

## Architecture Summary

```text
Spring Boot banking-core
  -> Spring Boot auth-service for local JWT issuance
  -> FastAPI fraud-decision-api
  -> Kafka transaction_events
  -> Spark Structured Streaming
  -> local data lake
  -> Airflow
  -> Postgres warehouse
  -> feature tables
  -> Python training
  -> MLflow
  -> Redis online feature cache
  -> FastAPI model serving
  -> Postgres prediction logs
```

Local Docker Compose runs the stateful development infrastructure. Local kind/Kubernetes deploys only the stateless app services: `banking-core` and `fraud-decision-api`.

## Backend Engineering Highlights

The main backend service is `services/banking-core`, a Java Spring Boot microservice designed around banking-style transaction ingestion. A separate `services/auth-service` Spring Boot service provides local register/login/JWT issuance for demo purposes.

- REST API with validation, versioned routes, structured error responses, and OpenAPI docs.
- Fraud decision integration with timeout, retry, circuit breaker, and safe `REVIEW` fallback behavior.
- Kafka event publishing for accepted transaction events.
- Best-effort Postgres audit persistence for transaction requests and responses.
- Account status validation for banking-style transaction controls.
- Optional `Idempotency-Key` handling to avoid duplicate transaction creation on client retries.
- Local transactional outbox table for Kafka event publication tracking.
- Correlation ID propagation through `X-Correlation-Id`.
- Optional JWT resource-server security for protected endpoints.
- Local auth-service with register/login/me, BCrypt password hashing, and JWT access tokens.
- Actuator health/metrics endpoints for local operations.

## Tech Stack

| Area | Tools |
| --- | --- |
| Backend | Java 21, Spring Boot, FastAPI, Python |
| Streaming | Kafka, Spark Structured Streaming |
| Orchestration | Airflow |
| Storage | Local filesystem data lake, Postgres warehouse |
| Cache | Redis online feature cache |
| ML/MLOps | LightGBM, XGBoost, scikit-learn metrics, MLflow |
| Dev Infra | Docker Compose, kind, Kubernetes, Makefile |
| Serverless Prototype | AWS Lambda style handler, AWS SAM template |
| Testing/CI | JUnit, pytest, unittest, GitHub Actions |

## Local-first Design

This repository is designed to run for free on a local machine:

- No required AWS deployment.
- No Snowflake.
- No MinIO.
- No paid cloud services.
- Secrets and local credentials belong in `.env`, never in Git.

AWS serverless files under `infra/aws/` are local prototypes only. They do not create cloud resources unless explicitly deployed.

## Main Flows

### Data Engineering Flow

```text
Kafka -> Spark -> local data lake -> Postgres warehouse -> Airflow -> feature tables
```

- `banking-core` publishes accepted transaction events to Kafka topic `transaction_events`.
- Spark reads Kafka events and writes bronze raw JSON, silver cleaned Parquet, and quarantine records with `error_reason`.
- Airflow loads silver data into `raw.transactions_raw` and transforms it into `core.cleaned_transactions`.
- A feature DAG builds `features.customer_transaction_features` with time-windowed customer behavior features.

### MLE Flow

```text
Postgres features -> training -> MLflow -> FastAPI serving -> prediction logs
```

- Training reads `core.cleaned_transactions` and `features.customer_transaction_features`.
- Synthetic fraud labels are generated for local testing if no labels exist.
- LightGBM and XGBoost candidates are trained and evaluated with ROC-AUC, PR-AUC, precision, recall, F1, and confusion matrix.
- Experiments and model artifacts are logged to local MLflow.
- `fraud-decision-api` loads the latest MLflow model or a local fallback artifact and writes decisions to `mlops.prediction_logs`.
- Redis caches online customer feature lookups by `user_id` to avoid hitting Postgres for repeated scoring requests.

### Backend Flow

```text
Spring Boot transaction API -> fraud-decision-api -> Kafka event
```

- `POST /internal/transactions` validates transaction requests.
- `banking-core` checks account status when an account record exists locally.
- `Idempotency-Key` lets clients safely retry transaction requests without creating duplicate responses.
- `banking-core` calls `fraud-decision-api` before returning a response.
- If the fraud API fails or times out, the transaction is still accepted with a safe fallback decision of `REVIEW`.
- The transaction event is recorded in `core.transaction_outbox` and then published to Kafka.
- Accepted transaction requests are written to local Postgres audit tables when Postgres is available.

## Repository Layout

```text
docs/                         Design notes and agent rules
services/banking-core/         Spring Boot transaction ingestion service
services/auth-service/         Spring Boot local auth and JWT issuer
services/fraud-decision-api/   FastAPI fraud scoring service
services/dashboard/            Next.js customer-facing transaction UI
pipelines/spark-streaming/     Kafka to local data lake streaming job
pipelines/airflow/dags/        Airflow orchestration DAGs
pipelines/postgres/            Warehouse DDL and SQL transforms
pipelines/training/            Fraud model training pipeline
infra/docker-compose.yml       Local infrastructure
infra/k8s/                     kind/Kubernetes manifests
infra/aws/                     Local AWS SAM/Lambda serverless prototype
data-lake/                     Local bronze/silver/quarantine/features/labels folders
tests/e2e/                     Local end-to-end demo script
```

## Run Locally

Create local environment config:

```sh
cp .env.example .env
```

Start local infrastructure:

```sh
make up
```

Useful service URLs:

| Service | URL |
| --- | --- |
| Kafka UI | http://localhost:8080 |
| Spark master UI | http://localhost:8081 |
| Spark worker UI | http://localhost:8082 |
| Airflow UI | http://localhost:8083 |
| MLflow UI | http://localhost:5000 |
| Postgres | `localhost:55432` |
| Redis | `localhost:6379` |
| auth-service | http://localhost:8085 |
| banking-core | http://localhost:8084 |
| fraud-decision-api | http://localhost:8000 |
| dashboard | http://localhost:3000 |

Stop local infrastructure:

```sh
make down
```

## Run The App Services

Run `banking-core` locally:

```sh
cd services/banking-core
gradle test --no-daemon
gradle bootRun --no-daemon
```

Run `auth-service` locally:

```sh
cd services/auth-service
gradle test --no-daemon
gradle bootRun --no-daemon
```

Run `fraud-decision-api` locally:

```sh
cd services/fraud-decision-api
py -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

FastAPI docs:

```text
http://localhost:8000/docs
```

Run the dashboard:

```sh
cd services/dashboard
cp .env.example .env.local
npm install
npm run dev
```

The dashboard is a Next.js customer-facing UI. Users login/register, select an account, submit normal payment details, see an approved/review/blocked result, and view recent transactions. It is deployable as a normal Next.js app on v0/Vercel, but a deployed frontend needs public backend URLs because it cannot reach local `localhost` services on your laptop.

## Run End-to-End Demo

The local e2e script sends a transaction through `banking-core`, checks the fraud decision response, looks for data lake outputs, and checks Postgres prediction logs.

```sh
make e2e
```

A healthy local run should show no failures. Some checks may warn or skip if Spark, Airflow, or optional Kafka consumer dependencies have not been run yet.

## AWS Serverless Prototype

The repository includes a local AWS SAM/Lambda prototype for fraud audit events:

```text
infra/aws/lambda/fraud-event-auditor
```

It accepts API Gateway, EventBridge, SQS, or direct Lambda-style transaction risk events and returns normalized audit records. It is intentionally side-effect free and does not require AWS credentials.

Run local unit tests:

```sh
make serverless-test
```

Optional local SAM invocation:

```sh
cd infra/aws/lambda/fraud-event-auditor
sam local invoke FraudEventAuditorFunction -e events/api-gateway-transaction.json
```

Do not run `sam deploy` unless you intentionally want to create AWS resources and understand any cost implications.

## Kubernetes Deployment Summary

kind is used only for stateless services:

- `banking-core`
- `auth-service`
- `fraud-decision-api`

Kafka, Spark, Airflow, Postgres, MLflow, and the local data lake stay in Docker Compose.

```sh
make k8s-create
make k8s-build-images
make k8s-load-images
make k8s-deploy
make k8s-status
```

Local kind service ports:

- `banking-core`: http://localhost:18084
- `auth-service`: http://localhost:18085
- `fraud-decision-api`: http://localhost:18080

Delete the cluster:

```sh
make k8s-delete
```

See `docs/KUBERNETES_DEPLOYMENT.md` for secret placeholders and smoke-test commands.

## Cloud Readiness

The current implementation is intentionally local-first. `docs/CLOUD_READINESS.md` describes how the same architecture could map to ECS/EKS, RDS Postgres, S3, Secrets Manager, managed Kafka, cloud monitoring, and FaaS in a future cloud version.

## Tests And CI

Local checks:

```sh
make up
make e2e
```

Service tests:

```sh
cd services/banking-core && gradle test --no-daemon
cd services/auth-service && gradle test --no-daemon
cd services/fraud-decision-api && py -m pytest
cd pipelines/training && py -m unittest discover -s tests
cd pipelines/spark-streaming && py -m unittest discover -s tests
```

GitHub Actions CI runs unit tests, Docker image builds, and Kubernetes YAML validation. It does not push images, start Docker Compose, or require AWS/Snowflake credentials.

## Screenshots

Add screenshots here after running the local demo:

| Screenshot | Placeholder |
| --- | --- |
| Kafka UI showing `transaction_events` | TODO: add image |
| Local data lake bronze/silver/quarantine folders | TODO: add image |
| Postgres raw/core/features/mlops tables | TODO: add image |
| Airflow DAG run success | TODO: add image |
| MLflow experiment and registered model | TODO: add image |
| FastAPI Swagger docs | TODO: add image |
| Kubernetes pods in `risk-platform` namespace | TODO: add image |

## Known Limitations

- Fraud labels are synthetic for local workflow testing.
- Model metrics are smoke-test signals, not production accuracy claims.
- JWT support exists for `banking-core`, and `auth-service` can issue local demo tokens.
- Full enterprise OAuth2/OIDC, role-based authorization, and managed secrets are not implemented yet.
- The local outbox records publish state but is not a full production-grade asynchronous relay with guaranteed broker acknowledgement.
- Kafka, Spark, Airflow, Postgres, and MLflow are local development services only.
- Redis is used as a local online feature cache, but it is not a full feature store with offline/online consistency guarantees.
- Kubernetes deployment is local kind only and does not include production ingress, TLS, autoscaling metrics setup, or managed secrets.
- Data contracts are early-stage and should be treated carefully before extension.

## Future Improvements

- Cloud data lake with S3.
- Cloud warehouse with Snowflake.
- dbt models and tests for warehouse transforms.
- Expand Redis into a proper online feature store with offline/online consistency checks.
- Evidently drift monitoring and model quality reports.
- Terraform for reproducible infrastructure.
- EKS deployment for managed Kubernetes.
- OAuth2/Keycloak for service and user authentication.

## CV Bullets

### Data Engineer

- Built a local streaming fraud detection data platform using Kafka, Spark Structured Streaming, Airflow, Postgres, and a bronze/silver/quarantine data lake layout.
- Implemented warehouse DDL, SQL transforms, feature tables, and data quality checks for transaction risk features.
- Designed a local-first orchestration flow that loads cleaned lake data into Postgres and materializes customer transaction features.

### Machine Learning Engineer

- Built a fraud model training pipeline using Postgres feature data, synthetic label generation, LightGBM, XGBoost, MLflow experiment tracking, and local fallback artifacts.
- Evaluated imbalanced fraud models with PR-AUC, ROC-AUC, precision, recall, F1, and confusion matrix metrics.
- Served model predictions through FastAPI with MLflow loading, fallback model support, Prometheus metrics, and prediction logging.

### Backend Engineer

- Implemented a Spring Boot transaction ingestion API with request validation, customer account listing, transaction history, Kafka event publishing, and fraud decision integration.
- Added backend reliability patterns including idempotency keys, account status validation, local outbox tracking, fraud API timeouts, retry, circuit breaker, correlation IDs, structured errors, JWT support, and Postgres audit persistence.
- Built a separate Spring Boot auth-service with register/login/me endpoints, BCrypt password hashing, and JWT access token issuance for local protected-route demos.
- Built a FastAPI fraud decision service with health, model info, scoring, metrics, Postgres feature lookup, and decision rules.
- Added local Docker and kind/Kubernetes deployment paths for stateless services with config maps, secret placeholders, probes, and resource limits.
