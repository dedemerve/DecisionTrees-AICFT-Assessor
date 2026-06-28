"""test_behaviour_to_ilo.py — Milestone 3 Behaviour → ILO inference mapping tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
MAP_PATH = REPO / "framework" / "Behaviour_to_ILO.json"
BUILDER = REPO / "scripts" / "build_behaviour_to_ilo.py"
VALIDATOR = REPO / "scripts" / "validate_behaviour_to_ilo.py"


class TestBehaviourToIlo(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        cls.mappings = cls.doc["mappings"]

    def _records(self, bid: str) -> list[dict]:
        return self.mappings[bid]["records"]

    def test_inference_layer(self) -> None:
        self.assertTrue(self.doc.get("inference_layer"))
        self.assertTrue(self.doc["confidence_policy"]["qualitative_only"])

    def test_no_numeric_confidence(self) -> None:
        blob = MAP_PATH.read_text()
        for bad in ('"mapping_confidence": 0.', '"mapping_confidence": 1'):
            self.assertNotIn(bad, blob)

    def test_all_behaviours_mapped(self) -> None:
        ob = json.loads((REPO / "framework" / "Observable_Behaviours.json").read_text())
        self.assertEqual(set(self.mappings), set(ob["behaviours"]))

    def test_each_behaviour_has_primary_and_rejected_structure(self) -> None:
        for bid, bundle in self.mappings.items():
            self.assertIn("records", bundle)
            self.assertIn("rejected_alternatives", bundle)
            roles = [r["mapping_role"] for r in bundle["records"]]
            if roles == ["diagnostic"]:
                continue
            primaries = [r for r in bundle["records"] if r["mapping_role"] == "primary"]
            self.assertEqual(len(primaries), 1, bid)
            for rej in bundle["rejected_alternatives"]:
                self.assertIn("reason_rejected", rej)

    def test_confidence_basis_present(self) -> None:
        for bid, bundle in self.mappings.items():
            for rec in bundle["records"]:
                self.assertIsInstance(rec["confidence_basis"], list)
                self.assertGreater(len(rec["confidence_basis"]), 0)
                self.assertIn(rec["mapping_confidence"], {"high", "moderate", "low", "baseline"})

    def test_roles_are_valid(self) -> None:
        allowed = {"primary", "secondary", "contextual", "diagnostic"}
        for bundle in self.mappings.values():
            for rec in bundle["records"]:
                self.assertIn(rec["mapping_role"], allowed)

    def test_bidirectional_ilo_consistency(self) -> None:
        ilo_data = json.loads((REPO / "framework" / "Learning_Objects.json").read_text())
        for iid, ilo in ilo_data["learning_objects"].items():
            for bid in ilo["related_behaviours"]:
                mapped = {r["ilo_id"] for r in self.mappings[bid]["records"]}
                self.assertIn(iid, mapped, f"{bid} -> {iid}")

    def test_analytics_reports_exist(self) -> None:
        report_dir = REPO / "reports" / "milestone3"
        for name in (
            "mapping_coverage_report.json",
            "construct_matrix.json",
            "cross_construct_matrix.json",
            "mapping_statistics.json",
        ):
            self.assertTrue((report_dir / name).is_file(), name)

    def test_validator_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(VALIDATOR), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_builder_check_passes(self) -> None:
        result = subprocess.run(
            [sys.executable, str(BUILDER), "--check"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)


if __name__ == "__main__":
    unittest.main()
