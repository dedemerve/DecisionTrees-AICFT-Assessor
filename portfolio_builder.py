"""
portfolio_builder.py — Aggregate worksheet evidence into AI-CFT portfolio proposals.

Reads all students/<id>/<WS>/evidence.json (+ scoring for review flags) and writes
students/<id>/portfolio.json. AI-CFT level is a researcher-facing *proposal* only.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from pipeline_schema import (
    competency_counts_toward_portfolio_peak,
    framework_item_index,
    load_framework,
)
from student_bundle import (
    artifact_payload,
    build_summary_from_scoring,
    list_worksheets,
    load_artifact,
    save_portfolio,
)

STRENGTH_RANK = {"none": 0, "weak": 1, "moderate": 2, "strong": 3}

ACQUIRE_LOS = ("LO3.1.1", "LO3.1.2", "LO3.1.3")
DEEPEN_LOS = ("LO3.2.1", "LO3.2.2", "LO3.2.3")
CREATE_LOS = ("LO3.3.1",)

OPTIONAL_ACQUIRE = frozenset({"LO3.1.3"})
OPTIONAL_DEEPEN = frozenset({"LO3.2.1"})


def _peak_strength(strengths: list[str]) -> str:
    if not strengths:
        return "none"
    return max(strengths, key=lambda s: STRENGTH_RANK.get(s, 0))


def _find_comp_prior(
    priors: list[dict[str, Any]],
    lo: str,
) -> dict[str, Any]:
    for p in priors:
        if p.get("lo") == lo:
            return p
    return {}


def _collect_worksheet_evidence(
    student_id: str,
    fw_index: dict[tuple[str, str], list[dict[str, Any]]],
) -> tuple[dict[str, Any], list[str], list[dict], list[dict]]:
    """Return (per_lo aggregates, worksheets_scored, item_records, baseline_records)."""
    framework = load_framework()
    competency_defs = framework.get("competency_definitions", {})
    all_los = list(competency_defs.keys())

    per_lo: dict[str, dict[str, Any]] = {
        lo: {
            "peak_strength": "none",
            "expected_level": competency_defs.get(lo, {}).get("expected_level", "Deepen"),
            "contributing_worksheets": [],
            "evidence_items": 0,
            "direct_evidence_count": 0,
            "supporting_evidence_count": 0,
            "mean_confidence": None,
            "_confidences": [],
            "_worksheets": set(),
        }
        for lo in all_los
    }

    worksheets_scored: list[str] = []
    item_records: list[dict[str, Any]] = []
    baseline_records: list[dict[str, Any]] = []

    for ws in list_worksheets(student_id):
        scoring = artifact_payload(load_artifact(student_id, ws, "scoring"))
        evidence = artifact_payload(load_artifact(student_id, ws, "evidence"))
        if not scoring and not evidence:
            continue
        if scoring:
            worksheets_scored.append(ws)

        review_items = set(
            build_summary_from_scoring(scoring, worksheet=ws).get("review_items") or []
        ) if scoring else set()

        for rec in (evidence or {}).get("items", []):
            item_id = rec.get("item", "")
            on_review = item_id in review_items
            priors = fw_index.get((ws, item_id), [])

            for comp in rec.get("competencies") or rec.get("learning_objects") or []:
                lo = comp.get("lo") or comp.get("LO")
                if not lo or lo not in per_lo:
                    continue
                strength = comp.get("strength") or comp.get("evidence_strength", "none")
                present = comp.get("evidence_present", strength != "none")
                et = comp.get("evidence_type", "direct")
                prior = _find_comp_prior(priors, lo)
                counts_peak = competency_counts_toward_portfolio_peak({
                    **prior,
                    "evidence_type": et,
                })

                record = {
                    "worksheet": ws,
                    "item": item_id,
                    "lo": lo,
                    "strength": strength,
                    "evidence_type": et,
                    "evidence_present": present,
                    "review": on_review,
                    "confidence": comp.get("confidence"),
                    "counts_toward_peak": counts_peak,
                }
                item_records.append(record)

                if not present or strength == "none":
                    continue

                if not counts_peak:
                    baseline_records.append(record)
                    continue

                bucket = per_lo[lo]
                bucket["evidence_items"] += 1
                bucket["_worksheets"].add(ws)
                if et == "supporting":
                    bucket["supporting_evidence_count"] += 1
                else:
                    bucket["direct_evidence_count"] += 1
                if comp.get("confidence") is not None:
                    bucket["_confidences"].append(float(comp["confidence"]))

    for lo, bucket in per_lo.items():
        strengths = [
            r["strength"] for r in item_records
            if r["lo"] == lo and r["evidence_present"] and r["strength"] != "none"
            and r["counts_toward_peak"]
        ]
        bucket["peak_strength"] = _peak_strength(strengths)
        bucket["contributing_worksheets"] = sorted(bucket["_worksheets"])
        if bucket["_confidences"]:
            bucket["mean_confidence"] = round(
                sum(bucket["_confidences"]) / len(bucket["_confidences"]), 3,
            )
        bucket.pop("_confidences", None)
        bucket.pop("_worksheets", None)

    return per_lo, sorted(worksheets_scored), item_records, baseline_records


def _lo_meets_threshold(
    learning_objects: dict[str, Any],
    lo: str,
    min_strength: str,
) -> bool:
    peak = learning_objects.get(lo, {}).get("peak_strength", "none")
    return STRENGTH_RANK.get(peak, 0) >= STRENGTH_RANK.get(min_strength, 0)


def _level_status(
    learning_objects: dict[str, Any],
    los: tuple[str, ...],
    min_strength: str,
    optional: frozenset[str] | None = None,
) -> str:
    optional = optional or frozenset()
    required = [lo for lo in los if lo not in optional]

    if not all(_lo_meets_threshold(learning_objects, lo, min_strength) for lo in required):
        return "insufficient"

    optional_present = [lo for lo in los if lo in optional]
    if optional_present:
        any_optional = any(
            _lo_meets_threshold(learning_objects, lo, "weak") for lo in optional_present
        )
        if all(_lo_meets_threshold(learning_objects, lo, min_strength) for lo in required):
            return "met" if any_optional or not optional_present else "partial"

    return "met"


def propose_ai_cft_level(learning_objects: dict[str, Any]) -> dict[str, Any]:
    """Rule-based Aspect 3 level proposal from aggregated LO evidence."""
    acquire_status = _level_status(learning_objects, ACQUIRE_LOS, "moderate", OPTIONAL_ACQUIRE)
    deepen_status = _level_status(learning_objects, DEEPEN_LOS, "moderate", OPTIONAL_DEEPEN)
    create_status = _level_status(learning_objects, CREATE_LOS, "weak")

    lo_line = lambda los: ", ".join(
        f"{lo}={learning_objects.get(lo, {}).get('peak_strength', 'none')}" for lo in los
    )

    if create_status == "met" and deepen_status == "met":
        aspect_level = "Create"
        rationale = (
            f"Create indicator LO3.3.1 shows evidence (peak={learning_objects.get('LO3.3.1', {}).get('peak_strength')}). "
            f"Deepen LOs: {lo_line(DEEPEN_LOS)}. Acquire LOs: {lo_line(ACQUIRE_LOS)}."
        )
    elif deepen_status in ("met", "partial"):
        aspect_level = "Deepen"
        rationale = (
            f"Deepen application LOs reach moderate-or-strong peaks across multiple worksheets "
            f"({lo_line(DEEPEN_LOS)}). "
            f"Acquire foundations: {lo_line(ACQUIRE_LOS)}. "
        )
        if create_status != "met":
            rationale += "Create-level LO3.3.1 not yet demonstrated."
    elif acquire_status == "met":
        aspect_level = "Acquire"
        rationale = (
            f"Foundational Acquire LOs show consistent evidence ({lo_line(ACQUIRE_LOS)}). "
            f"Deepen LOs remain limited ({lo_line(DEEPEN_LOS)})."
        )
    else:
        aspect_level = "Acquire"
        rationale = (
            f"Emerging evidence only. Acquire: {lo_line(ACQUIRE_LOS)}; "
            f"Deepen: {lo_line(DEEPEN_LOS)}. Review data gaps before levelling."
        )

    return {
        "Aspect3": aspect_level,
        "rationale": rationale.strip(),
        "confidence": "provisional",
        "is_final": False,
        "decision_owner": "researcher",
        "decision_note": (
            "Level aggregates multi-worksheet competency evidence; not assigned from any single worksheet. "
            "Baseline (prior_belief) and diagnostic (reflective) items are excluded from peak aggregation. "
            "Researcher makes final holistic judgement after reviewing flagged items."
        ),
        "level_diagnostics": {
            "Acquire": acquire_status,
            "Deepen": deepen_status,
            "Create": create_status,
        },
    }


def detect_data_gaps(
    student_id: str,
    item_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Surface review-flagged and missing-evidence items by worksheet."""
    gaps_by_ws: dict[str, dict[str, Any]] = defaultdict(lambda: {
        "items": [],
        "reasons": [],
    })

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

        responses = extraction.get("responses") or {}
        if extraction.get("gate_1_extraction"):
            responses = extraction["gate_1_extraction"].get("items", responses)
        for item_id, text in responses.items():
            if str(text).strip() in {"(bos)", "(missing)", "(not_extracted)", "(okunamiyor)", ""}:
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


def _baseline_summary(baseline_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Compact list of baseline/diagnostic evidence for researcher context."""
    out: list[dict[str, Any]] = []
    for rec in baseline_records:
        out.append({
            "worksheet": rec["worksheet"],
            "item": rec["item"],
            "lo": rec["lo"],
            "strength": rec["strength"],
            "evidence_type": rec["evidence_type"],
        })
    return out


def build_portfolio(student_id: str) -> dict[str, Any]:
    """Assemble portfolio.json from modular worksheet artifacts."""
    framework = load_framework()
    fw_index = framework_item_index(framework)
    learning_objects, worksheets_scored, item_records, baseline_records = (
        _collect_worksheet_evidence(student_id, fw_index)
    )

    proposal = propose_ai_cft_level(learning_objects)
    data_gaps = detect_data_gaps(student_id, item_records)

    return {
        "framework": framework["framework"],
        "aspect": framework["aspect"],
        "methodology": {
            "aggregation_note": (
                "LO peak_strength uses portfolio_weight=full items only; "
                "prior_belief and diagnostic reflective items are listed in baseline_evidence."
            ),
        },
        "worksheets_scored": worksheets_scored,
        "learning_objects": learning_objects,
        "competency_level_summary": proposal.pop("level_diagnostics"),
        "baseline_evidence": _baseline_summary(baseline_records),
        "ai_cft_proposal": proposal,
        "data_gaps": data_gaps,
        "evidence_item_count": len(item_records),
    }


def build_and_save_portfolio(student_id: str) -> dict[str, Any]:
    portfolio = build_portfolio(student_id)
    save_portfolio(student_id, portfolio)
    return portfolio
