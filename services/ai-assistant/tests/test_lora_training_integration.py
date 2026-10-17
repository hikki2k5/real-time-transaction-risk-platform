"""Opt-in actual tiny-model training; not a quality evaluation."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "research"))
from build_evidence_dataset import build_rows


@unittest.skipUnless(os.getenv("AI_RESEARCH_TRAINING_TEST") == "1", "Requires optional PyTorch/PEFT and model weights")
class LoraTrainingIntegrationTests(unittest.TestCase):
    def test_dev_checkpoint_and_test_comparison(self):
        rows = build_rows()
        fixture = [next(row for row in rows if row["split"] == split) for split in ("train", "dev", "test")]
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            data = directory / "data.jsonl"
            data.write_text("\n".join(json.dumps(row) for row in fixture), encoding="utf-8")
            output = directory / "run"
            result = subprocess.run([sys.executable, str(ROOT / "research/lora_experiment.py"),
                                     "--data", str(data), "--model", "sshleifer/tiny-gpt2",
                                     "--output", str(output), "--epochs", "2", "--generation-tokens", "8",
                                     "--allow-cpu"], capture_output=True, text=True, timeout=180)
            self.assertEqual(result.returncode, 0, result.stderr[-4000:])
            report = json.loads((output / "comparison.json").read_text(encoding="utf-8"))
            self.assertEqual(report["run"]["evaluation_split"], "test")
            history = report["run"]["epochs_history"]
            best = min(history, key=lambda epoch: epoch["dev_loss"])
            self.assertEqual(report["run"]["selected_epoch"], best["epoch"])
            self.assertEqual(len(report["run"]["training_losses"]), 2)
            self.assertEqual([row["id"] for row in report["comparisons"]], [fixture[2]["id"]])
            self.assertTrue((output / "adapter/adapter_model.safetensors").exists())
            self.assertEqual(report["automatic_summary"]["base"]["expected_value_present"]["total"], 1)


if __name__ == "__main__":
    unittest.main()
