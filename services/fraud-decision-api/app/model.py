from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd

from app.config import Settings


FEATURE_COLUMNS = [
    "amount",
    "tx_count_5min",
    "tx_count_1h",
    "tx_count_24h",
    "spend_24h",
    "avg_amount_7d",
    "max_amount_7d",
    "amount_stddev_7d",
    "declined_tx_count_24h",
    "overseas_tx_count_30d",
    "unique_merchant_count_7d",
    "cash_withdrawal_ratio_30d",
]

DEFAULT_FEATURES = {
    "tx_count_5min": 0,
    "tx_count_1h": 0,
    "tx_count_24h": 0,
    "spend_24h": 0,
    "avg_amount_7d": 0,
    "max_amount_7d": 0,
    "amount_stddev_7d": 0,
    "declined_tx_count_24h": 0,
    "overseas_tx_count_30d": 0,
    "unique_merchant_count_7d": 0,
    "cash_withdrawal_ratio_30d": 0,
}


@dataclass(frozen=True)
class ModelBundle:
    model: Any
    model_name: str
    model_version: str
    source: str
    feature_columns: list[str]


class ModelProvider:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._bundle: ModelBundle | None = None

    def get_bundle(self) -> ModelBundle:
        if self._bundle is None:
            self._bundle = self._load_model()
        return self._bundle

    def predict_probability(self, feature_payload: dict[str, Any]) -> float:
        bundle = self.get_bundle()
        frame = pd.DataFrame([{column: feature_payload.get(column, 0) for column in bundle.feature_columns}])
        probabilities = bundle.model.predict_proba(frame)
        return float(probabilities[0][1])

    def _load_model(self) -> ModelBundle:
        try:
            mlflow.set_tracking_uri(self.settings.mlflow_tracking_uri)
            model_uri = f"models:/{self.settings.model_name}/latest"
            model = mlflow.sklearn.load_model(model_uri)
            return ModelBundle(
                model=model,
                model_name=self.settings.model_name,
                model_version="latest",
                source="mlflow",
                feature_columns=FEATURE_COLUMNS,
            )
        except Exception:
            return self._load_fallback_model(self.settings.fallback_model_dir)

    def _load_fallback_model(self, model_dir: Path) -> ModelBundle:
        model_path = model_dir / "model.joblib"
        metadata_path = model_dir / "metadata.json"
        if not model_path.exists():
            raise RuntimeError(f"Fallback model artifact not found: {model_path}")

        metadata = {}
        if metadata_path.exists():
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

        return ModelBundle(
            model=joblib.load(model_path),
            model_name=str(metadata.get("model_name", self.settings.model_name)),
            model_version=str(metadata.get("selected_candidate", "fallback")),
            source="fallback",
            feature_columns=list(metadata.get("feature_columns", FEATURE_COLUMNS)),
        )


def build_feature_payload(amount: float, user_features: dict[str, Any] | None) -> dict[str, Any]:
    payload = {"amount": amount}
    payload.update(DEFAULT_FEATURES)
    if user_features:
        for key in DEFAULT_FEATURES:
            payload[key] = user_features.get(key, payload[key])
    return {key: _to_float(value) for key, value in payload.items()}


def _to_float(value: Any) -> float:
    if value is None:
        return 0.0
    return float(value)
