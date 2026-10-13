# Risk Platform Dashboard

Next.js customer-facing UI for the local fraud detection platform.

## Features

- Register and login through `auth-service`.
- Store the JWT access token in browser local storage for local demos.
- Show login/register first, then unlock the transaction page after auth.
- Use login/register tabs instead of exposing technical service configuration.
- Let a user submit normal payment details such as account, amount, currency, merchant, transaction type, and location.
- Capture payee name and payment reference for a more realistic payment flow.
- Show a review step before final submission.
- Load account options from `banking-core` `GET /v1/accounts`.
- Call `banking-core` `POST /internal/transactions`.
- Show a plain transaction result: approved, review needed, blocked, or error. Internal fraud scores are not shown to the customer.
- Show recent transaction history from `banking-core` `GET /v1/transactions`.
- AI Assistant tab with transaction selection, cited answers, send/stop, retry and clear chat.
- Server route verifies login via `auth-service` `/v1/auth/me` and forwards the
  verified user ID to scope assistant database tools to that customer's records.

## Local Run

```sh
cd services/dashboard
cp .env.example .env.local
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

The backend services must allow the dashboard origin through `DASHBOARD_ALLOWED_ORIGINS`.

## v0/Vercel Notes

The frontend can be deployed as a normal Next.js app. A deployed browser app cannot call `localhost` APIs on your laptop, so set public backend URLs when the APIs are deployed:

```text
NEXT_PUBLIC_AUTH_API_BASE_URL=https://...
NEXT_PUBLIC_BANKING_API_BASE_URL=https://...
NEXT_PUBLIC_FRAUD_API_BASE_URL=https://...
```

For local portfolio demos, run the dashboard locally and keep the API URLs as `localhost`.

## AI Assistant on Vercel

Deploy the Next.js application with Root Directory `services/dashboard`.
Keep existing public auth/banking API URLs. Add these server-only environment
variables in Vercel for each deployment environment:

```text
AUTH_API_BASE_URL=https://YOUR_AUTH_SERVICE
AI_ASSISTANT_BASE_URL=https://YOUR_AI_ASSISTANT_SERVICE
AI_ASSISTANT_API_TOKEN=THE_SAME_OPERATOR_TOKEN_AS_THE_ASSISTANT_BACKEND
```

Use base URLs without endpoint suffixes. Never prefix the operator token with
`NEXT_PUBLIC_`; never put a Gemini key in frontend variables. Gemini keys belong
on the assistant backend. Redeploy Vercel after changing environment variables.

Flow: browser JWT -> `/api/assistant` -> verify `/v1/auth/me` -> operator token
plus verified user ID -> assistant -> user-scoped SQL tools -> answer/citations.
The browser cannot choose a different user ID. Deploy the updated assistant
backend too: its transaction-audit tool must include the user ownership filter.
Keep Gemini mode authentication enabled. Do not expose an offline unauthenticated
assistant directly to the internet. Missing assistant configuration produces a
retryable unavailable message; the UI never fabricates a model answer.

Assistant deployment requires Gemini credentials, a pgvector-capable PostgreSQL
database and vector schema migration; see `../ai-assistant/README.md`. The
route allows up to 120 seconds; check the duration allowed by your Vercel plan.
Chat currently displays separate questions, not model conversational memory.

Verify after deployment: login, select AI Assistant, ask a policy question,
then select one of your transactions and ask why it received its decision.
An expired login must return 401; an unavailable assistant must show Retry.

## Verification

```sh
npm test
npm run build
```

Proxy tests use Node 22.18+ or Node 24 for native TypeScript stripping. Browser
fixtures in `tests/mock-services.mjs` are local test data only and are never used
by production application routes.

## TODO

- TODO Future: Add real account balance and saved beneficiary APIs.
- TODO Future: Replace local demo auth with hosted OAuth2/OIDC for deployed demos.
