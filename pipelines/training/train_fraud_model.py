from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import joblib
import lightgbm as lgb
import mlflow
import mlflow.sklearn
import xgboost as xgb
from evaluate_model import evaluate_classifier, save_metrics
from feature_builder import (
    FEATURE_COLUMNS,
    connect_postgres,
    load_training_dataset,
    preprocess_features,
    time_based_train_test_split,
)
from generate_synthetic_fraud_labels import ensure_synthetic_fraud_labels
from sklearn.model_selection import train_test_split

MODEL_NAME = "fraud-risk-model"
FALLBACK_MODEL_DIR = Path("model-artifacts") / MODEL_NAME


def train() -> dict[str, Any]:
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000"))
    mlflow.set_experiment("fraud-risk-training")

    label_count = ensure_synthetic_fraud_labels()
    with connect_postgres() as connection:
        dataset = load_training_dataset(connection)

    if dataset.empty:
        raise ValueError("Training dataset is empty after joining transactions, features, and labels")

    train_df, test_df = time_based_train_test_split(dataset)
    if train_df["is_fraud"].nunique() < 2 and dataset["is_fraud"].nunique() >= 2:
        train_df, test_df = train_test_split(
            dataset,
            test_size=0.25,
            random_state=42,
            stratify=dataset["is_fraud"],
        )

    x_train, y_train = preprocess_features(train_df)
    x_test, y_test = preprocess_features(test_df)

    if y_train.nunique() < 2:
        raise ValueError("Training data needs at least two label classes. Add more transactions or labels.")

    scale_pos_weight = calculate_scale_pos_weight(y_train)
    candidates = {
        "lightgbm": lgb.LGBMClassifier(
            objective="binary",
            n_estimators=150,
            learning_rate=0.05,
            num_leaves=31,
            scale_pos_weight=scale_pos_weight,
            random_state=42,
            verbose=-1,
        ),
        "xgboost": xgb.XGBClassifier(
            objective="binary:logistic",
            n_estimators=150,
            learning_rate=0.05,
            max_depth=4,
            subsample=0.9,
            colsample_bytree=0.9,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=42,
        ),
    }

    results: dict[str, dict[str, Any]] = {}
    best_name = ""
    best_model: Any = None
    best_score = -1.0

    for model_name, model in candidates.items():
        with mlflow.start_run(run_name=model_name):
            model.fit(x_train, y_train)
            metrics = evaluate_classifier(model, x_test, y_test)
            results[model_name] = metrics

            mlflow.log_param("model_type", model_name)
            mlflow.log_param("feature_columns", ",".join(FEATURE_COLUMNS))
            mlflow.log_param("train_rows", len(x_train))
            mlflow.log_param("test_rows", len(x_test))
            mlflow.log_param("label_rows", label_count)
            mlflow.log_param("note", "Synthetic labels are for local pipeline testing, not model accuracy claims.")

            for metric_name, metric_value in metrics.items():
                if metric_name != "confusion_matrix":
                    mlflow.log_metric(metric_name, float(metric_value))

            metrics_path = Path("model-artifacts") / model_name / "metrics.json"
            save_metrics(metrics, metrics_path)
            mlflow.log_artifact(str(metrics_path))
            mlflow.sklearn.log_model(model, artifact_path="model")

            score = float(metrics["pr_auc"])
            if score > best_score:
                best_score = score
                best_name = model_name
                best_model = model

    if best_model is None:
        raise RuntimeError("No model was trained")

    fallback_path = save_fallback_model(best_model, best_name, results[best_name])

    with mlflow.start_run(run_name="register_best_model"):
        mlflow.log_param("best_model", best_name)
        mlflow.log_metric("best_pr_auc", best_score)
        mlflow.log_artifact(str(fallback_path))
        registered_model_info = mlflow.sklearn.log_model(
            best_model,
            artifact_path="model",
            registered_model_name=MODEL_NAME,
        )

    return {
        "best_model": best_name,
        "best_pr_auc": best_score,
        "fallback_model_path": str(fallback_path),
        "registered_model_uri": getattr(registered_model_info, "model_uri", None),
        "results": results,
    }


def calculate_scale_pos_weight(labels: Any) -> float:
    negative_count = int((labels == 0).sum())
    positive_count = int((labels == 1).sum())
    if positive_count == 0:
        return 1.0
    return max(negative_count / positive_count, 1.0)


def save_fallback_model(model: Any, model_name: str, metrics: dict[str, Any]) -> Path:
    FALLBACK_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    model_path = FALLBACK_MODEL_DIR / "model.joblib"
    metadata_path = FALLBACK_MODEL_DIR / "metadata.json"

    joblib.dump(model, model_path)
    metadata_path.write_text(
        json.dumps(
            {
                "model_name": MODEL_NAME,
                "selected_candidate": model_name,
                "feature_columns": FEATURE_COLUMNS,
                "metrics": metrics,
                "label_note": "Synthetic labels are for local development only.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return model_path


if __name__ == "__main__":
    summary = train()
    print(json.dumps(summary, indent=2))
