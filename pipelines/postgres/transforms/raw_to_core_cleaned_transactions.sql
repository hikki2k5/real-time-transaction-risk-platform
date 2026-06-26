-- TODO Phase 5: Add richer data quality filters once transaction contracts are finalized.

WITH ranked_raw AS (
    SELECT
        event_id,
        transaction_id,
        user_id,
        account_id,
        amount,
        currency,
        merchant_category,
        transaction_type,
        channel,
        country,
        city,
        status,
        event_timestamp,
        ingestion_timestamp,
        loaded_at,
        ROW_NUMBER() OVER (
            PARTITION BY event_id
            ORDER BY loaded_at DESC
        ) AS row_num
    FROM raw.transactions_raw
    WHERE event_id IS NOT NULL
)
INSERT INTO core.cleaned_transactions (
    event_id,
    transaction_id,
    user_id,
    account_id,
    amount,
    currency,
    merchant_category,
    transaction_type,
    channel,
    country,
    city,
    status,
    event_timestamp,
    ingestion_timestamp,
    processed_at
)
SELECT
    event_id,
    transaction_id,
    user_id,
    account_id,
    amount,
    currency,
    merchant_category,
    transaction_type,
    channel,
    country,
    city,
    status,
    event_timestamp,
    ingestion_timestamp,
    CURRENT_TIMESTAMP
FROM ranked_raw
WHERE row_num = 1
ON CONFLICT (event_id) DO UPDATE SET
    transaction_id = EXCLUDED.transaction_id,
    user_id = EXCLUDED.user_id,
    account_id = EXCLUDED.account_id,
    amount = EXCLUDED.amount,
    currency = EXCLUDED.currency,
    merchant_category = EXCLUDED.merchant_category,
    transaction_type = EXCLUDED.transaction_type,
    channel = EXCLUDED.channel,
    country = EXCLUDED.country,
    city = EXCLUDED.city,
    status = EXCLUDED.status,
    event_timestamp = EXCLUDED.event_timestamp,
    ingestion_timestamp = EXCLUDED.ingestion_timestamp,
    processed_at = CURRENT_TIMESTAMP;

