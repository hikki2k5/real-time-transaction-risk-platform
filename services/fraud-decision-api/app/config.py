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
