#!/usr/bin/env python3
"""
build_worksheet_bundles.py

Generate worksheets/WS{1,3,4,5,6,7,10,11}/ bundles from legacy rubrics and frozen OB ontology.
Each bundle contains exactly five evidence-collection files (no ILO/Domain/AI-CFT).
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from pipeline_schema import (  # noqa: E402
    ITEM_IDS_WS1,
    ITEM_IDS_WS3,
    ITEM_IDS_WS4,
    ITEM_IDS_WS5,
    ITEM_IDS_WS6,
    ITEM_IDS_WS7,
    ITEM_IDS_WS10,
    ITEM_IDS_WS11_COGNITIVE,
    ITEM_IDS_WS11_DEMOGRAPHIC,
    ITEM_IDS_WS11_DESCRIPTIVE,
    ITEM_IDS_WS11_FEEDBACK,
    ITEM_IDS_WS11_SURVEY,
    RUBRICS_DIR,
    is_interpretive_rubric_item,
)
from worksheet_bundle_data import (  # noqa: E402
    ALL_WORKSHEETS,
    BEHAVIOUR_MAP,
    BUNDLE_FILES,
    DEPLOYED_WORKSHEETS,
    EXTRACTION_NOTES,
    OB_REF,
    VALIDITY_NOTES,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

WORKSHEETS_DIR = REPO_ROOT / "worksheets"

EXTRACTION_FIELD_IDS: dict[str, list[str]] = {
    "WS1": ITEM_IDS_WS1,
    "WS3": ITEM_IDS_WS3,
    "WS4": ITEM_IDS_WS4,
    "WS5": ITEM_IDS_WS5,
    "WS6": ITEM_IDS_WS6,
    "WS7": ITEM_IDS_WS7,
    "WS10": ITEM_IDS_WS10,
    "WS11": (
        ITEM_IDS_WS11_FEEDBACK
        + ITEM_IDS_WS11_COGNITIVE
        + ITEM_IDS_WS11_DESCRIPTIVE
    ),
}

FIELD_TYPE_HINTS: dict[str, str] = {
    "WS5": "table_cell",
    "WS6": "structured",
    "WS7": "path_label",
    "WS10": "numeric",
}

WS4_FIELD_TYPES: dict[str, str] = {
    "WS4_B1": "free_text",
    "WS4_B2": "free_text",
    "WS4_B3": "free_text",
    "WS4_B4": "free_text",
    "WS4_B5": "numeric",
}

WS4_LOCATION_HINTS: dict[str, str] = {
    "WS4_B1": "Blank 1 — threshold line between avocado and french fries",
    "WS4_B2": "Blank 2 — four misclassified foods (jelibon, kraker, yulaf, avokado)",
    "WS4_B3": "Blank 3 — fewer misclassifications after new threshold",
    "WS4_B4": "Blank 4 — Pia haklı; apple and raspberry jam same fat value",
    "WS4_B5": "Blank 5 — learned energy threshold (160–2223)",
}


def _field_type(worksheet: str, field_id: str) -> str:
    if worksheet == "WS4":
        return WS4_FIELD_TYPES.get(field_id, "free_text")
    default = FIELD_TYPE_HINTS.get(worksheet, "free_text")
    if worksheet == "WS5" and field_id == "WS5_B25":
        return "free_text"
    if worksheet == "WS11" and field_id.startswith("WS11_L"):
        return "free_text"
    if worksheet == "WS11" and field_id.startswith("WS11_Q"):
        return "boolean"
    return default


def _rubric_item_to_extraction_fields(
    worksheet: str,
    item_id: str,
    item: dict[str, Any],
) -> list[str]:
    if fields := item.get("fields"):
        return list(fields)
    if worksheet == "WS5" and item_id.startswith("WS5_row"):
        row_num = item_id.replace("WS5_row", "")
        base = (int(row_num) - 1) * 4
        return [f"WS5_B{base + i}" for i in range(1, 5)]
    if item_id in EXTRACTION_FIELD_IDS.get(worksheet, []):
        return [item_id]
    return []


def build_extraction_schema(worksheet: str, rubric: dict[str, Any]) -> dict[str, Any]:
    status = "deployed" if worksheet in DEPLOYED_WORKSHEETS else "not_deployed"
    if status == "not_deployed":
        return {
            "worksheet": worksheet,
            "curriculum_status": status,
            "pipeline_stage": "extraction_only",
            "interpretation_prohibited": True,
            "ocr_engine": "claude_vision",
            "source_type": "worksheet",
            "note": "Worksheet not deployed in the ProDaBi unplugged corpus.",
            "fields": [],
        }

    fields: list[dict[str, Any]] = []
    seen: set[str] = set()

    for item_id, item in rubric.get("items", {}).items():
        for fid in _rubric_item_to_extraction_fields(worksheet, item_id, item):
            if fid in seen:
                continue
            seen.add(fid)
            fields.append({
                "field_id": fid,
                "rubric_item_id": item_id,
                "type": _field_type(worksheet, fid),
                "required": True,
                "location_hint": WS4_LOCATION_HINTS.get(fid, f"{worksheet} worksheet response region")
                if worksheet == "WS4"
                else f"{worksheet} worksheet response region",
            })

    for fid in EXTRACTION_FIELD_IDS.get(worksheet, []):
        if fid not in seen:
            fields.append({
                "field_id": fid,
                "type": _field_type(worksheet, fid),
                "required": fid not in ITEM_IDS_WS11_DESCRIPTIVE and fid not in ITEM_IDS_WS11_FEEDBACK,
                "location_hint": (
                    WS4_LOCATION_HINTS.get(fid, f"{worksheet} worksheet response region")
                    if worksheet == "WS4"
                    else f"{worksheet} worksheet response region"
                ),
                "note": (
                    "Demographic field — no correct answer; exclude from scoring and competency"
                    if fid in ITEM_IDS_WS11_DEMOGRAPHIC
                    else "Survey/Likert — no correct answer; exclude from scoring and competency"
                    if fid in ITEM_IDS_WS11_SURVEY
                    else "Descriptive-only field"
                    if fid in ITEM_IDS_WS11_DESCRIPTIVE
                    else None
                ),
            })
            seen.add(fid)

    fields = [{k: v for k, v in f.items() if v is not None} for f in fields]
    from worksheet_blank_registry import enrich_extraction_field

    fields = [enrich_extraction_field(worksheet, f, rubric) for f in fields]
    fields.sort(key=lambda x: x["field_id"])

    return {
        "worksheet": worksheet,
        "curriculum_status": status,
        "pipeline_stage": "extraction_only",
        "interpretation_prohibited": True,
        "ocr_engine": "claude_vision",
        "source_type": "worksheet",
        "note": EXTRACTION_NOTES.get(worksheet, ""),
        "fields": fields,
    }


def build_behaviour_opportunities(
    worksheet: str,
    rubric: dict[str, Any],
) -> dict[str, Any]:
    status = "deployed" if worksheet in DEPLOYED_WORKSHEETS else "not_deployed"
    items: dict[str, Any] = {}
    if status == "deployed":
        ws_map = BEHAVIOUR_MAP.get(worksheet, {})
        for item_id in rubric.get("items", {}):
            if item_id not in ws_map:
                log.warning("%s: no behaviour map for rubric item %s", worksheet, item_id)
                continue
            entry = dict(ws_map[item_id])
            item = rubric["items"][item_id]
            if "extraction_fields" not in entry:
                ef = _rubric_item_to_extraction_fields(worksheet, item_id, item)
                if ef:
                    entry["extraction_fields"] = ef
            items[item_id] = entry

    return {
        "worksheet": worksheet,
        "curriculum_status": status,
        "behaviour_ontology_reference": OB_REF,
        "note": (
            "Evidence opportunity map only. Observable Behaviour candidates per rubric item. "
            "No instructional learning object, domain, or competency mapping at worksheet layer."
        ),
        "items": items,
    }


def build_validity_notes(worksheet: str) -> dict[str, Any]:
    status = "deployed" if worksheet in DEPLOYED_WORKSHEETS else "not_deployed"
    base = dict(VALIDITY_NOTES.get(worksheet, {}))
    return {
        "worksheet": worksheet,
        "curriculum_status": status,
        **base,
    }


def build_answer_key(worksheet: str, rubric: dict[str, Any]) -> dict[str, Any]:
    if worksheet == "WS_DT":
        status = "deployed"
    else:
        status = "deployed" if worksheet in DEPLOYED_WORKSHEETS else "not_deployed"
    items: dict[str, Any] = {}
    if status == "deployed":
        for item_id, item in rubric.get("items", {}).items():
            key: dict[str, Any] = {}
            for field in (
                "check", "evaluation", "answer", "correct_answer",
                "example_answer", "example_note", "tolerance", "accepted_forms",
                "token_groups", "need_tokens", "partial_on_tokens", "order_insensitive",
                "accept_sets", "extra_aliases", "accepted_aliases",
                "min_value", "max_value", "zero_credit_hints",
                "scoring_mode", "fields", "consistency_rules", "formula_reference",
                "partial_credit_rule", "partial_score", "credit_levels", "method", "tie_rule",
                "consistency_check", "mcr_note", "leaf_labels",
            ):
                if field in item:
                    key[field] = item[field]
            if is_interpretive_rubric_item(item, rubric, item_id=item_id):
                key["interpretive"] = True
                key["open_response"] = True
            elif item.get("check") or item.get("correct_answer") is not None:
                key["deterministic"] = True
            elif item.get("evaluation") in ("unordered_token_set", "any_of_tokens"):
                key["deterministic"] = True
            elif not key.get("example_answer"):
                key["open_response"] = True
            items[item_id] = key

    out = {
        "worksheet": worksheet,
        "curriculum_status": status,
        "note": "Scoring reference derived from rubric; extraction remains non-interpretive.",
        "items": items,
    }
    if rubric.get("equivalence_sets"):
        out["equivalence_sets"] = rubric["equivalence_sets"]
    if rubric.get("scoring_policy"):
        out["scoring_policy"] = rubric["scoring_policy"]
    if rubric.get("scoring_model"):
        out["scoring_model"] = rubric["scoring_model"]
    if rubric.get("row_scoring"):
        out["row_scoring"] = rubric["row_scoring"]
    if rubric.get("item_scoring"):
        out["item_scoring"] = rubric["item_scoring"]
    if rubric.get("field_map"):
        out["field_map"] = rubric["field_map"]
    from answer_key_enrichment import enrich_answer_key

    return enrich_answer_key(worksheet, rubric, out)


def load_legacy_rubric(worksheet: str) -> dict[str, Any]:
    path = RUBRICS_DIR / f"{worksheet}_rubric.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {
        "worksheet": worksheet,
        "curriculum_status": "not_deployed",
        "items": {},
    }


def build_rubric(worksheet: str) -> dict[str, Any]:
    rubric = load_legacy_rubric(worksheet)
    out = dict(rubric)
    out.pop("curriculum_status", None)
    out.pop("schema_version", None)
    if worksheet in DEPLOYED_WORKSHEETS or worksheet == "WS_DT":
        out.setdefault("curriculum_status", "deployed")
    return out


def write_bundle(worksheet: str) -> Path:
    out_dir = WORKSHEETS_DIR / worksheet
    out_dir.mkdir(parents=True, exist_ok=True)

    for existing in out_dir.iterdir():
        if existing.is_file() and existing.name not in BUNDLE_FILES:
            log.warning(
                "Extra file in %s (not removed): %s — bundle allows only %s",
                out_dir.relative_to(REPO_ROOT),
                existing.name,
                ", ".join(BUNDLE_FILES),
            )

    rubric = build_rubric(worksheet)
    artifacts = {
        "rubric.json": rubric,
        "extraction_schema.json": build_extraction_schema(worksheet, rubric),
        "behaviour_opportunities.json": build_behaviour_opportunities(worksheet, rubric),
        "validity_notes.json": build_validity_notes(worksheet),
        "answer_key.json": build_answer_key(worksheet, rubric),
    }

    for name, payload in artifacts.items():
        path = out_dir / name
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        log.info("Wrote %s", path.relative_to(REPO_ROOT))

    return out_dir


def main() -> int:
    for ws in ALL_WORKSHEETS:
        write_bundle(ws)
    log.info("Built %d worksheet bundles under %s", len(ALL_WORKSHEETS), WORKSHEETS_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
