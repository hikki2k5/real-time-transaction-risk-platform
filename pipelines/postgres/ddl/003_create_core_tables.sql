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

