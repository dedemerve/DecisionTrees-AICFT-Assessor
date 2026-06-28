#!/usr/bin/env python3
"""
calibrate_scoring.py — apply rule-based confidence calibration to scoring files.

Usage:
  python calibrate_scoring.py Sample_Student
  python calibrate_scoring.py Sample_Student --export-human-ref
  python calibrate_scoring.py Sample_Student --report
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from confidence_calibration import (
    HUMAN_CODING_PATH,
    build_human_reference_from_scoring,
    calibrate_student_scoring,
    calibration_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate scoring confidence values")
    parser.add_argument("student_id", help="e.g. Sample_Student")
    parser.add_argument("--export-human-ref", action="store_true",
                        help="Export human coding anchor from current scores")
    parser.add_argument("--report", action="store_true",
                        help="Print calibration report after applying")
    args = parser.parse_args()

    base = Path(__file__).parent
    bundle_file = base / "students" / f"{args.student_id}.json"

    if not bundle_file.exists():
        print(f"Student bundle not found: {bundle_file}", file=sys.stderr)
        return 1

    if args.export_human_ref:
        ref = build_human_reference_from_scoring(args.student_id)
        HUMAN_CODING_PATH.parent.mkdir(exist_ok=True)
        HUMAN_CODING_PATH.write_text(
            json.dumps(ref, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Exported {ref['item_count']} items to {HUMAN_CODING_PATH}")

    updated = calibrate_student_scoring(args.student_id)
    print(f"Calibrated bundle for {args.student_id}: {updated[0] if updated else bundle_file}")

    if args.report:
        report = calibration_report(args.student_id)
        print(json.dumps(report, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
