"""University research specialist — GEM Explorer briefing plus mapped-module AU."""

from __future__ import annotations

import re

from data.au_units import convert
from data.coursefinder_db import lookup_modules, mapping_details, search_university_name
from data.gem_brochure import cached_brochure
from graph.state import ExchangeState, Plan, RawProfileExtraction, StudentProfile

HOST_CREDIT_LABEL = "Number of Credits awarded by Host University to this course"


def _parse_credit_number(raw: str | None) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)", raw or "")
    return float(m.group(1)) if m else None


def _module_conversions(university_id: int, school: str, programme_type: str, limit: int = 8) -> list[dict]:
    rows = lookup_modules(university_id, school, programme_type, 0, limit)
    out: list[dict] = []
    for m in rows:
        details = mapping_details(m.mapping_id)
        host_raw = details.get(HOST_CREDIT_LABEL, "")
        host_val = _parse_credit_number(host_raw)
        host_au = None
        if host_val is not None:
            try:
                host_au = convert(host_val, "ects", "au")["au_equivalent"]
            except ValueError:
                host_au = None
        out.append(
            {
                "host_module_code": m.host_module_code,
                "host_module_title": m.host_module_title,
                "ntu_module_code": m.ntu_module_code,
                "mapped_au": m.credits,
                "host_credits": host_val,
                "host_credits_au": host_au,
            }
        )
    return out


def university_briefing(
    *,
    university_id: int | None,
    name: str,
    country: str | None = None,
    term: str | None = None,
    school: str | None = None,
    programme_type: str | None = None,
) -> dict:
    gem = cached_brochure(name, country or "", term or "")
    modules: list[dict] = []
    if university_id and school and programme_type:
        try:
            modules = _module_conversions(university_id, school, programme_type)
        except Exception:
            modules = []
    return {
        "name": name,
        "country": country,
        **gem,
        "module_conversions": modules,
    }


def format_briefing_text(briefing: dict, extra: str = "") -> str:
    bits = [briefing.get("name") or ""]
    if briefing.get("housing"):
        bits.append(briefing["housing"])
    if briefing.get("max_ects") is not None:
        if briefing.get("min_ects") is not None:
            bits.append(
                f"Course load: {briefing['min_ects']:g}–{briefing['max_ects']:g} ECTS ≈ "
                f"{briefing.get('min_au'):g}–{briefing['max_au']:g} NTU AU. "
                f"{briefing.get('au_note') or ''}"
            )
        else:
            bits.append(
                f"Course load: {briefing['max_ects']:g} ECTS ≈ {briefing['max_au']:g} NTU AU. "
                f"{briefing.get('au_note') or ''}"
            )
    elif briefing.get("course_load_raw"):
        bits.append(briefing["course_load_raw"])
    if briefing.get("error") and not briefing.get("housing") and briefing.get("max_ects") is None:
        bits.append(briefing["error"])
    if extra:
        bits.append(extra)
    return " ".join(b for b in bits if b)


def research_university(name: str, extra: str = "") -> str:
    return format_briefing_text(university_briefing(university_id=None, name=name), extra)


def research_agent(state: ExchangeState) -> dict:
    plan: Plan = state.get("plan") or Plan()
    if not plan.need_research:
        return {"research": state.get("research")}
    raw = state.get("raw_profile") or RawProfileExtraction()
    profile: StudentProfile | None = state.get("profile")
    query = raw.know_more_university or (profile.named_university if profile else None)
    if not query:
        return {"research": None}

    hits = search_university_name(query, limit=1)
    extra = ""
    country = None
    term = profile.preferred_semester if profile else None
    school = profile.school_code if profile else None
    programme_type = profile.programme_type if profile else None
    university_id = None
    if hits:
        uid, canon, country = hits[0]
        university_id = uid
        extra = f"Coursefinder name: {canon}. Country: {country}."
        if profile:
            extra += f" Student programme: {profile.school_code} ({profile.school_name}), {profile.preferred_semester}."
        name = canon
    else:
        name = query

    briefing = university_briefing(
        university_id=university_id,
        name=name,
        country=country,
        term=term,
        school=school,
        programme_type=programme_type,
    )
    return {"research": format_briefing_text(briefing, extra)}

