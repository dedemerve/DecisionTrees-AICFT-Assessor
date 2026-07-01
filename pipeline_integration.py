#!/usr/bin/env python3
"""
pipeline_integration.py — Wire Phase 1 layout + Phase 2 HTR into per-worksheet artifacts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from layout_isolator import LayoutIsolator
from pipeline_schema import LAYOUT_ROIS_DIR, REPO_ROOT, layout_manifest_path
from student_bundle import (
    artifact_payload,
    load_artifact,
    save_artifact,
    save_scoring_bundle,
)
from worksheet_validation import ws10_extraction_quality
from ws10_table_extractor import (
    Ws10ExtractionResult,
    extract_ws10_from_layout,
)

ANSWER_KEY_WS6 = REPO_ROOT / "answer_key_worksheets" / "Worksheet 6.pdf"


def attach_layout_manifest(student_id: str, worksheet: str) -> dict[str, Any] | None:
    manifest_path = layout_manifest_path(student_id, worksheet)
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def run_layout_phase(student_id: str) -> dict[str, str]:
    results = LayoutIsolator().process_student_bundle(student_id)
    return {ws: r.status for ws, r in results.items()}


def extract_ws6_from_answer_key_pdf(
    student_id: str,
    *,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    pdf_path = pdf_path or ANSWER_KEY_WS6
    if not pdf_path.exists():
        return {"status": "error", "message": f"PDF not found: {pdf_path}"}

    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        return {"status": "error", "message": f"pdf2image required: {exc}"}

    images = convert_from_path(str(pdf_path), dpi=200, first_page=1, last_page=1)
    if not images:
        return {"status": "error", "message": "PDF produced no pages."}

    out_dir = LAYOUT_ROIS_DIR / student_id / "_ws6_source"
    out_dir.mkdir(parents=True, exist_ok=True)
    page_path = out_dir / "worksheet6_page1.jpg"
    images[0].save(str(page_path), format="JPEG", quality=92)

    result = LayoutIsolator().extract_ws6_tree_canvas(page_path, student_id)
    result.save()
    return {
        "status": result.status,
        "message": result.message,
        "manifest": str(layout_manifest_path(student_id, "WS6")),
        "source_image": str(page_path.relative_to(REPO_ROOT)),
    }


def score_ws10_deterministic(responses: dict[str, str], student_id: str) -> dict[str, Any]:
    from pipeline_schema import load_rubric, scoring_item_ids
    from rubric_deterministic import score_from_credit
    from ws10_validation import validate_ws10_extraction

    rubric = load_rubric("WS10")
    validation = validate_ws10_extraction(responses)
    checks = validation["deterministic_checks"]
    items_out = []
    total = 0.0
    max_total = 0.0

    for item_id in scoring_item_ids("WS10"):
        cfg = rubric["items"][item_id]
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        check = checks.get(item_id) or {}
        score = score_from_credit(check, max_score)
        total += score
        review = bool(check.get("review")) or check.get("credit") == "not_attempted"
        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": 1.0 if score >= max_score else (0.35 if review else 0.85),
            "review": review,
        })

    return {
        "blocked": False,
        "items": items_out,
        "total_score": total,
        "max_score": max_total,
    }


def score_ws5_deterministic(
    responses: dict[str, str],
    student_id: str,
    *,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score WS5 grid rows and B25 (minimum misclassification) from validation checks."""
    from pipeline_schema import load_rubric, scoring_item_ids
    from rubric_deterministic import score_b25_minimum_errors, score_from_credit, score_row_consistency

    rubric = load_rubric("WS5")
    checks = (validation or {}).get("deterministic_checks") or {}
    items_out: list[dict[str, Any]] = []
    total = 0.0
    max_total = 0.0

    for item_id in scoring_item_ids("WS5"):
        cfg = rubric["items"][item_id]
        check_type = cfg.get("check")
        if check_type not in {"row_consistency", "b25_minimum_errors"}:
            continue
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score

        if check_type == "row_consistency":
            det = score_row_consistency(item_id, responses, rubric)
            score = float(det["score"])
            review = det["credit"] == "partial" or (
                det["credit"] == "zero" and det.get("reason") not in {"blank_row", None}
            )
            check = checks.get(item_id) or {}
            if check and score <= 0 and check.get("credit") in {"full", "partial"}:
                score = score_from_credit(check, max_score)
        else:
            det = score_b25_minimum_errors(responses, rubric, row_checks=checks)
            score = float(det["score"])
            review = bool(det.get("review"))
            check = checks.get("WS5_B25") or det

        if check_type == "b25_minimum_errors" and check and score <= 0:
            score = score_from_credit(check, max_score)
            review = bool(check.get("review"))

        total += score
        if review and check_type == "b25_minimum_errors":
            confidence = 0.65
        else:
            confidence = 1.0 if score >= max_score else 0.85
        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": confidence,
            "review": review,
        })

    return {
        "blocked": False,
        "items": items_out,
        "total_score": total,
        "max_score": max_total,
    }


def score_ws6_deterministic(
    responses: dict[str, str],
    student_id: str,
    *,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score all WS6 rubric items from food-card tree validation."""
    from pipeline_schema import load_rubric, scoring_item_ids
    from rubric_deterministic import score_from_credit, score_ws6_item

    rubric = load_rubric("WS6")
    checks = (validation or {}).get("deterministic_checks") or {}
    items_out: list[dict[str, Any]] = []
    total = 0.0
    max_total = 0.0

    for item_id in scoring_item_ids("WS6"):
        cfg = rubric["items"][item_id]
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score

        det = score_ws6_item(item_id, responses, rubric, checks=checks)
        score = float(det["score"])
        review = bool(det.get("review")) or (
            det["credit"] == "partial" and item_id.endswith("threshold")
        )

        check = checks.get(item_id) or {}
        if check and score <= 0 and check.get("credit") in {"full", "partial"}:
            score = score_from_credit(check, max_score)

        total += score
        confidence = 1.0 if score >= max_score and not review else (0.85 if score > 0 else 0.85)
        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": confidence,
            "review": review,
        })

    return {
        "blocked": False,
        "items": items_out,
        "total_score": total,
        "max_score": max_total,
    }


def score_ws7_deterministic(
    responses: dict[str, str],
    student_id: str,
    *,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score WS7 Part 1 path letters + Part 2 WS6-consistent rules."""
    from pipeline_schema import load_rubric, scoring_item_ids
    from rubric_deterministic import score_from_credit, score_ws7_item
    from student_bundle import load_extraction_responses

    rubric = load_rubric("WS7")
    checks = (validation or {}).get("deterministic_checks") or {}
    ws6_responses = load_extraction_responses(student_id, "WS6")
    items_out: list[dict[str, Any]] = []
    total = 0.0
    max_total = 0.0

    for item_id in scoring_item_ids("WS7"):
        cfg = rubric["items"][item_id]
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score

        det = score_ws7_item(
            item_id, responses, rubric, checks=checks, ws6_responses=ws6_responses,
        )
        score = float(det["score"])
        review = bool(det.get("review")) or det.get("credit") == "partial"

        check = checks.get(item_id) or {}
        if check and score <= 0 and check.get("credit") in {"full", "partial"}:
            score = score_from_credit(check, max_score)

        total += score
        if det.get("credit") == "not_attempted" and item_id.startswith("WS7_P1"):
            confidence = 0.35
            review = True
        elif score >= max_score and not review:
            confidence = 1.0
        else:
            confidence = 0.85 if score > 0 else 0.85

        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": confidence,
            "review": review,
        })

    blocked = bool((validation or {}).get("blocked"))
    return {
        "blocked": blocked,
        "blocked_reason": (validation or {}).get("blocked_reason"),
        "items": items_out,
        "total_score": total,
        "max_score": max_total,
    }


def score_ws11_deterministic(
    responses: dict[str, str],
    student_id: str,
    *,
    interpretive_items: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Score WS11 cognitive items: Q10–Q12 deterministically; B8a–B9 from interpretive_items if given."""
    from pipeline_schema import load_rubric, scoring_item_ids
    from rubric_deterministic import score_from_credit
    from ws11_validation import validate_ws11_deterministic

    rubric = load_rubric("WS11")
    validation = validate_ws11_deterministic(responses, rubric)
    checks = validation["deterministic_checks"]
    items_out: list[dict[str, Any]] = []
    total = 0.0
    max_total = 0.0
    interpretive_items = interpretive_items or {}

    for item_id in scoring_item_ids("WS11"):
        cfg = rubric["items"].get(item_id)
        if cfg is None:
            # pipeline_schema.ITEM_IDS_WS11_COGNITIVE (per-subitem ids like "WS11_Q10_3") has
            # drifted from the current worksheets/WS11/rubric.json bundle (grouped ids like
            # "WS11_Q10"). Surface this loudly instead of crashing the whole worksheet — a
            # rubric/schema owner needs to reconcile the id scheme, guessing here would risk
            # silently wrong scores.
            items_out.append({
                "item": item_id,
                "score": 0.0,
                "confidence": 0.0,
                "review": True,
                "reason": "rubric_item_missing",
            })
            continue
        max_score = float(cfg.get("max_score", 1))
        max_total += max_score
        ev = cfg.get("evaluation")

        if ev in {"true_false", "ordering_step", "multiselect_subitem"}:
            check = checks.get(item_id) or {}
            score = score_from_credit(check, max_score)
            review = check.get("credit") == "not_attempted"
            confidence = 1.0 if score >= max_score else (0.0 if review else 0.85)
        elif item_id in interpretive_items:
            rec = interpretive_items[item_id]
            score = float(rec.get("score") or 0)
            review = bool(rec.get("review"))
            confidence = float(rec.get("confidence") or 0.8)
        else:
            text = (responses.get(item_id) or "").strip()
            score = max_score if text else 0.0
            review = not text
            confidence = 0.8 if text else 0.0

        total += score
        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": confidence,
            "review": review,
        })

    return {
        "blocked": False,
        "items": items_out,
        "total_score": round(total, 2),
        "max_score": round(max_total, 2),
    }


def _patch_ws10_extraction(
    ext: dict[str, Any],
    extraction: Ws10ExtractionResult,
    layout_manifest: dict[str, Any] | None,
) -> dict[str, Any]:
    if not ext:
        ext = {"worksheet": "WS10", "student_id": extraction.student_id}

    ext.update({
        "worksheet": "WS10",
        "responses": extraction.responses,
        "numeric_table": extraction.numeric_table,
        "htr_status": extraction.status,
    })
    if layout_manifest:
        ext["layout_roi"] = layout_manifest
    return ext


def integrate_ws10_htr(student_id: str) -> dict[str, Any]:
    extraction = extract_ws10_from_layout(student_id)
    layout_manifest = attach_layout_manifest(student_id, "WS10")

    ext = artifact_payload(load_artifact(student_id, "WS10", "extraction"))
    patched = _patch_ws10_extraction(ext, extraction, layout_manifest)
    row_count = len(extraction.rows) or len(extraction.responses)
    quality = ws10_extraction_quality(extraction.status, row_count)
    patched.update(quality)
    save_artifact(student_id, "WS10", "extraction", patched)

    scoring = score_ws10_deterministic(extraction.responses, student_id)
    if quality["blocked"]:
        scoring["blocked"] = True
        scoring["blocked_reason"] = quality.get("blocked_reason")
    save_scoring_bundle(student_id, "WS10", scoring)

    return {
        "worksheet": "WS10",
        "htr_status": extraction.status,
        "blocked": quality["blocked"],
        "responses": extraction.responses,
    }


def integrate_student(student_id: str, *, ws6_pdf: bool = True) -> dict[str, Any]:
    report: dict[str, Any] = {"student_id": student_id, "layout": {}, "htr": {}, "ws6": {}}
    report["layout"] = run_layout_phase(student_id)
    report["htr"]["WS10"] = integrate_ws10_htr(student_id)

    if ws6_pdf and ANSWER_KEY_WS6.exists():
        report["ws6"] = extract_ws6_from_answer_key_pdf(student_id)

    ws5_manifest = attach_layout_manifest(student_id, "WS5")
    if ws5_manifest:
        ext = artifact_payload(load_artifact(student_id, "WS5", "extraction"))
        if ext and "gate_1_extraction" in ext:
            ext["gate_1_extraction"]["layout_roi"] = ws5_manifest
            save_artifact(student_id, "WS5", "extraction", ext)

    return report
