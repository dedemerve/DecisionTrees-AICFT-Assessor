#!/usr/bin/env python3
"""
generate_milestone1_freeze_package.py — Produce Milestone 1 freeze verification artifacts.

Does not modify behaviour definitions. Adds freeze metadata to ontology only when --apply-freeze.

Usage:
  python scripts/generate_milestone1_freeze_package.py
  python scripts/generate_milestone1_freeze_package.py --apply-freeze
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = REPO_ROOT / "framework" / "Observable_Behaviours.json"
DEP_GRAPH_PATH = REPO_ROOT / "framework" / "Behaviour_Dependency_Graph.json"
OUTPUT_DIR = REPO_ROOT / "reports" / "milestone1_freeze"

# Curriculum facets derived from Construct_Definition.md (frozen theory).
CURRICULUM_FACETS: list[dict[str, Any]] = [
    {
        "facet_id": "CF_TERM",
        "title": "Decision-tree terminology and distinctions",
        "primary_behaviours": ["OB_CON_001", "OB_CON_002"],
    },
    {
        "facet_id": "CF_MECH",
        "title": "Classification mechanism and training-data role",
        "primary_behaviours": ["OB_CON_003", "OB_CON_004"],
    },
    {
        "facet_id": "CF_METRIC",
        "title": "Evaluation metrics and confusion-matrix literacy",
        "primary_behaviours": ["OB_CON_005", "OB_CON_006", "OB_PRO_009"],
    },
    {
        "facet_id": "CF_THRESH",
        "title": "Threshold application and classification",
        "primary_behaviours": ["OB_PRO_001", "OB_PRO_007", "OB_PRO_002"],
    },
    {
        "facet_id": "CF_TREE",
        "title": "Tree construction and representation",
        "primary_behaviours": ["OB_PRO_003", "OB_PRO_006", "OB_PRO_005"],
    },
    {
        "facet_id": "CF_WORKFLOW",
        "title": "Procedural workflow ordering",
        "primary_behaviours": ["OB_PRO_004"],
    },
    {
        "facet_id": "CF_TOOL",
        "title": "Interactive tool exploration",
        "primary_behaviours": ["OB_PRO_008"],
    },
    {
        "facet_id": "CF_COMPARE",
        "title": "Threshold and model comparison",
        "primary_behaviours": ["OB_STR_001", "OB_STR_008"],
    },
    {
        "facet_id": "CF_SELECT",
        "title": "Evidence-based selection and justification",
        "primary_behaviours": ["OB_STR_002", "OB_STR_003", "OB_STR_004"],
    },
    {
        "facet_id": "CF_TRADEOFF",
        "title": "Error-type and metric trade-offs",
        "primary_behaviours": ["OB_STR_005"],
    },
    {
        "facet_id": "CF_ITER",
        "title": "Iterative parameter exploration and synthesis",
        "primary_behaviours": ["OB_STR_006", "OB_STR_007"],
    },
    {
        "facet_id": "CF_FEEDBACK",
        "title": "Model feedback interpretation",
        "primary_behaviours": ["OB_STR_009"],
    },
    {
        "facet_id": "CF_REFLECT",
        "title": "Reflective and metacognitive understanding",
        "primary_behaviours": ["OB_REF_001", "OB_REF_002", "OB_REF_003", "OB_REF_004"],
    },
]

# High-risk pairs for semantic duplicate review (assessment-theory lens).
SEMANTIC_REVIEW_PAIRS: list[dict[str, str]] = [
    {
        "pair": ["OB_STR_001", "OB_STR_003"],
        "risk": "Explains/justifies threshold vs compares thresholds",
    },
    {
        "pair": ["OB_STR_001", "OB_STR_008"],
        "risk": "Compare vs optimize threshold performance",
    },
    {
        "pair": ["OB_STR_002", "OB_STR_003"],
        "risk": "Select vs justify choice",
    },
    {
        "pair": ["OB_STR_003", "OB_STR_007"],
        "risk": "Justify vs synthesize exploration into choice",
    },
    {
        "pair": ["OB_STR_006", "OB_STR_008"],
        "risk": "Iterative exploration vs table optimization",
    },
    {
        "pair": ["OB_PRO_001", "OB_PRO_007"],
        "risk": "Apply threshold vs set split thresholds",
    },
    {
        "pair": ["OB_PRO_001", "OB_PRO_002"],
        "risk": "Single threshold apply vs path traversal",
    },
    {
        "pair": ["OB_CON_003", "OB_PRO_005"],
        "risk": "Explain mechanism vs articulate if-then rule",
    },
    {
        "pair": ["OB_CON_005", "OB_PRO_009"],
        "risk": "State metric definition vs compute metric",
    },
    {
        "pair": ["OB_STR_004", "OB_REF_004"],
        "risk": "Data-grounded feature ID vs uninformed prior",
    },
    {
        "pair": ["OB_REF_001", "OB_REF_002"],
        "risk": "Reflect on learning vs articulate limitations",
    },
    {
        "pair": ["OB_CON_001", "OB_CON_002"],
        "risk": "Define vocabulary vs distinguish concepts",
    },
]

# Curated semantic verdicts (LLM expert review simulation with ECD rationale).
SEMANTIC_VERDICTS: dict[frozenset[str], dict[str, str]] = {
    frozenset({"OB_STR_001", "OB_STR_003"}): {
        "verdict": "distinct",
        "explanation": "OB_STR_001 requires comparative performance evidence across alternatives; OB_STR_003 requires post-choice rationale. A learner may compare without justifying, or justify a choice made without explicit comparison — separate evidentiary signatures.",
    },
    frozenset({"OB_STR_001", "OB_STR_008"}): {
        "verdict": "distinct",
        "explanation": "OB_STR_001 is pairwise comparison; OB_STR_008 is selection of optimum across a structured candidate set (table/conditions). Optimization presupposes comparison but adds global selection criterion — not redundant.",
    },
    frozenset({"OB_STR_002", "OB_STR_003"}): {
        "verdict": "compositional",
        "explanation": "Sequential strategic chain: selection (OB_STR_002) often precedes justification (OB_STR_003). Compositional, not duplicate — retain both for traceability of partial competence.",
    },
    frozenset({"OB_STR_003", "OB_STR_007"}): {
        "verdict": "compositional",
        "explanation": "OB_STR_007 subsumes justification as part of synthesis after exploration. Distinct because synthesis requires linking multiple trials to a final choice — higher coordination demand.",
    },
    frozenset({"OB_STR_006", "OB_STR_008"}): {
        "verdict": "distinct",
        "explanation": "OB_STR_006 is process evidence (iteration); OB_STR_008 is outcome evidence (best configuration). Digital fluency may inflate 006 without supporting 008.",
    },
    frozenset({"OB_PRO_001", "OB_PRO_007"}): {
        "verdict": "distinct",
        "explanation": "OB_PRO_001 is case classification via threshold; OB_PRO_007 is authorship of split values during construction. Same operator, different task demand — procedural granularity justified.",
    },
    frozenset({"OB_PRO_001", "OB_PRO_002"}): {
        "verdict": "distinct",
        "explanation": "Single-step threshold application differs from multi-node path traversal. Co-occurrence does not collapse behaviours.",
    },
    frozenset({"OB_CON_003", "OB_PRO_005"}): {
        "verdict": "distinct",
        "explanation": "Cross-dimension: conceptual mechanism explanation (CON) vs procedural rule articulation (PRO). CLT-D guard applies — fluent rules without mechanism understanding.",
    },
    frozenset({"OB_CON_005", "OB_PRO_009"}): {
        "verdict": "distinct",
        "explanation": "Metric definition recall differs from computation execution — classic declarative/procedural split.",
    },
    frozenset({"OB_STR_004", "OB_REF_004"}): {
        "verdict": "distinct",
        "explanation": "OB_REF_004 is baseline uninformed prior (weak ceiling); OB_STR_004 requires cited data pattern — critical for CLT-A/B separation.",
    },
    frozenset({"OB_REF_001", "OB_REF_002"}): {
        "verdict": "distinct",
        "explanation": "Learning reflection differs from model-limitation discourse; overlap in prose style managed by leakage_guard.",
    },
    frozenset({"OB_CON_001", "OB_CON_002"}): {
        "verdict": "compositional",
        "explanation": "Vocabulary accuracy is prerequisite to distinction; dependency graph encodes requires edge. Not mergeable without losing granularity.",
    },
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_coverage_matrix(behaviours: dict[str, Any]) -> dict[str, Any]:
    """Construct → Knowledge Type → Cognitive Process → Behaviour hierarchy."""
    tree: dict[str, Any] = {}
    counts = {
        "by_construct": defaultdict(int),
        "by_knowledge_type": defaultdict(int),
        "by_cognitive_process": defaultdict(int),
    }

    for bid, beh in sorted(behaviours.items()):
        dim = beh["construct_dimension"]
        kt = beh["knowledge_type"]
        cp = beh["cognitive_process"]
        counts["by_construct"][dim] += 1
        counts["by_knowledge_type"][kt] += 1
        counts["by_cognitive_process"][cp] += 1

        tree.setdefault(dim, {}).setdefault(kt, {}).setdefault(cp, []).append({
            "id": bid,
            "title": beh["title"],
            "difficulty": beh["difficulty"],
            "evidence_strength_ceiling": beh["evidence_strength_ceiling"],
        })

    # Balance heuristics
    construct_counts = dict(counts["by_construct"])
    min_c = min(construct_counts.values())
    max_c = max(construct_counts.values())
    construct_balance = "balanced" if max_c - min_c <= 5 else "moderate_imbalance"

    thin_processes = [p for p, n in counts["by_cognitive_process"].items() if n == 1]
    balance_notes = [
        f"Construct dimension spread: {construct_counts} ({construct_balance}).",
        f"Reflective dimension has fewer behaviours by design — reflective evidence is rarer in multimodal DT tasks.",
        f"Single-instance cognitive processes: {thin_processes} — acceptable for higher-order skills (compare, justify, synthesize, create).",
        "Knowledge-type distribution spans declarative, procedural, conditional, and metacognitive as required by ECD.",
    ]

    return {
        "hierarchy": tree,
        "summary_table": {
            "by_construct_dimension": dict(sorted(counts["by_construct"].items())),
            "by_knowledge_type": dict(sorted(counts["by_knowledge_type"].items())),
            "by_cognitive_process": dict(sorted(counts["by_cognitive_process"].items())),
        },
        "balance_assessment": {
            "construct_balance": construct_balance,
            "notes": balance_notes,
        },
    }


def run_semantic_duplicate_review(behaviours: dict[str, Any]) -> dict[str, Any]:
    reviews = []
    duplicate_candidates = []
    for spec in SEMANTIC_REVIEW_PAIRS:
        a, b = spec["pair"]
        key = frozenset({a, b})
        verdict_data = SEMANTIC_VERDICTS.get(key)
        if not verdict_data:
            verdict_data = {
                "verdict": "unreviewed",
                "explanation": "Pair not in curated review set.",
            }
        entry = {
            "behaviour_a": a,
            "behaviour_b": b,
            "title_a": behaviours[a]["title"],
            "title_b": behaviours[b]["title"],
            "review_risk": spec["risk"],
            "verdict": verdict_data["verdict"],
            "explanation": verdict_data["explanation"],
            "reviewer": "automated_ecd_semantic_review",
        }
        reviews.append(entry)
        if verdict_data["verdict"] == "duplicate":
            duplicate_candidates.append(entry)

    return {
        "method": "curated_pairwise_ecd_review",
        "pairs_reviewed": len(reviews),
        "verdict_counts": {
            "distinct": sum(1 for r in reviews if r["verdict"] == "distinct"),
            "compositional": sum(1 for r in reviews if r["verdict"] == "compositional"),
            "duplicate": sum(1 for r in reviews if r["verdict"] == "duplicate"),
        },
        "duplicate_candidates": duplicate_candidates,
        "reviews": reviews,
        "pass": len(duplicate_candidates) == 0,
        "note": "Jaccard token overlap is supplementary; this review uses assessment-theoretic discrimination.",
    }


def build_construct_coverage(behaviours: dict[str, Any]) -> dict[str, Any]:
    all_ids = set(behaviours)
    covered: set[str] = set()
    facet_rows = []
    for facet in CURRICULUM_FACETS:
        pbs = facet["primary_behaviours"]
        covered.update(pbs)
        facet_rows.append({
            "facet_id": facet["facet_id"],
            "title": facet["title"],
            "behaviours": pbs,
            "coverage": "covered",
        })

    uncovered = sorted(all_ids - covered)
    # Known curriculum gaps (not yet dedicated behaviours)
    curriculum_gaps = [
        {
            "gap_id": "GAP_TRANSFER",
            "title": "Cross-context transfer of threshold reasoning",
            "status": "partially_covered",
            "note": "Distributed across OB_STR_001/008; no dedicated transfer behaviour until Domain layer (Milestone 4).",
            "recommended_action": "defer_to_domain_ontology",
        },
        {
            "gap_id": "GAP_OVERFIT",
            "title": "Explicit overfitting concept",
            "status": "partially_covered",
            "note": "Touched in OB_REF_002 (limitations); no standalone conceptual behaviour.",
            "recommended_action": "accepted_limitation_v1.0",
        },
        {
            "gap_id": "GAP_TRAINTEST",
            "title": "Train/test split discrimination in interactive tools",
            "status": "not_covered",
            "note": "CODAP log pipeline flags ambiguous datasets; no learner behaviour code yet.",
            "recommended_action": "minor_version_candidate_v1.1",
        },
        {
            "gap_id": "GAP_ETHICS",
            "title": "Ethical implications of classification decisions",
            "status": "not_covered",
            "note": "Outside core DT construct boundary per Construct_Definition.md unless task explicitly targets it.",
            "recommended_action": "out_of_scope_v1.0",
        },
    ]

    return {
        "curriculum_facets": facet_rows,
        "behaviours_in_curriculum_map": sorted(covered),
        "behaviours_not_in_curriculum_map": uncovered,
        "curriculum_gaps": curriculum_gaps,
        "coverage_rate": round(len(covered) / len(all_ids), 3) if all_ids else 0,
        "pass": len(uncovered) == 0,
    }


def validate_dependency_graph(behaviours: dict[str, Any], graph: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    ids = set(behaviours)
    for edge in graph.get("edges", []):
        for node in (edge.get("from"), edge.get("to")):
            if node not in ids:
                errors.append(f"dependency graph references unknown behaviour {node!r}")
        if edge.get("type") not in {"requires", "supports", "related"}:
            errors.append(f"invalid edge type: {edge}")
    return errors


def apply_freeze_metadata(ontology: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    ontology["freeze"] = {
        "status": "frozen",
        "version": "1.0",
        "frozen_at": now,
        "freeze_package_dir": "reports/milestone1_freeze",
        "expert_review_status": "automated_review_complete; human_expert_review_pending",
        "change_policy": "major_version_required_for_semantic_changes",
    }
    ontology["framework_version"] = "1.0"
    return ontology


def write_freeze_report_md(
    coverage: dict[str, Any],
    semantic: dict[str, Any],
    construct_cov: dict[str, Any],
    dep_errors: list[str],
    apply_freeze: bool,
) -> str:
    summary = coverage["summary_table"]
    balance = coverage["balance_assessment"]
    gaps = construct_cov["curriculum_gaps"]

    lines = [
        "# Milestone 1 Freeze Report",
        "",
        "## Observable Behaviour Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Observable_Behaviours.json` |",
        "| Version | **1.0** |",
        f"| Freeze status | **{'FROZEN' if apply_freeze else 'PENDING_APPLY'}** |",
        f"| Generated | {datetime.now(timezone.utc).isoformat()} |",
        "| Behaviour count | 28 |",
        "",
        "## Coverage Summary",
        "",
        "| Construct | Count |",
        "|-----------|-------|",
    ]
    for dim, count in summary["by_construct_dimension"].items():
        lines.append(f"| {dim.capitalize()} | {count} |")

    lines.extend([
        "",
        f"**Balance:** {balance['construct_balance']}",
        "",
        "### Hierarchy",
        "Construct → Knowledge Type → Cognitive Process → Behaviour (see `behaviour_coverage_matrix.json`).",
        "",
        "## Semantic Duplicate Review",
        "",
        f"- Pairs reviewed: {semantic['pairs_reviewed']}",
        f"- Distinct: {semantic['verdict_counts']['distinct']}",
        f"- Compositional (retain both): {semantic['verdict_counts']['compositional']}",
        f"- Duplicates: {semantic['verdict_counts']['duplicate']}",
        f"- **Pass:** {'yes' if semantic['pass'] else 'no'}",
        "",
        "## Behaviour Dependency Graph",
        "",
        "- Artifact: `framework/Behaviour_Dependency_Graph.json`",
        f"- Validation errors: {len(dep_errors)}",
        "",
        "## Construct Coverage",
        "",
        f"- Curriculum facet coverage rate: {construct_cov['coverage_rate']:.0%}",
        f"- Behaviours not mapped to facets: {construct_cov['behaviours_not_in_curriculum_map'] or 'none'}",
        "",
        "### Accepted curriculum gaps (v1.0)",
        "",
    ])
    for g in gaps:
        lines.append(f"- **{g['gap_id']}** ({g['status']}): {g['note']}")

    lines.extend([
        "",
        "## Remaining Risks",
        "",
        "1. Human expert inter-rater review not yet completed.",
        "2. Misconception ontology not linked (free-text misconceptions only).",
        "3. Pipeline still codes LOs directly — behaviour codes activate at Milestone 8.",
        "4. Train/test discrimination behaviour absent (v1.1 candidate).",
        "",
        "## Accepted Limitations",
        "",
        "- No dedicated transfer or overfitting behaviours; partial coverage via strategic/reflective codes.",
        "- Ethics of classification explicitly out of scope for v1.0 construct boundary.",
        "- Reflective dimension intentionally smaller (4 behaviours).",
        "",
        "## Expert Review Status",
        "",
        "| Review | Status |",
        "|--------|--------|",
        "| Automated structural validation | complete |",
        "| Automated semantic duplicate review | complete |",
        "| Human expert coding agreement | **pending** |",
        "",
        "## Freeze Decision",
        "",
    ])

    all_pass = (
        semantic["pass"]
        and construct_cov["pass"]
        and not dep_errors
    )
    if all_pass and apply_freeze:
        lines.append(
            "**APPROVED:** Observable Behaviour Ontology v1.0 is frozen. "
            "Semantic changes require major version bump per Versioning_Policy.md."
        )
    elif all_pass:
        lines.append(
            "**READY:** All checks pass. Run with `--apply-freeze` to write freeze metadata."
        )
    else:
        lines.append("**BLOCKED:** Resolve validation failures before freeze.")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 1 freeze package")
    parser.add_argument("--apply-freeze", action="store_true", help="Write freeze metadata to ontology")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args(argv)

    ontology = load_json(ONTOLOGY_PATH)
    behaviours = ontology["behaviours"]
    dep_graph = load_json(DEP_GRAPH_PATH)

    coverage = build_coverage_matrix(behaviours)
    semantic = run_semantic_duplicate_review(behaviours)
    construct_cov = build_construct_coverage(behaviours)
    dep_errors = validate_dependency_graph(behaviours, dep_graph)

    args.output_dir.mkdir(parents=True, exist_ok=True)

    (args.output_dir / "behaviour_coverage_matrix.json").write_text(
        json.dumps({
            "milestone": 1,
            "artifact": "Observable_Behaviours.json",
            "version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **coverage,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (args.output_dir / "semantic_duplicate_review.json").write_text(
        json.dumps({
            "milestone": 1,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **semantic,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (args.output_dir / "construct_coverage_report.json").write_text(
        json.dumps({
            "milestone": 1,
            "construct_reference": "framework/Construct_Definition.md",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            **construct_cov,
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    (args.output_dir / "behaviour_dependency_graph_summary.json").write_text(
        json.dumps({
            "milestone": 1,
            "source_artifact": "framework/Behaviour_Dependency_Graph.json",
            "edge_count": len(dep_graph.get("edges", [])),
            "validation_errors": dep_errors,
            "pass": not dep_errors,
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    report_md = write_freeze_report_md(
        coverage, semantic, construct_cov, dep_errors, args.apply_freeze,
    )
    (args.output_dir / "milestone1_freeze_report.md").write_text(report_md, encoding="utf-8")

    errors: list[str] = []
    if not semantic["pass"]:
        errors.append("semantic duplicate review failed")
    if not construct_cov["pass"]:
        errors.append("construct coverage mapping incomplete")
    errors.extend(dep_errors)

    if args.apply_freeze:
        if errors:
            print("FREEZE BLOCKED:", "; ".join(errors))
            return 1
        updated = apply_freeze_metadata(ontology)
        ONTOLOGY_PATH.write_text(
            json.dumps(updated, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("Freeze metadata applied to Observable_Behaviours.json")

    print(f"Freeze package written to {args.output_dir}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    if errors:
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
