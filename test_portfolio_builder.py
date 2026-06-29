"""test_portfolio_builder.py — Portfolio aggregation tests."""

from __future__ import annotations

import unittest

from lo_rubric_check import ResearcherRubricDecision, EvidenceExcerpt
from portfolio_builder import build_portfolio, collect_worksheet_excerpts_by_lo
from student_bundle import student_dir


class TestPortfolioBuilder(unittest.TestCase):
    def test_sample_student_portfolio_builds(self) -> None:
        self.assertTrue(student_dir("Sample_Student").is_dir())
        portfolio = build_portfolio("Sample_Student")
        self.assertIn("WS1", portfolio["worksheets_scored"])
        self.assertIn("LO3.2.2", portfolio["lo_review_packets"])
        self.assertIn("evidence_by_lo", portfolio)
        self.assertEqual(portfolio["methodology"]["approach"], "simple_lo_rubric")
        self.assertEqual(portfolio["researcher_rubric_decisions"], [])

    def test_collect_excerpts_has_lo_tags(self) -> None:
        by_lo = collect_worksheet_excerpts_by_lo("Sample_Student")
        self.assertTrue(any(by_lo.values()))
        self.assertTrue(any(lo.startswith("LO3.") for lo in by_lo))

    def test_researcher_decision_roundtrip(self) -> None:
        decision = ResearcherRubricDecision(
            lo_code="LO3.2.2",
            candidate_id="Sample_Student",
            decision="partial",
            supporting_evidence=[
                EvidenceExcerpt(
                    source="worksheet",
                    excerpt="Threshold comparison present but not fully justified.",
                    worksheet="WS5",
                ),
            ],
            researcher_note="Evidence shows comparison language without full metric linkage.",
        )
        self.assertEqual(decision.decision, "partial")


if __name__ == "__main__":
    unittest.main()
