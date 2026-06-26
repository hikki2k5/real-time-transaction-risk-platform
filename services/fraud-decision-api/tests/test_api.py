from __future__ import annotations

from dataclasses import dataclass

from fastapi.testclient import TestClient

from app.main import create_app, get_model_provider, get_repository
from app.model import FEATURE_COLUMNS, ModelBundle


class FakeRepository:
    def __init__(self) -> None:
        self.logged_predictions = []

    def get_customer_features(self, user_id: str) -> dict:
        return {
            "tx_count_5min": 1,
            "tx_count_1h": 2,
            "tx_count_24h": 5,
            "spend_24h": 500,
            "avg_amount_7d": 100,
            "max_amount_7d": 250,
            "amount_stddev_7d": 25,
            "declined_tx_count_24h": 0,
            "overseas_tx_count_30d": 1,
            "unique_merchant_count_7d": 3,
            "cash_withdrawal_ratio_30d": 0.1,
        }

    def log_prediction(self, **kwargs) -> None:
        self.logged_predictions.append(kwargs)


@dataclass
class FakeModelProvider:
    probability: float

    def get_bundle(self) -> ModelBundle:
        return ModelBundle(
            model=object(),
            model_name="fraud-risk-model",
            model_version="test",
            source="test",
            feature_columns=FEATURE_COLUMNS,
        )

    def predict_probability(self, feature_payload: dict) -> float:
        return self.probability


def build_client(probability: float = 0.2) -> tuple[TestClient, FakeRepository]:
    app = create_app()
    repository = FakeRepository()
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_model_provider] = lambda: FakeModelProvider(probability)
    return TestClient(app), repository


def valid_request() -> dict:
    return {
        "transaction_id": "tx_test_001",
        "user_id": "user_001",
        "amount": 125.5,
        "merchant_category": "GROCERY",
        "country": "AU",
        "channel": "MOBILE",
        "event_timestamp": "2026-06-26T01:30:00Z",
    }


def test_request_validation_rejects_negative_amount() -> None:
    client, _ = build_client()
    payload = valid_request()
    payload["amount"] = -1

    response = client.post("/v1/fraud-score", json=payload)

    assert response.status_code == 422


def test_health_does_not_require_model_load() -> None:
    client, _ = build_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_decision_rule_blocks_high_probability() -> None:
    client, repository = build_client(probability=0.85)

    response = client.post("/v1/fraud-score", json=valid_request())

    assert response.status_code == 200
    body = response.json()
    assert body["risk_level"] == "HIGH"
    assert body["decision"] == "BLOCK"
    assert repository.logged_predictions[0]["decision"] == "BLOCK"


def test_score_response_format() -> None:
    client, _ = build_client(probability=0.45)

    response = client.post("/v1/fraud-score", json=valid_request())

    assert response.status_code == 200
    body = response.json()
    assert body["transaction_id"] == "tx_test_001"
    assert body["fraud_probability"] == 0.45
    assert body["risk_level"] == "MEDIUM"
    assert body["decision"] == "REVIEW"
    assert body["model_name"] == "fraud-risk-model"
    assert body["model_version"] == "test"
    assert isinstance(body["reason_codes"], list)
