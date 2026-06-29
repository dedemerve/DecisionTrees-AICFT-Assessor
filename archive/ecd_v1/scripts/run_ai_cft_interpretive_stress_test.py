#!/usr/bin/env python3
"""
run_ai_cft_interpretive_stress_test.py — Adversarial tests preventing AI-CFT overclaim (Milestone 5 gate).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"

CONF_RANK = {"none": -1, "very_weak": 0, "weak": 1, "moderate": 2, "strong": 3}


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def find_contributions(policy: dict[str, Any], domain_id: str, aicft: str) -> list[dict[str, Any]]:
    return [
        c for c in policy["policies"][domain_id]["contributions"]
        if aicft in c["possible_ai_cft"]
    ]


def max_recommendable_confidence(
    policy: dict[str, Any],
    domain_strengths: dict[str, str],
    aicft: str,
    *,
    evidence_sources: int,
    contradictions: set[str],
) -> tuple[str, list[str]]:
    """Simulate interpretive recommendation ceiling for an AI-CFT indicator."""
    ceiling = "none"
    notes: list[str] = []

    for did, strength in domain_strengths.items():
        if strength in ("none",):
            continue
        if strength not in CONF_RANK:
            continue
        contribs = find_contributions(policy, did, aicft)
        for c in contribs:
            if CONF_RANK[strength] < CONF_RANK[c["minimum_domain_strength"]]:
                notes.append(f"{did} below minimum_domain_strength for {aicft}")
                continue
            for req in c.get("required_domains", []):
                if CONF_RANK[domain_strengths.get(req, "none")] < CONF_RANK["weak"]:
                    notes.append(f"required domain {req} not evidenced for {aicft}")
                    continue
            if evidence_sources < c.get("minimum_evidence_sources", 1):
                notes.append(f"insufficient sources for {aicft} via {did}")
                cap = min(CONF_RANK[c["confidence_ceiling"]], CONF_RANK["moderate"])
            else:
                cap = CONF_RANK[c["confidence_ceiling"]]

            for blocker in c.get("escalation_blockers", []):
                if blocker in contradictions or any(
                    b in contradictions for b in (
                        "single_source_only", "reflection_drives_deepen_without_procedural_corroboration",
                        "domain_present_without_convergence",
                    )
                ):
                    cap = min(cap, CONF_RANK["moderate"])
                    notes.append(f"escalation blocker active for {aicft}")

            for cond in c.get("contradiction_conditions", []):
                if cond in contradictions:
                    cap = min(cap, CONF_RANK["weak"])
                    notes.append(f"contradiction {cond} caps {aicft}")

            level = [k for k, v in CONF_RANK.items() if v == cap][0]
            if CONF_RANK.get(ceiling, -1) < cap:
                ceiling = level

    if evidence_sources < 2:
        ceiling = "moderate" if CONF_RANK.get(ceiling, 0) > CONF_RANK["moderate"] else ceiling
        if ceiling != "none":
            notes.append("single-source global cap")

    return ceiling if ceiling != "none" else "none", notes


def run_tests(policy: dict[str, Any]) -> list[dict[str, Any]]:
    tests: list[dict[str, Any]] = []

    # AST-01: Domain present alone must not yield strong Deepen
    strengths = {"DU_THRESHOLD_AND_PARAMETER_REASONING": "strong"}
    ceiling, notes = max_recommendable_confidence(
        policy, strengths, "LO3.2.2", evidence_sources=1, contradictions={"domain_present_without_convergence"},
    )
    tests.append({
        "test_id": "AST-01",
        "title": "Domain present without convergence",
        "pass": ceiling in ("none", "weak", "moderate", "very_weak"),
        "ceiling": ceiling,
        "errors": [] if ceiling != "strong" else ["LO3.2.2 must not reach strong with domain-only presence"],
        "notes": notes,
    })

    # AST-02: Reflection strong, procedural weak — no strong LO3.2.2
    strengths = {
        "DU_REFLECTIVE_UNDERSTANDING": "strong",
        "DU_CLASSIFICATION_REASONING": "weak",
        "DU_THRESHOLD_AND_PARAMETER_REASONING": "weak",
    }
    ceiling, notes = max_recommendable_confidence(
        policy, strengths, "LO3.2.2", evidence_sources=2,
        contradictions={"high_reflection_weak_procedural", "reflection_drives_deepen_without_procedural_corroboration"},
    )
    tests.append({
        "test_id": "AST-02",
        "title": "Reflection cannot inflate Deepen",
        "pass": ceiling != "strong",
        "ceiling": ceiling,
        "errors": [] if ceiling != "strong" else ["LO3.2.2 must not be strong on reflection alone"],
        "notes": notes,
    })

    # AST-03: Single source caps all strong recommendations
    strengths = {did: "strong" for did in policy["policies"]}
    ceiling, notes = max_recommendable_confidence(
        policy, strengths, "LO3.2.3", evidence_sources=1, contradictions={"single_source_only"},
    )
    tests.append({
        "test_id": "AST-03",
        "title": "Single evidence source",
        "pass": ceiling != "strong",
        "ceiling": ceiling,
        "errors": [] if ceiling != "strong" else ["No strong AI-CFT recommendation from single source"],
        "notes": notes,
    })

    # AST-04: Data representation alone cannot imply LO3.2.2
    strengths = {"DU_DATA_REPRESENTATION": "strong"}
    ceiling, notes = max_recommendable_confidence(
        policy, strengths, "LO3.2.2", evidence_sources=2, contradictions=set(),
    )
    tests.append({
        "test_id": "AST-04",
        "title": "Conceptual domain cannot imply application LO",
        "pass": ceiling == "none",
        "ceiling": ceiling,
        "errors": [] if ceiling == "none" else ["LO3.2.2 must not be indicated by representation alone"],
        "notes": notes,
    })

    # AST-05: Create claim requires multi-domain convergence; ceiling weak at most
    strengths = {
        "DU_GENERALISATION": "moderate",
        "DU_THRESHOLD_AND_PARAMETER_REASONING": "moderate",
        "DU_CLASSIFICATION_REASONING": "moderate",
    }
    ceiling, notes = max_recommendable_confidence(
        policy, strengths, "LO3.3.1", evidence_sources=2, contradictions=set(),
    )
    tests.append({
        "test_id": "AST-05",
        "title": "Create indicator capped weak",
        "pass": CONF_RANK.get(ceiling, 0) <= CONF_RANK["weak"],
        "ceiling": ceiling,
        "errors": [] if CONF_RANK.get(ceiling, 0) <= CONF_RANK["weak"] else ["LO3.3.1 ceiling must be ≤ weak"],
        "notes": notes,
    })

    # AST-06: Every contribution requires researcher review
    missing_rr = []
    for did, pol in policy["policies"].items():
        for c in pol["contributions"]:
            if not c.get("researcher_review_required"):
                missing_rr.append(did)
    tests.append({
        "test_id": "AST-06",
        "title": "Researcher review always required",
        "pass": not missing_rr,
        "errors": [f"{d} missing researcher_review_required" for d in missing_rr],
    })

    for t in tests:
        t["pass"] = t.get("pass", False) and not t.get("errors")

    return tests


def main(argv: list[str] | None = None) -> int:
    policy = load_policy()
    tests = run_tests(policy)
    all_pass = all(t["pass"] for t in tests)

    report = {
        "suite": "ai_cft_interpretive_stress_test",
        "status": "pass" if all_pass else "fail",
        "test_count": len(tests),
        "passed": sum(1 for t in tests if t["pass"]),
        "tests": tests,
    }

    sys.path.insert(0, str(REPO / "scripts"))
    from milestone_reporting import patch_validation  # noqa: E402

    patch_validation(5, {"stress_test": report})

    print(f"AI-CFT Interpretive Stress Test: {report['passed']}/{report['test_count']} passed")
    print(f"Status: {report['status'].upper()}")
    for t in tests:
        mark = "PASS" if t["pass"] else "FAIL"
        print(f"  [{mark}] {t['test_id']}: {t['title']}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
