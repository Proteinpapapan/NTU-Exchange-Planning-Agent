"""AU conversion specialist."""

from __future__ import annotations

from data.au_units import convert
from graph.state import ConversionResult, ExchangeState, Plan, RawProfileExtraction


def au_agent(state: ExchangeState) -> dict:
    plan: Plan = state.get("plan") or Plan()
    raw = state.get("raw_profile") or RawProfileExtraction()
    existing = list(state.get("conversions") or [])
    if not plan.need_au or raw.au_value is None:
        return {"conversions": existing}
    try:
        details = convert(raw.au_value, raw.au_from_unit or "AU", raw.au_to_unit or "ECTS")
        summary = (
            f"{details['input_value']:g} {details['from_unit'].upper()} = "
            f"{details['output_value']:g} {details['to_unit'].upper()} "
            f"(≈ {details['au_equivalent']:g} NTU AU). {details['note']}"
        )
        existing.append(ConversionResult(kind="au", summary=summary, details=details))
    except ValueError as e:
        existing.append(ConversionResult(kind="au", summary=str(e), details={}))
    return {"conversions": existing}
