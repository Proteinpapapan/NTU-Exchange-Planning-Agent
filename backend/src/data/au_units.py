"""NTU AU conversions. Arithmetic is table-driven, never LLM-invented."""

from __future__ import annotations

# Host unit -> how many of that unit equal 1 NTU AU.
# 2 ECTS ≈ 1 AU is the heuristic NTU students actually use (30 ECTS ≈ 15 AU).
UNIT_TO_AU: dict[str, float] = {
    "au": 1.0,
    "ntu au": 1.0,
    "academic unit": 1.0,
    "ects": 2.0,
    "us credit": 1.0,
    "us credits": 1.0,
    "semester hour": 1.0,
    "credit hour": 1.0,
    "cats": 4.0,
    "uk cats": 4.0,
    "japan credit": 2.0,
    "japanese credit": 2.0,
    "credits": 2.0,  # host "credits" on Coursefinder are often ECTS-like
}

ALIASES = {
    "european credit": "ects",
    "ects credits": "ects",
    "us": "us credit",
    "usa": "us credit",
    "american credits": "us credit",
    "credit hours": "us credit",
    "uk credits": "cats",
    "japan": "japan credit",
    "jp credits": "japan credit",
}


def _norm(unit: str) -> str | None:
    key = (unit or "").strip().lower()
    key = ALIASES.get(key, key)
    if key in UNIT_TO_AU:
        return key
    for name in UNIT_TO_AU:
        if name in key or key in name:
            return name
    return None


def convert(value: float, from_unit: str, to_unit: str) -> dict:
    src = _norm(from_unit)
    dst = _norm(to_unit)
    if src is None or dst is None:
        known = ", ".join(sorted(set(UNIT_TO_AU) | set(ALIASES)))
        raise ValueError(f"Unknown unit. Known units: {known}")
    aus = value / UNIT_TO_AU[src]
    out = aus * UNIT_TO_AU[dst]
    return {
        "input_value": value,
        "from_unit": src,
        "to_unit": dst,
        "au_equivalent": round(aus, 2),
        "output_value": round(out, 2),
        "note": "2 ECTS ≈ 1 NTU AU; 1 US semester credit ≈ 1 AU; 4 UK CATS ≈ 1 AU.",
    }
