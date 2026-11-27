import uuid

from langchain_core.documents import Document

from app.agent import rag_tool
from app.config import settings
from app.store import store


def _cfg(visibility):
    return {"configurable": {"thread_id": "t", "visibility": visibility}}


def _meta(doc_id, visibility):
    return {
        "scope": "company",
        "doc_id": doc_id,
        "filename": f"{doc_id}.pdf",
        "title": doc_id,
        "department": "HR",
        "visibility": visibility,
        "version": "1",
        "effective_date": "2026-01-01",
        "page": 1,
        "fingerprint": "test",
    }


def test_tool_never_returns_chunks_the_user_may_not_see(monkeypatch):
    monkeypatch.setattr(
        settings, "retriever_k", 20
    )  # return plenty, so absence means "filtered"
    marker = f"zq{uuid.uuid4().hex[:10]}"  # a unique word nothing else contains
    public_id, secret_id = f"TEST-PUB-{marker}", f"TEST-SEC-{marker}"
    docs = [
        Document(
            page_content=f"Public note {marker} about lunch hours.",
            metadata=_meta(public_id, "all"),
        ),
        Document(
            page_content=f"Secret salary {marker} band is confidential.",
            metadata=_meta(secret_id, "hr_only"),
        ),
    ]
    try:
        store.add_documents(docs)
        query = {
            "query": f"{marker} salary band"
        }  # a perfect keyword match for BOTH chunks
        employee = rag_tool.invoke(query, config=_cfg(["all"]))
        hr = rag_tool.invoke(query, config=_cfg(["all", "hr_only"]))

        assert "Secret salary" not in employee  # the leak check
        assert "Public note" in employee
        assert "Secret salary" in hr  # HR can still reach it
    finally:
        store.delete(where={"doc_id": {"$in": [public_id, secret_id]}})


def test_tool_fails_closed_when_visibility_is_missing():
    result = rag_tool.invoke(
        {"query": "salary band"}, config={"configurable": {"thread_id": "t"}}
    )
    assert result == "No relevant content found."
