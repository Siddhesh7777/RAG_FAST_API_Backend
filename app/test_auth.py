import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.security import create_token
from app.users import create_user, get_user


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Each test gets its own empty user database, so tests never touch real users.
    monkeypatch.setattr(settings, "users_db_path", str(tmp_path / "users.db"))
    create_user("alice", "alice-password-1", "employee", "Engineering")
    create_user("hannah", "hannah-password-1", "hr", "HR")
    create_user("root", "root-password-123", "admin", "IT")
    return TestClient(app)


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password})


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def token_for(client, username, password):
    return login(client, username, password).json()["access_token"]


def test_login_success_returns_token(client):
    r = login(client, "alice", "alice-password-1")
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_wrong_password_rejected(client):
    assert login(client, "alice", "not-her-password").status_code == 401


def test_unknown_user_gets_same_error_as_wrong_password(client):
    wrong = login(client, "alice", "not-her-password")
    unknown = login(client, "nobody", "whatever-password")
    assert unknown.status_code == wrong.status_code == 401
    assert unknown.json() == wrong.json()


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401


def test_me_shows_role_based_visibility(client):
    alice = client.get(
        "/auth/me", headers=bearer(token_for(client, "alice", "alice-password-1"))
    )
    hannah = client.get(
        "/auth/me", headers=bearer(token_for(client, "hannah", "hannah-password-1"))
    )
    assert alice.json()["visibility"] == ["all"]
    assert hannah.json()["visibility"] == ["all", "hr_only"]


def test_employee_cannot_use_admin_route_but_admin_can(client):
    employee = token_for(client, "alice", "alice-password-1")
    admin = token_for(client, "root", "root-password-123")
    assert client.get("/auth/admin-check", headers=bearer(employee)).status_code == 403
    assert client.get("/auth/admin-check", headers=bearer(admin)).status_code == 200


def test_tampered_token_rejected(client):
    header, payload, signature = token_for(client, "alice", "alice-password-1").split(
        "."
    )
    forged = ("x" if signature[0] != "x" else "y") + signature[1:]
    r = client.get("/auth/me", headers=bearer(f"{header}.{payload}.{forged}"))
    assert r.status_code == 401


def test_expired_token_rejected(client):
    r = client.get("/auth/me", headers=bearer(create_token("alice", minutes=-1)))
    assert r.status_code == 401


def test_password_is_not_stored_in_plain_text(client):
    stored = get_user("alice")["password_hash"]
    assert stored.startswith("scrypt$")
    assert "alice-password-1" not in stored
