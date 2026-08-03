#!/usr/bin/env python3
"""
run_portfolio.py — CLI entry point for the AI-CFT portfolio pipeline.

Usage:
  python src/pipeline/run_portfolio.py --student Amy
  python src/pipeline/run_portfolio.py --all
  python src/pipeline/run_portfolio.py --cohort
  python src/pipeline/run_portfolio.py --all --cohort
  python src/pipeline/run_portfolio.py --all --cohort --include-pending
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Ensure repo root is on sys.path when invoked directly.
_REPO_ROOT = Path(__file__).parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline.ws_lo_aggregator import run_all as ws_lo_run_all
from src.pipeline.ws_lo_aggregator import run_student as ws_lo_run_student
from src.pipeline.portfolio_builder import build_and_save_portfolio
from src.pipeline.cohort_report import run as cohort_run

STUDENTS_DIR = _REPO_ROOT / "students"
MMLA_DIR = _REPO_ROOT / "logs" / "pipeline_runs"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _student_ids_with_data() -> list[str]:
    """Return IDs of students with any scoring.json or MMLA final_scored.json."""
    ids: set[str] = set()
    if STUDENTS_DIR.is_dir():
        for d in STUDENTS_DIR.iterdir():
            if d.is_dir() and any(d.glob("*/scoring.json")):
                ids.add(d.name)
    if MMLA_DIR.is_dir():
        for f in MMLA_DIR.glob("*_final_scored.json"):
            parts = f.stem.split("_")
            if parts:
                ids.add(parts[0])
    return sorted(ids)


def run_student_pipeline(student_id: str) -> dict[str, Any]:
    """Run Task A + B for a single student. Returns the portfolio dict."""
    import typing
    if typing.TYPE_CHECKING:
        from typing import Any

    log.info("Running ws_lo_aggregator for %s …", student_id)
    ws_path = ws_lo_run_student(student_id)
    log.info("  → %s", ws_path)

    log.info("Running portfolio_builder for %s …", student_id)
    portfolio, pf_path = build_and_save_portfolio(student_id)
    log.info("  → %s", pf_path)
    return portfolio


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AI-CFT portfolio pipeline CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--student", metavar="ID", help="Process one student")
    group.add_argument("--all", action="store_true", help="Process all students")
    parser.add_argument(
        "--cohort", action="store_true",
        help="Run cohort aggregation after portfolios are built",
    )
    parser.add_argument(
        "--include-pending", action="store_true",
        help="Include unfinalized portfolios in cohort report",
    )
    args = parser.parse_args(argv)

    if not args.student and not args.all and not args.cohort:
        parser.print_help()
        return 1

    portfolios_written = 0
    total_flags = 0

    # Task A + B
    if args.student:
        portfolio = run_student_pipeline(args.student)
        portfolios_written = 1
        total_flags = len(portfolio.get("review_flags", []))
        print(json.dumps(portfolio, indent=2, ensure_ascii=False))

    elif args.all:
        student_ids = _student_ids_with_data()
        if not student_ids:
            log.warning("No students with data found in %s or %s", STUDENTS_DIR, MMLA_DIR)
        for sid in student_ids:
            try:
                portfolio = run_student_pipeline(sid)
                portfolios_written += 1
                total_flags += len(portfolio.get("review_flags", []))
            except Exception as exc:
                log.error("Failed for %s: %s", sid, exc)

    # Task C
    if args.cohort:
        log.info("Running cohort report …")
        try:
            json_path, csv_path = cohort_run(include_pending=args.include_pending)
            log.info("Cohort JSON → %s", json_path)
            log.info("Cohort CSV  → %s", csv_path)
        except Exception as exc:
            log.error("Cohort report failed: %s", exc)
            return 1

    print(
        f"\nPortfolio pipeline complete. "
        f"{portfolios_written} portfolio(s) written. "
        f"{total_flags} flag(s) raised."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
