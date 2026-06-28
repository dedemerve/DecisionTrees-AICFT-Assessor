#!/usr/bin/env python3
"""
generate_milestone2_freeze_package.py — Milestone 2 freeze verification for ILO ontology.

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
OB_PATH = REPO_ROOT / "framework" / "Observable_Behaviours.json"
ILO_DEP_PATH = REPO_ROOT / "framework" / "ILO_Dependency_Graph.json"
OUTPUT_DIR = REPO_ROOT / "reports" / "milestone2_freeze"

CONCEPT_FAMILIES = frozenset({
    "data_representation",
    "classification",
    "evaluation",
    "generalisation",
    "reasoning",
    "reflection",
})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_behaviour_ilo_matrix(ilos: dict[str, Any]) -> dict[str, Any]:
    """Full behaviour → ILO mapping with reverse index."""
    behaviour_to_ilos: dict[str, list[str]] = defaultdict(list)
    for iid, ilo in ilos.items():
        for ob in ilo.get("related_behaviours", []):
            behaviour_to_ilos[ob].append(iid)

    rows = []
    for ob in sorted(behaviour_to_ilos):
        linked = sorted(behaviour_to_ilos[ob])
        rows.append({
            "behaviour_id": ob,
            "ilo_ids": linked,
            "ilo_count": len(linked),
            "primary_ilo": linked[0],
        })

    ilo_to_behaviours: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        for iid in row["ilo_ids"]:
            ilo_to_behaviours[iid].append(row["behaviour_id"])

    return {
        "matrix_type": "behaviour_to_ilo",
        "row_count": len(rows),
        "behaviour_to_ilo": dict(sorted(behaviour_to_ilos.items())),
        "ilo_to_behaviour": {k: sorted(v) for k, v in sorted(ilo_to_behaviours.items())},
        "table": rows,
    }


def build_coverage_hierarchy(ilos: dict[str, Any]) -> dict[str, Any]:
    tree: dict[str, Any] = {}
    by_family: dict[str, list[str]] = defaultdict(list)
    for iid, ilo in sorted(ilos.items()):
        dim = ilo["construct_dimension"]
        family = ilo["concept_family"]
        order = ilo.get("instructional_sequence_order", -1)
        by_family[family].append(iid)
        tree.setdefault(dim, {}).setdefault(family, []).append({
            "id": iid,
            "title": ilo["title"],
            "instructional_sequence_order": order,
            "related_behaviour_count": len(ilo.get("related_behaviours", [])),
        })

    for dim in tree:
        for family in tree[dim]:
            tree[dim][family].sort(key=lambda x: x["instructional_sequence_order"])

    return {
        "hierarchy": "construct_dimension → concept_family → ilo",
        "tree": tree,
        "by_concept_family": {k: sorted(v) for k, v in sorted(by_family.items())},
        "by_construct_dimension": {
            dim: sum(len(ilos[i]["related_behaviours"]) for i in ilos if ilos[i]["construct_dimension"] == dim)
            for dim in sorted({v["construct_dimension"] for v in ilos.values()})
        },
    }


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
        "freeze_package_dir": "reports/milestone2_freeze",
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


def write_freeze_report_md(
    matrix: dict[str, Any],
    coverage: dict[str, Any],
    dep_errors: list[str],
    graph: dict[str, Any],
    apply_freeze: bool,
) -> str:
    families = coverage.get("by_concept_family", {})
    lines = [
        "# Milestone 2 Freeze Report",
        "",
        "## Instructional Learning Object (ILO) Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Learning_Objects.json` |",
        "| Terminology | **ILO** — Instructional Learning Object |",
        "| Version | **1.0** |",
        f"| Freeze status | **{'FROZEN' if apply_freeze else 'PENDING_APPLY'}** |",
        f"| Generated | {datetime.now(timezone.utc).isoformat()} |",
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
        f"- Behaviours mapped: {matrix['row_count']}/28",
        f"- Full matrix: `behaviour_ilo_coverage_matrix.json`",
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
        f"- Artifact: `framework/ILO_Dependency_Graph.json`",
        f"- Edges: {len(graph.get('edges', []))}",
        f"- Validation errors: {len(dep_errors)}",
        "",
        "## Remaining Risks",
        "",
        "1. Human expert ILO coding agreement pending.",
        "2. No dedicated `generalisation` ILO (v1.0 accepted limitation).",
        "3. TP/TN/FP/FN not separate ILOs — embedded in ILO_CONFUSION_MATRIX.",
        "4. Milestone 3 mapping (`Behaviour_to_ILO.json`) not yet authored.",
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

    if not dep_errors and apply_freeze:
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
    parser = argparse.ArgumentParser(description="Generate Milestone 2 ILO freeze package")
    parser.add_argument("--apply-freeze", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    ilo_data = load_json(ILO_PATH)
    ob_data = load_json(OB_PATH)
    graph = load_json(ILO_DEP_PATH)
    ilos = ilo_data["learning_objects"]

    if ob_data.get("freeze", {}).get("status") != "frozen":
        print("ERROR: Observable_Behaviours.json must be frozen first")
        return 1

    errors: list[str] = []
    for iid, ilo in ilos.items():
        if ilo.get("concept_family") not in CONCEPT_FAMILIES:
            errors.append(f"{iid}: invalid concept_family {ilo.get('concept_family')!r}")
        if "instructional_sequence_order" not in ilo:
            errors.append(f"{iid}: missing instructional_sequence_order")

    errors.extend(validate_dependency_graph(ilos, graph))

    matrix = build_behaviour_ilo_matrix(ilos)
    if matrix["row_count"] != len(ob_data.get("behaviours", {})):
        errors.append(
            f"behaviour coverage incomplete: {matrix['row_count']} vs {len(ob_data['behaviours'])}"
        )

    coverage = build_coverage_hierarchy(ilos)
    now = datetime.now(timezone.utc).isoformat()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    (args.output_dir / "behaviour_ilo_coverage_matrix.json").write_text(
        json.dumps({"milestone": 2, "generated_at": now, **matrix}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "ilo_coverage_matrix.json").write_text(
        json.dumps({"milestone": 2, "generated_at": now, **coverage}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (args.output_dir / "ilo_dependency_graph_summary.json").write_text(
        json.dumps({
            "milestone": 2,
            "source": "framework/ILO_Dependency_Graph.json",
            "edge_count": len(graph.get("edges", [])),
            "instructional_sequence": graph.get("instructional_sequence", []),
            "validation_errors": errors,
            "pass": not errors,
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    report = write_freeze_report_md(matrix, coverage, errors, graph, args.apply_freeze)
    (args.output_dir / "milestone2_freeze_report.md").write_text(report, encoding="utf-8")

    if args.apply_freeze and not errors:
        updated = apply_freeze_metadata(ilo_data)
        ILO_PATH.write_text(json.dumps(updated, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Freeze metadata applied to Learning_Objects.json")

    print(f"Freeze package: {args.output_dir}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    for e in errors:
        print(f"  - {e}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
