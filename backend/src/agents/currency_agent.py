"""Currency conversion specialist."""

from __future__ import annotations

from data.currency import convert_to_sgd
from graph.state import ConversionResult, ExchangeState, Plan, RawProfileExtraction


def currency_agent(state: ExchangeState) -> dict:
    plan: Plan = state.get("plan") or Plan()
    raw = state.get("raw_profile") or RawProfileExtraction()
    existing = list(state.get("conversions") or [])
    if not plan.need_fx or raw.budget_amount is None:
        return {"conversions": existing}
    try:
        details = convert_to_sgd(raw.budget_amount, raw.budget_currency or "SGD")
        summary = (
            f"{details['amount']:g} {details['currency']} ≈ S${details['sgd']:,.2f} "
            f"(rate {details['rate']}, {details['as_of']}, {details['source']})"
        )
        existing.append(ConversionResult(kind="fx", summary=summary, details=details))
    except ValueError as e:
        existing.append(ConversionResult(kind="fx", summary=str(e), details={}))
    return {"conversions": existing}
