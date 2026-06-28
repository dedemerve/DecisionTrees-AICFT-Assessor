"""
schema_validate.py — Structural validation for portfolio and mapping artifacts.

Uses hand-written checks (no jsonschema dependency) aligned with schema/*.schema.json.
"""

from __future__ import annotations

from typing import Any

from pipeline_schema import FRAMEWORK_SCHEMA_VERSION, PORTFOLIO_SCHEMA_VERSION

EVIDENCE_UNITS_SCHEMA_VERSION = "1.1"
SOURCE_FAMILIES_EU = frozenset({
    "worksheet", "codap", "screen_recording", "reflection", "observation", "interview",
})
EU_TYPES = frozenset({
    "definition", "formula", "drawing", "classification", "rule", "threshold",
    "reflection", "prediction", "comparison", "tree_construction",
    "parameter_selection", "model_evaluation",
})
EU_ORIGINS = frozenset({
    "learner_response", "learner_reflection", "digital_interaction",
    "recorded_action", "observed_event", "interview_utterance",
})
SOURCE_QUALITIES = frozenset({"excellent", "good", "acceptable", "poor", "unknown"})
OBSERVABILITY = frozenset({"direct", "indirect", "derived"})
COMPLETENESS = frozenset({"complete", "partial", "blank", "illegible", "missing", "unknown"})
REVIEW_LEVELS = frozenset({"none", "recommended", "required", "critical"})
EU_ID_PATTERN = __import__("re").compile(r"^EU_[0-9]{6}$")

STRENGTHS = frozenset({"none", "weak", "moderate", "strong"})
LEVELS = frozenset({"Acquire", "Deepen", "Create"})
LEVEL_STATUS = frozenset({"met", "partial", "insufficient"})
EVIDENCE_TYPES = frozenset({
    "direct", "supporting", "application", "early_indicator", "reflective", "prior_belief",
})
PORTFOLIO_WEIGHTS = frozenset({"full", "baseline", "diagnostic"})


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_portfolio_v1(data: dict[str, Any], prefix: str = "portfolio") -> list[str]:
    errors: list[str] = []

    if data.get("schema_version") != PORTFOLIO_SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {PORTFOLIO_SCHEMA_VERSION!r}")
    if not data.get("student_id"):
        _err(errors, f"{prefix}: missing student_id")

    for field in (
        "framework", "aspect", "methodology", "worksheets_scored",
        "learning_objects", "competency_level_summary", "baseline_evidence",
        "ai_cft_proposal", "data_gaps", "evidence_item_count", "updated_at",
    ):
        if field not in data:
            _err(errors, f"{prefix}: missing {field!r}")

    methodology = data.get("methodology", {})
    if not methodology.get("assessment_framework_version"):
        _err(errors, f"{prefix}: methodology.assessment_framework_version required")
    if not methodology.get("portfolio_builder_version"):
        _err(errors, f"{prefix}: methodology.portfolio_builder_version required")

    if not isinstance(data.get("worksheets_scored"), list) or not data["worksheets_scored"]:
        _err(errors, f"{prefix}: worksheets_scored must be a non-empty array")

    los = data.get("learning_objects", {})
    if not isinstance(los, dict):
        _err(errors, f"{prefix}: learning_objects must be an object")
    else:
        for lo_id, lo_data in los.items():
            if not lo_id.startswith("LO3."):
                _err(errors, f"{prefix} {lo_id}: invalid LO id")
            peak = lo_data.get("peak_strength")
            if peak not in STRENGTHS:
                _err(errors, f"{prefix} {lo_id}: invalid peak_strength")
            if lo_data.get("expected_level") not in LEVELS:
                _err(errors, f"{prefix} {lo_id}: invalid expected_level")

    summary = data.get("competency_level_summary", {})
    for lv in ("Acquire", "Deepen", "Create"):
        if summary.get(lv) not in LEVEL_STATUS:
            _err(errors, f"{prefix}: competency_level_summary.{lv} invalid")

    proposal = data.get("ai_cft_proposal", {})
    if proposal.get("Aspect3") not in LEVELS:
        _err(errors, f"{prefix}: ai_cft_proposal.Aspect3 invalid")
    if proposal.get("is_final") is not False:
        _err(errors, f"{prefix}: ai_cft_proposal.is_final must be false")
    if proposal.get("decision_owner") != "researcher":
        _err(errors, f"{prefix}: ai_cft_proposal.decision_owner must be 'researcher'")

    for i, gap in enumerate(data.get("data_gaps", [])):
        if not gap.get("worksheet") or not isinstance(gap.get("items"), list):
            _err(errors, f"{prefix}: data_gaps[{i}] malformed")

    if not isinstance(data.get("baseline_evidence"), list):
        _err(errors, f"{prefix}: baseline_evidence must be an array")

    return errors


def validate_mapping_v2(data: dict[str, Any], source: str = "") -> list[str]:
    prefix = f"{source}: " if source else ""
    errors: list[str] = []

    if data.get("schema_version") != FRAMEWORK_SCHEMA_VERSION:
        _err(errors, f"{prefix}schema_version must be {FRAMEWORK_SCHEMA_VERSION!r}")
    if not data.get("worksheet"):
        _err(errors, f"{prefix}missing worksheet")

    items = data.get("items")
    if not isinstance(items, dict) or not items:
        _err(errors, f"{prefix}items must be a non-empty object")
        return errors

    for item_id, comps in items.items():
        if not isinstance(comps, list) or not comps:
            _err(errors, f"{prefix}{item_id}: competencies must be a non-empty array")
            continue
        for j, comp in enumerate(comps):
            if not isinstance(comp, dict):
                _err(errors, f"{prefix}{item_id}[{j}]: must be object")
                continue
            for req in ("lo", "strength", "evidence_type", "expected_level", "rationale", "role", "portfolio_weight"):
                if req not in comp:
                    _err(errors, f"{prefix}{item_id}[{j}]: missing {req}")
            if comp.get("strength") not in {"weak", "moderate", "strong"}:
                _err(errors, f"{prefix}{item_id}[{j}]: invalid strength")
            if comp.get("evidence_type") not in EVIDENCE_TYPES:
                _err(errors, f"{prefix}{item_id}[{j}]: invalid evidence_type")
            if comp.get("portfolio_weight") not in PORTFOLIO_WEIGHTS:
                _err(errors, f"{prefix}{item_id}[{j}]: invalid portfolio_weight")
            if len(comp.get("rationale", "")) < 10:
                _err(errors, f"{prefix}{item_id}[{j}]: rationale too short")

    return errors


def _scan_forbidden_inferential(obj: Any, path: str, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            if str(key).lower() in {
                "behaviour_id", "observable_behaviour", "observable_behaviour_id",
                "ilo_id", "learning_object_id", "lo", "domain_id",
                "domain_understanding", "ai_cft", "competency", "competency_id",
                "inference",
            }:
                _err(errors, f"{path}: forbidden inferential key {key!r}")
            _scan_forbidden_inferential(value, f"{path}.{key}", errors)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _scan_forbidden_inferential(item, f"{path}[{i}]", errors)


def validate_evidence_units_v1(
    data: dict[str, Any],
    prefix: str = "evidence_units",
) -> list[str]:
    """Validate student or per-worksheet evidence_units.json (Layer 2 runtime)."""
    errors: list[str] = []

    if data.get("schema_version") != EVIDENCE_UNITS_SCHEMA_VERSION:
        _err(errors, f"{prefix}: schema_version must be {EVIDENCE_UNITS_SCHEMA_VERSION!r}")
    if not data.get("student_id"):
        _err(errors, f"{prefix}: missing student_id")
    if not data.get("updated_at"):
        _err(errors, f"{prefix}: missing updated_at")
    if not data.get("definition"):
        _err(errors, f"{prefix}: missing assessment-object definition")

    if data.get("artifact") == "worksheet_evidence_units" and not data.get("worksheet_id"):
        _err(errors, f"{prefix}: worksheet evidence_units requires worksheet_id")

    units = data.get("evidence_units")
    if not isinstance(units, list):
        _err(errors, f"{prefix}: evidence_units must be an array")
        return errors

    seen_ids: set[str] = set()
    for i, unit in enumerate(units):
        up = f"{prefix}.evidence_units[{i}]"
        if not isinstance(unit, dict):
            _err(errors, f"{up}: must be object")
            continue

        eu_id = unit.get("evidence_unit_id", "")
        if not EU_ID_PATTERN.match(str(eu_id)):
            _err(errors, f"{up}: invalid evidence_unit_id {eu_id!r}")
        elif eu_id in seen_ids:
            _err(errors, f"{up}: duplicate evidence_unit_id {eu_id!r}")
        else:
            seen_ids.add(str(eu_id))

        for req in (
            "student_id", "worksheet_id", "item_id",
            "evidence_unit_type", "evidence_origin",
            "source_family", "source_file", "source_quality",
            "observability", "evidence_completeness",
            "raw_content", "normalized_content", "confidence", "provenance",
            "uncertainty", "alternative_interpretations",
            "review_level", "requires_human_review", "timestamp",
        ):
            if req not in unit:
                _err(errors, f"{up}: missing {req!r}")

        if unit.get("evidence_unit_type") not in EU_TYPES:
            _err(errors, f"{up}: invalid evidence_unit_type")
        if unit.get("evidence_origin") not in EU_ORIGINS:
            _err(errors, f"{up}: invalid evidence_origin")
        if unit.get("source_family") not in SOURCE_FAMILIES_EU:
            _err(errors, f"{up}: invalid source_family")
        if unit.get("source_quality") not in SOURCE_QUALITIES:
            _err(errors, f"{up}: invalid source_quality")
        if unit.get("observability") not in OBSERVABILITY:
            _err(errors, f"{up}: invalid observability")
        if unit.get("evidence_completeness") not in COMPLETENESS:
            _err(errors, f"{up}: invalid evidence_completeness")
        if unit.get("review_level") not in REVIEW_LEVELS:
            _err(errors, f"{up}: invalid review_level")
        if not isinstance(unit.get("requires_human_review"), bool):
            _err(errors, f"{up}: requires_human_review must be boolean")

        conf = unit.get("confidence")
        if not isinstance(conf, dict):
            _err(errors, f"{up}: confidence must be object")
        else:
            ext = conf.get("extraction")
            eq = conf.get("evidence_quality")
            ocr = conf.get("ocr")
            if not isinstance(ext, (int, float)) or not (0 <= float(ext) <= 1):
                _err(errors, f"{up}.confidence.extraction invalid")
            if not isinstance(eq, (int, float)) or not (0 <= float(eq) <= 1):
                _err(errors, f"{up}.confidence.evidence_quality invalid")
            if ocr is not None and (not isinstance(ocr, (int, float)) or not (0 <= float(ocr) <= 1)):
                _err(errors, f"{up}.confidence.ocr invalid")

        prov = unit.get("provenance")
        if not isinstance(prov, dict):
            _err(errors, f"{up}: provenance must be object")
        else:
            for req in (
                "adapter", "source_file", "worksheet", "field",
                "timestamp", "pipeline_version", "extraction_artifact",
            ):
                if not prov.get(req):
                    _err(errors, f"{up}.provenance: missing {req!r}")

        alts = unit.get("alternative_interpretations")
        if not isinstance(alts, list):
            _err(errors, f"{up}: alternative_interpretations must be array")
        else:
            for j, alt in enumerate(alts):
                if not isinstance(alt, dict):
                    _err(errors, f"{up}.alternative_interpretations[{j}]: must be object")
                elif not alt.get("interpretation") or not alt.get("basis"):
                    _err(errors, f"{up}.alternative_interpretations[{j}]: needs interpretation and basis")

        review = unit.get("review_level")
        requires = unit.get("requires_human_review")
        if review == "none" and requires is True:
            _err(errors, f"{up}: requires_human_review must be false when review_level is none")
        if review in {"recommended", "required", "critical"} and requires is False:
            _err(errors, f"{up}: requires_human_review must be true when review_level is {review!r}")

        _scan_forbidden_inferential(unit, up, errors)

    return errors


def validate_all_mappings_v2(mappings_dir) -> list[str]:
    """Validate every mappings/<WS>_AICFT_mapping.json against schema 2.0."""
    import json
    from pathlib import Path

    errors: list[str] = []
    root = Path(mappings_dir)
    for path in sorted(root.glob("*_AICFT_mapping.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors.extend(validate_mapping_v2(data, path.name))
    return errors
