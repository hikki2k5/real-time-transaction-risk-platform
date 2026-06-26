from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from airflow.decorators import dag, task

LOGGER = logging.getLogger(__name__)

DEFAULT_DDL_PATH = Path("/opt/airflow/postgres/ddl")
DEFAULT_FEATURE_SQL_PATH = Path("/opt/airflow/postgres/transforms/customer_transaction_features.sql")
DATA_QUALITY_PATH = Path("/opt/airflow/data-quality")

if str(DATA_QUALITY_PATH) not in sys.path:
    sys.path.append(str(DATA_QUALITY_PATH))

from check_feature_tables import assert_feature_table_quality  # noqa: E402


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


def _ensure_feature_table() -> None:
    ddl_path = Path(os.getenv("POSTGRES_DDL_PATH", str(DEFAULT_DDL_PATH)))
    ddl_files = [
        ddl_path / "001_create_schemas.sql",
        ddl_path / "004_create_feature_tables.sql",
    ]

    with _connect_postgres() as connection:
        with connection.cursor() as cursor:
            for sql_file in ddl_files:
                _run_sql_file(cursor, sql_file)


@dag(
    dag_id="postgres_customer_transaction_features",
    description="Build customer transaction fraud features in Postgres.",
    schedule="@hourly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["local", "postgres", "features"],
)
def postgres_customer_transaction_features():
    @task
    def check_core_transactions() -> int:
        with _connect_postgres() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT to_regclass('core.cleaned_transactions')")
                if cursor.fetchone()[0] is None:
                    raise RuntimeError("core.cleaned_transactions does not exist")

                cursor.execute("SELECT COUNT(*) FROM core.cleaned_transactions")
                row_count = cursor.fetchone()[0]

        if row_count == 0:
            raise RuntimeError("core.cleaned_transactions has no rows")

        LOGGER.info("Core cleaned transaction rows: %s", row_count)
        return row_count

    @task
    def build_customer_features(core_row_count: int) -> int:
        _ensure_feature_table()
        feature_sql_path = Path(os.getenv("CUSTOMER_FEATURE_SQL_PATH", str(DEFAULT_FEATURE_SQL_PATH)))
        feature_sql = feature_sql_path.read_text(encoding="utf-8")

        with _connect_postgres() as connection:
            with connection.cursor() as cursor:
                cursor.execute(feature_sql)
                cursor.execute("SELECT COUNT(*) FROM features.customer_transaction_features")
                feature_row_count = cursor.fetchone()[0]

        LOGGER.info("Core rows available for feature build: %s", core_row_count)
        LOGGER.info("Feature row count: %s", feature_row_count)
        return feature_row_count

    @task
    def run_data_quality_checks(feature_row_count: int) -> int:
        with _connect_postgres() as connection:
            assert_feature_table_quality(connection)

        LOGGER.info("Feature data quality checks passed for %s rows", feature_row_count)
        return feature_row_count

    core_row_count = check_core_transactions()
    feature_row_count = build_customer_features(core_row_count)
    run_data_quality_checks(feature_row_count)


postgres_customer_transaction_features()

