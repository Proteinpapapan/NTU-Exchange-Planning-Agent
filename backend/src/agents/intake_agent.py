"""Intake agent — LLM extraction of degree, term, destination, and extras."""

from __future__ import annotations

import json
import re

from agents.intake_fallback import extract_fallback
from data.destinations import match_country
from data.programmes import extract_programme_from_message, resolve_programme
from graph.llm import get_llm, llm_available
from graph.state import RawProfileExtraction, SemesterLiteral

try:
    from typing import get_args
    _SEMESTERS = list(get_args(SemesterLiteral))
except Exception:
    _SEMESTERS = []

_SYSTEM = """You extract an NTU exchange-planning profile from the student's messages.

Return a JSON object with EXACTLY these keys:
  school_course          NTU programme CODE or null
  preferred_semester     EXACTLY one of {semesters}, or null
  destination_pref       country they want (e.g. "Spain"), or null
  budget_amount          number or null
  budget_currency         ISO code like SGD/USD/JPY, or null
  named_university       a specific university they named, or null
  know_more_university   university they asked to brief, or null
  au_value               number if converting credits, else null
  au_from_unit           e.g. "AU" or "ECTS", else null
  au_to_unit             e.g. "ECTS" or "AU", else null
  preferences_free_text  other wants, else ""

RULES:
- Read messy, shorthand, lowercase text. "eee", "EEE", and "electrical" are all EEE.
- "y2" / "year 2" is year of study, NOT a programme. Do not put it in school_course.
- "I want to go Spain" / "spain" / "in Spain" means destination_pref = "Spain".
- If a field is not mentioned, return null. NEVER guess a semester.
- "SUSEP Sem 1" is NOT "Semester 1 (Fall)".
- computer science -> CSC (not CS). CS is Communication Studies.
- Do not wrap the JSON in markdown.

Examples:
"y2 eee i want to go Spain"
{{"school_course":"EEE","preferred_semester":null,"destination_pref":"Spain","budget_amount":null,"budget_currency":null,"named_university":null,"know_more_university":null,"au_value":null,"au_from_unit":null,"au_to_unit":null,"preferences_free_text":""}}

"EEE, fall exchange in Japan"
{{"school_course":"EEE","preferred_semester":"Semester 1 (Fall)","destination_pref":"Japan","budget_amount":null,"budget_currency":null,"named_university":null,"know_more_university":null,"au_value":null,"au_from_unit":null,"au_to_unit":null,"preferences_free_text":""}}

"I want SUSEP sem 2, I'm in Business"
{{"school_course":"BUS","preferred_semester":"SUSEP Sem 2 (Spring)","destination_pref":null,"budget_amount":null,"budget_currency":null,"named_university":null,"know_more_university":null,"au_value":null,"au_from_unit":null,"au_to_unit":null,"preferences_free_text":""}}
"""


def _message_text(resp) -> str:
    content = getattr(resp, "content", "") or ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks: list[str] = []
        for part in content:
            if isinstance(part, str):
                chunks.append(part)
            elif isinstance(part, dict):
                chunks.append(str(part.get("text") or ""))
        return "".join(chunks)
    return str(content)


def _parse_json(text: str) -> dict:
    text = (text or "").strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.M).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if not m:
            return {}
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return {}


def _coerce(data: dict) -> RawProfileExtraction:
    def text(v):
        if v is None:
            return None
        s = str(v).strip()
        return s or None

    def num(v):
        if v is None or isinstance(v, bool):
            return None
        try:
            if isinstance(v, str):
                v = re.sub(r"[^\d.]", "", v) or None
                if v is None:
                    return None
            return float(v)
        except (TypeError, ValueError):
            return None

    school = text(data.get("school_course"))
    if school:
        hit = resolve_programme(school) or extract_programme_from_message(school)
        school = hit[0] if hit else school

    semester = text(data.get("preferred_semester"))
    if semester not in _SEMESTERS:
        semester = None
    dest = text(data.get("destination_pref"))
    if dest:
        dest = match_country(dest) or dest
    cur = text(data.get("budget_currency"))
    if cur:
        cur = cur.upper()
    return RawProfileExtraction(
        school_course=school,
        preferred_semester=semester,
        destination_pref=dest,
        budget_amount=num(data.get("budget_amount")),
        budget_currency=cur,
        named_university=text(data.get("named_university")),
        know_more_university=text(data.get("know_more_university")),
        au_value=num(data.get("au_value")),
        au_from_unit=text(data.get("au_from_unit")),
        au_to_unit=text(data.get("au_to_unit")),
        preferences_free_text=str(data.get("preferences_free_text") or "").strip(),
    )


def _merge_extraction(primary: RawProfileExtraction, fill: RawProfileExtraction) -> RawProfileExtraction:
    data = primary.model_dump()
    extra = fill.model_dump()
    for key, value in extra.items():
        if key == "preferences_free_text":
            if value and not data.get(key):
                data[key] = value
            continue
        if data.get(key) is None and value is not None:
            data[key] = value
    return RawProfileExtraction(**data)


def extract_profile(raw_input: str) -> RawProfileExtraction:
    if not (raw_input or "").strip():
        return RawProfileExtraction()
    fallback = extract_fallback(raw_input)
    if not llm_available():
        return fallback
    prompt = _SYSTEM.format(semesters=", ".join(f'"{s}"' for s in _SEMESTERS))
    try:
        llm = get_llm(temperature=0.0, json_mode=True)
        resp = llm.invoke([("system", prompt), ("human", raw_input)])
        parsed = _coerce(_parse_json(_message_text(resp)))
        return _merge_extraction(parsed, fallback)
    except Exception:
        return fallback


def _user_blob(state: dict) -> str:
    parts: list[str] = []
    for m in state.get("messages") or []:
        if isinstance(m, dict) and m.get("role") == "user":
            parts.append(str(m.get("content") or ""))
    current = state.get("raw_input") or ""
    if not parts or parts[-1] != current:
        parts.append(current)
    return "\n".join(p for p in parts if p).strip()


def intake_agent(state: dict) -> dict:
    extracted = extract_profile(_user_blob(state))
    return {"raw_profile": extracted}
