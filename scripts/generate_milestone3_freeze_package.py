#!/usr/bin/env python3
"""
generate_milestone3_freeze_package.py — Milestone 3 freeze verification for Behaviour→ILO inference.

Usage:
  python scripts/generate_milestone3_freeze_package.py
  python scripts/generate_milestone3_freeze_package.py --apply-freeze
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = REPO_ROOT / "framework" / "Behaviour_to_ILO.json"
OB_PATH = REPO_ROOT / "framework" / "Observable_Behaviours.json"
ILO_PATH = REPO_ROOT / "framework" / "Learning_Objects.json"
M3_REPORTS = REPO_ROOT / "reports" / "milestone3"
OUTPUT_DIR = REPO_ROOT / "reports" / "milestone3_freeze"
VALIDATOR = REPO_ROOT / "scripts" / "validate_behaviour_to_ilo.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_validator() -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "--quiet"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    validation_path = M3_REPORTS / "milestone3_validation.json"
    validation = load_json(validation_path) if validation_path.exists() else {}
    return proc.returncode, validation


def apply_freeze_metadata(mapping_doc: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    mapping_doc["freeze"] = {
        "status": "frozen",
        "version": "1.1",
        "frozen_at": now,
        "freeze_package_dir": "reports/milestone3_freeze",
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


def write_freeze_report_md(
    mapping_doc: dict[str, Any],
    validation: dict[str, Any],
    apply_freeze: bool,
) -> str:
    stats_path = M3_REPORTS / "mapping_statistics.json"
    stats = load_json(stats_path) if stats_path.exists() else {}
    density = stats.get("mapping_density", {})
    roles = stats.get("role_ratios", {}).get("counts", {})
    cross = stats.get("cross_construct_pair_count", validation.get("analytics_summary", {}).get("cross_construct_pairs", 0))

    lines = [
        "# Milestone 3 Freeze Report",
        "",
        "## Behaviour → ILO Inference Mapping",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Behaviour_to_ILO.json` |",
        "| Schema | **1.1** (qualitative confidence only) |",
        f"| Freeze status | **{'FROZEN' if apply_freeze else 'PENDING_APPLY'}** |",
        f"| Generated | {datetime.now(timezone.utc).isoformat()} |",
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
        "## Automated analytics (freeze package)",
        "",
        "- `mapping_coverage_report.json` — ILO → behaviour coverage",
        "- `construct_matrix.json` — behaviour × ILO dimension matrix",
        "- `cross_construct_matrix.json` — cross-dimension pairs with rationale",
        "- `mapping_statistics.json` — density, role ratios, counter/rejected stats",
        "- `milestone3_validation.json` — validation summary",
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
        "| Analytics reports | complete |",
        "| Human expert review | **pending** |",
        "",
        "## Freeze decision",
        "",
    ])

    val_status = validation.get("status", "unknown")
    if val_status == "pass" and apply_freeze:
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


def copy_reports(output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in (
        "mapping_coverage_report.json",
        "construct_matrix.json",
        "cross_construct_matrix.json",
        "mapping_statistics.json",
        "milestone3_validation.json",
    ):
        src = M3_REPORTS / name
        if src.exists():
            shutil.copy2(src, output_dir / name)
            copied.append(name)
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 3 freeze package")
    parser.add_argument("--apply-freeze", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    errors: list[str] = []
    ob_data = load_json(OB_PATH)
    ilo_data = load_json(ILO_PATH)
    mapping_doc = load_json(MAP_PATH)

    if ob_data.get("freeze", {}).get("status") != "frozen":
        errors.append("Observable_Behaviours.json must be frozen first")
    if ilo_data.get("freeze", {}).get("status") != "frozen":
        errors.append("Learning_Objects.json must be frozen first")
    if mapping_doc.get("schema_version") != "1.1":
        errors.append(f"Behaviour_to_ILO schema must be 1.1, got {mapping_doc.get('schema_version')!r}")
    if not mapping_doc.get("confidence_policy", {}).get("qualitative_only"):
        errors.append("Behaviour_to_ILO must use qualitative-only confidence policy")

    val_rc, validation = run_validator()
    if val_rc != 0:
        errors.append("validate_behaviour_to_ilo.py failed")
        for e in validation.get("errors", []):
            errors.append(f"  validator: {e}")

    copied = copy_reports(args.output_dir)
    if len(copied) < 5:
        errors.append(f"incomplete milestone3 reports copied ({len(copied)}/5)")

    report = write_freeze_report_md(mapping_doc, validation, args.apply_freeze and not errors)
    (args.output_dir / "milestone3_freeze_report.md").write_text(report, encoding="utf-8")

    freeze_summary = {
        "milestone": 3,
        "artifact": "Behaviour_to_ILO.json",
        "schema_version": mapping_doc.get("schema_version"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation.get("status"),
        "errors": errors,
        "reports_copied": copied,
        "pass": not errors,
    }
    (args.output_dir / "freeze_verification.json").write_text(
        json.dumps(freeze_summary, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.apply_freeze and not errors:
        updated = apply_freeze_metadata(mapping_doc)
        MAP_PATH.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Freeze metadata applied to Behaviour_to_ILO.json")

    print(f"Freeze package: {args.output_dir}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
