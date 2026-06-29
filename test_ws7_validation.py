"""Tests for WS7 path matching and WS6 rule consistency."""

from __future__ import annotations

import unittest

from ws7_validation import (
    P1_ANSWERS,
    enumerate_ws6_path_specs,
    parse_decision_rule,
    validate_path_matching,
    validate_rule_against_spec,
    validate_ws7_extraction,
)
from ws6_validation import build_ws6_tree

WS6_SAMPLE = {
    "WS6_B1": "şeker",
    "WS6_B2": "≤ 10",
    "WS6_B3": "evet (≤ 10)",
    "WS6_B4": "hayır (> 10)",
    "WS6_B6": "yağ",
    "WS6_B7": "≤ 5",
    "WS6_B8": "evet (≤ 5)",
    "WS6_B9": "hayır (> 5)",
    "WS6_B10": "Tavsiye edilir",
    "WS6_B11": "Tavsiye edilmez",
    "WS6_B13": "Tavsiye edilmez",
}


class TestWS7Validation(unittest.TestCase):
    def test_p1_letters(self):
        self.assertEqual(validate_path_matching("WS7_P1_box1", "B")["credit"], "full")
        self.assertEqual(validate_path_matching("WS7_P1_box2", "a")["credit"], "full")
        self.assertEqual(validate_path_matching("WS7_P1_box3", "C")["credit"], "full")
        self.assertEqual(validate_path_matching("WS7_P1_box1", "A")["credit"], "zero")

    def test_parse_sample_rules(self):
        r1 = parse_decision_rule("Eğer şeker ≤ 10 ve yağ ≤ 5 ise → Tavsiye edilir.")
        assert r1 is not None
        self.assertEqual(len(r1["conditions"]), 2)
        self.assertTrue(r1["recommended"])

        r3 = parse_decision_rule("Eğer şeker > 10 ise → Tavsiye edilmez.")
        assert r3 is not None
        self.assertEqual(r3["conditions"][0]["operator"], ">")

    def test_b1_full_credit_against_ws6(self):
        tree = build_ws6_tree(WS6_SAMPLE)
        specs = enumerate_ws6_path_specs(tree)
        out = validate_rule_against_spec(
            "Eğer şeker ≤ 10 ve yağ ≤ 5 ise → Tavsiye edilir.",
            specs[0],
        )
        self.assertEqual(out["credit"], "full")

    def test_b2_wrong_operator_partial(self):
        tree = build_ws6_tree(WS6_SAMPLE)
        specs = enumerate_ws6_path_specs(tree)
        out = validate_rule_against_spec(
            "Eğer şeker ≤ 10 ve yağ ≥ 5 ise → Tavsiye edilmez.",
            specs[1],
        )
        self.assertEqual(out["credit"], "partial")
        self.assertEqual(out["reason"], "wrong_operator_direction")

    def test_full_extraction_sample_student(self):
        from pipeline_schema import load_rubric

        ws7 = {
            "WS7_P1_box1": "B",
            "WS7_P1_box2": "A",
            "WS7_P1_box3": "C",
            "WS7_B1": "Eğer şeker ≤ 10 ve yağ ≤ 5 ise → Tavsiye edilir.",
            "WS7_B2": "Eğer şeker ≤ 10 ve yağ > 5 ise → Tavsiye edilmez.",
            "WS7_B3": "Eğer şeker > 10 ise → Tavsiye edilmez.",
        }
        out = validate_ws7_extraction(ws7, load_rubric("WS7"), ws6_responses=WS6_SAMPLE)
        checks = out["deterministic_checks"]
        for key in list(P1_ANSWERS) + ["WS7_B1", "WS7_B2", "WS7_B3"]:
            self.assertEqual(checks[key]["credit"], "full", key)


if __name__ == "__main__":
    unittest.main()
