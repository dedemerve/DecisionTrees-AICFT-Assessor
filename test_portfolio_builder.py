"""test_portfolio_builder.py — Portfolio aggregation tests."""

from __future__ import annotations

import unittest

from portfolio_builder import (
    _peak_strength,
    build_portfolio,
    propose_ai_cft_level,
)
from student_bundle import student_dir


class TestPortfolioBuilder(unittest.TestCase):
    def test_peak_strength_ordering(self):
        self.assertEqual(_peak_strength(["weak", "strong", "moderate"]), "strong")
        self.assertEqual(_peak_strength([]), "none")

    def test_propose_deepen_when_application_los_strong(self):
        los = {
            "LO3.1.1": {"peak_strength": "strong"},
            "LO3.1.2": {"peak_strength": "strong"},
            "LO3.1.3": {"peak_strength": "none"},
            "LO3.2.1": {"peak_strength": "moderate"},
            "LO3.2.2": {"peak_strength": "strong"},
            "LO3.2.3": {"peak_strength": "moderate"},
            "LO3.3.1": {"peak_strength": "none"},
        }
        proposal = propose_ai_cft_level(los)
        self.assertEqual(proposal["Aspect3"], "Deepen")
        self.assertFalse(proposal["is_final"])

    def test_sample_student_portfolio_builds(self):
        self.assertTrue(student_dir("Sample_Student").is_dir())
        portfolio = build_portfolio("Sample_Student")
        self.assertIn("WS1", portfolio["worksheets_scored"])
        self.assertIn("LO3.2.2", portfolio["learning_objects"])
        self.assertIn("ai_cft_proposal", portfolio)
        self.assertIn("baseline_evidence", portfolio)
        self.assertIn("methodology", portfolio)
        self.assertIn("competency_level_summary", portfolio)

    def test_baseline_excludes_prior_belief_from_peak(self):
        from pipeline_schema import framework_item_index, load_framework
        from portfolio_builder import _collect_worksheet_evidence

        fw_index = framework_item_index(load_framework())
        _, _, _, baseline = _collect_worksheet_evidence("Sample_Student", fw_index)
        baseline_items = {(r["worksheet"], r["item"]) for r in baseline}
        self.assertIn(("WS_DT", "DT_A_Q1"), baseline_items)


if __name__ == "__main__":
    unittest.main()
