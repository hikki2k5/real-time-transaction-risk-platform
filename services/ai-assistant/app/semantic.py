from __future__ import annotations

import hashlib
import json
from threading import Lock

from app.retriever import KnowledgeBase, SearchResult
from app.vector_store import PgVectorStore


class SemanticKnowledgeBase(KnowledgeBase):
    """Persist document vectors in pgvector; embed queries on demand."""

    def __init__(self, settings, embedder, store=None):
        super().__init__(settings.knowledge_dir)
        self.settings = settings
        self.embedder = embedder
        self.store = store if store is not None else PgVectorStore(settings)
        self._ready = False
        self.version = hashlib.sha256(json.dumps(
            [settings.embedding_model, settings.embedding_dimensions,
             [(c.doc_id, c.text) for c in self.chunks]], ensure_ascii=True,
        ).encode()).hexdigest()
        self._lock = Lock()

    def _ensure_index(self):
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            if not self.chunks:
                raise ValueError("No knowledge documents available")
            if not self.store.has_version(self.version, len(self.chunks)):
                vectors = self.embedder.embed_documents([c.text for c in self.chunks])
                self.store.put_version(self.version, self.chunks, vectors)
            self._ready = True

    def search(self, query: str, limit: int = 4) -> list[SearchResult]:
        if not query.strip():
            return []
        self._ensure_index()
        vector = self.embedder.embed_query(query)
        return self.store.search(self.version, vector, min(limit, len(self.chunks)))
