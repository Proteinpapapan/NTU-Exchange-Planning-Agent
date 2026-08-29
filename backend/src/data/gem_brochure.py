"""On-demand GEM Explorer brochure lookup (housing + course load).

Search is server-rendered HTML. Detail is the public Terra Dotta brochure JSON
behind anonymous OAuth2 — same flow as the earlier GEM ingestion client.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from typing import Optional

import httpx
from rapidfuzz import fuzz

BASE = "https://ntu-sa.terradotta.com"
CLIENT_ID = "453A841344B6D32F2220ECC9C247EEAF"
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

_LINK_RE = re.compile(
    r"""<a[^>]+href=["']([^"']*Program_ID=(\d+)[^"']*)["'][^>]*>(.*?)</a>""",
    re.I | re.S,
)
_HOUSING_RE = re.compile(
    r"hous|accommodat|rent|hostel|residenc|apartment|dorm|lodging|room",
    re.I,
)

GEM_COUNTRY = {
    "UNITED STATES OF AMERICA": "United States",
    "UNITED KINGDOM": "United Kingdom",
    "KOREA, REPUBLIC OF": "South Korea",
    "TURKIYE": "Turkey",
    "CZECHIA": "Czech Republic",
    "TAIWAN": "Taiwan",
    "HONG KONG": "Hong Kong",
    "UNITED ARAB EMIRATES": "United Arab Emirates",
    "RUSSIAN FEDERATION": "Russia",
    "VIET NAM": "Vietnam",
}

TERM_FALLBACKS = {
    "Semester 1 (Fall)": ["Semester 1 (Fall)"],
    "Semester 2 (Spring)": ["Semester 2 (Spring)"],
    "SUSEP Sem 1 (Fall)": ["SUSEP Sem 1 (Fall)", "Semester 1 (Fall)"],
    "SUSEP Sem 2 (Spring)": ["SUSEP Sem 2 (Spring)", "Semester 2 (Spring)"],
}


def gem_country_name(coursefinder_country: str | None) -> str | None:
    raw = (coursefinder_country or "").strip()
    if not raw:
        return None
    mapped = GEM_COUNTRY.get(raw.upper())
    if mapped:
        return mapped
    return raw.title() if raw.isupper() else raw


def _fold(text: str) -> str:
    return (
        unicodedata.normalize("NFKD", text or "")
        .encode("ascii", "ignore")
        .decode("ascii")
        .lower()
    )


@dataclass
class ProgramStub:
    program_id: str
    gem_name: str
    country: Optional[str] = None


@dataclass
class ProgramDetails:
    gpa_required: Optional[float] = None
    gpa_raw: str = ""
    budget_raw: str = ""
    housing_raw: str = ""
    min_ects: Optional[float] = None
    max_ects: Optional[float] = None
    max_aus_raw: str = ""


class GemClient:
    def __init__(self) -> None:
        self.s = httpx.Client(
            headers={"User-Agent": _UA, "Accept-Language": "en-US,en;q=0.9"},
            follow_redirects=True,
            timeout=httpx.Timeout(25.0, connect=10.0),
        )
        self._access_token: Optional[str] = None
        self._warmed = False

    def _warm(self) -> None:
        if not self._warmed:
            self.s.get(f"{BASE}/index.cfm?FuseAction=Programs.SimpleSearch")
            self._warmed = True

    def _get_token(self) -> str:
        self._warm()
        code = self.s.get(
            f"{BASE}/oauth2/authorize/",
            params={"client_id": CLIENT_ID, "response_type": "code"},
            headers={"Accept": "application/json"},
        ).json()["code"]
        tok = self.s.get(
            f"{BASE}/oauth2/token/",
            params={
                "client_id": CLIENT_ID,
                "grant_type": "authorization_code",
                "scope": "ProgramBrochureRead",
            },
            headers={"Accept": "application/json", "Authorization": code},
        ).json()
        self._access_token = tok["access_token"]
        return self._access_token

    def _auth_header(self, refresh: bool = False) -> dict:
        if refresh or not self._access_token:
            self._get_token()
        return {"Accept": "application/json", "Authorization": f"Bearer {self._access_token}"}

    def search_programs(
        self,
        term: str,
        country: Optional[str] = None,
        program_type: int = 1,
    ) -> list[ProgramStub]:
        self._warm()
        params: dict[str, str | int] = {
            "FuseAction": "Programs.SearchResults",
            "Program_Type_ID": program_type,
            "pt": term,
        }
        if country:
            params["pc"] = country
        r = self.s.get(f"{BASE}/index.cfm", params=params)
        r.raise_for_status()
        return self._parse_search_html(r.text)

    @staticmethod
    def _parse_search_html(html: str) -> list[ProgramStub]:
        seen: dict[str, ProgramStub] = {}
        for m in _LINK_RE.finditer(html):
            pid = m.group(2)
            text = re.sub(r"<[^>]+>", " ", m.group(3))
            text = re.sub(r"\s+", " ", unescape(text)).strip()
            name = re.sub(r"^GEM Explorer:\s*", "", text, flags=re.I).strip()
            country = None
            if "," in name:
                name, country = (p.strip() for p in name.rsplit(",", 1))
            if pid not in seen:
                seen[pid] = ProgramStub(program_id=pid, gem_name=name, country=country)
        return list(seen.values())

    def fetch_program_details(self, program_id: str) -> ProgramDetails:
        url = f"{BASE}/models/services/REST/index.cfm"
        params = {"endpoint": f"/v3/program/{program_id}/brochure"}
        r = self.s.get(url, params=params, headers=self._auth_header())
        if r.status_code == 401:
            r = self.s.get(url, params=params, headers=self._auth_header(refresh=True))
        r.raise_for_status()
        return self._parse_brochure(r.json())

    @classmethod
    def _parse_brochure(cls, j: dict) -> ProgramDetails:
        details = ProgramDetails()
        sections = (j.get("current") or {}).get("sections") or []
        for sec in sections:
            name = (sec.get("sectionDisplayName") or "").strip().lower()
            for w in sec.get("sectionWidgets") or []:
                cis = w.get("contentInformationSheet")
                if isinstance(cis, dict):
                    for p in cis.get("parameters", []):
                        pname = (p.get("parameterName") or "").lower()
                        if "cgpa" in pname or "gpa" in pname:
                            details.gpa_required = cls._parse_gpa(p.get("assignedValues"))
                            raw = p.get("assignedValues")
                            details.gpa_raw = (
                                str(raw[0] if isinstance(raw, list) and raw else raw or "")
                            ).strip()
                html = w.get("contentHTML") or ""
                if not html:
                    continue
                text = cls._strip_html(html)
                if not text:
                    continue
                if any(k in name for k in ("financial", "accommod", "hous", "living", "budget")):
                    details.budget_raw = (details.budget_raw + " " + text).strip()[:2500]
                if "coursework" in name or "course load" in name:
                    if re.search(r"course\s*load|ects|credit", text, re.I):
                        details.max_aus_raw = (details.max_aus_raw + " " + text).strip()[:2000]
        details.housing_raw = cls._housing_excerpt(details.budget_raw)
        details.min_ects, details.max_ects = cls._parse_ects_range(details.max_aus_raw)
        return details

    @staticmethod
    def _strip_html(html: str) -> str:
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html))).strip()

    @staticmethod
    def _parse_gpa(values) -> Optional[float]:
        if not values:
            return None
        raw = values[0] if isinstance(values, list) else values
        m = re.search(r"(\d+(?:\.\d+)?)", str(raw))
        return float(m.group(1)) if m else None

    @staticmethod
    def _parse_ects_range(text: str) -> tuple[Optional[float], Optional[float]]:
        if not text:
            return None, None
        m = re.search(
            r"minimum\s+maximum\s+(\d+(?:\.\d+)?)\s*ects\s+(\d+(?:\.\d+)?)\s*ects",
            text,
            re.I,
        )
        if m:
            return float(m.group(1)), float(m.group(2))
        mx = None
        m = re.search(r"maximum\D{0,20}(\d{1,3}(?:\.\d+)?)\s*ects", text, re.I)
        if m:
            mx = float(m.group(1))
        else:
            ects = [float(x) for x in re.findall(r"(\d{1,3}(?:\.\d+)?)\s*ects", text, re.I)]
            mx = max(ects) if ects else None
        mn = None
        m = re.search(r"minimum\D{0,20}(\d{1,3}(?:\.\d+)?)\s*ects", text, re.I)
        if m:
            mn = float(m.group(1))
        return mn, mx

    @staticmethod
    def _housing_excerpt(text: str) -> str:
        if not text:
            return ""
        parts = re.split(r"(?<=[.!?])\s+", text)
        hits = [p.strip() for p in parts if _HOUSING_RE.search(p)]
        if hits:
            return " ".join(hits)[:1600]
        return text[:1600]


_client: GemClient | None = None


def _gem() -> GemClient:
    global _client
    if _client is None:
        _client = GemClient()
    return _client


def _best_stub(stubs: list[ProgramStub], uni_name: str) -> ProgramStub | None:
    if not stubs:
        return None
    target = _fold(uni_name)
    best: tuple[float, ProgramStub] | None = None
    for stub in stubs:
        folded = _fold(stub.gem_name)
        score = max(
            fuzz.WRatio(target, folded),
            fuzz.token_set_ratio(target, folded),
        )
        if best is None or score > best[0]:
            best = (score, stub)
    if not best:
        return None
    score, stub = best
    if score >= 70:
        return stub
    if score >= 55 and any(tok in _fold(stub.gem_name) for tok in target.split() if len(tok) > 3):
        return stub
    return None


def _empty(error: str) -> dict:
    return {
        "gem_program": None,
        "term": None,
        "source": None,
        "housing": None,
        "course_load_raw": None,
        "min_ects": None,
        "max_ects": None,
        "min_au": None,
        "max_au": None,
        "au_note": "2 ECTS ≈ 1 NTU AU",
        "gpa": None,
        "brochure_url": None,
        "error": error,
    }


def lookup_brochure(name: str, country: str | None, term: str | None) -> dict:
    """Find the GEM Explorer program matching this Coursefinder university."""
    terms = TERM_FALLBACKS.get(term or "", [])
    if not terms:
        terms = [term] if term else ["Semester 1 (Fall)", "Semester 2 (Spring)"]
    country_name = gem_country_name(country)
    last_error = "No matching GEM Explorer programme was found."
    client = _gem()
    for pt in terms:
        try:
            stubs = client.search_programs(term=pt, country=country_name)
            if not stubs and country_name:
                stubs = client.search_programs(term=pt, country=None)
            stub = _best_stub(stubs, name)
            if not stub:
                last_error = (
                    f"GEM Explorer had no close match for {name} in {country_name or 'any country'}."
                )
                continue
            details = client.fetch_program_details(stub.program_id)
            min_ects = details.min_ects
            max_ects = details.max_ects
            min_au = round(min_ects / 2.0, 2) if min_ects is not None else None
            max_au = round(max_ects / 2.0, 2) if max_ects is not None else None
            housing = details.housing_raw.replace("**", " ").strip() or details.budget_raw or None
            if housing:
                housing = re.sub(r"\s+", " ", housing).strip()
            return {
                "gem_program": stub.gem_name,
                "term": pt,
                "source": "GEM Explorer",
                "housing": housing,
                "course_load_raw": details.max_aus_raw or None,
                "min_ects": min_ects,
                "max_ects": max_ects,
                "min_au": min_au,
                "max_au": max_au,
                "au_note": "2 ECTS ≈ 1 NTU AU",
                "gpa": details.gpa_raw or None,
                "brochure_url": (
                    f"{BASE}/index.cfm?FuseAction=Programs.ViewProgram&Program_ID={stub.program_id}"
                ),
                "error": None if (housing or details.max_aus_raw) else (
                    "GEM Explorer opened, but housing and course-load text were empty on the brochure."
                ),
            }
        except Exception:
            last_error = "Could not reach GEM Explorer just now."
            continue
    return _empty(last_error)


@lru_cache(maxsize=64)
def cached_brochure(name: str, country: str, term: str) -> dict:
    return lookup_brochure(name, country or None, term or None)
