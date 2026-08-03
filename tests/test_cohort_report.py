"""Tests for src/pipeline/cohort_report.py using synthetic fixture data."""

from __future__ import annotations

import csv
import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline.cohort_report import (
    build_cohort_csv_rows,
    build_cohort_report,
    load_portfolios,
    write_cohort_report,
)


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _portfolio(
    student_id: str,
    lo31: str = "strong",
    lo32: str = "absent",
    lo33: str = "absent",
    proposal: str = "Acquire",
    final_level: str | None = None,
    flags: list | None = None,
    missing: list | None = None,
) -> dict:
    def _rec(s: str) -> dict:
        return {"merged_score": 1 if s != "absent" else 0, "merged_max": 1,
                "evidence_strength": s, "primary_source": "worksheet",
                "source_detail": {"worksheet": {"score": 1, "strength": s}}}
    return {
        "student_id": student_id,
        "generated_at": "2026-08-01T00:00:00+00:00",
        "is_final": final_level is not None,
        "missing_sources": missing or [],
        "modality_coverage": {"worksheet": True, "video": False, "colab": False},
        "lo_profiles": {
            "LO3.1": _rec(lo31),
            "LO3.2": _rec(lo32),
            "LO3.3": _rec(lo33),
        },
        "ai_cft_proposal": proposal,
        "review_flags": flags or [],
        "researcher_decision": {
            "final_level": final_level,
            "override_reason": None,
            "reviewed_by": None,
            "reviewed_at": None,
        },
    }


class TestLoadPortfolios(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_finalized_included_by_default(self) -> None:
        pdir = self.tmp / "portfolios"
        _write(pdir / "Amy_portfolio.json", _portfolio("Amy", final_level="Deepen"))
        _write(pdir / "Bruno_portfolio.json", _portfolio("Bruno"))
        included, pending = load_portfolios(pdir)
        self.assertEqual(len(included), 1)
        self.assertEqual(len(pending), 1)

    def test_include_pending_includes_all(self) -> None:
        pdir = self.tmp / "portfolios"
        _write(pdir / "Amy_portfolio.json", _portfolio("Amy"))
        _write(pdir / "Bruno_portfolio.json", _portfolio("Bruno"))
        included, pending = load_portfolios(pdir, include_pending=True)
        self.assertEqual(len(included), 2)
        self.assertEqual(len(pending), 0)

    def test_missing_dir_returns_empty(self) -> None:
        included, pending = load_portfolios(self.tmp / "nonexistent")
        self.assertEqual(included, [])


class TestBuildCohortReport(unittest.TestCase):
    def test_level_distribution(self) -> None:
        portfolios = [
            _portfolio("Amy", lo31="strong", lo32="strong", proposal="Deepen"),
            _portfolio("Bruno", lo31="strong", lo32="absent", proposal="Acquire"),
        ]
        report = build_cohort_report(portfolios, n_pending=1)
        self.assertEqual(report["n_students"], 3)
        self.assertEqual(report["level_distribution"]["Deepen"], 1)
        self.assertEqual(report["level_distribution"]["Acquire"], 1)
        self.assertEqual(report["level_distribution"]["pending_review"], 1)

    def test_lo_distribution(self) -> None:
        portfolios = [_portfolio("Amy", lo31="strong", lo32="weak")]
        report = build_cohort_report(portfolios)
        self.assertEqual(report["lo_distribution"]["LO3.1"]["strong"], 1)
        self.assertEqual(report["lo_distribution"]["LO3.2"]["weak"], 1)

    def test_flags_summary(self) -> None:
        flags = [{"flag": "no_video_data", "severity": "high"}]
        portfolios = [_portfolio("Amy", flags=flags)]
        report = build_cohort_report(portfolios)
        self.assertEqual(report["flags_summary"]["no_video_data"], 1)


class TestWriteCohortReport(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_writes_json_and_csv(self) -> None:
        portfolios = [_portfolio("Amy", lo31="strong", proposal="Acquire")]
        report = build_cohort_report(portfolios)
        rows = build_cohort_csv_rows(portfolios)
        json_path, csv_path = write_cohort_report(report, rows, reports_dir=self.tmp)
        self.assertTrue(json_path.exists())
        self.assertTrue(csv_path.exists())
        with csv_path.open(encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            data = list(reader)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["student_id"], "Amy")
        self.assertEqual(data[0]["LO3.1_strength"], "strong")


if __name__ == "__main__":
    unittest.main()
