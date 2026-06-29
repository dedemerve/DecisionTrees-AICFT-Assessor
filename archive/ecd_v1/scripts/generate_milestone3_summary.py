#!/usr/bin/env python3
"""
generate_milestone3_summary.py — Milestone 3 human summary for Behaviour→ILO mapping.

Writes reports/milestone3_summary.md only.

Usage:
  python scripts/generate_milestone3_summary.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "framework" / "Behaviour_to_ILO.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_behaviour_to_ilo.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from milestone_reporting import (  # noqa: E402
    validation_status_label,
    load_json,
    load_validation,
    run_quiet_script,
    write_summary,
)


def write_summary_md(
    mapping_doc: dict[str, Any],
    validation: dict[str, Any],
) -> str:
    stats = validation.get("mapping_statistics", {})
    density = stats.get("mapping_density", {})
    roles = stats.get("role_ratios", {}).get("counts", {})
    cross = validation.get("cross_construct_matrix", {}).get("pair_count", 0)
    val_label = validation_status_label(validation.get("status"))

    lines = [
        "# Milestone 3 Summary",
        "",
        "## Behaviour → ILO Inference Mapping",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Behaviour_to_ILO.json` |",
        "| Schema | **1.1** (qualitative confidence only) |",
        f"| Validation status | **{val_label}** |",
        f"| Accepted pairs | {density.get('accepted_pair_count', mapping_doc.get('mapping_count', '?'))} |",
        f"| Behaviours covered | {density.get('behaviour_count', mapping_doc.get('behaviour_count', 28))}/28 |",
        f"| Rejected alternatives | {density.get('rejected_alternative_count', '?')} |",
        f"| Cross-construct pairs | {cross} |",
        "",
        "## Scientific significance",
        "",
        "> First inference layer of the framework: assessment theory becomes operational mapping "
        "from Observable Behaviours to Instructional Learning Objects with explicit roles, "
        "rejected alternatives, and counter-evidence.",
        "",
        "## Confidence policy",
        "",
        "- Qualitative levels only: `high`, `moderate`, `low`, `baseline`",
        "- Each record requires `confidence_basis[]`",
        "- Numeric quantization deferred to `Confidence_Model.json`",
        "- Ad-hoc numeric confidence **prohibited**",
        "",
        "## Mapping roles",
        "",
        "| Role | Count |",
        "|------|-------|",
    ]
    for role in ("primary", "secondary", "contextual", "diagnostic"):
        lines.append(f"| {role} | {roles.get(role, 0)} |")

    lines.extend([
        "",
        "## Automated validation",
        "",
        "- `reports/milestone3_validation.json` — single validation artifact",
        "",
        "## Remaining risks",
        "",
        "1. Human expert agreement on cross-construct bridges pending.",
        "2. Counter-evidence templates require calibration against pilot portfolios.",
        "3. `Confidence_Model.json` not yet authored — no numeric aggregation.",
        "",
        "## Accepted limitations",
        "",
        "- Some ILOs supported by only one behaviour (underrepresentation flagged in coverage report).",
        "- `ILO_PRIOR_BELIEF` mapped as diagnostic-only baseline.",
        "- Rejected alternatives documented for high-ambiguity behaviours only (9/28).",
        "",
        "## Expert review status",
        "",
        "| Review | Status |",
        "|--------|--------|",
        "| Automated validation | complete |",
        "| Human expert review | **pending** |",
        "",
        "## Validation summary",
        "",
        f"Automated validation (`milestone3_validation.json`): **{validation.get('status', 'unknown')}**.",
        "",
    ])

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 3 summary")
    args = parser.parse_args(argv)

    errors: list[str] = []
    mapping_doc = load_json(MAP_PATH)

    if not mapping_doc.get("inference_layer"):
        errors.append("Behaviour_to_ILO must set inference_layer=true")
    if not mapping_doc.get("confidence_policy", {}).get("qualitative_only"):
        errors.append("Behaviour_to_ILO must use qualitative-only confidence policy")

    if run_quiet_script(VALIDATOR) != 0:
        errors.append("validate_behaviour_to_ilo.py failed")

    validation = load_validation(3)
    errors.extend(validation.get("errors", []))

    summary_path = write_summary(3, write_summary_md(mapping_doc, validation))

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
