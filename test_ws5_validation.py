"""Tests for WS5 food-card row validation."""

from __future__ import annotations

import unittest

from ws5_validation import (
    expected_row_counts,
    parse_threshold_expression,
    validate_ws5_row,
)


class TestWS5Validation(unittest.TestCase):
    def test_parse_threshold(self):
        p = parse_threshold_expression("şeker ≤ 10")
        self.assertIsNotNone(p)
        assert p is not None
        self.assertEqual(p["feature"], "sugar_g")
        self.assertEqual(p["operator"], "<=")
        self.assertEqual(p["value"], 10.0)

    def test_inclusive_full_credit(self):
        exp = expected_row_counts(parse_threshold_expression("şeker ≤ 12"))
        self.assertEqual(exp["dataset_size"], 11)
        self.assertEqual(exp["correct"], 9)
        self.assertEqual(exp["errors"], 2)
        row = validate_ws5_row("şeker ≤ 12", "9", "2", "0.18")
        self.assertTrue(row["ok"])
        self.assertEqual(row["credit"], "full")

    def test_strict_operator_full_if_complement_counts_match(self):
        row = validate_ws5_row("şeker < 11", "8", "3", "0.27")
        self.assertTrue(row["ok"])
        self.assertEqual(row["credit"], "full")
        self.assertEqual(row["parsed"]["expected_complement"], ">=")

    def test_wrong_mcr_zero(self):
        row = validate_ws5_row("şeker ≤ 12", "9", "2", "0.25")
        self.assertEqual(row["credit"], "zero")
        self.assertEqual(row["reason"], "arithmetic_inconsistent")

    def test_wrong_counts_partial_when_arithmetic_ok(self):
        row = validate_ws5_row("şeker ≤ 12", "10", "1", "0.09")
        self.assertEqual(row["credit"], "partial")
        self.assertEqual(row["reason"], "wrong_counts_with_valid_feature_and_arithmetic")
        self.assertEqual(row["score"], 0.5)
        self.assertTrue(row.get("review"))

    def test_extraction_keys_match_scoring_items(self):
        from pipeline_schema import load_rubric
        from ws5_validation import validate_ws5_extraction

        rubric = load_rubric("WS5")
        responses = {
            "WS5_B1": "şeker ≤ 12",
            "WS5_B2": "9",
            "WS5_B3": "2",
            "WS5_B4": "0.18",
        }
        out = validate_ws5_extraction(responses, rubric)
        self.assertIn("WS5_row1", out["deterministic_checks"])
        self.assertNotIn("row_1", out["deterministic_checks"])

    def test_b25_minimum_with_tie_flag(self):
        from pipeline_schema import load_rubric
        from ws5_validation import validate_ws5_b25

        rubric = load_rubric("WS5")
        responses = {
            "WS5_B1": "şeker ≤ 5", "WS5_B2": "8", "WS5_B3": "3", "WS5_B4": "0.27",
            "WS5_B5": "yağ ≤ 8", "WS5_B6": "8", "WS5_B7": "3", "WS5_B8": "0.27",
            "WS5_B9": "şeker ≤ 10", "WS5_B10": "8", "WS5_B11": "3", "WS5_B12": "0.27",
            "WS5_B13": "şeker ≤ 12", "WS5_B14": "9", "WS5_B15": "2", "WS5_B16": "0.18",
            "WS5_B17": "şeker ≤ 15", "WS5_B18": "9", "WS5_B19": "2", "WS5_B20": "0.18",
            "WS5_B25": "Şeker ≤ 12'yi tercih ederim.",
        }
        b25 = validate_ws5_b25(responses, rubric)
        self.assertEqual(b25["credit"], "full")
        self.assertTrue(b25["tie_at_minimum"])
        self.assertTrue(b25.get("review"))
        self.assertIn("şeker ≤ 15", b25.get("tie_note", ""))

    def test_b25_not_minimum_partial(self):
        from pipeline_schema import load_rubric
        from ws5_validation import validate_ws5_b25

        rubric = load_rubric("WS5")
        responses = {
            "WS5_B1": "şeker ≤ 5", "WS5_B2": "8", "WS5_B3": "3", "WS5_B4": "0.27",
            "WS5_B13": "şeker ≤ 12", "WS5_B14": "9", "WS5_B15": "2", "WS5_B16": "0.18",
            "WS5_B25": "Şeker ≤ 5",
        }
        b25 = validate_ws5_b25(responses, rubric)
        self.assertEqual(b25["credit"], "partial")
        self.assertEqual(b25["reason"], "not_minimum_misclassification")


if __name__ == "__main__":
    unittest.main()
