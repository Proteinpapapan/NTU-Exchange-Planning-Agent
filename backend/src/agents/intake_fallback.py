"""Deterministic intake when Groq is unavailable or as a merge fill-in."""

from __future__ import annotations

import re

from data.destinations import extract_country_from_message
from data.programmes import extract_programme_from_message
from graph.state import RawProfileExtraction

_SEMESTERS = [
    ("susep sem 1", "SUSEP Sem 1 (Fall)"),
    ("susep sem 2", "SUSEP Sem 2 (Spring)"),
    ("susep semester 1", "SUSEP Sem 1 (Fall)"),
    ("susep semester 2", "SUSEP Sem 2 (Spring)"),
    ("susep", "SUSEP Sem 1 (Fall)"),
    ("semester 1", "Semester 1 (Fall)"),
    ("sem 1", "Semester 1 (Fall)"),
    ("fall", "Semester 1 (Fall)"),
    ("gem explorer", "Semester 1 (Fall)"),
    ("semester 2", "Semester 2 (Spring)"),
    ("sem 2", "Semester 2 (Spring)"),
    ("spring", "Semester 2 (Spring)"),
]

_CURRENCY = {
    "sgd": "SGD", "s$": "SGD", "singapore dollar": "SGD",
    "usd": "USD", "us$": "USD", "dollar": "USD",
    "eur": "EUR", "euro": "EUR", "€": "EUR",
    "gbp": "GBP", "pound": "GBP", "£": "GBP",
    "jpy": "JPY", "yen": "JPY", "¥": "JPY",
    "krw": "KRW", "won": "KRW",
    "cny": "CNY", "rmb": "CNY", "yuan": "CNY",
    "hkd": "HKD", "aud": "AUD", "cad": "CAD", "twd": "TWD",
}


def extract_fallback(raw_input: str) -> RawProfileExtraction:
    text = raw_input or ""
    lower = text.lower()

    semester = None
    for key, canonical in _SEMESTERS:
        if key in lower:
            semester = canonical
            break

    school = None
    hit = extract_programme_from_message(text)
    if hit:
        school = hit[0]

    currency = None
    for key, code in _CURRENCY.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            if key not in ("dollar",):
                currency = code
                break

    budget = None
    m = re.search(
        r"(?:budget|around|about)?\s*([0-9]{1,3}(?:,[0-9]{3})+|[0-9]+(?:\.[0-9]+)?)\s*(k|m)?\s*(sgd|usd|eur|jpy|yen|gbp|krw|hkd|aud)?",
        lower,
    )
    if m and ("budget" in lower or m.group(3)):
        val = float(m.group(1).replace(",", ""))
        if m.group(2) == "k":
            val *= 1000
        if m.group(2) == "m":
            val *= 1_000_000
        budget = val
        if m.group(3):
            currency = _CURRENCY.get(m.group(3), m.group(3).upper())

    au_value = None
    au_from = None
    au_to = None
    au_m = re.search(
        r"([0-9]+(?:\.[0-9]+)?)\s*(au|ects|cats|credits?)\b.*?\b(to|into|in)\b\s*(au|ects|cats|credits?)",
        lower,
    )
    if au_m:
        au_value = float(au_m.group(1))
        au_from = au_m.group(2)
        au_to = au_m.group(4)

    know = None
    km = re.search(
        r"(?:know more about|tell me about)\s+(.{3,80}?)(?:\?|$)",
        text,
        re.I,
    )
    if km:
        know = km.group(1).strip(" .")

    return RawProfileExtraction(
        school_course=school,
        preferred_semester=semester,
        destination_pref=extract_country_from_message(text),
        budget_amount=budget,
        budget_currency=currency,
        au_value=au_value,
        au_from_unit=au_from,
        au_to_unit=au_to,
        know_more_university=know,
    )
