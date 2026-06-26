from __future__ import annotations

import time

from fastapi import Depends, FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import Settings, get_settings
from app.decision import build_reason_codes, classify_decision
from app.model import ModelProvider, build_feature_payload
from app.repository import PredictionRepository
from app.schemas import (
    FraudScoreRequest,
    FraudScoreResponse,
    HealthResponse,
    ModelInfoResponse,
)

REQUEST_COUNT = Counter(
    "fraud_decision_requests_total",
    "Total fraud score requests.",
)
REQUEST_LATENCY = Histogram(
    "fraud_decision_latency_seconds",
    "Fraud score request latency in seconds.",
)
DECISION_COUNT = Counter(
    "fraud_decision_decisions_total",
    "Fraud decision count by label.",
    ["decision"],
)


def create_app() -> FastAPI:
    app = FastAPI(title="Fraud Decision API", version="0.1.0")

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", model_loaded=False)

    @app.get("/v1/model-info", response_model=ModelInfoResponse)
    def model_info(model_provider: ModelProvider = Depends(get_model_provider)) -> ModelInfoResponse:
        bundle = model_provider.get_bundle()
        return ModelInfoResponse(
            model_name=bundle.model_name,
            model_version=bundle.model_version,
            source=bundle.source,
            feature_columns=bundle.feature_columns,
        )

    @app.post("/v1/fraud-score", response_model=FraudScoreResponse)
    def fraud_score(
        request: FraudScoreRequest,
        repository: PredictionRepository = Depends(get_repository),
        model_provider: ModelProvider = Depends(get_model_provider),
    ) -> FraudScoreResponse:
        start_time = time.perf_counter()
        REQUEST_COUNT.inc()

        user_features = repository.get_customer_features(request.user_id)
        feature_payload = build_feature_payload(request.amount, user_features)
        fraud_probability = model_provider.predict_probability(feature_payload)
        risk_level, decision = classify_decision(fraud_probability)
        bundle = model_provider.get_bundle()
        reason_codes = build_reason_codes(
            fraud_probability,
            request.model_dump(),
            features_found=user_features is not None,
        )
        latency_ms = int((time.perf_counter() - start_time) * 1000)

        repository.log_prediction(
            transaction_id=request.transaction_id,
            user_id=request.user_id,
            fraud_probability=fraud_probability,
            risk_level=risk_level,
            decision=decision,
            model_name=bundle.model_name,
            model_version=bundle.model_version,
            feature_payload=feature_payload,
            reason_codes=reason_codes,
            latency_ms=latency_ms,
        )

        DECISION_COUNT.labels(decision=decision).inc()
        REQUEST_LATENCY.observe((time.perf_counter() - start_time))

        return FraudScoreResponse(
            transaction_id=request.transaction_id,
            fraud_probability=fraud_probability,
            risk_level=risk_level,
            decision=decision,
            model_name=bundle.model_name,
            model_version=bundle.model_version,
            reason_codes=reason_codes,
        )

    @app.get("/metrics")
    def metrics() -> Response:
        return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return app


def get_repository() -> PredictionRepository:
    return PredictionRepository(get_settings())


def get_model_provider() -> ModelProvider:
    return ModelProvider(get_settings())


app = create_app()
