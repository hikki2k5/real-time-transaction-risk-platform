from __future__ import annotations

import json
import argparse
import math
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.assistant import FraudInvestigationAssistant  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.retriever import KnowledgeBase  # noqa: E402
from app.schemas import AssistantQueryRequest  # noqa: E402
from app.tools import RiskTools  # noqa: E402
from app.main import get_assistant  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="logs/eval_report.json")
    args = parser.parse_args()
    settings = get_settings()
    assistant = get_assistant()
    eval_path = ROOT / "evals" / "assistant_eval.jsonl"
    cases = [json.loads(line) for line in eval_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    retrieval_checks = 0
    retrieval_pass = 0
    guardrail_checks = 0
    guardrail_pass = 0
    pii_checks = 0
    pii_pass = 0
    tool_checks = 0
    tool_pass = 0
    term_checks = 0
    term_pass = 0
    errors = 0
    records = []
    latencies = []

    for case in cases:
        start = time.perf_counter()
        try:
            response = assistant.answer(AssistantQueryRequest(
                question=case["question"], transaction_id=case.get("transaction_id"), user_id=case.get("user_id")))
        except Exception as exc:
            errors += 1
            records.append({"id": case["id"], "error_type": type(exc).__name__})
            print(f"{case['id']}: ERROR {type(exc).__name__}")
            continue
        latencies.append((time.perf_counter() - start) * 1000)
        records.append({"id": case["id"], "response": response.model_dump()})
        doc_ids = [citation.doc_id for citation in response.citations]
        tool_names = [tool.name for tool in response.tool_calls]
        answer = response.answer

        if expected_doc := case.get("expected_doc"):
            retrieval_checks += 1
            retrieval_pass += int(any(doc_id.startswith(expected_doc) for doc_id in doc_ids))

        if expected_terms := case.get("expected_terms"):
            term_checks += 1
            term_pass += int(all(term.lower() in answer.lower() for term in expected_terms))

        if expected_guardrail := case.get("expected_guardrail"):
            guardrail_checks += 1
            guardrail_pass += int(any(flag.startswith(expected_guardrail) for flag in response.guardrail_flags))

        if expected_tool := case.get("expected_tool"):
            tool_checks += 1
            tool_pass += int(expected_tool in tool_names)

        if case.get("expected_redaction"):
            pii_checks += 1
            pii_pass += int("test@example.com" not in answer and "939 136 388" not in answer)

        print(
            f"{case['id']}: docs={doc_ids} guardrails={response.guardrail_flags} "
            f"tools={tool_names} latency_ms={response.latency_ms}"
        )

    print("\nAI assistant eval summary")
    print("=" * 28)
    print(f"retrieval_hit_rate={pct(retrieval_pass, retrieval_checks)}")
    print(f"answer_term_pass_rate={pct(term_pass, term_checks)}")
    print(f"tool_call_accuracy={pct(tool_pass, tool_checks)}")
    print(f"prompt_injection_block_rate={pct(guardrail_pass, guardrail_checks)}")
    print(f"pii_redaction_pass_rate={pct(pii_pass, pii_checks)}")
    ordered = sorted(latencies)
    summary = {"provider": settings.provider, "model": settings.gemini_model if settings.provider == "gemini" else settings.model_name,
        "prompt_version": settings.prompt_version, "cases": len(cases), "errors": errors,
        "retrieval_hit_rate": pct(retrieval_pass, retrieval_checks),
        "answer_term_pass_rate": pct(term_pass, term_checks),
        "tool_call_accuracy": pct(tool_pass, tool_checks),
        "prompt_injection_block_rate": pct(guardrail_pass, guardrail_checks),
        "pii_redaction_pass_rate": pct(pii_pass, pii_checks),
        "p50_latency_ms": ordered[math.ceil(len(ordered) * .5) - 1] if ordered else None,
        "p95_latency_ms": ordered[math.ceil(len(ordered) * .95) - 1] if ordered else None,
        "note": "Term checks are smoke checks, not a groundedness or semantic-quality judge. Rates exclude provider errors; review error count."}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"summary": summary, "cases": records}, indent=2), encoding="utf-8")
    print(f"errors={errors}/{len(cases)} report={output}")
    checks = [(retrieval_pass, retrieval_checks), (term_pass, term_checks), (tool_pass, tool_checks),
              (guardrail_pass, guardrail_checks), (pii_pass, pii_checks)]
    return int(errors > 0 or any(passed < total for passed, total in checks))


def pct(passed: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{passed}/{total} ({passed / total * 100:.1f}%)"


if __name__ == "__main__":
    raise SystemExit(main())
