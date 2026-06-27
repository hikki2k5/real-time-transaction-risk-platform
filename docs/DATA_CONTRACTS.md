# Data Contracts

Data contracts are early-stage local contracts. They are stable enough for the current local demo, but should not be treated as production banking contracts.

## Contract Areas

- Transaction request contract for `banking-core`.
- Kafka transaction event contract.
- Local data lake bronze transaction layout.
- Local data lake silver transaction layout.
- Postgres fraud feature tables.
- Fraud prediction request and response contract.
- Backend transaction audit records.
- Account records, idempotency keys, and transaction outbox records.
- Local auth users and refresh token records.

## Change Control

Do not change data contracts unless explicitly asked. Contract changes must include tests and documentation updates.

## TODO

- TODO Future: Add formal JSON Schema or OpenAPI contract files.
- TODO Future: Add consumer-driven contract tests across services.
