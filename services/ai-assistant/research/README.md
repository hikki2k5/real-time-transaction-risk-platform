# Retrieval and LoRA Experiments

For the larger controlled bilingual dataset, train/dev/test selection, and
step-by-step GPU commands, see [COLAB_EVIDENCE_SFT.md](COLAB_EVIDENCE_SFT.md).
The committed `data/evidence_qa_v1.jsonl` contains 480 synthetic rows across
40 scenarios, not 480 independent manually reviewed real-world questions.
The manifest records generation provenance and limitations.

Research utilities are isolated from the deployed Gemini API. They neither
replace the production retriever nor change authentication. No Gemini key,
customer database, or paid hosted GPU is needed for the local smoke runs.

## Setup

From the repository root (PowerShell):

```powershell
py -m venv services/ai-assistant/research/.venv
services/ai-assistant/research/.venv/Scripts/python.exe -m pip install -r services/ai-assistant/research/requirements.txt
```

Install a PyTorch build matching your machine using the official PyTorch
instructions if GPU support is needed. Model weights are downloaded separately
on first use; review their model cards, licenses, memory needs and provenance.
Do not add research dependencies to the Render Docker image.

## Retrieval Baselines

BM25 only needs `rank-bm25==0.2.2` and NumPy:

From the repository root:

```powershell
services/ai-assistant/research/.venv/Scripts/python.exe services/ai-assistant/research/benchmark_retrieval.py
services/ai-assistant/research/.venv/Scripts/python.exe services/ai-assistant/research/benchmark_retrieval.py --dense-model sentence-transformers/all-MiniLM-L6-v2 --reranker-model cross-encoder/ms-marco-MiniLM-L6-v2 --output services/ai-assistant/logs/retrieval_hybrid.json
```

The second command compares BM25, local dense cosine search, reciprocal-rank
fusion (RRF), and pretrained cross-encoder reranking on identical queries.
These local dense embeddings are not the production Gemini embeddings: this
is an offline architecture comparison, not a migration or speed comparison
against pgvector/Gemini. Reranking uses pretrained weights, not reranker training.
The English example models are not a claim of Vietnamese retrieval quality.

Local model verification status: the MiniLM dense/reranker run could not load
the dense model because Windows returned error 1455 (paging file too small).
No real dense/hybrid/reranked scores are reported yet. Unit tests use fake dense
and reranker models to exercise pipeline wiring; this does not verify pretrained
model quality or successful model loading. BM25 alone was executed with real
corpus text. Repeat the full command on a machine with sufficient RAM/GPU.

Metrics are **document-level** Recall@5, MRR@10 and binary NDCG@10, after
deduplicating chunk results. Existing `expected_doc` labels are used directly.
No chunk-level relevance labels are invented. The report fingerprints query and
corpus content and includes raw rankings. Combined pipeline latency excludes
model loading but includes every enabled method; do not compare it as individual
method speed. Scores include all documents even for zero lexical overlap.

### Initial Measured Smoke Baseline

BM25 on the existing 20 labeled English questions / 5 documents / 5 chunks:

| Metric | Measured value |
| --- | ---: |
| Recall@5 | 1.0000 |
| MRR@10 | 0.9500 |
| NDCG@10 | 0.9631 |

Recall@5 is trivial for five documents. These authored questions already reflect
the corpus vocabulary; results do not measure held-out generalization or scale.
Do not present these as production accuracy or optimization percentages on a CV.

Before making quality claims, curate a larger corpus and independent bilingual
queries with graded relevance judgments, keep scenario/paraphrase families in
the same split, tune on development data, and freeze a separate test set.

## Response-Only LoRA SFT

Each JSONL row needs `id`, `group`, `split`, `question`, `context`, `answer`.
Use `train` and `eval` splits. Group by source/scenario, not arbitrary row ID;
paraphrases of the same scenario must stay together. The loader rejects overlap
and exact duplicate question/context pairs, but cannot detect semantic leakage.
Training labels mask the prompt with -100; only answer tokens and EOS contribute
to the gradient. Oversized examples fail instead of silently truncating evidence.

`sft_smoke.jsonl` contains six manually authored synthetic plumbing fixtures:
four training rows and two held-out scenarios. It is **not a sufficient training
dataset** or a fraud-quality benchmark. No customer records are included.

Explicit CPU smoke run (downloads the selected base model):

```powershell
services/ai-assistant/research/.venv/Scripts/python.exe services/ai-assistant/research/lora_experiment.py --data services/ai-assistant/research/sft_smoke.jsonl --model HuggingFaceTB/SmolLM2-135M-Instruct --output services/ai-assistant/research/runs/smoke --allow-cpu
```

### Verified Local Training Status

The 135M example could not load on the current machine: PyTorch reported CPU
allocation failure before training. A smaller **plumbing-only** run completed:

```powershell
services/ai-assistant/research/.venv/Scripts/python.exe services/ai-assistant/research/lora_experiment.py --data services/ai-assistant/research/sft_smoke.jsonl --model sshleifer/tiny-gpt2 --output services/ai-assistant/research/runs/tiny-smoke --allow-cpu
```

It trained 512 adapter parameters on four synthetic examples for one epoch,
saved `adapter_model.safetensors`, and generated paired outputs on two held-out
scenarios. Both base and adapter produced repetitive, unsupported text. There
is **no measured answer-quality improvement**. This verifies training/checkpoint/
comparison wiring only, not useful domain adaptation or deep PyTorch experience.
Use a new output directory when repeating a run. Artifacts are ignored by Git.

For meaningful experiments, replace the fixtures with reviewed licensed data
and use an appropriate GPU/model. Omit `--allow-cpu` to require CUDA. Optional
`--mlflow-uri file:///ABSOLUTE/PATH/mlruns` logs configuration, train loss and the
comparison report. No experiment is sent to an external tracker by default.

Outputs contain adapter weights, tokenizer, dataset hash, seed, base model
commit when available, hyperparameters, trainable parameter count, losses,
training duration, peak CUDA allocation when applicable, and paired deterministic
base/adapter answers on the same eval prompts. Base evaluation disables the
adapter on the same frozen weights; eval references never enter training.
Manually blind-review factual support, citation correctness, refusal when evidence
is missing, and language before reporting any quality improvement. Loss decrease
alone is not improvement in answer quality. This is LoRA, **not QLoRA or DPO**.

## Verification

```powershell
py -m unittest discover -s services/ai-assistant/tests -p test_retrieval_research.py
py -m unittest discover -s services/ai-assistant/tests -p test_lora_data.py
```

These lightweight tests check metric correctness, ranking deduplication, RRF,
Unicode tokenization, response-only loss masking, length limits and split leakage.
They do not substitute for running pretrained models or a training experiment.

References: [PEFT](https://huggingface.co/docs/peft/quicktour),
[Sentence Transformers](https://www.sbert.net/docs/package_reference/cross_encoder/model.html).
