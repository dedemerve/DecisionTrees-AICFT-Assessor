"""
portfolio_builder.py — Aggregate worksheet evidence for researcher LO rubric review.

Reads students/<id>/<WS>/evidence.json (+ extraction for verbatim text) and writes
students/<id>/portfolio.json. Does not assign AI-CFT levels; see lo_rubric_check.py.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from lo_rubric_check import (
    EvidenceExcerpt,
    LOReferenceText,
    load_lo_catalog,
    present_for_review,
)
from pipeline_schema import load_framework
from student_bundle import (
    artifact_payload,
    build_summary_from_scoring,
    list_worksheets,
    load_artifact,
    save_portfolio,
)

BLANK_SENTINELS = frozenset({
    "(bos)", "(okunamiyor)", "(missing)", "(not_extracted)", "(transcription_error)", "",
})


def _evidence_source_for_worksheet(ws: str) -> str:
    return "codap_log" if ws == "WS_DT" else "worksheet"


def _extraction_responses(extraction: dict[str, Any]) -> dict[str, str]:
    if not extraction:
        return {}
    if extraction.get("gate_1_extraction"):
        return extraction["gate_1_extraction"].get("items", {}) or {}
    return extraction.get("responses") or {}


def collect_worksheet_excerpts_by_lo(student_id: str) -> dict[str, list[EvidenceExcerpt]]:
    """Gather raw evidence excerpts tagged by LO from worksheet pipeline artifacts."""
    by_lo: dict[str, list[EvidenceExcerpt]] = defaultdict(list)

    for ws in list_worksheets(student_id):
        evidence = artifact_payload(load_artifact(student_id, ws, "evidence"))
        extraction = artifact_payload(load_artifact(student_id, ws, "extraction"))
        responses = _extraction_responses(extraction)
        source = _evidence_source_for_worksheet(ws)

        for rec in (evidence or {}).get("items", []):
            item_id = rec.get("item", "")
            verbatim = str(responses.get(item_id, "")).strip()
            for comp in rec.get("competencies") or rec.get("learning_objects") or []:
                lo = comp.get("lo") or comp.get("LO")
                if not lo:
                    continue
                if not comp.get("evidence_present", True):
                    continue
                rationale = (comp.get("rationale") or "").strip()
                if verbatim and verbatim not in BLANK_SENTINELS:
                    excerpt_text = verbatim
                elif rationale:
                    excerpt_text = rationale
                else:
                    continue
                by_lo[lo].append(
                    EvidenceExcerpt(
                        source=source,  # type: ignore[arg-type]
                        excerpt=excerpt_text,
                        worksheet=ws,
                        item_id=item_id,
                    )
                )

        # Extraction-only rows with no evidence.json competency tag are not LO-tagged here.

    return dict(by_lo)


def build_lo_review_packets(
    lo_catalog: dict[str, LOReferenceText],
    evidence_by_lo: dict[str, list[EvidenceExcerpt]],
) -> dict[str, str]:
    """One formatted review block per LO for researcher reading."""
    return {
        lo: present_for_review(lo_catalog[lo], evidence_by_lo.get(lo, []))
        for lo in lo_catalog
    }


def detect_data_gaps(
    student_id: str,
    item_records: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Surface review-flagged and missing-evidence items by worksheet."""
    item_records = item_records or []
    gaps_by_ws: dict[str, dict[str, Any]] = defaultdict(lambda: {"items": [], "reasons": []})

    for ws in list_worksheets(student_id):
        scoring = artifact_payload(load_artifact(student_id, ws, "scoring"))
        extraction = artifact_payload(load_artifact(student_id, ws, "extraction"))
        validation = artifact_payload(load_artifact(student_id, ws, "validation"))

        for item_id in (build_summary_from_scoring(scoring, worksheet=ws).get("review_items") or [] if scoring else []):
            gaps_by_ws[ws]["items"].append(item_id)
            gaps_by_ws[ws]["reasons"].append("flagged for human review (low scorer confidence)")

        if validation.get("blocked"):
            gaps_by_ws[ws]["reasons"].append(
                validation.get("blocked_reason") or "worksheet blocked by technical validation",
            )

        responses = _extraction_responses(extraction)
        for item_id, text in responses.items():
            if str(text).strip() in BLANK_SENTINELS:
                if item_id not in gaps_by_ws[ws]["items"]:
                    gaps_by_ws[ws]["items"].append(item_id)
                    gaps_by_ws[ws]["reasons"].append("blank or missing extraction")

    for rec in item_records:
        if rec.get("review") and rec["item"] not in gaps_by_ws[rec["worksheet"]]["items"]:
            gaps_by_ws[rec["worksheet"]]["items"].append(rec["item"])

    priority_map = {"WS_DT": 1, "WS5": 2, "WS6": 2, "WS7": 2, "WS11": 3, "WS3": 4}
    out: list[dict[str, Any]] = []
    for ws in sorted(gaps_by_ws, key=lambda w: (priority_map.get(w, 9), w)):
        entry = gaps_by_ws[ws]
        if not entry["items"] and not entry["reasons"]:
            continue
        why = "; ".join(dict.fromkeys(entry["reasons"])) if entry["reasons"] else "items need review"
        out.append({
            "worksheet": ws,
            "items": sorted(set(entry["items"])),
            "priority": priority_map.get(ws, 5),
            "why": why,
        })
    return out


def _count_evidence_items(evidence_by_lo: dict[str, list[EvidenceExcerpt]]) -> int:
    return sum(len(v) for v in evidence_by_lo.values())


def build_portfolio(student_id: str) -> dict[str, Any]:
    """Assemble portfolio.json for simple LO rubric researcher review."""
    framework = load_framework()
    lo_catalog = load_lo_catalog()
    evidence_by_lo = collect_worksheet_excerpts_by_lo(student_id)
    review_packets = build_lo_review_packets(lo_catalog, evidence_by_lo)

    worksheets_scored: list[str] = []
    for ws in list_worksheets(student_id):
        if artifact_payload(load_artifact(student_id, ws, "scoring")):
            worksheets_scored.append(ws)

    serializable_evidence = {
        lo: [e.model_dump() for e in excerpts]
        for lo, excerpts in evidence_by_lo.items()
    }

    return {
        "framework": framework["framework"],
        "aspect": framework["aspect"],
        "methodology": {
            "approach": "simple_lo_rubric",
            "ecd_archive": "archive/ecd_v1",
            "aggregation_note": (
                "Evidence excerpts are grouped by LO for side-by-side review with UNESCO indicator text. "
                "No automated AI-CFT level or domain convergence is computed."
            ),
        },
        "worksheets_scored": sorted(worksheets_scored),
        "lo_reference_source": "mappings/AICFT_assessment_framework.json",
        "lo_review_packets": review_packets,
        "evidence_by_lo": serializable_evidence,
        "researcher_rubric_decisions": [],
        "data_gaps": detect_data_gaps(student_id),
        "evidence_item_count": _count_evidence_items(evidence_by_lo),
    }


def build_and_save_portfolio(student_id: str) -> dict[str, Any]:
    portfolio = build_portfolio(student_id)
    save_portfolio(student_id, portfolio)
    return portfolio
