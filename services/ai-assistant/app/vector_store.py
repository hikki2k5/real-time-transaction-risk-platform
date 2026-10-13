from __future__ import annotations

import json
import math
from pathlib import Path

import psycopg2
from psycopg2.extras import execute_values

from app.retriever import DocumentChunk, SearchResult, tokenize


class PgVectorStore:
    def __init__(self, settings):
        self.settings = settings
        if not 1 <= settings.embedding_dimensions <= 2000:
            raise ValueError("AI_EMBEDDING_DIMENSIONS must be between 1 and 2000")

    def _connect(self):
        return psycopg2.connect(
            host=self.settings.postgres_host, port=self.settings.postgres_port,
            dbname=self.settings.postgres_db, user=self.settings.postgres_user,
            password=self.settings.postgres_password, sslmode=self.settings.postgres_sslmode,
            connect_timeout=5,
        )

    def initialize(self):
        migration = Path(__file__).resolve().parents[1] / "sql" / "001_vector_store.sql"
        connection = self._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute(migration.read_text(encoding="utf-8"))
        finally:
            connection.close()

    def has_version(self, version: str, chunk_count: int) -> bool:
        connection = self._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute("""
                        SELECT chunk_count FROM ai.knowledge_versions
                        WHERE collection = %s AND version = %s
                    """, (self.settings.vector_collection, version))
                    row = cursor.fetchone()
                    return row is not None and row[0] == chunk_count
        finally:
            connection.close()

    def _vector(self, values) -> str:
        values = [float(value) for value in values]
        if len(values) != self.settings.embedding_dimensions:
            raise ValueError("Embedding dimension mismatch")
        if not all(math.isfinite(value) for value in values) or not any(values):
            raise ValueError("Embedding must be finite and nonzero for cosine search")
        return json.dumps(values, allow_nan=False)

    def put_version(self, version: str, chunks: list[DocumentChunk], vectors: list[list[float]]):
        if not chunks or len(chunks) != len(vectors):
            raise ValueError("Each document chunk needs one embedding")
        rows = [(self.settings.vector_collection, version, chunk.doc_id, chunk.title,
                 chunk.text, self.settings.embedding_dimensions, self._vector(vector))
                for chunk, vector in zip(chunks, vectors)]
        connection = self._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute("SELECT pg_advisory_xact_lock(hashtext(%s))",
                                   (self.settings.vector_collection + ":" + version,))
                    cursor.execute("""
                        SELECT 1 FROM ai.knowledge_versions WHERE collection=%s AND version=%s
                    """, (self.settings.vector_collection, version))
                    if cursor.fetchone():
                        return
                    cursor.execute("""
                        INSERT INTO ai.knowledge_versions
                        (collection, version, embedding_model, dimensions, chunk_count)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (self.settings.vector_collection, version, self.settings.embedding_model,
                          self.settings.embedding_dimensions, len(chunks)))
                    execute_values(cursor, """
                        INSERT INTO ai.knowledge_chunks
                        (collection, version, doc_id, title, content, dimensions, embedding)
                        VALUES %s
                    """, rows, template="(%s, %s, %s, %s, %s, %s, %s::vector)")
        finally:
            connection.close()

    def search(self, version: str, vector, limit: int) -> list[SearchResult]:
        encoded = self._vector(vector)
        connection = self._connect()
        try:
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SET LOCAL statement_timeout = '10s'")
                    cursor.execute("""
                        SELECT doc_id, title, content, 1 - (embedding <=> %s::vector) AS score
                        FROM ai.knowledge_chunks
                        WHERE collection = %s AND version = %s
                        ORDER BY embedding <=> %s::vector, doc_id
                        LIMIT %s
                    """, (encoded, self.settings.vector_collection, version, encoded, max(1, min(limit, 20))))
                    return [SearchResult(DocumentChunk(doc_id, title, content, tokenize(content)), round(float(score), 4))
                            for doc_id, title, content, score in cursor.fetchall()]
        finally:
            connection.close()
