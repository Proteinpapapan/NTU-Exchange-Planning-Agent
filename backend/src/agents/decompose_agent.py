"""Decomposition agent — short todo list of which specialists to run."""

from __future__ import annotations

from graph.state import ExchangeState, Plan, RawProfileExtraction, StudentProfile


def decompose_agent(state: ExchangeState) -> dict:
    raw = state.get("raw_profile") or RawProfileExtraction()
    profile: StudentProfile | None = state.get("profile")
    critique = (state.get("plan").critique if state.get("plan") else "") or ""

    need_mapping = profile is not None
    need_au = raw.au_value is not None and raw.au_from_unit and raw.au_to_unit
    need_fx = (
        raw.budget_amount is not None
        and (raw.budget_currency or "SGD").upper() != "SGD"
    )
    need_research = bool(raw.know_more_university or (profile and profile.named_university and "know more" in (state.get("raw_input") or "").lower()))

    if "research" in critique.lower():
        need_research = True
    if "mapping" in critique.lower():
        need_mapping = True

    plan = Plan(
        need_mapping=need_mapping,
        need_au=bool(need_au),
        need_fx=need_fx,
        need_research=need_research,
        critique=critique,
    )
    return {
        "plan": plan,
        "retry_count": state.get("retry_count") or 0,
        "conversions": [],
        "research": None if need_research else state.get("research"),
    }
