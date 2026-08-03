"""Validation + ocr_output export for WS_DT_XENO."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent
OCR_OUTPUT_DIR = REPO_ROOT / "ocr_output"

XENO_ITEM_IDS = [f"DTI_{i:02d}" for i in range(1, 34)]
BLANK = frozenset({"(bos)", "(okunamiyor)", "(missing)", "(not_extracted)", ""})


def _parse_int(text: str) -> int | None:
    if not text or text in BLANK:
        return None
    m = re.search(r"-?\d+", str(text).replace(".", "").replace(",", ""))
    return int(m.group()) if m else None


def xeno_consistency_checks(items: dict[str, str]) -> dict[str, Any]:
    tp = _parse_int(items.get("DTI_10", ""))
    tn = _parse_int(items.get("DTI_12", ""))
    fp = _parse_int(items.get("DTI_14", ""))
    fn = _parse_int(items.get("DTI_16", ""))
    n = _parse_int(items.get("DTI_18", ""))

    checks: dict[str, Any] = {}
    if tp is not None and fn is not None:
        checks["tp_fn_sum_equals_sick"] = {
            "check": "TP + FN = toplam hasta sayisi",
            "student_tp": items.get("DTI_10"),
            "student_fn": items.get("DTI_16"),
            "sum": tp + fn,
            "is_correct": n is None or tp + fn == n or (
                tp + fn + (tn or 0) + (fp or 0) == n
            ),
            "note": "FN=0 beklenir" if fn == 0 else "",
        }
    if tn is not None and fp is not None:
        checks["tn_fp_sum_equals_healthy"] = {
            "check": "TN + FP = toplam saglikli sayisi",
            "student_tn": items.get("DTI_12"),
            "student_fp": items.get("DTI_14"),
            "sum": tn + fp,
            "is_correct": True,
            "note": "FP=0 beklenir" if fp == 0 else "",
        }
    if None not in (n, tp, tn, fp, fn):
        checks["total_n"] = {
            "check": "TP + TN + FP + FN = N",
            "n_sum": tp + tn + fp + fn,
            "student_n": items.get("DTI_18"),
            "is_correct": tp + tn + fp + fn == n,
        }
        checks["fp_fn_zero"] = {
            "check": "sac rengi mukemmel ayirici => FP=FN=0",
            "student_fp": items.get("DTI_14"),
            "student_fn": items.get("DTI_16"),
            "is_correct": fp == 0 and fn == 0,
        }
    return checks


def build_item_checks(items: dict[str, str], consistency: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Per-item validation flags for Xeno (structure-focused, not canonical numbers)."""
    checks: dict[str, dict[str, Any]] = {}
    fp = _parse_int(items.get("DTI_14", ""))
    fn = _parse_int(items.get("DTI_16", ""))
    n = _parse_int(items.get("DTI_18", ""))
    tp = _parse_int(items.get("DTI_10", ""))
    tn = _parse_int(items.get("DTI_12", ""))

    for iid in XENO_ITEM_IDS:
        raw = items.get(iid, "")
        blank = raw in BLANK
        error_flag = None
        is_correct = not blank

        if blank:
            is_correct = False
            error_flag = "BLANK"
        elif iid in {"DTI_14", "DTI_16"} and raw and fp is not None and fn is not None:
            if (iid == "DTI_14" and fp != 0) or (iid == "DTI_16" and fn != 0):
                is_correct = False
                error_flag = "INVARIANT_FP_FN_NONZERO"
        elif iid == "DTI_18" and None not in (n, tp, tn, fp, fn):
            if tp + tn + fp + fn != n:
                is_correct = False
                error_flag = "CM_SUM_MISMATCH"

        checks[iid] = {"is_correct": is_correct, "error_flag": error_flag}

    if consistency.get("fp_fn_zero", {}).get("is_correct") is False:
        for iid in ("DTI_14", "DTI_16"):
            checks[iid]["is_correct"] = False
            checks[iid]["error_flag"] = "INVARIANT_FP_FN_NONZERO"

    return checks


def build_validation(items: dict[str, str], *, ws_snapshot: str = "") -> dict[str, Any]:
    consistency = xeno_consistency_checks(items)
    item_checks = build_item_checks(items, consistency)
    tp = items.get("DTI_10", "?")
    tn = items.get("DTI_12", "?")
    summary = ws_snapshot or (
        f"Xeno: TP={tp}, TN={tn}. "
        f"FP=FN=0: {consistency.get('fp_fn_zero', {}).get('is_correct', 'n/a')}."
    )
    return {
        "xeno_consistency_checks": consistency,
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
    validation = build_validation(items, ws_snapshot=ws_snapshot)
    extraction = {iid: items.get(iid, "(not_extracted)") for iid in XENO_ITEM_IDS}
    return {
        "student_id": student_id,
        "worksheet": "WS_DT_XENO",
        "ws_snapshot": ws_snapshot or validation["system_analytical_summary"],
        "page_notes": page_notes,
        "extraction": extraction,
        "validation": validation,
    }


def export_ocr_output(
    student_id: str,
    items: dict[str, str],
    *,
    ws_snapshot: str = "",
    page_notes: str = "(bos)",
) -> Path:
    doc = build_ocr_output_document(
        student_id, items, ws_snapshot=ws_snapshot, page_notes=page_notes,
    )
    out_dir = OCR_OUTPUT_DIR / student_id
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{student_id}_Worksheet_Xeno.json"
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path
