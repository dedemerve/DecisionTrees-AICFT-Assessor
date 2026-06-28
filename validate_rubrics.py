#!/usr/bin/env python3
"""
validate_rubrics.py — enforce Rubric Schema 3.0 invariants.

Run: python validate_rubrics.py
Exit 0 if all rubrics pass; exit 1 with error list otherwise.
"""

from __future__ import annotations

import sys

from pipeline_schema import RUBRICS_DIR, validate_all_rubrics


def main() -> int:
    rubric_files = sorted(RUBRICS_DIR.glob("*_rubric.json"))
    if not rubric_files:
        print("No rubric files found.", file=sys.stderr)
        return 1

    errors = validate_all_rubrics()
    if errors:
        print(f"Rubric validation failed ({len(errors)} issues):\n", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"All {len(rubric_files)} rubrics pass Schema 3.0 validation.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
