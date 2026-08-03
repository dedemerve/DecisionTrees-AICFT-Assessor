"""Helpers for ham vs labeled transcript separation."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent

SPEAKER_SEGMENT_FIELDS = (
    "speaker_role",
    "speaker_confidence",
    "speaker_method",
    "speaker_id",
    "focal_pt_student_id",
    "needs_review",
    "review_reason",
)

SPEAKER_TOP_LEVEL_FIELDS = ("speaker_labeling",)


def strip_segment_speaker_fields(segment: dict[str, Any]) -> dict[str, Any]:
    out = {k: v for k, v in segment.items() if k not in SPEAKER_SEGMENT_FIELDS}
    return out


def strip_transcript_to_ham(transcript: dict[str, Any]) -> dict[str, Any]:
    """Return mlx transcript without speaker labeling artifacts."""
    ham = copy.deepcopy(transcript)
    for key in SPEAKER_TOP_LEVEL_FIELDS:
        ham.pop(key, None)
    if ham.get("segments"):
        ham["segments"] = [strip_segment_speaker_fields(s) for s in ham["segments"]]
    return ham


def labeled_transcript_path(student_dir: Path, student_id: str) -> Path:
    return student_dir / f"{student_id}_transcript_labeled.json"


def ham_transcript_path(student_dir: Path, student_id: str) -> Path:
    return student_dir / f"{student_id}_transcript.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
