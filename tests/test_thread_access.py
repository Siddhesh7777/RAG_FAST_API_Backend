def _new_thread(client, headers, username):
    r = client.post("/threads", headers=headers(username))
    assert r.status_code == 200
    return r.json()["thread_id"]


def test_threads_require_login(client):
    assert client.get("/threads").status_code == 401
    assert client.post("/threads").status_code == 401
    assert (
        client.post("/chat", json={"thread_id": "x", "message": "hi"}).status_code
        == 401
    )


def test_threads_list_shows_only_own_threads(client, headers):
    mine = _new_thread(client, headers, "alice")
    theirs = _new_thread(client, headers, "bob")
    ids = [
        t["thread_id"] for t in client.get("/threads", headers=headers("alice")).json()
    ]
    assert mine in ids
    assert theirs not in ids


def test_cannot_read_someone_elses_messages(client, headers):
    alice_thread = _new_thread(client, headers, "alice")
    assert (
        client.get(
            f"/threads/{alice_thread}/messages", headers=headers("alice")
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/threads/{alice_thread}/messages", headers=headers("bob")
        ).status_code
        == 404
    )


def test_cannot_chat_in_someone_elses_thread(client, headers):
    alice_thread = _new_thread(client, headers, "alice")
    r = client.post(
        "/chat",
        json={"thread_id": alice_thread, "message": "hello"},
        headers=headers("bob"),
    )
    assert r.status_code == 404


def test_chat_in_unknown_thread_is_404(client, headers):
    r = client.post(
        "/chat",
        json={"thread_id": "does-not-exist", "message": "hello"},
        headers=headers("alice"),
    )
    assert r.status_code == 404


def test_chat_requires_a_message(client, headers):
    thread = _new_thread(client, headers, "alice")
    r = client.post("/chat", json={"thread_id": thread}, headers=headers("alice"))
    assert r.status_code == 422
