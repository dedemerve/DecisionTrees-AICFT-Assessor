#!/usr/bin/env python3
"""
build_domain_to_ai_cft.py — Generate Domain_to_AI_CFT.json (Milestone 5 interpretive policy).

This is NOT a deterministic lookup table. Outputs provisional interpretive recommendations
for researcher review — never final AI-CFT competency claims.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
LO_DOMAIN_PATH = REPO / "framework" / "LO_to_Domain_Understanding.json"
AICFT_REF = REPO / "mappings" / "AICFT_assessment_framework.json"
OUT_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"

DESIGN_CONSTRAINT = (
    "A Domain Understanding construct does not represent an AI-CFT competency. Rather, it "
    "constitutes domain-specific evidence that may contribute to a provisional interpretation "
    "of selected AI-CFT indicators when sufficient converging evidence exists and no unresolved "
    "contradictions remain."
)

IMPLEMENTATION_CONSTRAINT = (
    "Domain_to_AI_CFT must not be implemented as a deterministic lookup table. AI-CFT claims "
    "are interpretive, provisional, and evidence-weighted. Each policy must specify theoretical "
    "rationale, minimum evidence requirements, convergence criteria, contradiction conditions, "
    "confidence ceiling, and explicit situations where escalation to the AI-CFT level is "
    "prohibited. No Domain may map directly to an AI-CFT competency solely because it is present."
)

VALID_AICFT = frozenset({
    "LO3.1.1", "LO3.1.2", "LO3.1.3", "LO3.2.1", "LO3.2.2", "LO3.2.3", "LO3.3.1",
})

SHARED_ESCALATION_BLOCKERS = [
    "domain_present_without_convergence",
    "single_evidence_source_for_deepen_claim",
    "unresolved_contradiction_across_sources",
    "construct_leakage_unmitigated",
    "prior_belief_used_as_mastery_evidence",
]

SHARED_NEVER_IMPLIES_GLOBAL = [
    "final_ai_cft_competency_claim",
    "automatic_acquire_deepen_create_classification",
    "researcher_bypass",
]

def contrib(
    lo: str,
    interpretation_type: str,
    verb: str,
    *,
    required_domains: list[str] | None = None,
    minimum_domain_strength: str = "moderate",
    minimum_evidence_sources: int = 1,
    required_convergence: str,
    allowed_confidence: str = "moderate",
    confidence_ceiling: str = "strong",
    contradiction_conditions: list[str] | None = None,
    escalation_blockers: list[str] | None = None,
    insufficient_when: list[str] | None = None,
    alternative_explanations: list[str] | None = None,
    never_implies: list[str] | None = None,
    theoretical_rationale: str,
) -> dict[str, Any]:
    return {
        "possible_ai_cft": [lo],
        "interpretation_type": interpretation_type,
        "interpretation_verb": verb,
        "required_domains": required_domains or [],
        "minimum_domain_strength": minimum_domain_strength,
        "minimum_evidence_sources": minimum_evidence_sources,
        "required_convergence": required_convergence,
        "allowed_confidence": allowed_confidence,
        "confidence_ceiling": confidence_ceiling,
        "contradiction_conditions": contradiction_conditions or [],
        "escalation_blockers": list(SHARED_ESCALATION_BLOCKERS) + (escalation_blockers or []),
        "insufficient_when": insufficient_when or [],
        "alternative_explanations": alternative_explanations or [],
        "researcher_review_required": True,
        "never_implies": list(SHARED_NEVER_IMPLIES_GLOBAL) + (never_implies or []),
        "theoretical_rationale": theoretical_rationale,
    }


DOMAIN_POLICIES: dict[str, dict[str, Any]] = {
    "DU_DATA_REPRESENTATION": {
        "construct_limitations": [
            "Supervised data representation does not imply tool operation or model optimization.",
            "Vocabulary mastery does not imply Deepen-level AI-CFT application skills.",
            "Does not imply ethical AI awareness, pedagogical design, or critical societal evaluation of AI.",
        ],
        "contributions": [
            contrib(
                "LO3.1.1", "supporting", "may_contribute_to",
                minimum_evidence_sources=1,
                required_convergence=(
                    "DU_DATA_REPRESENTATION at moderate+ with at least two representational facets "
                    "(e.g., feature/label/dataset) evidenced without feature-label confusion."
                ),
                allowed_confidence="moderate",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Only isolated terminology recall without structural distinction (leakage L4).",
                    "Representational vocabulary appears only in polished prose without DT anchors.",
                    "Single worksheet item proves one term but not integrated representation.",
                ],
                alternative_explanations=[
                    "General numeracy or generic data literacy rather than supervised-learning representation.",
                    "Memorized definitions without transfer to classification tasks.",
                ],
                never_implies=["LO3.2.1", "LO3.2.2", "LO3.2.3", "LO3.3.1"],
                theoretical_rationale=(
                    "Acquire-level AI-CFT conceptual indicators concern foundational vocabulary; "
                    "domain-specific representational evidence may support a provisional Acquire "
                    "interpretation but cannot alone warrant application-level claims."
                ),
            ),
            contrib(
                "LO3.1.2", "supporting", "may_indicate",
                required_domains=["DU_DATA_REPRESENTATION"],
                minimum_domain_strength="moderate",
                required_convergence=(
                    "Learner explains why labeled data enable learning, linking representation to "
                    "decision-tree purpose — not vocabulary list alone."
                ),
                allowed_confidence="weak",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Explanation of 'how AI works' lacks decision-tree or supervised-learning specificity.",
                    "Training-role understanding absent when LO3.1.2 claim is attempted.",
                ],
                never_implies=["LO3.2.2", "LO3.2.3"],
                theoretical_rationale=(
                    "LO3.1.2 concerns foundational mechanism understanding; representational domain "
                    "evidence contributes only when explanations connect data structure to learning."
                ),
            ),
        ],
    },
    "DU_CLASSIFICATION_REASONING": {
        "construct_limitations": [
            "Classification execution in a DT curriculum does not imply general AI problem-solving across domains.",
            "Correct labels without traceable rules do not support LO3.2.x Deepen claims.",
            "Does not imply tool selection (LO3.1.3) or Create-level solution design.",
        ],
        "contributions": [
            contrib(
                "LO3.2.2", "supporting", "may_contribute_to",
                required_domains=["DU_DATA_REPRESENTATION"],
                minimum_domain_strength="weak",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_CLASSIFICATION_REASONING at moderate+ with documented assignment acts and "
                    "multi-source corroboration (worksheet and log/recording where available)."
                ),
                confidence_ceiling="strong",
                insufficient_when=[
                    "Only worksheet evidence with no procedural corroboration from interactive sources.",
                    "Classification vocabulary in reflection without execution evidence.",
                    "Correct class label with no traceable threshold, rule, or path.",
                ],
                contradiction_conditions=[
                    "procedural_reflection_split",
                    "inconsistent_class_across_sources",
                ],
                escalation_blockers=["reflection_only_classification_claim"],
                alternative_explanations=[
                    "Pattern matching on worksheet format rather than classification reasoning.",
                    "Single-task procedural success without transfer.",
                ],
                never_implies=["LO3.1.3", "LO3.3.1", "pedagogical_competence", "ethical_ai_awareness"],
                theoretical_rationale=(
                    "LO3.2.2 Application Skills include threshold application and classification; "
                    "procedural classification domain evidence may support provisional Deepen "
                    "interpretation only with convergence and source diversity."
                ),
            ),
        ],
    },
    "DU_TREE_STRUCTURE_REASONING": {
        "construct_limitations": [
            "Tree structure literacy does not alone imply threshold optimization or test-set generalization.",
            "Workflow ordering without valid topology does not support strong LO3.2.2 claims.",
            "Does not imply UNESCO Create-level adaptation of AI solutions for novel contexts.",
        ],
        "contributions": [
            contrib(
                "LO3.2.2", "supporting", "may_contribute_to",
                required_domains=["DU_CLASSIFICATION_REASONING"],
                minimum_domain_strength="weak",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_TREE_STRUCTURE_REASONING at moderate+ with construction or multi-step "
                    "traversal plus at least one structural ILO corroborated across sources."
                ),
                insufficient_when=[
                    "Static diagram copying without node-level split rationale.",
                    "Single-threshold drill framed as full tree competence.",
                ],
                never_implies=["LO3.2.3", "LO3.3.1"],
                theoretical_rationale=(
                    "Decision-tree construction and rule articulation are within LO3.2.2 scope; "
                    "structural domain evidence contributes when topology and path logic cohere."
                ),
            ),
            contrib(
                "LO3.1.2", "supporting", "may_indicate",
                minimum_evidence_sources=1,
                required_convergence=(
                    "Learner explains how hierarchical feature tests lead to classification outcomes."
                ),
                allowed_confidence="weak",
                confidence_ceiling="moderate",
                insufficient_when=["Workflow recall without structural understanding of splits.",
                                   "Tree diagram copied without explaining split logic."],
                theoretical_rationale=(
                    "Acquire-level 'how AI works' may be weakly indicated by coherent tree-structure "
                    "explanations — not by procedural ordering alone."
                ),
            ),
            contrib(
                "LO3.2.1", "supporting", "may_indicate",
                required_domains=["DU_TREE_STRUCTURE_REASONING", "DU_MODEL_EVALUATION"],
                minimum_domain_strength="moderate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "Learner compares multiple models/trees or variables with performance evidence — "
                    "evaluate → select → apply cycle documented across sources."
                ),
                allowed_confidence="moderate",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Single tree construction without comparison across alternatives.",
                    "Tool use without performance-based selection rationale.",
                ],
                never_implies=["LO3.1.3", "LO3.3.1"],
                theoretical_rationale=(
                    "LO3.2.1 requires evaluate-select-apply with tool-mediated model comparison; "
                    "structural and evaluation domains together may indicate this indicator."
                ),
            ),
        ],
    },
    "DU_THRESHOLD_REASONING": {
        "construct_limitations": [
            "Threshold reasoning in classroom DT tasks does not imply critical evaluation of AI in society.",
            "Comparative cutoff judgment does not imply ethical awareness or pedagogical competence.",
            "Does not imply validated tool selection for novel educational contexts (LO3.1.3).",
            "Does not imply Create-level design of AI-supported learning innovations.",
        ],
        "contributions": [
            contrib(
                "LO3.2.2", "contributing", "may_contribute_to",
                required_domains=["DU_MODEL_EVALUATION"],
                minimum_domain_strength="moderate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_THRESHOLD_REASONING at moderate+ with comparison or justification citing "
                    "performance evidence; multi-source required for confidence above moderate."
                ),
                confidence_ceiling="strong",
                insufficient_when=[
                    "Only worksheet evidence without procedural or log corroboration.",
                    "Single threshold application without comparison or justification context.",
                    "Contradictory screen recording undermines worksheet threshold claims.",
                    "Reflection praises thresholds but CODAP/log shows weak execution (leakage L5).",
                ],
                contradiction_conditions=[
                    "threshold_misconception",
                    "high_reflection_weak_procedural",
                    "worksheet_video_source_asymmetry",
                ],
                escalation_blockers=[
                    "single_threshold_application_only",
                    "reflection_inflates_strategic_without_performance_evidence",
                ],
                alternative_explanations=[
                    "Arithmetic manipulation of cutoff values without strategic reasoning.",
                    "Memorized 'best threshold' from answer key patterns.",
                ],
                never_implies=[
                    "critical_ai_evaluation",
                    "ethical_awareness",
                    "pedagogical_competence",
                    "LO3.1.3",
                    "LO3.3.1",
                ],
                theoretical_rationale=(
                    "LO3.2.2 explicitly includes threshold optimization and model behaviour "
                    "interpretation; strategic threshold domain evidence is primary contributory "
                    "evidence but never sufficient alone for a final Deepen claim."
                ),
            ),
            contrib(
                "LO3.2.3", "supporting", "may_indicate",
                required_domains=["DU_THRESHOLD_REASONING", "DU_PARAMETER_TUNING"],
                minimum_domain_strength="moderate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "Iterative threshold refinement evidenced across tasks with performance-linked "
                    "justification — not one-off cutoff selection."
                ),
                allowed_confidence="moderate",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Threshold comparison without iterative improvement trajectory.",
                    "Problem-solving claim based on single worksheet row.",
                ],
                theoretical_rationale=(
                    "LO3.2.3 problem-solving requires iterative refinement; threshold reasoning "
                    "may weakly indicate this indicator when paired with tuning evidence."
                ),
            ),
        ],
    },
    "DU_MODEL_EVALUATION": {
        "construct_limitations": [
            "Metric literacy in DT classroom tasks does not imply broad AI evaluation competence.",
            "Confusion-matrix interpretation does not imply critical societal AI critique.",
            "Does not imply tool validation or selection (LO3.1.3).",
        ],
        "contributions": [
            contrib(
                "LO3.2.2", "supporting", "may_contribute_to",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_MODEL_EVALUATION at moderate+ spanning matrix and metric or interpretation "
                    "components with multi-source corroboration for strong recommendations."
                ),
                insufficient_when=[
                    "Formula recall without numeric or matrix application.",
                    "Single confusion-matrix cell without relational interpretation.",
                ],
                contradiction_conditions=["matrix_interpretation_contradicts_metrics"],
                never_implies=["LO3.1.3", "ethical_ai_awareness", "LO3.3.1"],
                theoretical_rationale=(
                    "Model behaviour interpretation is within LO3.2.2; evaluation domain evidence "
                    "supports provisional Deepen recommendations when convergent."
                ),
            ),
            contrib(
                "LO3.2.3", "supporting", "may_indicate",
                required_domains=["DU_MODEL_EVALUATION"],
                required_convergence=(
                    "Evaluation evidence used to drive iterative performance improvement decisions."
                ),
                allowed_confidence="moderate",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Metrics computed but not used to revise model decisions.",
                    "Evaluation narrative without matrix or metric artifacts.",
                ],
                theoretical_rationale=(
                    "LO3.2.3 includes evaluating and improving performance; evaluation domain "
                    "may indicate this when linked to refinement actions."
                ),
            ),
            contrib(
                "LO3.1.1", "supporting", "may_indicate",
                required_convergence="Metric definitions (MCR, sensitivity) correctly stated with matrix context.",
                allowed_confidence="weak",
                confidence_ceiling="weak",
                insufficient_when=[
                    "Metric vocabulary without computation or interpretation context.",
                    "Formula stated with no confusion-matrix or numeric application.",
                ],
                theoretical_rationale=(
                    "Acquire-level conceptual metric knowledge may be weakly indicated by evaluation "
                    "literacy — not by procedural computation alone."
                ),
            ),
        ],
    },
    "DU_PARAMETER_TUNING": {
        "construct_limitations": [
            "Parameter exploration in CODAP/tables does not imply Create-level AI solution design.",
            "Iterative clicking without interpreted convergence is not optimization competence.",
            "Does not imply ethical or pedagogical AI competencies.",
        ],
        "contributions": [
            contrib(
                "LO3.2.3", "contributing", "may_contribute_to",
                required_domains=["DU_MODEL_EVALUATION"],
                minimum_domain_strength="weak",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_PARAMETER_TUNING at moderate+ with traceable exploration trail and "
                    "defended convergence across at least two evidence sources."
                ),
                confidence_ceiling="strong",
                insufficient_when=[
                    "Single final parameter with no exploration trail.",
                    "High click volume without meaningful state change (leakage L3).",
                    "Table completion without performance interpretation.",
                ],
                contradiction_conditions=["tool_fluency_only", "exploration_without_convergence"],
                never_implies=["LO3.3.1", "LO3.1.3", "pedagogical_competence"],
                theoretical_rationale=(
                    "LO3.2.3 centres iterative problem solving; parameter tuning domain evidence "
                    "is primary contributory evidence for provisional Deepen problem-solving interpretation."
                ),
            ),
            contrib(
                "LO3.2.2", "supporting", "may_indicate",
                required_domains=["DU_PARAMETER_TUNING"],
                required_convergence="Optimization linked to threshold performance comparison.",
                allowed_confidence="moderate",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Optimization isolated from threshold/classification outcomes.",
                    "Parameter table filled without defended final choice.",
                ],
                theoretical_rationale=(
                    "Parameter search supports LO3.2.2 application skills when tied to model behaviour."
                ),
            ),
            contrib(
                "LO3.1.3", "supporting", "may_indicate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "Learner selects and validates an appropriate interactive tool (e.g. CODAP) "
                    "with documented setup for the DT task — not navigation fluency alone."
                ),
                allowed_confidence="weak",
                confidence_ceiling="moderate",
                insufficient_when=[
                    "Tool named without validation or task-appropriateness rationale.",
                    "Digital fluency without meaningful model-building actions (leakage L3).",
                ],
                contradiction_conditions=["tool_fluency_only"],
                never_implies=["LO3.2.3", "LO3.3.1", "pedagogical_competence"],
                theoretical_rationale=(
                    "LO3.1.3 concerns locating and validating AI tools; parameter tuning with "
                    "documented tool setup may weakly indicate this Acquire indicator."
                ),
            ),
        ],
    },
    "DU_GENERALISATION": {
        "construct_limitations": [
            "Pattern transfer within DT curriculum does not imply full AI Create competency.",
            "Feature hypothesis on one dataset does not imply designing novel AI educational solutions.",
            "Known v1.0 limitation: partial proxy coverage via reasoning ILOs only.",
        ],
        "contributions": [
            contrib(
                "LO3.2.3", "supporting", "may_contribute_to",
                required_domains=["DU_GENERALISATION", "DU_CLASSIFICATION_REASONING"],
                minimum_domain_strength="moderate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "DU_GENERALISATION at moderate+ with pattern evidence applied on a different "
                    "task or source than initial example."
                ),
                insufficient_when=[
                    "Generic 'pattern' language without feature/class reference.",
                    "No cross-context application occasion (cap at moderate).",
                    "Transfer claim supported only by reflective prose.",
                ],
                confidence_ceiling="moderate",
                never_implies=["LO3.3.1", "full_create_competence"],
                theoretical_rationale=(
                    "Transferable problem solving within LO3.2.3 may be supported by "
                    "generalisation domain evidence when cross-context coherence is documented."
                ),
            ),
            contrib(
                "LO3.3.1", "supporting", "may_indicate",
                required_domains=["DU_GENERALISATION", "DU_PARAMETER_TUNING"],
                minimum_domain_strength="moderate",
                minimum_evidence_sources=2,
                required_convergence=(
                    "Early Create indicator only: learner adapts model approach based on test or "
                    "holdout evidence with documented transfer — never from pattern citation alone."
                ),
                allowed_confidence="very_weak",
                confidence_ceiling="weak",
                insufficient_when=[
                    "No test-set or novel-context application evidence.",
                    "Generalisation claim from single classroom example only.",
                ],
                escalation_blockers=["create_claim_from_single_task_family"],
                never_implies=["confirmed_create_competence", "LO3.2.1"],
                theoretical_rationale=(
                    "LO3.3.1 Create is a high bar; generalisation domain may weakly indicate early "
                    "Create potential only with multi-domain convergence — never as automatic output."
                ),
            ),
        ],
    },
    "DU_REFLECTIVE_UNDERSTANDING": {
        "construct_limitations": [
            "Reflective DT awareness does not substitute for procedural or strategic performance evidence.",
            "Writing quality does not imply LO3.2.x Deepen competence (leakage L5).",
            "Does not imply tool selection, optimization, or Create-level design.",
        ],
        "contributions": [
            contrib(
                "LO3.1.2", "supporting", "may_indicate",
                minimum_evidence_sources=1,
                required_convergence=(
                    "Reflection accurately names DT concepts learned and misconceptions with "
                    "concept-specific content — not generic study comments."
                ),
                allowed_confidence="weak",
                confidence_ceiling="weak",
                insufficient_when=[
                    "Polished prose without DT conceptual anchors (leakage L1).",
                    "Reflection contradicts procedural/log evidence.",
                    "Only ILO_PRIOR_BELIEF diagnostic present.",
                ],
                contradiction_conditions=["high_reflection_weak_procedural", "procedural_reflection_split"],
                escalation_blockers=[
                    "reflection_drives_deepen_without_procedural_corroboration",
                    "reflection_quality_inflates_strategic_claims",
                ],
                never_implies=["LO3.2.2", "LO3.2.3", "LO3.3.1", "LO3.2.1"],
                theoretical_rationale=(
                    "Reflective domain evidence informs researcher interpretation and weak Acquire "
                    "indicators only; it must never escalate to Deepen or Create without independent "
                    "procedural/strategic domain convergence."
                ),
            ),
        ],
    },
}

# Add domain_id to policies
for domain_id, policy in DOMAIN_POLICIES.items():
    policy["domain_id"] = domain_id


def build_document(domain_doc: dict[str, Any]) -> dict[str, Any]:
    domain_ids = set(domain_doc["domains"])
    if set(DOMAIN_POLICIES) != domain_ids:
        missing = domain_ids - set(DOMAIN_POLICIES)
        extra = set(DOMAIN_POLICIES) - domain_ids
        raise ValueError(f"Policy/domain mismatch missing={missing} extra={extra}")

    contribution_count = sum(len(p["contributions"]) for p in DOMAIN_POLICIES.values())

    return {
        "artifact": "domain_to_ai_cft_interpretive_policy",
        "interpretation_layer": True,
        "design_constraint": DESIGN_CONSTRAINT,
        "implementation_constraint": IMPLEMENTATION_CONSTRAINT,
        "terminology": {
            "artifact_type": "interpretive_policy",
            "not_artifact_type": "deterministic_competency_mapping",
            "output": "interpretive_recommendation",
            "not_output": "final_ai_cft_competency_claim",
            "forbidden_schema_fields": ["maps_to", "is_final", "automatic_claim"],
            "interpretation_verbs": ["may_contribute_to", "may_indicate", "supports", "contributes"],
            "claim_chain": [
                "evidence",
                "observable_behaviour",
                "instructional_learning_object",
                "domain_understanding",
                "interpretive_recommendation",
                "researcher_review",
                "ai_cft_competency_claim",
            ],
        },
        "confidence_policy": {
            "qualitative_only": True,
            "numeric_quantization": "deferred_to_Confidence_Model.json",
            "allowed_levels": ["very_weak", "weak", "moderate", "strong"],
            "prohibited": "ad_hoc_numeric_confidence",
        },
        "domain_ontology_reference": "framework/Domain_Understanding.json",
        "domain_ontology_version": domain_doc.get("framework_version", "1.0"),
        "aicft_reference": "mappings/AICFT_assessment_framework.json",
        "aicft_framework": "UNESCO AI Competency Framework for Teachers (AI-CFT) 2024",
        "aicft_aspect": "Aspect 3: AI foundations and applications",
        "domain_policy_count": len(DOMAIN_POLICIES),
        "contribution_count": contribution_count,
        "policies": DOMAIN_POLICIES,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    domain_doc = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    lo_domain = json.loads(LO_DOMAIN_PATH.read_text(encoding="utf-8"))

    for policy in DOMAIN_POLICIES.values():
        for c in policy["contributions"]:
            for lo in c["possible_ai_cft"]:
                if lo not in VALID_AICFT:
                    print(f"ERROR: unknown AI-CFT code {lo}")
                    return 1

    doc = build_document(domain_doc)
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Domain policies: {doc['domain_policy_count']}, contributions: {doc['contribution_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
