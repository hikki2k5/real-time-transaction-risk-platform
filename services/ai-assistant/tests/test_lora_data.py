import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from lora_experiment import encode_row, load_rows


class FakeTokenizer:
    eos_token_id = 99

    def __call__(self, text, **kwargs):
        return {"input_ids": list(range(len(text)))}


class LoraDataTests(unittest.TestCase):
    def test_smoke_split(self):
        rows = load_rows(Path(__file__).resolve().parents[1] / "research/sft_smoke.jsonl")
        self.assertEqual(len(rows), 6)

    def test_response_only_labels_and_overflow(self):
        row = {"id": "a", "question": "q", "context": "c", "answer": "yes"}
        ids, labels = encode_row(row, FakeTokenizer(), 1000)
        self.assertEqual(len(ids), len(labels))
        self.assertEqual(labels[-4:], [0, 1, 2, 99])
        self.assertTrue(all(label == -100 for label in labels[:-4]))
        with self.assertRaises(ValueError):
            encode_row(row, FakeTokenizer(), 16)

    def test_group_leakage_rejected(self):
        rows = [{"id": str(i), "group": "same", "split": split, "question": str(i),
                 "context": "evidence", "answer": "answer"} for i, split in enumerate(["train", "eval"])]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "data.jsonl"
            path.write_text("\n".join(map(json.dumps, rows)), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_rows(path)


if __name__ == "__main__":
    unittest.main()
