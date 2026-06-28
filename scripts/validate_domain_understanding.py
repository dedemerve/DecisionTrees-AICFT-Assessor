#!/usr/bin/env python3
"""
validate_domain_understanding.py — Milestone 4 verification and analytics.

Validates Domain_Understanding.json ontology and LO_to_Domain_Understanding.json inference mapping.
Generates coverage matrices and convergence statistics under reports/milestone4/.
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
DOMAIN_PATH = REPO / "framework" / "Domain_Understanding.json"
MAP_PATH = REPO / "framework" / "LO_to_Domain_Understanding.json"
ILO_PATH = REPO / "framework" / "Learning_Objects.json"
B2I_PATH = REPO / "framework" / "Behaviour_to_ILO.json"
REPORT_DIR = REPO / "reports" / "milestone4"

DOMAIN_PATTERN = re.compile(r"^DU_[A-Z][A-Z0-9_]+$")
ILO_PATTERN = re.compile(r"^ILO_[A-Z][A-Z0-9_]+$")
VALID_ROLES = frozenset({"primary", "secondary", "contextual", "diagnostic"})
VALID_CONFIDENCE = frozenset({"high", "moderate", "low", "baseline"})
REQUIRED_DOMAIN_FIELDS = frozenset({
    "id", "title", "construct_dimension", "assessment_construct_type", "construct_definition",
    "theoretical_rationale", "inclusion_criteria", "exclusion_criteria",
    "convergence_requirements", "contradiction_handling", "indicative_ilos",
    "not_equivalent_to", "construct_validation",
})
REQUIRED_CV_FIELDS = frozenset({
    "what_construct_represents",
    "supporting_evidence",
    "non_supporting_evidence",
    "not_formed_when",
    "confusable_with",
})
REQUIRED_RECORD_FIELDS = frozenset({
    "domain_id", "mapping_role", "mapping_confidence", "confidence_basis",
    "supporting_rationale", "counter_evidence", "construct_alignment",
})


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def iter_ilo_records(mappings: dict[str, Any]) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    out: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for iid, bundle in mappings.items():
        for rec in bundle.get("records", []):
            out.append((iid, bundle, rec))
    return out


def validate_domain_ontology(
    domain_doc: dict[str, Any],
    ilo_data: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not domain_doc.get("design_constraint"):
        errors.append("missing design_constraint at root")
    if domain_doc.get("ontology_layer") != "assessment_construct":
        warnings.append("ontology_layer should be assessment_construct")

    domains = domain_doc.get("domains", {})
    ilo_ids = set(ilo_data["learning_objects"])

    for did, dom in domains.items():
        if did != dom.get("id"):
            errors.append(f"{did}: id mismatch")
        if not DOMAIN_PATTERN.match(did):
            errors.append(f"{did}: invalid domain id pattern")
        missing = REQUIRED_DOMAIN_FIELDS - dom.keys()
        if missing:
            errors.append(f"{did}: missing fields {missing}")
        if dom.get("assessment_construct_type") != "emergent":
            errors.append(f"{did}: assessment_construct_type must be emergent")
        for iid in dom.get("indicative_ilos", []):
            if iid not in ilo_ids:
                errors.append(f"{did}: unknown indicative ILO {iid}")
        if len(dom.get("inclusion_criteria", [])) < 2:
            errors.append(f"{did}: need ≥2 inclusion_criteria")
        if len(dom.get("exclusion_criteria", [])) < 2:
            errors.append(f"{did}: need ≥2 exclusion_criteria")
        conv = dom.get("convergence_requirements", {})
        if "minimum_distinct_ilos" not in conv:
            errors.append(f"{did}: convergence_requirements incomplete")
        cv = dom.get("construct_validation", {})
        missing_cv = REQUIRED_CV_FIELDS - cv.keys()
        if missing_cv:
            errors.append(f"{did}: construct_validation missing {missing_cv}")
        for field in ("supporting_evidence", "non_supporting_evidence", "not_formed_when", "confusable_with"):
            if field in cv and len(cv[field]) < 2:
                errors.append(f"{did}: construct_validation.{field} needs ≥2 items")
        if cv.get("what_construct_represents") and len(cv["what_construct_represents"]) < 40:
            errors.append(f"{did}: what_construct_represents too brief")

    dimension_counts = Counter(d.get("construct_dimension") for d in domains.values())
    return errors, warnings, {
        "domain_count": len(domains),
        "domain_dimension_distribution": dict(dimension_counts),
        "domain_ids": sorted(domains),
    }


def validate_lo_mapping(
    map_doc: dict[str, Any],
    domain_doc: dict[str, Any],
    ilo_data: dict[str, Any],
) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []

    if not map_doc.get("confidence_policy", {}).get("qualitative_only"):
        errors.append("LO mapping: qualitative_only confidence required")

    domain_ids = set(domain_doc["domains"])
    ilo_ids = set(ilo_data["learning_objects"])
    mappings = map_doc.get("mappings", {})

    if set(mappings) != ilo_ids:
        errors.append(f"ILO key mismatch: missing={sorted(ilo_ids - set(mappings))}")

    domain_ilo_count: dict[str, set[str]] = defaultdict(set)
    role_counts: Counter[str] = Counter()
    cross_pairs: list[dict[str, str]] = []
    rejected_stats: list[dict[str, str]] = []
    pair_set: set[tuple[str, str]] = set()

    for iid, bundle, rec in iter_ilo_records(mappings):
        prefix = f"{iid}/{rec.get('domain_id')}"
        missing = REQUIRED_RECORD_FIELDS - rec.keys()
        if missing:
            errors.append(f"{prefix}: missing {missing}")

        did = rec.get("domain_id")
        if did not in domain_ids:
            errors.append(f"{prefix}: unknown domain")
        pair = (iid, did)
        if pair in pair_set:
            errors.append(f"duplicate pair {pair}")
        pair_set.add(pair)
        domain_ilo_count[did].add(iid)

        role = rec.get("mapping_role")
        if role not in VALID_ROLES:
            errors.append(f"{prefix}: invalid role {role!r}")
        role_counts[role] += 1

        conf = rec.get("mapping_confidence")
        if isinstance(conf, (int, float)):
            errors.append(f"{prefix}: numeric confidence forbidden")
        elif conf not in VALID_CONFIDENCE:
            errors.append(f"{prefix}: invalid confidence {conf!r}")

        align = rec.get("construct_alignment", {})
        if align.get("cross_construct"):
            cross_pairs.append({
                "ilo_id": iid,
                "domain_id": did,
                "ilo_dimension": align.get("ilo_dimension", ""),
                "domain_dimension": align.get("domain_dimension", ""),
                "mapping_role": role or "",
                "rationale": rec.get("cross_construct_rationale", ""),
            })
            if not rec.get("cross_construct_rationale"):
                errors.append(f"{prefix}: cross_construct requires rationale")

    for iid, bundle in mappings.items():
        roles = [r.get("mapping_role") for r in bundle.get("records", [])]
        if roles == ["diagnostic"]:
            continue
        if roles.count("primary") != 1:
            errors.append(f"{iid}: expected 1 primary domain, found {roles.count('primary')}")
        for rej in bundle.get("rejected_alternatives", []):
            if not rej.get("reason_rejected"):
                errors.append(f"{iid}: rejected alternative missing reason_rejected")
            rejected_stats.append({
                "ilo_id": iid,
                "domain_id": rej.get("domain_id", ""),
                "reason_rejected": rej.get("reason_rejected", ""),
            })

    orphan_domains = sorted(domain_ids - set(domain_ilo_count))
    if orphan_domains:
        errors.append(f"orphan domains (no ILO mapping): {orphan_domains}")

    underrepresented = [
        {"domain_id": did, "ilo_count": len(domain_ilo_count.get(did, set()))}
        for did in sorted(domain_ids)
        if len(domain_ilo_count.get(did, set())) <= 1
    ]

    domain_coverage = [
        {
            "domain_id": did,
            "ilo_count": len(domain_ilo_count.get(did, set())),
            "ilos": sorted(domain_ilo_count.get(did, set())),
        }
        for did in sorted(domain_ids)
    ]
    domain_coverage.sort(key=lambda x: -x["ilo_count"])

    ilo_domain_count = [
        {"ilo_id": iid, "domain_count": len(bundle.get("records", [])), "domains": [r["domain_id"] for r in bundle.get("records", [])]}
        for iid, bundle in sorted(mappings.items())
    ]

    construct_matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for _, _, rec in iter_ilo_records(mappings):
        idim = rec["construct_alignment"]["ilo_dimension"]
        ddim = rec["construct_alignment"]["domain_dimension"]
        construct_matrix[idim][ddim] += 1

    analytics = {
        "domain_coverage_report": {
            "domain_to_ilo_count": domain_coverage,
            "underrepresented_domains": underrepresented,
            "ilo_to_domain_count": ilo_domain_count,
        },
        "construct_matrix": {k: dict(v) for k, v in sorted(construct_matrix.items())},
        "cross_construct_matrix": {"pair_count": len(cross_pairs), "pairs": cross_pairs},
        "mapping_density": {
            "ilo_count": len(mappings),
            "domain_count": len(domain_ids),
            "accepted_pair_count": len(pair_set),
            "avg_domains_per_ilo": round(len(pair_set) / len(mappings), 2) if mappings else 0,
            "rejected_alternative_count": len(rejected_stats),
        },
        "role_ratios": {
            "counts": dict(role_counts),
            "primary_ratio": round(role_counts["primary"] / len(pair_set), 3) if pair_set else 0,
            "secondary_ratio": round(role_counts["secondary"] / len(pair_set), 3) if pair_set else 0,
        },
        "rejected_alternative_statistics": {
            "total_rejected": len(rejected_stats),
            "by_ilo": dict(Counter(r["ilo_id"] for r in rejected_stats)),
            "records": rejected_stats,
        },
    }

    if underrepresented:
        warnings.append(f"{len(underrepresented)} domain(s) linked from only one ILO (may be intentional)")

    return errors, warnings, analytics


def build_domain_independence_matrix(
    domain_doc: dict[str, Any],
    map_doc: dict[str, Any],
) -> dict[str, Any]:
    """Pairwise domain overlap from shared ILO mappings (accepted records)."""
    domain_ilos: dict[str, set[str]] = defaultdict(set)
    for iid, bundle in map_doc.get("mappings", {}).items():
        for rec in bundle.get("records", []):
            domain_ilos[rec["domain_id"]].add(iid)

    domain_ids = sorted(domain_doc["domains"])
    pair_notes = {
        (p["domain_a"], p["domain_b"]): p for p in domain_doc.get("domain_pair_differentiation", [])
    }
    pair_notes.update({
        (p["domain_b"], p["domain_a"]): p for p in domain_doc.get("domain_pair_differentiation", [])
    })

    indicative_ilos: dict[str, set[str]] = {
        did: set(domain_doc["domains"][did].get("indicative_ilos", [])) for did in domain_ids
    }

    def risk_label(shared_mapped: int, shared_indicative: int, dim_a: str, dim_b: str) -> str:
        score = max(shared_mapped, shared_indicative)
        if score >= 4:
            return "high"
        if score >= 3:
            return "moderate" if dim_a == dim_b else "moderate"
        if score == 2:
            return "moderate"
        if score == 1:
            return "low"
        return "minimal"

    rows: list[dict[str, Any]] = []
    for i, da in enumerate(domain_ids):
        for db in domain_ids[i + 1:]:
            shared_mapped = sorted(domain_ilos[da] & domain_ilos[db])
            shared_indicative = sorted(indicative_ilos[da] & indicative_ilos[db])
            dim_a = domain_doc["domains"][da]["construct_dimension"]
            dim_b = domain_doc["domains"][db]["construct_dimension"]
            note = pair_notes.get((da, db), {})
            rows.append({
                "domain_a": da,
                "domain_a_title": domain_doc["domains"][da]["title"],
                "domain_b": db,
                "domain_b_title": domain_doc["domains"][db]["title"],
                "shared_mapped_ilo_count": len(shared_mapped),
                "shared_mapped_ilos": shared_mapped,
                "shared_indicative_ilo_count": len(shared_indicative),
                "shared_indicative_ilos": shared_indicative,
                "overlap_risk": note.get("overlap_risk", risk_label(
                    len(shared_mapped), len(shared_indicative), dim_a, dim_b,
                )),
                "same_construct_dimension": dim_a == dim_b,
                "discriminating_criteria": note.get("discriminating_criteria", ""),
            })
    rows.sort(key=lambda r: (
        -max(r["shared_mapped_ilo_count"], r["shared_indicative_ilo_count"]),
        r["domain_a"],
        r["domain_b"],
    ))
    high_moderate = [r for r in rows if r["overlap_risk"] in ("high", "moderate")]

    return {
        "matrix_type": "domain_independence",
        "pair_count": len(rows),
        "high_or_moderate_risk_pairs": len(high_moderate),
        "pairs": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    domain_doc = load_json(DOMAIN_PATH)
    map_doc = load_json(MAP_PATH)
    ilo_data = load_json(ILO_PATH)

    d_errors, d_warnings, d_summary = validate_domain_ontology(domain_doc, ilo_data)
    m_errors, m_warnings, analytics = validate_lo_mapping(map_doc, domain_doc, ilo_data)

    errors = d_errors + m_errors
    warnings = d_warnings + m_warnings
    independence = build_domain_independence_matrix(domain_doc, map_doc)
    status = "pass" if not errors else "fail"
    now = datetime.now(timezone.utc).isoformat()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    (args.reports_dir / "domain_independence_matrix.json").write_text(
        json.dumps({"generated_at": now, **independence}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "domain_coverage_report.json").write_text(
        json.dumps({"generated_at": now, **analytics["domain_coverage_report"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "construct_matrix.json").write_text(
        json.dumps({"generated_at": now, **analytics["construct_matrix"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "cross_construct_matrix.json").write_text(
        json.dumps({"generated_at": now, **analytics["cross_construct_matrix"]}, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "mapping_statistics.json").write_text(
        json.dumps({
            "generated_at": now,
            "status": status,
            "domain_ontology_summary": d_summary,
            "mapping_density": analytics["mapping_density"],
            "role_ratios": analytics["role_ratios"],
            "rejected_alternative_statistics": analytics["rejected_alternative_statistics"],
            "cross_construct_pair_count": analytics["cross_construct_matrix"]["pair_count"],
        }, indent=2) + "\n",
        encoding="utf-8",
    )
    (args.reports_dir / "milestone4_validation.json").write_text(
        json.dumps({
            "milestone": 4,
            "artifacts": ["Domain_Understanding.json", "LO_to_Domain_Understanding.json"],
            "generated_at": now,
            "status": status,
            "errors": errors,
            "warnings": warnings,
            "domain_ontology_summary": d_summary,
            "analytics_summary": analytics["mapping_density"],
            "independence_summary": {
                "pair_count": independence["pair_count"],
                "high_or_moderate_risk_pairs": independence["high_or_moderate_risk_pairs"],
            },
        }, indent=2) + "\n",
        encoding="utf-8",
    )

    if not args.quiet:
        print(f"Domains: {d_summary['domain_count']}")
        print(f"ILO→Domain pairs: {analytics['mapping_density']['accepted_pair_count']}")
        print(f"Cross-construct pairs: {analytics['cross_construct_matrix']['pair_count']}")
        print(f"Status: {status.upper()}")
        for e in errors:
            print(f"  ERROR: {e}")

    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
