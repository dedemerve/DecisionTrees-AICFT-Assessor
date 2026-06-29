#!/usr/bin/env python3
"""Deterministic WS5 row scoring from extraction + validation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_integration import score_ws5_deterministic
from student_bundle import STUDENTS_DIR, artifact_payload, extraction_responses, load_artifact, save_artifact, save_scoring_bundle
from ws_extraction_normalize import normalize_scoring_responses
from worksheet_validation import build_technical_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Score WS5 grid rows deterministically")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS5", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS5 extraction for {args.student_id}", file=sys.stderr)
        return 1

    ext = artifact_payload(extraction)
    responses = normalize_scoring_responses("WS5", extraction_responses(ext))
    validation = build_technical_validation("WS5", extraction)
    val_path = save_artifact(
        args.student_id,
        "WS5",
        "validation",
        {"stage": "validation", "student_id": args.student_id, "worksheet": "WS5", **validation},
        STUDENTS_DIR,
    )

    scoring = score_ws5_deterministic(responses, args.student_id, validation=validation)

    if scoring.get("max_score") is None or scoring["max_score"] < 6:
        scoring["max_score"] = 6.0

    paths = save_scoring_bundle(args.student_id, "WS5", scoring, base_dir=STUDENTS_DIR)
    print(f"Wrote validation {val_path}")
    print(f"Wrote scoring {paths[0]} — total {scoring['total_score']}/{scoring['max_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
