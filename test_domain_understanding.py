"""test_domain_understanding.py — Milestone 4 Domain Understanding tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
MAP_PATH = REPO / "framework" / "LO_to_Domain_Understanding.json"
BUILD_DOMAIN = REPO / "scripts" / "build_domain_understanding.py"
BUILD_MAP = REPO / "scripts" / "build_lo_to_domain_understanding.py"
VALIDATOR = REPO / "scripts" / "validate_domain_understanding.py"


class TestDomainUnderstanding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.domain_doc = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
        cls.map_doc = json.loads(MAP_PATH.read_text(encoding="utf-8"))
        cls.domains = cls.domain_doc["domains"]
        cls.mappings = cls.map_doc["mappings"]

    def test_design_constraint_present(self) -> None:
        dc = self.domain_doc.get("design_constraint", "")
        self.assertIn("emergent disciplinary understanding", dc)
        self.assertIn("not curriculum topics", dc.lower())

    def test_domains_are_emergent_constructs(self) -> None:
        self.assertEqual(self.domain_doc["domain_count"], 7)
        for did, dom in self.domains.items():
            self.assertEqual(dom["assessment_construct_type"], "emergent")
            self.assertIn("construct_definition", dom)
            self.assertIn("convergence_requirements", dom)
            self.assertIn("not_equivalent_to", dom)
            self.assertIn("evidence_criteria", dom)
            ec = dom["evidence_criteria"]
            for field in ("counts", "does_not_count"):
                self.assertIn(field, ec, f"{did}.{field}")
                self.assertGreaterEqual(len(ec[field]), 2, f"{did}.{field}")

    def test_no_ilo_folder_domain_names(self) -> None:
        forbidden = {"ILO_THRESHOLD", "ILO_FEATURE", "ILO_RULE", "ILO_DECISION_TREE"}
        for did in self.domains:
            self.assertNotIn(did, forbidden)
            self.assertTrue(did.startswith("DU_"))

    def test_all_ilos_mapped_to_domains(self) -> None:
        ilos = json.loads((REPO / "framework" / "Learning_Objects.json").read_text())["learning_objects"]
        self.assertEqual(set(self.mappings), set(ilos))

    def test_qualitative_confidence_only(self) -> None:
        blob = MAP_PATH.read_text()
        self.assertTrue(self.map_doc["confidence_policy"]["qualitative_only"])
        self.assertNotIn('"mapping_confidence": 0.', blob)

    def test_each_ilo_primary_or_diagnostic(self) -> None:
        for iid, bundle in self.mappings.items():
            roles = [r["mapping_role"] for r in bundle["records"]]
            if roles == ["diagnostic"]:
                continue
            primaries = [r for r in bundle["records"] if r["mapping_role"] == "primary"]
            self.assertEqual(len(primaries), 1, iid)

    def test_rejected_alternatives_have_reasons(self) -> None:
        for bundle in self.mappings.values():
            for rej in bundle.get("rejected_alternatives", []):
                self.assertIn("reason_rejected", rej)
                self.assertGreaterEqual(len(rej["reason_rejected"]), 16)

    def test_validator_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_analytics_reports_exist(self) -> None:
        validation_path = REPO / "reports" / "milestone4_validation.json"
        self.assertTrue(validation_path.is_file())
        validation = json.loads(validation_path.read_text())
        for key in (
            "domain_coverage_report",
            "domain_independence_matrix",
            "construct_matrix",
            "cross_construct_matrix",
            "mapping_statistics",
        ):
            self.assertIn(key, validation, key)

    def test_domain_stress_test_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "run_domain_stress_test.py"), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        validation = json.loads((REPO / "reports" / "milestone4_validation.json").read_text())
        self.assertEqual(validation["stress_test"]["status"], "pass")

    def test_domain_independence_matrix(self) -> None:
        validation = json.loads((REPO / "reports" / "milestone4_validation.json").read_text())
        matrix = validation["domain_independence_matrix"]
        self.assertGreater(matrix["pair_count"], 0)
        domain_ids = set(self.domain_doc["domains"])
        self.assertIn("DU_THRESHOLD_AND_PARAMETER_REASONING", domain_ids)
        self.assertEqual(len(domain_ids), 7)
        class_tree = [
            p for p in matrix["pairs"]
            if "CLASSIFICATION" in p["domain_a"] and "TREE_STRUCTURE" in p["domain_b"]
            or "TREE_STRUCTURE" in p["domain_a"] and "CLASSIFICATION" in p["domain_b"]
        ]
        self.assertEqual(len(class_tree), 1)
        pair = class_tree[0]
        self.assertEqual(pair["overlap_risk"], "moderate")

    def test_builders_succeed(self) -> None:
        for script in (BUILD_DOMAIN, BUILD_MAP):
            proc = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
