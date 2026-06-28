#!/usr/bin/env python3
"""
validate_behaviour_to_ilo.py — Milestone 3 inference-layer verification and analytics.

Generates: coverage matrix, construct matrix, cross-construct matrix,
mapping density, role ratios, counter-evidence and rejected-alternative statistics.

Usage:
  python scripts/validate_behaviour_to_ilo.py
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
MAP_PATH = REPO / "framework" / "Behaviour_to_ILO.json"
OB_PATH = REPO / "framework" / "Observable_Behaviours.json"
ILO_PATH = REPO / "framework" / "Learning_Objects.json"

OB_PATTERN = re.compile(r"^OB_[A-Z]{3}_[0-9]{3}$")
ILO_PATTERN = re.compile(r"^ILO_[A-Z][A-Z0-9_]+$")
VALID_ROLES = frozenset({"primary", "secondary", "contextual", "diagnostic"})
VALID_CONFIDENCE = frozenset({"high", "moderate", "low", "baseline"})
VALID_BASIS = frozenset({
    "construct_alignment", "instructional_consensus", "frozen_ilo_behaviour_link",
    "contextual_facilitation", "cross_construct_bridge", "diagnostic_baseline",
})
REQUIRED_RECORD_FIELDS = frozenset({
    "ilo_id", "mapping_role", "mapping_confidence", "confidence_basis",
    "supporting_rationale", "counter_evidence", "construct_alignment",
})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_records(mappings: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    """Yield (behaviour_id, bundle, record)."""
    out: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for bid, bundle in mappings.items():
        if isinstance(bundle, dict) and "records" in bundle:
            for rec in bundle["records"]:
                out.append((bid, bundle, rec))
        elif isinstance(bundle, list):
            for rec in bundle:
                out.append((bid, {"records": bundle, "rejected_alternatives": []}, rec))
    return out


def validate_structure(
    mapping_doc: dict[str, Any],
    ob_data: dict[str, Any],
    ilo_data: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    if ob_data.get("framework_version") != "1.0":
        errors.append("Observable_Behaviours.json framework_version must be 1.0")
    if ilo_data.get("framework_version") != "1.0":
        errors.append("Learning_Objects.json framework_version must be 1.0")

    policy = mapping_doc.get("confidence_policy", {})
    if not policy.get("qualitative_only"):
        errors.append("confidence_policy.qualitative_only must be true")
    if policy.get("prohibited") != "ad_hoc_numeric_confidence":
        warnings.append("confidence_policy should prohibit ad_hoc_numeric_confidence")

    ob_ids = set(ob_data["behaviours"])
    ilo_ids = set(ilo_data["learning_objects"])
    mappings = mapping_doc.get("mappings", {})

    if set(mappings) != ob_ids:
        errors.append(f"behaviour key mismatch: missing={sorted(ob_ids - set(mappings))}")

    ilo_behaviour_count: dict[str, set[str]] = defaultdict(set)
    role_counts: Counter[str] = Counter()
    confidence_counts: Counter[str] = Counter()
    cross_construct_pairs: list[dict[str, str]] = []
    counter_stats: Counter[str] = Counter()
    counter_blocking = 0
    rejected_stats: list[dict[str, str]] = []
    pair_set: set[tuple[str, str]] = set()

    for bid, bundle, rec in iter_records(mappings):
        prefix = f"{bid}/{rec.get('ilo_id')}"
        missing = REQUIRED_RECORD_FIELDS - rec.keys()
        if missing:
            errors.append(f"{prefix}: missing {missing}")

        iid = rec.get("ilo_id")
        if iid not in ilo_ids:
            errors.append(f"{prefix}: unknown ilo")
        pair = (bid, iid)
        if pair in pair_set:
            errors.append(f"duplicate pair {pair}")
        pair_set.add(pair)
        ilo_behaviour_count[iid].add(bid)

        role = rec.get("mapping_role")
        if role not in VALID_ROLES:
            errors.append(f"{prefix}: invalid role {role!r}")
        role_counts[role] += 1

        conf = rec.get("mapping_confidence")
        if isinstance(conf, (int, float)):
            errors.append(f"{prefix}: numeric mapping_confidence forbidden; use qualitative level")
        elif conf not in VALID_CONFIDENCE:
            errors.append(f"{prefix}: invalid mapping_confidence {conf!r}")
        confidence_counts[conf] += 1

        basis = rec.get("confidence_basis", [])
        if not basis:
            errors.append(f"{prefix}: empty confidence_basis")
        for b in basis:
            if b not in VALID_BASIS:
                errors.append(f"{prefix}: invalid confidence_basis item {b!r}")

        align = rec.get("construct_alignment", {})
        if align.get("cross_construct"):
            cross_construct_pairs.append({
                "behaviour_id": bid,
                "ilo_id": iid,
                "behaviour_dimension": align.get("behaviour_dimension", ""),
                "ilo_dimension": align.get("ilo_dimension", ""),
                "mapping_role": role or "",
                "rationale": rec.get("cross_construct_rationale", ""),
            })
            if not rec.get("cross_construct_rationale"):
                errors.append(f"{prefix}: cross_construct requires cross_construct_rationale")

        for ce in rec.get("counter_evidence", []):
            counter_stats[ce.get("source_type", "unknown")] += 1
            if ce.get("blocks_escalation"):
                counter_blocking += 1

    for bid, bundle in mappings.items():
        if not isinstance(bundle, dict):
            continue
        for rej in bundle.get("rejected_alternatives", []):
            if not rej.get("reason_rejected"):
                errors.append(f"{bid}: rejected alternative missing reason_rejected")
            rejected_stats.append({
                "behaviour_id": bid,
                "ilo_id": rej.get("ilo_id", ""),
                "reason_rejected": rej.get("reason_rejected", ""),
            })

    # One primary per behaviour, except diagnostic-only baseline bundles
    for bid in mappings:
        records = mappings[bid]["records"] if isinstance(mappings[bid], dict) else mappings[bid]
        roles = [r.get("mapping_role") for r in records]
        if roles == ["diagnostic"]:
            continue
        if roles.count("primary") != 1:
            errors.append(f"{bid}: expected 1 primary, found {roles.count('primary')}")

    # Bidirectional ILO consistency
    for iid, ilo in ilo_data["learning_objects"].items():
        expected = set(ilo["related_behaviours"])
        actual = ilo_behaviour_count.get(iid, set())
        if expected != actual:
            errors.append(f"{iid}: related_behaviours mismatch")

    orphan_ilos = sorted(ilo_ids - set(ilo_behaviour_count))
    if orphan_ilos:
        errors.append(f"orphan ILOs: {orphan_ilos}")

    # Construct matrix: behaviour_dim -> ilo_dim counts
    construct_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for bid, _, rec in iter_records(mappings):
        bd = rec["construct_alignment"]["behaviour_dimension"]
        idim = rec["construct_alignment"]["ilo_dimension"]
        construct_matrix[bd][idim] += 1

    ilo_coverage = [
        {"ilo_id": iid, "behaviour_count": len(ilo_behaviour_count.get(iid, set())), "behaviours": sorted(ilo_behaviour_count.get(iid, set()))}
        for iid in sorted(ilo_ids)
    ]
    ilo_coverage.sort(key=lambda x: -x["behaviour_count"])

    underrepresented = [row for row in ilo_coverage if row["behaviour_count"] <= 1]

    analytics = {
        "mapping_coverage_report": {
            "ilo_to_behaviour_count": ilo_coverage,
            "underrepresented_ilos": underrepresented,
        },
        "construct_matrix": {k: dict(v) for k, v in sorted(construct_matrix.items())},
        "cross_construct_matrix": {
            "pair_count": len(cross_construct_pairs),
            "pairs": cross_construct_pairs,
        },
        "mapping_density": {
            "behaviour_count": len(mappings),
            "ilo_count": len(ilo_behaviour_count),
            "accepted_pair_count": len(pair_set),
            "avg_ilos_per_behaviour": round(len(pair_set) / len(mappings), 2) if mappings else 0,
            "rejected_alternative_count": len(rejected_stats),
        },
        "role_ratios": {
            "counts": dict(role_counts),
            "primary_ratio": round(role_counts["primary"] / len(pair_set), 3) if pair_set else 0,
            "secondary_ratio": round(role_counts["secondary"] / len(pair_set), 3) if pair_set else 0,
            "contextual_ratio": round(role_counts["contextual"] / len(pair_set), 3) if pair_set else 0,
            "diagnostic_ratio": round(role_counts["diagnostic"] / len(pair_set), 3) if pair_set else 0,
        },
        "confidence_level_distribution": dict(confidence_counts),
        "counter_evidence_statistics": {
            "total_counter_items": sum(counter_stats.values()),
            "by_source_type": dict(counter_stats),
            "blocking_escalation_count": counter_blocking,
        },
        "rejected_alternative_statistics": {
            "total_rejected": len(rejected_stats),
            "by_behaviour": dict(Counter(r["behaviour_id"] for r in rejected_stats)),
            "records": rejected_stats,
        },
    }

    if underrepresented:
        warnings.append(f"{len(underrepresented)} ILO(s) supported by only one behaviour")

    return errors, warnings, analytics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mapping", type=Path, default=MAP_PATH)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    mapping_doc = load_json(args.mapping)
    ob_data = load_json(OB_PATH)
    ilo_data = load_json(ILO_PATH)

    errors, warnings, analytics = validate_structure(mapping_doc, ob_data, ilo_data)
    status = "pass" if not errors else "fail"

    from milestone_reporting import write_validation  # noqa: E402

    write_validation(3, {
        "artifact": "Behaviour_to_ILO.json",
        "status": status,
        "errors": errors,
        "warnings": warnings,
        "mapping_coverage_report": analytics["mapping_coverage_report"],
        "construct_matrix": analytics["construct_matrix"],
        "cross_construct_matrix": analytics["cross_construct_matrix"],
        "mapping_statistics": {
            "mapping_density": analytics["mapping_density"],
            "role_ratios": analytics["role_ratios"],
            "confidence_level_distribution": analytics["confidence_level_distribution"],
            "counter_evidence_statistics": analytics["counter_evidence_statistics"],
            "rejected_alternative_statistics": analytics["rejected_alternative_statistics"],
        },
    })

    if not args.quiet:
        print(f"Behaviour_to_ILO: {analytics['mapping_density']['accepted_pair_count']} pairs")
        print(f"Cross-construct pairs: {analytics['cross_construct_matrix']['pair_count']}")
        print(f"Status: {status.upper()}")
        for e in errors:
            print(f"  ERROR: {e}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
