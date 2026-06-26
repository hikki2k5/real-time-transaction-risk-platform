# Spark Streaming Pipeline

Structured Streaming job that reads `transaction_events` from Kafka and writes transaction data to the local data lake.

## Paths

- Bronze raw JSON: `data-lake/bronze/transactions/year=YYYY/month=MM/day=DD/hour=HH/`
- Silver cleaned Parquet: `data-lake/silver/transactions_cleaned/year=YYYY/month=MM/day=DD/hour=HH/`
- Quarantine JSON: `data-lake/quarantine/bad_transactions/year=YYYY/month=MM/day=DD/`
- Checkpoint: `data-lake/checkpoints/transaction_streaming/`

## Environment

```text
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
DATA_LAKE_ROOT=./data-lake
```

Inside Docker Compose, use:

```text
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
DATA_LAKE_ROOT=/data-lake
```

## Run Locally

Start local infrastructure first:

```sh
make up
```

Run with Spark submit from the Spark container or a local Spark install that includes the Kafka connector.

Example package coordinate for Spark 4:

```sh
spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.13:4.0.3 \
  pipelines/spark-streaming/transaction_streaming_job.py
```

## Tests

Validation tests do not require Spark:

```sh
cd pipelines/spark-streaming
python -m unittest discover -s tests
```

On Windows, use the Python launcher if `python` is not on PATH:

```powershell
py -m unittest discover -s tests
```

## TODO

- TODO Phase 4: Add integration tests with a local Kafka topic and Spark runtime.
- TODO Phase 4: Add schema evolution handling once data contracts are finalized.
- TODO Phase 4: Tune trigger intervals and file sizing for local workloads.
