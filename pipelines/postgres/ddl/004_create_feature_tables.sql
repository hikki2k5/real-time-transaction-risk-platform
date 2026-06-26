-- TODO Phase 4: Rebuild feature definitions once data contracts and windows are finalized.

CREATE TABLE IF NOT EXISTS features.customer_transaction_features (
    user_id TEXT PRIMARY KEY,
    tx_count_5min INTEGER NOT NULL DEFAULT 0,
    tx_count_1h INTEGER NOT NULL DEFAULT 0,
    tx_count_24h INTEGER NOT NULL DEFAULT 0,
    spend_24h NUMERIC(18, 2) NOT NULL DEFAULT 0,
    avg_amount_7d NUMERIC(18, 2),
    max_amount_7d NUMERIC(18, 2),
    amount_stddev_7d NUMERIC(18, 6),
    declined_tx_count_24h INTEGER NOT NULL DEFAULT 0,
    overseas_tx_count_30d INTEGER NOT NULL DEFAULT 0,
    unique_merchant_count_7d INTEGER NOT NULL DEFAULT 0,
    cash_withdrawal_ratio_30d NUMERIC(8, 6),
    last_transaction_at TIMESTAMPTZ,
    feature_snapshot_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customer_transaction_features_snapshot
    ON features.customer_transaction_features (feature_snapshot_at);

