from __future__ import annotations

import uuid
from typing import Any

import psycopg2
from psycopg2.extras import Json, RealDictCursor

from app.cache import FeatureCache
from app.config import Settings


CREATE_PREDICTION_LOGS_SQL = """
CREATE SCHEMA IF NOT EXISTS mlops;

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
"""


class PredictionRepository:
    def __init__(self, settings: Settings, feature_cache: FeatureCache | None = None):
        self.settings = settings
        self.feature_cache = feature_cache or FeatureCache(settings)

    def _connect(self) -> Any:
        return psycopg2.connect(
            host=self.settings.postgres_host,
            port=self.settings.postgres_port,
            dbname=self.settings.postgres_db,
            user=self.settings.postgres_user,
            password=self.settings.postgres_password,
        )

    def get_customer_features(self, user_id: str) -> dict[str, Any] | None:
        cached_features = self.feature_cache.get(user_id)
        if cached_features is not None:
            return cached_features

        query = """
            SELECT
                tx_count_5min,
                tx_count_1h,
                tx_count_24h,
                spend_24h,
                avg_amount_7d,
                max_amount_7d,
                amount_stddev_7d,
                declined_tx_count_24h,
                overseas_tx_count_30d,
                unique_merchant_count_7d,
                cash_withdrawal_ratio_30d,
                last_transaction_at,
                feature_snapshot_at
            FROM features.customer_transaction_features
            WHERE user_id = %s
        """
        with self._connect() as connection:
            with connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (user_id,))
                row = cursor.fetchone()
        features = dict(row) if row else None
        if features is not None:
            self.feature_cache.set(user_id, features)
        return features

    def log_prediction(
        self,
        transaction_id: str,
        user_id: str,
        fraud_probability: float,
        risk_level: str,
        decision: str,
        model_name: str,
        model_version: str,
        feature_payload: dict[str, Any],
        reason_codes: list[str],
        latency_ms: int,
    ) -> None:
        query = """
            INSERT INTO mlops.prediction_logs (
                prediction_id,
                transaction_id,
                user_id,
                fraud_probability,
                risk_level,
                decision,
                model_name,
                model_version,
                feature_payload,
                reason_codes,
                latency_ms
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            str(uuid.uuid4()),
            transaction_id,
            user_id,
            fraud_probability,
            risk_level,
            decision,
            model_name,
            model_version,
            Json(feature_payload),
            Json(reason_codes),
            latency_ms,
        )
        with self._connect() as connection:
            with connection.cursor() as cursor:
                cursor.execute(CREATE_PREDICTION_LOGS_SQL)
                cursor.execute(query, values)
