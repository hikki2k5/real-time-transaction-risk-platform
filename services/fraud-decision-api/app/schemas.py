from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class FraudScoreRequest(BaseModel):
    transaction_id: str = Field(..., min_length=1)
    user_id: str = Field(..., min_length=1)
    amount: float = Field(..., gt=0)
    merchant_category: str = Field(..., min_length=1)
    country: str = Field(..., min_length=1)
    channel: str = Field(..., min_length=1)
    event_timestamp: datetime


class FraudScoreResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    risk_level: str
    decision: str
    model_name: str
    model_version: str
    reason_codes: list[str]


class ModelInfoResponse(BaseModel):
    model_name: str
    model_version: str
    source: str
    feature_columns: list[str]


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
