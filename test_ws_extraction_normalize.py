"""Tests for post-OCR normalization (WS5/WS6 extraction bridge)."""

from __future__ import annotations

import unittest

from ws_extraction_normalize import (
    fix_operator_artifacts,
    is_ws5_threshold_field,
    normalize_scoring_responses,
    normalization_diff,
)


class TestWsExtractionNormalize(unittest.TestCase):
    def test_ws5_threshold_field_pattern(self):
        self.assertTrue(is_ws5_threshold_field("WS5_B1"))
        self.assertTrue(is_ws5_threshold_field("WS5_B25"))
        self.assertFalse(is_ws5_threshold_field("WS5_B2"))

    def test_fix_operator_artifacts(self):
        self.assertEqual(fix_operator_artifacts("  şeker =< 10 "), "şeker <= 10")

    def test_normalize_ws5_threshold_only(self):
        raw = {"WS5_B1": "şeker =< 10", "WS5_B2": " 9 "}
        out = normalize_scoring_responses("WS5", raw)
        self.assertEqual(out["WS5_B1"], "şeker <= 10")
        self.assertEqual(out["WS5_B2"], "9")

    def test_normalization_diff(self):
        raw = {"WS6_B2": "=< 10"}
        diff = normalization_diff("WS6", raw)
        self.assertEqual(len(diff), 1)
        self.assertEqual(diff[0]["field"], "WS6_B2")


if __name__ == "__main__":
    unittest.main()
