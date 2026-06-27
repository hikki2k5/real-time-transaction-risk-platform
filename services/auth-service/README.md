# auth-service

Local Spring Boot authentication service for portfolio demos.

It issues local JWT access tokens that `banking-core` can verify with the shared `BANKING_CORE_JWT_SECRET`.

## Endpoints

- `GET /health`
- `POST /v1/auth/register`
- `POST /v1/auth/login`
- `GET /v1/auth/me`
- `GET /swagger-ui.html`

## Configuration

```text
AUTH_SERVICE_PORT=8085
POSTGRES_HOST=localhost
POSTGRES_PORT=55432
POSTGRES_DB=transaction_risk
POSTGRES_USER=risk_user
POSTGRES_PASSWORD=risk_password
BANKING_CORE_JWT_SECRET=local-dev-jwt-secret-change-me-32chars
AUTH_JWT_ISSUER=local-auth-service
AUTH_ACCESS_TOKEN_TTL_MINUTES=60
```

This is a local JWT issuer for demonstration. In a production banking environment, services would normally integrate with an enterprise OAuth2/OIDC provider.

## Run Locally

```powershell
gradle test --no-daemon
gradle bootRun --no-daemon
```

## Example

```bash
curl -X POST http://localhost:8085/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "password123",
    "fullName": "Demo User"
  }'
```

Use the returned `access_token` against `banking-core` when `BANKING_CORE_SECURITY_ENABLED=true`:

```bash
curl -H "Authorization: Bearer <access_token>" http://localhost:8084/v1/internal/transactions
```
