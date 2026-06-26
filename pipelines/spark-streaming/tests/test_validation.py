import unittest

from transaction_streaming_job import error_reason_for_payload, validate_transaction_payload


class TransactionValidationTest(unittest.TestCase):
    def test_valid_payload_has_no_errors(self):
        payload = valid_payload()

        self.assertEqual([], validate_transaction_payload(payload))

    def test_required_fields_are_validated(self):
        payload = valid_payload()
        payload["user_id"] = ""
        payload.pop("event_timestamp")

        errors = validate_transaction_payload(payload)

        self.assertIn("user_id is required", errors)
        self.assertIn("event_timestamp is required", errors)

    def test_amount_must_be_positive(self):
        payload = valid_payload()
        payload["amount"] = "0"

        self.assertIn("amount must be greater than 0", validate_transaction_payload(payload))

    def test_allowed_values_are_validated(self):
        payload = valid_payload()
        payload["currency"] = "EUR"
        payload["transaction_type"] = "CRYPTO_PURCHASE"
        payload["channel"] = "KIOSK"

        errors = validate_transaction_payload(payload)

        self.assertIn("currency must be one of AUD, VND, USD", errors)
        self.assertIn(
            "transaction_type must be one of CARD_PAYMENT, ATM_WITHDRAWAL, TRANSFER, LOAN_REPAYMENT",
            errors,
        )
        self.assertIn("channel must be one of MOBILE, WEB, ATM, BRANCH", errors)

    def test_event_timestamp_must_be_iso_8601(self):
        payload = valid_payload()
        payload["event_timestamp"] = "23-06-2026"

        self.assertIn("event_timestamp must be an ISO-8601 timestamp", validate_transaction_payload(payload))

    def test_malformed_json_gets_error_reason(self):
        reason = error_reason_for_payload("{bad-json")

        self.assertTrue(reason.startswith("invalid_json"))


def valid_payload():
    return {
        "event_id": "event-1",
        "transaction_id": "transaction-1",
        "user_id": "user-1",
        "account_id": "acct-1",
        "amount": "42.50",
        "currency": "AUD",
        "merchant_category": "GROCERY",
        "transaction_type": "CARD_PAYMENT",
        "channel": "MOBILE",
        "country": "AU",
        "city": "Sydney",
        "status": "PENDING",
        "event_timestamp": "2026-06-23T10:15:30Z",
        "ingestion_timestamp": "2026-06-23T10:15:31Z",
    }


if __name__ == "__main__":
    unittest.main()

