"""Document-level smoke benchmark using the existing authored eval questions."""
import argparse
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.retriever import KnowledgeBase
from retrieval import RetrievalExperiment, ranking_metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "evals/assistant_eval.jsonl")
    parser.add_argument("--knowledge", type=Path, default=ROOT / "knowledge")
    parser.add_argument("--dense-model", help="Optional SentenceTransformer model ID; downloads weights")
    parser.add_argument("--reranker-model", help="Optional CrossEncoder model ID; downloads weights")
    parser.add_argument("--output", type=Path, default=ROOT / "logs/retrieval_baseline.json")
    args = parser.parse_args()
    corpus = KnowledgeBase(args.knowledge)
    cases = [json.loads(line) for line in args.cases.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [case for case in cases if case.get("expected_doc")]
    if not cases:
        parser.error("No document relevance labels")
    ids = {chunk.doc_id.split("#")[0] for chunk in corpus.chunks}
    if any(case["expected_doc"] not in ids for case in cases):
        parser.error("Relevance labels reference missing documents")
    engine = RetrievalExperiment(corpus.chunks, args.dense_model, args.reranker_model)
    engine.rank(cases[0]["question"])  # Exclude first inference initialization from query timing.
    records = []
    for case in cases:
        start = time.perf_counter()
        rankings = engine.rank(case["question"])
        elapsed = (time.perf_counter() - start) * 1000
        records.append({"id": case["id"], "combined_pipeline_latency_ms": elapsed,
                        "rankings": rankings, "metrics": {name: ranking_metrics(order, {case["expected_doc"]: 1})
                                                           for name, order in rankings.items()}})
    summary = {name: {metric: statistics.mean(record["metrics"][name][metric] for record in records)
                      for metric in records[0]["metrics"][name]} for name in records[0]["rankings"]}
    fingerprint = hashlib.sha256(json.dumps({"chunks": [(c.doc_id, c.text) for c in corpus.chunks],
                                            "cases": cases}, sort_keys=True).encode()).hexdigest()
    report = {"corpus_documents": len(ids), "chunks": len(corpus.chunks), "queries": len(cases),
              "fingerprint": fingerprint, "dense_model": args.dense_model, "reranker_model": args.reranker_model,
              "summary": summary, "records": records,
              "limitations": "Small authored English smoke set; one document label per query, not exhaustive chunk judgments. Recall@5 is trivial when corpus has five documents. Not held-out generalization, Vietnamese quality, production scale, or Gemini latency. Pipeline latency combines enabled methods and is not a per-method speed comparison. No models are trained by this script."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "records"}, indent=2))


if __name__ == "__main__":
    main()
