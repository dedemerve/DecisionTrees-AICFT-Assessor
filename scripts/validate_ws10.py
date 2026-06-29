#!/usr/bin/env python3
"""Run WS10 deterministic validation (optional artifact; Group A worksheet)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from student_bundle import STUDENTS_DIR, artifact_payload, extraction_responses, load_artifact, save_artifact
from ws10_validation import validate_ws10_extraction


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WS10 responses against fixed reference")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS10", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS10 extraction for {args.student_id}", file=sys.stderr)
        return 1

    responses = extraction_responses(artifact_payload(extraction))
    validation = validate_ws10_extraction(responses)
    path = save_artifact(
        args.student_id,
        "WS10",
        "validation",
        {
            "stage": "validation",
            "student_id": args.student_id,
            "worksheet": "WS10",
            **validation,
        },
        STUDENTS_DIR,
    )
    print(f"Wrote {path} — all_correct={validation.get('all_correct')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
