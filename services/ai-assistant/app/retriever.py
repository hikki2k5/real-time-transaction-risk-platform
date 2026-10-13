from __future__ import annotations

import math
import re
from dataclasses import dataclass
from pathlib import Path


TOKEN_RE = re.compile(r"[a-zA-Z0-9_./:-]+")


@dataclass(frozen=True)
class DocumentChunk:
    doc_id: str
    title: str
    text: str
    tokens: set[str]


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


class KnowledgeBase:
    def __init__(self, knowledge_dir: Path):
        self.knowledge_dir = knowledge_dir
        self.chunks = self._load_chunks()

    def search(self, query: str, limit: int = 4) -> list[SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        results = []
        for chunk in self.chunks:
            overlap = query_tokens & chunk.tokens
            if not overlap:
                continue
            score = len(overlap) / math.sqrt(max(1, len(chunk.tokens)))
            results.append(SearchResult(chunk=chunk, score=round(score, 4)))

        return sorted(results, key=lambda result: result.score, reverse=True)[:limit]

    def _load_chunks(self) -> list[DocumentChunk]:
        chunks = []
        for path in sorted(self.knowledge_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            title = extract_title(text, path.stem)
            for index, chunk_text in enumerate(split_markdown(text), start=1):
                doc_id = f"{path.stem}#{index}"
                chunks.append(
                    DocumentChunk(
                        doc_id=doc_id,
                        title=title,
                        text=chunk_text,
                        tokens=tokenize(chunk_text),
                    )
                )
        return chunks


def tokenize(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 2}


def extract_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback.replace("-", " ").title()


def split_markdown(text: str, max_chars: int = 900) -> list[str]:
    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    chunks = []
    current = ""
    for paragraph in paragraphs:
        if current and len(current) + len(paragraph) + 2 > max_chars:
            chunks.append(current)
            current = paragraph
        else:
            current = f"{current}\n\n{paragraph}".strip()
    if current:
        chunks.append(current)
    return chunks
