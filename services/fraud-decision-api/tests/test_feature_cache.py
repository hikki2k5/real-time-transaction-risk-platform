from __future__ import annotations

from pathlib import Path

from app.config import Settings
from app.repository import PredictionRepository


class FakeCache:
    def __init__(self, value=None) -> None:
        self.value = value
        self.set_calls = []

    def get(self, user_id: str):
        return self.value

    def set(self, user_id: str, features: dict) -> None:
        self.set_calls.append((user_id, features))


class FakeRepository(PredictionRepository):
    def __init__(self, cache: FakeCache):
        super().__init__(settings(), feature_cache=cache)
        self.db_calls = 0

    def _connect(self):  # pragma: no cover - deliberately not used in these tests
        self.db_calls += 1
        raise AssertionError("database should not be called")


def settings() -> Settings:
    return Settings(
        postgres_host="localhost",
        postgres_port=55432,
        postgres_db="transaction_risk",
        postgres_user="risk_user",
        postgres_password="risk_password",
        mlflow_tracking_uri="http://localhost:5000",
        model_name="fraud-risk-model",
        fallback_model_dir=Path("."),
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_enabled=True,
        feature_cache_ttl_seconds=300,
        dashboard_allowed_origins=["http://localhost:3000"],
    )


def test_customer_feature_cache_hit_skips_postgres() -> None:
    cache = FakeCache(value={"tx_count_24h": 3})
    repository = FakeRepository(cache)

    features = repository.get_customer_features("user-1")

    assert features == {"tx_count_24h": 3}
    assert repository.db_calls == 0


def test_customer_feature_cache_can_be_disabled_without_redis_dependency() -> None:
    disabled = Settings(
        postgres_host="localhost",
        postgres_port=55432,
        postgres_db="transaction_risk",
        postgres_user="risk_user",
        postgres_password="risk_password",
        mlflow_tracking_uri="http://localhost:5000",
        model_name="fraud-risk-model",
        fallback_model_dir=Path("."),
        redis_host="localhost",
        redis_port=6379,
        redis_db=0,
        redis_enabled=False,
        feature_cache_ttl_seconds=300,
        dashboard_allowed_origins=["http://localhost:3000"],
    )

    repository = PredictionRepository(disabled)

    assert repository.feature_cache.get("user-1") is None
