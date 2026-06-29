#!/usr/bin/env python3
"""
generate_milestone4_summary.py — Milestone 4 human summary for Domain Understanding.

Writes reports/milestone4_summary.md only.

Usage:
  python scripts/generate_milestone4_summary.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_PATH = REPO_ROOT / "framework" / "Domain_Understanding.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_domain_understanding.py"
STRESS_TEST = REPO_ROOT / "scripts" / "run_domain_stress_test.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from milestone_reporting import (  # noqa: E402
    validation_status_label,
    load_json,
    load_validation,
    run_quiet_script,
    write_summary,
)

MILESTONE5_DESIGN_CONSTRAINT = (
    "Domain_to_AI_CFT must not be implemented as a deterministic lookup table. AI-CFT claims are "
    "interpretive, provisional, and evidence-weighted. Each mapping must specify the theoretical "
    "rationale, minimum evidence requirements, convergence criteria, contradiction conditions, "
    "confidence ceiling, and explicit situations where escalation to the AI-CFT level is prohibited. "
    "No Domain may map directly to an AI-CFT competency solely because it is present. Domain evidence "
    "must satisfy sufficiency and coherence requirements before an AI-CFT interpretation becomes available."
)


def write_summary_md(
    domain_doc: dict[str, Any],
    validation: dict[str, Any],
    stress: dict[str, Any],
) -> str:
    density = validation.get("mapping_statistics", {}).get("mapping_density", {})
    independence = validation.get("domain_independence_matrix", {})
    val_label = validation_status_label(validation.get("status"))

    lines = [
        "# Milestone 4 Summary",
        "",
        "## Domain Understanding Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifacts | `Domain_Understanding.json`, `LO_to_Domain_Understanding.json` |",
        "| Version | **1.0** |",
        f"| Validation status | **{val_label}** |",
        f"| Domains | {domain_doc.get('domain_count', 8)} emergent assessment constructs |",
        f"| ILO→Domain pairs | {density.get('accepted_pair_count', '?')} |",
        f"| Domain stress tests | {stress.get('passed', '?')}/{stress.get('test_count', 5)} passed |",
        "",
        "## Methodological contribution",
        "",
        "> You are not assessing AI-CFT directly. You are assessing Decision Tree understanding "
        "through an Evidence-Centered, multimodal, explainable assessment framework, and only then "
        "deriving provisional AI-CFT interpretations through a constrained, human-governed inferential process.",
        "",
        "## Construct validation gate",
        "",
        "Each domain includes `construct_validation` with:",
        "",
        "- what_construct_represents",
        "- supporting_evidence / non_supporting_evidence",
        "- not_formed_when",
        "- confusable_with",
        "",
        "## Domain Independence Matrix",
        "",
        f"- Pairs analyzed: {independence.get('pair_count', 28)}",
        f"- High/moderate overlap risk: {independence.get('high_or_moderate_risk_pairs', '?')}",
        "",
        "### Top overlap pairs",
        "",
        "| Domain A | Domain B | Shared ILO | Risk |",
        "|----------|----------|------------|------|",
    ]
    for row in independence.get("pairs", [])[:5]:
        lines.append(
            f"| {row['domain_a_title']} | {row['domain_b_title']} | "
            f"{max(row['shared_mapped_ilo_count'], row['shared_indicative_ilo_count'])} | {row['overlap_risk']} |"
        )

    lines.extend([
        "",
        "## Domain Stress Test",
        "",
        "| Test | Scenario | Status |",
        "|------|----------|--------|",
    ])
    for t in stress.get("tests", []):
        lines.append(f"| {t['test_id']} | {t['title']} | {'PASS' if t['pass'] else 'FAIL'} |")

    lines.extend([
        "",
        "## Automated validation",
        "",
        "- `reports/milestone4_validation.json` — single validation artifact (includes stress test when run)",
        "",
        "## Remaining risks",
        "",
        "1. Human expert domain boundary agreement pending.",
        "2. `DU_GENERALISATION` partial ILO proxy coverage (accepted limitation).",
        "3. Domain synthesis engine is provisional until `Aggregation_Policy.json` is authored.",
        "",
        "## Milestone 5 design constraint",
        "",
        "Domain_to_AI_CFT must follow the design constraint in `Domain_Understanding.json`:",
        "",
        f"> {MILESTONE5_DESIGN_CONSTRAINT}",
        "",
        "## Expert review status",
        "",
        "| Review | Status |",
        "|--------|--------|",
        "| Automated validation | complete |",
        "| Domain stress test | complete |",
        "| Independence matrix | complete |",
        "| Human expert review | **pending** |",
        "",
        "## Validation summary",
        "",
        "| Check | Status |",
        "|-------|--------|",
        f"| `milestone4_validation.json` | {validation.get('status', 'unknown')} |",
        f"| Domain stress test | {stress.get('status', 'unknown')} |",
        "",
    ])

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 4 summary")
    args = parser.parse_args(argv)

    errors: list[str] = []

    if run_quiet_script(VALIDATOR) != 0:
        errors.append("validate_domain_understanding.py failed")
    if run_quiet_script(STRESS_TEST) != 0:
        errors.append("run_domain_stress_test.py failed")

    validation = load_validation(4)
    stress = validation.get("stress_test", {})
    if not stress:
        errors.append("run_domain_stress_test.py must populate stress_test in milestone4_validation.json")
    errors.extend(validation.get("errors", []))

    domain_doc = load_json(DOMAIN_PATH)

    for did, dom in domain_doc.get("domains", {}).items():
        if "construct_validation" not in dom:
            errors.append(f"{did}: missing construct_validation")

    summary_path = write_summary(4, write_summary_md(domain_doc, validation, stress))

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
