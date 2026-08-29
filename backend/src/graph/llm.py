"""Single Groq client constructor."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from graph.config import REPO_ROOT

DEFAULT_MODEL = "llama-3.3-70b-versatile"
_dotenv_loaded = False


def _load_dotenv_once() -> None:
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv(REPO_ROOT / "backend" / ".env", override=False)


@lru_cache(maxsize=None)
def get_llm(
    model: str | None = None,
    temperature: float = 0.0,
    json_mode: bool = False,
) -> Any:
    from langchain_groq import ChatGroq

    _load_dotenv_once()
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy backend/.env.example to backend/.env."
        )
    resolved = model or os.environ.get("GROQ_MODEL", DEFAULT_MODEL)
    kwargs: dict[str, Any] = {
        "model": resolved,
        "temperature": temperature,
        "api_key": api_key,
    }
    if json_mode:
        kwargs["model_kwargs"] = {"response_format": {"type": "json_object"}}
    try:
        return ChatGroq(**kwargs)
    except TypeError:
        kwargs.pop("model_kwargs", None)
        return ChatGroq(**kwargs)


def llm_available() -> bool:
    _load_dotenv_once()
    if not os.environ.get("GROQ_API_KEY"):
        return False
    try:
        import langchain_groq  # noqa: F401
    except ImportError:
        return False
    return True
