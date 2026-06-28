#!/usr/bin/env python3
"""
run_research_dashboard.py — Print researcher-facing portfolio report.

Usage:
  python run_research_dashboard.py Sample_Student
  python run_research_dashboard.py Sample_Student -o reports/Sample_Student.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from portfolio_builder import build_and_save_portfolio
from research_dashboard import render_portfolio_report
from student_bundle import student_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Research dashboard — portfolio summary report")
    parser.add_argument("student_id", help="e.g. Sample_Student")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Write markdown report to this path (default: stdout)",
    )
    parser.add_argument(
        "--rebuild-portfolio",
        action="store_true",
        help="Rebuild portfolio.json before rendering",
    )
    args = parser.parse_args()

    if not student_dir(args.student_id).is_dir():
        print(f"Student not found: {args.student_id}", file=sys.stderr)
        return 1

    if args.rebuild_portfolio:
        build_and_save_portfolio(args.student_id)

    report = render_portfolio_report(args.student_id)

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"Report written → {args.output}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
