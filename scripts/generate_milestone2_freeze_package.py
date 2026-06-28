#!/usr/bin/env python3
"""
generate_milestone2_freeze_package.py — Milestone 2 human summary for ILO ontology.

Legacy script name; writes reports/milestone2_summary.md only.

Usage:
  python scripts/generate_milestone2_freeze_package.py
  python scripts/generate_milestone2_freeze_package.py --apply-freeze
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ILO_PATH = REPO_ROOT / "framework" / "Learning_Objects.json"
ILO_DEP_PATH = REPO_ROOT / "framework" / "ILO_Dependency_Graph.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_learning_objects.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from milestone_reporting import (  # noqa: E402
    freeze_status_label,
    load_json,
    load_validation,
    run_quiet_script,
    write_summary,
)


def build_coverage_hierarchy(ilos: dict[str, Any]) -> dict[str, Any]:
    by_family: dict[str, list[str]] = defaultdict(list)
    for iid, ilo in sorted(ilos.items()):
        by_family[ilo["concept_family"]].append(iid)
    return {"by_concept_family": {k: sorted(v) for k, v in sorted(by_family.items())}}


def validate_dependency_graph(ilos: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids = set(ilos)
    for edge in graph.get("edges", []):
        for node in (edge.get("from"), edge.get("to")):
            if node not in ids:
                errors.append(f"ILO dependency graph: unknown node {node!r}")
    seq = graph.get("instructional_sequence", [])
    if set(seq) != ids:
        missing = ids - set(seq)
        extra = set(seq) - ids
        if missing:
            errors.append(f"instructional_sequence missing ILOs: {sorted(missing)}")
        if extra:
            errors.append(f"instructional_sequence unknown ILOs: {sorted(extra)}")
    return errors


def apply_freeze_metadata(ilo_data: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    ilo_data["freeze"] = {
        "status": "frozen",
        "version": "1.0",
        "frozen_at": now,
        "freeze_package_dir": "reports",
        "expert_review_status": "automated_review_complete; human_expert_review_pending",
        "change_policy": "major_version_required_for_semantic_changes",
        "downstream_artifacts_locked": [
            "Behaviour_to_ILO.json",
            "LO_to_Domain_Understanding.json",
            "worksheet behaviour_opportunities.json",
        ],
    }
    ilo_data["framework_version"] = "1.0"
    return ilo_data


def write_summary_md(
    ilo_data: dict[str, Any],
    behaviours_covered: int,
    coverage: dict[str, Any],
    dep_errors: list[str],
    graph: dict[str, Any],
    applying: bool,
) -> str:
    families = coverage.get("by_concept_family", {})
    status = freeze_status_label(ilo_data, applying=applying)
    lines = [
        "# Milestone 2 Summary",
        "",
        "## Instructional Learning Object (ILO) Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Learning_Objects.json` |",
        "| Terminology | **ILO** — Instructional Learning Object |",
        "| Version | **1.0** |",
        f"| Freeze status | **{status}** |",
        "| ILO count | 21 |",
        "| Frozen behaviour input | Observable_Behaviours.json v1.0 |",
        "",
        "## Contribution (publication)",
        "",
        "> The framework distinguishes reusable Observable Behaviours from Instructional Learning Objects, "
        "allowing behavioural evidence to be interpreted independently of competency frameworks.",
        "",
        "## Behaviour → ILO Coverage Matrix",
        "",
        f"- Behaviours mapped: {behaviours_covered}/28",
        "",
        "## Concept Families",
        "",
        "| Family | ILO count |",
        "|--------|-----------|",
    ]
    for fam, items in sorted(families.items()):
        lines.append(f"| {fam} | {len(items)} |")

    lines.extend([
        "",
        "## Instructional Sequence",
        "",
        "Canonical order documented in `ILO_Dependency_Graph.json` → `instructional_sequence`.",
        "",
        "```",
        " → ".join(graph.get("instructional_sequence", [])[:8]) + " → ...",
        "```",
        "",
        "## ILO Dependency Graph",
        "",
        "- Artifact: `framework/ILO_Dependency_Graph.json`",
        f"- Edges: {len(graph.get('edges', []))}",
        f"- Validation errors: {len(dep_errors)}",
        "",
        "## Automated validation",
        "",
        "- `reports/milestone2_validation.json` — single validation artifact",
        "",
        "## Remaining Risks",
        "",
        "1. Human expert ILO coding agreement pending.",
        "2. No dedicated `generalisation` ILO (v1.0 accepted limitation).",
        "3. TP/TN/FP/FN not separate ILOs — embedded in ILO_CONFUSION_MATRIX.",
        "",
        "## Accepted Limitations",
        "",
        "- `generalisation` concept family has no standalone ILO; partial coverage via `reasoning` ILOs.",
        "- AI-CFT competency codes (LO3.x) remain separate from ILO layer.",
        "- `ILO_PRIOR_BELIEF` is diagnostic (sequence position 0) and excluded from mastery aggregation.",
        "",
        "## Expert Review Status",
        "",
        "| Review | Status |",
        "|--------|--------|",
        "| Automated validation | complete |",
        "| Behaviour→ILO matrix complete | complete |",
        "| Human expert review | **pending** |",
        "",
        "## Freeze Decision",
        "",
    ])

    if not dep_errors and applying:
        lines.append(
            "**APPROVED:** Instructional Learning Object Ontology v1.0 is frozen. "
            "Milestone 3 may proceed with `Behaviour_to_ILO.json` only — no new OB or ILO definitions."
        )
    elif not dep_errors:
        lines.append("**READY:** Run with `--apply-freeze` to write freeze metadata.")
    else:
        lines.append("**BLOCKED:** Resolve dependency graph errors.")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 2 ILO summary")
    parser.add_argument("--apply-freeze", action="store_true")
    args = parser.parse_args(argv)

    ilo_data = load_json(ILO_PATH)
    graph = load_json(ILO_DEP_PATH)
    ilos = ilo_data["learning_objects"]

    errors: list[str] = []
    if run_quiet_script(VALIDATOR) != 0:
        errors.append("validate_learning_objects.py failed")

    validation = load_validation(2)
    errors.extend(validation.get("errors", []))
    dep_errors = validate_dependency_graph(ilos, graph)
    errors.extend(dep_errors)

    cov = validation.get("coverage", {})
    behaviours_covered = cov.get("behaviours_covered", 0)
    coverage = build_coverage_hierarchy(ilos)
    applying = args.apply_freeze and not errors

    report = write_summary_md(
        ilo_data, behaviours_covered, coverage, dep_errors, graph, applying,
    )
    summary_path = write_summary(2, report)

    if applying:
        ILO_PATH.write_text(
            json.dumps(apply_freeze_metadata(ilo_data), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Freeze metadata applied to Learning_Objects.json")

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
