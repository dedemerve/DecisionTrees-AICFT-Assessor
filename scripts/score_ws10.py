#!/usr/bin/env python3
"""Deterministic WS10 scoring from extraction."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_integration import score_ws10_deterministic
from student_bundle import STUDENTS_DIR, artifact_payload, extraction_responses, load_artifact, save_scoring_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Score WS10 deterministically")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS10", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS10 extraction for {args.student_id}", file=sys.stderr)
        return 1

    responses = extraction_responses(artifact_payload(extraction))
    scoring = score_ws10_deterministic(responses, args.student_id)
    paths = save_scoring_bundle(args.student_id, "WS10", scoring, base_dir=STUDENTS_DIR)
    print(f"Wrote scoring {paths[0]} — total {scoring['total_score']}/{scoring['max_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
