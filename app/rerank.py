from sentence_transformers import CrossEncoder

_model = None


def get_reranker():
    global _model
    if _model is None:
        _model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2", device="cpu")
    return _model


def rerank(query, docs, k=4):
    if not docs:
        return []
    pairs = [(query, d.page_content) for d in docs]
    scores = get_reranker().predict(pairs)
    ranked = sorted(zip(scores, docs), key=lambda pair: pair[0], reverse=True)
    return [doc for score, doc in ranked[:k]]
