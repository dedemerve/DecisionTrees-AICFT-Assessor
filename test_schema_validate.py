"""test_schema_validate.py — Portfolio and mapping schema validation tests."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from portfolio_builder import build_portfolio
from schema_validate import validate_all_mappings_v2, validate_mapping_v2, validate_portfolio_v1

REPO = Path(__file__).parent


class TestSchemaValidate(unittest.TestCase):
    def test_all_worksheet_mappings_v2(self):
        errors = validate_all_mappings_v2(REPO / "mappings")
        self.assertEqual(errors, [], f"Mapping errors: {errors[:5]}")

    def test_sample_portfolio_v1(self):
        portfolio = build_portfolio("Sample_Student")
        portfolio["student_id"] = "Sample_Student"
        errors = validate_portfolio_v1(portfolio)
        self.assertEqual(errors, [], f"Portfolio errors: {errors}")

    def test_ws11_q11_mapping_has_portfolio_weight(self):
        data = json.loads((REPO / "mappings" / "WS11_AICFT_mapping.json").read_text())
        q11 = data["items"]["WS11_Q11_2"][0]
        self.assertEqual(q11["lo"], "LO3.1.2")
        self.assertEqual(q11["portfolio_weight"], "full")

    def test_dt_a_q1_is_baseline(self):
        data = json.loads((REPO / "mappings" / "WS_DT_AICFT_mapping.json").read_text())
        q1 = data["items"]["DT_A_Q1"][0]
        self.assertEqual(q1["evidence_type"], "prior_belief")
        self.assertEqual(q1["portfolio_weight"], "baseline")


if __name__ == "__main__":
    unittest.main()
