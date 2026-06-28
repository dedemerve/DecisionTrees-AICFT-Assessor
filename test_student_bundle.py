"""test_student_bundle.py — Modular per-worksheet artifact tests."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pipeline_schema import ARTIFACT_SCHEMA_VERSION
from student_bundle import (
    artifact_path,
    artifact_payload,
    load_artifact,
    migrate_combined_worksheet_file,
    migrate_student_to_v30,
    portfolio_path,
    save_artifact,
    save_portfolio,
    save_scoring_bundle,
    student_dir,
)


class TestStudentBundle(unittest.TestCase):
    def test_extraction_artifact_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            save_artifact("Roundtrip", "WS1", "extraction", {
                "responses": {"WS1_B1": "test"},
            }, base_dir=base)
            loaded = load_artifact("Roundtrip", "WS1", "extraction", base_dir=base)
            self.assertEqual(loaded["schema_version"], ARTIFACT_SCHEMA_VERSION)
            self.assertEqual(loaded["stage"], "extraction")
            self.assertEqual(artifact_payload(loaded)["responses"]["WS1_B1"], "test")

    def test_scoring_bundle_splits_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            save_scoring_bundle("S1", "WS3", {
                "max_score": 2,
                "items": [{
                    "item": "WS3_B1",
                    "score": 1.0,
                    "confidence": 0.8,
                    "review": False,
                    "competencies": [{
                        "lo": "LO3.1.1",
                        "strength": "moderate",
                        "evidence_type": "direct",
                        "rationale": "test",
                        "evidence_present": True,
                    }],
                }],
            }, base_dir=base)
            scoring = artifact_payload(load_artifact("S1", "WS3", "scoring", base_dir=base))
            evidence = artifact_payload(load_artifact("S1", "WS3", "evidence", base_dir=base))
            summary = artifact_payload(load_artifact("S1", "WS3", "summary", base_dir=base))
            self.assertNotIn("learning_objects", scoring["items"][0])
            self.assertNotIn("competencies", scoring["items"][0])
            self.assertEqual(evidence["items"][0]["competencies"][0]["lo"], "LO3.1.1")
            self.assertIn("review_items", summary)
            self.assertNotIn("learning_objects", summary)

    def test_migrate_combined_v21_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            combined = {
                "schema_version": "2.1",
                "student_id": "M1",
                "worksheet": "WS1",
                "extraction": {"responses": {"WS1_B1": "x"}},
                "validation": {"answered": 1, "blank": 0, "missing": []},
                "scoring": {
                    "items": [{
                        "item": "WS1_B1",
                        "score": 1.0,
                        "confidence": 0.8,
                        "review": False,
                        "learning_objects": [],
                    }],
                    "max_score": 1,
                },
                "summary": {"total_score": 1, "max_score": 1, "learning_objects": {}},
            }
            migrate_combined_worksheet_file("M1", "WS1", combined, base_dir=base)
            self.assertTrue(artifact_path("M1", "WS1", "extraction", base_dir=base).exists())
            self.assertFalse(artifact_path("M1", "WS1", "validation", base_dir=base).exists())

    def test_sample_student_worksheets_exist(self):
        root = student_dir("Sample_Student")
        self.assertTrue(root.is_dir(), "Run migrate_student_to_v30 if flat WS*.json remain")
        self.assertTrue(artifact_path("Sample_Student", "WS1", "extraction").exists())
        self.assertTrue(portfolio_path("Sample_Student").exists())


if __name__ == "__main__":
    unittest.main()
