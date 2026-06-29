"""Tests for WS10 fixed energy table validation."""

from __future__ import annotations

import unittest

from ws10_validation import (
    expected_answers,
    validate_ws10_blank,
    validate_ws10_extraction,
    verify_reference_answers,
)


class TestWS10Validation(unittest.TestCase):
    def test_reference_internally_consistent(self):
        issues = verify_reference_answers()
        self.assertEqual(issues, [], issues)

    def test_expected_answers_from_image(self):
        ans = expected_answers()
        self.assertEqual(ans["WS10_B1"], 4)
        self.assertEqual(ans["WS10_B6"], 1)
        self.assertEqual(ans["WS10_B8"], 408)

    def test_wrong_count_zero(self):
        self.assertEqual(validate_ws10_blank("WS10_B1", "3")["credit"], "zero")

    def test_full_grid(self):
        responses = {k: str(v) for k, v in expected_answers().items()}
        out = validate_ws10_extraction(responses)
        self.assertTrue(out["all_correct"])
        for check in out["deterministic_checks"].values():
            self.assertEqual(check["credit"], "full")


if __name__ == "__main__":
    unittest.main()
