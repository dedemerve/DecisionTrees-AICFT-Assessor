"""Tests for WS6 two-level tree validation on food cards."""

from __future__ import annotations

import unittest

from ws6_validation import (
    build_ws6_tree,
    compute_tree_mcr,
    validate_tree_structure,
    validate_ws6_extraction,
)


SAMPLE_RESPONSES = {
    "WS6_B1": "şeker",
    "WS6_B2": "≤ 10",
    "WS6_B3": "evet (≤ 10)",
    "WS6_B4": "hayır (> 10)",
    "WS6_B5": "Tavsiye edilir",
    "WS6_B6": "yağ",
    "WS6_B7": "≤ 5",
    "WS6_B8": "evet (≤ 5)",
    "WS6_B9": "hayır (> 5)",
    "WS6_B10": "Tavsiye edilir",
    "WS6_B11": "Tavsiye edilmez",
    "WS6_B12": "",
    "WS6_B13": "Tavsiye edilmez",
}


class TestWS6Validation(unittest.TestCase):
    def test_two_level_tree_parsed(self):
        tree = build_ws6_tree(SAMPLE_RESPONSES)
        self.assertTrue(tree["has_inner"])
        self.assertEqual(tree["root_threshold"]["value"], 10.0)

    def test_mcr_computed(self):
        tree = build_ws6_tree(SAMPLE_RESPONSES)
        stats = compute_tree_mcr(tree)
        self.assertEqual(stats["dataset_size"], 11)

    def test_full_validation_not_blocked(self):
        from pipeline_schema import load_rubric

        out = validate_ws6_extraction(SAMPLE_RESPONSES, load_rubric("WS6"))
        self.assertFalse(out["blocked"])
        self.assertTrue(out["deterministic_checks"]["WS6_root_feature"]["ok"])
        self.assertEqual(
            out["deterministic_checks"]["WS6_root_threshold"]["credit"],
            "full",
        )

    def test_mcr_zero_two_level_still_valid(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS6")
        tree = build_ws6_tree(SAMPLE_RESPONSES)
        mcr = compute_tree_mcr(tree)
        hol = validate_tree_structure(SAMPLE_RESPONSES, tree, mcr)
        self.assertIn("mcr_zero_valid", hol)
        self.assertTrue(hol["two_level_ok"])

    def test_strict_threshold_with_wrong_complement(self):
        from ws6_validation import validate_threshold_field

        row = validate_threshold_field("< 10", "şeker", false_label="hayır (> 10)")
        self.assertEqual(row["credit"], "partial")
        self.assertEqual(row["operator_issue"], "complementary_operator_mismatch")

    def test_complement_pair_valid_sample(self):
        from ws6_validation import validate_threshold_field

        row = validate_threshold_field("≤ 10", "şeker", false_label="hayır (> 10)")
        self.assertEqual(row["credit"], "full")

    def test_complement_mismatch_ws6(self):
        from pipeline_schema import load_rubric

        responses = dict(SAMPLE_RESPONSES)
        responses["WS6_B2"] = "< 10"
        responses["WS6_B4"] = "hayır (> 10)"
        out = validate_ws6_extraction(responses, load_rubric("WS6"))
        self.assertEqual(
            out["deterministic_checks"]["WS6_root_threshold"]["credit"],
            "partial",
        )
        self.assertFalse(out["deterministic_checks"]["WS6_tree_structure"]["components"]["operators"])

    def test_alternative_valid_tree_full_credit(self):
        """Different features/thresholds are valid when notation and complements hold."""
        from pipeline_schema import load_rubric

        alt = {
            "WS6_B1": "protein",
            "WS6_B2": "≥ 5",
            "WS6_B3": "evet (≥ 5)",
            "WS6_B4": "hayır (< 5)",
            "WS6_B6": "enerji",
            "WS6_B7": "≤ 100",
            "WS6_B8": "evet (≤ 100)",
            "WS6_B9": "hayır (> 100)",
            "WS6_B10": "Tavsiye edilir",
            "WS6_B11": "Tavsiye edilmez",
            "WS6_B13": "Tavsiye edilmez",
        }
        out = validate_ws6_extraction(alt, load_rubric("WS6"))
        checks = out["deterministic_checks"]
        self.assertEqual(checks["WS6_root_threshold"]["credit"], "full")
        self.assertEqual(checks["WS6_inner_threshold"]["credit"], "full")
        self.assertEqual(checks["WS6_root_feature"]["credit"], "full")
        self.assertEqual(checks["WS6_inner_feature"]["credit"], "full")


if __name__ == "__main__":
    unittest.main()
