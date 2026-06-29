#!/usr/bin/env python3
"""generate_milestone5_summary.py — Milestone 5 human summary for Domain→AI-CFT policy.

Writes reports/milestone5_summary.md only.

Usage:
  python scripts/generate_milestone5_summary.py
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"
VALIDATOR = REPO / "scripts" / "validate_domain_to_ai_cft.py"
STRESS = REPO / "scripts" / "run_ai_cft_interpretive_stress_test.py"

sys.path.insert(0, str(REPO / "scripts"))
from milestone_reporting import (  # noqa: E402
    load_json,
    load_validation,
    run_quiet_script,
    validation_status_label,
    write_summary,
)


def write_report(
    doc: dict[str, Any],
    validation: dict[str, Any],
    stress: dict[str, Any],
) -> str:
    stats = validation.get("interpretation_statistics", {})
    val_label = validation_status_label(validation.get("status"))
    lines = [
        "# Milestone 5 Summary",
        "",
        "## Domain → AI-CFT Interpretive Policy",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Domain_to_AI_CFT.json` |",
        "| Type | **Interpretive policy** (not deterministic mapping) |",
        "| Version | **1.0** |",
        f"| Validation status | **{val_label}** |",
        f"| Domain policies | {doc.get('domain_policy_count', 8)} |",
        f"| Contribution records | {stats.get('contribution_count', doc.get('contribution_count', '?'))} |",
        f"| Interpretive stress tests | {stress.get('passed', '?')}/{stress.get('test_count', 6)} passed |",
        "",
        "## Core design constraint",
        "",
        f"> {doc.get('design_constraint', '')}",
        "",
        "## Claim chain",
        "",
        "Evidence → Behaviour → ILO → Domain → **Interpretive Recommendation** → Researcher → AI-CFT Claim",
        "",
        "The framework does **not** output final AI-CFT competencies. It outputs provisional, evidence-weighted interpretive recommendations for researcher governance.",
        "",
        "## Prohibited patterns",
        "",
        "- `maps_to` deterministic lookup",
        "- `is_final: true` automatic claims",
        "- Domain presence implying AI-CFT without convergence",
        "",
        "## Automated validation",
        "",
        "- `reports/milestone5_validation.json` — single validation artifact (includes stress test when run)",
        "",
        "## Theory phase complete",
        "",
        "With Milestone 5 validated, the framework theory chain is complete. New theory artifacts require an explicit schema revision. Next phase:",
        "",
        "1. Remodel WS1–WS11 bundles to new architecture",
        "2. Implement OCR → Evidence → … → interpretive recommendation pipeline",
        "3. Pilot on real student portfolios",
        "4. Reliability and validity analyses",
        "",
        "## Validation summary",
        "",
        "| Check | Status |",
        "|-------|--------|",
        f"| `milestone5_validation.json` | {validation.get('status', 'unknown')} |",
        f"| Interpretive stress test | {stress.get('status', 'unknown')} |",
        "",
    ]

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    args = parser.parse_args(argv)

    errors: list[str] = []
    if run_quiet_script(VALIDATOR) != 0:
        errors.append(f"{VALIDATOR.name} failed")
    if run_quiet_script(STRESS) != 0:
        errors.append(f"{STRESS.name} failed")

    validation = load_validation(5)
    stress = validation.get("stress_test", {})
    if not stress:
        errors.append("run_ai_cft_interpretive_stress_test.py must populate stress_test in milestone5_validation.json")
    errors.extend(validation.get("errors", []))

    doc = load_json(POLICY_PATH)

    if re.search(r'"maps_to"\s*:', POLICY_PATH.read_text()):
        errors.append("maps_to field prohibited in artifact")

    summary_path = write_summary(5, write_report(doc, validation, stress))

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
