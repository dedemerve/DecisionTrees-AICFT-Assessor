"""Tests for worksheet blank registry."""

from __future__ import annotations

import unittest

from pipeline_schema import WORKSHEET_ITEM_IDS, scoring_item_ids
from worksheet_blank_registry import (
    build_worksheet_registry,
    field_registry_entry,
    worksheet_field_ids,
)


class TestWorksheetBlankRegistry(unittest.TestCase):
    def test_ws10_blank_numbers_and_fixed_responses(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS10")
        for i in range(1, 9):
            fid = f"WS10_B{i}"
            meta = field_registry_entry("WS10", fid, rubric)
            self.assertEqual(meta["printed_blank"], i)
            self.assertEqual(meta["scoring_mode"], "fixed_exact")
            self.assertTrue(meta["scored"])
            self.assertIsNotNone(meta.get("fixed_response"))

    def test_ws7_p1_fixed_letters(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS7")
        self.assertEqual(
            field_registry_entry("WS7", "WS7_P1_box1", rubric)["fixed_response"],
            "B",
        )
        self.assertEqual(
            field_registry_entry("WS7", "WS7_B1", rubric)["scoring_mode"],
            "cross_worksheet",
        )

    def test_ws5_row6_not_scored(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS5")
        meta = field_registry_entry("WS5", "WS5_B21", rubric)
        self.assertFalse(meta["scored"])
        self.assertEqual(meta["scoring_item_id"], "WS5_row6")

    def test_all_deployed_worksheets_have_fields(self):
        for ws in ("WS1", "WS3", "WS4", "WS5", "WS6", "WS7", "WS10", "WS11"):
            self.assertEqual(len(worksheet_field_ids(ws)), len(WORKSHEET_ITEM_IDS[ws]))

    def test_registry_covers_scoring_items(self):
        for ws in ("WS5", "WS6", "WS7", "WS10"):
            reg = build_worksheet_registry(ws)
            scored_fields = [f for f, m in reg["fields"].items() if m.get("scored")]
            self.assertTrue(len(scored_fields) >= len(scoring_item_ids(ws)))


    def test_ws11_survey_not_scored(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS11")
        meta = field_registry_entry("WS11", "WS11_B1", rubric)
        self.assertEqual(meta["printed_question"], 1)
        self.assertEqual(meta["scoring_mode"], "survey")
        self.assertFalse(meta["scored"])
        self.assertIn("Çok iyi", meta.get("allowed_responses", []))

    def test_ws11_demographic_b6_b7(self):
        from pipeline_schema import load_rubric

        rubric = load_rubric("WS11")
        meta = field_registry_entry("WS11", "WS11_B7", rubric)
        self.assertEqual(meta["scoring_mode"], "demographic")
        self.assertEqual(meta.get("allowed_responses"), ["Erkek", "Kız"])


if __name__ == "__main__":
    unittest.main()
