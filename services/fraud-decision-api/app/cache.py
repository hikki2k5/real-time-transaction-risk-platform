from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any

try:
    import redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - local tests can run before optional dependency install.
    redis = None

    class RedisError(Exception):
        pass

from app.config import Settings


class FeatureCache:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client: Any | None = None
        if settings.redis_enabled and redis is not None:
            self.client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                socket_connect_timeout=0.25,
                socket_timeout=0.25,
                decode_responses=True,
            )

    def get(self, user_id: str) -> dict[str, Any] | None:
        if self.client is None:
            return None
        try:
            value = self.client.get(self._key(user_id))
        except RedisError:
            return None
        if value is None:
            return None
        return json.loads(value)

    def set(self, user_id: str, features: dict[str, Any]) -> None:
        if self.client is None:
            return
        try:
            self.client.setex(
                self._key(user_id),
                self.settings.feature_cache_ttl_seconds,
                json.dumps(features, default=_json_default),
            )
        except RedisError:
            return

    @staticmethod
    def _key(user_id: str) -> str:
        return f"customer_features:{user_id}"


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")
