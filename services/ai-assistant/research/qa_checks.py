"""Transparent string checks, not semantic factuality/groundedness judgments."""
import re


def answer_checks(row, answer):
    citations = re.findall(r"\[([A-Za-z0-9_-]+)\]", answer)
    checks = {}
    if "expected_citations" in row:
        checks["citation_ids_match"] = set(citations) == set(row["expected_citations"])
    if row.get("unanswerable"):
        checks["refusal_marker_present"] = any(marker in answer.casefold() for marker in (
            "insufficient evidence", "not enough information", "cannot determine", "not recorded",
            "khong du thong tin", "khong du bang chung", "kh\u00f4ng \u0111\u1ee7 th\u00f4ng tin"))
    elif row.get("expected_value"):
        value = re.escape(row["expected_value"].casefold())
        checks["expected_value_present"] = re.search(r"(?<!\w)" + value + r"(?!\w)", answer.casefold()) is not None
    return checks


def summarize_checks(comparisons):
    result = {}
    for model in ("base", "adapter"):
        aggregates = {}
        for comparison in comparisons:
            for name, passed in comparison.get("automatic_checks", {}).get(model, {}).items():
                counts = aggregates.setdefault(name, {"passed": 0, "total": 0})
                counts["passed"] += int(passed)
                counts["total"] += 1
        for counts in aggregates.values():
            counts["rate"] = counts["passed"] / counts["total"]
        result[model] = aggregates
    return result
