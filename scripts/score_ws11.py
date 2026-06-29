#!/usr/bin/env python3
"""Deterministic WS11 scoring for Q10–Q12 (true/false, ordering, multiselect)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_integration import score_ws11_deterministic
from student_bundle import STUDENTS_DIR, artifact_payload, extraction_responses, load_artifact, save_scoring_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Score WS11 deterministic items (Q10–Q12)")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    parser.add_argument(
        "--merge-interpretive",
        action="store_true",
        help="Include B8a–B9 interpretive scores from existing scoring.json when present",
    )
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS11", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS11 extraction for {args.student_id}", file=sys.stderr)
        return 1

    responses = extraction_responses(artifact_payload(extraction))
    existing = load_artifact(args.student_id, "WS11", "scoring", STUDENTS_DIR) if args.merge_interpretive else None
    interpretive = None
    if existing:
        interpretive = {
            r["item"]: r
            for r in artifact_payload(existing).get("items", [])
            if r["item"] in {"WS11_B8a", "WS11_B8b", "WS11_B9"}
        }

    scoring = score_ws11_deterministic(responses, args.student_id, interpretive_items=interpretive)
    paths = save_scoring_bundle(args.student_id, "WS11", scoring, base_dir=STUDENTS_DIR)
    print(f"Wrote scoring {paths[0]} — total {scoring['total_score']}/{scoring['max_score']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
