"""Country / destination string helpers."""

from __future__ import annotations

import re

COUNTRY_ALIASES = {
    "usa": "UNITED STATES OF AMERICA",
    "us": "UNITED STATES OF AMERICA",
    "united states": "UNITED STATES OF AMERICA",
    "america": "UNITED STATES OF AMERICA",
    "uk": "UNITED KINGDOM",
    "britain": "UNITED KINGDOM",
    "england": "UNITED KINGDOM",
    "korea": "KOREA, REPUBLIC OF",
    "south korea": "KOREA, REPUBLIC OF",
    "turkey": "TURKIYE",
    "turkiye": "TURKIYE",
    "hongkong": "HONG KONG",
    "hong kong": "HONG KONG",
    "uae": "UNITED ARAB EMIRATES",
    "czech": "CZECHIA",
    "czech republic": "CZECHIA",
    "spain": "SPAIN",
    "japan": "JAPAN",
    "france": "FRANCE",
    "germany": "GERMANY",
    "canada": "CANADA",
    "australia": "AUSTRALIA",
    "singapore": "SINGAPORE",
    "netherlands": "NETHERLANDS",
    "sweden": "SWEDEN",
    "finland": "FINLAND",
    "italy": "ITALY",
    "taiwan": "TAIWAN",
    "china": "CHINA",
}


def _countries() -> list[str]:
    from data.coursefinder_db import list_countries

    return list_countries()


def match_country(destination: str | None) -> str | None:
    """Return the Coursefinder country label, or None."""
    if not destination:
        return None
    key = destination.strip().lower()
    if key in ("europe", "asia", "asia-pacific", "oceania", "anywhere", "any"):
        return None
    aliased = COUNTRY_ALIASES.get(key)
    countries = _countries()
    by_upper = {c.upper(): c for c in countries}
    if aliased:
        return by_upper.get(aliased.upper(), aliased)
    if destination.strip().upper() in by_upper:
        return by_upper[destination.strip().upper()]
    for c in countries:
        if key in c.lower() or c.lower() in key:
            return c
    return destination.strip().upper()


def country_query(destination: str | None) -> str | None:
    matched = match_country(destination)
    if not matched:
        return None
    return matched.upper()


def extract_country_from_message(text: str | None) -> str | None:
    if not text:
        return None
    lower = text.lower()
    for alias, canon in sorted(COUNTRY_ALIASES.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(alias)}\b", lower):
            return match_country(canon)
    try:
        countries = _countries()
    except Exception:
        countries = []
    for country in countries:
        head = country.split(",")[0].strip().lower()
        if len(head) < 4:
            continue
        if re.search(rf"\b{re.escape(head)}\b", lower):
            return country
    return None
