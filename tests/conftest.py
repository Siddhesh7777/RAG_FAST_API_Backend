import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app
from app.users import create_user

PASSWORDS = {
    "alice": "alice-password-1",
    "bob": "bob-password-123",
    "hannah": "hannah-password-1",
    "root": "root-password-123",
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # A fresh, empty user database for every test.
    monkeypatch.setattr(settings, "users_db_path", str(tmp_path / "users.db"))
    create_user("alice", PASSWORDS["alice"], "employee", "Engineering")
    create_user("bob", PASSWORDS["bob"], "employee", "Sales")
    create_user("hannah", PASSWORDS["hannah"], "hr", "HR")
    create_user("root", PASSWORDS["root"], "admin", "IT")
    return TestClient(app)


@pytest.fixture()
def headers(client):
    def _for(username):
        r = client.post(
            "/auth/login",
            data={"username": username, "password": PASSWORDS[username]},
        )
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _for
