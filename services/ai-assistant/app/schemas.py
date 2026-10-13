from __future__ import annotations

from pydantic import BaseModel, Field


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    transaction_id: str | None = None
    user_id: str | None = None


class Citation(BaseModel):
    doc_id: str
    title: str
    score: float
    snippet: str


class ToolCall(BaseModel):
    name: str
    arguments: dict
    result_summary: str


class AssistantQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    tool_calls: list[ToolCall]
    guardrail_flags: list[str]
    prompt_version: str
    model_name: str
    latency_ms: int
    estimated_input_tokens: int
    estimated_output_tokens: int
    estimated_cost_usd: float
    provider: str = "offline"
    input_tokens: int | None = None
    output_tokens: int | None = None


class HealthResponse(BaseModel):
    status: str
    prompt_version: str
    indexed_documents: int
