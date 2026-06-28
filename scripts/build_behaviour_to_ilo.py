#!/usr/bin/env python3
"""
build_behaviour_to_ilo.py — Generate Behaviour_to_ILO.json (Milestone 3 inference layer).

Confidence is qualitative only; numeric quantization deferred to Confidence_Model.json.
Does not create new OB or ILO definitions.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
OB_PATH = REPO / "framework" / "Observable_Behaviours.json"
ILO_PATH = REPO / "framework" / "Learning_Objects.json"
OUT_PATH = REPO / "framework" / "Behaviour_to_ILO.json"

CONFIDENCE_BY_ROLE = {
    "primary": "high",
    "secondary": "moderate",
    "contextual": "low",
    "diagnostic": "baseline",
}

BASIS_BY_ROLE = {
    "primary": ["construct_alignment", "instructional_consensus", "frozen_ilo_behaviour_link"],
    "secondary": ["construct_alignment", "instructional_consensus", "frozen_ilo_behaviour_link"],
    "contextual": ["instructional_consensus", "contextual_facilitation", "frozen_ilo_behaviour_link"],
    "diagnostic": ["diagnostic_baseline", "frozen_ilo_behaviour_link"],
}

PAIR_RATIONALE: dict[tuple[str, str], str] = {
    ("OB_CON_001", "ILO_INSTANCE"): "Correct use of instance/object vocabulary indicates grasp of the unit of classification.",
    ("OB_CON_001", "ILO_FEATURE"): "Learner names or explains features as predictive inputs.",
    ("OB_CON_001", "ILO_LABEL"): "Learner distinguishes labels/targets from features.",
    ("OB_CON_001", "ILO_DATASET"): "Learner references labeled collections when explaining vocabulary.",
    ("OB_CON_002", "ILO_THRESHOLD"): "Learner contrasts threshold/split from related concepts.",
    ("OB_CON_002", "ILO_RULE"): "Learner distinguishes rules from whole-tree structure.",
    ("OB_CON_002", "ILO_DECISION_TREE"): "Learner differentiates tree components from isolated rules or thresholds.",
    ("OB_CON_003", "ILO_DECISION_TREE"): "Explanation links features and thresholds to tree-based classification.",
    ("OB_CON_003", "ILO_CLASSIFICATION"): "Mechanism explanation includes assigning class outcomes.",
    ("OB_CON_004", "ILO_DATASET"): "Explanation references labeled examples as learning material.",
    ("OB_CON_004", "ILO_TRAINING_ROLE"): "Learner explains why training data enables pattern learning.",
    ("OB_CON_005", "ILO_CONFUSION_MATRIX"): "Learner states or explains confusion-matrix structure or cells.",
    ("OB_CON_005", "ILO_MCR"): "Learner recalls or explains misclassification rate definition.",
    ("OB_CON_005", "ILO_SENSITIVITY"): "Learner recalls or explains sensitivity/true positive rate.",
    ("OB_CON_006", "ILO_CONFUSION_MATRIX"): "Learner interprets relationships among TP/TN/FP/FN.",
    ("OB_CON_006", "ILO_MODEL_EVALUATION"): "Matrix interpretation supports evaluation literacy.",
    ("OB_PRO_001", "ILO_THRESHOLD"): "Learner applies a stated cutoff to partition or classify cases.",
    ("OB_PRO_001", "ILO_CLASSIFICATION"): "Threshold application yields documented class assignment.",
    ("OB_PRO_002", "ILO_RULE"): "Path traversal follows explicit if-then conditions.",
    ("OB_PRO_002", "ILO_DECISION_TREE"): "Multi-step path reflects tree structure traversal.",
    ("OB_PRO_002", "ILO_CLASSIFICATION"): "Path ends in class label assignment.",
    ("OB_PRO_003", "ILO_DECISION_TREE"): "Learner authors or extends tree structure with splits and branches.",
    ("OB_PRO_003", "ILO_LABEL"): "Class labels assigned at nodes during construction.",
    ("OB_PRO_003", "ILO_TREE_SPLIT"): "Learner selects feature/threshold at node positions.",
    ("OB_PRO_004", "ILO_DT_WORKFLOW"): "Learner orders construction steps in valid sequence.",
    ("OB_PRO_005", "ILO_RULE"): "Learner states explicit if-then decision rule.",
    ("OB_PRO_006", "ILO_LABEL"): "Learner assigns class label at tree position.",
    ("OB_PRO_006", "ILO_CLASSIFICATION"): "Label assignment completes classification act.",
    ("OB_PRO_007", "ILO_THRESHOLD"): "Learner sets numeric or categorical cutoff at node.",
    ("OB_PRO_007", "ILO_TREE_SPLIT"): "Threshold setting is part of node split decision.",
    ("OB_PRO_008", "ILO_PARAMETER_OPTIMIZATION"): "Meaningful tool actions change splits/thresholds iteratively.",
    ("OB_PRO_009", "ILO_MCR"): "Learner computes or records MCR from given counts.",
    ("OB_PRO_009", "ILO_SENSITIVITY"): "Learner computes or records sensitivity from given counts.",
    ("OB_STR_001", "ILO_MODEL_EVALUATION"): "Comparison cites performance indicators across alternatives.",
    ("OB_STR_001", "ILO_PARAMETER_OPTIMIZATION"): "Threshold comparison is part of parameter search.",
    ("OB_STR_001", "ILO_THRESHOLD"): "Compared alternatives are threshold values.",
    ("OB_STR_002", "ILO_FEATURE_SELECTION"): "Learner selects feature with stated criterion.",
    ("OB_STR_002", "ILO_FEATURE"): "Selection references named predictive feature.",
    ("OB_STR_002", "ILO_THRESHOLD"): "Selection may include threshold choice at node.",
    ("OB_STR_002", "ILO_TREE_SPLIT"): "Feature-threshold pair defines structural split.",
    ("OB_STR_003", "ILO_MODEL_EVALUATION"): "Justification references model performance evidence.",
    ("OB_STR_003", "ILO_PARAMETER_OPTIMIZATION"): "Rationale defends parameter or threshold choice.",
    ("OB_STR_004", "ILO_DATA_PATTERN"): "Learner cites observed pattern suggesting class separation.",
    ("OB_STR_004", "ILO_FEATURE"): "Named feature is linked to cited pattern.",
    ("OB_STR_004", "ILO_FEATURE_SELECTION"): "Pattern evidence informs feature hypothesis.",
    ("OB_STR_005", "ILO_CONFUSION_MATRIX"): "Trade-off reasoning references error types or cells.",
    ("OB_STR_005", "ILO_MODEL_EVALUATION"): "Trade-off discourse evaluates model consequences.",
    ("OB_STR_006", "ILO_PARAMETER_OPTIMIZATION"): "Multiple parameter trials with observed outcomes.",
    ("OB_STR_007", "ILO_MODEL_EVALUATION"): "Synthesis links exploration results to final evaluation.",
    ("OB_STR_007", "ILO_PARAMETER_OPTIMIZATION"): "Final choice integrates iterative parameter trials.",
    ("OB_STR_008", "ILO_MCR"): "Learner identifies best MCR across conditions.",
    ("OB_STR_008", "ILO_PARAMETER_OPTIMIZATION"): "Optimization selects best-performing configuration.",
    ("OB_STR_009", "ILO_MODEL_EVALUATION"): "Learner interprets model feedback for practical decision.",
    ("OB_REF_001", "ILO_METACOGNITIVE_REFLECTION"): "Learner reflects on own DT learning or confusion.",
    ("OB_REF_002", "ILO_METACOGNITIVE_REFLECTION"): "Limitation discourse includes metacognitive commentary.",
    ("OB_REF_002", "ILO_MODEL_LIMITATION"): "Learner articulates model limits or uncertainty.",
    ("OB_REF_002", "ILO_TRAINING_ROLE"): "Limitation references data or learning constraints.",
    ("OB_REF_003", "ILO_METACOGNITIVE_REFLECTION"): "Belief revision includes reflective awareness.",
    ("OB_REF_003", "ILO_PRIOR_BELIEF"): "Documented change from prior to posterior belief.",
    ("OB_REF_004", "ILO_PRIOR_BELIEF"): "Uninformed prior stated before structured evidence.",
}

CROSS_CONSTRUCT_RATIONALE: dict[tuple[str, str], str] = {
    ("OB_CON_003", "ILO_CLASSIFICATION"): (
        "Conceptual mechanism explanation can support procedural classification ILO only when "
        "the learner explicitly links mechanism to class assignment, not vocabulary alone."
    ),
    ("OB_CON_006", "ILO_MODEL_EVALUATION"): (
        "Conceptual matrix interpretation enables strategic evaluation literacy as a bridging "
        "construct; requires explicit performance interpretation, not cell recall alone."
    ),
    ("OB_REF_002", "ILO_TRAINING_ROLE"): (
        "Reflective limitation discourse may reference training-data constraints without "
        "demonstrating full conceptual training-role mastery."
    ),
}

REJECTED_ALTERNATIVES: dict[str, list[tuple[str, str]]] = {
    "OB_CON_001": [
        ("ILO_THRESHOLD", "Vocabulary recall does not evidence threshold application."),
        ("ILO_RULE", "Terminology use alone does not evidence rule articulation."),
    ],
    "OB_CON_003": [
        ("ILO_THRESHOLD", "Mechanism explanation without application does not support threshold ILO."),
        ("ILO_PARAMETER_OPTIMIZATION", "Explanation is not parameter search."),
    ],
    "OB_PRO_001": [
        ("ILO_PARAMETER_OPTIMIZATION", "Single threshold application is not optimization."),
        ("ILO_RULE", "Applying a cutoff is not equivalent to stating a full if-then rule."),
    ],
    "OB_PRO_005": [
        ("ILO_THRESHOLD", "Rule articulation is not threshold setting."),
        ("ILO_DECISION_TREE", "Single rule statement does not evidence full tree construction."),
    ],
    "OB_STR_001": [
        ("ILO_RULE", "Threshold comparison does not require if-then rule articulation."),
        ("ILO_FEATURE", "Comparison targets thresholds, not feature vocabulary."),
    ],
    "OB_STR_002": [
        ("ILO_DECISION_TREE", "Feature/threshold selection is not full tree construction."),
        ("ILO_MCR", "Selection criterion need not include metric computation."),
    ],
    "OB_STR_004": [
        ("ILO_THRESHOLD", "Pattern citation is not threshold application."),
        ("ILO_CLASSIFICATION", "Feature hypothesis is not case classification."),
    ],
    "OB_PRO_008": [
        ("ILO_CLASSIFICATION", "Tool manipulation alone does not document classification outcome."),
        ("ILO_RULE", "Exploration actions are not rule articulation."),
    ],
    "OB_REF_001": [
        ("ILO_MODEL_EVALUATION", "Reflection without performance evidence does not support evaluation ILO."),
        ("ILO_THRESHOLD", "Metacognitive reflection is not threshold reasoning."),
    ],
}

COUNTER_EVIDENCE: dict[str, list[dict[str, Any]]] = {
    "OB_CON": [
        {
            "description": "Terminology recall without application or distinction",
            "effect": "Caps mapping at moderate qualitative confidence; blocks procedural ILO escalation",
            "source_type": "construct_leakage",
            "blocks_escalation": True,
            "applies_to_roles": ["primary", "secondary"],
        },
    ],
    "OB_PRO": [
        {
            "description": "Correct execution contradicted by threshold misconception in another evidence unit",
            "effect": "Blocks primary ILO_THRESHOLD or ILO_CLASSIFICATION until contradiction resolved",
            "source_type": "contradictory_evidence",
            "blocks_escalation": True,
            "applies_to_roles": ["primary", "secondary"],
        },
        {
            "description": "Execution without interpretable criterion in learner text",
            "effect": "Procedural ILO supported at moderate; strategic ILO requires separate evidence",
            "source_type": "construct_leakage",
            "blocks_escalation": False,
            "applies_to_roles": ["primary"],
        },
    ],
    "OB_STR": [
        {
            "description": "Fluent justification without performance or data linkage",
            "effect": "Caps confidence at low; CLT-A leakage guard (PAT-BLOCK-001)",
            "source_type": "construct_leakage",
            "blocks_escalation": True,
            "applies_to_roles": ["primary", "secondary"],
        },
        {
            "description": "Threshold misconception documented in worksheet or log while strategic claim made",
            "effect": "Blocks ILO_THRESHOLD and ILO_PARAMETER_OPTIMIZATION primary inference",
            "source_type": "misconception",
            "blocks_escalation": True,
            "applies_to_roles": ["primary"],
        },
    ],
    "OB_REF": [
        {
            "description": "Excellent reflection with incorrect threshold or classification elsewhere",
            "effect": "Reflective ILO only; blocks procedural/strategic ILO escalation (CLT-D)",
            "source_type": "contradictory_evidence",
            "blocks_escalation": True,
            "applies_to_roles": ["primary", "secondary"],
        },
        {
            "description": "Generic study-habit reflection without DT content",
            "effect": "Null or baseline reflective mapping only",
            "source_type": "construct_leakage",
            "blocks_escalation": True,
            "applies_to_roles": ["primary"],
        },
    ],
}

def _behaviour_primary_ilo_map(ilos: dict[str, Any]) -> dict[str, str]:
    behaviour_to_ilos: dict[str, list[str]] = defaultdict(list)
    for iid, ilo in ilos.items():
        for ob in ilo.get("related_behaviours", []):
            behaviour_to_ilos[ob].append(iid)
    return {ob: sorted(linked)[0] for ob, linked in sorted(behaviour_to_ilos.items())}


def _load_primary_ilo() -> dict[str, str]:
    ilos = json.loads(ILO_PATH.read_text(encoding="utf-8"))["learning_objects"]
    return _behaviour_primary_ilo_map(ilos)


PRIMARY_ILO: dict[str, str] = _load_primary_ilo()

# Explicit secondary ILOs (remaining same-dimension links after primary)
SECONDARY_ILO: dict[str, set[str]] = {
    "OB_CON_001": {"ILO_FEATURE", "ILO_INSTANCE", "ILO_LABEL"},
    "OB_CON_002": {"ILO_THRESHOLD", "ILO_RULE"},
    "OB_CON_003": {"ILO_DECISION_TREE"},
    "OB_CON_004": {"ILO_TRAINING_ROLE"},
    "OB_CON_006": set(),
    "OB_CON_005": {"ILO_MCR", "ILO_SENSITIVITY"},
    "OB_PRO_001": {"ILO_THRESHOLD"},
    "OB_PRO_002": {"ILO_RULE", "ILO_DECISION_TREE"},
    "OB_PRO_003": {"ILO_LABEL", "ILO_TREE_SPLIT"},
    "OB_PRO_006": {"ILO_LABEL"},
    "OB_PRO_007": {"ILO_TREE_SPLIT"},
    "OB_PRO_009": {"ILO_SENSITIVITY"},
    "OB_STR_001": {"ILO_PARAMETER_OPTIMIZATION", "ILO_THRESHOLD"},
    "OB_STR_002": {"ILO_FEATURE_SELECTION", "ILO_THRESHOLD", "ILO_TREE_SPLIT"},
    "OB_STR_003": {"ILO_PARAMETER_OPTIMIZATION"},
    "OB_STR_004": {"ILO_FEATURE", "ILO_FEATURE_SELECTION"},
    "OB_STR_005": {"ILO_MODEL_EVALUATION"},
    "OB_STR_007": {"ILO_PARAMETER_OPTIMIZATION"},
    "OB_STR_008": {"ILO_PARAMETER_OPTIMIZATION"},
    "OB_REF_002": {"ILO_MODEL_LIMITATION", "ILO_TRAINING_ROLE"},
    "OB_REF_003": {"ILO_PRIOR_BELIEF"},
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def behaviour_prefix(bid: str) -> str:
    return bid.rsplit("_", 1)[0]


def assign_role(behaviour_id: str, ilo_id: str, primary: str) -> str:
    if behaviour_id == "OB_REF_004":
        return "diagnostic"
    if ilo_id == primary:
        return "primary"
    if ilo_id in SECONDARY_ILO.get(behaviour_id, set()):
        return "secondary"
    return "contextual"


def build_counter_evidence(behaviour_id: str, role: str) -> list[dict[str, Any]]:
    prefix = behaviour_prefix(behaviour_id)
    out = []
    for item in COUNTER_EVIDENCE.get(prefix, []):
        applies = item.get("applies_to_roles", [])
        if not applies or role in applies:
            out.append({k: v for k, v in item.items() if k != "applies_to_roles"})
    return out


def build_record(
    behaviour_id: str,
    ilo_id: str,
    behaviours: dict[str, Any],
    ilos: dict[str, Any],
) -> dict[str, Any]:
    primary = PRIMARY_ILO[behaviour_id]
    role = assign_role(behaviour_id, ilo_id, primary)
    beh_dim = behaviours[behaviour_id]["construct_dimension"]
    ilo_dim = ilos[ilo_id]["construct_dimension"]
    cross = beh_dim != ilo_dim

    basis = list(BASIS_BY_ROLE[role])
    if cross:
        if "construct_alignment" in basis:
            basis.remove("construct_alignment")
        if "contextual_facilitation" not in basis:
            basis.append("cross_construct_bridge")

    record: dict[str, Any] = {
        "ilo_id": ilo_id,
        "mapping_role": role,
        "mapping_confidence": CONFIDENCE_BY_ROLE[role],
        "confidence_basis": basis,
        "supporting_rationale": PAIR_RATIONALE[(behaviour_id, ilo_id)],
        "counter_evidence": build_counter_evidence(behaviour_id, role),
        "pattern_id": "PAT-POS-001",
        "construct_alignment": {
            "behaviour_dimension": beh_dim,
            "ilo_dimension": ilo_dim,
            "cross_construct": cross,
        },
    }
    if cross:
        record["cross_construct_rationale"] = CROSS_CONSTRUCT_RATIONALE.get(
            (behaviour_id, ilo_id),
            f"Cross-dimension bridge: {behaviour_id} ({beh_dim}) partially supports {ilo_id} ({ilo_dim}) with documented interpretive caution.",
        )
    return record


def build_behaviour_bundle(
    behaviour_id: str,
    behaviours: dict[str, Any],
    ilos: dict[str, Any],
) -> dict[str, Any]:
    ilo_list = sorted(iid for iid, spec in ilos.items() if behaviour_id in spec["related_behaviours"])
    records = [build_record(behaviour_id, iid, behaviours, ilos) for iid in ilo_list]
    records.sort(key=lambda r: (
        {"primary": 0, "secondary": 1, "contextual": 2, "diagnostic": 3}[r["mapping_role"]],
        r["ilo_id"],
    ))

    rejected = [
        {"ilo_id": iid, "reason_rejected": reason}
        for iid, reason in REJECTED_ALTERNATIVES.get(behaviour_id, [])
        if iid not in ilo_list
    ]

    return {
        "behaviour_id": behaviour_id,
        "records": records,
        "rejected_alternatives": rejected,
    }


def build_document() -> dict[str, Any]:
    ob_data = load_json(OB_PATH)
    ilo_data = load_json(ILO_PATH)
    if ob_data.get("freeze", {}).get("status") != "frozen":
        raise SystemExit("Observable_Behaviours.json is not frozen")
    if ilo_data.get("freeze", {}).get("status") != "frozen":
        raise SystemExit("Learning_Objects.json is not frozen")

    behaviours = ob_data["behaviours"]
    ilos = ilo_data["learning_objects"]
    mappings = {bid: build_behaviour_bundle(bid, behaviours, ilos) for bid in sorted(behaviours)}

    record_count = sum(len(b["records"]) for b in mappings.values())
    rejected_count = sum(len(b["rejected_alternatives"]) for b in mappings.values())

    return {
        "artifact": "behaviour_to_ilo_mapping",
        "inference_layer": True,
        "terminology": {
            "mapping_target": "Instructional Learning Object (ILO)",
            "note": "Not a mapping to UNESCO AI-CFT competency codes (LO3.x).",
        },
        "confidence_policy": {
            "qualitative_only": True,
            "numeric_quantization": "deferred_to_Confidence_Model.json",
            "allowed_levels": ["high", "moderate", "low", "baseline"],
            "allowed_basis": [
                "construct_alignment",
                "instructional_consensus",
                "frozen_ilo_behaviour_link",
                "contextual_facilitation",
                "cross_construct_bridge",
                "diagnostic_baseline",
            ],
            "prohibited": "ad_hoc_numeric_confidence",
        },
        "behaviour_ontology_reference": "framework/Observable_Behaviours.json",
        "behaviour_ontology_version": "1.0",
        "ilo_ontology_reference": "framework/Learning_Objects.json",
        "ilo_ontology_version": "1.0",
        "mapping_count": record_count,
        "rejected_alternative_count": rejected_count,
        "behaviour_count": len(mappings),
        "mappings": mappings,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args()
    doc = build_document()
    if args.check:
        print(f"OK: {doc['mapping_count']} records, {doc['rejected_alternative_count']} rejected alts")
        return 0
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
