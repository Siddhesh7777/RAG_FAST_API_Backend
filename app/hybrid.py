import re

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

from app.store import search_where, store

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
    "i",
    "my",
    "me",
}


def _tokens(text):
    words = re.findall(r"\w+", text.lower())
    return [w for w in words if w not in STOPWORDS]


def semantic_ranking(where, query, n):
    return search_where(where, query, n)


def keyword_ranking(where, query, n):
    data = store.get(where=where, include=["documents", "metadatas"])
    docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(data["documents"], data["metadatas"])
    ]
    if not docs:
        return []
    bm25 = BM25Okapi([_tokens(d.page_content) for d in docs])
    scores = bm25.get_scores(_tokens(query))
    ranked = sorted(zip(scores, docs), key=lambda pair: pair[0], reverse=True)
    return [doc for score, doc in ranked[:n]]


def combine(rankings, k):
    points = {}
    docs_by_text = {}
    for ranking in rankings:
        for rank, doc in enumerate(ranking, start=1):
            text = doc.page_content
            docs_by_text[text] = doc
            points[text] = points.get(text, 0) + 1 / (60 + rank)
    best = sorted(points, key=points.get, reverse=True)[:k]
    return [docs_by_text[t] for t in best]


def hybrid_search_where(where, query, k=4, pool=20):
    return combine(
        [semantic_ranking(where, query, pool), keyword_ranking(where, query, pool)],
        k,
    )


def hybrid_search(thread_id, query, k=4, pool=20):
    return hybrid_search_where({"thread_id": thread_id}, query, k, pool)
