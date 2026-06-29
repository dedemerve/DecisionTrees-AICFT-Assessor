"""Unit tests for Evidence Unit assessment metadata derivation."""

from __future__ import annotations

import unittest

from evidence_unit_metadata import (
    derive_assessment_metadata,
    infer_completeness,
    infer_evidence_unit_type,
    infer_observability,
    infer_review_level,
    infer_source_quality,
)


class TestEvidenceUnitMetadata(unittest.TestCase):
    def test_ws1_definition_type(self):
        self.assertEqual(
            infer_evidence_unit_type("WS1", "WS1_B1", "WS1_B1", {"type": "free_text"}),
            "definition",
        )

    def test_formula_type_from_rubric(self):
        self.assertEqual(
            infer_evidence_unit_type("WS_DT", "DT_E_MCR_formula", "DT_E_MCR_formula", {"type": "free_text"}),
            "formula",
        )

    def test_ws4_b4_peer_evaluation_type(self):
        self.assertEqual(
            infer_evidence_unit_type("WS4", "WS4_B4", "WS4_B4", {"type": "free_text"}),
            "model_evaluation",
        )

    def test_ws4_b2_classification_type(self):
        self.assertEqual(
            infer_evidence_unit_type("WS4", "WS4_B2", "WS4_B2", {"type": "free_text"}),
            "classification",
        )

    def test_blank_completeness(self):
        self.assertEqual(infer_completeness("(bos)", "", "definition"), "blank")

    def test_partial_short_definition(self):
        self.assertEqual(infer_completeness("kısa", "kısa", "definition"), "partial")

    def test_source_quality_unknown_without_ocr(self):
        self.assertEqual(
            infer_source_quality("complete", None, 0.85),
            "good",
        )

    def test_observability_reflection_indirect(self):
        self.assertEqual(
            infer_observability("reflection", "learner_reflection"),
            "indirect",
        )

    def test_review_critical_for_illegible(self):
        self.assertEqual(
            infer_review_level("illegible", "poor", 0.9, 0.2),
            "critical",
        )

    def test_derive_populates_alternatives_for_partial(self):
        meta = derive_assessment_metadata(
            worksheet_id="WS1",
            field_id="WS1_B1",
            rubric_item_id="WS1_B1",
            source_family="worksheet",
            raw_content="nesne",
            normalized_content="nesne",
            extraction_confidence=0.85,
            ocr_confidence=None,
            uncertainty="none",
            alternative_interpretations=[],
        )
        self.assertEqual(meta.evidence_completeness, "partial")
        self.assertTrue(any(
            "incomplete" in a["interpretation"] for a in meta.alternative_interpretations
        ))
        self.assertEqual(meta.review_level, "recommended")
        self.assertTrue(meta.requires_human_review)


    def test_observability_demographic_indirect(self):
        self.assertEqual(
            infer_observability("observation", "learner_response"),
            "indirect",
        )

    def test_ws11_survey_not_demographic_type(self):
        self.assertEqual(
            infer_evidence_unit_type("WS11", "WS11_B1", None, {"type": "free_text"}),
            "reflection",
        )

    def test_ws11_demographic_b6_type(self):
        self.assertEqual(
            infer_evidence_unit_type("WS11", "WS11_B6", None, {"type": "free_text"}),
            "parameter_selection",
        )


if __name__ == "__main__":
    unittest.main()
