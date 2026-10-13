from dataclasses import replace
import os
import unittest
from uuid import uuid4

from app.config import get_settings
from app.retriever import DocumentChunk
from app.vector_store import PgVectorStore


class VectorValidationTest(unittest.TestCase):
    def setUp(self):
        self.store = PgVectorStore(replace(get_settings(), embedding_dimensions=3))

    def test_invalid_vectors_are_rejected_before_database_access(self):
        for values in ([1, 2], [0, 0, 0], [float("nan"), 1, 0], [float("inf"), 1, 0]):
            with self.assertRaises(ValueError):
                self.store._vector(values)

    def test_chunk_count_mismatch_is_rejected(self):
        with self.assertRaises(ValueError):
            self.store.put_version("test", [DocumentChunk("id", "title", "text", set())], [])


@unittest.skipUnless(os.getenv("AI_PGVECTOR_INTEGRATION") == "1", "Enable against a dedicated pgvector test database")
class PgVectorIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.settings = replace(get_settings(), vector_collection="test-" + uuid4().hex, embedding_dimensions=3)
        self.store = PgVectorStore(self.settings)
        self.store.initialize()
        self.chunks = [DocumentChunk("a", "Review", "Review policy", set()),
                       DocumentChunk("b", "Cache", "Redis cache", set())]

    def tearDown(self):
        connection = self.store._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM ai.knowledge_chunks WHERE collection=%s", (self.settings.vector_collection,))
                    cursor.execute("DELETE FROM ai.knowledge_versions WHERE collection=%s", (self.settings.vector_collection,))
        finally:
            connection.close()

    def test_persistence_ranking_version_and_collection_isolation(self):
        self.store.put_version("v1", self.chunks, [[1, 0, 0], [0, 1, 0]])
        restarted = PgVectorStore(self.settings)
        self.assertTrue(restarted.has_version("v1", 2))
        self.assertFalse(restarted.has_version("v2", 2))
        result = restarted.search("v1", [1, 0, 0], 2)
        self.assertEqual([r.chunk.doc_id for r in result], ["a", "b"])
        self.assertAlmostEqual(result[0].score, 1.)
        # A duplicate snapshot must not overwrite already committed embeddings.
        restarted.put_version("v1", self.chunks, [[0, 1, 0], [1, 0, 0]])
        self.assertEqual(restarted.search("v1", [1, 0, 0], 1)[0].chunk.doc_id, "a")
        restarted.put_version("v2", [self.chunks[1]], [[1, 0, 0]])
        self.assertEqual([r.chunk.doc_id for r in restarted.search("v2", [1, 0, 0], 4)], ["b"])
        other = PgVectorStore(replace(self.settings, vector_collection="other-" + uuid4().hex))
        self.assertEqual(other.search("v1", [1, 0, 0], 4), [])

    def test_failed_snapshot_rolls_back_metadata_and_chunks(self):
        duplicates = [self.chunks[0], self.chunks[0]]
        with self.assertRaises(Exception):
            self.store.put_version("broken", duplicates, [[1, 0, 0], [0, 1, 0]])
        self.assertFalse(self.store.has_version("broken", 2))
        self.assertEqual(self.store.search("broken", [1, 0, 0], 4), [])

if __name__ == "__main__":
    unittest.main()
