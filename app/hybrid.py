from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.store import search, store

import re

STOPWORDS = {
    "what",
    "does",
    "do",
    "is",
    "are",
    "the",
    "a",
    "an",
    "for",
    "and",
    "how",
    "it",
    "in",
    "of",
    "to",
    "work",
    "works",
}


def _tokens(text):
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS]


# this was before one
# /def _tokens(text):
#     return text.lower().split()


def hybrid_search(thread_id, query, k=4, pool=20):
    vector_docs = search(thread_id, query, k=pool)

    data = store.get(where={"thread_id": thread_id}, include=["documents", "metadatas"])
    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(data["documents"], data["metadatas"])
    ]
    if not docs:
        return []

    bm25 = BM25Okapi([_tokens(d.page_content) for d in docs])
    scores = bm25.get_scores(_tokens(query))
    top_idx = sorted(range(len(docs)), key=lambda i: scores[i], reverse=True)[:pool]
    keyword_docs = [docs[i] for i in top_idx]

    fused = {}
    for ranking in (vector_docs, keyword_docs):
        for rank, doc in enumerate(ranking, start=1):
            entry = fused.setdefault(doc.page_content, {"doc": doc, "score": 0.0})
            entry["score"] += 1 / (60 + rank)

    best = sorted(fused.values(), key=lambda e: e["score"], reverse=True)
    return [e["doc"] for e in best[:k]]
