"""Reflection agent — drop invalid cards. Never discard a country the student named."""

from __future__ import annotations

from graph.state import ExchangeState, Plan, StudentProfile


def reflect_agent(state: ExchangeState) -> dict:
    cards = [c for c in (state.get("results") or []) if c.approved_count >= 1]
    retry = int(state.get("retry_count") or 0)
    profile: StudentProfile | None = state.get("profile")
    plan: Plan = state.get("plan") or Plan()
    critique = ""

    if plan.need_mapping and profile is not None and not cards:
        if profile.destination_pref:
            critique = (
                f"No approved mappings for {profile.school_code} in "
                f"{profile.destination_pref}. Keeping that country filter."
            )
        else:
            critique = (
                "No partner universities have approved mappings for this degree and programme."
            )

    return {
        "results": cards,
        "retry_count": retry,
        "plan": plan.model_copy(update={"critique": critique}),
    }


def route_after_reflect(state: ExchangeState) -> str:
    return "render"
