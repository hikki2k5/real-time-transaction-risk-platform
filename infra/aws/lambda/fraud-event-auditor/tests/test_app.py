import json
import unittest

from app import build_audit_record, lambda_handler


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


if __name__ == "__main__":
    unittest.main()
