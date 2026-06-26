from __future__ import annotations

import logging
import os
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from airflow.decorators import dag, task

LOGGER = logging.getLogger(__name__)

SILVER_RELATIVE_PATH = Path("silver") / "transactions_cleaned"
DEFAULT_TRANSFORM_SQL_PATH = Path("/opt/airflow/postgres/transforms/raw_to_core_cleaned_transactions.sql")
DEFAULT_DDL_PATH = Path("/opt/airflow/postgres/ddl")


def _postgres_config() -> dict[str, Any]:
    return {
        "host": os.environ["POSTGRES_HOST"],
        "port": int(os.environ["POSTGRES_PORT"]),
        "dbname": os.environ["POSTGRES_DB"],
        "user": os.environ["POSTGRES_USER"],
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def _connect_postgres():
    import psycopg2

    return psycopg2.connect(**_postgres_config())


def _run_sql_file(cursor: Any, sql_path: Path) -> None:
    cursor.execute(sql_path.read_text(encoding="utf-8"))


def _ensure_warehouse_tables() -> None:
    ddl_path = Path(os.getenv("POSTGRES_DDL_PATH", str(DEFAULT_DDL_PATH)))
    ddl_files = [
        ddl_path / "001_create_schemas.sql",
        ddl_path / "002_create_raw_tables.sql",
        ddl_path / "003_create_core_tables.sql",
    ]

    with _connect_postgres() as connection:
        with connection.cursor() as cursor:
            for sql_file in ddl_files:
                _run_sql_file(cursor, sql_file)


def _normalise_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if hasattr(value, "as_py"):
        return value.as_py()
    return value


@dag(
    dag_id="local_lake_to_postgres_transactions",
    description="Load local data lake silver transactions into Postgres raw/core tables.",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["local", "postgres", "transactions"],
)
def local_lake_to_postgres_transactions():
    @task
    def find_silver_parquet_files() -> list[str]:
        data_lake_root = Path(os.environ["DATA_LAKE_ROOT"])
        silver_path = data_lake_root / SILVER_RELATIVE_PATH

        parquet_files = sorted(str(path) for path in silver_path.rglob("*.parquet") if path.is_file())
        if not parquet_files:
            raise FileNotFoundError(f"No Parquet files found under {silver_path}")

        LOGGER.info("Found %s silver transaction Parquet files", len(parquet_files))
        return parquet_files

    @task
    def load_raw_transactions(parquet_files: list[str]) -> int:
        import pyarrow.parquet as pq
        from psycopg2.extras import execute_values

        _ensure_warehouse_tables()

        insert_sql = """
            INSERT INTO raw.transactions_raw (
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
                source_file
            )
            VALUES %s
        """

        rows: list[tuple[Any, ...]] = []
        for file_path in parquet_files:
            table = pq.read_table(file_path)
            for record in table.to_pylist():
                rows.append(
                    (
                        _normalise_value(record.get("event_id")),
                        _normalise_value(record.get("transaction_id")),
                        _normalise_value(record.get("user_id")),
                        _normalise_value(record.get("account_id")),
                        _normalise_value(record.get("amount")),
                        _normalise_value(record.get("currency")),
                        _normalise_value(record.get("merchant_category")),
                        _normalise_value(record.get("transaction_type")),
                        _normalise_value(record.get("channel")),
                        _normalise_value(record.get("country")),
                        _normalise_value(record.get("city")),
                        _normalise_value(record.get("status")),
                        _normalise_value(record.get("event_timestamp")),
                        _normalise_value(record.get("ingestion_timestamp")),
                        file_path,
                    )
                )

        if not rows:
            raise ValueError("Silver Parquet files were found, but they contained no rows")

        with _connect_postgres() as connection:
            with connection.cursor() as cursor:
                execute_values(cursor, insert_sql, rows, page_size=1000)

        LOGGER.info("Raw rows loaded: %s", len(rows))
        return len(rows)

    @task
    def transform_raw_to_core(raw_rows_loaded: int) -> int:
        transform_sql_path = Path(
            os.getenv("RAW_TO_CORE_SQL_PATH", str(DEFAULT_TRANSFORM_SQL_PATH))
        )
        transform_sql = transform_sql_path.read_text(encoding="utf-8")

        with _connect_postgres() as connection:
            with connection.cursor() as cursor:
                cursor.execute(transform_sql)
                cursor.execute("SELECT COUNT(*) FROM core.cleaned_transactions")
                core_row_count = cursor.fetchone()[0]

        LOGGER.info("Raw rows loaded in this run: %s", raw_rows_loaded)
        LOGGER.info("Core rows after transform: %s", core_row_count)
        return core_row_count

    parquet_files = find_silver_parquet_files()
    raw_rows_loaded = load_raw_transactions(parquet_files)
    transform_raw_to_core(raw_rows_loaded)


local_lake_to_postgres_transactions()
