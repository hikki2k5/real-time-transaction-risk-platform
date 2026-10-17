"""Offline retrieval experiments. No change to the production retriever."""
from __future__ import annotations

import math
import re


def tokens(text):
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def unique_documents(chunk_ids):
    return list(dict.fromkeys(chunk_id.split("#")[0] for chunk_id in chunk_ids))


def ranking_metrics(ranking, relevance, k=5):
    if k < 1 or not relevance or any(grade <= 0 for grade in relevance.values()):
        raise ValueError("Positive k and positive relevance grades are required")
    if len(ranking) != len(set(ranking)):
        raise ValueError("Duplicate ranked documents would inflate metrics")
    hits = sum(doc in relevance for doc in ranking[:k])
    reciprocal_rank = next((1 / rank for rank, doc in enumerate(ranking[:10], 1)
                            if doc in relevance), 0.0)
    def dcg(grades):
        return sum((2 ** grade - 1) / math.log2(rank + 1)
                   for rank, grade in enumerate(grades, 1))
    ideal = dcg(sorted(relevance.values(), reverse=True)[:10])
    return {f"recall@{k}": hits / len(relevance), "mrr@10": reciprocal_rank,
            "ndcg@10": dcg([relevance.get(doc, 0) for doc in ranking[:10]]) / ideal}


def reciprocal_rank_fusion(rankings, constant=60):
    if constant < 1:
        raise ValueError("RRF constant must be positive")
    scores = {}
    for ranking in rankings:
        for rank, doc in enumerate(dict.fromkeys(ranking), 1):
            scores[doc] = scores.get(doc, 0) + 1 / (constant + rank)
    return sorted(scores, key=lambda doc: (-scores[doc], doc))


class RetrievalExperiment:
    def __init__(self, chunks, dense_model=None, reranker_model=None):
        from rank_bm25 import BM25Okapi
        if not chunks:
            raise ValueError("Corpus is empty")
        if reranker_model and not dense_model:
            raise ValueError("Reranking requires dense retrieval for hybrid candidates")
        self.chunks = chunks
        self.bm25 = BM25Okapi([tokens(chunk.text) for chunk in chunks])
        self.dense = self.reranker = None
        if dense_model:
            from sentence_transformers import SentenceTransformer
            self.dense = SentenceTransformer(dense_model)
            self.vectors = self.dense.encode([c.text for c in chunks], normalize_embeddings=True)
        if reranker_model:
            from sentence_transformers import CrossEncoder
            self.reranker = CrossEncoder(reranker_model)

    def rank(self, query, candidates=20):
        scores = self.bm25.get_scores(tokens(query))
        lexical = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))
        result = {"bm25": lexical}
        if self.dense:
            vector = self.dense.encode(query, normalize_embeddings=True)
            scores = self.vectors @ vector
            dense = sorted(range(len(scores)), key=lambda i: (-float(scores[i]), i))
            hybrid = reciprocal_rank_fusion([lexical[:candidates], dense[:candidates]])
            result.update(dense=dense, hybrid=hybrid)
            if self.reranker:
                pool = hybrid[:candidates]
                scores = self.reranker.predict([(query, self.chunks[i].text) for i in pool])
                result["hybrid_reranked"] = [i for _, i in sorted(
                    zip(map(float, scores), pool), key=lambda pair: (-pair[0], pair[1]))]
        return {name: unique_documents([self.chunks[i].doc_id for i in order])
                for name, order in result.items()}
