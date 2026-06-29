"""Tests for WS11 deterministic validation (Q10–Q12)."""

from __future__ import annotations

import unittest

from ws11_validation import validate_multiselect, validate_true_false, validate_ws11_deterministic


class TestWs11Validation(unittest.TestCase):
    def test_q10_full_key(self):
        responses = {
            f"WS11_Q10_{i}": v
            for i, v in enumerate(
                ["Doğru", "Doğru", "Yanlış", "Doğru", "Doğru", "Yanlış", "Yanlış", "Doğru"],
                start=1,
            )
        }
        out = validate_ws11_deterministic(responses)
        self.assertTrue(out["all_correct"])
        self.assertEqual(out["items_correct"], 8)

    def test_q12_multiselect(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS11")
        self.assertTrue(validate_multiselect("WS11_Q12_1", "İşaretli", rubric)["ok"])
        self.assertTrue(validate_multiselect("WS11_Q12_2", "İşaretlenmemiş", rubric)["ok"])


if __name__ == "__main__":
    unittest.main()
