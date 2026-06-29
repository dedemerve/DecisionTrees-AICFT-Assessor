"""
evidence_unit_metadata.py — Assessment-object metadata for canonical Evidence Units.

Derives descriptive (non-inferential) metadata to support downstream Behaviour Engine
pattern matching without performing behavioural, ILO, Domain, or AI-CFT inference.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from pipeline_schema import WORKSHEET_DESCRIPTIVE_ONLY, WORKSHEETS_DIR, load_rubric

EVIDENCE_UNIT_TYPES: frozenset[str] = frozenset({
    "definition",
    "formula",
    "drawing",
    "classification",
    "rule",
    "threshold",
    "reflection",
    "prediction",
    "comparison",
    "tree_construction",
    "parameter_selection",
    "model_evaluation",
})

EVIDENCE_ORIGINS: frozenset[str] = frozenset({
    "learner_response",
    "learner_reflection",
    "digital_interaction",
    "recorded_action",
    "observed_event",
    "interview_utterance",
})

SOURCE_QUALITIES: frozenset[str] = frozenset({
    "excellent",
    "good",
    "acceptable",
    "poor",
    "unknown",
})

OBSERVABILITY_LEVELS: frozenset[str] = frozenset({
    "direct",
    "indirect",
    "derived",
})

COMPLETENESS_LEVELS: frozenset[str] = frozenset({
    "complete",
    "partial",
    "blank",
    "illegible",
    "missing",
    "unknown",
})

REVIEW_LEVELS: frozenset[str] = frozenset({
    "none",
    "recommended",
    "required",
    "critical",
})

EXTRACTION_FIELD_TYPES: frozenset[str] = frozenset({
    "free_text",
    "numeric",
    "boolean",
    "structured",
    "table_cell",
    "path_label",
})

RUBRIC_EVAL_TO_EU_TYPE: dict[str, str] = {
    "single_concept": "definition",
    "two_component": "definition",
    "classification": "classification",
    "reasoning": "comparison",
    "threshold": "threshold",
    "feature_name": "tree_construction",
    "branch_labels": "tree_construction",
    "leaf_labels": "classification",
    "rule": "rule",
    "definition": "definition",
    "justification": "comparison",
    "criterion": "comparison",
    "comparison": "comparison",
    "threshold_placement": "threshold",
    "improvement_reasoning": "comparison",
    "peer_evaluation": "model_evaluation",
    "true_false": "model_evaluation",
    "ordering_step": "tree_construction",
    "multiselect_subitem": "model_evaluation",
    "path_matching": "rule",
    "unordered_token_set": "classification",
    "numeric_range": "prediction",
}

RUBRIC_CHECK_TO_EU_TYPE: dict[str, str] = {
    "formula": "formula",
    "numeric": "prediction",
    "numeric_optimal": "parameter_selection",
    "numeric_value": "prediction",
    "numeric_consistency": "model_evaluation",
    "row_consistency": "model_evaluation",
    "tree_validity": "tree_construction",
    "threshold": "threshold",
    "threshold_with_operator": "threshold",
    "rule_consistency_with_WS6": "rule",
    "path_matching": "rule",
    "leaf_consistency_with_tree_logic": "classification",
}

FIELD_TYPE_TO_EU_TYPE: dict[str, str] = {
    "free_text": "definition",
    "numeric": "prediction",
    "boolean": "model_evaluation",
    "structured": "tree_construction",
    "table_cell": "model_evaluation",
    "path_label": "rule",
}

WS_ITEM_OVERRIDES: dict[str, str] = {
    "WS6_tree_structure": "drawing",
    "WS5_B25": "comparison",
    "WS4_B1": "threshold",
    "WS4_B2": "classification",
    "WS4_B3": "comparison",
    "WS4_B4": "model_evaluation",
    "WS4_B5": "prediction",
}


@dataclass
class AssessmentMetadata:
    evidence_unit_type: str
    evidence_origin: str
    source_quality: str
    observability: str
    evidence_completeness: str
    review_level: str
    requires_human_review: bool
    ocr_confidence: float | None
    extraction_confidence: float
    evidence_quality_confidence: float
    alternative_interpretations: list[dict[str, str]]
    uncertainty: str


def _load_extraction_field_meta(worksheet_id: str) -> dict[str, dict[str, Any]]:
    path = WORKSHEETS_DIR / worksheet_id / "extraction_schema.json"
    if not path.exists():
        return {}
    import json
    schema = json.loads(path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for fld in schema.get("fields", []):
        fid = fld.get("field_id")
        if fid:
            out[str(fid)] = fld
    return out


@lru_cache(maxsize=None)
def _rubric_item_config(worksheet_id: str, rubric_item_id: str) -> dict[str, Any]:
    try:
        rubric = load_rubric(worksheet_id)
        return dict(rubric.get("items", {}).get(rubric_item_id, {}))
    except FileNotFoundError:
        return {}


def infer_evidence_unit_type(
    worksheet_id: str,
    field_id: str,
    rubric_item_id: str | None,
    field_meta: dict[str, Any] | None,
) -> str:
    descriptive = WORKSHEET_DESCRIPTIVE_ONLY.get(worksheet_id, [])
    if field_id in descriptive:
        return "reflection"

    if field_id in WS_ITEM_OVERRIDES:
        return WS_ITEM_OVERRIDES[field_id]
    if rubric_item_id and rubric_item_id in WS_ITEM_OVERRIDES:
        return WS_ITEM_OVERRIDES[rubric_item_id]

    rid = rubric_item_id or field_id
    item = _rubric_item_config(worksheet_id, rid) if rid else {}
    check = item.get("check")
    if isinstance(check, str) and check in RUBRIC_CHECK_TO_EU_TYPE:
        return RUBRIC_CHECK_TO_EU_TYPE[check]

    evaluation = item.get("evaluation")
    if isinstance(evaluation, str) and evaluation in RUBRIC_EVAL_TO_EU_TYPE:
        return RUBRIC_EVAL_TO_EU_TYPE[evaluation]

    ftype = (field_meta or {}).get("type")
    if isinstance(ftype, str) and ftype in FIELD_TYPE_TO_EU_TYPE:
        return FIELD_TYPE_TO_EU_TYPE[ftype]

    if worksheet_id == "WS_DT":
        return "model_evaluation"

    return "definition"


def infer_evidence_origin(source_family: str, field_id: str, worksheet_id: str) -> str:
    descriptive = WORKSHEET_DESCRIPTIVE_ONLY.get(worksheet_id, [])
    if field_id in descriptive or source_family == "reflection":
        return "learner_reflection"
    if source_family == "codap":
        return "digital_interaction"
    if source_family == "screen_recording":
        return "recorded_action"
    if source_family == "observation":
        return "observed_event"
    if source_family == "interview":
        return "interview_utterance"
    return "learner_response"


def infer_observability(source_family: str, evidence_origin: str) -> str:
    if source_family == "screen_recording" or evidence_origin == "recorded_action":
        return "derived"
    if source_family in {"reflection", "observation"} or evidence_origin in {
        "learner_reflection", "observed_event",
    }:
        return "indirect"
    return "direct"


def infer_completeness(normalized_content: str, raw_content: str, eu_type: str) -> str:
    lower = normalized_content.strip().lower()
    if lower in {"(bos)", "(blank)", "(empty)"}:
        return "blank"
    if lower in {"(okunamiyor)", "(illegible)"}:
        return "illegible"
    if lower in {"(missing)", "(not_extracted)", "(transcription_error)"}:
        return "missing"

    text = normalized_content.strip()
    if not text:
        return "blank"

    if eu_type in {"definition", "comparison", "rule"} and len(text) < 12:
        return "partial"
    if text.endswith("...") or text.endswith("…"):
        return "partial"
    if re.search(r"_+\s*$", raw_content):
        return "partial"
    if eu_type == "formula" and "=" not in text and "/" not in text and len(text) < 6:
        return "partial"
    if eu_type == "threshold" and not re.search(r"[<>=≤≥]|\\b(en fazla|en az|küçük|büyük)", text, re.I):
        return "partial"

    return "complete"


def infer_source_quality(
    completeness: str,
    ocr_confidence: float | None,
    extraction_confidence: float,
) -> str:
    if completeness in {"missing", "illegible"}:
        return "poor"
    if completeness == "blank":
        return "acceptable"
    if ocr_confidence is None and extraction_confidence >= 0.8 and completeness == "complete":
        return "good"
    if ocr_confidence is None:
        return "unknown"

    if ocr_confidence >= 0.9 and extraction_confidence >= 0.85 and completeness == "complete":
        return "excellent"
    if ocr_confidence >= 0.75 and extraction_confidence >= 0.7 and completeness != "partial":
        return "good"
    if ocr_confidence >= 0.55 or extraction_confidence >= 0.5:
        return "acceptable"
    return "poor"


def infer_evidence_quality_confidence(
    source_quality: str,
    completeness: str,
    extraction_confidence: float,
    ocr_confidence: float | None,
) -> float:
    quality_scores = {
        "excellent": 0.95,
        "good": 0.8,
        "acceptable": 0.6,
        "poor": 0.3,
        "unknown": 0.55,
    }
    completeness_scores = {
        "complete": 1.0,
        "partial": 0.55,
        "blank": 0.2,
        "illegible": 0.15,
        "missing": 0.05,
        "unknown": 0.45,
    }
    base = quality_scores.get(source_quality, 0.5) * completeness_scores.get(completeness, 0.5)
    conf_inputs = [extraction_confidence]
    if ocr_confidence is not None:
        conf_inputs.append(ocr_confidence)
    adapter_mean = sum(conf_inputs) / len(conf_inputs)
    return round(min(1.0, max(0.0, (base * 0.6) + (adapter_mean * 0.4))), 4)


def infer_review_level(
    completeness: str,
    source_quality: str,
    ocr_confidence: float | None,
    extraction_confidence: float,
) -> str:
    if completeness == "blank":
        return "none"
    if completeness == "illegible":
        return "critical"
    if completeness == "missing":
        return "critical" if extraction_confidence < 0.2 else "required"
    if source_quality == "poor":
        return "required"
    if ocr_confidence is not None and ocr_confidence < 0.55:
        return "required"
    if completeness == "partial":
        return "recommended"
    if source_quality == "acceptable":
        return "recommended"
    if ocr_confidence is not None and ocr_confidence < 0.75:
        return "recommended"
    return "none"


def build_alternative_interpretations(
    *,
    completeness: str,
    source_quality: str,
    eu_type: str,
    normalized_content: str,
    existing: list[dict[str, str]],
) -> list[dict[str, str]]:
    alts: list[dict[str, str]] = list(existing)
    seen = {a.get("interpretation", a.get("content", "")) for a in alts}

    def add(interpretation: str, basis: str) -> None:
        if interpretation not in seen:
            alts.append({"interpretation": interpretation, "basis": basis})
            seen.add(interpretation)

    if completeness == "partial":
        if eu_type == "definition":
            add("definition may be incomplete", "Response shorter than expected for a definition field.")
        elif eu_type == "threshold":
            add("threshold expression may be incomplete", "Operator or value may be missing.")
        else:
            add("response may be incomplete", "Content appears truncated or underspecified.")
    if completeness == "illegible":
        add("possible OCR misread", "Field marked illegible; transcription may not match learner intent.")
    if completeness == "blank":
        add("absence of evidence", "Learner left field blank; non-response is not negative evidence.")
    if source_quality in {"poor", "unknown"}:
        add("possible OCR truncation", "Source quality limits fidelity of the captured response.")
    if eu_type == "formula" and completeness == "complete" and "/" not in normalized_content:
        add("formula notation may differ", "Equivalent formula forms may use different notation.")
    if eu_type == "comparison" and "çünkü" not in normalized_content.lower() and "because" not in normalized_content.lower():
        add("justification may be implicit", "Comparative claim may lack explicit reasoning text.")

    return alts


def derive_assessment_metadata(
    *,
    worksheet_id: str,
    field_id: str,
    rubric_item_id: str | None,
    source_family: str,
    raw_content: str,
    normalized_content: str,
    extraction_confidence: float,
    ocr_confidence: float | None,
    uncertainty: str,
    alternative_interpretations: list[dict[str, str]],
) -> AssessmentMetadata:
    field_meta = _load_extraction_field_meta(worksheet_id).get(field_id, {})
    eu_type = infer_evidence_unit_type(worksheet_id, field_id, rubric_item_id, field_meta)

    origin = infer_evidence_origin(source_family, field_id, worksheet_id)
    observability = infer_observability(source_family, origin)
    completeness = infer_completeness(normalized_content, raw_content, eu_type)
    source_quality = infer_source_quality(completeness, ocr_confidence, extraction_confidence)
    eq_conf = infer_evidence_quality_confidence(
        source_quality, completeness, extraction_confidence, ocr_confidence,
    )
    review_level = infer_review_level(
        completeness, source_quality, ocr_confidence, extraction_confidence,
    )
    alts = build_alternative_interpretations(
        completeness=completeness,
        source_quality=source_quality,
        eu_type=eu_type,
        normalized_content=normalized_content,
        existing=alternative_interpretations,
    )

    unc = uncertainty
    if review_level == "critical" and unc == "none":
        unc = "Critical review required before evidence can support downstream inference."
    elif review_level == "required" and unc == "none":
        unc = "Human review recommended due to source or completeness limitations."

    return AssessmentMetadata(
        evidence_unit_type=eu_type,
        evidence_origin=origin,
        source_quality=source_quality,
        observability=observability,
        evidence_completeness=completeness,
        review_level=review_level,
        requires_human_review=review_level != "none",
        ocr_confidence=ocr_confidence,
        extraction_confidence=extraction_confidence,
        evidence_quality_confidence=eq_conf,
        alternative_interpretations=alts,
        uncertainty=unc,
    )
