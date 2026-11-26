import sqlite3
from contextlib import closing
from datetime import datetime, timezone

from app.config import settings
from app.security import hash_password

ROLES = ("employee", "hr", "admin")

# THE access rule, in one place. Which document visibilities may each role read?
# Decision: admins manage documents but do NOT automatically read HR-only ones
# (least privilege). Change this one table if you disagree.
_VISIBILITY = {
    "employee": ["all"],
    "hr": ["all", "hr_only"],
    "admin": ["all"],
}


def visibility_for(role: str) -> list:
    return list(_VISIBILITY.get(role, []))  # unknown role -> sees nothing


def _connect():
    conn = sqlite3.connect(settings.users_db_path)
    conn.row_factory = sqlite3.Row  # rows behave like dictionaries
    # conn.row_factory is the facotry package if not written sqlite.row then tuple if wrritten then dict
    # Create the table on first use. IF NOT EXISTS makes this safe to repeat.
    conn.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            department TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )""")
    return conn


def create_user(username, password, role="employee", department="General"):
    if role not in ROLES:
        raise ValueError(f"role must be one of {ROLES}")
    if len(password) < 8:
        raise ValueError("password must be at least 8 characters")
    username = username.strip().lower()  # "Alice" and "alice" are the same user
    try:
        with closing(_connect()) as conn:
            with conn:  # commits the insert, or rolls back on error
                # The ? marks are placeholders, never build SQL with string
                # concatenation: that's how SQL injection happens.
                conn.execute(
                    "INSERT INTO users (username, password_hash, role, department, created_at) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        username,
                        hash_password(password),
                        role,
                        department,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
    except sqlite3.IntegrityError:  # the UNIQUE rule on username was broken
        raise ValueError(f"user '{username}' already exists")


def get_user(username):
    with closing(_connect()) as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None  # None means "no such user"
