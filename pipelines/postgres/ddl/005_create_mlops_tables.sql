-- TODO Phase 6: Add model registry linkage once serving and promotion workflows exist.

CREATE TABLE IF NOT EXISTS mlops.prediction_logs (
    prediction_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    fraud_probability NUMERIC(8, 7) NOT NULL,
    risk_level TEXT NOT NULL,
    decision TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    feature_payload JSONB,
    reason_codes JSONB,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_transaction_id
    ON mlops.prediction_logs (transaction_id);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_user_created_at
    ON mlops.prediction_logs (user_id, created_at);

