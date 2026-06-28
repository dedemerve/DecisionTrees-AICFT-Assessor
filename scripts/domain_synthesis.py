#!/usr/bin/env python3
"""
domain_synthesis.py — Provisional domain claim synthesis from ILO evidence profiles.

Operationalizes convergence_requirements and contradiction_handling from
Domain_Understanding.json for stress testing and future Aggregation_Policy.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"

STRENGTH_LEVELS = ("none", "weak", "moderate", "strong")
STRENGTH_RANK = {s: i for i, s in enumerate(STRENGTH_LEVELS)}


def min_strength(a: str, b: str) -> str:
    return a if STRENGTH_RANK[a] <= STRENGTH_RANK[b] else b


def max_strength(a: str, b: str) -> str:
    return a if STRENGTH_RANK[a] >= STRENGTH_RANK[b] else b


@dataclass
class EvidenceProfile:
    """Synthetic portfolio evidence state for domain stress testing."""

    ilo_strengths: dict[str, str]
    ilo_sources: dict[str, set[str]] = field(default_factory=dict)
    contradictions: set[str] = field(default_factory=set)
    global_source_cap: str | None = None  # e.g. "moderate" when single-source rule applies

    def qualifying_strength(self, ilo_id: str) -> str:
        s = self.ilo_strengths.get(ilo_id, "none")
        if s in ("moderate", "strong"):
            return s
        if s == "weak":
            return "weak"
        return "none"

    def sources_for_ilos(self, ilo_ids: list[str]) -> set[str]:
        out: set[str] = set()
        for iid in ilo_ids:
            out |= self.ilo_sources.get(iid, set())
        return out


class DomainSynthesizer:
    def __init__(self, domain_doc: dict[str, Any] | None = None) -> None:
        self.domain_doc = domain_doc or json.loads(DOMAIN_PATH.read_text(encoding="utf-8"))
        self.domains = self.domain_doc["domains"]

    def synthesize(self, profile: EvidenceProfile) -> dict[str, dict[str, Any]]:
        results: dict[str, dict[str, Any]] = {}
        for did, dom in self.domains.items():
            results[did] = self._synthesize_domain(did, dom, profile)
        return results

    def domain_strengths(self, profile: EvidenceProfile) -> dict[str, str]:
        return {did: r["claim_strength"] for did, r in self.synthesize(profile).items()}

    def _synthesize_domain(
        self, did: str, dom: dict[str, Any], profile: EvidenceProfile,
    ) -> dict[str, Any]:
        conv = dom["convergence_requirements"]
        exclusions = set(dom.get("aggregation_exclusions", []))
        indicative = [i for i in dom.get("indicative_ilos", []) if i not in exclusions]

        qualifying = [i for i in indicative if profile.qualifying_strength(i) in ("moderate", "strong")]
        strong_qualifying = [i for i in indicative if profile.qualifying_strength(i) == "strong"]

        claim = "none"
        rationale: list[str] = []

        if not qualifying:
            return {
                "domain_id": did,
                "claim_strength": "none",
                "qualifying_ilos": [],
                "distinct_source_count": 0,
                "rationale": ["No indicative ILO at moderate+ strength."],
            }

        if len(qualifying) >= conv["minimum_distinct_ilos"]:
            claim = "moderate"
            rationale.append(
                f"{len(qualifying)} indicative ILO(s) at moderate+ (minimum {conv['minimum_distinct_ilos']})."
            )
        elif any(profile.qualifying_strength(i) == "weak" for i in indicative):
            claim = "weak"
            rationale.append("Partial ILO signal below convergence threshold.")
        else:
            return {
                "domain_id": did,
                "claim_strength": "none",
                "qualifying_ilos": qualifying,
                "distinct_source_count": len(profile.sources_for_ilos(qualifying)),
                "rationale": ["Insufficient distinct ILO convergence."],
            }

        sources = profile.sources_for_ilos(qualifying)
        source_count = len(sources)

        if source_count < conv.get("minimum_evidence_sources", 1):
            claim = min_strength(claim, "weak")
            rationale.append(f"Evidence sources ({source_count}) below domain minimum.")

        if conv.get("strong_claim_requires_multi_source") and source_count < 2:
            claim = min_strength(claim, "moderate")
            rationale.append("Strong claim requires multi-source convergence.")

        if len(strong_qualifying) >= conv["minimum_distinct_ilos"] and source_count >= 2:
            if not conv.get("requires_procedural_corroboration_for_strong") or dom["construct_dimension"] != "strategic":
                claim = "strong"
                rationale.append("Multi-source strong ILO convergence met.")
            elif any(
                profile.qualifying_strength(i) in ("moderate", "strong")
                for i in indicative
                if i in ("ILO_CLASSIFICATION", "ILO_RULE", "ILO_THRESHOLD", "ILO_DECISION_TREE", "ILO_DT_WORKFLOW")
            ):
                claim = "strong"
                rationale.append("Strategic domain with procedural corroboration.")
            else:
                claim = min_strength(claim, "moderate")
                rationale.append("Strategic strong claim blocked: procedural corroboration missing.")

        claim = self._apply_contradictions(did, dom, profile, claim, rationale)
        if profile.global_source_cap:
            claim = min_strength(claim, profile.global_source_cap)
            rationale.append(f"Global source cap applied: {profile.global_source_cap}.")

        return {
            "domain_id": did,
            "claim_strength": claim,
            "qualifying_ilos": qualifying,
            "distinct_source_count": source_count,
            "rationale": rationale,
        }

    def _apply_contradictions(
        self,
        did: str,
        dom: dict[str, Any],
        profile: EvidenceProfile,
        claim: str,
        rationale: list[str],
    ) -> str:
        dim = dom["construct_dimension"]
        c = profile.contradictions

        if "vocabulary_without_application" in c and dim == "conceptual":
            claim = min_strength(claim, "moderate")
            rationale.append("Contradiction: vocabulary without application.")

        if "high_reflection_weak_procedural" in c:
            if dim == "reflective":
                rationale.append("Reflective evidence accepted with procedural weakness (leakage guard).")
            elif dim in ("procedural", "strategic"):
                claim = min_strength(claim, "moderate")
                rationale.append("Contradiction: strong reflection cannot inflate procedural/strategic domains (L5).")

        if "procedural_reflection_split" in c:
            if did == "DU_REFLECTIVE_UNDERSTANDING":
                rationale.append("Reflective domain evaluated on reflection evidence independently.")
            elif did in ("DU_CLASSIFICATION_REASONING", "DU_TREE_STRUCTURE_REASONING", "DU_THRESHOLD_REASONING"):
                claim = min_strength(claim, "moderate")
                rationale.append("Contradiction: weak CODAP/procedural blocks strong classification/strategic.")

        if "threshold_misconception" in c and did in ("DU_THRESHOLD_REASONING", "DU_CLASSIFICATION_REASONING"):
            claim = min_strength(claim, "weak")
            rationale.append("Contradiction: threshold misconception blocks escalation.")

        if "tool_fluency_only" in c and did == "DU_PARAMETER_TUNING":
            claim = min_strength(claim, "weak")
            rationale.append("Contradiction: digital fluency leakage (L3).")

        if "single_source_only" in c:
            claim = min_strength(claim, "moderate")
            rationale.append("Contradiction: single evidence source caps all domains below strong.")

        if "worksheet_video_source_asymmetry" in c and did in (
            "DU_THRESHOLD_REASONING", "DU_PARAMETER_TUNING", "DU_MODEL_EVALUATION", "DU_GENERALISATION",
        ):
            claim = min_strength(claim, "moderate")
            rationale.append("Strategic domain: video-only strength cannot reach strong without corroboration.")

        return claim
