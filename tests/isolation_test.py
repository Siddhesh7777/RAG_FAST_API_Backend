import uuid

from app.store import add_chunk, search, store


def test_thread_cannot_see_other_threads_documents():
    thread_a = f"test-a-{uuid.uuid4()}"
    thread_b = f"test-b-{uuid.uuid4()}"
    chunks = [{"text": "The refund policy allows returns within 30 days.", "page": 1}]

    try:
        add_chunk(chunks, thread_a, "policy.pdf")

        assert len(search(thread_a, "refund policy", k=3)) >= 1
        assert search(thread_b, "refund policy", k=3) == []
    finally:
        store.delete(where={"thread_id": thread_a})
