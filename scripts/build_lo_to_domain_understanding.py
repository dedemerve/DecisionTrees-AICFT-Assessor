#!/usr/bin/env python3
"""
build_lo_to_domain_understanding.py — Generate LO_to_Domain_Understanding.json (Milestone 4 inference).

Second inference layer: ILO → emergent Domain with roles, rejected alternatives, counter-evidence.
Qualitative confidence only. Does not create new ILO or domain definitions.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
ILO_PATH = REPO / "framework" / "Learning_Objects.json"
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
OUT_PATH = REPO / "framework" / "LO_to_Domain_Understanding.json"

CONFIDENCE_BY_ROLE = {
    "primary": "high",
    "secondary": "moderate",
    "contextual": "low",
    "diagnostic": "baseline",
}

BASIS_BY_ROLE = {
    "primary": ["construct_alignment", "domain_convergence_logic", "frozen_ilo_reference"],
    "secondary": ["construct_alignment", "domain_convergence_logic", "frozen_ilo_reference"],
    "contextual": ["contextual_facilitation", "domain_convergence_logic", "frozen_ilo_reference"],
    "diagnostic": ["diagnostic_baseline", "frozen_ilo_reference"],
}

# (ilo_id, domain_id, role, rationale)
ILO_DOMAIN_PAIRS: list[tuple[str, str, str, str]] = [
    ("ILO_INSTANCE", "DU_DATA_REPRESENTATION", "primary",
     "Instance vocabulary anchors supervised representation construct."),
    ("ILO_INSTANCE", "DU_CLASSIFICATION_REASONING", "contextual",
     "Instances are classified but instance ILO alone does not demonstrate classification reasoning."),
    ("ILO_FEATURE", "DU_DATA_REPRESENTATION", "primary",
     "Feature-as-predictor is core to representational understanding."),
    ("ILO_FEATURE", "DU_GENERALISATION", "secondary",
     "Feature naming supports but does not alone demonstrate pattern generalisation."),
    ("ILO_LABEL", "DU_DATA_REPRESENTATION", "primary",
     "Label/target distinction is essential representational knowledge."),
    ("ILO_LABEL", "DU_CLASSIFICATION_REASONING", "secondary",
     "Labels are outputs of classification acts when assignment is evidenced."),
    ("ILO_DATASET", "DU_DATA_REPRESENTATION", "primary",
     "Labeled collections integrate instances, features, and labels."),
    ("ILO_TRAINING_ROLE", "DU_DATA_REPRESENTATION", "primary",
     "Training-data role explains why labeled datasets enable learning."),
    ("ILO_TRAINING_ROLE", "DU_REFLECTIVE_UNDERSTANDING", "secondary",
     "Learners may reflect on what data taught them about patterns."),
    ("ILO_THRESHOLD", "DU_THRESHOLD_REASONING", "primary",
     "Threshold ILO targets cutoff reasoning central to this strategic domain."),
    ("ILO_THRESHOLD", "DU_CLASSIFICATION_REASONING", "secondary",
     "Threshold application enables classification when execution is documented."),
    ("ILO_THRESHOLD", "DU_TREE_STRUCTURE_REASONING", "contextual",
     "Node cutoffs contextualize tree splits but do not alone demonstrate structure."),
    ("ILO_RULE", "DU_TREE_STRUCTURE_REASONING", "primary",
     "If-then rules articulate path logic within hierarchical structure."),
    ("ILO_RULE", "DU_CLASSIFICATION_REASONING", "secondary",
     "Rules execute classification along decision paths."),
    ("ILO_DECISION_TREE", "DU_TREE_STRUCTURE_REASONING", "primary",
     "Tree topology is the defining structural element of this domain."),
    ("ILO_DECISION_TREE", "DU_CLASSIFICATION_REASONING", "secondary",
     "Tree traversal produces classification outcomes when evidenced."),
    ("ILO_TREE_SPLIT", "DU_TREE_STRUCTURE_REASONING", "primary",
     "Node splits are structural decisions distinct from single-threshold drills."),
    ("ILO_TREE_SPLIT", "DU_THRESHOLD_REASONING", "secondary",
     "Split cutoffs contribute to strategic threshold reasoning at nodes."),
    ("ILO_CLASSIFICATION", "DU_CLASSIFICATION_REASONING", "primary",
     "Executable class assignment is the core procedural evidence for this domain."),
    ("ILO_CLASSIFICATION", "DU_TREE_STRUCTURE_REASONING", "contextual",
     "Classification at leaves contextualizes tree structure without proving topology mastery."),
    ("ILO_DT_WORKFLOW", "DU_TREE_STRUCTURE_REASONING", "primary",
     "Workflow sequencing evidences procedural structure comprehension."),
    ("ILO_CONFUSION_MATRIX", "DU_MODEL_EVALUATION", "primary",
     "Matrix literacy is foundational to evaluation reasoning."),
    ("ILO_MCR", "DU_MODEL_EVALUATION", "primary",
     "MCR computation and use supports error-rate evaluation."),
    ("ILO_SENSITIVITY", "DU_MODEL_EVALUATION", "primary",
     "Sensitivity links matrix cells to recall-oriented evaluation."),
    ("ILO_DATA_PATTERN", "DU_GENERALISATION", "primary",
     "Pattern citation is primary evidence for generalisation hypotheses."),
    ("ILO_DATA_PATTERN", "DU_THRESHOLD_REASONING", "secondary",
     "Patterns may motivate threshold choice when linked to separation evidence."),
    ("ILO_FEATURE_SELECTION", "DU_GENERALISATION", "primary",
     "Evidence-based feature choice demonstrates transfer from data to model design."),
    ("ILO_FEATURE_SELECTION", "DU_TREE_STRUCTURE_REASONING", "secondary",
     "Feature selection precedes structural splits in tree construction."),
    ("ILO_PARAMETER_OPTIMIZATION", "DU_PARAMETER_TUNING", "primary",
     "Iterative parameter search is the defining evidence for tuning domain."),
    ("ILO_PARAMETER_OPTIMIZATION", "DU_THRESHOLD_REASONING", "secondary",
     "Threshold search is one form of parameter optimization."),
    ("ILO_MODEL_EVALUATION", "DU_MODEL_EVALUATION", "primary",
     "Integrated performance interpretation is central to evaluation domain."),
    ("ILO_MODEL_EVALUATION", "DU_THRESHOLD_REASONING", "secondary",
     "Evaluation evidence informs threshold and model comparison decisions."),
    ("ILO_MODEL_EVALUATION", "DU_PARAMETER_TUNING", "contextual",
     "Interpreting exploration outcomes contextualizes parameter convergence."),
    ("ILO_MODEL_LIMITATION", "DU_REFLECTIVE_UNDERSTANDING", "primary",
     "Limitation awareness is reflective construct evidence."),
    ("ILO_MODEL_LIMITATION", "DU_MODEL_EVALUATION", "secondary",
     "Limits contextualize metric interpretation without replacing computation."),
    ("ILO_METACOGNITIVE_REFLECTION", "DU_REFLECTIVE_UNDERSTANDING", "primary",
     "Metacognitive articulation is direct reflective-domain evidence."),
    ("ILO_PRIOR_BELIEF", "DU_REFLECTIVE_UNDERSTANDING", "diagnostic",
     "Prior belief captures baseline for growth; excluded from mastery aggregation."),
]

REJECTED_ALTERNATIVES: dict[str, list[dict[str, str]]] = {
    "ILO_INSTANCE": [
        {"domain_id": "DU_THRESHOLD_REASONING", "reason_rejected": "Instance vocabulary does not evidence strategic cutoff reasoning."},
        {"domain_id": "DU_MODEL_EVALUATION", "reason_rejected": "Naming instances is not model evaluation literacy."},
    ],
    "ILO_FEATURE": [
        {"domain_id": "DU_THRESHOLD_REASONING", "reason_rejected": "Feature vocabulary alone does not demonstrate threshold comparison or selection."},
    ],
    "ILO_THRESHOLD": [
        {"domain_id": "DU_DATA_REPRESENTATION", "reason_rejected": "Threshold application is procedural/strategic, not representational vocabulary."},
        {"domain_id": "DU_REFLECTIVE_UNDERSTANDING", "reason_rejected": "Cutoff setting is not metacognitive reflection unless explicitly framed as learning process."},
    ],
    "ILO_RULE": [
        {"domain_id": "DU_THRESHOLD_REASONING", "reason_rejected": "Rule articulation is structural/procedural, not comparative threshold optimization."},
    ],
    "ILO_DECISION_TREE": [
        {"domain_id": "DU_DATA_REPRESENTATION", "reason_rejected": "Tree structure exceeds representational vocabulary scope."},
    ],
    "ILO_CLASSIFICATION": [
        {"domain_id": "DU_DATA_REPRESENTATION", "reason_rejected": "Classification execution is procedural evidence, not representational recall."},
        {"domain_id": "DU_REFLECTIVE_UNDERSTANDING", "reason_rejected": "Class assignment act is not reflective understanding without metacognitive framing."},
    ],
    "ILO_DT_WORKFLOW": [
        {"domain_id": "DU_CLASSIFICATION_REASONING", "reason_rejected": "Workflow ordering is structural sequencing, not classification outcome evidence."},
    ],
    "ILO_CONFUSION_MATRIX": [
        {"domain_id": "DU_CLASSIFICATION_REASONING", "reason_rejected": "Matrix literacy is evaluation construct, not classification execution."},
    ],
    "ILO_PARAMETER_OPTIMIZATION": [
        {"domain_id": "DU_CLASSIFICATION_REASONING", "reason_rejected": "Parameter search is strategic tuning, not a single classification act."},
    ],
    "ILO_METACOGNITIVE_REFLECTION": [
        {"domain_id": "DU_THRESHOLD_REASONING", "reason_rejected": "Reflection quality must not proxy strategic threshold mastery (leakage L5)."},
        {"domain_id": "DU_CLASSIFICATION_REASONING", "reason_rejected": "Metacognitive prose does not substitute for documented classification execution."},
    ],
    "ILO_PRIOR_BELIEF": [
        {"domain_id": "DU_THRESHOLD_REASONING", "reason_rejected": "Uninformed prior belief is diagnostic baseline, not threshold reasoning."},
        {"domain_id": "DU_CLASSIFICATION_REASONING", "reason_rejected": "Prior guesses are not evidenced classification acts."},
        {"domain_id": "DU_MODEL_EVALUATION", "reason_rejected": "Baseline belief is not evaluation literacy."},
    ],
}

COUNTER_EVIDENCE_TEMPLATES: dict[str, list[dict[str, Any]]] = {
    "conceptual": [{
        "description": "Terminology or vocabulary without converging application across ILOs",
        "effect": "Caps domain synthesis at weak/moderate; blocks strategic domain escalation",
        "source_type": "construct_leakage",
        "blocks_escalation": True,
    }],
    "procedural": [{
        "description": "Isolated procedural success without cross-task or multi-ILO convergence",
        "effect": "Moderate domain claim only until convergence requirements met",
        "source_type": "underconvergence",
        "blocks_escalation": True,
    }],
    "strategic": [{
        "description": "Single-source strategic evidence without comparison or justification",
        "effect": "Blocks strong Threshold, Evaluation, or Tuning domain claims",
        "source_type": "underconvergence",
        "blocks_escalation": True,
    }],
    "reflective": [{
        "description": "Eloquent reflection contradicting procedural or log evidence",
        "effect": "Cap reflective domain; do not inflate strategic claims (leakage L5)",
        "source_type": "contradictory_evidence",
        "blocks_escalation": True,
    }],
}


def build_record(ilo_id: str, domain_id: str, role: str, rationale: str, ilo_dim: str) -> dict[str, Any]:
    domain_dims = {
        "DU_DATA_REPRESENTATION": "conceptual",
        "DU_CLASSIFICATION_REASONING": "procedural",
        "DU_TREE_STRUCTURE_REASONING": "procedural",
        "DU_THRESHOLD_REASONING": "strategic",
        "DU_MODEL_EVALUATION": "strategic",
        "DU_PARAMETER_TUNING": "strategic",
        "DU_GENERALISATION": "strategic",
        "DU_REFLECTIVE_UNDERSTANDING": "reflective",
    }
    d_dim = domain_dims[domain_id]
    cross = ilo_dim != d_dim
    rec: dict[str, Any] = {
        "domain_id": domain_id,
        "mapping_role": role,
        "mapping_confidence": CONFIDENCE_BY_ROLE[role],
        "confidence_basis": list(BASIS_BY_ROLE[role]),
        "supporting_rationale": rationale,
        "counter_evidence": list(COUNTER_EVIDENCE_TEMPLATES.get(ilo_dim, COUNTER_EVIDENCE_TEMPLATES["conceptual"])),
        "construct_alignment": {
            "ilo_dimension": ilo_dim,
            "domain_dimension": d_dim,
            "cross_construct": cross,
        },
    }
    if cross:
        rec["cross_construct_rationale"] = (
            f"ILO construct dimension ({ilo_dim}) bridges to domain dimension ({d_dim}) "
            f"only when convergence requirements for {domain_id} are satisfied."
        )
    return rec


def build_mappings(ilos: dict[str, Any]) -> dict[str, Any]:
    bundles: dict[str, Any] = {}
    for ilo_id in sorted(ilos):
        ilo_dim = ilos[ilo_id]["construct_dimension"]
        pairs = [(i, d, r, t) for i, d, r, t in ILO_DOMAIN_PAIRS if i == ilo_id]
        if not pairs:
            raise ValueError(f"No domain mapping defined for {ilo_id}")
        records = [build_record(i, d, r, t, ilo_dim) for i, d, r, t in pairs]
        bundles[ilo_id] = {
            "ilo_id": ilo_id,
            "records": records,
            "rejected_alternatives": REJECTED_ALTERNATIVES.get(ilo_id, []),
        }
    return bundles


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    ilo_data = json.loads(ILO_PATH.read_text(encoding="utf-8"))
    domain_data = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    ilos = ilo_data["learning_objects"]
    domain_ids = set(domain_data["domains"])

    mappings = build_mappings(ilos)
    pair_count = sum(len(b["records"]) for b in mappings.values())

    for bundle in mappings.values():
        for rec in bundle["records"]:
            if rec["domain_id"] not in domain_ids:
                print(f"ERROR: unknown domain {rec['domain_id']}")
                return 1

    doc = {
        "artifact": "ilo_to_domain_understanding_mapping",
        "inference_layer": True,
        "confidence_policy": {
            "qualitative_only": True,
            "numeric_quantization": "deferred_to_Confidence_Model.json",
            "allowed_levels": ["high", "moderate", "low", "baseline"],
            "allowed_basis": list(BASIS_BY_ROLE["primary"]) + ["contextual_facilitation", "diagnostic_baseline"],
            "prohibited": "ad_hoc_numeric_confidence",
        },
        "design_constraint": domain_data.get("design_constraint"),
        "domain_ontology_reference": "framework/Domain_Understanding.json",
        "ilo_ontology_reference": "framework/Learning_Objects.json",
        "mapping_count": pair_count,
        "ilo_count": len(mappings),
        "rejected_alternative_count": sum(len(b["rejected_alternatives"]) for b in mappings.values()),
        "mappings": mappings,
    }

    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"ILO→Domain pairs: {pair_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
