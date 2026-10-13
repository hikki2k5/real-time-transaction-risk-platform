from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    postgres_host: str
    postgres_port: int
    postgres_db: str
    postgres_user: str
    postgres_password: str
    knowledge_dir: Path
    prompt_path: Path
    prompt_version: str
    log_path: Path
    model_name: str
    estimated_input_cost_per_1k: float
    estimated_output_cost_per_1k: float
    provider: str = "offline"
    gemini_model: str = "gemini-2.5-flash"
    embedding_model: str = "gemini-embedding-001"
    gemini_api_key: str = field(default="", repr=False)
    api_token: str = field(default="", repr=False)
    vector_collection: str = "fraud-investigation"
    embedding_dimensions: int = 768
    postgres_sslmode: str = "prefer"


@lru_cache
def get_settings() -> Settings:
    root = Path(__file__).resolve().parents[1]
    return Settings(
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "55432")),
        postgres_db=os.getenv("POSTGRES_DB", "transaction_risk"),
        postgres_user=os.getenv("POSTGRES_USER", "risk_user"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "risk_password"),
        knowledge_dir=Path(os.getenv("AI_KNOWLEDGE_DIR", str(root / "knowledge"))),
        prompt_path=Path(os.getenv("AI_PROMPT_PATH", str(root / "prompts" / "fraud_investigation_v1.md"))),
        prompt_version=os.getenv("AI_PROMPT_VERSION", "fraud-investigation-v1"),
        log_path=Path(os.getenv("AI_ASSISTANT_LOG_PATH", str(root / "logs" / "assistant_traces.jsonl"))),
        model_name=os.getenv("AI_ASSISTANT_MODEL", "deterministic-rag-v1"),
        estimated_input_cost_per_1k=float(os.getenv("AI_INPUT_COST_PER_1K", "0")),
        estimated_output_cost_per_1k=float(os.getenv("AI_OUTPUT_COST_PER_1K", "0")),
        provider=os.getenv("AI_ASSISTANT_PROVIDER", "offline"),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        embedding_model=os.getenv("AI_EMBEDDING_MODEL", "gemini-embedding-001"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
        api_token=os.getenv("AI_ASSISTANT_API_TOKEN", ""),
        vector_collection=os.getenv("AI_VECTOR_COLLECTION", "fraud-investigation"),
        embedding_dimensions=int(os.getenv("AI_EMBEDDING_DIMENSIONS", "768")),
        postgres_sslmode=os.getenv("POSTGRES_SSLMODE", "prefer"),
    )
