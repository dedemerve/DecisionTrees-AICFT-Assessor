"""test_ws10_htr.py — WS10 Phase 2 extraction tests."""

from __future__ import annotations

import unittest

from ws10_table_extractor import extract_ws10_from_layout


class TestWs10Calibration(unittest.TestCase):
    def test_sample_student_unblocked(self):
        r = extract_ws10_from_layout("Sample_Student")
        self.assertEqual(r.status, "success")
        self.assertEqual(r.responses.get("WS10_B8"), "408")
        self.assertEqual(r.responses.get("WS10_B5"), "408")
        self.assertEqual(len(r.rows), 7)


if __name__ == "__main__":
    unittest.main()
