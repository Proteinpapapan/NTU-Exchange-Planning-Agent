"""Mapping specialist — Approved Coursefinder rows only."""

from __future__ import annotations

from data.coursefinder_db import PAGE_SIZE, eligible_universities, search_university_name
from data.destinations import country_query
from graph.state import ExchangeState, Plan, StudentProfile


def mapping_agent(state: ExchangeState) -> dict:
    plan: Plan = state.get("plan") or Plan()
    profile: StudentProfile | None = state.get("profile")
    if not plan.need_mapping or profile is None:
        return {"results": state.get("results") or [], "total_universities": 0}

    country = country_query(profile.destination_pref)

    cards, total = eligible_universities(
        school_code=profile.school_code,
        programme_type=profile.programme_type,
        country_substr=country,
        name_substr=None,
        offset=0,
        limit=PAGE_SIZE,
    )

    # If they named a university, pin it first among the page.
    if profile.named_university:
        hits = search_university_name(profile.named_university, limit=3)
        wanted = {h[1].upper() for h in hits}
        cards.sort(key=lambda c: 0 if c.name.upper() in wanted else 1)

    return {"results": cards, "total_universities": total}
