"""test_observable_behaviours.py — Milestone 1 ontology validation tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
ONTOLOGY_PATH = REPO / "framework" / "Observable_Behaviours.json"
VALIDATOR = REPO / "scripts" / "validate_observable_behaviours.py"


class TestObservableBehaviours(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data = json.loads(ONTOLOGY_PATH.read_text(encoding="utf-8"))
        cls.behaviours = cls.data["behaviours"]

    def test_ontology_file_exists(self) -> None:
        self.assertTrue(ONTOLOGY_PATH.is_file())

    def test_behaviour_count(self) -> None:
        self.assertGreaterEqual(len(self.behaviours), 24)

    def test_all_construct_dimensions_represented(self) -> None:
        dims = {b["construct_dimension"] for b in self.behaviours.values()}
        self.assertEqual(
            dims,
            {"conceptual", "procedural", "strategic", "reflective"},
        )

    def test_no_worksheet_references(self) -> None:
        blob = ONTOLOGY_PATH.read_text(encoding="utf-8")
        for token in ("WS1", "WS4", "WS11", "WS_DT", "DT_A_Q"):
            self.assertNotIn(token, blob, f"worksheet reference {token!r} found")

    def test_no_aicft_references(self) -> None:
        blob = ONTOLOGY_PATH.read_text(encoding="utf-8").lower()
        for token in ("ai-cft", "lo3.", "acquire", "deepen"):
            self.assertNotIn(token, blob, f"AI-CFT reference {token!r} found")

    def test_required_fields_on_every_behaviour(self) -> None:
        required = {
            "id", "title", "description", "construct_dimension", "cognitive_process",
            "knowledge_type", "possible_sources", "required_evidence",
            "possible_misconceptions", "related_behaviours", "difficulty",
            "confidence_requirements", "evidence_strength_ceiling",
        }
        for bid, beh in self.behaviours.items():
            missing = required - beh.keys()
            self.assertFalse(missing, f"{bid} missing {missing}")

    def test_related_behaviours_resolve(self) -> None:
        ids = set(self.behaviours)
        for bid, beh in self.behaviours.items():
            for rel in beh["related_behaviours"]:
                self.assertIn(rel, ids, f"{bid} -> {rel} undefined")

    def test_baseline_behaviour_has_weak_ceiling(self) -> None:
        baseline = self.behaviours.get("OB_REF_004")
        self.assertIsNotNone(baseline)
        self.assertEqual(baseline["evidence_strength_ceiling"], "weak")

    def test_validator_script_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"validator failed:\n{result.stdout}\n{result.stderr}",
        )

    def test_ontology_is_frozen_v1(self) -> None:
        freeze = self.data.get("freeze", {})
        self.assertEqual(freeze.get("status"), "frozen")
        self.assertEqual(freeze.get("version"), "1.0")
        self.assertEqual(self.data.get("framework_version"), "1.0")

    def test_freeze_package_exists(self) -> None:
        freeze_report = REPO / "reports" / "milestone1_freeze" / "milestone1_freeze_report.md"
        self.assertTrue(freeze_report.is_file())
        dep_graph = REPO / "framework" / "Behaviour_Dependency_Graph.json"
        self.assertTrue(dep_graph.is_file())

    def test_freeze_package_generator_passes(self) -> None:
        generator = REPO / "scripts" / "generate_milestone1_freeze_package.py"
        result = subprocess.run(
            [sys.executable, str(generator)],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
