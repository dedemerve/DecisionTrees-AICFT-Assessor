#!/usr/bin/env python3
"""generate_milestone5_freeze_package.py — Milestone 5 freeze for Domain→AI-CFT interpretive policy."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
M5_REPORTS = REPO / "reports" / "milestone5"
OUTPUT_DIR = REPO / "reports" / "milestone5_freeze"
VALIDATOR = REPO / "scripts" / "validate_domain_to_ai_cft.py"
STRESS = REPO / "scripts" / "run_ai_cft_interpretive_stress_test.py"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def apply_freeze(doc: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    doc["freeze"] = {
        "status": "frozen",
        "version": "1.0",
        "frozen_at": now,
        "freeze_package_dir": "reports/milestone5_freeze",
        "expert_review_status": "automated_review_complete; interpretive_stress_test_passed; human_expert_review_pending",
        "change_policy": "major_version_required_for_semantic_changes",
        "interpretation_layer": True,
        "artifact_role": "interpretive_policy_not_competency_output",
        "upstream_frozen_inputs": [
            "Domain_Understanding.json@1.0",
            "LO_to_Domain_Understanding.json@1.0",
            "Behaviour_to_ILO.json@1.1",
            "Learning_Objects.json@1.0",
            "Observable_Behaviours.json@1.0",
        ],
        "downstream_artifacts_locked": ["Aggregation_Policy.json", "portfolio interpretive pipeline"],
        "framework_complete": True,
        "next_phase": "pilot_implementation_not_new_theory",
    }
    return doc


def write_report(doc: dict[str, Any], validation: dict[str, Any], stress: dict[str, Any], frozen: bool) -> str:
    stats = load_json(M5_REPORTS / "interpretation_statistics.json") if (M5_REPORTS / "interpretation_statistics.json").exists() else {}
    lines = [
        "# Milestone 5 Freeze Report",
        "",
        "## Domain → AI-CFT Interpretive Policy",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Domain_to_AI_CFT.json` |",
        "| Type | **Interpretive policy** (not deterministic mapping) |",
        "| Version | **1.0** |",
        f"| Freeze status | **{'FROZEN' if frozen else 'PENDING_APPLY'}** |",
        f"| Domain policies | {doc.get('domain_policy_count', 8)} |",
        f"| Contribution records | {doc.get('contribution_count', '?')} |",
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
        "## Framework theory phase complete",
        "",
        "After this freeze, new theory artifacts should not be added without version bump. Next phase:",
        "",
        "1. Remodel WS1–WS11 bundles to new architecture",
        "2. Implement OCR → Evidence → … → interpretive recommendation pipeline",
        "3. Pilot on real student portfolios",
        "4. Reliability and validity analyses",
        "",
        "## Freeze decision",
        "",
    ]
    if validation.get("status") == "pass" and stress.get("status") == "pass" and frozen:
        lines.append("**APPROVED:** Domain_to_AI_CFT.json v1.0 frozen. Framework theory chain complete.")
    elif validation.get("status") == "pass" and stress.get("status") == "pass":
        lines.append("**READY:** Run with `--apply-freeze`.")
    else:
        lines.append("**BLOCKED:** Fix validation or stress test failures.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply-freeze", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    errors: list[str] = []
    if load_json(DOMAIN_PATH).get("freeze", {}).get("status") != "frozen":
        errors.append("Domain_Understanding.json must be frozen")

    for script in (VALIDATOR, STRESS):
        if subprocess.run([sys.executable, str(script), "--quiet"], cwd=REPO).returncode != 0:
            errors.append(f"{script.name} failed")

    validation = load_json(M5_REPORTS / "milestone5_validation.json")
    stress = load_json(M5_REPORTS / "ai_cft_interpretive_stress_test.json")
    doc = load_json(POLICY_PATH)

    if re.search(r'"maps_to"\s*:', POLICY_PATH.read_text()):
        errors.append("maps_to field prohibited in artifact")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name in ("aicft_coverage_report.json", "interpretation_statistics.json",
                 "ai_cft_interpretive_stress_test.json", "milestone5_validation.json"):
        src = M5_REPORTS / name
        if src.exists():
            shutil.copy2(src, args.output_dir / name)

    frozen = args.apply_freeze and not errors
    (args.output_dir / "milestone5_freeze_report.md").write_text(
        write_report(doc, validation, stress, frozen), encoding="utf-8",
    )

    if frozen:
        POLICY_PATH.write_text(json.dumps(apply_freeze(doc), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Freeze metadata applied to Domain_to_AI_CFT.json")

    print(f"Freeze package: {args.output_dir}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
