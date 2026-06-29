"""Tests for order-insensitive token-set rubric scoring."""

from __future__ import annotations

import unittest

from pipeline_schema import get_assessor_rubric, validate_all_rubrics
from rubric_deterministic import (
    resolve_accepted_aliases,
    score_any_of_tokens,
    score_numeric_range,
    score_unordered_token_set,
)


WS1_B5_ITEM = {
    "max_score": 1,
    "evaluation": "unordered_token_set",
    "check": "unordered_token_set",
    "need_tokens": 5,
    "partial_on_tokens": 3,
    "token_groups": [
        {"id": "enerji", "aliases": ["enerji", "energy"]},
        {"id": "yag", "aliases": ["yağ", "yag", "fat"]},
        {"id": "doymus_yag", "aliases": ["doymuş yağ", "doymuş", "doymus"]},
        {"id": "karbonhidrat", "aliases": ["karbonhidrat"]},
        {"id": "seker", "aliases": ["şeker", "seker"]},
        {"id": "protein", "aliases": ["protein"]},
        {"id": "tuz", "aliases": ["tuz", "salt"]},
    ],
}


WS1_RUBRIC = {
    "equivalence_sets": {
        "object_feature": {
            "aliases": ["nesne", "özellik", "ozellik", "karakteristik"],
        },
        "variable_label": {
            "aliases": ["değişken", "degisken", "etiket", "etiket olarak"],
        },
    },
}

WS1_B1_ITEM = {
    "check": "any_of_tokens",
    "evaluation": "any_of_tokens",
    "accept_sets": ["variable_label"],
}

WS1_B2_ITEM = {
    "check": "any_of_tokens",
    "evaluation": "any_of_tokens",
    "accept_sets": ["object_feature"],
}

WS1_B3_ITEM = {
    "check": "any_of_tokens",
    "evaluation": "any_of_tokens",
    "accept_sets": ["object_feature", "variable_label"],
}

WS1_B4_ITEM = {
    "check": "any_of_tokens",
    "evaluation": "any_of_tokens",
    "accepted_aliases": ["7", "yedi"],
}


class TestAnyOfTokens(unittest.TestCase):
    def test_b1_accepts_etiket_or_degisken(self):
        self.assertEqual(
            score_any_of_tokens("etiket", WS1_B1_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )
        self.assertEqual(
            score_any_of_tokens("değişken", WS1_B1_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )

    def test_b1_rejects_nesne(self):
        self.assertEqual(
            score_any_of_tokens("nesne", WS1_B1_ITEM, WS1_RUBRIC)["credit"],
            "zero",
        )

    def test_b2_accepts_nesne_or_ozellik(self):
        self.assertEqual(
            score_any_of_tokens("nesne", WS1_B2_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )
        self.assertEqual(
            score_any_of_tokens("özellik", WS1_B2_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )

    def test_b3_accepts_either_pair(self):
        self.assertEqual(
            score_any_of_tokens("değişken", WS1_B3_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )
        self.assertEqual(
            score_any_of_tokens("nesne", WS1_B3_ITEM, WS1_RUBRIC)["credit"],
            "full",
        )

    def test_b4_accepts_seven_numeric_or_word(self):
        self.assertEqual(score_any_of_tokens("7", WS1_B4_ITEM, WS1_RUBRIC)["credit"], "full")
        self.assertEqual(score_any_of_tokens("yedi", WS1_B4_ITEM, WS1_RUBRIC)["credit"], "full")
        self.assertEqual(score_any_of_tokens("Yedi", WS1_B4_ITEM, WS1_RUBRIC)["credit"], "full")

    def test_b4_rejects_eight(self):
        self.assertEqual(score_any_of_tokens("8", WS1_B4_ITEM, WS1_RUBRIC)["credit"], "zero")
        self.assertEqual(score_any_of_tokens("sekiz", WS1_B4_ITEM, WS1_RUBRIC)["credit"], "zero")

    def test_assessor_criteria_b1_lists_equivalents(self):
        criteria = get_assessor_rubric("WS1_B1", "WS1")
        joined = " ".join(criteria["full_credit_criteria"]).lower()
        self.assertIn("etiket", joined)
        self.assertIn("değişken", joined)


class TestUnorderedTokenSet(unittest.TestCase):
    def test_full_credit_any_order(self):
        shuffled = "Tuz, Protein, Şeker, Karbonhidrat, Doymuş Yağ, Yağ, Enerji"
        result = score_unordered_token_set(shuffled, WS1_B5_ITEM)
        self.assertEqual(result["credit"], "full")
        self.assertTrue(result["ok"])

    def test_full_credit_reversed_example(self):
        answer = "Protein, Tuz, Şeker, Karbonhidrat, Doymuş Yağ, Yağ, Enerji"
        result = score_unordered_token_set(answer, WS1_B5_ITEM)
        self.assertEqual(result["credit"], "full")

    def test_partial_credit(self):
        answer = "Enerji, Yağ, Protein"
        result = score_unordered_token_set(answer, WS1_B5_ITEM)
        self.assertEqual(result["credit"], "partial")
        self.assertEqual(result["matched_tokens"], 3)

    def test_zero_credit(self):
        answer = "Enerji, Yağ"
        result = score_unordered_token_set(answer, WS1_B5_ITEM)
        self.assertEqual(result["credit"], "zero")

    def test_blank_not_attempted(self):
        result = score_unordered_token_set("(bos)", WS1_B5_ITEM)
        self.assertEqual(result["credit"], "not_attempted")

    def test_assessor_criteria_mentions_order_insensitive(self):
        criteria = get_assessor_rubric("WS1_B5", "WS1")
        joined = " ".join(criteria["full_credit_criteria"])
        self.assertIn("order does not matter", joined.lower())

    def test_rubrics_validate(self):
        errors = validate_all_rubrics()
        self.assertEqual(errors, [])


WS4_B2_ITEM = {
    "max_score": 1,
    "check": "unordered_token_set",
    "need_tokens": 4,
    "partial_on_tokens": 4,
    "token_groups": [
        {"id": "jelibon", "aliases": ["jelibon", "jellybean"]},
        {"id": "kraker", "aliases": ["kraker", "cracker"]},
        {"id": "yulaf", "aliases": ["yulaf", "oatmeal"]},
        {"id": "avokado", "aliases": ["avokado", "avocado"]},
    ],
}

WS4_B5_ITEM = {
    "max_score": 1,
    "check": "numeric_range",
    "min_value": 160,
    "max_value": 2223,
}


class TestWS4Rubric(unittest.TestCase):
    def test_b2_requires_all_four_foods_any_order(self):
        shuffled = "avokado, jelibon, yulaf, kraker"
        self.assertEqual(score_unordered_token_set(shuffled, WS4_B2_ITEM)["credit"], "full")

    def test_b2_rejects_three_foods(self):
        answer = "jelibon, kraker, yulaf"
        self.assertEqual(score_unordered_token_set(answer, WS4_B2_ITEM)["credit"], "zero")

    def test_b5_accepts_inclusive_range(self):
        self.assertEqual(score_numeric_range("408", WS4_B5_ITEM)["credit"], "full")
        self.assertEqual(score_numeric_range("160", WS4_B5_ITEM)["credit"], "full")
        self.assertEqual(score_numeric_range("2223", WS4_B5_ITEM)["credit"], "full")

    def test_b5_rejects_outside_range(self):
        self.assertEqual(score_numeric_range("159", WS4_B5_ITEM)["credit"], "zero")
        self.assertEqual(score_numeric_range("2224", WS4_B5_ITEM)["credit"], "zero")


if __name__ == "__main__":
    unittest.main()
