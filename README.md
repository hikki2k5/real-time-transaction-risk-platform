# Real-time Transaction Fraud Detection Platform

Free local-first banking-style fraud detection platform for demonstrating backend engineering, data engineering, MLOps, and serverless fundamentals.

This project simulates a transaction risk workflow end to end: a Spring Boot banking API receives transactions, calls a FastAPI fraud scoring service, publishes events to Kafka, streams data into a local data lake, loads curated data into Postgres, builds feature tables, trains fraud models, logs experiments to MLflow, and records prediction decisions. It also includes a RAG-style fraud investigation assistant with tool calls, prompt versioning, safety checks, and evals, plus a small AWS SAM/Lambda serverless prototype for fraud audit events.

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
  -> RAG/tool-calling fraud investigation assistant
```

Local Docker Compose runs the development infrastructure. The public demo deploys the frontend and API services only; stateful streaming and orchestration services remain local.

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
| AI Assistant | FastAPI, Gemini, LangGraph, PostgreSQL/pgvector retrieval, prompt evals |
| Dev Infra | Docker Compose, Makefile, Render/Vercel demo deployment |
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

### AI Assistant Flow

```text
User question -> safety checks -> RAG retrieval -> transaction audit tools -> cited answer -> trace log
```

- `services/ai-assistant` exposes a FastAPI assistant for fraud investigation questions.
- Knowledge files are chunked and retrieved with citations for fraud policy, Redis cache behavior, AWS audit ingestion, and production safety.
- Agent-style tools can query Postgres transaction audit records by `transaction_id` or recent transactions by `user_id`.
- Prompts are versioned in `prompts/fraud_investigation_v1.md` and treated like code.
- Safety checks block prompt-injection/secret requests and redact common PII patterns.
- Each query writes an observability trace with prompt version, model name, latency, token estimates, estimated cost, retrieved document IDs, tool calls, and guardrail flags.
- Offline deterministic answers keep the portfolio demo free; the same interface can be swapped to GPT, Claude, Gemini, Llama, or Qwen later.

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
services/ai-assistant/         RAG and tool-calling fraud investigation assistant
services/dashboard/            Next.js customer-facing transaction UI
pipelines/spark-streaming/     Kafka to local data lake streaming job
pipelines/airflow/dags/        Airflow orchestration DAGs
pipelines/postgres/            Warehouse DDL and SQL transforms
pipelines/training/            Fraud model training pipeline
infra/docker-compose.yml       Local infrastructure
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
| ai-assistant | http://localhost:8010 |
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

Run the AI assistant:

```sh
cd services/ai-assistant
py -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Ask an investigation question:

```sh
curl -X POST http://localhost:8010/v1/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Why would a transaction be marked REVIEW?"}'
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

## Measurable Optimization Checks

These checks are useful for portfolio screenshots and CV numbers. They measure behavior in the local demo instead of claiming production scale.

Quick local summary:

```sh
make measure-optimizations
```

The script also prints approximate local latency deltas for Redis cache reuse and idempotent retries. Treat these as local demo measurements, not production benchmarks.

Run a small 50-request local throughput check for transaction submission:

```sh
make benchmark-tps
```

### 1. Fraud Feature Cache

`fraud-decision-api` records Redis feature-cache hits, misses, and Postgres feature lookups. Run the same fraud-score request twice for the same `user_id`, then check metrics:

```sh
curl http://localhost:8000/metrics | grep fraud_feature
```

Expected metric names:

```text
fraud_feature_cache_events_total{result="hit"}
fraud_feature_cache_events_total{result="miss"}
fraud_feature_db_lookups_total
```

How to describe it honestly: "Instrumented Redis cache hit/miss metrics for online customer feature lookup to measure avoided Postgres reads during repeated fraud scoring."

### 2. Banking Idempotency

`banking-core` records idempotency outcomes for client retries:

```sh
curl http://localhost:8084/actuator/metrics/banking.idempotency.requests
```

Send the same transaction twice with the same `Idempotency-Key` to increase `result=hit`. Send a different payload with the same key to increase `result=conflict`.

How to describe it honestly: "Added idempotency metrics to track accepted new keys, safe retry hits, and duplicate-key conflicts for transaction submission."

### 3. Lake-to-Warehouse Rows

After the Airflow DAG `local_lake_to_postgres_transactions` runs, check the generated local report:

```sh
cat data-lake/metrics/lake_to_postgres_transactions/latest.json
```

The report includes source file count, raw rows loaded, load duration, core table row count, and transform duration. Use it to quote measured local demo numbers such as rows loaded per DAG run.

How to describe it honestly: "Added a pipeline run report that records source files, raw rows loaded, cleaned warehouse rows, and local processing duration after each lake-to-Postgres DAG run."

## AI Assistant Evals

The fraud investigation assistant includes a small regression eval set for portfolio-friendly AI engineering practice:

```sh
make ai-assistant-test
make ai-assistant-eval
```

The eval reports:

- retrieval hit rate for expected knowledge documents.
- answer term pass rate for required explanation terms.
- tool-call accuracy for transaction audit lookups.
- prompt-injection block rate.
- PII redaction pass rate.

The assistant has an offline baseline and a Gemini mode using PostgreSQL/pgvector
for document embeddings and LangGraph for tool calls. See
[the service README](services/ai-assistant/README.md) for vector schema migration,
private environment setup, operator authentication and live evaluation. Unit tests
do not prove live Gemini quality; report live metrics only after running them.

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

## Cloud Readiness

The current implementation is intentionally local-first. `docs/CLOUD_READINESS.md` describes how the same architecture could map to ECS or Azure Container Apps, RDS Postgres, S3, Secrets Manager, managed Kafka, cloud monitoring, and FaaS in a future cloud version.

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

GitHub Actions CI runs unit tests and Docker image builds. It does not push images, start Docker Compose, or require AWS/Snowflake credentials.

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

## Known Limitations

- Fraud labels are synthetic for local workflow testing.
- Model metrics are smoke-test signals, not production accuracy claims.
- JWT support exists for `banking-core`, and `auth-service` can issue local demo tokens.
- Full enterprise OAuth2/OIDC, role-based authorization, and managed secrets are not implemented yet.
- The local outbox records publish state but is not a full production-grade asynchronous relay with guaranteed broker acknowledgement.
- Kafka, Spark, Airflow, Postgres, and MLflow are local development services only.
- Redis is used as a local online feature cache, but it is not a full feature store with offline/online consistency guarantees.
- Data contracts are early-stage and should be treated carefully before extension.

## Future Improvements

- Cloud data lake with S3.
- Cloud warehouse with Snowflake.
- dbt models and tests for warehouse transforms.
- Expand Redis into a proper online feature store with offline/online consistency checks.
- Evidently drift monitoring and model quality reports.
- Terraform for reproducible infrastructure.
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

### AI Engineer

- Built an offline-first fraud investigation assistant with RAG retrieval, cited answers, transaction audit tool calls, prompt versioning, and FastAPI serving.
- Added lightweight AI evals covering retrieval hit rate, answer quality terms, tool-call accuracy, prompt-injection blocking, and PII redaction.
- Logged assistant traces with prompt version, model name, latency, token estimates, estimated cost, retrieved document IDs, tool calls, and guardrail flags.

### Backend Engineer

- Implemented a Spring Boot transaction ingestion API with request validation, customer account listing, transaction history, Kafka event publishing, and fraud decision integration.
- Added backend reliability patterns including idempotency keys, account status validation, local outbox tracking, fraud API timeouts, retry, circuit breaker, correlation IDs, structured errors, JWT support, and Postgres audit persistence.
- Built a separate Spring Boot auth-service with register/login/me endpoints, BCrypt password hashing, and JWT access token issuance for local protected-route demos.
- Built a FastAPI fraud decision service with health, model info, scoring, metrics, Postgres feature lookup, and decision rules.
