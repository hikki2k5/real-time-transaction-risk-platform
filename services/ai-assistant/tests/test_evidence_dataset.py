import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from build_evidence_dataset import build_rows, write_dataset
from lora_experiment import load_rows
from qa_checks import answer_checks, summarize_checks
from export_blind_review import export_review


class EvidenceDatasetTests(unittest.TestCase):
    def test_deterministic_balanced_split(self):
        rows = build_rows()
        self.assertEqual(rows, build_rows())
        self.assertEqual(len(rows), 480)
        self.assertEqual(sum(row["split"] == "train" for row in rows), 288)
        groups = {split: {row["group"] for row in rows if row["split"] == split}
                  for split in ("train", "dev", "test")}
        self.assertEqual([len(groups[s]) for s in groups], [24, 8, 8])
        self.assertFalse(groups["train"] & groups["dev"] or groups["train"] & groups["test"]
                         or groups["dev"] & groups["test"])
        self.assertEqual(sum(row["language"] == "vi" for row in rows), 240)

    def test_gold_values_and_sources_exist(self):
        for row in build_rows():
            self.assertTrue(all(answer_checks(row, row["answer"]).values()), row["id"])
            if row["expected_value"]:
                self.assertIn(row["expected_value"], row["context"])
                self.assertIn("[" + row["expected_citations"][0] + "]", row["context"])

    def test_dataset_is_loadable_and_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            manifest = write_dataset(path)
            self.assertEqual(len(load_rows(path)), 480)
            self.assertEqual(manifest["human_review_status"], "NOT_HUMAN_REVIEWED")
            with self.assertRaises(ValueError):
                write_dataset(path)

    def test_mixed_legacy_split_and_group_leakage_rejected(self):
        rows = build_rows()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "bad.jsonl"
            rows[0]["split"] = "eval"
            path.write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rows(path)

    def test_checks_do_not_accept_wrong_value_or_citation(self):
        row = {"expected_value": "S3", "expected_citations": ["cfg-1"]}
        self.assertEqual(answer_checks(row, "Lambda [other]"),
                         {"citation_ids_match": False, "expected_value_present": False})
        self.assertFalse(answer_checks(row, "S3 [cfg-1] [invented]")["citation_ids_match"])
        self.assertFalse(answer_checks(row, "S33 [cfg-1]")["expected_value_present"])

    def test_missing_data_and_summary_denominators(self):
        row = {"unanswerable": True, "expected_citations": []}
        checks = answer_checks(row, "Insufficient evidence.")
        summary = summarize_checks([{"automatic_checks": {"base": checks, "adapter": checks}}])
        self.assertEqual(summary["base"]["refusal_marker_present"], {"passed": 1, "total": 1, "rate": 1})

    def test_blind_review_keeps_mapping_separate(self):
        report = {"comparisons": [{"id": "a", "group": "g", "question": "q", "context": "c",
                                    "reference": "yes", "base": "yes", "adapter": "no"}]}
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "review"
            self.assertEqual(export_review(report, output), 1)
            row = json.loads((output / "review.jsonl").read_text(encoding="utf-8"))
            self.assertNotIn("base", row)
            self.assertNotIn("adapter", row)
            mapping = json.loads((output / "PRIVATE_mapping.json").read_text())["a"]
            self.assertEqual(row["A"], report["comparisons"][0][mapping["A"]])


if __name__ == "__main__":
    unittest.main()
