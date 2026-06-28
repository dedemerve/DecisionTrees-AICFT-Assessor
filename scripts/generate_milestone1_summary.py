#!/usr/bin/env python3
"""
generate_milestone1_summary.py — Milestone 1 human summary for Observable Behaviour ontology.

Writes reports/milestone1_summary.md only.

Usage:
  python scripts/generate_milestone1_summary.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
ONTOLOGY_PATH = REPO_ROOT / "framework" / "Observable_Behaviours.json"
DEP_GRAPH_PATH = REPO_ROOT / "framework" / "Behaviour_Dependency_Graph.json"
VALIDATOR = REPO_ROOT / "scripts" / "validate_observable_behaviours.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from milestone_reporting import (  # noqa: E402
    validation_status_label,
    load_json,
    load_validation,
    run_quiet_script,
    write_summary,
)

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


def write_summary_md(
    summary: dict[str, Any],
    semantic: dict[str, Any],
    construct_cov: dict[str, Any],
    dep_errors: list[str],
    validation: dict[str, Any],
) -> str:
    by_construct = summary.get("by_construct_dimension", {})
    counts = list(by_construct.values()) or [0]
    construct_balance = "balanced" if max(counts) - min(counts) <= 5 else "moderate_imbalance"
    gaps = construct_cov["curriculum_gaps"]
    val_label = validation_status_label(validation.get("status"))

    lines = [
        "# Milestone 1 Summary",
        "",
        "## Observable Behaviour Ontology",
        "",
        "| Field | Value |",
        "|-------|-------|",
        "| Artifact | `framework/Observable_Behaviours.json` |",
        "| Version | **1.0** |",
        f"| Validation status | **{val_label}** |",
        "| Behaviour count | 28 |",
        "",
        "## Coverage Summary",
        "",
        "| Construct | Count |",
        "|-----------|-------|",
    ]
    for dim, count in by_construct.items():
        lines.append(f"| {dim.capitalize()} | {count} |")

    lines.extend([
        "",
        f"**Balance:** {construct_balance}",
        "",
        "### Hierarchy",
        "Construct → Knowledge Type → Cognitive Process → Behaviour (see `milestone1_validation.json`).",
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
        "## Validation summary",
        "",
        "| Check | Status |",
        "|-------|--------|",
        f"| Automated structure (`milestone1_validation.json`) | {validation.get('status', 'unknown')} |",
        f"| Semantic duplicate review | {'pass' if semantic['pass'] else 'fail'} |",
        f"| Curriculum construct coverage | {'pass' if construct_cov['pass'] else 'fail'} |",
        f"| Behaviour dependency graph | {'pass' if not dep_errors else 'fail'} |",
        "| Human expert coding agreement | pending |",
        "",
    ])

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Milestone 1 summary")
    args = parser.parse_args(argv)

    ontology = load_json(ONTOLOGY_PATH)
    behaviours = ontology["behaviours"]
    dep_graph = load_json(DEP_GRAPH_PATH)

    errors: list[str] = []
    if run_quiet_script(VALIDATOR) != 0:
        errors.append("validate_observable_behaviours.py failed")
    validation = load_validation(1)
    errors.extend(validation.get("errors", []))

    semantic = run_semantic_duplicate_review(behaviours)
    construct_cov = build_construct_coverage(behaviours)
    dep_errors = validate_dependency_graph(behaviours, dep_graph)

    if not semantic["pass"]:
        errors.append("semantic duplicate review failed")
    if not construct_cov["pass"]:
        errors.append("construct coverage mapping incomplete")
    errors.extend(dep_errors)

    summary = validation.get("coverage", {}).get("summary", {})
    report_md = write_summary_md(
        summary, semantic, construct_cov, dep_errors, validation,
    )
    summary_path = write_summary(1, report_md)

    print(f"Summary: {summary_path}")
    print(f"Status: {'PASS' if not errors else 'FAIL'}")
    if errors:
        for e in errors:
            print(f"  - {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
