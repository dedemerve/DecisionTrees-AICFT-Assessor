"""
schema_validate.py — Structural validation for portfolio and mapping artifacts.

Uses hand-written checks (no jsonschema dependency) aligned with schema/*.schema.json.
For draft-2020-12 instance validation, use schema_json_validate.py and validate_schemas.py.
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
EU_ID_PATTERN = __import__("re").compile(r"^EU_[0-9]{6}$")

EU_FORBIDDEN_OUTPUT_KEYS = frozenset({
    "schema_version",
    "evidence_unit_id",
    "field_id",
    "evidence_origin",
    "source_family",
    "source_file",
    "source_quality",
    "observability",
    "timestamp",
    "updated_at",
    "provenance",
    "raw_content",
    "normalized_content",
    "uncertainty",
    "alternative_interpretations",
    "review_level",
    "requires_human_review",
})

EU_DOCUMENT_FORBIDDEN_OUTPUT_KEYS = frozenset({
    "schema_version",
    "updated_at",
    "definition",
    "note",
    "artifact",
    "pipeline_stage",
    "source_stage",
})

STRENGTHS = frozenset({"none", "weak", "moderate", "strong"})
LEVELS = frozenset({"Acquire", "Deepen", "Create"})
LEVEL_STATUS = frozenset({"met", "partial", "insufficient"})
EVIDENCE_TYPES = frozenset({
    "direct", "supporting", "application", "early_indicator", "reflective", "prior_belief",
})
PORTFOLIO_WEIGHTS = frozenset({"full", "baseline", "diagnostic"})


def _err(errors: list[str], msg: str) -> None:
    errors.append(msg)


def validate_portfolio(data: dict[str, Any], prefix: str = "portfolio") -> list[str]:
    errors: list[str] = []

    if data.get("schema_version") is not None:
        _err(errors, f"{prefix}: schema_version must not appear in pipeline output")
    if not data.get("student_id"):
        _err(errors, f"{prefix}: missing student_id")

    for field in (
        "framework", "aspect", "methodology", "worksheets_scored",
        "learning_objects", "competency_level_summary", "baseline_evidence",
        "ai_cft_proposal", "data_gaps", "evidence_item_count",
    ):
        if field not in data:
            _err(errors, f"{prefix}: missing {field!r}")

    if data.get("updated_at") is not None:
        _err(errors, f"{prefix}: updated_at must not appear in pipeline output")

    methodology = data.get("methodology", {})
    if not methodology.get("aggregation_note"):
        _err(errors, f"{prefix}: methodology.aggregation_note required")
    if methodology.get("assessment_framework_version") is not None:
        _err(errors, f"{prefix}: methodology.assessment_framework_version must not appear in output")
    if methodology.get("portfolio_builder_version") is not None:
        _err(errors, f"{prefix}: methodology.portfolio_builder_version must not appear in output")

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


def validate_mapping(data: dict[str, Any], source: str = "") -> list[str]:
    prefix = f"{source}: " if source else ""
    errors: list[str] = []

    if data.get("schema_version") is not None:
        _err(errors, f"{prefix}schema_version must not appear in mapping output")
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


def validate_evidence_units(
    data: dict[str, Any],
    prefix: str = "evidence_units",
) -> list[str]:
    """Validate student or per-worksheet evidence_units.json (Layer 2 runtime)."""
    errors: list[str] = []

    if data.get("schema_version") is not None:
        _err(errors, f"{prefix}: schema_version must not appear in pipeline output")
    if data.get("updated_at") is not None:
        _err(errors, f"{prefix}: updated_at must not appear in pipeline output")
    if not data.get("student_id"):
        _err(errors, f"{prefix}: missing student_id")

    for key in EU_DOCUMENT_FORBIDDEN_OUTPUT_KEYS:
        if key in data and key not in {"schema_version", "updated_at"}:
            _err(errors, f"{prefix}: {key} must not appear in pipeline output")

    doc_worksheet_id = data.get("worksheet_id")
    if doc_worksheet_id is not None and not doc_worksheet_id:
        _err(errors, f"{prefix}: worksheet_id must not be empty when present")

    units = data.get("evidence_units")
    if not isinstance(units, list):
        _err(errors, f"{prefix}: evidence_units must be an array")
        return errors

    seen_items: set[tuple[str, str, str]] = set()
    for i, unit in enumerate(units):
        up = f"{prefix}.evidence_units[{i}]"
        if not isinstance(unit, dict):
            _err(errors, f"{up}: must be object")
            continue

        for key in EU_FORBIDDEN_OUTPUT_KEYS:
            if key in unit:
                _err(errors, f"{up}: {key} must not appear in pipeline output")

        item_id = unit.get("item_id", "")
        st_id = unit.get("student_id", data.get("student_id", ""))
        ws_id = unit.get("worksheet_id", doc_worksheet_id or "")
        item_key = (st_id, ws_id, item_id)
        if not item_id:
            _err(errors, f"{up}: missing item_id")
        elif item_key in seen_items:
            _err(errors, f"{up}: duplicate item {item_id!r} for {ws_id!r}")
        else:
            seen_items.add(item_key)

        if doc_worksheet_id:
            for redundant in ("student_id", "worksheet_id"):
                if redundant in unit:
                    _err(errors, f"{up}: redundant {redundant!r} in per-worksheet file")
        else:
            for req_ctx in ("student_id", "worksheet_id"):
                if not unit.get(req_ctx):
                    _err(errors, f"{up}: missing {req_ctx!r}")

        for req in (
            "item_id",
            "evidence_unit_type",
            "evidence_completeness",
            "content",
            "confidence",
        ):
            if req not in unit:
                _err(errors, f"{up}: missing {req!r}")

        if unit.get("evidence_unit_type") not in EU_TYPES:
            _err(errors, f"{up}: invalid evidence_unit_type")
        if unit.get("evidence_completeness") not in COMPLETENESS:
            _err(errors, f"{up}: invalid evidence_completeness")
        if not isinstance(unit.get("content"), str):
            _err(errors, f"{up}: content must be string")

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

        _scan_forbidden_inferential(unit, up, errors)

    return errors


def validate_all_mappings(mappings_dir) -> list[str]:
    """Validate every mappings/<WS>_AICFT_mapping.json against schema 2.0."""
    import json
    from pathlib import Path

    errors: list[str] = []
    root = Path(mappings_dir)
    for path in sorted(root.glob("*_AICFT_mapping.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        errors.extend(validate_mapping(data, path.name))
    return errors
