"""Tests for WS_DT interpretive scoring policy."""

from __future__ import annotations

import unittest

from pipeline_schema import (
    WS_DT_DETERMINISTIC_ITEM_IDS,
    get_assessor_rubric,
    is_interpretive_rubric_item,
    load_rubric,
    rubric_item,
    validate_all_rubrics,
)


class TestWsDtInterpretive(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rubric = load_rubric("WS_DT")

    def test_text_items_are_interpretive(self):
        for item_id in ("DT_A_Q1", "DT_A_Q4", "DT_B_Q4", "DT_G_Q2"):
            item = rubric_item("WS_DT", item_id)
            self.assertTrue(
                is_interpretive_rubric_item(item, self.rubric, item_id=item_id),
                item_id,
            )

    def test_emit_items_are_not_interpretive(self):
        for item_id in WS_DT_DETERMINISTIC_ITEM_IDS:
            item = rubric_item("WS_DT", item_id)
            self.assertFalse(
                is_interpretive_rubric_item(item, self.rubric, item_id=item_id),
                item_id,
            )

    def test_assessor_criteria_no_single_answer(self):
        criteria = get_assessor_rubric("DT_A_Q4", "WS_DT")
        joined = " ".join(criteria["full_credit_criteria"]).lower()
        self.assertIn("no single canonical", joined)
        self.assertIn("illustrative example only", criteria["prompt_description"].lower())

    def test_e_q4_conceptual_not_rigid_no(self):
        item = rubric_item("WS_DT", "DT_E_Q4")
        self.assertEqual(item["evaluation"], "conceptual_limitation")
        self.assertEqual(item.get("scoring_mode"), "interpretive")
        ideas = " ".join(c["idea"] for c in item["components"])
        self.assertIn("overlap", ideas.lower())

    def test_rubrics_validate(self):
        self.assertEqual(validate_all_rubrics(), [])


if __name__ == "__main__":
    unittest.main()
