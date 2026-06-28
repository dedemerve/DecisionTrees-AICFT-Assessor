#!/usr/bin/env python3
"""
pipeline_integration.py — Wire Phase 1 layout + Phase 2 HTR into student bundle.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from layout_isolator import LayoutIsolator
from pipeline_schema import LAYOUT_ROIS_DIR, REPO_ROOT, layout_manifest_path
from student_bundle import get_section, load_bundle, save_bundle, set_section
from ws10_table_extractor import (
    Ws10ExtractionResult,
    build_validation_ws10,
    extract_ws10_from_layout,
)

ANSWER_KEY_WS6 = REPO_ROOT / "answer_key_worksheets" / "Worksheet 6.pdf"


def attach_layout_manifest(student_id: str, worksheet: str) -> dict[str, Any] | None:
    manifest_path = layout_manifest_path(student_id, worksheet)
    if not manifest_path.exists():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def run_layout_phase(student_id: str) -> dict[str, str]:
    """Phase 1: produce layout_rois manifests."""
    results = LayoutIsolator().process_student_bundle(student_id)
    return {ws: r.status for ws, r in results.items()}


def extract_ws6_from_answer_key_pdf(
    student_id: str,
    *,
    pdf_path: Path | None = None,
) -> dict[str, Any]:
    """Render Worksheet 6.pdf and run WS6 tree canvas layout."""
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
    """Deterministic WS10 scoring from rubric answers (all items max 1)."""
    from pipeline_schema import load_mapping, load_rubric

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
        for lo in mapping["items"].get(item_id, []):
            strength = "strong" if score >= max_score else ("weak" if score > 0 else "none")
            if strength == "strong" and lo.get("weight", "moderate") == "moderate":
                strength = "moderate"
            lo_entries.append({
                "LO": lo["LO"],
                "evidence_present": score > 0,
                "evidence_strength": strength if score > 0 else "none",
            })

        items_out.append({
            "item": item_id,
            "score": score,
            "confidence": 1.0 if check in {"numeric", "numeric_optimal"} else 0.85,
            "review": False,
            "learning_outcomes": lo_entries,
        })

    return {
        "schema_version": "1.0",
        "worksheet": "WS10",
        "student_id": student_id,
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
    if "gate_1_extraction" in ext:
        g1 = ext["gate_1_extraction"]
        g1["items"] = extraction.responses
        g1["numeric_table"] = extraction.numeric_table
        g1["htr"] = extraction.to_dict()
        if layout_manifest:
            g1["layout_roi"] = layout_manifest
        return ext

    ext.update({
        "schema_version": "1.0",
        "worksheet": "WS10",
        "responses": extraction.responses,
        "numeric_table": extraction.numeric_table,
        "htr_status": extraction.status,
    })
    if layout_manifest:
        ext["layout_roi"] = layout_manifest
    return ext


def integrate_ws10_htr(student_id: str) -> dict[str, Any]:
    """Phase 2: HTR table → update student bundle WS10 sections."""
    extraction = extract_ws10_from_layout(student_id)
    bundle = load_bundle(student_id)
    layout_manifest = attach_layout_manifest(student_id, "WS10")

    ext = get_section(bundle, "WS10", "extraction") or {
        "schema_version": "1.0",
        "worksheet": "WS10",
        "student_id": student_id,
    }
    set_section(bundle, "WS10", "extraction", _patch_ws10_extraction(ext, extraction, layout_manifest))
    validation = build_validation_ws10(extraction)
    set_section(bundle, "WS10", "validation", validation)

    scoring = score_ws10_deterministic(extraction.responses, student_id)
    set_section(bundle, "WS10", "scoring", scoring)
    set_section(bundle, "WS10", "summary", {
        "schema_version": "1.0",
        "worksheet": "WS10",
        "student_id": student_id,
        "total_score": scoring["total_score"],
        "max_score": scoring["max_score"],
        "learning_outcomes": {"LO3.2.1": "strong" if scoring["total_score"] >= 7 else "moderate"},
        "blocked": False,
    })
    save_bundle(bundle)

    return {
        "worksheet": "WS10",
        "htr_status": extraction.status,
        "blocked": validation["blocked"],
        "responses": extraction.responses,
    }


def integrate_student(student_id: str, *, ws6_pdf: bool = True) -> dict[str, Any]:
    """Run layout + HTR integration for one student."""
    report: dict[str, Any] = {"student_id": student_id, "layout": {}, "htr": {}, "ws6": {}}
    report["layout"] = run_layout_phase(student_id)
    report["htr"]["WS10"] = integrate_ws10_htr(student_id)

    if ws6_pdf and ANSWER_KEY_WS6.exists():
        report["ws6"] = extract_ws6_from_answer_key_pdf(student_id)

    bundle = load_bundle(student_id)
    ws5_manifest = attach_layout_manifest(student_id, "WS5")
    if ws5_manifest:
        ext = get_section(bundle, "WS5", "extraction")
        if ext and "gate_1_extraction" in ext:
            ext["gate_1_extraction"]["layout_roi"] = ws5_manifest
            set_section(bundle, "WS5", "extraction", ext)
            save_bundle(bundle)

    return report
