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
    from pipeline_schema import competency_strength_ceiling, item_competencies, load_mapping, load_rubric

    rubric = load_rubric("WS10")
    mapping = load_mapping("WS10")
    items_out = []
    total = 0.0

    for item_id in rubric["items"]:
        cfg = rubric["items"][item_id]
        max_score = float(cfg.get("max_score", 1))
        ans = responses.get(item_id, "")
        score = 0.0
        check = cfg.get("check")
        expected = cfg.get("answer")
        tol = float(cfg.get("tolerance", 0))

        try:
            val = float(str(ans).split("|")[0])
            if check == "numeric" and expected is not None:
                score = max_score if abs(val - float(expected)) <= tol else 0.0
            elif check == "numeric_optimal" and expected is not None:
                score = max_score if val == float(expected) else 0.0
            elif check == "row_consistency":
                score = max_score if "|" in str(ans) else 0.0
        except (ValueError, TypeError):
            score = 0.0

        total += score
        lo_entries = []
        for comp_prior in item_competencies(mapping, item_id):
            ceiling = competency_strength_ceiling(comp_prior)
            strength = ceiling if score >= max_score else ("weak" if score > 0 else "none")
            if strength == "strong" and ceiling == "moderate":
                strength = "moderate"
            lo_entries.append({
                "lo": comp_prior["lo"],
                "strength": strength if score > 0 else "none",
                "evidence_type": comp_prior.get("evidence_type", "direct"),
                "rationale": comp_prior.get("rationale", ""),
                "confidence": 1.0 if check in {"numeric", "numeric_optimal"} else 0.85,
                "evidence_present": score > 0,
            })

        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": 1.0 if check in {"numeric", "numeric_optimal"} else 0.85,
            "review": False,
            "competencies": lo_entries,
        })

    return {
        "blocked": False,
        "items": items_out,
        "total_score": total,
        "max_score": 8.0,
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
