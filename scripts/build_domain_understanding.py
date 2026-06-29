#!/usr/bin/env python3
"""
build_domain_understanding.py — Refresh Domain_Understanding.json metadata (Milestone 4).

Domain definitions are authored in framework/Domain_Understanding.json. This builder
re-reads that file and rewrites the ontology wrapper (counts, pair differentiation,
references). It does not embed domain bodies in Python constants.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
ILO_PATH = REPO / "framework" / "Learning_Objects.json"
OB_PATH = REPO / "framework" / "Observable_Behaviours.json"
MAP_PATH = REPO / "framework" / "Behaviour_to_ILO.json"
OUT_PATH = REPO / "framework" / "Domain_Understanding.json"

DESIGN_CONSTRAINT = (
    "Domain Understanding must NOT be treated as a simple grouping of Instructional Learning "
    "Objects. A Domain represents an emergent disciplinary understanding supported by converging "
    "evidence across multiple Instructional Learning Objects, Observable Behaviours, and evidence "
    "sources. Every Domain must therefore have an explicit construct definition, evidence criteria, "
    "convergence requirements, contradiction handling rules, and theoretical rationale. Domains "
    "are assessment constructs, not curriculum topics."
)

DOMAIN_PAIR_DIFFERENTIATION: list[dict[str, Any]] = [
    {
        "domain_a": "DU_CLASSIFICATION_REASONING",
        "domain_b": "DU_TREE_STRUCTURE_REASONING",
        "overlap_risk": "moderate",
        "discriminating_criteria": (
            "Classification evidences outcome assignment; Tree Structure evidences topology, splits, "
            "and workflow. Leaf assignment alone does not prove structural mastery."
        ),
    },
    {
        "domain_a": "DU_MODEL_EVALUATION",
        "domain_b": "DU_THRESHOLD_AND_PARAMETER_REASONING",
        "overlap_risk": "moderate",
        "discriminating_criteria": (
            "Evaluation interprets performance artifacts; Threshold-and-Parameter Reasoning selects "
            "cutoffs and explores parameter states. Metrics may inform thresholds but do not substitute "
            "for comparative threshold decisions or documented search."
        ),
    },
    {
        "domain_a": "DU_GENERALISATION",
        "domain_b": "DU_DATA_REPRESENTATION",
        "overlap_risk": "low",
        "discriminating_criteria": (
            "Representation is prerequisite vocabulary and structure; Generalisation requires "
            "cross-context pattern transfer beyond initial examples."
        ),
    },
]


def load_domains() -> list[dict[str, Any]]:
    if not OUT_PATH.is_file():
        raise FileNotFoundError(
            f"Domain ontology source missing: {OUT_PATH}. "
            "Edit framework/Domain_Understanding.json directly; this builder only refreshes metadata."
        )
    doc = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    return list(doc["domains"].values())


def build_document(ilo_data: dict[str, Any], ob_data: dict[str, Any], map_data: dict[str, Any]) -> dict[str, Any]:
    domains = load_domains()
    domain_map = {d["id"]: d for d in domains}
    return {
        "artifact": "domain_understanding_ontology",
        "unesco_aicft_reference": {
            "edition": "2024",
            "title": "UNESCO AI Competency Framework for Teachers",
            "isbn": "978-92-3-100707-1",
            "aspect": "Aspect 3 — AI foundations and applications",
            "note": "Operational LO3.1.x–LO3.3.x indicators map to this 2024 edition (ISBN 978-92-3-100707-1); update this reference if UNESCO publishes a revised framework.",
        },
        "ontology_layer": "assessment_construct",
        "design_constraint": DESIGN_CONSTRAINT,
        "terminology": {
            "domain": "Emergent assessment construct synthesizing evidence across ILOs, behaviours, and sources.",
            "not_a_domain": "Curriculum topic, worksheet section, or ILO folder.",
            "upstream": [
                "framework/Observable_Behaviours.json",
                "framework/Learning_Objects.json",
                "framework/Behaviour_to_ILO.json",
            ],
            "downstream": ["LO_to_Domain_Understanding.json", "Domain_to_AI_CFT.json", "Aggregation_Policy.json"],
        },
        "construct": "Decision Tree Understanding",
        "construct_reference": "framework/Construct_Definition.md",
        "construct_dimensions": ["conceptual", "procedural", "strategic", "reflective"],
        "ilo_ontology_reference": "framework/Learning_Objects.json",
        "behaviour_ontology_reference": "framework/Observable_Behaviours.json",
        "behaviour_to_ilo_reference": "framework/Behaviour_to_ILO.json",
        "domain_count": len(domains),
        "domain_pair_differentiation": DOMAIN_PAIR_DIFFERENTIATION,
        "domains": domain_map,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT_PATH)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    ilo_data = json.loads(ILO_PATH.read_text(encoding="utf-8"))
    ob_data = json.loads(OB_PATH.read_text(encoding="utf-8"))
    map_data = json.loads(MAP_PATH.read_text(encoding="utf-8"))

    doc = build_document(ilo_data, ob_data, map_data)
    args.output.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {args.output}")
    print(f"Domains: {doc['domain_count']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
