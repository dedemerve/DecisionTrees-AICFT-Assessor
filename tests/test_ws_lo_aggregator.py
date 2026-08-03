"""Tests for src/pipeline/ws_lo_aggregator.py using synthetic fixture data."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from src.pipeline.ws_lo_aggregator import (
    TOP_LEVEL_LOS,
    aggregate_student_ws_lo,
    lo_parent,
    load_ws_mapping,
)


def _write(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


class TestLoParent(unittest.TestCase):
    def test_granular_maps_to_parent(self) -> None:
        self.assertEqual(lo_parent("LO3.1.2"), "LO3.1")
        self.assertEqual(lo_parent("LO3.2.3"), "LO3.2")
        self.assertEqual(lo_parent("LO3.3.1"), "LO3.3")

    def test_unknown_returns_none(self) -> None:
        self.assertIsNone(lo_parent("LO4.1.1"))
        self.assertIsNone(lo_parent("bad"))
        self.assertIsNone(lo_parent("LO3.9"))


class TestAggregateStudentWsLo(unittest.TestCase):
    def setUp(self) -> None:
        import tempfile
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

        # Synthetic mapping: WS1_B1 → LO3.1, WS1_B2 → LO3.2
        mapping_dir = self.tmp / "mappings"
        mapping_dir.mkdir()
        _write(mapping_dir / "WS1_AICFT_mapping.json", {
            "items": {
                "WS1_B1": [{"lo": "LO3.1.2"}],
                "WS1_B2": [{"lo": "LO3.2.2"}],
                "WS1_B3": [{"lo": "LO3.2.2"}],
            }
        })

        # Synthetic scoring for student Alice/WS1
        student_dir = self.tmp / "students" / "Alice" / "WS1"
        student_dir.mkdir(parents=True)
        _write(student_dir / "scoring.json", {
            "stage": "scoring",
            "student_id": "Alice",
            "worksheet": "WS1",
            "items": [
                {"item": "WS1_B1", "score": 1.0, "confidence": 0.9, "review": False},
                {"item": "WS1_B2", "score": 0.0, "confidence": 0.8, "review": False},
                {"item": "WS1_B3", "score": 1.0, "confidence": 0.6, "review": True},
            ],
        })

        # Monkeypatch MAPPINGS_DIR
        import src.pipeline.ws_lo_aggregator as mod
        self._orig_mappings = mod.MAPPINGS_DIR
        self._orig_students = mod.STUDENTS_DIR
        mod.MAPPINGS_DIR = mapping_dir
        mod.STUDENTS_DIR = self.tmp / "students"
        self._mod = mod

    def tearDown(self) -> None:
        self._mod.MAPPINGS_DIR = self._orig_mappings
        self._mod.STUDENTS_DIR = self._orig_students
        self._mod.load_ws_mapping.cache_clear() if hasattr(self._mod.load_ws_mapping, "cache_clear") else None
        self._tmp.cleanup()

    def test_lo31_strong(self) -> None:
        result = aggregate_student_ws_lo("Alice", students_dir=self.tmp / "students")
        lo31 = result["lo_scores"]["LO3.1"]
        self.assertEqual(lo31["score"], 1.0)
        self.assertEqual(lo31["evidence_strength"], "strong")
        self.assertIn("WS1_B1", lo31["contributing_items"])

    def test_lo32_weak_due_to_review(self) -> None:
        result = aggregate_student_ws_lo("Alice", students_dir=self.tmp / "students")
        lo32 = result["lo_scores"]["LO3.2"]
        # WS1_B2 scored 0, WS1_B3 scored 1 but review=True → weak
        self.assertEqual(lo32["score"], 1.0)
        self.assertEqual(lo32["evidence_strength"], "weak")
        self.assertIn("WS1_B3", lo32["review_flags"])

    def test_lo33_absent(self) -> None:
        result = aggregate_student_ws_lo("Alice", students_dir=self.tmp / "students")
        lo33 = result["lo_scores"]["LO3.3"]
        self.assertEqual(lo33["evidence_strength"], "absent")
        self.assertEqual(lo33["contributing_items"], [])

    def test_missing_mapping_skips_gracefully(self) -> None:
        # WS2 has no mapping — should not crash
        ws2_dir = self.tmp / "students" / "Alice" / "WS2"
        ws2_dir.mkdir(parents=True)
        _write(ws2_dir / "scoring.json", {
            "stage": "scoring", "student_id": "Alice", "worksheet": "WS2",
            "items": [{"item": "WS2_B1", "score": 1.0, "confidence": 0.9, "review": False}],
        })
        result = aggregate_student_ws_lo("Alice", students_dir=self.tmp / "students")
        self.assertIn("lo_scores", result)

    def test_unknown_student_returns_empty(self) -> None:
        result = aggregate_student_ws_lo("NoSuch", students_dir=self.tmp / "students")
        for lo in TOP_LEVEL_LOS:
            self.assertEqual(result["lo_scores"][lo]["evidence_strength"], "absent")


if __name__ == "__main__":
    unittest.main()
