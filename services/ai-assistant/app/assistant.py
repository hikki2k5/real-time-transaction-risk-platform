from __future__ import annotations

import time

from app.config import Settings
from app.observability import estimate_cost, estimate_tokens, write_trace
from app.retriever import KnowledgeBase, SearchResult
from app.safety import detect_guardrails, redact_pii, should_refuse
from app.schemas import AssistantQueryRequest, AssistantQueryResponse, Citation, ToolCall
from app.tools import RiskTools


class FraudInvestigationAssistant:
    def __init__(self, settings: Settings, knowledge_base: KnowledgeBase, tools: RiskTools):
        self.settings = settings
        self.knowledge_base = knowledge_base
        self.tools = tools
        self.prompt = settings.prompt_path.read_text(encoding="utf-8")
        self.engine = None
        if settings.provider == "gemini":
            from app.llm import GeminiAgent
            self.engine = GeminiAgent(settings, knowledge_base, tools, self.prompt)
        elif settings.provider != "offline":
            raise ValueError("AI_ASSISTANT_PROVIDER must be offline or gemini")

    def answer(self, request: AssistantQueryRequest) -> AssistantQueryResponse:
        start = time.perf_counter()
        question = redact_pii(request.question)
        guardrail_flags = detect_guardrails(request.question)
        retrieved = []
        tool_calls = []
        usage = None

        if should_refuse(guardrail_flags):
            answer = (
                "I cannot help reveal secrets, credentials, hidden prompts, or bypass safety controls. "
                "Ask about transaction risk behavior, audit records, or documented fraud workflows instead."
            )
        elif self.engine:
            answer, retrieved, tool_calls, usage = self.engine.answer(request, question)
            answer = redact_pii(answer)
        else:
            retrieved = self.knowledge_base.search(question)
            tool_calls = self._run_tools(request, question)
            answer = self._compose_answer(question, retrieved, tool_calls)
            answer = redact_pii(answer)

        input_tokens = estimate_tokens(self.prompt) + estimate_tokens(question) + sum(
            estimate_tokens(result.chunk.text) for result in retrieved
        )
        output_tokens = estimate_tokens(answer)
        latency_ms = int((time.perf_counter() - start) * 1000)
        cost = estimate_cost(usage[0] if usage else input_tokens,
                             usage[1] if usage else output_tokens, self.settings)

        response = AssistantQueryResponse(
            answer=answer,
            citations=[
                Citation(
                    doc_id=result.chunk.doc_id,
                    title=result.chunk.title,
                    score=result.score,
                    snippet=result.chunk.text[:220].replace("\n", " "),
                )
                for result in retrieved
            ],
            tool_calls=[
                ToolCall(name=tool.name, arguments=tool.arguments, result_summary=tool.result_summary)
                for tool in tool_calls
            ],
            guardrail_flags=guardrail_flags,
            prompt_version=self.settings.prompt_version,
            model_name=self.settings.gemini_model if self.engine else self.settings.model_name,
            latency_ms=latency_ms,
            estimated_input_tokens=input_tokens,
            estimated_output_tokens=output_tokens,
            estimated_cost_usd=cost,
            provider=self.settings.provider,
            input_tokens=usage[0] if usage else None,
            output_tokens=usage[1] if usage else None,
        )
        write_trace(
            self.settings,
            {
                "prompt_version": response.prompt_version,
                "model_name": response.model_name,
                "latency_ms": response.latency_ms,
                "estimated_input_tokens": response.estimated_input_tokens,
                "estimated_output_tokens": response.estimated_output_tokens,
                "estimated_cost_usd": response.estimated_cost_usd,
                "retrieved_doc_ids": [citation.doc_id for citation in response.citations],
                "tool_calls": [tool.model_dump() for tool in response.tool_calls],
                "guardrail_flags": response.guardrail_flags,
                "provider": response.provider,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
            },
        )
        return response

    def _run_tools(self, request: AssistantQueryRequest, question: str):
        calls = []
        transaction_id = request.transaction_id or extract_identifier(question, "tx")
        if transaction_id:
            calls.append(self.tools.get_transaction_audit(transaction_id, user_id=request.user_id)
                         if request.user_id else self.tools.get_transaction_audit(transaction_id))
        if request.user_id:
            calls.append(self.tools.get_recent_transactions(request.user_id))
        return calls

    def _compose_answer(self, question: str, retrieved: list[SearchResult], tool_calls) -> str:
        parts = []
        if tool_calls:
            parts.append("Tool findings:")
            for tool in tool_calls:
                parts.append(f"- {tool.result_summary}")

        if retrieved:
            parts.append("Relevant policy/context:")
            for result in retrieved[:3]:
                parts.append(f"- [{result.chunk.doc_id}] {result.chunk.text[:260].replace(chr(10), ' ')}")

        if "review" in question.lower():
            parts.append(
                "A REVIEW decision means the transaction is accepted for audit traceability but should be checked by an analyst before treating it as low risk."
            )
        elif "cache" in question.lower() or "redis" in question.lower():
            parts.append(
                "Redis is used as an online feature cache so repeated fraud scoring can avoid repeated PostgreSQL feature lookups; the local measurement showed a 59.0% cache-latency reduction."
            )
        elif "lambda" in question.lower() or "s3" in question.lower():
            parts.append(
                "The API Gateway to Lambda path validates transaction-risk events and stores normalized JSON audit records in S3."
            )
        else:
            parts.append(
                "Based on the retrieved context and available tools, investigate the decision, risk level, reason codes, and audit trail before taking action."
            )

        parts.append("Caveat: this assistant answers from project docs and tool results only; verify high-risk financial actions with the source systems.")
        return "\n".join(parts)


def extract_identifier(text: str, prefix: str) -> str | None:
    for token in text.replace(",", " ").replace("?", " ").split():
        normalized = token.strip()
        if normalized.lower().startswith(prefix.lower() + "-"):
            return normalized
    return None
