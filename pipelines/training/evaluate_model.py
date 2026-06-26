from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)


def evaluate_classifier(model: Any, features: pd.DataFrame, labels: pd.Series) -> dict[str, Any]:
    probabilities = model.predict_proba(features)[:, 1]
    predictions = (probabilities >= 0.5).astype(int)

    metrics: dict[str, Any] = {
        "pr_auc": safe_average_precision(labels, probabilities),
        "precision": precision_score(labels, predictions, zero_division=0),
        "recall": recall_score(labels, predictions, zero_division=0),
        "f1": f1_score(labels, predictions, zero_division=0),
        "confusion_matrix": confusion_matrix(labels, predictions).tolist(),
    }
    metrics["roc_auc"] = safe_roc_auc(labels, probabilities)
    return metrics


def safe_roc_auc(labels: pd.Series, probabilities: Any) -> float:
    if labels.nunique() < 2:
        return 0.0
    return float(roc_auc_score(labels, probabilities))


def safe_average_precision(labels: pd.Series, probabilities: Any) -> float:
    if labels.nunique() < 2:
        return 0.0
    return float(average_precision_score(labels, probabilities))


def save_metrics(metrics: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")

