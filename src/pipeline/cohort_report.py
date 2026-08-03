"""
cohort_report.py — Aggregate all portfolio JSONs into cohort-level summary.

Reads outputs/portfolios/*_portfolio.json.
Writes outputs/reports/cohort_report.json and cohort_report.csv.

By default includes only portfolios where researcher_decision.final_level
is not null. Pass include_pending=True to include all portfolios.
"""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
PORTFOLIO_DIR = REPO_ROOT / "outputs" / "portfolios"
REPORTS_DIR = REPO_ROOT / "outputs" / "reports"

TOP_LEVEL_LOS = ("LO3.1", "LO3.2", "LO3.3")

KNOWN_LEVELS = (
    "Acquire",
    "Deepen",
    "Create",
    "Acquire (provisional)",
    "Insufficient evidence",
)


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def load_portfolios(
    portfolio_dir: Path | None = None,
    *,
    include_pending: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Load portfolio files. Returns (included, excluded_pending)."""
    pdir = portfolio_dir or PORTFOLIO_DIR
    included: list[dict[str, Any]] = []
    pending: list[dict[str, Any]] = []

    if not pdir.is_dir():
        log.warning("Portfolio dir not found: %s", pdir)
        return [], []

    for path in sorted(pdir.glob("*_portfolio.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        final_level = data.get("researcher_decision", {}).get("final_level")
        if final_level is not None or include_pending:
            included.append(data)
        else:
            pending.append(data)

    return included, pending


def build_cohort_report(
    portfolios: list[dict[str, Any]],
    n_pending: int = 0,
) -> dict[str, Any]:
    """Build the cohort_report.json structure from a list of portfolio dicts."""
    n_students = len(portfolios) + n_pending
    n_finalized = sum(
        1 for p in portfolios
        if p.get("researcher_decision", {}).get("final_level") is not None
    )

    lo_distribution: dict[str, dict[str, int]] = {
        lo: {"strong": 0, "weak": 0, "absent": 0, "missing": 0}
        for lo in TOP_LEVEL_LOS
    }
    level_distribution: dict[str, int] = {lvl: 0 for lvl in KNOWN_LEVELS}
    level_distribution["pending_review"] = n_pending
    flags_summary: dict[str, int] = {}

    for portfolio in portfolios:
        lo_profiles = portfolio.get("lo_profiles", {})
        for lo in TOP_LEVEL_LOS:
            lo_rec = lo_profiles.get(lo, {})
            strength = lo_rec.get("evidence_strength", "missing")
            if strength not in lo_distribution[lo]:
                strength = "missing"
            lo_distribution[lo][strength] += 1

        # Use final_level if set, else proposal.
        researcher = portfolio.get("researcher_decision", {})
        final_level = researcher.get("final_level")
        level = final_level or portfolio.get("ai_cft_proposal", "Insufficient evidence")
        if level in level_distribution:
            level_distribution[level] += 1
        else:
            level_distribution.setdefault(level, 0)
            level_distribution[level] += 1

        for flag_rec in portfolio.get("review_flags", []):
            flag_key = flag_rec.get("flag", "unknown")
            flags_summary[flag_key] = flags_summary.get(flag_key, 0) + 1

    return {
        "generated_at": _now_iso(),
        "n_students": n_students,
        "n_finalized": n_finalized,
        "lo_distribution": lo_distribution,
        "level_distribution": level_distribution,
        "flags_summary": flags_summary,
    }


def build_cohort_csv_rows(portfolios: list[dict[str, Any]]) -> list[dict[str, str]]:
    """Build per-student rows for cohort_report.csv."""
    rows: list[dict[str, str]] = []
    for portfolio in portfolios:
        sid = portfolio.get("student_id", "")
        lo_profiles = portfolio.get("lo_profiles", {})
        researcher = portfolio.get("researcher_decision", {})

        missing_sources = portfolio.get("missing_sources", [])
        flag_count = len(portfolio.get("review_flags", []))

        rows.append({
            "student_id": sid,
            "LO3.1_strength": lo_profiles.get("LO3.1", {}).get("evidence_strength", "missing"),
            "LO3.2_strength": lo_profiles.get("LO3.2", {}).get("evidence_strength", "missing"),
            "LO3.3_strength": lo_profiles.get("LO3.3", {}).get("evidence_strength", "missing"),
            "ai_cft_proposal": portfolio.get("ai_cft_proposal", ""),
            "final_level": researcher.get("final_level") or "",
            "missing_sources": "|".join(missing_sources),
            "flag_count": str(flag_count),
        })
    return rows


def write_cohort_report(
    report: dict[str, Any],
    csv_rows: list[dict[str, str]],
    *,
    reports_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Write JSON and CSV reports. Returns (json_path, csv_path)."""
    out_dir = reports_dir or REPORTS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "cohort_report.json"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    csv_path = out_dir / "cohort_report.csv"
    fieldnames = [
        "student_id",
        "LO3.1_strength",
        "LO3.2_strength",
        "LO3.3_strength",
        "ai_cft_proposal",
        "final_level",
        "missing_sources",
        "flag_count",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)

    return json_path, csv_path


def run(
    *,
    portfolio_dir: Path | None = None,
    reports_dir: Path | None = None,
    include_pending: bool = False,
) -> tuple[Path, Path]:
    """Run cohort aggregation end-to-end. Returns (json_path, csv_path)."""
    portfolios, pending = load_portfolios(
        portfolio_dir, include_pending=include_pending
    )
    all_portfolios = portfolios + (pending if include_pending else [])

    if not all_portfolios:
        log.warning("No portfolios found — report will be empty")

    report = build_cohort_report(all_portfolios, n_pending=len(pending))
    csv_rows = build_cohort_csv_rows(all_portfolios)
    return write_cohort_report(report, csv_rows, reports_dir=reports_dir)
