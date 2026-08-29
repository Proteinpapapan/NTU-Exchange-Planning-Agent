"""Path and environment resolution."""

from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]

try:
    from dotenv import load_dotenv as _load_dotenv

    _load_dotenv(_REPO_ROOT / "backend" / ".env", override=False)
except ImportError:
    pass


def _resolve(env_var: str, default_rel: str) -> Path:
    raw = os.environ.get(env_var)
    if raw:
        p = Path(raw)
        return p if p.is_absolute() else (_REPO_ROOT / p).resolve()
    return (_REPO_ROOT / default_rel).resolve()


def coursefinder_db_path() -> Path:
    return _resolve("COURSEFINDER_DB", "coursefinder (1).db")


def app_state_db_path() -> Path:
    return _resolve("APP_STATE_DB", "data/app_state.db")


REPO_ROOT = _REPO_ROOT
