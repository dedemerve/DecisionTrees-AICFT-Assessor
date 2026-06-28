#!/usr/bin/env python3
"""
run_domain_stress_test.py — Adversarial domain synthesis verification (Milestone 4 gate).

Five canonical scenarios validating that domain claims respect convergence,
leakage guards, and source diversity before milestone sign-off.

Usage:
  python scripts/run_domain_stress_test.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

REPO = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(REPO / "scripts"))
from domain_synthesis import DomainSynthesizer, EvidenceProfile, STRENGTH_RANK  # noqa: E402


def assert_strength(actual: str, maximum: str | None, minimum: str | None, label: str) -> list[str]:
    errors: list[str] = []
    if maximum and STRENGTH_RANK[actual] > STRENGTH_RANK[maximum]:
        errors.append(f"{label}: expected ≤{maximum}, got {actual}")
    if minimum and STRENGTH_RANK[actual] < STRENGTH_RANK[minimum]:
        errors.append(f"{label}: expected ≥{minimum}, got {actual}")
    return errors


def run_test_1_conceptual_high_procedural_low(synth: DomainSynthesizer) -> dict[str, Any]:
    """Conceptual high, procedural low → representational domain only; procedural/strategic capped."""
    profile = EvidenceProfile(
        ilo_strengths={
            "ILO_INSTANCE": "strong",
            "ILO_FEATURE": "strong",
            "ILO_LABEL": "strong",
            "ILO_DATASET": "strong",
            "ILO_TRAINING_ROLE": "moderate",
            "ILO_CLASSIFICATION": "weak",
            "ILO_RULE": "weak",
            "ILO_THRESHOLD": "weak",
            "ILO_DECISION_TREE": "weak",
        },
        ilo_sources={i: {"worksheet"} for i in (
            "ILO_INSTANCE", "ILO_FEATURE", "ILO_LABEL", "ILO_DATASET", "ILO_TRAINING_ROLE",
            "ILO_CLASSIFICATION", "ILO_RULE", "ILO_THRESHOLD", "ILO_DECISION_TREE",
        )},
        contradictions={"vocabulary_without_application"},
    )
    strengths = synth.domain_strengths(profile)
    errors: list[str] = []
    errors += assert_strength(strengths["DU_DATA_REPRESENTATION"], None, "moderate", "DU_DATA_REPRESENTATION")
    errors += assert_strength(strengths["DU_CLASSIFICATION_REASONING"], "weak", None, "DU_CLASSIFICATION_REASONING")
    errors += assert_strength(strengths["DU_TREE_STRUCTURE_REASONING"], "weak", None, "DU_TREE_STRUCTURE_REASONING")
    errors += assert_strength(strengths["DU_THRESHOLD_REASONING"], "weak", None, "DU_THRESHOLD_REASONING")
    errors += assert_strength(strengths["DU_PARAMETER_TUNING"], "none", None, "DU_PARAMETER_TUNING")
    return {
        "test_id": "DST-01",
        "title": "Conceptual high, procedural low",
        "profile_summary": "Strong representational ILOs; weak procedural ILOs",
        "domain_strengths": strengths,
        "pass": not errors,
        "errors": errors,
    }


def run_test_2_procedural_high_reflection_low(synth: DomainSynthesizer) -> dict[str, Any]:
    """Procedural high, reflection low → procedural domains rise; reflective does not."""
    profile = EvidenceProfile(
        ilo_strengths={
            "ILO_CLASSIFICATION": "strong",
            "ILO_RULE": "strong",
            "ILO_THRESHOLD": "strong",
            "ILO_DECISION_TREE": "strong",
            "ILO_DT_WORKFLOW": "moderate",
            "ILO_TREE_SPLIT": "moderate",
            "ILO_METACOGNITIVE_REFLECTION": "weak",
            "ILO_MODEL_LIMITATION": "weak",
        },
        ilo_sources={
            i: {"worksheet", "codap"} for i in (
                "ILO_CLASSIFICATION", "ILO_RULE", "ILO_THRESHOLD", "ILO_DECISION_TREE",
                "ILO_DT_WORKFLOW", "ILO_TREE_SPLIT",
            )
        } | {
            i: {"reflection"} for i in ("ILO_METACOGNITIVE_REFLECTION", "ILO_MODEL_LIMITATION")
        },
    )
    strengths = synth.domain_strengths(profile)
    errors: list[str] = []
    errors += assert_strength(strengths["DU_CLASSIFICATION_REASONING"], None, "moderate", "DU_CLASSIFICATION_REASONING")
    errors += assert_strength(strengths["DU_TREE_STRUCTURE_REASONING"], None, "moderate", "DU_TREE_STRUCTURE_REASONING")
    errors += assert_strength(strengths["DU_REFLECTIVE_UNDERSTANDING"], "moderate", None, "DU_REFLECTIVE_UNDERSTANDING")
    if strengths["DU_REFLECTIVE_UNDERSTANDING"] == "strong":
        errors.append("DU_REFLECTIVE_UNDERSTANDING: must not be strong when reflection ILOs are weak")
    return {
        "test_id": "DST-02",
        "title": "Procedural high, reflection low",
        "profile_summary": "Strong procedural ILOs (multi-source); weak reflection ILOs",
        "domain_strengths": strengths,
        "pass": not errors,
        "errors": errors,
    }


def run_test_3_video_strong_worksheet_weak(synth: DomainSynthesizer) -> dict[str, Any]:
    """Video/log strong, worksheet weak → strategic domains must not reach strong on video alone."""
    profile = EvidenceProfile(
        ilo_strengths={
            "ILO_THRESHOLD": "strong",
            "ILO_PARAMETER_OPTIMIZATION": "strong",
            "ILO_MODEL_EVALUATION": "strong",
            "ILO_TREE_SPLIT": "moderate",
            "ILO_DATA_PATTERN": "weak",
        },
        ilo_sources={
            "ILO_THRESHOLD": {"screen_recording"},
            "ILO_PARAMETER_OPTIMIZATION": {"screen_recording"},
            "ILO_MODEL_EVALUATION": {"screen_recording"},
            "ILO_TREE_SPLIT": {"screen_recording"},
            "ILO_DATA_PATTERN": {"worksheet"},
        },
        contradictions={"worksheet_video_source_asymmetry"},
    )
    strengths = synth.domain_strengths(profile)
    errors: list[str] = []
    for did in ("DU_THRESHOLD_REASONING", "DU_PARAMETER_TUNING", "DU_MODEL_EVALUATION"):
        errors += assert_strength(strengths[did], "moderate", None, f"{did} (video-only)")
    return {
        "test_id": "DST-03",
        "title": "Video strong, worksheet weak",
        "profile_summary": "Strategic ILOs strong from screen_recording only; worksheet weak",
        "domain_strengths": strengths,
        "pass": not errors,
        "errors": errors,
    }


def run_test_4_reflection_strong_codap_weak(synth: DomainSynthesizer) -> dict[str, Any]:
    """Reflection excellent, CODAP weak → reflective may rise; classification must not."""
    profile = EvidenceProfile(
        ilo_strengths={
            "ILO_METACOGNITIVE_REFLECTION": "strong",
            "ILO_MODEL_LIMITATION": "strong",
            "ILO_CLASSIFICATION": "weak",
            "ILO_DECISION_TREE": "weak",
            "ILO_THRESHOLD": "weak",
        },
        ilo_sources={
            "ILO_METACOGNITIVE_REFLECTION": {"reflection"},
            "ILO_MODEL_LIMITATION": {"reflection"},
            "ILO_CLASSIFICATION": {"codap"},
            "ILO_DECISION_TREE": {"codap"},
            "ILO_THRESHOLD": {"codap"},
        },
        contradictions={"procedural_reflection_split", "high_reflection_weak_procedural"},
    )
    strengths = synth.domain_strengths(profile)
    errors: list[str] = []
    errors += assert_strength(strengths["DU_REFLECTIVE_UNDERSTANDING"], None, "moderate", "DU_REFLECTIVE_UNDERSTANDING")
    errors += assert_strength(strengths["DU_CLASSIFICATION_REASONING"], "moderate", None, "DU_CLASSIFICATION_REASONING")
    errors += assert_strength(strengths["DU_THRESHOLD_REASONING"], "moderate", None, "DU_THRESHOLD_REASONING")
    if strengths["DU_CLASSIFICATION_REASONING"] == "strong":
        errors.append("DU_CLASSIFICATION_REASONING: must not be strong when CODAP procedural is weak")
    return {
        "test_id": "DST-04",
        "title": "Reflection strong, CODAP weak",
        "profile_summary": "Strong reflection ILOs; weak procedural CODAP evidence",
        "domain_strengths": strengths,
        "pass": not errors,
        "errors": errors,
    }


def run_test_5_single_source(synth: DomainSynthesizer) -> dict[str, Any]:
    """Single evidence source → no domain may be strong."""
    all_ilos = [
        "ILO_INSTANCE", "ILO_FEATURE", "ILO_LABEL", "ILO_DATASET", "ILO_CLASSIFICATION",
        "ILO_RULE", "ILO_THRESHOLD", "ILO_DECISION_TREE", "ILO_CONFUSION_MATRIX",
        "ILO_MCR", "ILO_MODEL_EVALUATION", "ILO_PARAMETER_OPTIMIZATION",
        "ILO_METACOGNITIVE_REFLECTION", "ILO_DATA_PATTERN",
    ]
    profile = EvidenceProfile(
        ilo_strengths={i: "strong" for i in all_ilos},
        ilo_sources={i: {"worksheet"} for i in all_ilos},
        contradictions={"single_source_only"},
        global_source_cap="moderate",
    )
    strengths = synth.domain_strengths(profile)
    errors: list[str] = []
    strong_domains = [d for d, s in strengths.items() if s == "strong"]
    if strong_domains:
        errors.append(f"No domain should be strong with single source; found: {strong_domains}")
    return {
        "test_id": "DST-05",
        "title": "Single evidence source",
        "profile_summary": "All ILOs strong but from worksheet only",
        "domain_strengths": strengths,
        "pass": not errors,
        "errors": errors,
    }


TESTS: list[Callable[[DomainSynthesizer], dict[str, Any]]] = [
    run_test_1_conceptual_high_procedural_low,
    run_test_2_procedural_high_reflection_low,
    run_test_3_video_strong_worksheet_weak,
    run_test_4_reflection_strong_codap_weak,
    run_test_5_single_source,
]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    synth = DomainSynthesizer()
    results = [fn(synth) for fn in TESTS]
    all_pass = all(r["pass"] for r in results)

    report = {
        "suite": "domain_stress_test",
        "status": "pass" if all_pass else "fail",
        "test_count": len(results),
        "passed": sum(1 for r in results if r["pass"]),
        "tests": results,
    }

    sys.path.insert(0, str(REPO / "scripts"))
    from milestone_reporting import patch_validation  # noqa: E402

    patch_validation(4, {"stress_test": report})

    if not args.quiet:
        print(f"Domain Stress Test: {report['passed']}/{report['test_count']} passed")
        print(f"Status: {report['status'].upper()}")
        for t in results:
            mark = "PASS" if t["pass"] else "FAIL"
            print(f"  [{mark}] {t['test_id']}: {t['title']}")
            for e in t.get("errors", []):
                print(f"         {e}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
