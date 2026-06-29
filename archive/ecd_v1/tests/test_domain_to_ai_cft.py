"""test_domain_to_ai_cft.py — Milestone 5 interpretive policy tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).parent
POLICY_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"
BUILDER = REPO / "scripts" / "build_domain_to_ai_cft.py"
VALIDATOR = REPO / "scripts" / "validate_domain_to_ai_cft.py"
STRESS = REPO / "scripts" / "run_ai_cft_interpretive_stress_test.py"


class TestDomainToAiCft(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.doc = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        cls.policies = cls.doc["policies"]

    def test_is_interpretive_policy_not_mapping(self) -> None:
        self.assertEqual(self.doc["artifact"], "domain_to_ai_cft_interpretive_policy")
        import re
        blob = POLICY_PATH.read_text()
        self.assertIsNone(re.search(r'"maps_to"\s*:', blob))
        self.assertIn("interpretive_recommendation", json.dumps(self.doc["terminology"]))

    def test_design_constraint_present(self) -> None:
        dc = self.doc["design_constraint"]
        self.assertIn("does not represent an AI-CFT competency", dc)
        self.assertIn("provisional interpretation", dc)

    def test_qualitative_confidence_only(self) -> None:
        self.assertTrue(self.doc["confidence_policy"]["qualitative_only"])
        self.assertIn("very_weak", self.doc["confidence_policy"]["allowed_levels"])
        self.assertNotIn('"allowed_confidence": 0.', POLICY_PATH.read_text())

    def test_all_domains_have_policies(self) -> None:
        domains = json.loads((REPO / "framework" / "Domain_Understanding.json").read_text())["domains"]
        self.assertEqual(set(self.policies), set(domains))

    def test_contribution_schema(self) -> None:
        for did, pol in self.policies.items():
            self.assertGreaterEqual(len(pol["construct_limitations"]), 2, did)
            for c in pol["contributions"]:
                self.assertTrue(c["researcher_review_required"], did)
                self.assertGreaterEqual(len(c["insufficient_when"]), 2, did)
                self.assertGreaterEqual(len(c["never_implies"]), 2, did)
                self.assertIn(c["interpretation_verb"], ("may_contribute_to", "may_indicate", "supports", "contributes"))
                self.assertNotIn("maps_to", c)

    def test_validator_and_stress_pass(self) -> None:
        for script in (VALIDATOR, STRESS):
            proc = subprocess.run([sys.executable, str(script)], cwd=REPO, capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_builder_succeeds(self) -> None:
        proc = subprocess.run([sys.executable, str(BUILDER)], cwd=REPO, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)


if __name__ == "__main__":
    unittest.main()
