# Fraud Investigation AI Assistant

Optional offline BM25/dense/hybrid retrieval experiments, cross-encoder reranking,
and response-only LoRA SFT are documented in [research/README.md](research/README.md).
These are separate from the deployed Gemini pipeline; smoke results are not
production-quality or large-scale retrieval claims.

Gemini RAG and LangGraph tool-calling assistant for the transaction risk platform.

This service is intentionally offline-first for portfolio use: it uses a small
deterministic retrieval and answer engine by default, so tests and demos do not
require a paid model API key. The interfaces are shaped like a production AI
service: prompts are versioned, tools are explicit, safety checks are tested,
and every query logs latency, retrieval IDs, tool calls, token estimates, and
estimated cost.

## What It Demonstrates

- RAG ingestion, chunking, indexing, retrieval, and cited answers.
- Agent-style tool selection for transaction audit lookups.
- Prompt versioning in `prompts/fraud_investigation_v1.md`.
- Safety defaults for prompt-injection attempts and PII redaction.
- Evaluation with retrieval hit rate, tool-call accuracy, and safety checks.
- AI observability logs with prompt version, latency, token estimates, cost,
  retrieved document IDs, and tool calls.

## Run Locally

```sh
cd services/ai-assistant
py -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010
```

Health:

```sh
curl http://localhost:8010/health
```

Ask a question:

```sh
curl -X POST http://localhost:8010/v1/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Why would a transaction be marked REVIEW?"}'
```

Ask with a tool call:

```sh
curl -X POST http://localhost:8010/v1/assistant/query \
  -H "Content-Type: application/json" \
  -d '{"question":"Why was transaction tx-s3-001 marked review?","transaction_id":"tx-s3-001"}'
```

## Run Tests

```sh
cd services/ai-assistant
py -m unittest discover -s tests
```

## Run Evals

```sh
py evals/run_assistant_eval.py
```

Expected output includes:

- `retrieval_hit_rate`
- `tool_call_accuracy`
- `pii_redaction_pass_rate`
- `prompt_injection_block_rate`

## Gemini Mode (Windows)

From this service directory:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit the ignored `.env` with a fresh `GEMINI_API_KEY`, a random
`AI_ASSISTANT_API_TOKEN`, and database settings. Do not commit or share keys.
Select a model available to your account with `GEMINI_MODEL`.

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8010
```

The Gemini endpoint requires operator authentication:

```powershell
$headers = @{ Authorization = 'Bearer YOUR_OPERATOR_TOKEN' }
$body = @{ question = 'Why can a transaction be marked REVIEW?' } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8010/v1/assistant/query -Method Post -Headers $headers -ContentType application/json -Body $body
```

This is an operator API: its shared bearer token grants audit access and must
remain server-side, never in `NEXT_PUBLIC_*`. Customer-facing integration needs
verified JWT identity and ownership checks. The dashboard server route now
verifies `/v1/auth/me` and passes the verified `user_id`; audit SQL applies that
ownership filter. Direct operator requests without `user_id` retain operator
access. Never let a browser call this endpoint using the operator token.
Audit questions need an explicit
`transaction_id`; recent-history queries need `user_id`. Model-invented IDs
are denied. Database tools use read-only transactions and five-second limits.

Gemini document embeddings are stored in PostgreSQL + pgvector under
`ai.knowledge_chunks`, alongside document IDs, titles, text and corpus version.
`ai.knowledge_versions` records complete snapshots. The version hashes document
content, embedding model and dimension (768 by default); restarts reuse vectors,
and modified documents create a new snapshot without overwriting existing data.
Questions use pgvector's cosine-distance operator `<=>`. For this small corpus,
search is exact; there is no approximate HNSW index. The first query indexes
documents and can be slower. LangGraph
runs at most four model rounds, selecting search or read-only database tools.
Provider failures are errors; they never silently return an offline answer.

## Prepare pgvector

The Compose Postgres image is `pgvector/pgvector:pg16`, preserving the existing
`postgres_data` volume and PostgreSQL major version. From the repository root:

```powershell
docker compose -f infra/docker-compose.yml --env-file .env up -d postgres
```

Fresh databases run the vector migration automatically. For an existing volume
or hosted database, from this service directory run the migration explicitly:

```powershell
.\.venv\Scripts\python.exe -m dotenv -f .env run -- .\.venv\Scripts\python.exe scripts/init_vector_store.py
```

Database integration tests run only when explicitly enabled against a dedicated
test database (set its `POSTGRES_*` variables first):

```powershell
$env:AI_PGVECTOR_INTEGRATION = '1'
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_vector_store.py -v
```

They verify persisted vectors after recreating the store, cosine ranking,
collection/version isolation, duplicate ingestion and transaction rollback.

The database must support pgvector. Migration needs permission to create the
`vector` extension/schema/tables; after migration runtime needs SELECT/INSERT
on the `ai` tables. Set `POSTGRES_SSLMODE=require` for hosts requiring TLS.
Do not run `docker compose down -v`: that would delete project data.
No file-based vector cache or scikit-learn search is used in Gemini mode.

Inspect persisted vectors:

```sql
SELECT collection, version, doc_id, vector_dims(embedding)
FROM ai.knowledge_chunks;
```

## Gemini Evaluation

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m dotenv -f .env run -- .\.venv\Scripts\python.exe evals/run_assistant_eval.py
```

The 32-case eval writes `logs/eval_report.json`: retrieval hit rate, answer term
checks, expected tool calls, basic safety, error count and p50/p95 latency.
Live eval consumes API quota. Unit tests use mocked models/embeddings and do
not demonstrate live Gemini quality. Term checks are regression smoke checks,
not semantic-quality or groundedness metrics. Review generated claims and
citations manually before reporting quality on a CV.

Traces record actual provider-reported chat token usage. Cost estimates depend
on configured prices and exclude embeddings; zero prices mean unconfigured
rates, not guaranteed free usage. Citations list retrieved evidence and do not
guarantee generated claims are supported. Pattern-based safety is a baseline;
use synthetic data. `/health` does not probe Gemini or PostgreSQL.

## Measure the Deployed Service

From the repository root, no local database or Gemini key is needed:

```powershell
py services/ai-assistant/evals/measure_deployed_assistant.py --url https://risk-platform-ai-assistant.onrender.com --repeat 3 --output services/ai-assistant/logs/deployed_baseline.json
```

Enter the Render operator token at the hidden prompt (or set
`AI_ASSISTANT_API_TOKEN` privately). This makes one warmup and 96 measured real
requests with the default 32-case suite, sequentially with a two-second gap.
It consumes Gemini API quota. API errors count against success and check rates;
authentication/quota failures stop the run. Reports contain answers/tool data,
so keep them private and ignored. Use synthetic audit IDs in eval cases.

Report regular-query p50/p95 separately from cheap guardrail refusals. The
source-coverage and keyword tests are smoke checks, not answer groundedness;
manually review answers before stating quality claims. Remote measurements
include laptop-to-Render network time and exclude the Vercel/auth route.

After a specific optimization, rerun the exact command/workload with a new
output filename and `--baseline services/ai-assistant/logs/deployed_baseline.json`.
The report checks workload/model compatibility before calculating measured
latency/input-token differences. Repeat runs and preserve answer quality;
differences between an idle/cold service and a warm service do not by themselves
prove code optimization. Existing Redis/idempotency measurements are separate
backend results and must not be relabeled as AI improvements.

## Render Deployment

Use the Dockerfile with this service as its build context and port 8010. Set
`AI_ASSISTANT_PROVIDER=gemini`, `GEMINI_API_KEY`, `GEMINI_MODEL`,
`AI_EMBEDDING_MODEL`, `AI_ASSISTANT_API_TOKEN` and `POSTGRES_*` on the host.
Docker Compose passes these from the root `.env`. Logs should be shipped to
CloudWatch or a tracing platform, and
secrets/model API keys should come from AWS Secrets Manager or SSM Parameter
Store rather than local `.env` files.

References: https://ai.google.dev/gemini-api/docs/function-calling,
https://ai.google.dev/gemini-api/docs/embeddings,
https://docs.langchain.com/oss/python/langgraph/overview,
https://github.com/pgvector/pgvector.
