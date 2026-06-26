from __future__ import annotations

from typing import Any


def run_feature_table_checks(connection: Any) -> list[str]:
    checks = [
        (
            "features.customer_transaction_features must have one row per user_id",
            """
            SELECT COUNT(*)
            FROM (
                SELECT user_id
                FROM features.customer_transaction_features
                GROUP BY user_id
                HAVING COUNT(*) > 1
            ) duplicate_users
            """,
        ),
        (
            "features.customer_transaction_features must not have negative counts",
            """
            SELECT COUNT(*)
            FROM features.customer_transaction_features
            WHERE tx_count_5min < 0
               OR tx_count_1h < 0
               OR tx_count_24h < 0
               OR declined_tx_count_24h < 0
               OR overseas_tx_count_30d < 0
               OR unique_merchant_count_7d < 0
            """,
        ),
        (
            "features.customer_transaction_features feature_snapshot_at must not be null",
            """
            SELECT COUNT(*)
            FROM features.customer_transaction_features
            WHERE feature_snapshot_at IS NULL
            """,
        ),
        (
            "features.customer_transaction_features tx_count_24h must be >= tx_count_1h",
            """
            SELECT COUNT(*)
            FROM features.customer_transaction_features
            WHERE tx_count_24h < tx_count_1h
            """,
        ),
        (
            "features.customer_transaction_features tx_count_1h must be >= tx_count_5min",
            """
            SELECT COUNT(*)
            FROM features.customer_transaction_features
            WHERE tx_count_1h < tx_count_5min
            """,
        ),
    ]

    failures: list[str] = []
    with connection.cursor() as cursor:
        for message, sql in checks:
            cursor.execute(sql)
            failure_count = cursor.fetchone()[0]
            if failure_count:
                failures.append(f"{message}: {failure_count} failing rows")

    return failures


def assert_feature_table_quality(connection: Any) -> None:
    failures = run_feature_table_checks(connection)
    if failures:
        raise AssertionError("; ".join(failures))

