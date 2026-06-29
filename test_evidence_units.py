"""Unit tests for canonical Evidence Unit runtime (Phase 2 Milestone 2)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from evidence_unit_runtime import (
    build_and_save_evidence_units,
    build_evidence_units_from_student,
    deterministic_evidence_unit_id,
    evidence_units_path,
    generate_sample_evidence_unit,
    load_evidence_units,
    normalize_field_content,
    FieldExtractionInput,
)
from schema_validate import validate_evidence_units
from student_bundle import save_artifact


class TestEvidenceUnitRuntime(unittest.TestCase):
    def test_deterministic_id_stable(self):
        a = deterministic_evidence_unit_id("S", "WS1", "WS1_B1")
        b = deterministic_evidence_unit_id("S", "WS1", "WS1_B1")
        self.assertEqual(a, b)
        self.assertRegex(a, r"^EU_\d{6}$")

    def test_normalize_blank_and_illegible(self):
        blank = normalize_field_content("")
        self.assertEqual(blank.normalized_content, "(bos)")
        self.assertLess(blank.extraction_confidence, 0.5)

        illeg = normalize_field_content("(okunamiyor)")
        self.assertEqual(illeg.normalized_content, "(okunamiyor)")

    def test_build_unit_is_assessment_object(self):
        unit = generate_sample_evidence_unit()
        forbidden = {
            "behaviour_id", "ilo_id", "learning_object_id", "lo",
            "domain_id", "ai_cft", "competency",
        }
        self.assertFalse(forbidden & set(unit.keys()))
        self.assertEqual(unit["evidence_unit_type"], "comparison")
        self.assertEqual(unit["evidence_completeness"], "complete")
        self.assertIn("evidence_quality", unit["confidence"])
        self.assertIn("content", unit)
        self.assertNotIn("uncertainty", unit)
        self.assertNotIn("review_level", unit)
        self.assertNotIn("provenance", unit)
        self.assertNotIn("evidence_unit_id", unit)

    def test_sample_unit_validates(self):
        doc = {
            "student_id": "Student_04",
            "evidence_units": [generate_sample_evidence_unit()],
        }
        self.assertEqual(validate_evidence_units(doc), [])

    def test_build_from_student_extractions(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            save_artifact("EU_Test", "WS1", "extraction", {
                "responses": {
                    "WS1_B1": "Nesne tanımı",
                    "WS1_B2": "",
                },
            }, base_dir=base)

            doc = build_evidence_units_from_student("EU_Test", base_dir=base)
            self.assertNotIn("schema_version", doc)
            self.assertEqual(len(doc["evidence_units"]), 2)
            self.assertEqual(validate_evidence_units(doc), [])

            by_item = {u["item_id"]: u for u in doc["evidence_units"]}
            self.assertEqual(by_item["WS1_B2"]["evidence_completeness"], "blank")
            self.assertEqual(by_item["WS1_B1"]["evidence_unit_type"], "definition")

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            save_artifact("RT", "WS3", "extraction", {
                "responses": {"WS3_B1": "Tavsiye edilemez"},
            }, base_dir=base)
            path = build_and_save_evidence_units("RT", base_dir=base)
            self.assertTrue(path.exists())
            loaded = load_evidence_units("RT", base_dir=base)
            assert loaded is not None
            self.assertNotIn("schema_version", loaded)
            self.assertEqual(validate_evidence_units(loaded), [])

    def test_sample_student_bundle_generates(self):
        path = evidence_units_path("Sample_Student")
        if not path.parent.joinpath("WS1/extraction.json").exists():
            self.skipTest("Sample_Student extractions not present")
        out = build_and_save_evidence_units("Sample_Student")
        data = json.loads(out.read_text(encoding="utf-8"))
        self.assertGreater(len(data["evidence_units"]), 0)
        self.assertEqual(validate_evidence_units(data), [])
        ws1_eu = path.parent / "WS1" / "evidence_units.json"
        self.assertTrue(ws1_eu.exists(), "per-worksheet evidence_units.json expected")
        ws1_doc = json.loads(ws1_eu.read_text(encoding="utf-8"))
        self.assertEqual(ws1_doc.get("worksheet_id"), "WS1")
        self.assertNotIn("definition", ws1_doc)
        first = ws1_doc["evidence_units"][0]
        self.assertNotIn("student_id", first)
        self.assertNotIn("worksheet_id", first)
        self.assertEqual(validate_evidence_units(ws1_doc), [])


if __name__ == "__main__":
    unittest.main()
