#!/usr/bin/env python3
"""Build WS6 validation.json from extraction + food-card tree checks."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from student_bundle import STUDENTS_DIR, load_artifact, save_artifact
from worksheet_validation import build_technical_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WS6 extraction against food cards")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS6", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS6 extraction for {args.student_id}", file=sys.stderr)
        return 1

    payload = build_technical_validation("WS6", extraction)
    path = save_artifact(
        args.student_id,
        "WS6",
        "validation",
        {
            "stage": "validation",
            "student_id": args.student_id,
            "worksheet": "WS6",
            **payload,
        },
        STUDENTS_DIR,
    )
    checks = payload.get("deterministic_checks", {})
    full = sum(1 for k, v in checks.items() if isinstance(v, dict) and v.get("credit") == "full")
    print(f"Wrote {path} ({full}/{len(checks)} items full)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
