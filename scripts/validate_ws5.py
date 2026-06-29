#!/usr/bin/env python3
"""Build WS5 validation.json from extraction + food-card reference data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from student_bundle import STUDENTS_DIR, load_artifact, save_artifact
from worksheet_validation import build_technical_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate WS5 extraction against food cards")
    parser.add_argument("student_id", nargs="?", default="Sample_Student")
    args = parser.parse_args()

    extraction = load_artifact(args.student_id, "WS5", "extraction", STUDENTS_DIR)
    if not extraction:
        print(f"No WS5 extraction for {args.student_id}", file=sys.stderr)
        return 1

    payload = build_technical_validation("WS5", extraction)
    out = {
        "stage": "validation",
        "student_id": args.student_id,
        "worksheet": "WS5",
        **payload,
    }
    path = save_artifact(args.student_id, "WS5", "validation", out, STUDENTS_DIR)
    checks = payload.get("deterministic_checks", {})
    ok_rows = sum(1 for c in checks.values() if c.get("credit") == "full")
    partial = sum(1 for c in checks.values() if c.get("credit") == "partial")
    print(f"Wrote {path} ({ok_rows} full, {partial} partial, {len(checks)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
