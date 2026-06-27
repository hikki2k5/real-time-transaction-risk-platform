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

## TODO

- TODO Future: Add real account balance and saved beneficiary APIs.
- TODO Future: Replace local demo auth with hosted OAuth2/OIDC for deployed demos.
