# Fraud Event Auditor Lambda Prototype

AWS serverless prototype for transaction fraud audit and ingestion events.

This module demonstrates AWS Lambda/SAM development for a small portfolio-friendly deployment. It can be tested locally, or deployed to API Gateway, Lambda, and S3.

## Purpose

The handler accepts a transaction risk decision event from one of these shapes:

- API Gateway style request
- EventBridge style event
- SQS style batch record
- direct Lambda invoke payload

It validates the core event fields, returns normalized audit records, writes
valid audit records to S3 when deployed with SAM, and also builds Kafka-ready
stream events that can be connected to MSK/Kafka, Kinesis, EventBridge, or SQS.

Required fields:

- `event_id`
- `transaction_id`
- `user_id`
- `fraud_probability`

Audit records contain:

- `transaction_id`
- `user_id`
- `fraud_probability`
- `risk_level`
- `decision`
- `requires_manual_review`

Stream events contain:

- `target_topic`
- `stream_key`
- `payload`

Set `TARGET_STREAM_TOPIC` to override the default local topic name,
`transaction_risk_events`.

S3 output uses:

- `AUDIT_BUCKET`
- `AUDIT_PREFIX`, defaulting to `raw/fraud-audit`

When `AUDIT_BUCKET` is not set, the handler remains side-effect free and only
returns the normalized response.

## Run Tests

From the repository root:

```sh
make serverless-test
```

Or directly:

```sh
cd infra/aws/lambda/fraud-event-auditor
py -m unittest discover -s tests
```

## Run With AWS SAM Locally

AWS SAM CLI is optional. It is only needed if you want to emulate Lambda locally.

```sh
cd infra/aws/lambda/fraud-event-auditor
sam local invoke FraudEventAuditorFunction -e events/api-gateway-transaction.json
sam local invoke FraudEventAuditorFunction -e events/eventbridge-transaction.json
sam local invoke FraudEventAuditorFunction -e events/sqs-transaction.json
```

## Deploy With AWS SAM

```sh
cd infra/aws/lambda/fraud-event-auditor
sam build
sam deploy --guided
```

The SAM template provisions:

- API Gateway `POST /fraud-audit`
- Lambda `fraud-event-auditor`
- encrypted S3 bucket for normalized audit JSON records
- Lambda permission to write objects to that bucket

## Cost Note

Running unit tests or `sam local invoke` is local-only and should not incur AWS cost.

Do not run `sam deploy` unless you intentionally want to create AWS resources and understand the account cost implications.

## Future AWS Integration

A production AWS design could connect this Lambda to:

- API Gateway for synchronous audit ingestion
- EventBridge for fraud decision events
- SQS for retryable asynchronous processing
- MSK/Kafka or Kinesis for streaming validated events into the data platform
- CloudWatch for operational logs and metrics

The current SAM stack keeps the cloud scope intentionally small: API Gateway,
Lambda, and S3 only.
