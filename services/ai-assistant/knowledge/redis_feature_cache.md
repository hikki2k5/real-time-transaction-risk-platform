# Redis Feature Cache

The fraud-decision API reads customer transaction features from PostgreSQL and
caches them in Redis by user id. Repeated fraud scoring for the same user can
reuse cached feature rows and avoid repeated PostgreSQL lookups.

The project exposes Prometheus counters for feature cache hits, misses, and
database lookups:

- `fraud_feature_cache_events_total{result="hit"}`
- `fraud_feature_cache_events_total{result="miss"}`
- `fraud_feature_db_lookups_total`

In EC2 testing, repeated fraud feature lookup latency dropped from 66.78ms to
27.41ms, a 59.0 percent reduction.
