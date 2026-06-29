#!/usr/bin/env python3
"""
build_domain_to_ai_cft.py — Refresh Domain_to_AI_CFT.json metadata (Milestone 5).

Interpretive policies are authored in framework/Domain_to_AI_CFT.json. This builder
re-reads that file and rewrites the policy wrapper (counts, references). It does not
embed policy bodies in Python constants.
"""

from __future__ import annotations

import argparse
import json
import sys
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


def load_policies() -> dict[str, Any]:
    if not OUT_PATH.is_file():
        raise FileNotFoundError(
            f"Interpretive policy source missing: {OUT_PATH}. "
            "Edit framework/Domain_to_AI_CFT.json directly; this builder only refreshes metadata."
        )
    return json.loads(OUT_PATH.read_text(encoding="utf-8"))["policies"]


def build_document(domain_doc: dict[str, Any], existing: dict[str, Any]) -> dict[str, Any]:
    policies = existing["policies"]
    domain_ids = set(domain_doc["domains"])
    if set(policies) != domain_ids:
        missing = domain_ids - set(policies)
        extra = set(policies) - domain_ids
        raise ValueError(f"Policy/domain mismatch missing={missing} extra={extra}")

    contribution_count = sum(len(p["contributions"]) for p in policies.values())
    confidence_policy = existing.get("confidence_policy", {
        "qualitative_only": True,
        "enforcement": (
            "Contributions must use qualitative allowed_confidence and confidence_ceiling labels only; "
            "minimum_evidence_sources is a convergence gate, not a numeric probability or percentage score."
        ),
        "numeric_quantization": "deferred_to_Confidence_Model.json",
        "allowed_levels": ["very_weak", "weak", "moderate", "strong"],
        "prohibited": "ad_hoc_numeric_confidence",
    })

    return {
        "artifact": "domain_to_ai_cft_interpretive_policy",
        "interpretation_layer": True,
        "design_constraint": DESIGN_CONSTRAINT,
        "implementation_constraint": IMPLEMENTATION_CONSTRAINT,
        "terminology": existing.get("terminology", {
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
        }),
        "confidence_policy": confidence_policy,
        "domain_ontology_reference": "framework/Domain_Understanding.json",
        "aicft_reference": "mappings/AICFT_assessment_framework.json",
        "aicft_framework": "UNESCO AI Competency Framework for Teachers (AI-CFT) 2024",
        "aicft_aspect": "Aspect 3: AI foundations and applications",
        "domain_policy_count": len(policies),
        "contribution_count": contribution_count,
        "policies": policies,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    args = parser.parse_args(argv)

    domain_doc = json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
    existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))

    for policy in existing["policies"].values():
        for c in policy["contributions"]:
            for lo in c["possible_ai_cft"]:
                if lo not in VALID_AICFT:
                    print(f"ERROR: unknown AI-CFT code {lo}")
                    return 1

    doc = build_document(domain_doc, existing)
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Domain policies: {doc['domain_policy_count']}, contributions: {doc['contribution_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
