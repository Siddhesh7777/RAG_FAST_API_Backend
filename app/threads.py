import sqlite3
import uuid
from contextlib import closing
from datetime import datetime, timezone

from app.config import settings

DEFAULT_TITLE = "New chat"


def _connect():
    # Same SQLite file as the users table, a second table inside it.
    conn = sqlite3.connect(settings.users_db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS threads (
            thread_id TEXT PRIMARY KEY,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT NOT NULL
        )""")
    return conn


def create_thread(username):
    thread_id = str(uuid.uuid4())  # random and unguessable, made by the server
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "INSERT INTO threads (thread_id, username, title, created_at) VALUES (?, ?, ?, ?)",
                (
                    thread_id,
                    username,
                    DEFAULT_TITLE,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
    return {"thread_id": thread_id, "title": DEFAULT_TITLE}


def list_threads(username):
    # Only this user's rows, newest first.
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT thread_id, title, created_at FROM threads "
            "WHERE username = ? ORDER BY created_at DESC",
            (username,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_owned_thread(thread_id, username):
    # The ownership check: the thread must exist AND belong to this user.
    # Someone else's thread looks exactly like a thread that doesn't exist.
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT thread_id, title, created_at FROM threads "
            "WHERE thread_id = ? AND username = ?",
            (thread_id, username),
        ).fetchone()
    return dict(row) if row else None


def set_title(thread_id, title):
    with closing(_connect()) as conn:
        with conn:
            conn.execute(
                "UPDATE threads SET title = ? WHERE thread_id = ?", (title, thread_id)
            )
