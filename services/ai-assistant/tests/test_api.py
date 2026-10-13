from dataclasses import replace
import unittest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.config import get_settings
from app.llm import AssistantProviderError
from app.main import create_app


class ApiTest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(create_app())
        self.settings = replace(get_settings(), provider="gemini", api_token="test-operator-token")

    def test_unauthenticated_request_never_initializes_provider(self):
        with patch("app.main.get_settings", return_value=self.settings), patch("app.main.get_assistant") as assistant:
            response = self.client.post("/v1/assistant/query", json={"question": "Explain REVIEW"})
        self.assertEqual(response.status_code, 401)
        assistant.assert_not_called()

    def test_missing_operator_token_fails_closed(self):
        with patch("app.main.get_settings", return_value=replace(self.settings, api_token="")):
            response = self.client.post("/v1/assistant/query", json={"question": "Explain REVIEW"})
        self.assertEqual(response.status_code, 503)

    def test_provider_error_response_does_not_expose_exception_text(self):
        assistant = Mock()
        assistant.answer.side_effect = AssistantProviderError("private-provider-detail")
        with patch("app.main.get_settings", return_value=self.settings), patch("app.main.get_assistant", return_value=assistant):
            response = self.client.post("/v1/assistant/query", json={"question": "Explain REVIEW"},
                                        headers={"Authorization": "Bearer test-operator-token"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("private-provider-detail", response.text)

if __name__ == "__main__":
    unittest.main()
