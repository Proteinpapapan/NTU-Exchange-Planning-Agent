"""SQLite for sessions and chat titles."""

from __future__ import annotations

import sqlite3
import threading

from graph.config import app_state_db_path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id  TEXT PRIMARY KEY,
    state_json  TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS chats (
    session_id  TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    folder      TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""

_lock = threading.Lock()
_conn: sqlite3.Connection | None = None


def get_conn() -> sqlite3.Connection:
    global _conn
    with _lock:
        if _conn is None:
            path = app_state_db_path()
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.executescript(_SCHEMA)
            conn.commit()
            _conn = conn
        return _conn


def write(sql: str, params: tuple = ()) -> None:
    try:
        conn = get_conn()
        with _lock:
            conn.execute(sql, params)
            conn.commit()
    except Exception:
        pass
