"""
ws_lo_aggregator.py — Aggregate worksheet item scores to top-level LO scores.

Reads students/<id>/<WS>/scoring.json and mappings/WS*_AICFT_mapping.json.
Produces outputs/ws_lo/<student_id>_ws_lo.json.

LO codes in mapping files use granular notation (e.g. LO3.1.2).
This module collapses them to top-level LOs: LO3.1, LO3.2, LO3.3.
"""

from __future__ import annotations

import json
import logging
import warnings
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
STUDENTS_DIR = REPO_ROOT / "students"
MAPPINGS_DIR = REPO_ROOT / "mappings"
OUTPUT_DIR = REPO_ROOT / "outputs" / "ws_lo"

TOP_LEVEL_LOS = ("LO3.1", "LO3.2", "LO3.3")

# Confidence threshold below which evidence_strength is capped at "weak".
CONFIDENCE_THRESHOLD = 0.70

_STRENGTH_ORDER = {"strong": 2, "weak": 1, "absent": 0}


def lo_parent(lo_code: str) -> str | None:
    """Map granular LO code to top-level parent.

    "LO3.1.2" -> "LO3.1", "LO3.2.3" -> "LO3.2", "LO3.3.1" -> "LO3.3".
    Returns None if the code does not map to a known top-level LO.
    """
    parts = lo_code.strip().split(".")
    if len(parts) < 2 or parts[0] != "LO3":
        return None
    candidate = f"LO3.{parts[1]}"
    return candidate if candidate in TOP_LEVEL_LOS else None


def load_ws_mapping(worksheet: str) -> dict[str, list[str]] | None:
    """Load item -> [parent LO codes] mapping for a worksheet.

    Returns None if no mapping file exists (caller should warn and skip).
    """
    path = MAPPINGS_DIR / f"{worksheet}_AICFT_mapping.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    result: dict[str, list[str]] = {}
    for item_id, item_data in raw.get("items", {}).items():
        comps: list[dict[str, Any]] = (
            item_data if isinstance(item_data, list)
            else item_data.get("competencies", [])
        )
        parents: list[str] = []
        for c in comps:
            if not isinstance(c, dict):
                continue
            parent = lo_parent(c.get("lo", ""))
            if parent and parent not in parents:
                parents.append(parent)
        if parents:
            result[item_id] = parents
    return result


def _strength_for_item(score: float, review: bool) -> str:
    """Compute evidence_strength for a single scored item."""
    if score == 0:
        return "absent"
    return "weak" if review else "strong"


def _merge_strength(a: str, b: str) -> str:
    """Return the stronger of two evidence_strength values."""
    return a if _STRENGTH_ORDER.get(a, 0) >= _STRENGTH_ORDER.get(b, 0) else b


def aggregate_student_ws_lo(
    student_id: str,
    *,
    students_dir: Path | None = None,
) -> dict[str, Any]:
    """Build LO aggregation from all worksheet scoring artifacts for one student.

    For each LO, takes MAX score across all items that map to it.
    evidence_strength is "weak" if any contributing item has review=True;
    "absent" if score==0; "strong" otherwise.
    """
    root = (students_dir or STUDENTS_DIR) / student_id

    lo_scores: dict[str, float] = {lo: 0.0 for lo in TOP_LEVEL_LOS}
    lo_max: dict[str, float] = {lo: 0.0 for lo in TOP_LEVEL_LOS}
    lo_items: dict[str, list[str]] = {lo: [] for lo in TOP_LEVEL_LOS}
    lo_review_flags: dict[str, list[str]] = {lo: [] for lo in TOP_LEVEL_LOS}
    lo_strength: dict[str, str] = {lo: "absent" for lo in TOP_LEVEL_LOS}

    if not root.is_dir():
        log.warning("Student directory not found: %s", root)
        return _empty_ws_lo(student_id)

    worksheets = [
        p.name for p in sorted(root.iterdir())
        if p.is_dir() and (p / "scoring.json").exists()
    ]

    for ws in worksheets:
        mapping = load_ws_mapping(ws)
        if mapping is None:
            log.warning("No AICFT mapping for %s — skipping", ws)
            continue

        scoring_path = root / ws / "scoring.json"
        data = json.loads(scoring_path.read_text(encoding="utf-8"))
        if data.get("blocked"):
            log.info("Skipping blocked scoring for %s/%s: %s", student_id, ws, data.get("blocked_reason"))
            continue
        items: list[dict[str, Any]] = data.get("items", [])

        for rec in items:
            if not isinstance(rec, dict):
                continue
            item_id: str = rec.get("item", "")
            raw_score = rec.get("score")
            review: bool = bool(rec.get("review", False))
            confidence: float | None = rec.get("confidence")

            if raw_score is None:
                continue
            score = float(raw_score)

            # Confidence below threshold caps strength at weak.
            confidence_weak = (
                confidence is not None and confidence < CONFIDENCE_THRESHOLD
            )

            lo_list = mapping.get(item_id, [])
            for lo in lo_list:
                if lo not in TOP_LEVEL_LOS:
                    continue

                # Rubric max_score from mapping is not easily available here;
                # track per-item max from rubric separately if needed.
                # For now: max is the max observed score (proxy).
                if score > lo_scores[lo]:
                    lo_scores[lo] = score

                item_strength = _strength_for_item(score, review or confidence_weak)

                if score > 0 and item_id not in lo_items[lo]:
                    lo_items[lo].append(item_id)
                if review and item_id not in lo_review_flags[lo]:
                    lo_review_flags[lo].append(item_id)

                lo_strength[lo] = _merge_strength(lo_strength[lo], item_strength)

    # Build lo_max from rubric files for each worksheet.
    lo_max = _compute_lo_max_scores(worksheets, students_dir=students_dir)

    lo_profiles: dict[str, Any] = {}
    for lo in TOP_LEVEL_LOS:
        lo_profiles[lo] = {
            "score": lo_scores[lo],
            "max_score": lo_max.get(lo, 0.0),
            "evidence_strength": lo_strength[lo],
            "contributing_items": sorted(lo_items[lo]),
            "review_flags": sorted(lo_review_flags[lo]),
        }

    return {
        "student_id": student_id,
        "source": "worksheet",
        "lo_scores": lo_profiles,
    }


def _compute_lo_max_scores(
    worksheets: list[str],
    *,
    students_dir: Path | None = None,
) -> dict[str, float]:
    """Compute max possible score per top-level LO across given worksheets."""
    from pipeline_schema import load_rubric

    lo_max: dict[str, float] = {lo: 0.0 for lo in TOP_LEVEL_LOS}

    for ws in worksheets:
        mapping = load_ws_mapping(ws)
        if mapping is None:
            continue
        try:
            rubric = load_rubric(ws)
        except FileNotFoundError:
            log.warning("No rubric for %s — skipping max_score computation", ws)
            continue
        rubric_items = rubric.get("items", {})
        for item_id, lo_list in mapping.items():
            item_cfg = rubric_items.get(item_id, {})
            item_max = float(item_cfg.get("max_score", 0))
            for lo in lo_list:
                if lo in TOP_LEVEL_LOS:
                    lo_max[lo] = max(lo_max[lo], item_max)

    return lo_max


def _empty_ws_lo(student_id: str) -> dict[str, Any]:
    return {
        "student_id": student_id,
        "source": "worksheet",
        "lo_scores": {
            lo: {
                "score": 0.0,
                "max_score": 0.0,
                "evidence_strength": "absent",
                "contributing_items": [],
                "review_flags": [],
            }
            for lo in TOP_LEVEL_LOS
        },
    }


def run_student(
    student_id: str,
    *,
    students_dir: Path | None = None,
    output_dir: Path | None = None,
) -> Path:
    """Aggregate and write ws_lo JSON for one student. Returns output path."""
    out_dir = output_dir or OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    result = aggregate_student_ws_lo(student_id, students_dir=students_dir)
    out_path = out_dir / f"{student_id}_ws_lo.json"
    out_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return out_path


def run_all(
    *,
    students_dir: Path | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    """Aggregate ws_lo for all students with any scoring.json. Returns written paths."""
    root = students_dir or STUDENTS_DIR
    if not root.is_dir():
        log.warning("Students dir not found: %s", root)
        return []
    student_ids = [
        d.name for d in sorted(root.iterdir())
        if d.is_dir() and any(d.glob("*/scoring.json"))
    ]
    paths: list[Path] = []
    for sid in student_ids:
        paths.append(run_student(sid, students_dir=students_dir, output_dir=output_dir))
    return paths
