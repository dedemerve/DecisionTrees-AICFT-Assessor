#!/usr/bin/env python3
"""
validate_domain_to_ai_cft.py — Milestone 5 interpretive policy verification and analytics.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parent.parent
POLICY_PATH = REPO / "framework" / "Domain_to_AI_CFT.json"
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
REPORT_DIR = REPO / "reports" / "milestone5"

DOMAIN_PATTERN = re.compile(r"^DU_[A-Z][A-Z0-9_]+$")
AICFT_PATTERN = re.compile(r"^LO3\.\d+\.\d+$")
VALID_INTERP_TYPES = frozenset({"supporting", "contributing", "may_indicate"})
VALID_VERBS = frozenset({"may_contribute_to", "may_indicate", "supports", "contributes"})
VALID_CONFIDENCE = frozenset({"very_weak", "weak", "moderate", "strong"})
PROHIBITED_FIELD_PATTERNS = (
    re.compile(r'"maps_to"\s*:'),
    re.compile(r'"is_final"\s*:\s*true'),
    re.compile(r'"automatic_claim"\s*:\s*true'),
)

REQUIRED_CONTRIB = frozenset({
    "possible_ai_cft", "interpretation_type", "interpretation_verb",
    "required_domains", "minimum_domain_strength", "minimum_evidence_sources",
    "required_convergence", "allowed_confidence", "confidence_ceiling",
    "contradiction_conditions", "escalation_blockers", "insufficient_when",
    "alternative_explanations", "researcher_review_required", "never_implies",
    "theoretical_rationale",
})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_policy(
    doc: dict[str, Any],
    domain_doc: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    if domain_doc.get("freeze", {}).get("status") != "frozen":
        errors.append("Domain_Understanding.json must be frozen")

    blob = POLICY_PATH.read_text(encoding="utf-8")
    for pat in PROHIBITED_FIELD_PATTERNS:
        if pat.search(blob):
            errors.append(f"prohibited field pattern in artifact: {pat.pattern}")

    if doc.get("artifact") != "domain_to_ai_cft_interpretive_policy":
        errors.append("artifact must be domain_to_ai_cft_interpretive_policy")
    if not doc.get("design_constraint"):
        errors.append("missing design_constraint")
    if not doc.get("implementation_constraint"):
        errors.append("missing implementation_constraint")
    if not doc.get("confidence_policy", {}).get("qualitative_only"):
        errors.append("qualitative_only confidence required")

    domain_ids = set(domain_doc["domains"])
    policies = doc.get("policies", {})
    if set(policies) != domain_ids:
        errors.append(f"policy/domain mismatch: missing={sorted(domain_ids - set(policies))}")

    aicft_counts: Counter[str] = Counter()
    contrib_records: list[dict[str, Any]] = []

    for did, policy in policies.items():
        if not DOMAIN_PATTERN.match(did):
            errors.append(f"{did}: invalid domain id")
        if "construct_limitations" not in policy or len(policy["construct_limitations"]) < 2:
            errors.append(f"{did}: need construct_limitations (≥2)")
        contributions = policy.get("contributions", [])
        if not contributions:
            errors.append(f"{did}: no contributions")

        for i, c in enumerate(contributions):
            prefix = f"{did}/contrib[{i}]"
            missing = REQUIRED_CONTRIB - c.keys()
            if missing:
                errors.append(f"{prefix}: missing {missing}")
            if c.get("interpretation_type") not in VALID_INTERP_TYPES:
                errors.append(f"{prefix}: invalid interpretation_type")
            if c.get("interpretation_verb") not in VALID_VERBS:
                errors.append(f"{prefix}: invalid interpretation_verb")
            if not c.get("researcher_review_required"):
                errors.append(f"{prefix}: researcher_review_required must be true")
            if len(c.get("insufficient_when", [])) < 2:
                errors.append(f"{prefix}: insufficient_when needs ≥2 items")
            if len(c.get("never_implies", [])) < 2:
                errors.append(f"{prefix}: never_implies needs ≥2 items")

            for level in ("allowed_confidence", "confidence_ceiling", "minimum_domain_strength"):
                val = c.get(level)
                if isinstance(val, (int, float)):
                    errors.append(f"{prefix}: numeric {level} forbidden")
                elif val not in VALID_CONFIDENCE:
                    errors.append(f"{prefix}: invalid {level} {val!r}")

            for lo in c.get("possible_ai_cft", []):
                if not AICFT_PATTERN.match(lo):
                    errors.append(f"{prefix}: invalid AI-CFT code {lo!r}")
                aicft_counts[lo] += 1
                contrib_records.append({
                    "domain_id": did,
                    "ai_cft": lo,
                    "interpretation_type": c.get("interpretation_type"),
                    "interpretation_verb": c.get("interpretation_verb"),
                    "confidence_ceiling": c.get("confidence_ceiling"),
                    "minimum_evidence_sources": c.get("minimum_evidence_sources"),
                })

            for req in c.get("required_domains", []):
                if req not in domain_ids:
                    errors.append(f"{prefix}: unknown required_domain {req!r}")

    # Coverage matrix: AI-CFT → contributing domains
    aicft_to_domains: dict[str, list[str]] = defaultdict(list)
    for rec in contrib_records:
        aicft_to_domains[rec["ai_cft"]].append(rec["domain_id"])

    uncovered = sorted({"LO3.1.1", "LO3.1.2", "LO3.1.3", "LO3.2.1", "LO3.2.2", "LO3.2.3", "LO3.3.1"} - set(aicft_counts))
    if uncovered:
        warnings.append(f"AI-CFT indicators with no domain policy path: {uncovered}")

    if aicft_counts["LO3.1.3"] == 0:
        warnings.append("LO3.1.3 (tool selection) has no direct domain policy — acceptable if only via portfolio items")

    analytics = {
        "aicft_coverage_report": {
            "aicft_to_domain_count": [
                {"ai_cft": lo, "domain_count": len(set(aicft_to_domains[lo])), "domains": sorted(set(aicft_to_domains[lo]))}
                for lo in sorted(aicft_counts)
            ],
            "contribution_total": len(contrib_records),
            "domain_policy_count": len(policies),
        },
        "interpretation_type_distribution": dict(Counter(r["interpretation_type"] for r in contrib_records)),
        "confidence_ceiling_distribution": dict(Counter(r["confidence_ceiling"] for r in contrib_records)),
        "contributions": contrib_records,
    }

    return errors, warnings, analytics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    doc = load_json(POLICY_PATH)
    domain_doc = load_json(DOMAIN_PATH)
    errors, warnings, analytics = validate_policy(doc, domain_doc)
    status = "pass" if not errors else "fail"
    now = datetime.now(timezone.utc).isoformat()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "aicft_coverage_report.json").write_text(
        json.dumps({"generated_at": now, **analytics["aicft_coverage_report"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "interpretation_statistics.json").write_text(
        json.dumps({
            "generated_at": now,
            "status": status,
            "interpretation_type_distribution": analytics["interpretation_type_distribution"],
            "confidence_ceiling_distribution": analytics["confidence_ceiling_distribution"],
            "contribution_count": analytics["aicft_coverage_report"]["contribution_total"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "milestone5_validation.json").write_text(
        json.dumps({
            "milestone": 5,
            "artifact": "Domain_to_AI_CFT.json",
            "generated_at": now,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "analytics_summary": analytics["aicft_coverage_report"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    if not args.quiet:
        print(f"Domain policies: {analytics['aicft_coverage_report']['domain_policy_count']}")
        print(f"Contributions: {analytics['aicft_coverage_report']['contribution_total']}")
        print(f"Status: {status.upper()}")
        for e in errors:
            print(f"  ERROR: {e}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
