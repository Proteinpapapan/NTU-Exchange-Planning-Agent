"""Read-only Coursefinder access. Numbers never come from the LLM."""

from __future__ import annotations

import sqlite3
from functools import lru_cache

from graph.config import coursefinder_db_path
from graph.state import MappingRow, UniversityCard

PREVIEW_MODULES = 5
PAGE_SIZE = 6


def _connect() -> sqlite3.Connection:
    path = coursefinder_db_path()
    if not path.exists():
        raise FileNotFoundError(f"coursefinder.db not found at {path}")
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


@lru_cache(maxsize=1)
def _shared_conn() -> sqlite3.Connection:
    return _connect()


def _parse_au(raw: str | None) -> float:
    if raw is None:
        return 0.0
    try:
        return float(str(raw).strip())
    except (TypeError, ValueError):
        return 0.0


def list_programmes() -> list[tuple[str, str]]:
    rows = _shared_conn().execute(
        "SELECT code, name FROM school_programmes ORDER BY code"
    ).fetchall()
    return [(r["code"], r["name"]) for r in rows]


@lru_cache(maxsize=1)
def programme_index() -> list[tuple[str, str]]:
    return list_programmes()


def list_countries() -> list[str]:
    rows = _shared_conn().execute(
        "SELECT DISTINCT country FROM universities WHERE country IS NOT NULL ORDER BY 1"
    ).fetchall()
    return [r["country"] for r in rows]


def _module_from_row(r: sqlite3.Row) -> MappingRow:
    return MappingRow(
        mapping_id=int(r["mapping_id"]),
        host_module_code=(r["host_module"] or "").strip(),
        host_module_title=(r["host_module_title"] or "").strip(),
        ntu_module_code=(r["ntu_module"] or "").strip(),
        ntu_module_title=(r["ntu_module_title"] or "").strip(),
        ntu_module_type=(r["ntu_module_type"] or "").strip(),
        credits=_parse_au(r["au"]),
        year=(r["year"] or "").strip(),
        sem=(r["sem"] or "").strip(),
        has_details=True,
    )


def eligible_universities(
    school_code: str,
    programme_type: str,
    country_substr: str | None = None,
    name_substr: str | None = None,
    offset: int = 0,
    limit: int = PAGE_SIZE,
) -> tuple[list[UniversityCard], int]:
    """Universities with at least one Approved mapping. Rejected-only omitted."""
    conn = _shared_conn()
    where = [
        "m.school_code_queried = ?",
        "m.status = 'Approved'",
        "m.programme_type = ?",
    ]
    params: list[object] = [school_code, programme_type]
    if country_substr:
        where.append("UPPER(u.country) = ?")
        params.append(country_substr.strip().upper())
    if name_substr:
        where.append("UPPER(u.name) LIKE ?")
        params.append(f"%{name_substr.strip().upper()}%")

    clause = " AND ".join(where)
    total = conn.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT u.university_id
            FROM mappings m
            JOIN universities u ON u.university_id = m.university_id
            WHERE {clause}
            GROUP BY u.university_id
        )
        """,
        params,
    ).fetchone()[0]

    uni_rows = conn.execute(
        f"""
        SELECT u.university_id, u.name, u.country, COUNT(*) AS approved_count
        FROM mappings m
        JOIN universities u ON u.university_id = m.university_id
        WHERE {clause}
        GROUP BY u.university_id
        ORDER BY approved_count DESC, u.name
        LIMIT ? OFFSET ?
        """,
        (*params, limit, offset),
    ).fetchall()

    cards: list[UniversityCard] = []
    for u in uni_rows:
        preview = lookup_modules(
            university_id=int(u["university_id"]),
            school_code=school_code,
            programme_type=programme_type,
            offset=0,
            limit=PREVIEW_MODULES,
        )
        cards.append(
            UniversityCard(
                university_id=int(u["university_id"]),
                name=u["name"],
                country=u["country"] or "",
                approved_count=int(u["approved_count"]),
                programme_type=programme_type,
                mappings_preview=preview,
                preview_shown=len(preview),
            )
        )
    return cards, int(total)


# Core / Major-PE first, other types next, BDE (and UE) last.
_TYPE_RANK_SQL = """
CASE
  WHEN UPPER(TRIM(COALESCE(ntu_module_type, ''))) IN ('CORE', 'GER-CORE') THEN 0
  WHEN UPPER(REPLACE(TRIM(COALESCE(ntu_module_type, '')), ' ', ''))
       IN ('MAJOR-PE', 'MAJORPE', '2NDSPEC-PE', '2ND-SPEC-PE') THEN 1
  WHEN UPPER(TRIM(COALESCE(ntu_module_type, ntu_module, ''))) IN ('BDE', 'UE') THEN 9
  ELSE 5
END
"""


def lookup_modules(
    university_id: int,
    school_code: str,
    programme_type: str,
    offset: int = 0,
    limit: int = PREVIEW_MODULES,
) -> list[MappingRow]:
    rows = _shared_conn().execute(
        f"""
        SELECT mapping_id, host_module, host_module_title,
               ntu_module, ntu_module_title, ntu_module_type, au, year, sem
        FROM mappings
        WHERE university_id = ?
          AND school_code_queried = ?
          AND status = 'Approved'
          AND programme_type = ?
        ORDER BY {_TYPE_RANK_SQL}, ntu_module, host_module
        LIMIT ? OFFSET ?
        """,
        (university_id, school_code, programme_type, limit, offset),
    ).fetchall()
    seen: set[tuple[str, str]] = set()
    out: list[MappingRow] = []
    for r in rows:
        key = ((r["host_module"] or "").strip(), (r["ntu_module"] or "").strip())
        if key in seen:
            continue
        seen.add(key)
        out.append(_module_from_row(r))
    return out


def mapping_details(mapping_id: int) -> dict[str, str]:
    """Expanded 'Click here to show more details' panel from submission_fields."""
    conn = _shared_conn()
    sub = conn.execute(
        """
        SELECT submission_id FROM submissions
        WHERE mapping_id = ?
        ORDER BY submission_number DESC
        LIMIT 1
        """,
        (mapping_id,),
    ).fetchone()
    if not sub:
        return {}
    rows = conn.execute(
        "SELECT label, value FROM submission_fields WHERE submission_id = ?",
        (sub["submission_id"],),
    ).fetchall()
    return {r["label"]: (r["value"] or "").strip() for r in rows}


def university_by_id(university_id: int) -> tuple[int, str, str] | None:
    row = _shared_conn().execute(
        "SELECT university_id, name, country FROM universities WHERE university_id = ?",
        (university_id,),
    ).fetchone()
    if not row:
        return None
    return int(row["university_id"]), row["name"], row["country"] or ""


def search_university_name(query: str, limit: int = 8) -> list[tuple[int, str, str]]:
    q = (query or "").strip()
    if not q:
        return []
    rows = _shared_conn().execute(
        """
        SELECT university_id, name, country FROM universities
        WHERE UPPER(name) LIKE ?
        ORDER BY LENGTH(name)
        LIMIT ?
        """,
        (f"%{q.upper()}%", limit),
    ).fetchall()
    return [(int(r["university_id"]), r["name"], r["country"] or "") for r in rows]


def db_stats() -> dict:
    conn = _shared_conn()
    return {
        "universities": conn.execute("SELECT COUNT(*) FROM universities").fetchone()[0],
        "mappings": conn.execute("SELECT COUNT(*) FROM mappings").fetchone()[0],
        "approved": conn.execute(
            "SELECT COUNT(*) FROM mappings WHERE status='Approved'"
        ).fetchone()[0],
        "programmes": conn.execute("SELECT COUNT(*) FROM school_programmes").fetchone()[0],
        "path": str(coursefinder_db_path()),
    }
