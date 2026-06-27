# banking-core

Spring Boot banking-style transaction ingestion service.

This service is the main backend entry point of the local fraud detection platform. It validates transaction requests, generates server-side identifiers, calls `fraud-decision-api` for an online risk decision, publishes accepted transaction events to Kafka, and writes best-effort transaction audit records to Postgres.

## Backend Features

- Java 21 and Spring Boot 3.
- REST API with request validation and structured error responses.
- Versioned endpoint support under `/v1/internal/transactions`.
- Backward-compatible endpoint under `/internal/transactions`.
- Kafka event publishing to `transaction_events`.
- Account status validation using local Postgres account records when available.
- Optional `Idempotency-Key` support for safe client retries.
- Local transaction outbox persistence before Kafka publish attempts.
- Fraud API integration with timeout, retry, circuit breaker, and safe `REVIEW` fallback.
- Correlation ID support through `X-Correlation-Id` response/request header.
- Optional JWT resource-server security for protected endpoints.
- Best-effort Postgres audit persistence for accepted transaction requests.
- OpenAPI/Swagger UI through Springdoc.
- Actuator health/metrics endpoints.

## Endpoints

- `GET /health`
- `GET /v1/accounts`
- `GET /v1/transactions?limit=10`
- `POST /v1/internal/transactions`
- `GET /v1/internal/transactions/{transaction_id}`
- `GET /v1/accounts/{account_id}`
- `POST /internal/transactions` legacy-compatible route
- `GET /swagger-ui.html`
- `GET /actuator/health`

## Configuration

Use environment variables:

```text
BANKING_CORE_PORT=8084
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
TRANSACTION_EVENTS_TOPIC=transaction_events
FRAUD_API_BASE_URL=http://localhost:8000
FRAUD_API_CONNECT_TIMEOUT_MS=1000
FRAUD_API_READ_TIMEOUT_MS=1500
POSTGRES_HOST=localhost
POSTGRES_PORT=55432
POSTGRES_DB=transaction_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=risk_password
BANKING_CORE_SECURITY_ENABLED=false
BANKING_CORE_JWT_SECRET=local-dev-jwt-secret-change-me-32chars
```

JWT is disabled by default for local demos. Enable it with:

```text
BANKING_CORE_SECURITY_ENABLED=true
```

When enabled, protected endpoints require an `Authorization: Bearer <jwt>` header signed with the configured HMAC secret. Production usage should replace this local HMAC setup with an OAuth2/OIDC identity provider.

For local demos, `services/auth-service` can issue compatible JWTs when both services use the same `BANKING_CORE_JWT_SECRET`.

When JWT security is enabled, transaction submission uses the authenticated JWT subject as the effective `user_id`. The frontend still sends a legacy-compatible request body, but `banking-core` does not trust the browser-provided user id when a JWT is present.

## Local Commands

Run tests from this directory:

```powershell
gradle test --no-daemon
```

If Gradle cache or build files are locked on Windows, use temporary locations:

```powershell
$env:GRADLE_USER_HOME="$env:TEMP\banking-core-gradle-home"
$env:BANKING_CORE_BUILD_DIR="$env:TEMP\banking-core-build"
gradle test --no-daemon
```

Run the service after Kafka is available. For online decisions, also run `fraud-decision-api`; if it is unavailable, banking-core returns a safe `REVIEW` fallback.

```powershell
gradle bootRun --no-daemon
```

## Example Request

```sh
curl -X POST http://localhost:8084/v1/internal/transactions \
  -H "Content-Type: application/json" \
  -H "X-Correlation-Id: demo-correlation-001" \
  -H "Idempotency-Key: demo-transaction-001" \
  -d '{
    "user_id": "user-123",
    "account_id": "acct-456",
    "amount": 42.50,
    "currency": "AUD",
    "merchant_category": "GROCERY",
    "transaction_type": "CARD_PAYMENT",
    "channel": "MOBILE",
    "country": "AU",
    "city": "Sydney",
    "status": "PENDING",
    "event_timestamp": "2026-06-23T10:15:30Z"
  }'
```

Example response:

```json
{
  "transaction_id": "generated-transaction-id",
  "event_id": "generated-event-id",
  "status": "ACCEPTED",
  "decision": "APPROVE",
  "fraud_probability": 0.12,
  "risk_level": "LOW",
  "reason_codes": ["LOW_MODEL_SCORE"]
}
```

## Audit Tables

`banking-core` writes to these Postgres tables when available:

- `core.accounts`
- `core.idempotency_keys`
- `core.transaction_requests`
- `core.transaction_audit_logs`
- `core.transaction_outbox`

Audit, idempotency, account lookup, and outbox persistence are local development patterns. If Postgres is unavailable, account/idempotency checks are skipped and transaction ingestion can still continue for the local demo.

`GET /v1/accounts` returns local accounts for the authenticated user when present. If no local account rows exist, it returns demo active accounts so the customer UI can still be used in a fresh local setup.

`GET /v1/transactions` returns recent accepted transaction audit records for the authenticated user.

## Banking Reliability Notes

- `Idempotency-Key` prevents duplicate transaction responses when a client retries the same request.
- Account records with status `FROZEN` or `CLOSED` are rejected with `409 ACCOUNT_NOT_AVAILABLE`.
- The outbox table records Kafka publication intent and local publish status. A production implementation would normally use an asynchronous relay and broker acknowledgements.

## Notes

- This is a portfolio-grade local backend service, not production banking software.
- Real production usage would need managed secrets, OAuth2/OIDC, TLS, stricter authorization, rate limiting, distributed tracing, and platform-level monitoring.
