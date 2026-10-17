"""Create A/B review records without revealing model labels to the reviewer."""
import argparse
import json
from pathlib import Path
import random


def export_review(report, output, seed=42):
    if output.exists():
        raise ValueError("Review directory exists; choose a fresh path")
    rng = random.Random(seed)
    rows, key = [], {}
    for comparison in report["comparisons"]:
        names = ["base", "adapter"]
        rng.shuffle(names)
        identifier = comparison["id"]
        key[identifier] = dict(zip(("A", "B"), names))
        rows.append({"id": identifier, "group": comparison.get("group"),
                     "question": comparison["question"], "context": comparison["context"],
                     "reference": comparison["reference"], "A": comparison[names[0]], "B": comparison[names[1]],
                     "review": {"A_factually_supported": None, "B_factually_supported": None,
                                "A_citations_correct": None, "B_citations_correct": None, "notes": ""}})
    rng.shuffle(rows)
    output.mkdir(parents=True)
    (output / "review.jsonl").write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")
    (output / "PRIVATE_mapping.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return len(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    count = export_review(json.loads(args.report.read_text(encoding="utf-8")), args.output)
    print(f"Exported {count} records. Give reviewer only review.jsonl, not PRIVATE_mapping.json.")
