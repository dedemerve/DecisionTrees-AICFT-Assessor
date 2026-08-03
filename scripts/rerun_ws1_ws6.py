#!/usr/bin/env python3
"""
Re-run OCR extraction for WS1 and WS6 only.

Safely updates ONLY students/<id>/WS1/ and students/<id>/WS6/ extraction files.
Does NOT touch WS10 or any other worksheet.

Usage:
    python scripts/rerun_ws1_ws6.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

import anthropic
from ocr_pipeline import (
    process_pdf,
    is_answered,
    validate_ocr_output,
)
from pipeline_schema import (
    WORKSHEET_ITEM_IDS,
    WORKSHEET_PDF_SOURCE,
)
from student_bundle import save_artifact, STUDENTS_DIR

WS6_VISION_ENABLED = True

TARGETS = {
    "WS1": "24 Mart 2026 Çalışma Kâğıdı 1.pdf",
    "WS6": "31 Mart 2026 Çalışma Kâğıdı 6.pdf",
}


def _ws6_gate1_status(tree: dict) -> str:
    """Derive gate_1 status from WS6 tree_structure completeness."""
    d0 = tree.get("depth_0", {})
    if not d0.get("parsed_feature"):
        return "fail"
    d1 = tree.get("depth_1", {})
    if not d1.get("left_child") and not d1.get("right_child"):
        return "partial"
    return "pass"


def build_extraction_record(
    student_name: str,
    ws_label: str,
    raw_source: dict,
    client: anthropic.Anthropic,
    ocr_model: str = "claude-sonnet-5",
) -> dict:
    """Build an extraction record for one worksheet from the raw Claude output."""
    item_ids = WORKSHEET_ITEM_IDS.get(ws_label, [])
    pdf = WORKSHEET_PDF_SOURCE.get(ws_label, "")
    extracted_at = datetime.now(timezone.utc).isoformat()

    # WS6 uses tree_structure, not flat WS6_B* items.
    # PROMPT_WS6 embeds the tree under raw["extraction"]["tree_structure"].
    if ws_label == "WS6":
        tree_structure = raw_source.get("extraction", {}).get("tree_structure", {})
        g1_status = _ws6_gate1_status(tree_structure)
        tree_present = bool(tree_structure.get("depth_0"))
        completion_rate = 1.0 if tree_present else 0.0
        record: dict = {
            "student_name": student_name,
            "worksheet": ws_label,
            "pdf_source": pdf,
            "gate_1_extraction": {
                "status": g1_status,
                "extracted_at": extracted_at,
                "ocr_model": ocr_model,
                "items": {iid: "(not_extracted)" for iid in item_ids},
                "tree_structure": tree_structure,
                "raw_ocr": {
                    k: v for k, v in raw_source.items()
                    if k not in ("student_name", "page_notes", "ws_snapshot")
                },
            },
            "gate_2_validation": {
                "status": "pass" if tree_present else "fail",
                "item_coverage": {
                    "answered": 0,
                    "total": len(item_ids),
                    "blank_or_illegible": 0,
                    "missing": len(item_ids),
                    "completion_rate": 0.0,
                    "note": "WS6 scored from tree_structure, not flat items",
                },
                "warnings": [],
                "student_snapshot": {
                    "completion_rate": completion_rate,
                    "engagement_level": "high" if tree_present else "low",
                    "llm_observations": raw_source.get("ws_snapshot", ""),
                    "page_quality_notes": raw_source.get("page_notes", ""),
                },
            },
            "gate_3_scoring": {"status": "pending", "scored_at": None, "scoring_model": None, "items": {}},
            "gate_4_aicft": {"status": "pending", "level": None, "evidence": None},
        }
        return record

    # All other worksheets: flat item extraction.
    items = {}
    for iid in item_ids:
        val = raw_source.get(iid)
        if val is None:
            items[iid] = "(not_extracted)"
        else:
            items[iid] = str(val).strip() or "(bos)"

    answered = sum(1 for v in items.values() if is_answered(v))
    blank_or_illegible = sum(1 for v in items.values() if v in {"(bos)", "(okunamiyor)"})
    missing = sum(1 for v in items.values() if v in {"(missing)", "(not_extracted)"})
    total = len(item_ids)
    completion_rate = round(answered / total, 3) if total else 0.0

    if missing == total:
        g1_status = "fail"
    elif missing > 0 or blank_or_illegible > answered:
        g1_status = "partial"
    else:
        g1_status = "pass"

    g2_status = "fail" if completion_rate < 0.3 else ("partial" if completion_rate < 0.7 else "pass")

    ocr_warnings = validate_ocr_output({
        "student_name": student_name,
        "responses": items,
    })

    raw_ocr_clean = {
        k: v for k, v in raw_source.items()
        if k not in ("student_name", "page_notes", "ws_snapshot")
    }

    return {
        "student_name": student_name,
        "worksheet": ws_label,
        "pdf_source": pdf,
        "gate_1_extraction": {
            "status": g1_status,
            "extracted_at": extracted_at,
            "ocr_model": ocr_model,
            "items": items,
            "raw_ocr": raw_ocr_clean,
        },
        "gate_2_validation": {
            "status": g2_status,
            "item_coverage": {
                "answered": answered,
                "total": total,
                "blank_or_illegible": blank_or_illegible,
                "missing": missing,
                "completion_rate": completion_rate,
            },
            "warnings": ocr_warnings,
            "student_snapshot": {
                "completion_rate": completion_rate,
                "engagement_level": (
                    "high" if completion_rate >= 0.7
                    else "medium" if completion_rate >= 0.4
                    else "low"
                ),
                "llm_observations": raw_source.get("ws_snapshot", ""),
                "page_quality_notes": raw_source.get("page_notes", ""),
            },
        },
        "gate_3_scoring": {"status": "pending", "scored_at": None, "scoring_model": None, "items": {}},
        "gate_4_aicft": {"status": "pending", "level": None, "evidence": None},
    }


def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    totals = {"processed": 0, "items_scored": 0, "failures": 0}

    for ws_label, pdf_name in TARGETS.items():
        print(f"\n{'='*60}")
        print(f"Processing {ws_label} from: {pdf_name}")
        print("="*60)

        raw_by_student = process_pdf(client, pdf_name, resume=True)

        if not raw_by_student:
            print(f"  WARNING: No students found in {pdf_name}")
            continue

        for student_name, raw_source in sorted(raw_by_student.items()):
            if "_error" in raw_source:
                print(f"  FAIL {student_name}: {raw_source['_error']}")
                totals["failures"] += 1
                continue

            record = build_extraction_record(
                student_name, ws_label, raw_source, client
            )
            save_artifact(student_name, ws_label, "extraction", record)

            g1 = record["gate_1_extraction"]["status"]
            if ws_label == "WS6":
                ts = record["gate_1_extraction"].get("tree_structure", {})
                d0_feat = ts.get("depth_0", {}).get("parsed_feature", "—")
                print(f"  OK  {student_name:<14} WS6  tree_structure root={d0_feat}  gate1={g1}")
            else:
                answered = record["gate_2_validation"]["item_coverage"]["answered"]
                total = record["gate_2_validation"]["item_coverage"]["total"]
                print(f"  OK  {student_name:<14} {ws_label}  {answered}/{total} answered  gate1={g1}")
            totals["processed"] += 1
            totals["items_scored"] += answered

    print(f"\n{'='*60}")
    print(f"Re-extraction complete.")
    print(f"  Students processed : {totals['processed']}")
    print(f"  Items with answers : {totals['items_scored']}")
    print(f"  Failures           : {totals['failures']}")


if __name__ == "__main__":
    main()
