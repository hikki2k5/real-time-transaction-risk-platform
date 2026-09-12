import json
import os
import unittest

from app import build_audit_record, build_ingestion_record, lambda_handler


class FraudEventAuditorTest(unittest.TestCase):
    def test_builds_review_audit_from_direct_event(self):
        audit = build_audit_record(
            {
                "event_id": "event-001",
                "transaction_id": "tx-001",
                "user_id": "user-001",
                "fraud_probability": 0.55,
            }
        )

        self.assertEqual("tx-001", audit["transaction_id"])
        self.assertEqual("REVIEW", audit["decision"])
        self.assertEqual("MEDIUM", audit["risk_level"])
        self.assertTrue(audit["requires_manual_review"])

    def test_api_gateway_event_returns_http_response(self):
        response = lambda_handler(
            {
                "requestContext": {"requestId": "req-001"},
                "body": json.dumps(
                    {
                        "event_id": "event-002",
                        "transaction_id": "tx-002",
                        "user_id": "user-002",
                        "fraud_probability": 0.12,
                    }
                ),
            },
            None,
        )

        self.assertEqual(200, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual("APPROVE", body["audits"][0]["decision"])
        self.assertEqual("transaction_risk_events", body["stream_events"][0]["target_topic"])
        self.assertEqual("tx-002", body["stream_events"][0]["stream_key"])

    def test_sqs_event_extracts_records(self):
        response = lambda_handler(
            {
                "Records": [
                    {
                        "body": json.dumps(
                            {
                                "event_id": "event-003",
                                "transaction_id": "tx-003",
                                "user_id": "user-003",
                                "fraud_probability": 0.92,
                            }
                        )
                    }
                ]
            },
            None,
        )

        self.assertEqual("BLOCK", response["audits"][0]["decision"])
        self.assertEqual("HIGH", response["audits"][0]["risk_level"])

    def test_builds_kafka_ready_stream_event_with_configurable_topic(self):
        os.environ["TARGET_STREAM_TOPIC"] = "local_transaction_events"
        try:
            ingestion = build_ingestion_record(
                {
                    "event_id": "event-004",
                    "transaction_id": "tx-004",
                    "user_id": "user-004",
                    "fraud_probability": 0.41,
                }
            )
        finally:
            os.environ.pop("TARGET_STREAM_TOPIC", None)

        self.assertTrue(ingestion["valid"])
        self.assertEqual([], ingestion["errors"])
        self.assertEqual("local_transaction_events", ingestion["stream_event"]["target_topic"])
        self.assertEqual("tx-004", ingestion["stream_event"]["stream_key"])

    def test_api_gateway_event_rejects_invalid_risk_payload(self):
        response = lambda_handler(
            {
                "requestContext": {"requestId": "req-005"},
                "body": json.dumps(
                    {
                        "event_id": "event-005",
                        "transaction_id": "tx-005",
                        "user_id": "user-005",
                        "fraud_probability": 1.4,
                    }
                ),
            },
            None,
        )

        self.assertEqual(400, response["statusCode"])
        body = json.loads(response["body"])
        self.assertEqual([], body["stream_events"])
        self.assertIn("fraud_probability must be between 0 and 1", body["invalid_records"][0]["errors"])


if __name__ == "__main__":
    unittest.main()
