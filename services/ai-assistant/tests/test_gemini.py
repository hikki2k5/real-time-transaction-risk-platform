from dataclasses import replace
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest
from unittest.mock import Mock

from langchain_core.messages import AIMessage

from app.config import get_settings
from app.llm import GeminiAgent, AssistantProviderError
from app.retriever import KnowledgeBase
from app.schemas import AssistantQueryRequest
from app.semantic import SemanticKnowledgeBase
from app.tools import ToolResult


class GeminiTest(unittest.TestCase):
    def setUp(self):
        self.settings = get_settings()
        self.knowledge = KnowledgeBase(self.settings.knowledge_dir)
        self.tools = Mock()
        self.tools.get_transaction_audit.return_value = ToolResult(
            "get_transaction_audit", {"transaction_id": "tx-test"}, None, "no audit row found")

    def engine(self, responses):
        model = Mock()
        model.bind_tools.return_value.invoke.side_effect = responses
        return GeminiAgent(self.settings, self.knowledge, self.tools, "Cite evidence", model=model)

    def test_model_selects_audit_tool_and_usage_is_summed(self):
        engine = self.engine([
            AIMessage(content="", tool_calls=[{"name": "get_transaction_audit", "args": {"transaction_id": "tx-test"}, "id": "call1"}],
                      usage_metadata={"input_tokens": 20, "output_tokens": 5, "total_tokens": 25}),
            AIMessage(content="The audit is missing.", usage_metadata={"input_tokens": 30, "output_tokens": 10, "total_tokens": 40}),
        ])
        answer, docs, calls, usage = engine.answer(AssistantQueryRequest(question="Look up REVIEW", transaction_id="tx-test"), "Look up REVIEW")
        self.assertIn("missing", answer)
        self.assertEqual(usage, (50, 15))
        self.assertEqual(len(calls), 1)
        self.tools.get_transaction_audit.assert_called_once_with("tx-test")

    def test_model_cannot_lookup_an_unsupplied_id(self):
        engine = self.engine([
            AIMessage(content="", tool_calls=[{"name": "get_transaction_audit", "args": {"transaction_id": "tx-other"}, "id": "call1"}]),
            AIMessage(content="Access denied."),
        ])
        engine.answer(AssistantQueryRequest(question="Look up REVIEW", transaction_id="tx-test"), "Look up REVIEW")
        self.tools.get_transaction_audit.assert_not_called()

    def test_provider_error_is_not_replaced_by_offline_answer(self):
        engine = self.engine([RuntimeError("quota")])
        with self.assertRaises(AssistantProviderError):
            engine.answer(AssistantQueryRequest(question="Explain REVIEW"), "Explain REVIEW")

    def test_repeated_tool_calls_are_bounded(self):
        calls = [AIMessage(content="", tool_calls=[{"name": "get_transaction_audit", "args": {"transaction_id": "tx-test"}, "id": f"call{i}"}]) for i in range(5)]
        engine = self.engine(calls)
        with self.assertRaises(AssistantProviderError):
            engine.answer(AssistantQueryRequest(question="Explain REVIEW", transaction_id="tx-test"), "Explain REVIEW")
        self.assertEqual(self.tools.get_transaction_audit.call_count, 3)

    def test_semantic_index_is_reused_and_invalidated_on_document_change(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "policy.md").write_text("# Policy\n\nPayment held for review.")
            settings = replace(self.settings, knowledge_dir=root)
            embedder = Mock()
            embedder.embed_documents.return_value = [[1., 0.]]
            embedder.embed_query.return_value = [1., 0.]
            stored_versions = set()
            store = Mock()
            store.has_version.side_effect = lambda version, count: version in stored_versions
            store.put_version.side_effect = lambda version, chunks, vectors: stored_versions.add(version)
            store.search.return_value = [Mock(score=1.)]
            self.assertEqual(SemanticKnowledgeBase(settings, embedder, store).search("held")[0].score, 1.)
            SemanticKnowledgeBase(settings, embedder, store).search("review")
            self.assertEqual(embedder.embed_documents.call_count, 1)
            (root / "policy.md").write_text("# Policy\n\nPayment blocked.")
            SemanticKnowledgeBase(settings, embedder, store).search("blocked")
            self.assertEqual(embedder.embed_documents.call_count, 2)

    def test_embedding_model_and_dimensions_change_version(self):
        first = SemanticKnowledgeBase(self.settings, Mock(), Mock())
        second = SemanticKnowledgeBase(replace(self.settings, embedding_model="other"), Mock(), Mock())
        third = SemanticKnowledgeBase(replace(self.settings, embedding_dimensions=256), Mock(), Mock())
        self.assertNotEqual(first.version, second.version)
        self.assertNotEqual(first.version, third.version)

    def test_failed_insert_is_retried_instead_of_marking_index_ready(self):
        store = Mock()
        store.has_version.return_value = False
        store.put_version.side_effect = RuntimeError("database unavailable")
        embedder = Mock()
        knowledge = SemanticKnowledgeBase(self.settings, embedder, store)
        for attempt in range(2):
            with self.assertRaises(RuntimeError):
                knowledge.search("review")
        self.assertEqual(store.put_version.call_count, 2)

if __name__ == "__main__":
    unittest.main()
