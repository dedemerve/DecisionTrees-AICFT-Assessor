"""test_learning_objects.py — Milestone 2 Instructional Learning Object ontology tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
ILO_PATH = REPO / "framework" / "Learning_Objects.json"
OB_PATH = REPO / "framework" / "Observable_Behaviours.json"
VALIDATOR = REPO / "scripts" / "validate_learning_objects.py"


class TestLearningObjects(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ilo = json.loads(ILO_PATH.read_text(encoding="utf-8"))
        cls.ob = json.loads(OB_PATH.read_text(encoding="utf-8"))
        cls.ilos = cls.ilo["learning_objects"]

    def test_terminology_ilo_disambiguation(self) -> None:
        term = self.ilo["terminology"]
        self.assertEqual(term["abbreviation"], "ILO")
        self.assertIn("SCORM", term["disambiguation"])
        self.assertIn("LO3", term["aicft_competency_note"])

    def test_all_construct_dimensions(self) -> None:
        dims = {v["construct_dimension"] for v in self.ilos.values()}
        self.assertEqual(dims, {"conceptual", "procedural", "strategic", "reflective"})

    def test_all_frozen_behaviours_linked(self) -> None:
        ob_ids = set(self.ob["behaviours"])
        linked: set[str] = set()
        for ilo in self.ilos.values():
            linked.update(ilo["related_behaviours"])
        self.assertEqual(linked, ob_ids)

    def test_no_worksheet_or_lo3_in_ilo_entries(self) -> None:
        for iid, ilo in self.ilos.items():
            blob = " ".join([
                ilo.get("title", ""),
                ilo.get("description", ""),
                ilo.get("instructional_purpose", ""),
            ])
            for token in ("WS1", "WS_DT", "LO3.1", "LO3.2", "AI-CFT"):
                self.assertNotIn(token, blob, f"{iid}: forbidden reference {token!r}")

    def test_no_orphan_ilos(self) -> None:
        for iid, ilo in self.ilos.items():
            self.assertGreaterEqual(len(ilo["related_behaviours"]), 1, iid)

    def test_references_behaviour_ontology(self) -> None:
        self.assertEqual(
            self.ilo["behaviour_ontology_reference"],
            "framework/Observable_Behaviours.json",
        )
        self.assertNotIn("framework_version", self.ob)
        self.assertNotIn("behaviour_ontology_version", self.ilo)

    def test_concept_families_standardized(self) -> None:
        allowed = {
            "data_representation", "classification", "evaluation",
            "generalisation", "reasoning", "reflection",
        }
        for iid, ilo in self.ilos.items():
            self.assertIn(ilo["concept_family"], allowed, iid)
            self.assertIsInstance(ilo["instructional_sequence_order"], int)

    def test_no_version_stamps(self) -> None:
        self.assertNotIn("framework_version", self.ilo)
        self.assertNotIn("freeze", self.ilo)

    def test_milestone_summary_exists(self) -> None:
        report = REPO / "reports" / "milestone2_summary.md"
        validation = REPO / "reports" / "milestone2_validation.json"
        self.assertTrue(report.is_file())
        self.assertTrue(validation.is_file())
        dep = REPO / "framework" / "ILO_Dependency_Graph.json"
        self.assertTrue(dep.is_file())

    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_summary_generator_passes(self) -> None:
        gen = REPO / "scripts" / "generate_milestone2_summary.py"
        result = subprocess.run(
            [sys.executable, str(gen)],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_milestone3_mapping_artifact_name(self) -> None:
        self.assertEqual(
            self.ilo["terminology"].get("milestone3_mapping_artifact"),
            "Behaviour_to_ILO.json",
        )


if __name__ == "__main__":
    unittest.main()
