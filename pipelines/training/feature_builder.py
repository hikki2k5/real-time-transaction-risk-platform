from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import pandas as pd


FEATURE_COLUMNS = [
    "amount",
    "tx_count_5min",
    "tx_count_1h",
    "tx_count_24h",
    "spend_24h",
    "avg_amount_7d",
    "max_amount_7d",
    "amount_stddev_7d",
    "declined_tx_count_24h",
    "overseas_tx_count_30d",
    "unique_merchant_count_7d",
    "cash_withdrawal_ratio_30d",
]

LABEL_COLUMN = "is_fraud"


@dataclass(frozen=True)
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str


def postgres_config_from_env() -> PostgresConfig:
    return PostgresConfig(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ["POSTGRES_PORT"]),
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


def connect_postgres(config: PostgresConfig | None = None) -> Any:
    import psycopg2

    config = config or postgres_config_from_env()
    return psycopg2.connect(
        host=config.host,
        port=config.port,
        dbname=config.database,
        user=config.user,
        password=config.password,
    )


def load_training_dataset(connection: Any) -> pd.DataFrame:
    query = """
        SELECT
            t.event_id,
            t.transaction_id,
            t.user_id,
            t.amount,
            t.currency,
            t.transaction_type,
            t.channel,
            t.country,
            t.status,
            t.event_timestamp,
            f.tx_count_5min,
            f.tx_count_1h,
            f.tx_count_24h,
            f.spend_24h,
            f.avg_amount_7d,
            f.max_amount_7d,
            f.amount_stddev_7d,
            f.declined_tx_count_24h,
            f.overseas_tx_count_30d,
            f.unique_merchant_count_7d,
            f.cash_withdrawal_ratio_30d,
            l.is_fraud
        FROM core.cleaned_transactions t
        JOIN features.customer_transaction_features f
            ON t.user_id = f.user_id
        JOIN core.fraud_labels l
            ON t.event_id = l.event_id
        WHERE l.is_fraud IS NOT NULL
    """
    return pd.read_sql_query(query, connection)


def preprocess_features(dataset: pd.DataFrame) -> tuple[pd.DataFrame, pd.Series]:
    missing = [column for column in FEATURE_COLUMNS + [LABEL_COLUMN] if column not in dataset.columns]
    if missing:
        raise ValueError(f"Training dataset missing columns: {', '.join(missing)}")

    features = dataset[FEATURE_COLUMNS].copy()
    for column in FEATURE_COLUMNS:
        features[column] = pd.to_numeric(features[column], errors="coerce")

    features = features.fillna(0)
    labels = dataset[LABEL_COLUMN].astype(int)
    return features, labels


def time_based_train_test_split(
    dataset: pd.DataFrame,
    test_fraction: float = 0.25,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if dataset.empty:
        raise ValueError("Training dataset is empty")

    if "event_timestamp" in dataset.columns:
        ordered = dataset.sort_values("event_timestamp")
    else:
        ordered = dataset.copy()

    split_index = max(1, int(len(ordered) * (1 - test_fraction)))
    if split_index >= len(ordered):
        split_index = len(ordered) - 1

    train_df = ordered.iloc[:split_index].copy()
    test_df = ordered.iloc[split_index:].copy()
    if train_df.empty or test_df.empty:
        raise ValueError("Training dataset needs at least two rows for train/test split")

    return train_df, test_df

