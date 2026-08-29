"""Persist profile + message history per chat session."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from graph.state import RawProfileExtraction, StudentProfile
from services.app_state_db import get_conn, write


def new_session_id() -> str:
    return uuid.uuid4().hex


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(session_id: str) -> dict[str, Any]:
    if not session_id:
        return {}
    try:
        row = get_conn().execute(
            "SELECT state_json FROM sessions WHERE session_id = ?", (session_id,)
        ).fetchone()
    except Exception:
        return {}
    if not row:
        return {}
    try:
        data = json.loads(row["state_json"])
    except (json.JSONDecodeError, TypeError):
        return {}
    state: dict[str, Any] = {}
    raw = data.get("raw_profile")
    if isinstance(raw, dict):
        try:
            state["raw_profile"] = RawProfileExtraction(**raw)
        except Exception:
            pass
    if isinstance(data.get("messages"), list):
        state["messages"] = data["messages"]
    if isinstance(data.get("profile"), dict):
        try:
            state["profile"] = StudentProfile(**data["profile"])
        except Exception:
            pass
    return state


def save(session_id: str, state: dict[str, Any], title: str | None = None) -> None:
    if not session_id:
        return
    payload: dict[str, Any] = {}
    for key in ("raw_profile", "profile", "messages"):
        value = state.get(key)
        if value is None:
            continue
        payload[key] = value.model_dump() if hasattr(value, "model_dump") else value
    now = _now()
    write(
        "INSERT INTO sessions (session_id, state_json, created_at, updated_at)"
        " VALUES (?,?,?,?)"
        " ON CONFLICT(session_id) DO UPDATE SET state_json=excluded.state_json,"
        " updated_at=excluded.updated_at",
        (session_id, json.dumps(payload), now, now),
    )
    if title:
        write(
            "INSERT INTO chats (session_id, title, folder, created_at, updated_at)"
            " VALUES (?,?,?,?,?)"
            " ON CONFLICT(session_id) DO UPDATE SET title=excluded.title,"
            " updated_at=excluded.updated_at",
            (session_id, title, _folder_for(state), now, now),
        )


def ensure_chat(session_id: str, title: str = "New chat", folder: str | None = None) -> None:
    now = _now()
    write(
        "INSERT INTO chats (session_id, title, folder, created_at, updated_at)"
        " VALUES (?,?,?,?,?)"
        " ON CONFLICT(session_id) DO UPDATE SET updated_at=excluded.updated_at",
        (session_id, title, folder, now, now),
    )


def list_chats() -> list[dict[str, Any]]:
    rows = get_conn().execute(
        "SELECT session_id, title, folder, created_at, updated_at FROM chats"
        " ORDER BY updated_at DESC"
    ).fetchall()
    return [dict(r) for r in rows]


def get_chat(session_id: str) -> dict[str, Any] | None:
    row = get_conn().execute(
        "SELECT session_id, title, folder, created_at, updated_at FROM chats"
        " WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not row:
        return None
    state = load(session_id)
    return {**dict(row), "messages": state.get("messages") or []}


def delete_chat(session_id: str) -> None:
    write("DELETE FROM chats WHERE session_id = ?", (session_id,))
    write("DELETE FROM sessions WHERE session_id = ?", (session_id,))


def title_from_message(text: str) -> str:
    t = " ".join((text or "").split())
    if not t:
        return "New chat"
    return (t[:48] + "…") if len(t) > 48 else t


def _folder_for(state: dict[str, Any]) -> str | None:
    profile = state.get("profile")
    if profile is None:
        return None
    sem = getattr(profile, "preferred_semester", "") or ""
    if "SUSEP" in sem:
        return "SUSEP"
    if sem:
        return "GEM Explorer"
    return None
