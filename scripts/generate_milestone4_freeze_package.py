#!/usr/bin/env python3
"""
generate_milestone4_freeze_package.py — Milestone 4 freeze verification for Domain Understanding.

Requires: validation pass, domain stress test pass, upstream M3 frozen.

Usage:
  python scripts/generate_milestone4_freeze_package.py
  python scripts/generate_milestone4_freeze_package.py --apply-freeze
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
DOMAIN_PATH = REPO_ROOT / "framework" / "Domain_Understanding.json"
MAP_PATH = REPO_ROOT / "framework" / "LO_to_Domain_Understanding.json"
B2I_PATH = REPO_ROOT / "framework" / "Behaviour_to_ILO.json"
M4_REPORTS = REPO_ROOT / "reports" / "milestone4"
OUTPUT_DIR = REPO_ROOT / "reports" / "milestone4_freeze"
VALIDATOR = REPO_ROOT / "scripts" / "validate_domain_understanding.py"
STRESS_TEST = REPO_ROOT / "scripts" / "run_domain_stress_test.py"

MILESTONE5_DESIGN_CONSTRAINT = (
    "Domain_to_AI_CFT must not be implemented as a deterministic lookup table. AI-CFT claims are "
    "interpretive, provisional, and evidence-weighted. Each mapping must specify the theoretical "
    "rationale, minimum evidence requirements, convergence criteria, contradiction conditions, "
    "confidence ceiling, and explicit situations where escalation to the AI-CFT level is prohibited. "
    "No Domain may map directly to an AI-CFT competency solely because it is present. Domain evidence "
    "must satisfy sufficiency and coherence requirements before an AI-CFT interpretation becomes available."
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def run_script(script: Path) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, str(script), "--quiet"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, {}


def apply_freeze_metadata(domain_doc: dict[str, Any], map_doc: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    now = datetime.now(timezone.utc).isoformat()
    freeze_block = {
        "status": "frozen",
        "version": "1.0",
        "frozen_at": now,
        "freeze_package_dir": "reports/milestone4_freeze",
        "expert_review_status": "automated_review_complete; domain_stress_test_passed; human_expert_review_pending",
        "change_policy": "major_version_required_for_semantic_changes",
        "inference_layer": True,
        "upstream_frozen_inputs": [
            "Observable_Behaviours.json@1.0",
            "Learning_Objects.json@1.0",
            "Behaviour_to_ILO.json@1.1",
        ],
        "downstream_artifacts_locked": [
            "Domain_to_AI_CFT.json",
            "Aggregation_Policy.json",
        ],
        "milestone5_design_constraint": MILESTONE5_DESIGN_CONSTRAINT,
    }
    domain_doc["freeze"] = {**freeze_block, "artifact": "domain_understanding_ontology"}
    map_doc["freeze"] = {**freeze_block, "artifact": "ilo_to_domain_understanding_mapping"}
    return domain_doc, map_doc


def write_freeze_report_md(
    domain_doc: dict[str, Any],
    validation: dict[str, Any],
    stress: dict[str, Any],
    independence: dict[str, Any],
    apply_freeze: bool,
) -> str:
    stats = load_json(M4_REPORTS / "mapping_statistics.json") if (M4_REPORTS / "mapping_statistics.json").exists() else {}
    density = stats.get("mapping_density", {})

    lines = [
        "# Milestone 4 Freeze Report",
        "",
        "## Domain Understanding Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifacts | `Domain_Understanding.json`, `LO_to_Domain_Understanding.json` |",
        "| Version | **1.0** |",
        f"| Freeze status | **{'FROZEN' if apply_freeze else 'PENDING_APPLY'}** |",
        f"| Generated | {datetime.now(timezone.utc).isoformat()} |",
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
        "- Full matrix: `domain_independence_matrix.json`",
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
        "## Automated analytics (freeze package)",
        "",
        "- `domain_coverage_report.json`",
        "- `domain_independence_matrix.json`",
        "- `domain_stress_test.json`",
        "- `construct_matrix.json`",
        "- `cross_construct_matrix.json`",
        "- `mapping_statistics.json`",
        "- `milestone4_validation.json`",
        "",
        "## Remaining risks",
        "",
        "1. Human expert domain boundary agreement pending.",
        "2. `DU_GENERALISATION` partial ILO proxy coverage (v1.0 accepted limitation).",
        "3. Domain synthesis engine is provisional until `Aggregation_Policy.json` is authored.",
        "",
        "## Milestone 5 gate (not started)",
        "",
        "Domain_to_AI_CFT must follow the design constraint recorded in freeze metadata:",
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
        "## Freeze decision",
        "",
    ])

    val_ok = validation.get("status") == "pass"
    stress_ok = stress.get("status") == "pass"
    if val_ok and stress_ok and apply_freeze:
        lines.append(
            "**APPROVED:** Domain Understanding v1.0 and LO_to_Domain_Understanding v1.0 are frozen. "
            "Milestone 5 (`Domain_to_AI_CFT.json`) may proceed only under the recorded design constraint."
        )
    elif val_ok and stress_ok:
        lines.append("**READY:** Run with `--apply-freeze` to write freeze metadata.")
    else:
        lines.append("**BLOCKED:** Resolve validation or stress test failures.")

    return "\n".join(lines) + "\n"


def copy_reports(output_dir: Path) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in (
        "domain_coverage_report.json",
        "domain_independence_matrix.json",
        "domain_stress_test.json",
        "construct_matrix.json",
        "cross_construct_matrix.json",
        "mapping_statistics.json",
        "milestone4_validation.json",
    ):
        src = M4_REPORTS / name
        if src.exists():
            shutil.copy2(src, output_dir / name)
            copied.append(name)
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 4 freeze package")
    parser.add_argument("--apply-freeze", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    errors: list[str] = []
    b2i = load_json(B2I_PATH)
    if b2i.get("freeze", {}).get("status") != "frozen":
        errors.append("Behaviour_to_ILO.json must be frozen first")

    val_rc, _ = run_script(VALIDATOR)
    stress_rc, _ = run_script(STRESS_TEST)
    validation = load_json(M4_REPORTS / "milestone4_validation.json")
    stress = load_json(M4_REPORTS / "domain_stress_test.json")
    independence = load_json(M4_REPORTS / "domain_independence_matrix.json")

    if val_rc != 0:
        errors.append("validate_domain_understanding.py failed")
    if stress_rc != 0:
        errors.append("run_domain_stress_test.py failed")

    domain_doc = load_json(DOMAIN_PATH)
    map_doc = load_json(MAP_PATH)

    for did, dom in domain_doc.get("domains", {}).items():
        if "construct_validation" not in dom:
            errors.append(f"{did}: missing construct_validation")

    copied = copy_reports(args.output_dir)
    if len(copied) < 7:
        errors.append(f"incomplete milestone4 reports copied ({len(copied)}/7)")

    report = write_freeze_report_md(
        domain_doc, validation, stress, independence, args.apply_freeze and not errors,
    )
    (args.output_dir / "milestone4_freeze_report.md").write_text(report, encoding="utf-8")

    freeze_summary = {
        "milestone": 4,
        "artifacts": ["Domain_Understanding.json", "LO_to_Domain_Understanding.json"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "validation_status": validation.get("status"),
        "stress_test_status": stress.get("status"),
        "errors": errors,
        "reports_copied": copied,
        "pass": not errors,
    }
    (args.output_dir / "freeze_verification.json").write_text(
        json.dumps(freeze_summary, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.apply_freeze and not errors:
        updated_domain, updated_map = apply_freeze_metadata(domain_doc, map_doc)
        DOMAIN_PATH.write_text(json.dumps(updated_domain, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        MAP_PATH.write_text(json.dumps(updated_map, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Freeze metadata applied to Domain_Understanding.json and LO_to_Domain_Understanding.json")

    print(f"Freeze package: {args.output_dir}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
