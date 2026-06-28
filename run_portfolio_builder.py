#!/usr/bin/env python3
"""
run_portfolio_builder.py — Build AI-CFT portfolio from worksheet evidence artifacts.

Usage:
  python run_portfolio_builder.py Sample_Student
  python run_portfolio_builder.py Sample_Student --json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from portfolio_builder import build_and_save_portfolio
from student_bundle import student_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Build portfolio.json from evidence artifacts")
    parser.add_argument("student_id", help="e.g. Sample_Student")
    parser.add_argument("--json", action="store_true", help="Print portfolio JSON to stdout")
    args = parser.parse_args()

    root = student_dir(args.student_id)
    if not root.is_dir():
        print(f"Student not found: {root}", file=sys.stderr)
        return 1

    portfolio = build_and_save_portfolio(args.student_id)
    path = root / "portfolio.json"
    print(f"Portfolio written → {path}")
    print(f"  Worksheets scored: {len(portfolio['worksheets_scored'])}")
    print(f"  Proposed Aspect 3 level: {portfolio['ai_cft_proposal']['Aspect3']}")
    print(f"  Data gaps: {len(portfolio['data_gaps'])} worksheet(s)")

    if args.json:
        print(json.dumps(portfolio, indent=2, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
