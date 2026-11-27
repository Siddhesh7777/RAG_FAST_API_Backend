def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# def test_upload_requires_login(client):
#     r = client.post(
#         "/upload",
#         params={"thread_id": "t"},
#         files={"file": ("notes.txt", b"hello", "text/plain")},
#     )
#     assert r.status_code == 401


# def test_upload_is_admin_only(client, headers):
#     r = client.post(
#         "/upload",
#         params={"thread_id": "t"},
#         files={"file": ("notes.pdf", b"%PDF-1.4", "application/pdf")},
#         headers=headers("alice"),
#     )
#     assert r.status_code == 403


# def test_upload_rejects_non_pdf(client, headers):
#     r = client.post(
#         "/upload",
#         params={"thread_id": "t"},
#         files={"file": ("notes.txt", b"hello", "text/plain")},
#         headers=headers("root"),
#     )
#     assert r.status_code == 400
