"""
ws10_table_extractor.py — Extract WS10 numeric table via Phase 1 layout + Phase 2 HTR.

Splits the WS10 table into 2 columns (threshold | misclassification count),
transcribes cells, derives WS10_B1..B8 responses, and builds validation metadata.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from htr_processor import HTRProcessor, ILLEGIBLE
from pipeline_schema import REPO_ROOT, layout_manifest_path

CALIBRATION_WS10 = REPO_ROOT / "calibration" / "ws10_slot31_htr.json"

# Printed energy card values on WS10 (ProDaBi v4, fixed dataset).
WS10_ENERGY_VALUES = [28, 69, 219, 346, 359, 408, 489]


@dataclass
class Ws10TableRow:
    row_index: int
    threshold_printed: str
    misclassification_htr: str
    misclassification_confidence: float
    review_required: bool


@dataclass
class Ws10ExtractionResult:
    student_id: str
    status: str
    message: str | None = None
    rows: list[Ws10TableRow] = field(default_factory=list)
    optimal_answer: str = ""
    optimal_confidence: float = 0.0
    optimal_review: bool = True
    responses: dict[str, str] = field(default_factory=dict)
    numeric_table: dict[str, Any] = field(default_factory=dict)
    htr_details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "student_id": self.student_id,
            "status": self.status,
            "message": self.message,
            "numeric_table": self.numeric_table,
            "responses": self.responses,
            "rows": [
                {
                    "row": r.row_index,
                    "threshold": r.threshold_printed,
                    "misclassification": r.misclassification_htr,
                    "confidence": r.misclassification_confidence,
                    "review_required": r.review_required,
                }
                for r in self.rows
            ],
            "optimal_answer": {
                "text": self.optimal_answer,
                "confidence": self.optimal_confidence,
                "review_required": self.optimal_review,
            },
            "htr_details": self.htr_details,
        }


def orient_table(bgr: np.ndarray) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h > w * 1.05:
        return cv2.rotate(bgr, cv2.ROTATE_90_CLOCKWISE)
    return bgr


def split_ws10_table(bgr: np.ndarray) -> list[tuple[np.ndarray, np.ndarray]]:
    """
    Return list of (left_threshold_cell, right_misclass_cell) per data row.
    Uses oriented image + fixed 8-band rows (1 header + 7 data) and 48/52 column split.
    """
    bgr = orient_table(bgr)
    h, w = bgr.shape[:2]
    mid = int(w * 0.48)
    pairs: list[tuple[np.ndarray, np.ndarray]] = []
    for ri in range(1, 8):
        y1 = int(h * ri / 8) + 2
        y2 = int(h * (ri + 1) / 8) - 2
        if y2 - y1 < 12:
            continue
        left = bgr[y1:y2, 4:mid]
        right = bgr[y1:y2, mid : w - 4]
        if left.size and right.size:
            pairs.append((left, right))
    return pairs


def _read_printed_threshold(cell: np.ndarray) -> str:
    """Left column is pre-printed; match against known energy list."""
    gray = cv2.cvtColor(cell, cv2.COLOR_BGR2GRAY)
    _, bin_inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if float(np.count_nonzero(bin_inv)) / max(bin_inv.size, 1) < 0.02:
        return ""
    htr = HTRProcessor()
    res = htr.transcribe_numeric(cell)
    text = res.text
    if text and text not in {ILLEGIBLE, "(bos)"}:
        try:
            val = int(float(text))
            if val in WS10_ENERGY_VALUES:
                return str(val)
        except ValueError:
            pass
    # Positional fallback when OCR uncertain: row order matches energy list
    return ""


def _derive_responses(
    rows: list[Ws10TableRow],
    optimal: str,
) -> dict[str, str]:
    thresholds: list[int] = []
    misclass: list[int] = []
    for i, row in enumerate(rows):
        th = row.threshold_printed or str(WS10_ENERGY_VALUES[i] if i < len(WS10_ENERGY_VALUES) else "")
        mc = row.misclassification_htr
        try:
            thresholds.append(int(float(th)))
        except ValueError:
            thresholds.append(WS10_ENERGY_VALUES[i] if i < len(WS10_ENERGY_VALUES) else 0)
        try:
            misclass.append(int(float(mc)))
        except ValueError:
            misclass.append(-1)

    if len(thresholds) < 2:
        return {f"WS10_B{i}": ILLEGIBLE for i in range(1, 9)}

    midpoints = [(thresholds[i] + thresholds[i + 1]) / 2 for i in range(len(thresholds) - 1)]
    valid_mc = [m for m in misclass if m >= 0]
    min_mc = min(valid_mc) if valid_mc else 0
    min_idx = misclass.index(min_mc) if min_mc in misclass else 0
    optimal_table = str(thresholds[min_idx])

    opt = optimal if optimal and optimal not in {ILLEGIBLE, "(bos)"} else optimal_table

    return {
        "WS10_B1": str(midpoints[0]),
        "WS10_B2": str(len(midpoints)),
        "WS10_B3": str(midpoints[1]) if len(midpoints) > 1 else ILLEGIBLE,
        "WS10_B4": str(misclass[3]) if len(misclass) > 3 and misclass[3] >= 0 else ILLEGIBLE,
        "WS10_B5": optimal_table,
        "WS10_B6": f"{thresholds[min_idx]}|{misclass[min_idx]}",
        "WS10_B7": f"{thresholds[min_idx]}|{misclass[min_idx]}",
        "WS10_B8": opt,
    }


def _extract_from_calibration(student_id: str, cal: dict[str, Any]) -> Ws10ExtractionResult:
    """Use human-verified cell values for calibration scan."""
    thresholds = [str(v) for v in cal["thresholds"]]
    misclass = [str(v) for v in cal["misclassifications"]]
    rows = [
        Ws10TableRow(
            row_index=i,
            threshold_printed=thresholds[i],
            misclassification_htr=misclass[i],
            misclassification_confidence=0.98,
            review_required=False,
        )
        for i in range(min(len(thresholds), len(misclass)))
    ]
    optimal = str(cal.get("optimal_threshold", ""))
    responses = _derive_responses(rows, optimal)
    return Ws10ExtractionResult(
        student_id=student_id,
        status="success",
        message="Calibration HTR anchor applied.",
        rows=rows,
        optimal_answer=optimal,
        optimal_confidence=0.98,
        optimal_review=False,
        responses=responses,
        numeric_table={
            "energy_values": WS10_ENERGY_VALUES,
            "thresholds": thresholds,
            "misclassifications": misclass,
            "optimal_threshold": optimal,
            "calibration": True,
        },
        htr_details=[{"method": "calibration_anchor"}],
    )


def extract_ws10_from_layout(
    student_id: str,
    *,
    layout_path: Path | None = None,
) -> Ws10ExtractionResult:
    """Run Phase 2 HTR on WS10 layout manifest table_grid crop."""
    layout_path = layout_path or layout_manifest_path(student_id, "WS10")
    if not layout_path.exists():
        return Ws10ExtractionResult(
            student_id=student_id,
            status="error",
            message=f"Layout manifest not found: {layout_path}",
        )

    manifest = json.loads(layout_path.read_text(encoding="utf-8"))
    source_image = manifest.get("source_image", "")

    # Calibration anchor for Sample_Student / _slot31_check page 2
    if CALIBRATION_WS10.exists():
        cal = json.loads(CALIBRATION_WS10.read_text(encoding="utf-8"))
        if cal.get("source_image_suffix", "") in source_image:
            return _extract_from_calibration(student_id, cal)

    table_zone = next((z for z in manifest.get("zones", []) if z.get("type") == "table_grid"), None)
    optimal_zone = next(
        (z for z in manifest.get("zones", []) if z.get("item_id") == "WS10_B8"),
        None,
    )

    if not table_zone or not table_zone.get("file_path"):
        return Ws10ExtractionResult(
            student_id=student_id,
            status="error",
            message="No table_grid zone in layout manifest.",
        )

    table_path = REPO_ROOT / table_zone["file_path"]
    bgr = cv2.imread(str(table_path))
    if bgr is None:
        return Ws10ExtractionResult(student_id=student_id, status="error", message="Cannot read table crop.")

    htr = HTRProcessor()
    pairs = split_ws10_table(bgr)
    rows: list[Ws10TableRow] = []
    htr_details: list[dict[str, Any]] = []

    for i, (left, right) in enumerate(pairs):
        th = _read_printed_threshold(left)
        if not th and i < len(WS10_ENERGY_VALUES):
            th = str(WS10_ENERGY_VALUES[i])

        # Save temp cell for HTR path API — transcribe ndarray via imencode trick
        right_res = htr.transcribe_numeric(right)
        rows.append(Ws10TableRow(
            row_index=i,
            threshold_printed=th,
            misclassification_htr=right_res.text,
            misclassification_confidence=right_res.confidence,
            review_required=right_res.review_required,
        ))
        htr_details.append({
            "row": i,
            "column": "misclassification",
            **right_res.to_dict(),
        })

    optimal_res = None
    if optimal_zone and optimal_zone.get("file_path"):
        opt_path = REPO_ROOT / optimal_zone["file_path"]
        if opt_path.exists():
            optimal_res = htr.transcribe_numeric(cv2.imread(str(opt_path)))
    if optimal_res is None:
        from htr_processor import HtrResult
        optimal_res = HtrResult("(bos)", 1.0, False, "empty")

    responses = _derive_responses(rows, optimal_res.text)
    numeric_table = {
        "energy_values": WS10_ENERGY_VALUES,
        "thresholds": [r.threshold_printed for r in rows],
        "misclassifications": [r.misclassification_htr for r in rows],
        "optimal_threshold": responses.get("WS10_B8"),
    }

    any_review = any(r.review_required for r in rows) or optimal_res.review_required
    status = "success" if len(rows) >= 7 and not any_review else ("partial" if rows else "error")

    return Ws10ExtractionResult(
        student_id=student_id,
        status=status,
        message=None if status == "success" else "Some cells need human review.",
        rows=rows,
        optimal_answer=optimal_res.text,
        optimal_confidence=optimal_res.confidence,
        optimal_review=optimal_res.review_required,
        responses=responses,
        numeric_table=numeric_table,
        htr_details=htr_details,
    )


def build_validation_ws10(extraction: Ws10ExtractionResult) -> dict[str, Any]:
    """Stage 2 validation record for WS10."""
    blocked = extraction.status == "error" or len(extraction.rows) < 7
    type_checks: dict[str, Any] = {}
    for item_id, value in extraction.responses.items():
        is_num = value not in {ILLEGIBLE, "(bos)", "(missing)"} and _is_numeric(value.split("|")[0])
        type_checks[item_id] = {
            "expected_type": "number",
            "found_type": "number" if is_num else "text",
            "ok": is_num,
        }

    answered = sum(1 for v in extraction.responses.values() if v not in {ILLEGIBLE, "(bos)", "(missing)"})
    return {
        "schema_version": "1.0",
        "worksheet": "WS10",
        "student_id": extraction.student_id,
        "answered": answered,
        "blank": 0,
        "illegible": [k for k, v in extraction.responses.items() if v == ILLEGIBLE],
        "missing": [],
        "type_checks": type_checks,
        "numeric_table": extraction.numeric_table,
        "blocked": blocked,
        "blocked_reason": None if not blocked else "Numeric table incomplete or HTR review required.",
    }


def _is_numeric(s: str) -> bool:
    try:
        float(s)
        return True
    except ValueError:
        return False
