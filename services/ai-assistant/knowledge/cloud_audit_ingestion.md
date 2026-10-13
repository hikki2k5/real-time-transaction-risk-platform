# Cloud Audit Ingestion

The AWS serverless audit endpoint receives transaction-risk events through API
Gateway, invokes Lambda, validates required fields, normalizes audit records,
and stores JSON audit records in S3 under a date-partitioned prefix.

Required event fields are `event_id`, `transaction_id`, `user_id`, and
`fraud_probability`. The endpoint also returns Kafka-ready stream payloads so
the same event can later feed streaming ingestion.

The EC2 demo hosts long-running services behind Caddy HTTPS routing, while the
Lambda path is separate serverless ingestion. Lambda requests do not route
through EC2 or Caddy.
