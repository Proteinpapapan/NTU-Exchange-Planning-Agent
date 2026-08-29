"""Shared LangGraph state and Pydantic contracts."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Optional, TypedDict

from pydantic import BaseModel, Field

SemesterLiteral = Literal[
    "Semester 1 (Fall)",
    "Semester 2 (Spring)",
    "SUSEP Sem 1 (Fall)",
    "SUSEP Sem 2 (Spring)",
]

SEMESTER_TO_PROGRAMME: dict[str, str] = {
    "Semester 1 (Fall)": "GEMX",
    "Semester 2 (Spring)": "GEMX",
    "SUSEP Sem 1 (Fall)": "SUSEP",
    "SUSEP Sem 2 (Spring)": "SUSEP",
}

REQUIRED_FIELDS: list[str] = ["school_course", "preferred_semester"]

CLARIFICATION_QUESTIONS: dict[str, str] = {
    "school_course": (
        "Which NTU degree programme are you in? "
        "A code is fine (e.g. CSC, EEE, BUS) or the full name."
    ),
    "preferred_semester": (
        "Which exchange programme are you planning for — "
        "Semester 1 (Fall), Semester 2 (Spring), "
        "SUSEP Sem 1 (Fall), or SUSEP Sem 2 (Spring)?"
    ),
}


class RawProfileExtraction(BaseModel):
    school_course: Optional[str] = None
    preferred_semester: Optional[SemesterLiteral] = None
    destination_pref: Optional[str] = None
    budget_amount: Optional[float] = None
    budget_currency: Optional[str] = None
    named_university: Optional[str] = None
    know_more_university: Optional[str] = None
    au_value: Optional[float] = None
    au_from_unit: Optional[str] = None
    au_to_unit: Optional[str] = None
    preferences_free_text: str = ""


class StudentProfile(BaseModel):
    school_code: str
    school_name: str
    preferred_semester: SemesterLiteral
    programme_type: str
    destination_pref: Optional[str] = None
    budget_amount: Optional[float] = None
    budget_currency: Optional[str] = None
    named_university: Optional[str] = None
    preferences_free_text: str = ""


class MappingRow(BaseModel):
    mapping_id: int
    host_module_code: str
    host_module_title: str
    ntu_module_code: str
    ntu_module_title: str
    ntu_module_type: str = ""
    credits: float = 0.0
    year: str = ""
    sem: str = ""
    has_details: bool = True


class UniversityCard(BaseModel):
    university_id: int
    name: str
    country: str
    approved_count: int
    programme_type: str
    mappings_preview: list[MappingRow] = Field(default_factory=list)
    preview_shown: int = 0


class Plan(BaseModel):
    need_mapping: bool = True
    need_au: bool = False
    need_fx: bool = False
    need_research: bool = False
    critique: str = ""


class ConversionResult(BaseModel):
    kind: str
    summary: str
    details: dict[str, Any] = Field(default_factory=dict)


def _merge_raw_profile(
    existing: Optional[RawProfileExtraction],
    incoming: Optional[RawProfileExtraction],
) -> RawProfileExtraction:
    if existing is None:
        return incoming or RawProfileExtraction()
    if incoming is None:
        return existing
    merged = existing.model_dump()
    for key, value in incoming.model_dump().items():
        if key == "preferences_free_text":
            if value:
                merged[key] = value
            continue
        if value is not None:
            merged[key] = value
    return RawProfileExtraction(**merged)


class ExchangeState(TypedDict, total=False):
    raw_input: str
    raw_profile: Annotated[RawProfileExtraction, _merge_raw_profile]
    profile: Optional[StudentProfile]
    plan: Plan
    results: list[UniversityCard]
    total_universities: int
    conversions: list[ConversionResult]
    research: Optional[str]
    final_report: str
    ui_payload: dict[str, Any]
    messages: list
    clarification_needed: bool
    clarification_question: Optional[str]
    retry_count: int
    session_id: Optional[str]
