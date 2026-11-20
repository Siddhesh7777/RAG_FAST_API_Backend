from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_upload_rejects_non_pdf():
    r = client.post(
        "/upload",
        params={"thread_id": "test"},
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert r.status_code == 400


def test_chat_requires_message():
    r = client.post("/chat", json={"thread_id": "test"})
    assert r.status_code == 422
