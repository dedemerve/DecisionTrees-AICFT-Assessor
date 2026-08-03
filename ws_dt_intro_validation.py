"""Backward-compatible combined validation for legacy WS_DT_INTRO exports."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from pipeline_schema import ITEM_IDS_DT_XENO, OCR_OUTPUT_DIR
from student_bundle import STUDENTS_DIR
from ws_dt_titanic_validation import (
    TITANIC_ITEM_IDS,
    apply_operator_corrections as titanic_apply_corrections,
    build_ocr_output_document as build_titanic_ocr_document,
    build_validation as build_titanic_validation,
    export_ocr_output as export_titanic_ocr_output,
    sectioned_extraction as titanic_sectioned,
)
from ws_dt_xeno_validation import (
    XENO_ITEM_IDS,
    build_ocr_output_document as build_xeno_ocr_document,
    build_validation as build_xeno_validation,
    export_ocr_output as export_xeno_ocr_output,
    xeno_consistency_checks,
)

INTRO_ITEM_IDS = XENO_ITEM_IDS + [f"DTI_{i:02d}" for i in range(34, 81)]
LEGACY_TITANIC_OFFSET = 33


def flatten_combined_extraction(extraction: dict[str, Any]) -> dict[str, str]:
    """Flatten sectioned WS_DT_INTRO extraction to legacy flat DTI_01-80."""
    flat: dict[str, str] = {}
    for section, items in extraction.items():
        if not isinstance(items, dict):
            continue
        for key, value in items.items():
            if re.fullmatch(r"DTI_\d+", key):
                flat[key] = value
    return flat


def titanic_split_to_legacy_intro(items: dict[str, str]) -> dict[str, str]:
    """Map WS_DT_TITANIC DTI_01-47 → legacy combined DTI_34-80."""
    return {
        f"DTI_{i + LEGACY_TITANIC_OFFSET:02d}": items[f"DTI_{i:02d}"]
        for i in range(1, 48)
        if f"DTI_{i:02d}" in items
    }


def split_intro_flat_items(flat: dict[str, str]) -> tuple[dict[str, str], dict[str, str]]:
    """Split legacy flat DTI_01-80 into Xeno (01-33) and Titanic (01-47) worksheets."""
    xeno = {iid: flat.get(iid, "(not_extracted)") for iid in XENO_ITEM_IDS}
    titanic = {
        f"DTI_{i:02d}": flat.get(f"DTI_{i + LEGACY_TITANIC_OFFSET:02d}", "(not_extracted)")
        for i in range(1, 48)
    }
    return xeno, titanic


def _student_record_items(student_id: str, worksheet: str) -> dict[str, str] | None:
    path = STUDENTS_DIR / student_id / worksheet / "extraction.json"
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    g1 = record.get("gate_1_extraction") or {}
    items = g1.get("items")
    return dict(items) if items else None


def _student_record_meta(student_id: str, worksheet: str) -> tuple[str, str]:
    path = STUDENTS_DIR / student_id / worksheet / "extraction.json"
    if not path.is_file():
        return "", "(bos)"
    record = json.loads(path.read_text(encoding="utf-8"))
    snap = record.get("gate_2_validation", {}).get("student_snapshot") or {}
    ws_snapshot = str(snap.get("llm_observations") or "").strip()
    page_notes = str(snap.get("page_notes") or "(bos)").strip() or "(bos)"
    return ws_snapshot, page_notes


def _intro_record_items(student_id: str) -> dict[str, str] | None:
    path = STUDENTS_DIR / student_id / "WS_DT_INTRO" / "extraction.json"
    if not path.is_file():
        return None
    record = json.loads(path.read_text(encoding="utf-8"))
    items = flat_items_from_extraction_record(record)
    return items if items else None


def _intro_record_meta(student_id: str) -> tuple[str, str]:
    path = STUDENTS_DIR / student_id / "WS_DT_INTRO" / "extraction.json"
    if not path.is_file():
        return "", "(bos)"
    record = json.loads(path.read_text(encoding="utf-8"))
    snap = record.get("gate_2_validation", {}).get("student_snapshot") or {}
    ws_snapshot = str(snap.get("llm_observations") or "").strip()
    page_notes = str(snap.get("page_notes") or "(bos)").strip() or "(bos)"
    return ws_snapshot, page_notes


def load_split_items(
    student_id: str,
    *,
    combined_doc: dict[str, Any] | None = None,
) -> tuple[dict[str, str], dict[str, str], str, str, str, str]:
    """Resolve Xeno/Titanic item dicts and metadata for split ocr_output export."""
    xeno_items = _student_record_items(student_id, "WS_DT_XENO")
    titanic_items = _student_record_items(student_id, "WS_DT_TITANIC")

    xeno_snapshot, xeno_notes = _student_record_meta(student_id, "WS_DT_XENO")
    titanic_snapshot, titanic_notes = _student_record_meta(student_id, "WS_DT_TITANIC")

    if xeno_items is None or titanic_items is None:
        intro_items = _intro_record_items(student_id)
        intro_snapshot, intro_notes = _intro_record_meta(student_id)
        if intro_items:
            split_xeno, split_titanic = split_intro_flat_items(intro_items)
            if xeno_items is None:
                xeno_items = split_xeno
            if titanic_items is None:
                titanic_items = split_titanic
            if not xeno_snapshot and not titanic_snapshot:
                pass  # validators build per-worksheet summaries
            elif not xeno_snapshot:
                xeno_snapshot = intro_snapshot
            elif not titanic_snapshot:
                titanic_snapshot = intro_snapshot
            if xeno_notes == "(bos)" and intro_notes != "(bos)":
                xeno_notes = intro_notes
            if titanic_notes == "(bos)" and intro_notes != "(bos)":
                titanic_notes = intro_notes
        else:
            if combined_doc is None:
                combined_path = OCR_OUTPUT_DIR / student_id / f"{student_id}_Worksheet_Xeno_Titanic.json"
                if not combined_path.is_file():
                    raise FileNotFoundError(
                        f"No split student records or combined ocr_output for {student_id}"
                    )
                combined_doc = json.loads(combined_path.read_text(encoding="utf-8"))
            flat = flatten_combined_extraction(combined_doc.get("extraction") or {})
            split_xeno, split_titanic = split_intro_flat_items(flat)
            if xeno_items is None:
                xeno_items = split_xeno
            if titanic_items is None:
                titanic_items = split_titanic
            if not xeno_snapshot:
                xeno_snapshot = str(combined_doc.get("ws_snapshot") or "")
            if not titanic_snapshot:
                titanic_snapshot = str(combined_doc.get("ws_snapshot") or "")
            if xeno_notes == "(bos)" and titanic_notes == "(bos)":
                shared_notes = str(combined_doc.get("page_notes") or "(bos)")
                xeno_notes = shared_notes
                titanic_notes = shared_notes

    return (
        xeno_items,
        titanic_items,
        xeno_snapshot,
        titanic_snapshot,
        xeno_notes,
        titanic_notes,
    )


def export_split_ocr_output(
    student_id: str,
    *,
    combined_doc: dict[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Write separate WS_DT_XENO and WS_DT_TITANIC ocr_output JSON files."""
    (
        xeno_items,
        titanic_items,
        xeno_snapshot,
        titanic_snapshot,
        xeno_notes,
        titanic_notes,
    ) = load_split_items(student_id, combined_doc=combined_doc)

    xeno_path = export_xeno_ocr_output(
        student_id,
        xeno_items,
        ws_snapshot=xeno_snapshot,
        page_notes=xeno_notes,
    )
    titanic_path = export_titanic_ocr_output(
        student_id,
        titanic_items,
        ws_snapshot=titanic_snapshot,
        page_notes=titanic_notes,
    )
    return xeno_path, titanic_path



def sectioned_extraction(items: dict[str, str]) -> dict[str, dict[str, str]]:
    xeno = {iid: items.get(iid, "(not_extracted)") for iid in XENO_ITEM_IDS}
    titanic = titanic_sectioned(items)
    return {"xeno_section": xeno, **titanic}


def build_validation(items: dict[str, str], *, ws_snapshot: str = "") -> dict[str, Any]:
    xeno_val = build_xeno_validation(items, ws_snapshot="")
    titanic_val = build_titanic_validation(items, ws_snapshot="")
    item_checks = {
        **xeno_val.get("item_checks", {}),
        **titanic_val.get("item_checks", {}),
    }
    summary = ws_snapshot or (
        f"{xeno_val.get('system_analytical_summary', '')} "
        f"{titanic_val.get('system_analytical_summary', '')}"
    ).strip()
    return {
        "xeno_consistency_checks": xeno_val.get("xeno_consistency_checks", {}),
        "titanic_numeric_checks": titanic_val.get("titanic_numeric_checks", {}),
        "titanic_reading_errors": titanic_val.get("titanic_reading_errors", {}),
        "trap_question_check": titanic_val.get("trap_question_check", {}),
        "item_checks": item_checks,
        "system_analytical_summary": summary,
    }


def build_ocr_output_document(
    student_id: str,
    items: dict[str, str],
    *,
    ws_snapshot: str = "",
    page_notes: str = "(bos)",
) -> dict[str, Any]:
    corrected, _ = titanic_apply_corrections(items)
    validation = build_validation(items, ws_snapshot=ws_snapshot)
    return {
        "student_id": student_id,
        "worksheet": "WS_DT_INTRO",
        "ws_snapshot": ws_snapshot or validation["system_analytical_summary"],
        "page_notes": page_notes,
        "extraction": sectioned_extraction(corrected),
        "validation": validation,
    }


def export_ocr_output(student_id: str, items: dict[str, str], **kwargs: Any):
    """Legacy combined export — prefer ws_dt_xeno_validation / ws_dt_titanic_validation."""
    from pathlib import Path
    import json
    from pipeline_schema import OCR_OUTPUT_DIR

    doc = build_ocr_output_document(student_id, items, **kwargs)
    out_dir = OCR_OUTPUT_DIR / student_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{student_id}_Worksheet_Xeno_Titanic.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


# Re-export helpers used by tests / older imports
apply_operator_corrections = titanic_apply_corrections


def flat_items_from_extraction_record(record: dict) -> dict[str, str]:
    g1 = record.get("gate_1_extraction") or {}
    if g1.get("items"):
        return dict(g1["items"])
    return dict(record.get("responses") or {})
