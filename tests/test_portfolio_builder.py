"""Tests for src/pipeline/portfolio_builder.py using synthetic fixture data."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline.portfolio_builder import (
    build_portfolio,
    merge_sources,
    normalise_video_source,
    normalise_ws_source,
    propose_ai_cft_level,
)


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _ws_lo(lo31: str = "strong", lo32: str = "absent", lo33: str = "absent") -> dict:
    def _rec(s: str) -> dict:
        return {"score": 1.0 if s != "absent" else 0.0, "max_score": 2.0, "evidence_strength": s,
                "contributing_items": [], "review_flags": []}
    return {
        "student_id": "Alice",
        "source": "worksheet",
        "lo_scores": {"LO3.1": _rec(lo31), "LO3.2": _rec(lo32), "LO3.3": _rec(lo33)},
    }


class TestNormaliseWsSource(unittest.TestCase):
    def test_strong_lo31(self) -> None:
        ws = _ws_lo(lo31="strong")
        norm = normalise_ws_source(ws)
        self.assertEqual(norm["source"], "worksheet")
        self.assertEqual(norm["LO3.1"]["evidence_strength"], "strong")
        self.assertEqual(norm["LO3.2"]["evidence_strength"], "absent")


class TestNormaliseVideoSource(unittest.TestCase):
    def _session(self, observed_behaviors: list[str], confidences: dict | None = None) -> dict:
        confidences = confidences or {}
        behaviors = {}
        all_ids = ["B0", "B1", "B2", "B3", "B4", "B5", "B6",
                   "B7", "B8", "B9", "B10", "B11", "B12", "B13"]
        for b in all_ids:
            behaviors[b] = {
                "decision": "observed" if b in observed_behaviors else "not_observed",
                "confidence": confidences.get(b, "High"),
                "frame_evidence": [],
            }
        return {"student_id": "Alice", "session_key": "21apr", "behaviors": behaviors}

    def test_b0_triggers_lo31(self) -> None:
        session = self._session(["B0"])
        norm = normalise_video_source([session])
        self.assertEqual(norm["LO3.1"]["evidence_strength"], "strong")
        self.assertEqual(norm["LO3.2"]["evidence_strength"], "absent")

    def test_medium_confidence_gives_weak(self) -> None:
        session = self._session(["B0"], {"B0": "Medium"})
        norm = normalise_video_source([session])
        self.assertEqual(norm["LO3.1"]["evidence_strength"], "weak")

    def test_no_behaviors_all_absent(self) -> None:
        session = self._session([])
        norm = normalise_video_source([session])
        for lo in ("LO3.1", "LO3.2", "LO3.3"):
            self.assertEqual(norm[lo]["evidence_strength"], "absent")


class TestMergeSources(unittest.TestCase):
    def test_max_score_wins(self) -> None:
        ws = normalise_ws_source(_ws_lo(lo31="weak"))
        vid = {"source": "video", "LO3.1": {"score": 1, "max_score": 1, "evidence_strength": "strong"},
               "LO3.2": {"score": 0, "max_score": 1, "evidence_strength": "absent"},
               "LO3.3": {"score": 0, "max_score": 1, "evidence_strength": "absent"}}
        merged = merge_sources([ws, vid])
        self.assertEqual(merged["LO3.1"]["evidence_strength"], "strong")
        self.assertEqual(merged["LO3.1"]["primary_source"], "video")

    def test_absent_stays_absent(self) -> None:
        ws = normalise_ws_source(_ws_lo(lo31="absent"))
        merged = merge_sources([ws])
        self.assertEqual(merged["LO3.1"]["evidence_strength"], "absent")


class TestProposeLevel(unittest.TestCase):
    def _profiles(self, lo31: str, lo32: str, lo33: str) -> dict:
        return {lo: {"evidence_strength": s} for lo, s in
                [("LO3.1", lo31), ("LO3.2", lo32), ("LO3.3", lo33)]}

    def test_create(self) -> None:
        self.assertEqual(propose_ai_cft_level(self._profiles("strong", "strong", "strong")), "Create")

    def test_deepen(self) -> None:
        self.assertEqual(propose_ai_cft_level(self._profiles("strong", "strong", "absent")), "Deepen")

    def test_acquire(self) -> None:
        self.assertEqual(propose_ai_cft_level(self._profiles("strong", "absent", "absent")), "Acquire")

    def test_acquire_provisional(self) -> None:
        self.assertEqual(propose_ai_cft_level(self._profiles("weak", "absent", "absent")), "Acquire (provisional)")

    def test_insufficient(self) -> None:
        self.assertEqual(propose_ai_cft_level(self._profiles("absent", "absent", "absent")), "Insufficient evidence")


class TestBuildPortfolio(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_missing_all_sources_still_builds(self) -> None:
        portfolio = build_portfolio(
            "NoData",
            ws_lo_dir=self.tmp / "ws_lo",
            mmla_dir=self.tmp / "mmla",
        )
        self.assertEqual(portfolio["student_id"], "NoData")
        self.assertFalse(portfolio["is_final"])
        self.assertIn("video", portfolio["missing_sources"])
        self.assertIn("worksheet", portfolio["missing_sources"])

    def test_ws_only_portfolio(self) -> None:
        ws_lo_dir = self.tmp / "ws_lo"
        _write(ws_lo_dir / "Alice_ws_lo.json", _ws_lo(lo31="strong", lo32="strong"))
        portfolio = build_portfolio(
            "Alice",
            ws_lo_dir=ws_lo_dir,
            mmla_dir=self.tmp / "mmla",
        )
        self.assertTrue(portfolio["modality_coverage"]["worksheet"])
        self.assertFalse(portfolio["modality_coverage"]["video"])
        self.assertEqual(portfolio["ai_cft_proposal"], "Deepen")

    def test_researcher_decision_is_null(self) -> None:
        portfolio = build_portfolio(
            "Alice",
            ws_lo_dir=self.tmp / "ws_lo",
            mmla_dir=self.tmp / "mmla",
        )
        self.assertIsNone(portfolio["researcher_decision"]["final_level"])


if __name__ == "__main__":
    unittest.main()
