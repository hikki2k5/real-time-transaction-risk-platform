-- TODO Phase 4: Align raw table loading with Airflow ingestion from the local data lake.

CREATE TABLE IF NOT EXISTS raw.transactions_raw (
    event_id TEXT,
    transaction_id TEXT,
    user_id TEXT,
    account_id TEXT,
    amount NUMERIC(18, 2),
    currency CHAR(3),
    merchant_category TEXT,
    transaction_type TEXT,
    channel TEXT,
    country TEXT,
    city TEXT,
    status TEXT,
    event_timestamp TIMESTAMPTZ,
    ingestion_timestamp TIMESTAMPTZ,
    source_file TEXT,
    loaded_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_raw_event_timestamp
    ON raw.transactions_raw (event_timestamp);

CREATE INDEX IF NOT EXISTS idx_transactions_raw_transaction_id
    ON raw.transactions_raw (transaction_id);

