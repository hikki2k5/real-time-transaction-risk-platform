# RAG And Agent Design

The fraud investigation assistant uses retrieval over project knowledge and
tool calls over backend audit data.

Retrieval context includes architecture notes, fraud review policy, serverless
audit ingestion behavior, Redis cache behavior, and data pipeline definitions.
The assistant should cite retrieved chunks and avoid answering from memory when
evidence is unavailable.

Transaction-specific questions should call `get_transaction_audit` with a
transaction id. User history questions should call `get_recent_transactions`
with a user id. Tool results are treated as higher-priority evidence than
general documentation.

Prompts are versioned in source control and evaluated like code. Prompt or model
changes should run regression evals before release.
