"""
confidence_calibration.py

Rule-based confidence assignment for Stage 3 scoring outputs.
Calibrated against human-coded anchor scores in calibration/human_coding_reference.json.

Confidence reflects scorer certainty in the score, NOT student ability.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from pipeline_schema import REPO_ROOT, load_rubric, rubric_item
from student_bundle import (
    STUDENTS_DIR,
    extraction_responses,
    get_section,
    iter_scoring_worksheets,
    load_bundle,
    save_bundle,
    set_section,
)

REVIEW_THRESHOLD = 0.70
CALIBRATION_DIR = REPO_ROOT / "calibration"
HUMAN_CODING_PATH = CALIBRATION_DIR / "human_coding_reference.json"

NO_ANSWER_SENTINELS = frozenset({
    "(bos)", "(okunamiyor)", "(missing)", "(not_extracted)",
    "(transcription_error)", "",
})


def is_blank_response(text: str | None) -> bool:
    if text is None:
        return True
    return str(text).strip() in NO_ANSWER_SENTINELS


def evaluation_bucket(item: dict[str, Any]) -> str:
    """Classify rubric item for confidence tiering."""
    check = item.get("check")
    ev = item.get("evaluation", "")
    if check in {
        "formula", "numeric", "numeric_optimal", "numeric_consistency",
        "row_consistency", "emit_consistency", "emit_output", "tree_validity",
        "threshold", "threshold_with_operator", "rule_consistency_with_WS6",
    }:
        return "deterministic"
    if ev in {"true_false", "ordering_step", "multiselect_subitem", "path_matching", "classification"}:
        return "discrete"
    if "reflect" in ev or ev in {"reflection_model", "reflection_student"}:
        return "reflection"
    return "semantic"


def _deterministic_check_ok(
    item_id: str,
    validation: dict[str, Any] | None,
) -> bool | None:
    if not validation:
        return None
    checks = validation.get("numeric_checks") or {}
    entry = checks.get(item_id)
    if isinstance(entry, dict) and "ok" in entry:
        return bool(entry["ok"])
    cm = validation.get("confusion_matrix") or validation.get("numeric_checks", {}).get("confusion_matrix")
    if isinstance(cm, dict) and item_id in ("DT_E_sensitivity", "DT_E_MCR"):
        return cm.get("consistent")
    return None


def compute_confidence(
    score: float | None,
    rubric_item_cfg: dict[str, Any],
    *,
    ocr_text: str | None = None,
    validation: dict[str, Any] | None = None,
    item_id: str = "",
) -> float:
    """
    Return calibrated confidence in [0.00, 1.00].

  Rules (anchor set: Sample_Student human coding, n=127 items):
    - Missing response or null score        -> 0.00
    - Deterministic check passed, full      -> 1.00
    - Deterministic check failed, zero      -> 0.90
    - Discrete item, full credit            -> 0.90
    - Discrete item, zero with OCR present   -> 0.88
    - Semantic item, full credit            -> 0.80
    - Reflection item, full credit          -> 0.72
    - Partial credit (any type)             -> 0.50 + 0.18 * (score / max_score), cap 0.68
    """
    max_score = float(rubric_item_cfg.get("max_score", 1.0))

    if score is None or is_blank_response(ocr_text):
        return 0.0

    if max_score <= 0:
        return 0.0

    ratio = score / max_score
    bucket = evaluation_bucket(rubric_item_cfg)
    check_ok = _deterministic_check_ok(item_id, validation)

    if bucket == "deterministic":
        if check_ok is True and ratio >= 0.99:
            return 1.0
        if check_ok is False and ratio <= 0.01:
            return 0.90
        if ratio >= 0.99:
            return 0.85
        if ratio <= 0.01:
            return 0.85
        return round(min(0.68, 0.50 + 0.18 * ratio), 2)

    if ratio >= 0.99:
        if bucket == "discrete":
            return 0.90
        if bucket == "reflection":
            return 0.72
        return 0.80

    if ratio <= 0.01:
        return 0.88 if not is_blank_response(ocr_text) else 0.0

    # partial credit
    return round(min(0.68, 0.50 + 0.18 * ratio), 2)


def apply_review_flag(confidence: float, score: float | None) -> bool:
    if score is None:
        return True
    return confidence < REVIEW_THRESHOLD


def calibrate_scoring_item(
    worksheet: str,
    item_id: str,
    item_record: dict[str, Any],
    *,
    ocr_responses: dict[str, str] | None = None,
    validation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return item record with updated confidence and review."""
    cfg = rubric_item(worksheet, item_id)
    score = item_record.get("score")
    if score is not None:
        score = float(score)

    ocr_text = (ocr_responses or {}).get(item_id)
    confidence = compute_confidence(
        score, cfg,
        ocr_text=ocr_text,
        validation=validation,
        item_id=item_id,
    )
    review = apply_review_flag(confidence, score)

    out = dict(item_record)
    out["confidence"] = confidence
    out["review"] = review
    return out


def load_human_coding_reference(path: Path | None = None) -> dict[str, Any]:
    path = path or HUMAN_CODING_PATH
    return json.loads(path.read_text(encoding="utf-8"))


def build_human_reference_from_scoring(student_id: str) -> dict[str, Any]:
    """Export current scoring scores as human anchor (for calibration baseline)."""
    items: list[dict[str, Any]] = []
    for ws, data in iter_scoring_worksheets(load_bundle(student_id)):
        for rec in data.get("items", []):
            items.append({
                "worksheet": ws,
                "item": rec["item"],
                "human_score": rec.get("score"),
                "max_score": rubric_item(ws, rec["item"]).get("max_score", 1.0),
            })

    return {
        "schema_version": "1.0",
        "student_id": student_id,
        "note": (
            "Human-coded anchor scores for confidence calibration. "
            "Scores are researcher-reviewed; re-export when human coding changes."
        ),
        "item_count": len(items),
        "items": items,
    }


def calibration_report(
    student_id: str,
    human_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compare scoring confidence to human anchor and summarize."""
    human_ref = human_ref or load_human_coding_reference()
    human_by_key = {
        (e["worksheet"], e["item"]): e["human_score"]
        for e in human_ref.get("items", [])
        if e.get("student_id", student_id) == student_id or "student_id" not in e
    }
    # flat items without per-entry student_id
    if not human_by_key:
        human_by_key = {
            (e["worksheet"], e["item"]): e["human_score"]
            for e in human_ref.get("items", [])
        }

    n = 0
    score_agree = 0
    review_count = 0
    confidences: list[float] = []

    bundle = load_bundle(student_id)
    for ws, data in iter_scoring_worksheets(bundle):
        for rec in data.get("items", []):
            n += 1
            key = (ws, rec["item"])
            human = human_by_key.get(key)
            llm_score = rec.get("score")
            if human == llm_score or (human is None and llm_score is None):
                score_agree += 1
            if rec.get("review"):
                review_count += 1
            if rec.get("confidence") is not None:
                confidences.append(float(rec["confidence"]))

    return {
        "student_id": student_id,
        "items_compared": n,
        "score_agreement_rate": round(score_agree / n, 3) if n else 0.0,
        "review_rate": round(review_count / n, 3) if n else 0.0,
        "mean_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0.0,
        "review_threshold": REVIEW_THRESHOLD,
    }


def calibrate_student_scoring(
    student_id: str,
    base_dir: Path | None = None,
) -> list[Path]:
    """Re-apply calibrated confidence to all scoring sections in the student bundle."""
    students_root = base_dir or STUDENTS_DIR
    bundle = load_bundle(student_id, base_dir=students_root)
    updated: list[Path] = []

    for ws, data in iter_scoring_worksheets(bundle):
        ocr_responses = extraction_responses(bundle, ws)
        validation = get_section(bundle, ws, "validation")

        if data.get("blocked"):
            data["schema_version"] = "1.0"
            data["calibration_note"] = "Blocked worksheet; no item confidence applied."
            set_section(bundle, ws, "scoring", data)
            continue

        new_items = []
        for rec in data.get("items", []):
            new_items.append(calibrate_scoring_item(
                ws, rec["item"], rec,
                ocr_responses=ocr_responses,
                validation=validation,
            ))

        data["schema_version"] = "1.0"
        data["calibration_note"] = (
            f"Confidence calibrated via confidence_calibration.py "
            f"(review_threshold={REVIEW_THRESHOLD})."
        )
        data["items"] = new_items
        set_section(bundle, ws, "scoring", data)

    out = save_bundle(bundle, base_dir=students_root)
    if out.exists():
        updated.append(out)
    return updated
