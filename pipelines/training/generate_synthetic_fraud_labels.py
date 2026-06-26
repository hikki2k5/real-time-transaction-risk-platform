from __future__ import annotations

from feature_builder import connect_postgres


CREATE_LABEL_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS core.fraud_labels (
    event_id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    is_fraud INTEGER NOT NULL,
    label_source TEXT NOT NULL DEFAULT 'synthetic',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""

INSERT_SYNTHETIC_LABELS_SQL = """
INSERT INTO core.fraud_labels (
    event_id,
    transaction_id,
    user_id,
    is_fraud,
    label_source
)
SELECT
    t.event_id,
    t.transaction_id,
    t.user_id,
    CASE
        WHEN t.amount >= 1000 THEN 1
        WHEN UPPER(COALESCE(t.status, '')) IN ('DECLINED', 'FAILED', 'REJECTED') THEN 1
        WHEN UPPER(COALESCE(t.country, '')) NOT IN ('AU', 'AUS', 'AUSTRALIA') THEN 1
        WHEN random() < 0.03 THEN 1
        ELSE 0
    END AS is_fraud,
    'synthetic' AS label_source
FROM core.cleaned_transactions t
ON CONFLICT (event_id) DO NOTHING;
"""

ENSURE_POSITIVE_LABEL_SQL = """
WITH label_stats AS (
    SELECT COUNT(*) AS total_labels,
           SUM(CASE WHEN is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_labels
    FROM core.fraud_labels
),
candidate AS (
    SELECT event_id
    FROM core.fraud_labels
    ORDER BY event_id DESC
    LIMIT 1
)
UPDATE core.fraud_labels
SET is_fraud = 1
FROM label_stats, candidate
WHERE core.fraud_labels.event_id = candidate.event_id
  AND label_stats.total_labels > 0
  AND label_stats.fraud_labels = 0;
"""

ENSURE_NEGATIVE_LABEL_SQL = """
WITH label_stats AS (
    SELECT COUNT(*) AS total_labels,
           SUM(CASE WHEN is_fraud = 0 THEN 1 ELSE 0 END) AS non_fraud_labels
    FROM core.fraud_labels
),
candidate AS (
    SELECT event_id
    FROM core.fraud_labels
    ORDER BY event_id ASC
    LIMIT 1
)
UPDATE core.fraud_labels
SET is_fraud = 0
FROM label_stats, candidate
WHERE core.fraud_labels.event_id = candidate.event_id
  AND label_stats.total_labels > 1
  AND label_stats.non_fraud_labels = 0;
"""


def ensure_synthetic_fraud_labels() -> int:
    with connect_postgres() as connection:
        with connection.cursor() as cursor:
            cursor.execute(CREATE_LABEL_TABLE_SQL)
            cursor.execute("SELECT COUNT(*) FROM core.fraud_labels")
            existing_count = cursor.fetchone()[0]

            if existing_count == 0:
                cursor.execute(INSERT_SYNTHETIC_LABELS_SQL)
            else:
                cursor.execute(INSERT_SYNTHETIC_LABELS_SQL)

            cursor.execute(ENSURE_POSITIVE_LABEL_SQL)
            cursor.execute(ENSURE_NEGATIVE_LABEL_SQL)
            cursor.execute("SELECT COUNT(*) FROM core.fraud_labels")
            label_count = cursor.fetchone()[0]

    return label_count


if __name__ == "__main__":
    labels = ensure_synthetic_fraud_labels()
    print(f"fraud label rows: {labels}")
