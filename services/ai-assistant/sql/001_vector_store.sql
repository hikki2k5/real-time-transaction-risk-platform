CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS ai;

CREATE TABLE IF NOT EXISTS ai.knowledge_versions (
    collection TEXT NOT NULL,
    version TEXT NOT NULL,
    embedding_model TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    chunk_count INTEGER NOT NULL CHECK (chunk_count > 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (collection, version)
);

CREATE TABLE IF NOT EXISTS ai.knowledge_chunks (
    collection TEXT NOT NULL,
    version TEXT NOT NULL,
    doc_id TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    embedding vector NOT NULL,
    PRIMARY KEY (collection, version, doc_id),
    FOREIGN KEY (collection, version) REFERENCES ai.knowledge_versions (collection, version),
    CHECK (vector_dims(embedding) = dimensions)
);

-- Exact cosine search is sufficient for this small knowledge corpus.
-- The primary key filters collection/version before the distance sort.
