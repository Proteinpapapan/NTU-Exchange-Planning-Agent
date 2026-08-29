"""Convert student budgets into SGD. Live FX with a static fallback."""

from __future__ import annotations

from datetime import date

import httpx

# Approximate mid-2026 fallbacks if the FX API is unreachable.
FALLBACK_TO_SGD = {
    "USD": 1.35,
    "EUR": 1.48,
    "GBP": 1.72,
    "JPY": 0.0091,
    "KRW": 0.00098,
    "CNY": 0.19,
    "HKD": 0.17,
    "AUD": 0.88,
    "CAD": 0.99,
    "CHF": 1.55,
    "SEK": 0.13,
    "TWD": 0.042,
    "THB": 0.041,
    "SGD": 1.0,
}


def convert_to_sgd(amount: float, currency: str) -> dict:
    code = (currency or "SGD").strip().upper()
    if code in ("S$", "S", "$S"):
        code = "SGD"
    if code in ("$", "DOLLAR"):
        code = "USD"
    if code == "SGD":
        return {
            "amount": amount,
            "currency": "SGD",
            "sgd": round(amount, 2),
            "rate": 1.0,
            "as_of": date.today().isoformat(),
            "source": "identity",
        }
    rate = None
    source = "fallback"
    try:
        r = httpx.get(
            "https://api.frankfurter.app/latest",
            params={"amount": amount, "from": code, "to": "SGD"},
            timeout=6.0,
        )
        if r.status_code == 200:
            data = r.json()
            sgd = float(data["rates"]["SGD"])
            rate = sgd / amount if amount else None
            source = "frankfurter.app (ECB)"
            return {
                "amount": amount,
                "currency": code,
                "sgd": round(sgd, 2),
                "rate": round(rate, 6) if rate else None,
                "as_of": data.get("date", date.today().isoformat()),
                "source": source,
            }
    except Exception:
        pass
    if code not in FALLBACK_TO_SGD:
        raise ValueError(f"Unsupported currency {code}")
    rate = FALLBACK_TO_SGD[code]
    return {
        "amount": amount,
        "currency": code,
        "sgd": round(amount * rate, 2),
        "rate": rate,
        "as_of": date.today().isoformat(),
        "source": "offline fallback rate",
    }
