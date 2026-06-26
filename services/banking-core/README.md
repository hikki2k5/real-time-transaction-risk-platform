# banking-core

Spring Boot service that accepts transaction requests, validates them, generates server-side identifiers, publishes accepted transaction events to Kafka, and calls `fraud-decision-api` for an online fraud decision.

## Endpoints

- `GET /health`
- `POST /internal/transactions`

## Configuration

Use environment variables:

```text
BANKING_CORE_PORT=8084
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
TRANSACTION_EVENTS_TOPIC=transaction_events
FRAUD_API_BASE_URL=http://localhost:8000
```

## Local Commands

Run tests from this directory:

```powershell
.\gradlew.cmd test
```

Run the service after Kafka is available. For online decisions, also run `fraud-decision-api`; if it is unavailable, banking-core returns a safe `REVIEW` fallback.

```powershell
.\gradlew.cmd run
```

## Example Request

```sh
curl -X POST http://localhost:8084/internal/transactions \
  -H "Content-Type: application/json" \
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

## TODO

- TODO Phase 3: Wire service into local Docker Compose after the app service boundary is ready.
- TODO Phase 3: Add contract tests once data contracts are finalized.
- TODO Phase 9: Tune fraud API timeout and retry policy after local end-to-end testing.
- TODO Future: Add authentication and authorization.
