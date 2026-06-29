#!/usr/bin/env python3
"""Build WS7 validation.json from extraction + WS6 cross-reference."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from pipeline_schema import load_rubric
from student_bundle import STUDENTS_DIR, load_artifact, save_artifact
from worksheet_validation import build_technical_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WS7 extraction (P1 + WS6 rules)")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS7", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS7 extraction for {args.student_id}", file=sys.stderr)
        return 1

    payload = build_technical_validation("WS7", extraction, student_id=args.student_id)
    path = save_artifact(
        args.student_id,
        "WS7",
        "validation",
        {
            "stage": "validation",
            "student_id": args.student_id,
            "worksheet": "WS7",
            **payload,
        },
        STUDENTS_DIR,
    )
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
