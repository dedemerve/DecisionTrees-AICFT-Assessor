"""test_ws10_htr.py — WS10 Phase 2 extraction tests."""

from __future__ import annotations

import json
import unittest

from pipeline_schema import layout_manifest_path
from ws10_table_extractor import (
    CALIBRATION_WS10,
    Ws10ExtractionResult,
    _extract_from_calibration,
    extract_ws10_from_layout,
)


def _extract_sample_student_ws10() -> Ws10ExtractionResult:
    """Use layout manifest when present; otherwise calibration fixture (CI-safe)."""
    if layout_manifest_path("Sample_Student", "WS10").exists():
        return extract_ws10_from_layout("Sample_Student")
    if CALIBRATION_WS10.exists():
        cal = json.loads(CALIBRATION_WS10.read_text(encoding="utf-8"))
        return _extract_from_calibration("Sample_Student", cal)
    return Ws10ExtractionResult(
        student_id="Sample_Student",
        status="error",
        message="No WS10 layout manifest or calibration fixture available.",
    )


class TestWs10Calibration(unittest.TestCase):
    def test_sample_student_unblocked(self):
        if not layout_manifest_path("Sample_Student", "WS10").exists() and not CALIBRATION_WS10.exists():
            self.skipTest("WS10 layout/calibration fixtures not available")
        r = _extract_sample_student_ws10()
        self.assertEqual(r.status, "success", r.message)
        self.assertEqual(r.responses.get("WS10_B8"), "408")
        self.assertEqual(r.responses.get("WS10_B5"), "408")
        self.assertEqual(len(r.rows), 7)


if __name__ == "__main__":
    unittest.main()
