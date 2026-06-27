-- TODO Phase 4: Add transformation lineage columns when cleaned transaction jobs are implemented.

CREATE TABLE IF NOT EXISTS core.cleaned_transactions (
    event_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    merchant_category TEXT,
    transaction_type TEXT,
    channel TEXT,
    country TEXT,
    city TEXT,
    status TEXT,
    event_timestamp TIMESTAMPTZ NOT NULL,
    ingestion_timestamp TIMESTAMPTZ,
    processed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cleaned_transactions_user_time
    ON core.cleaned_transactions (user_id, event_timestamp);

CREATE INDEX IF NOT EXISTS idx_cleaned_transactions_transaction_id
    ON core.cleaned_transactions (transaction_id);

-- Backend audit tables used by banking-core for local transaction request tracing.
CREATE TABLE IF NOT EXISTS core.transaction_requests (
    transaction_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    amount NUMERIC(18, 2) NOT NULL,
    currency CHAR(3) NOT NULL,
    transaction_type TEXT NOT NULL,
    channel TEXT NOT NULL,
    decision TEXT NOT NULL,
    fraud_probability NUMERIC(8, 6) NOT NULL,
    risk_level TEXT NOT NULL,
    request_payload JSONB NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transaction_requests_user_created_at
    ON core.transaction_requests (user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS core.transaction_audit_logs (
    audit_id BIGSERIAL PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    action TEXT NOT NULL,
    detail JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transaction_audit_logs_transaction_id
    ON core.transaction_audit_logs (transaction_id, created_at DESC);

CREATE TABLE IF NOT EXISTS core.accounts (
    account_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('ACTIVE', 'FROZEN', 'CLOSED')),
    currency CHAR(3) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_accounts_user_id
    ON core.accounts (user_id);

CREATE TABLE IF NOT EXISTS core.idempotency_keys (
    idempotency_key TEXT PRIMARY KEY,
    request_hash TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    response_payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_idempotency_keys_transaction_id
    ON core.idempotency_keys (transaction_id);

CREATE TABLE IF NOT EXISTS core.transaction_outbox (
    outbox_id TEXT PRIMARY KEY,
    aggregate_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_payload JSONB NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('PENDING', 'PUBLISHED', 'FAILED')),
    publish_attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_transaction_outbox_status_created_at
    ON core.transaction_outbox (status, created_at);
