import sys
from pathlib import Path
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "research"))
from retrieval import RetrievalExperiment, ranking_metrics, reciprocal_rank_fusion, tokens, unique_documents


class RetrievalMetricsTests(unittest.TestCase):
    def test_perfect_ranking(self):
        self.assertEqual(ranking_metrics(["a"], {"a": 1}),
                         {"recall@5": 1, "mrr@10": 1, "ndcg@10": 1})

    def test_miss_and_rank(self):
        self.assertEqual(ranking_metrics(["b"], {"a": 1})["mrr@10"], 0)
        self.assertEqual(ranking_metrics(["b", "a"], {"a": 1})["mrr@10"], .5)

    def test_duplicates_rejected_and_chunks_deduplicated(self):
        with self.assertRaises(ValueError):
            ranking_metrics(["a", "a"], {"a": 1})
        self.assertEqual(unique_documents(["a#2", "a#1", "b#1"]), ["a", "b"])

    def test_fusion_and_unicode(self):
        self.assertEqual(reciprocal_rank_fusion([[0, 1], [1, 0]])[0], 0)
        self.assertIn("giao", tokens("Giao dich"))
        self.assertEqual(tokens("\u0110I\u1ec2M"), ["\u0111i\u1ec3m"])

    def test_hybrid_and_reranking_wiring_with_fake_models(self):
        try:
            import numpy as np
            import rank_bm25
        except ImportError:
            self.skipTest("Optional rank-bm25/numpy research dependencies not installed")

        class FakeDense:
            def __init__(self, name):
                pass

            def encode(self, text, **kwargs):
                return np.eye(3) if isinstance(text, list) else np.array([0., 1., 0.])

        class FakeReranker:
            def __init__(self, name):
                pass

            def predict(self, pairs):
                return [10. if "third" in text else 0. for query, text in pairs]

        chunks = [SimpleNamespace(doc_id=f"{name}#1", text=text) for name, text in
                  [("a", "fraud review"), ("b", "feature cache"), ("c", "third document")]]
        with patch.dict(sys.modules, {"sentence_transformers": SimpleNamespace(
                SentenceTransformer=FakeDense, CrossEncoder=FakeReranker)}):
            rankings = RetrievalExperiment(chunks, "fake", "fake").rank("fraud review")
        self.assertEqual(set(rankings), {"bm25", "dense", "hybrid", "hybrid_reranked"})
        self.assertEqual(rankings["dense"][0], "b")
        self.assertEqual(rankings["bm25"][0], "a")
        self.assertEqual(rankings["hybrid_reranked"][0], "c")


if __name__ == "__main__":
    unittest.main()
