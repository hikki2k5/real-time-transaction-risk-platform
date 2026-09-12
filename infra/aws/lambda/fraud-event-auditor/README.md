# Fraud Event Auditor Lambda Prototype

Local AWS serverless prototype for transaction fraud audit and ingestion events.

This module demonstrates AWS Lambda/SAM development without requiring an AWS deployment. It is designed to be run locally and is safe for a free portfolio workflow.

## Purpose

The handler accepts a transaction risk decision event from one of these shapes:

- API Gateway style request
- EventBridge style event
- SQS style batch record
- direct Lambda invoke payload

It validates the core event fields, returns normalized audit records, and also
builds Kafka-ready stream events that can be connected to MSK/Kafka, Kinesis,
EventBridge, or SQS in a real AWS deployment.

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

## Cost Note

This prototype does not create AWS resources by itself. Running unit tests or `sam local invoke` is local-only and should not incur AWS cost.

Do not run `sam deploy` unless you intentionally want to create AWS resources and understand the account cost implications.

## Future AWS Integration

A production AWS design could connect this Lambda to:

- API Gateway for synchronous audit ingestion
- EventBridge for fraud decision events
- SQS for retryable asynchronous processing
- MSK/Kafka or Kinesis for streaming validated events into the data platform
- DynamoDB or S3 for durable audit storage
- CloudWatch for operational logs and metrics

Those cloud resources are intentionally not provisioned in this local-first project.
