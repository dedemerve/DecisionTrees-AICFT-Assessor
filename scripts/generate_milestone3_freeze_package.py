#!/usr/bin/env python3
"""
generate_milestone3_freeze_package.py — Milestone 3 human summary for Behaviour→ILO mapping.

Legacy script name; writes reports/milestone3_summary.md only.

Usage:
  python scripts/generate_milestone3_freeze_package.py
  python scripts/generate_milestone3_freeze_package.py --apply-freeze
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "framework" / "Behaviour_to_ILO.json"
OB_PATH = REPO_ROOT / "framework" / "Observable_Behaviours.json"
ILO_PATH = REPO_ROOT / "framework" / "Learning_Objects.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_behaviour_to_ilo.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from milestone_reporting import (  # noqa: E402
    freeze_status_label,
    load_json,
    load_validation,
    run_quiet_script,
    write_summary,
)


def apply_freeze_metadata(mapping_doc: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    mapping_doc["freeze"] = {
        "status": "frozen",
        "version": "1.1",
        "frozen_at": now,
        "freeze_package_dir": "reports",
        "expert_review_status": "automated_review_complete; human_expert_review_pending",
        "change_policy": "major_version_required_for_semantic_changes",
        "inference_layer": True,
        "upstream_frozen_inputs": [
            "Observable_Behaviours.json@1.0",
            "Learning_Objects.json@1.0",
        ],
        "downstream_artifacts_locked": [
            "LO_to_Domain_Understanding.json",
            "Domain_to_AI_CFT.json",
            "Aggregation_Policy.json",
        ],
    }
    return mapping_doc


def write_summary_md(
    mapping_doc: dict[str, Any],
    validation: dict[str, Any],
    applying: bool,
) -> str:
    stats = validation.get("mapping_statistics", {})
    density = stats.get("mapping_density", {})
    roles = stats.get("role_ratios", {}).get("counts", {})
    cross = validation.get("cross_construct_matrix", {}).get("pair_count", 0)
    status = freeze_status_label(mapping_doc, applying=applying)

    lines = [
        "# Milestone 3 Summary",
        "",
        "## Behaviour → ILO Inference Mapping",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Behaviour_to_ILO.json` |",
        "| Schema | **1.1** (qualitative confidence only) |",
        f"| Freeze status | **{status}** |",
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
        "## Freeze decision",
        "",
    ])

    val_status = validation.get("status", "unknown")
    if val_status == "pass" and applying:
        lines.append(
            "**APPROVED:** Behaviour_to_ILO.json v1.1 is frozen. "
            "Milestone 4 may proceed with `Domain_Understanding.json` and `LO_to_Domain_Understanding.json` "
            "only — no new OB or ILO definitions without ontology version bump."
        )
    elif val_status == "pass":
        lines.append("**READY:** Run with `--apply-freeze` to write freeze metadata.")
    else:
        lines.append("**BLOCKED:** Resolve validation errors before freeze.")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 3 summary")
    parser.add_argument("--apply-freeze", action="store_true")
    args = parser.parse_args(argv)

    errors: list[str] = []
    ob_data = load_json(OB_PATH)
    ilo_data = load_json(ILO_PATH)
    mapping_doc = load_json(MAP_PATH)

    if ob_data.get("freeze", {}).get("status") != "frozen":
        errors.append("Observable_Behaviours.json must be frozen first")
    if ilo_data.get("freeze", {}).get("status") != "frozen":
        errors.append("Learning_Objects.json must be frozen first")
    if not mapping_doc.get("inference_layer"):
        errors.append("Behaviour_to_ILO must set inference_layer=true")
    if not mapping_doc.get("confidence_policy", {}).get("qualitative_only"):
        errors.append("Behaviour_to_ILO must use qualitative-only confidence policy")

    if run_quiet_script(VALIDATOR) != 0:
        errors.append("validate_behaviour_to_ilo.py failed")

    validation = load_validation(3)
    errors.extend(validation.get("errors", []))

    applying = args.apply_freeze and not errors
    summary_path = write_summary(3, write_summary_md(mapping_doc, validation, applying))

    if applying:
        MAP_PATH.write_text(
            json.dumps(apply_freeze_metadata(mapping_doc), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Freeze metadata applied to Behaviour_to_ILO.json")

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
