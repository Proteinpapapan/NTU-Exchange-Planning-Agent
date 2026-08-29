"""FastAPI app — chat, sessions, mapping details, research."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agents.research_agent import university_briefing
from data.coursefinder_db import (
    PAGE_SIZE,
    db_stats,
    eligible_universities,
    lookup_modules,
    mapping_details,
    programme_index,
    university_by_id,
)
from graph.build_graph import graph
from graph.config import coursefinder_db_path
from graph.llm import llm_available
from services import session_store

app = FastAPI(title="NTU Exchange Planner", version="1.0.0")
_origins = os.environ.get("CORS_ALLOW_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins.split(",")] if _origins != "*" else ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ResearchRequest(BaseModel):
    university_id: int | None = None
    name: str | None = None
    country: str | None = None
    term: str | None = None
    school: str | None = None
    programme_type: str | None = None


def _append_messages(state: dict, user: str, assistant: dict) -> None:
    history = list(state.get("messages") or [])
    history.append({"role": "user", "content": user})
    history.append({"role": "assistant", **assistant})
    state["messages"] = history


@app.post("/api/chat")
def chat(req: ChatRequest):
    session_id = req.session_id or session_store.new_session_id()
    state = session_store.load(session_id)
    state["raw_input"] = req.message
    state["session_id"] = session_id
    final = graph.invoke(state)

    payload = final.get("ui_payload") or {
        "clarification": final.get("clarification_question"),
        "narration": final.get("final_report") or "",
        "cards": [],
        "conversions": [],
        "research": None,
        "profile": None,
        "has_more": False,
        "total_universities": 0,
    }
    assistant = {
        "content": payload.get("narration") or payload.get("clarification") or "",
        "payload": payload,
    }
    _append_messages(final, req.message, assistant)
    title = None
    existing = session_store.get_chat(session_id)
    if not existing or existing.get("title") in (None, "New chat"):
        title = session_store.title_from_message(req.message)
    session_store.save(session_id, final, title=title)
    session_store.ensure_chat(session_id, title or (existing["title"] if existing else "New chat"))

    return {
        "session_id": session_id,
        "title": title or (existing["title"] if existing else "New chat"),
        **payload,
        "messages": final.get("messages") or [],
    }


@app.get("/api/chats")
def chats():
    return {"chats": session_store.list_chats()}


@app.post("/api/chats")
def new_chat():
    sid = session_store.new_session_id()
    session_store.ensure_chat(sid, "New chat")
    return {"session_id": sid, "title": "New chat", "messages": []}


@app.get("/api/chats/{session_id}")
def get_chat(session_id: str):
    chat = session_store.get_chat(session_id)
    if not chat:
        raise HTTPException(404, "Chat not found")
    return chat


@app.delete("/api/chats/{session_id}")
def delete_chat(session_id: str):
    session_store.delete_chat(session_id)
    return {"cleared": session_id}


@app.get("/api/programmes")
def programmes():
    return {"programmes": [{"code": c, "name": n} for c, n in programme_index()]}


@app.get("/api/universities")
def more_universities(
    school: str,
    programme_type: str,
    country: str | None = None,
    offset: int = 0,
    limit: int = PAGE_SIZE,
):
    cards, total = eligible_universities(
        school_code=school,
        programme_type=programme_type,
        country_substr=country,
        offset=offset,
        limit=limit,
    )
    return {
        "cards": [c.model_dump() for c in cards],
        "total": total,
        "has_more": offset + len(cards) < total,
    }


@app.get("/api/universities/{university_id}/mappings")
def uni_mappings(
    university_id: int,
    school: str,
    programme_type: str,
    offset: int = 0,
    limit: int = 20,
):
    rows = lookup_modules(university_id, school, programme_type, offset, limit)
    return {"mappings": [m.model_dump() for m in rows]}


@app.get("/api/mappings/{mapping_id}/details")
def details(mapping_id: int):
    return {"details": mapping_details(mapping_id)}


@app.post("/api/research")
def research(req: ResearchRequest):
    name = req.name
    country = req.country
    if req.university_id:
        uni = university_by_id(req.university_id)
        if uni:
            name = uni[1]
            country = uni[2]
    if not name:
        raise HTTPException(400, "Provide university_id or name")
    briefing = university_briefing(
        university_id=req.university_id,
        name=name,
        country=country,
        term=req.term,
        school=req.school,
        programme_type=req.programme_type,
    )
    return briefing


@app.get("/api/health")
def health():
    stats = {}
    try:
        stats = db_stats()
    except Exception as e:
        stats = {"error": str(e)}
    return {
        "status": "ok",
        "llm_configured": llm_available(),
        "coursefinder_db": coursefinder_db_path().exists(),
        **stats,
    }
