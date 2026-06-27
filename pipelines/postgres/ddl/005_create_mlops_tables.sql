-- TODO Phase 6: Add model registry linkage once serving and promotion workflows exist.

CREATE SCHEMA IF NOT EXISTS security;

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

CREATE TABLE IF NOT EXISTS security.users (
    user_id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    full_name TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS security.refresh_tokens (
    refresh_token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES security.users(user_id),
    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user_id
    ON security.refresh_tokens (user_id);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_transaction_id
    ON mlops.prediction_logs (transaction_id);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_user_created_at
    ON mlops.prediction_logs (user_id, created_at);
