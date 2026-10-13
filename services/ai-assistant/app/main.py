from __future__ import annotations

from functools import lru_cache

import secrets
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.assistant import FraudInvestigationAssistant
from app.config import get_settings
from app.diagnostics import log_failure, logger
from app.retriever import KnowledgeBase
from app.schemas import AssistantQueryRequest, AssistantQueryResponse, HealthResponse
from app.tools import RiskTools


def create_app() -> FastAPI:
    app = FastAPI(title="Fraud Investigation AI Assistant", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type"],
    )

    @app.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        settings = get_settings()
        return HealthResponse(
            status="ok",
            prompt_version=settings.prompt_version,
            indexed_documents=len(KnowledgeBase(settings.knowledge_dir).chunks),
        )

    @app.post("/v1/assistant/query", response_model=AssistantQueryResponse)
    def query(request: AssistantQueryRequest, authorization: str | None = Header(default=None)) -> AssistantQueryResponse:
        settings = get_settings()
        if settings.provider == "gemini" and not settings.api_token:
            logger.error("assistant_configuration_error missing=AI_ASSISTANT_API_TOKEN")
            raise HTTPException(503, "Configure AI_ASSISTANT_API_TOKEN for the operator API")
        if settings.api_token and not secrets.compare_digest(authorization or "", "Bearer " + settings.api_token):
            raise HTTPException(401, "Operator authentication required")
        if settings.provider == "gemini" and not settings.gemini_api_key:
            logger.error("assistant_configuration_error missing=GEMINI_API_KEY")
            raise HTTPException(503, "Gemini credentials are not configured")
        from app.llm import AssistantProviderError
        stage = "initialize"
        try:
            assistant = get_assistant()
            stage = "answer"
            return assistant.answer(request)
        except AssistantProviderError as error:
            log_failure(stage, error)
            raise HTTPException(502, "Model provider unavailable; check key, quota and model configuration")
        except Exception as error:
            log_failure(stage, error)
            raise HTTPException(503, "Assistant unavailable; check provider and index configuration")

    return app


@lru_cache
def get_assistant() -> FraudInvestigationAssistant:
    settings = get_settings()
    knowledge_base = KnowledgeBase(settings.knowledge_dir)
    if settings.provider == "gemini":
        from langchain_google_genai import GoogleGenerativeAIEmbeddings
        from app.semantic import SemanticKnowledgeBase
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required")
        embedder = GoogleGenerativeAIEmbeddings(model=settings.embedding_model,
                                               google_api_key=settings.gemini_api_key,
                                               output_dimensionality=settings.embedding_dimensions)
        knowledge_base = SemanticKnowledgeBase(settings, embedder)
    return FraudInvestigationAssistant(settings, knowledge_base, RiskTools(settings))


app = create_app()
