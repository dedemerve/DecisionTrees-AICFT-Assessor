#!/usr/bin/env python3
"""Generate Phase 2 M2 implementation freeze package."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FREEZE_DIR = REPO_ROOT / "reports" / "implementation" / "m2_freeze"

FROZEN_ARTIFACTS = [
    "schema/evidence_units_v1.schema.json",
    "evidence_unit_runtime.py",
    "evidence_unit_metadata.py",
    "schema_validate.py",
    "scripts/build_evidence_units.py",
    "scripts/validate_evidence_units.py",
    "test_evidence_units.py",
    "test_evidence_unit_metadata.py",
]

SCHEMA_VERSION = "1.1"


def _run_tests() -> tuple[bool, str]:
    cmd = [
        sys.executable, "-m", "pytest",
        "test_evidence_units.py",
        "test_evidence_unit_metadata.py",
        "-q",
    ]
    proc = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr


def main() -> int:
    FREEZE_DIR.mkdir(parents=True, exist_ok=True)
    tests_ok, test_output = _run_tests()

    manifest = {
        "freeze": {
            "milestone": "Phase 2 — M2: Canonical Evidence Unit Runtime",
            "status": "FROZEN",
            "schema_version": SCHEMA_VERSION,
            "frozen_at": datetime.now(timezone.utc).isoformat(),
            "framework_version": "1.0",
            "modification_policy": (
                "No schema or runtime changes without explicit researcher approval "
                "and construct-validity justification."
            ),
        },
        "assessment_object_definition": (
            "The smallest traceable assessment object representing an interpretable "
            "piece of learner evidence while preserving provenance, uncertainty, "
            "source quality, and review metadata."
        ),
        "frozen_artifacts": FROZEN_ARTIFACTS,
        "verification": {
            "pytest": "PASS" if tests_ok else "FAIL",
            "test_output": test_output.strip(),
        },
        "inferential_boundary": {
            "permitted": [
                "descriptive normalization",
                "assessment-object metadata derivation",
                "provenance and uncertainty preservation",
            ],
            "forbidden": [
                "observable_behaviour inference",
                "ilo_inference",
                "domain_inference",
                "ai_cft_interpretation",
                "competency_labels",
            ],
        },
        "downstream_consumer": "Behaviour Engine (M3) reads evidence_units.json only",
    }

    (FREEZE_DIR / "freeze_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    report_lines = [
        "# Phase 2 M2 Freeze Report — Evidence Unit Runtime",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Status | **FROZEN** |",
        f"| Schema version | **{SCHEMA_VERSION}** |",
        f"| Frozen at | {manifest['freeze']['frozen_at']} |",
        f"| Tests | {'PASS' if tests_ok else 'FAIL'} |",
        "",
        "## Scope",
        "",
        "Canonical Layer 2 runtime: `students/<id>/evidence_units.json`",
        "",
        "## Modification policy",
        "",
        "> No further Evidence Unit fields without construct-validity justification.",
        "> OCR adapters are upstream only; they do not alter this schema.",
        "",
        "## Inferential boundary",
        "",
        "Everything up to and including Evidence Units remains **descriptive**.",
        "The first inferential leap occurs in **M3: Behaviour Engine**.",
    ]
    (FREEZE_DIR / "m2_freeze_report.md").write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(json.dumps(manifest["freeze"], indent=2))
    return 0 if tests_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
