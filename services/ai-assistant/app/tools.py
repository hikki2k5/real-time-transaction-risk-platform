from __future__ import annotations

import json
from contextlib import closing
from dataclasses import dataclass
from typing import Any

from app.config import Settings


@dataclass(frozen=True)
class ToolResult:
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any] | list[dict[str, Any]] | None
    result_summary: str


class RiskTools:
    def __init__(self, settings: Settings):
        self.settings = settings

    def get_transaction_audit(self, transaction_id: str, user_id: str | None = None) -> ToolResult:
        query = """
            SELECT transaction_id, event_id, user_id, account_id, amount, currency,
                   transaction_type, channel, decision, fraud_probability, risk_level,
                   response_payload->'reason_codes' AS reason_codes, created_at
            FROM core.transaction_requests
            WHERE transaction_id = %s
        """
        params = (transaction_id,)
        if user_id is not None:
            query += " AND user_id = %s"
            params = (transaction_id, user_id)
        try:
            with closing(self._connect()) as connection, connection:
                with connection.cursor(cursor_factory=self._cursor_factory()) as cursor:
                    cursor.execute(query, params)
                    row = cursor.fetchone()
        except Exception as exc:
            return ToolResult(
                name="get_transaction_audit",
                arguments={"transaction_id": transaction_id},
                result=None,
                result_summary=f"transaction audit lookup unavailable: {type(exc).__name__}",
            )

        if not row:
            return ToolResult(
                name="get_transaction_audit",
                arguments={"transaction_id": transaction_id},
                result=None,
                result_summary=f"no audit row found for transaction_id={transaction_id}",
            )

        result = normalize_json(row)
        return ToolResult(
            name="get_transaction_audit",
            arguments={"transaction_id": transaction_id},
            result=result,
            result_summary=(
                f"transaction {result['transaction_id']} decision={result['decision']} "
                f"risk={result['risk_level']} probability={result['fraud_probability']}"
            ),
        )

    def get_recent_transactions(self, user_id: str, limit: int = 5) -> ToolResult:
        query = """
            SELECT transaction_id, amount, currency, decision, risk_level, created_at
            FROM core.transaction_requests
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
        """
        try:
            with closing(self._connect()) as connection, connection:
                with connection.cursor(cursor_factory=self._cursor_factory()) as cursor:
                    cursor.execute(query, (user_id, max(1, min(limit, 10))))
                    rows = cursor.fetchall()
        except Exception as exc:
            return ToolResult(
                name="get_recent_transactions",
                arguments={"user_id": user_id, "limit": limit},
                result=[],
                result_summary=f"recent transaction lookup unavailable: {type(exc).__name__}",
            )

        result = [normalize_json(row) for row in rows]
        return ToolResult(
            name="get_recent_transactions",
            arguments={"user_id": user_id, "limit": limit},
            result=result,
            result_summary=f"found {len(result)} recent transactions for user_id={user_id}",
        )

    def _connect(self) -> Any:
        import psycopg2

        return psycopg2.connect(
            host=self.settings.postgres_host,
            port=self.settings.postgres_port,
            dbname=self.settings.postgres_db,
            user=self.settings.postgres_user,
            password=self.settings.postgres_password,
            sslmode=self.settings.postgres_sslmode,
            connect_timeout=5,
            options="-c statement_timeout=5000 -c default_transaction_read_only=on",
        )

    @staticmethod
    def _cursor_factory() -> Any:
        from psycopg2.extras import RealDictCursor

        return RealDictCursor


def normalize_json(value: Any) -> Any:
    return json.loads(json.dumps(value, default=str))
