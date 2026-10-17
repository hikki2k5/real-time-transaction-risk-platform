# Evidence QA: Colab Experiment

## What This Experiment Can Establish

This is a controlled synthetic evidence-reading experiment, not a production
fraud model, general Vietnamese assistant, or independent real-world benchmark.
The data has 480 rows from 40 independent fictional service/transaction scenarios:

| Split | Rows | Scenarios |
| --- | ---: | ---: |
| Train | 288 | 24 |
| Development | 96 | 8 |
| Test | 96 | 8 |

Each scenario has six tasks in English and Vietnamese: feature origin, audit
storage, audit processor, recorded decision, missing approver, and a quoted
injection instruction. Evidence is English. Most gold responses are short entity
answers with source IDs. This is deliberately narrower than conversational QA.
Target values, source IDs, evidence order and scenario identifiers vary. Relation
schemas and answer vocabularies are shared across splits; question templates and
scenarios are separate. Template and scenario variants are correlated, so the
96 test rows are not 96 independent real-world observations.

The generator and automated checks do not replace human review. Dataset status
is `NOT_HUMAN_REVIEWED`. Before training, inspect examples from every category
and language for wording, consistency and label correctness. Maintain an
independent manually authored test set for subsequent real-world claims.

## 1. Push These Files First

Push `research/data`, the new Python scripts, and the updated training script.
Never push `.env`, `.venv`, caches or generated `runs`. This experiment does not
need a Gemini key, database credentials, customer records or Drive authorization.

In Colab, select a GPU runtime. Run each block in a separate cell.

## 2. Update the Colab Checkout

If already cloned and no notebook-side tracked files were changed:

```python
%cd /content/real-time-transaction-risk-platform
!git pull --ff-only
!git rev-parse HEAD
!ls services/ai-assistant/research/data
```

For a fresh runtime, clone the repository first. Do not regenerate or edit the
test set after seeing its results. Use a new dataset version for substantive
data changes, and report that previous test exposure is a limitation.

## 3. Dependencies and GPU

These versions were used to verify the local tiny-model pipeline. Retain Colab's
GPU PyTorch build. TorchAO is not used by this ordinary LoRA experiment; an
incompatible preinstalled version previously blocked PEFT adapter injection.

```python
%pip uninstall -y torchao
%pip install "transformers==4.57.6" "peft==0.21.2"
```

After changing installed packages, restart the session, not delete the runtime.
Then:

```python
import torch
assert torch.cuda.is_available(), "Select a GPU runtime first"
print(torch.__version__, torch.cuda.get_device_name(0))
%cd /content/real-time-transaction-risk-platform
```

## 4. Inspect Data Before Training

```python
import json
from pathlib import Path
data = Path("services/ai-assistant/research/data/evidence_qa_v1.jsonl")
rows = [json.loads(line) for line in data.read_text().splitlines() if line.strip()]
print({split: sum(r["split"] == split for r in rows) for split in ("train", "dev", "test")})
# Review training examples first, without tuning from test answers.
for category in sorted({r["category"] for r in rows}):
    for language in ("en", "vi"):
        r = next(r for r in rows if r["split"] == "train" and r["category"] == category and r["language"] == language)
        print(json.dumps(r, ensure_ascii=False, indent=2))
```

## 5. Train and Evaluate Once

```python
!python services/ai-assistant/research/lora_experiment.py \
  --data services/ai-assistant/research/data/evidence_qa_v1.jsonl \
  --model HuggingFaceTB/SmolLM2-135M-Instruct \
  --output services/ai-assistant/research/runs/smollm2-evidence-v1 \
  --epochs 3 --learning-rate 0.0002 --rank 8 --generation-tokens 64
```

Training masks the prompt and learns only answer/EOS tokens. After each epoch,
response-token-weighted development loss selects the best adapter. The script
restores that adapter before generating paired base/adapter answers on test.
Base generation disables the adapter on the same frozen model. Both receive the
same prompt, evidence and deterministic generation budget. No test reference
is used for gradients or checkpoint selection. A lower dev loss is not proof
of factual accuracy. Existing output paths fail rather than overwrite artifacts.

## 6. Read the Results

```python
report_path = Path("services/ai-assistant/research/runs/smollm2-evidence-v1/comparison.json")
report = json.loads(report_path.read_text())
print(json.dumps(report["run"]["epochs_history"], indent=2))
print("Selected epoch:", report["run"]["selected_epoch"])
print(json.dumps(report["automatic_summary"], indent=2))
```

Automatic metrics are literal expected-value presence, citation-ID set match,
and refusal marker presence. A wrong sentence can still contain the right value
and citation. **These are string checks, not accuracy or groundedness scores.**
Do not select another model/epoch using these test results and then call the
same test untouched. Use development data to refine future experiments and
reserve an additional independent test set for a final claim.

For blinded manual inspection:

```python
!python services/ai-assistant/research/export_blind_review.py \
  --report services/ai-assistant/research/runs/smollm2-evidence-v1/comparison.json \
  --output services/ai-assistant/research/runs/smollm2-evidence-v1/blind-review
```

Give the reviewer only `review.jsonl`, not `PRIVATE_mapping.json`. Review factual
support, correct citations, and appropriate refusal across every task/language;
report the reviewed sample size and errors, not just a preferred example.

## 7. Preserve Artifacts

```python
import shutil
from google.colab import files
shutil.make_archive("/content/smollm2-evidence-v1", "zip",
                    "services/ai-assistant/research/runs/smollm2-evidence-v1")
files.download("/content/smollm2-evidence-v1.zip")
```

The results stay on your Colab runtime until downloaded. No model is automatically
deployed to the app. Do not change CV claims until the actual run, labels and
answer quality have been inspected. Even a successful run is a small controlled
LoRA experiment, not production fine-tuning or training an embedding/reranker.
