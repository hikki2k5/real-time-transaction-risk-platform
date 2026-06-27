from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    mlflow_tracking_uri: str
    model_name: str
    fallback_model_dir: Path
    redis_host: str
    redis_port: int
    redis_db: int
    redis_enabled: bool
    feature_cache_ttl_seconds: int
    dashboard_allowed_origins: list[str]


def get_settings() -> Settings:
    fallback_model_dir = _resolve_path(
        os.getenv(
            "FALLBACK_MODEL_DIR",
            "pipelines/training/model-artifacts/fraud-risk-model",
        )
    )
    return Settings(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "55432")),
        postgres_db=os.getenv("POSTGRES_DB", "transaction_risk"),
        postgres_user=os.getenv("POSTGRES_USER", "risk_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "risk_password"),
        mlflow_tracking_uri=os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"),
        model_name=os.getenv("MODEL_NAME", "fraud-risk-model"),
        fallback_model_dir=fallback_model_dir,
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        redis_enabled=os.getenv("REDIS_ENABLED", "true").lower() == "true",
        feature_cache_ttl_seconds=int(os.getenv("FEATURE_CACHE_TTL_SECONDS", "300")),
        dashboard_allowed_origins=_split_csv(
            os.getenv(
                "DASHBOARD_ALLOWED_ORIGINS",
                "http://localhost:3000,http://127.0.0.1:3000,http://localhost:8088",
            )
        ),
    )


def _resolve_path(path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path

    cwd_path = path.resolve()
    if cwd_path.exists():
        return cwd_path

    repo_root = Path(__file__).resolve().parents[3]
    return (repo_root / path).resolve()


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]
