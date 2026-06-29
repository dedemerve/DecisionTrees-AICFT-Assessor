#!/usr/bin/env python3
"""Deterministic WS7 scoring from extraction + WS6 cross-reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_integration import score_ws7_deterministic
from student_bundle import STUDENTS_DIR, artifact_payload, extraction_responses, load_artifact, save_artifact, save_scoring_bundle
from worksheet_validation import build_technical_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Score WS7 deterministically")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS7", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS7 extraction for {args.student_id}", file=sys.stderr)
        return 1

    ext = artifact_payload(extraction)
    responses = extraction_responses(ext)
    validation = build_technical_validation("WS7", extraction, student_id=args.student_id)
    save_artifact(
        args.student_id,
        "WS7",
        "validation",
        {"stage": "validation", "student_id": args.student_id, "worksheet": "WS7", **validation},
        STUDENTS_DIR,
    )

    scoring = score_ws7_deterministic(responses, args.student_id, validation=validation)
    paths = save_scoring_bundle(args.student_id, "WS7", scoring, base_dir=STUDENTS_DIR)
    print(f"Wrote scoring {paths[0]} — total {scoring['total_score']}/{scoring['max_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
