"""Gate: only degree programme + exchange term are required."""

from __future__ import annotations

from data.destinations import match_country
from data.programmes import extract_programme_from_message, resolve_programme
from graph.state import (
    CLARIFICATION_QUESTIONS,
    SEMESTER_TO_PROGRAMME,
    ExchangeState,
    RawProfileExtraction,
    StudentProfile,
)


def first_missing_field(raw: RawProfileExtraction) -> str | None:
    school = raw.school_course
    if not school or (
        resolve_programme(school) is None
        and extract_programme_from_message(school) is None
    ):
        return "school_course"
    if raw.preferred_semester is None:
        return "preferred_semester"
    return None


def _is_side_question(raw: RawProfileExtraction) -> bool:
    return bool(raw.au_value or raw.know_more_university)


def promote_to_profile(raw: RawProfileExtraction) -> StudentProfile:
    hit = resolve_programme(raw.school_course) or extract_programme_from_message(
        raw.school_course
    )
    if hit is None:
        raise ValueError("cannot promote without a resolvable programme")
    code, name = hit
    sem = raw.preferred_semester
    dest = match_country(raw.destination_pref) or raw.destination_pref
    return StudentProfile(
        school_code=code,
        school_name=name,
        preferred_semester=sem,
        programme_type=SEMESTER_TO_PROGRAMME[sem],
        destination_pref=dest,
        budget_amount=raw.budget_amount,
        budget_currency=raw.budget_currency,
        named_university=raw.named_university or raw.know_more_university,
        preferences_free_text=raw.preferences_free_text,
    )


def route_after_intake(state: ExchangeState) -> str:
    raw = state.get("raw_profile") or RawProfileExtraction()
    missing = first_missing_field(raw)
    if missing and not _is_side_question(raw):
        return "clarify"
    return "discover"


def clarify_node(state: ExchangeState) -> dict:
    raw = state.get("raw_profile") or RawProfileExtraction()
    field = first_missing_field(raw)
    question = CLARIFICATION_QUESTIONS.get(field, "Could you tell me a bit more?")
    return {
        "clarification_needed": True,
        "clarification_question": question,
        "final_report": question,
        "results": [],
        "ui_payload": {
            "clarification": question,
            "cards": [],
            "conversions": [],
            "research": None,
        },
    }


def build_profile_node(state: ExchangeState) -> dict:
    raw = state.get("raw_profile") or RawProfileExtraction()
    if first_missing_field(raw):
        return {
            "profile": None,
            "clarification_needed": False,
            "clarification_question": None,
        }
    return {
        "profile": promote_to_profile(raw),
        "clarification_needed": False,
        "clarification_question": None,
    }
