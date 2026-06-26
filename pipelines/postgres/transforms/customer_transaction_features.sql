-- TODO Phase 6: Revisit feature windows and definitions when fraud labels are available.

WITH latest_user_activity AS (
    SELECT
        user_id,
        MAX(event_timestamp) AS feature_snapshot_at
    FROM core.cleaned_transactions
    GROUP BY user_id
),
feature_values AS (
    SELECT
        t.user_id,
        COUNT(*) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '5 minutes'
        )::INTEGER AS tx_count_5min,
        COUNT(*) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '1 hour'
        )::INTEGER AS tx_count_1h,
        COUNT(*) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '24 hours'
        )::INTEGER AS tx_count_24h,
        COALESCE(SUM(t.amount) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '24 hours'
        ), 0)::NUMERIC(18, 2) AS spend_24h,
        AVG(t.amount) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '7 days'
        )::NUMERIC(18, 2) AS avg_amount_7d,
        MAX(t.amount) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '7 days'
        )::NUMERIC(18, 2) AS max_amount_7d,
        STDDEV_SAMP(t.amount) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '7 days'
        )::NUMERIC(18, 6) AS amount_stddev_7d,
        COUNT(*) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '24 hours'
              AND UPPER(COALESCE(t.status, '')) IN ('DECLINED', 'FAILED', 'REJECTED')
        )::INTEGER AS declined_tx_count_24h,
        COUNT(*) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '30 days'
              AND UPPER(COALESCE(t.country, '')) NOT IN ('AU', 'AUS', 'AUSTRALIA')
        )::INTEGER AS overseas_tx_count_30d,
        COUNT(DISTINCT t.merchant_category) FILTER (
            WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '7 days'
              AND t.merchant_category IS NOT NULL
        )::INTEGER AS unique_merchant_count_7d,
        COALESCE(
            (
                COUNT(*) FILTER (
                    WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '30 days'
                      AND t.transaction_type = 'ATM_WITHDRAWAL'
                )::NUMERIC
                / NULLIF(
                    COUNT(*) FILTER (
                        WHERE t.event_timestamp >= a.feature_snapshot_at - INTERVAL '30 days'
                    )::NUMERIC,
                    0
                )
            ),
            0
        )::NUMERIC(8, 6) AS cash_withdrawal_ratio_30d,
        MAX(t.event_timestamp) AS last_transaction_at,
        a.feature_snapshot_at
    FROM core.cleaned_transactions t
    JOIN latest_user_activity a
        ON t.user_id = a.user_id
    GROUP BY t.user_id, a.feature_snapshot_at
)
INSERT INTO features.customer_transaction_features (
    user_id,
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
)
SELECT
    user_id,
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
FROM feature_values
ON CONFLICT (user_id) DO UPDATE SET
    tx_count_5min = EXCLUDED.tx_count_5min,
    tx_count_1h = EXCLUDED.tx_count_1h,
    tx_count_24h = EXCLUDED.tx_count_24h,
    spend_24h = EXCLUDED.spend_24h,
    avg_amount_7d = EXCLUDED.avg_amount_7d,
    max_amount_7d = EXCLUDED.max_amount_7d,
    amount_stddev_7d = EXCLUDED.amount_stddev_7d,
    declined_tx_count_24h = EXCLUDED.declined_tx_count_24h,
    overseas_tx_count_30d = EXCLUDED.overseas_tx_count_30d,
    unique_merchant_count_7d = EXCLUDED.unique_merchant_count_7d,
    cash_withdrawal_ratio_30d = EXCLUDED.cash_withdrawal_ratio_30d,
    last_transaction_at = EXCLUDED.last_transaction_at,
    feature_snapshot_at = EXCLUDED.feature_snapshot_at;

