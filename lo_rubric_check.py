"""
lo_rubric_check.py — UNESCO AI-CFT LO rubric presentation (simple assessment path).

Replaces the archived ECD multi-layer evidence-threshold chain
(see archive/ecd_v1/README.md). The researcher reviews every portfolio manually;
this module does NOT compute sufficiency, confidence ceilings, or competency levels.

It only:
  1. Loads official LO reference text from mappings/AICFT_assessment_framework.json
  2. Groups raw evidence excerpts by LO code
  3. Formats LO text beside excerpts for human review
  4. Validates structured researcher decisions (met/partial/not_met/insufficient_data)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

REPO_ROOT = Path(__file__).resolve().parent
AICFT_FRAMEWORK_PATH = REPO_ROOT / "mappings" / "AICFT_assessment_framework.json"

ProgressionLevel = Literal["Acquire", "Deepen", "Create"]
EvidenceSource = Literal["worksheet", "codap_log", "screen_recording"]
RubricDecision = Literal["met", "partial", "not_met", "insufficient_data"]

_LEVEL_NORMALIZE = {
    "acquire": "Acquire",
    "deepen": "Deepen",
    "create": "Create",
    "acquire-to-deepen": "Acquire",
    "acquire-to-deepen_boundary": "Acquire",
    "deepen-to-create": "Deepen",
}


class LOReferenceText(BaseModel):
    """UNESCO AI-CFT LO indicator text assembled from the project framework file."""

    lo_code: str = Field(description="e.g. LO3.2.1")
    full_text: str = Field(description="Title, scope, and UNESCO reference for this LO")
    progression_level: ProgressionLevel

    @field_validator("lo_code")
    @classmethod
    def _lo_prefix(cls, value: str) -> str:
        if not value.startswith("LO3."):
            raise ValueError("lo_code must be an Aspect 3 LO (LO3.x.x)")
        return value


class EvidenceExcerpt(BaseModel):
    """Single raw evidence fragment — no automated strength or confidence."""

    source: EvidenceSource
    excerpt: str = Field(min_length=1, description="Verbatim quote, response text, or log line")
    timestamp: str | None = None
    worksheet: str | None = Field(
        default=None,
        description="Worksheet id when source is worksheet (e.g. WS1, WS_DT)",
    )
    item_id: str | None = Field(default=None, description="Rubric item id when applicable")


class ResearcherRubricDecision(BaseModel):
    """Researcher's decision for one LO — judgement is entered by the human only."""

    lo_code: str
    candidate_id: str = Field(description="Student / portfolio id (e.g. Sample_Student)")
    decision: RubricDecision
    supporting_evidence: list[EvidenceExcerpt] = Field(
        min_length=1,
        description="Evidence excerpts selected by the researcher to support the decision",
    )
    researcher_note: str = Field(
        min_length=8,
        description="One-sentence rationale for this decision",
    )

    @field_validator("researcher_note")
    @classmethod
    def _note_not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("researcher_note must not be empty")
        return value.strip()


def _normalize_level(raw: str) -> ProgressionLevel:
    key = raw.strip().lower().replace(" ", "_")
    if key in _LEVEL_NORMALIZE:
        return _LEVEL_NORMALIZE[key]  # type: ignore[return-value]
    for level in ("Acquire", "Deepen", "Create"):
        if level.lower() in key:
            return level  # type: ignore[return-value]
    return "Deepen"


def load_lo_catalog(path: Path | None = None) -> dict[str, LOReferenceText]:
    """Build LO reference objects from mappings/AICFT_assessment_framework.json."""
    data = json.loads((path or AICFT_FRAMEWORK_PATH).read_text(encoding="utf-8"))
    defs: dict[str, Any] = data.get("competency_definitions", {})
    out: dict[str, LOReferenceText] = {}
    for lo_code, spec in sorted(defs.items()):
        title = spec.get("title", "").strip()
        scope = spec.get("scope", "").strip()
        unesco = spec.get("unesco_reference", "").strip()
        parts = [p for p in (title, scope, unesco) if p]
        full_text = "\n\n".join(parts) if parts else title or lo_code
        out[lo_code] = LOReferenceText(
            lo_code=lo_code,
            full_text=full_text,
            progression_level=_normalize_level(spec.get("expected_level", "Deepen")),
        )
    return out


def present_for_review(lo: LOReferenceText, evidence: list[EvidenceExcerpt]) -> str:
    """
    Format LO text and evidence side by side for researcher reading.
    Does not score, threshold, or recommend a competency level.
    """
    lines = [
        f"=== {lo.lo_code} ({lo.progression_level}) ===",
        lo.full_text,
        "",
        "--- Kanıt ---",
    ]
    if not evidence:
        lines.append("(Bu LO için otomatik toplanan kanıt yok — portföyü elle kontrol edin.)")
    for e in evidence:
        ts = f" [{e.timestamp}]" if e.timestamp else ""
        ws = f" {e.worksheet}" if e.worksheet else ""
        item = f"/{e.item_id}" if e.item_id else ""
        lines.append(f"[{e.source}]{ws}{item}{ts} {e.excerpt}")
    return "\n".join(lines)


def validate_researcher_decisions(
    decisions: list[ResearcherRubricDecision] | list[dict[str, Any]],
) -> list[ResearcherRubricDecision]:
    """Return validated decisions (Pydantic parse). Raises on invalid input. Empty list is valid."""
    out: list[ResearcherRubricDecision] = []
    for d in decisions:
        if isinstance(d, ResearcherRubricDecision):
            out.append(d)
        else:
            out.append(ResearcherRubricDecision.model_validate(d))
    return out


class ResearcherDecisionCompleteness(BaseModel):
    """Non-judgemental completeness report for researcher LO decisions."""

    recorded_count: int = Field(ge=0)
    expected_lo_count: int = Field(ge=0)
    status: Literal["pending", "partial", "complete"]
    message: str


def assess_researcher_decision_completeness(
    decisions: list[ResearcherRubricDecision] | list[dict[str, Any]],
    *,
    expected_lo_codes: list[str] | None = None,
) -> ResearcherDecisionCompleteness:
    """
    Report how many LO decisions are recorded vs expected.
    Empty decisions → status 'pending' (not an error).
    """
    validated = validate_researcher_decisions(decisions) if decisions else []
    expected = sorted(expected_lo_codes or load_lo_catalog().keys())
    recorded = len(validated)
    expected_n = len(expected)
    if recorded == 0:
        return ResearcherDecisionCompleteness(
            recorded_count=0,
            expected_lo_count=expected_n,
            status="pending",
            message=f"0/{expected_n} LO için karar verildi; araştırmacı incelemesi bekliyor.",
        )
    if recorded < expected_n:
        return ResearcherDecisionCompleteness(
            recorded_count=recorded,
            expected_lo_count=expected_n,
            status="partial",
            message=f"{recorded}/{expected_n} LO için karar verildi; kalan LO'lar bekliyor.",
        )
    return ResearcherDecisionCompleteness(
        recorded_count=recorded,
        expected_lo_count=expected_n,
        status="complete",
        message=f"{recorded}/{expected_n} LO için karar verildi.",
    )
