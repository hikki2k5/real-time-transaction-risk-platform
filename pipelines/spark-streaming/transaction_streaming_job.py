"""Spark Structured Streaming job for Kafka transaction events.

Reads JSON events from Kafka, writes raw payloads to the local bronze data lake,
valid cleaned records to silver Parquet, and invalid records to quarantine JSON.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping

ALLOWED_CURRENCIES = {"AUD", "VND", "USD"}
ALLOWED_TRANSACTION_TYPES = {
    "CARD_PAYMENT",
    "ATM_WITHDRAWAL",
    "TRANSFER",
    "LOAN_REPAYMENT",
}
ALLOWED_CHANNELS = {"MOBILE", "WEB", "ATM", "BRANCH"}

REQUIRED_FIELDS = (
    "event_id",
    "transaction_id",
    "user_id",
    "account_id",
    "amount",
    "currency",
    "transaction_type",
    "channel",
    "country",
    "event_timestamp",
)


def parse_json_payload(raw_payload: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        parsed = json.loads(raw_payload)
    except json.JSONDecodeError as exc:
        return None, f"invalid_json: {exc.msg}"

    if not isinstance(parsed, dict):
        return None, "invalid_json: payload must be an object"

    return parsed, None


def validate_transaction_payload(payload: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []

    for field in REQUIRED_FIELDS:
        value = payload.get(field)
        if value is None or (isinstance(value, str) and not value.strip()):
            errors.append(f"{field} is required")

    amount = payload.get("amount")
    if amount is not None:
        try:
            if Decimal(str(amount)) <= 0:
                errors.append("amount must be greater than 0")
        except (InvalidOperation, ValueError):
            errors.append("amount must be numeric")

    currency = payload.get("currency")
    if currency is not None and currency not in ALLOWED_CURRENCIES:
        errors.append("currency must be one of AUD, VND, USD")

    transaction_type = payload.get("transaction_type")
    if transaction_type is not None and transaction_type not in ALLOWED_TRANSACTION_TYPES:
        errors.append(
            "transaction_type must be one of CARD_PAYMENT, ATM_WITHDRAWAL, TRANSFER, LOAN_REPAYMENT"
        )

    channel = payload.get("channel")
    if channel is not None and channel not in ALLOWED_CHANNELS:
        errors.append("channel must be one of MOBILE, WEB, ATM, BRANCH")

    event_timestamp = payload.get("event_timestamp")
    if event_timestamp is not None and str(event_timestamp).strip():
        if not _is_iso_timestamp(str(event_timestamp)):
            errors.append("event_timestamp must be an ISO-8601 timestamp")

    return errors


def error_reason_for_payload(raw_payload: str) -> str | None:
    payload, parse_error = parse_json_payload(raw_payload)
    if parse_error:
        return parse_error

    errors = validate_transaction_payload(payload or {})
    if errors:
        return "; ".join(errors)

    return None


def _is_iso_timestamp(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def main() -> None:
    from pyspark.sql import SparkSession

    kafka_bootstrap_servers = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    data_lake_root = Path(os.getenv("DATA_LAKE_ROOT", "./data-lake")).resolve()

    spark = (
        SparkSession.builder.appName("transaction-streaming-job")
        .config("spark.sql.session.timeZone", "UTC")
        .getOrCreate()
    )

    kafka_stream = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", kafka_bootstrap_servers)
        .option("subscribe", "transaction_events")
        .option("startingOffsets", "latest")
        .load()
    )

    query = (
        kafka_stream.writeStream.foreachBatch(
            lambda batch_df, batch_id: process_batch(batch_df, batch_id, data_lake_root)
        )
        .option("checkpointLocation", str(data_lake_root / "checkpoints" / "transaction_streaming"))
        .start()
    )

    query.awaitTermination()


def process_batch(batch_df: Any, batch_id: int, data_lake_root: Path) -> None:
    from pyspark.sql.functions import col, concat_ws, current_timestamp, date_format, from_json, lit, to_timestamp, when

    raw_df = (
        batch_df.select(
            col("topic").alias("kafka_topic"),
            col("partition").alias("kafka_partition"),
            col("offset").alias("kafka_offset"),
            col("timestamp").alias("kafka_timestamp"),
            col("key").cast("string").alias("kafka_key"),
            col("value").cast("string").alias("raw_payload"),
        )
        .withColumn("processing_timestamp", current_timestamp())
        .withColumn("partition_timestamp", col("kafka_timestamp"))
        .withColumn("year", date_format(col("partition_timestamp"), "yyyy"))
        .withColumn("month", date_format(col("partition_timestamp"), "MM"))
        .withColumn("day", date_format(col("partition_timestamp"), "dd"))
        .withColumn("hour", date_format(col("partition_timestamp"), "HH"))
    )

    bronze_path = data_lake_root / "bronze" / "transactions"
    raw_df.write.mode("append").partitionBy("year", "month", "day", "hour").json(str(bronze_path))

    parsed_df = raw_df.withColumn("parsed", from_json(col("raw_payload"), transaction_schema()))
    flattened_df = parsed_df.select(
        "raw_payload",
        "processing_timestamp",
        col("parsed.event_id").alias("event_id"),
        col("parsed.transaction_id").alias("transaction_id"),
        col("parsed.user_id").alias("user_id"),
        col("parsed.account_id").alias("account_id"),
        col("parsed.amount").alias("amount"),
        col("parsed.currency").alias("currency"),
        col("parsed.merchant_category").alias("merchant_category"),
        col("parsed.transaction_type").alias("transaction_type"),
        col("parsed.channel").alias("channel"),
        col("parsed.country").alias("country"),
        col("parsed.city").alias("city"),
        col("parsed.status").alias("status"),
        col("parsed.event_timestamp").alias("event_timestamp_raw"),
        to_timestamp(col("parsed.event_timestamp")).alias("event_timestamp"),
        to_timestamp(col("parsed.ingestion_timestamp")).alias("ingestion_timestamp"),
    )

    validation_errors = spark_validation_error_column()
    classified_df = flattened_df.withColumn("error_reason", validation_errors)

    valid_df = (
        classified_df.filter(col("error_reason") == "")
        .drop("raw_payload", "error_reason", "event_timestamp_raw")
        .withColumn("partition_timestamp", col("event_timestamp"))
        .withColumn("year", date_format(col("partition_timestamp"), "yyyy"))
        .withColumn("month", date_format(col("partition_timestamp"), "MM"))
        .withColumn("day", date_format(col("partition_timestamp"), "dd"))
        .withColumn("hour", date_format(col("partition_timestamp"), "HH"))
    )

    silver_path = data_lake_root / "silver" / "transactions_cleaned"
    valid_df.write.mode("append").partitionBy("year", "month", "day", "hour").parquet(str(silver_path))

    invalid_df = (
        classified_df.filter(col("error_reason") != "")
        .select("raw_payload", "error_reason", "processing_timestamp")
        .withColumn("partition_timestamp", col("processing_timestamp"))
        .withColumn("year", date_format(col("partition_timestamp"), "yyyy"))
        .withColumn("month", date_format(col("partition_timestamp"), "MM"))
        .withColumn("day", date_format(col("partition_timestamp"), "dd"))
    )

    quarantine_path = data_lake_root / "quarantine" / "bad_transactions"
    invalid_df.write.mode("append").partitionBy("year", "month", "day").json(str(quarantine_path))


def transaction_schema() -> Any:
    from pyspark.sql.types import DecimalType, StringType, StructField, StructType

    return StructType(
        [
            StructField("event_id", StringType(), True),
            StructField("transaction_id", StringType(), True),
            StructField("user_id", StringType(), True),
            StructField("account_id", StringType(), True),
            StructField("amount", DecimalType(18, 2), True),
            StructField("currency", StringType(), True),
            StructField("merchant_category", StringType(), True),
            StructField("transaction_type", StringType(), True),
            StructField("channel", StringType(), True),
            StructField("country", StringType(), True),
            StructField("city", StringType(), True),
            StructField("status", StringType(), True),
            StructField("event_timestamp", StringType(), True),
            StructField("ingestion_timestamp", StringType(), True),
        ]
    )


def spark_validation_error_column() -> Any:
    from pyspark.sql.functions import col, concat_ws, lit, when

    null_string = lit(None).cast("string")
    required_checks = []
    for field in REQUIRED_FIELDS:
        if field == "amount":
            required_checks.append(when(col("amount").isNull(), lit("amount is required")).otherwise(null_string))
        elif field == "event_timestamp":
            required_checks.append(
                when(
                    col("event_timestamp_raw").isNull() | (col("event_timestamp_raw") == ""),
                    lit("event_timestamp is required"),
                ).otherwise(null_string)
            )
        else:
            required_checks.append(
                when(col(field).isNull() | (col(field) == ""), lit(f"{field} is required")).otherwise(null_string)
            )

    return concat_ws(
        "; ",
        *required_checks,
        when(col("amount").isNotNull() & (col("amount") <= 0), lit("amount must be greater than 0")).otherwise(null_string),
        when(col("currency").isNotNull() & ~col("currency").isin(*sorted(ALLOWED_CURRENCIES)),
             lit("currency must be one of AUD, VND, USD")).otherwise(null_string),
        when(col("transaction_type").isNotNull() & ~col("transaction_type").isin(*sorted(ALLOWED_TRANSACTION_TYPES)),
             lit("transaction_type must be one of CARD_PAYMENT, ATM_WITHDRAWAL, TRANSFER, LOAN_REPAYMENT")).otherwise(null_string),
        when(col("channel").isNotNull() & ~col("channel").isin(*sorted(ALLOWED_CHANNELS)),
             lit("channel must be one of MOBILE, WEB, ATM, BRANCH")).otherwise(null_string),
        when(
            col("event_timestamp_raw").isNotNull() & (col("event_timestamp_raw") != "") & col("event_timestamp").isNull(),
            lit("event_timestamp must be an ISO-8601 timestamp"),
        ).otherwise(null_string),
    )


if __name__ == "__main__":
    main()
