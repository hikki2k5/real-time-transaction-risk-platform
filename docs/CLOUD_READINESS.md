# Cloud Readiness

This project currently runs locally and does not require AWS, Azure, Snowflake, or paid cloud services.

The design can be mapped to managed cloud services later:

- Stateless services: ECS, EKS, AKS, or Azure Container Apps.
- Transaction database: RDS Postgres or Azure Database for PostgreSQL.
- Online cache: ElastiCache Redis or Azure Cache for Redis.
- Streaming: MSK, Confluent Cloud, or Event Hubs with Kafka API.
- Data lake: S3 or Azure Data Lake Storage.
- Warehouse: Snowflake, Redshift, or Azure Synapse.
- Secrets: AWS Secrets Manager, SSM Parameter Store, or Azure Key Vault.
- Observability: CloudWatch, Azure Monitor, OpenTelemetry, and centralized log aggregation.
- FaaS: AWS Lambda or Azure Functions for small async jobs and operational automations.

## Backend Notes

- `banking-core` is configured through environment variables so it can move from local Docker Compose to container platforms.
- `fraud-decision-api` uses Redis as a local online feature cache; managed Redis would be used in a cloud deployment.
- JWT resource-server support can be enabled with `BANKING_CORE_SECURITY_ENABLED=true`.
- Docker and kind manifests are local deployment examples, not production infrastructure.
- A production deployment would need managed secrets, TLS, ingress, autoscaling metrics, real identity provider integration, and stricter network policies.

## TODO

- TODO Future: Add Terraform modules for cloud infrastructure.
- TODO Future: Add EKS/ECS deployment examples.
- TODO Future: Replace local JWT HMAC configuration with an OAuth2/OIDC provider such as Keycloak, Entra ID, or Cognito.
