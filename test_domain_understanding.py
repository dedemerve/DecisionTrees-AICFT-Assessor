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
        self.assertEqual(self.domain_doc["domain_count"], 8)
        for did, dom in self.domains.items():
            self.assertEqual(dom["assessment_construct_type"], "emergent")
            self.assertIn("construct_definition", dom)
            self.assertIn("convergence_requirements", dom)
            self.assertIn("not_equivalent_to", dom)
            self.assertIn("construct_validation", dom)
            cv = dom["construct_validation"]
            for field in (
                "what_construct_represents",
                "supporting_evidence",
                "non_supporting_evidence",
                "not_formed_when",
                "confusable_with",
            ):
                self.assertIn(field, cv, f"{did}.{field}")
                if field != "what_construct_represents":
                    self.assertGreaterEqual(len(cv[field]), 2, f"{did}.{field}")
            self.assertGreaterEqual(len(dom["inclusion_criteria"]), 2)

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
        report_dir = REPO / "reports" / "milestone4"
        for name in (
            "domain_coverage_report.json",
            "domain_independence_matrix.json",
            "domain_stress_test.json",
            "construct_matrix.json",
            "cross_construct_matrix.json",
            "mapping_statistics.json",
            "milestone4_validation.json",
        ):
            self.assertTrue((report_dir / name).exists(), name)

    def test_domain_stress_test_passes(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(REPO / "scripts" / "run_domain_stress_test.py"), "--quiet"],
            cwd=REPO,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        report = json.loads((REPO / "reports" / "milestone4" / "domain_stress_test.json").read_text())
        self.assertEqual(report["status"], "pass")

    def test_domain_independence_matrix(self) -> None:
        matrix = json.loads(
            (REPO / "reports" / "milestone4" / "domain_independence_matrix.json").read_text()
        )
        self.assertGreater(matrix["pair_count"], 0)
        threshold_tuning = [
            p for p in matrix["pairs"]
            if "THRESHOLD" in p["domain_a"] and "PARAMETER" in p["domain_b"]
            or "PARAMETER" in p["domain_a"] and "THRESHOLD" in p["domain_b"]
        ]
        self.assertEqual(len(threshold_tuning), 1)
        pair = threshold_tuning[0]
        self.assertEqual(pair["overlap_risk"], "high")
        self.assertTrue(pair["discriminating_criteria"])
        shared = max(pair["shared_mapped_ilo_count"], pair["shared_indicative_ilo_count"])
        self.assertGreaterEqual(shared, 1)

    def test_builders_succeed(self) -> None:
        for script in (BUILD_DOMAIN, BUILD_MAP):
            proc = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
