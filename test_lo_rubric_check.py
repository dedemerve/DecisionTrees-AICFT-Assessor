"""test_lo_rubric_check.py — Simple LO rubric module tests."""

from __future__ import annotations

import unittest

from pydantic import ValidationError

from lo_rubric_check import (
    EvidenceExcerpt,
    LOReferenceText,
    ResearcherRubricDecision,
    assess_researcher_decision_completeness,
    load_lo_catalog,
    present_for_review,
    validate_researcher_decisions,
)


class TestLoRubricCheck(unittest.TestCase):
    def test_lo_reference_text_validates(self) -> None:
        lo = LOReferenceText(
            lo_code="LO3.2.1",
            full_text="Apply AI tools to compare models.",
            progression_level="Deepen",
        )
        self.assertEqual(lo.lo_code, "LO3.2.1")

    def test_evidence_excerpt_validates(self) -> None:
        ex = EvidenceExcerpt(
            source="worksheet",
            excerpt="Student compares two thresholds using MCR.",
            worksheet="WS5",
            item_id="WS5_B1",
        )
        self.assertEqual(ex.source, "worksheet")

    def test_present_for_review_readable(self) -> None:
        lo = LOReferenceText(
            lo_code="LO3.1.1",
            full_text="Foundational AI vocabulary.",
            progression_level="Acquire",
        )
        evidence = [
            EvidenceExcerpt(source="worksheet", excerpt="Defines feature and label.", worksheet="WS1"),
        ]
        text = present_for_review(lo, evidence)
        self.assertIn("LO3.1.1", text)
        self.assertIn("Foundational AI vocabulary", text)
        self.assertIn("[worksheet]", text)
        self.assertIn("Defines feature and label", text)

    def test_researcher_note_required(self) -> None:
        with self.assertRaises(ValidationError):
            ResearcherRubricDecision(
                lo_code="LO3.2.2",
                candidate_id="Sample_Student",
                decision="met",
                supporting_evidence=[
                    EvidenceExcerpt(source="worksheet", excerpt="Compared thresholds."),
                ],
                researcher_note="",
            )

    def test_load_lo_catalog_from_framework(self) -> None:
        catalog = load_lo_catalog()
        self.assertIn("LO3.1.1", catalog)
        self.assertIn("LO3.3.1", catalog)
        self.assertTrue(catalog["LO3.2.2"].full_text)

    def test_validate_researcher_decisions_empty_list_passes(self) -> None:
        self.assertEqual(validate_researcher_decisions([]), [])

    def test_empty_decisions_reported_as_pending_not_error(self) -> None:
        status = assess_researcher_decision_completeness(
            [],
            expected_lo_codes=["LO3.1.1", "LO3.2.1", "LO3.3.1"],
        )
        self.assertEqual(status.recorded_count, 0)
        self.assertEqual(status.expected_lo_count, 3)
        self.assertEqual(status.status, "pending")
        self.assertIn("bekliyor", status.message)


if __name__ == "__main__":
    unittest.main()
