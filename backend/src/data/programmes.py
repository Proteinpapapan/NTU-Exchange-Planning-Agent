"""Map free-text degree names onto school_programmes.code."""

from __future__ import annotations

import re

from rapidfuzz import fuzz, process

from data.coursefinder_db import programme_index
from data.destinations import COUNTRY_ALIASES

_SKIP_TOKENS = {
    "i", "im", "i'm", "to", "go", "in", "my", "the", "a", "an", "on", "for",
    "and", "or", "want", "wanna", "going", "year", "y1", "y2", "y3", "y4",
    "y5", "sem", "sem1", "sem2",
}

ALIASES = {
    "computer science": "CSC",
    "comp sci": "CSC",
    "cs": "CSC",
    "computer engineering": "CE",
    "electrical": "EEE",
    "electrical engineering": "EEE",
    "electrical and electronic": "EEE",
    "electrical & electronic": "EEE",
    "business": "BUS",
    "accountancy": "ACC",
    "mechanical": "ME",
    "mechanical engineering": "ME",
    "civil": "CEE",
    "civil engineering": "CEE",
    "chemical": "CBE",
    "data science": "DSAI",
    "dsai": "DSAI",
    "psychology": "PSY",
    "economics": "ECON",
    "aerospace": "AERO",
    "materials": "MAT",
    "physics": "PHY",
    "math": "MATH",
    "mathematics": "MATH",
    "biological sciences": "BS",
    "bio": "BS",
    "communication studies": "CS",
    "adm": "ADM",
    "design": "ADM",
    "public policy": "PPGA",
    "sociology": "SOC",
    "history": "HIST",
    "english": "ELH",
    "linguistics": "LMS",
    "renaissance": "REP",
    "rep": "REP",
    "iem": "IEM",
    "maritime": "MS",
    "environment": "ENE",
    "environmental engineering": "ENE",
}


def resolve_programme(text: str | None) -> tuple[str, str] | None:
    if not text:
        return None
    raw = text.strip()
    if not raw:
        return None
    programmes = programme_index()
    by_code = {code.upper(): (code, name) for code, name in programmes}
    upper = raw.upper()
    alias = ALIASES.get(raw.lower())
    if alias and alias in by_code:
        return by_code[alias]
    if upper in by_code:
        return by_code[upper]

    names = {name.lower(): (code, name) for code, name in programmes}
    if raw.lower() in names:
        return names[raw.lower()]

    # Substring on official name
    for code, name in programmes:
        if raw.lower() in name.lower() or name.lower() in raw.lower():
            return code, name

    choices = [name for _, name in programmes]
    match = process.extractOne(raw, choices, scorer=fuzz.WRatio)
    if match and match[1] >= 86:
        return names[match[0].lower()]
    return None


def extract_programme_from_message(text: str | None) -> tuple[str, str] | None:
    """Pull a programme code out of a messy sentence (e.g. 'y2 eee spain')."""
    if not text:
        return None
    lower = text.lower()
    for alias, code in sorted(ALIASES.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            hit = resolve_programme(code)
            if hit:
                return hit
    tokens = re.findall(r"[A-Za-z]{2,6}", text)
    for tok in tokens:
        if tok.lower() in _SKIP_TOKENS or tok.lower() in COUNTRY_ALIASES:
            continue
        hit = resolve_programme(tok)
        if hit:
            return hit
    return None
