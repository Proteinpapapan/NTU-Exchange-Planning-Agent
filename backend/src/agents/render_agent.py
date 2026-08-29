"""Turn specialist output into narration + structured UI payload."""

from __future__ import annotations

from graph.llm import get_llm, llm_available
from graph.state import ExchangeState, StudentProfile, UniversityCard

TOP_SHOWN = 6


def _intro_fallback(state: ExchangeState) -> str:
    profile: StudentProfile | None = state.get("profile")
    cards: list[UniversityCard] = state.get("results") or []
    total = state.get("total_universities") or len(cards)
    conversions = state.get("conversions") or []
    research = state.get("research")
    bits: list[str] = []
    if profile:
        dest = f" in {profile.destination_pref}" if profile.destination_pref else ""
        bits.append(
            f"Here are partner universities with previously approved mappings "
            f"for {profile.school_name} ({profile.school_code}) on "
            f"{profile.preferred_semester}{dest}."
        )
        if total:
            bits.append(
                f"{total} universities have at least one approved mapping; "
                f"showing {min(len(cards), TOP_SHOWN)} first, ranked by catalogue depth."
            )
        else:
            bits.append("No universities with approved mappings matched those filters.")
        critique = ""
        plan = state.get("plan")
        if plan and getattr(plan, "critique", ""):
            critique = plan.critique
        if critique:
            bits.append(critique)
    if conversions:
        bits.extend(c.summary for c in conversions)
    if research:
        bits.append(research)
    if not bits:
        bits.append("Tell me your degree programme and which of the four exchange terms you want.")
    return " ".join(bits)


def _maybe_llm_intro(state: ExchangeState, fallback: str) -> str:
    profile: StudentProfile | None = state.get("profile")
    cards: list[UniversityCard] = state.get("results") or []
    if not llm_available() or not cards:
        return fallback
    facts = "; ".join(
        f"{c.name} ({c.country}, {c.approved_count} approved)" for c in cards[:6]
    )
    who = ""
    if profile:
        who = f"{profile.school_code}, {profile.preferred_semester}"
    try:
        llm = get_llm(temperature=0.3)
        resp = llm.invoke(
            [
                (
                    "system",
                    "Write 2 short sentences for an NTU student. Use ONLY the facts. "
                    "Do not invent universities or counts. No markdown.",
                ),
                ("human", f"Student: {who}\nUniversities: {facts}"),
            ]
        )
        text = (getattr(resp, "content", "") or "").strip()
        return text or fallback
    except Exception:
        return fallback


def render_agent(state: ExchangeState) -> dict:
    cards: list[UniversityCard] = state.get("results") or []
    conversions = state.get("conversions") or []
    narration = _maybe_llm_intro(state, _intro_fallback(state))
    research = state.get("research")
    payload = {
        "clarification": None,
        "narration": narration,
        "cards": [c.model_dump() for c in cards],
        "total_universities": state.get("total_universities") or len(cards),
        "conversions": [c.model_dump() for c in conversions],
        "research": research,
        "profile": state["profile"].model_dump() if state.get("profile") else None,
        "has_more": (state.get("total_universities") or 0) > len(cards),
    }
    return {"final_report": narration, "ui_payload": payload}
