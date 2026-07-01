"""
Central registry: printed blank number → field_id → scoring mode.

Used by bundle generation, validation modules, and PIPELINE documentation.
Reference answer files (when fixed): data/ws10_energy_reference.json, ws7_sample_tree.json,
data/prodabi_food_cards.csv.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pipeline_schema import (
    ITEM_IDS_DT,
    ITEM_IDS_WS1,
    ITEM_IDS_WS10,
    ITEM_IDS_WS11_COGNITIVE,
    ITEM_IDS_WS11_DESCRIPTIVE,
    ITEM_IDS_WS11_FEEDBACK,
    ITEM_IDS_WS3,
    ITEM_IDS_WS4,
    ITEM_IDS_WS5,
    ITEM_IDS_WS6,
    ITEM_IDS_WS7,
    scoring_item_ids,
)

ScoringMode = str  # fixed_exact | computed | equivalence | interpretive | cross_worksheet | descriptive | survey | demographic

WORKSHEET_META: dict[str, dict[str, Any]] = {
    "WS1": {"pipeline_group": "A", "reference": None, "validation_module": None},
    "WS3": {"pipeline_group": "A", "reference": None, "validation_module": None},
    "WS4": {"pipeline_group": "A", "reference": None, "validation_module": None},
    "WS5": {
        "pipeline_group": "B",
        "reference": "data/prodabi_food_cards.csv",
        "validation_module": "ws5_validation",
        "validate_script": "scripts/validate_ws5.py",
        "score_script": "scripts/score_ws5.py",
    },
    "WS6": {
        "pipeline_group": "B",
        "reference": "data/prodabi_food_cards.csv",
        "validation_module": "ws6_validation",
        "validate_script": "scripts/validate_ws6.py",
        "score_script": "scripts/score_ws6.py",
    },
    "WS7": {
        "pipeline_group": "B",
        "reference": "data/ws7_sample_tree.json",
        "validation_module": "ws7_validation",
        "validate_script": "scripts/validate_ws7.py",
        "score_script": "scripts/score_ws7.py",
        "cross_worksheet": ["WS6"],
    },
    "WS10": {
        "pipeline_group": "A",
        "reference": "data/ws10_energy_reference.json",
        "validation_module": "ws10_validation",
        "validate_script": "scripts/validate_ws10.py",
        "score_script": "scripts/score_ws10.py",
    },
    "WS11": {
        "pipeline_group": "A",
        "reference": "data/ws11_feedback_reference.json",
        "validation_module": "ws11_validation",
        "validate_script": "scripts/validate_ws11.py",
        "score_script": "scripts/score_ws11.py",
    },
    "WS_DT": {"pipeline_group": "DT", "reference": None, "validation_module": None},
}

# WS6 OCR field → composite scoring item
WS6_FIELD_TO_SCORING_ITEM: dict[str, str] = {
    "WS6_B1": "WS6_root_feature",
    "WS6_B2": "WS6_root_threshold",
    "WS6_B3": "WS6_root_labels",
    "WS6_B4": "WS6_root_labels",
    "WS6_B5": "WS6_leaves",
    "WS6_B6": "WS6_inner_feature",
    "WS6_B7": "WS6_inner_threshold",
    "WS6_B8": "WS6_inner_labels",
    "WS6_B9": "WS6_inner_labels",
    "WS6_B10": "WS6_leaves",
    "WS6_B11": "WS6_leaves",
    "WS6_B12": "WS6_leaves",
    "WS6_B13": "WS6_leaves",
}

WS5_ROW_FOR_BLANK: dict[str, str] = {}
for _row in range(1, 7):
    _base = (_row - 1) * 4
    _item = f"WS5_row{_row}"
    for _off, _cell in enumerate(("threshold", "correct", "errors", "mcr"), start=1):
        WS5_ROW_FOR_BLANK[f"WS5_B{_base + _off}"] = _item
WS5_ROW_FOR_BLANK["WS5_B25"] = "WS5_B25"


def _printed_blank_ws1(field_id: str) -> int | None:
    if field_id.startswith("WS1_B"):
        try:
            return int(field_id.replace("WS1_B", ""))
        except ValueError:
            return None
    return None


def _scoring_mode_for_item(worksheet: str, item_id: str, item: dict[str, Any]) -> ScoringMode:
    check = item.get("check") or ""
    ev = item.get("evaluation") or ""
    if check == "any_of_tokens":
        return "equivalence"
    if check in {"numeric_exact", "path_matching", "true_false", "ordering_step", "multiselect_subitem"}:
        return "fixed_exact"
    if check in {"numeric", "numeric_range", "unordered_token_set"}:
        return "fixed_exact"
    if check in {"formula"}:
        return "fixed_exact"
    if check in {"row_consistency", "b25_minimum_errors", "threshold_with_operator", "tree_validity",
                 "leaf_consistency_with_tree_logic", "emit_consistency", "numeric_consistency"}:
        return "computed"
    if check == "rule_consistency_with_WS6":
        return "cross_worksheet"
    if item.get("scoring_mode") == "interpretive" or ev in {
        "classification", "reasoning", "threshold", "threshold_placement",
        "improvement_reasoning", "peer_evaluation", "definition", "rule",
    }:
        return "interpretive"
    if ev:
        return "interpretive"
    return "interpretive"


def _load_ws11_feedback_reference() -> dict[str, Any]:
    from pathlib import Path
    import json

    path = Path(__file__).resolve().parent / "data" / "ws11_feedback_reference.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _field_meta_ws11_feedback(field_id: str) -> dict[str, Any]:
    ref = _load_ws11_feedback_reference()["fields"].get(field_id, {})
    n = ref.get("printed_question") or int(field_id.replace("WS11_B", ""))
    mode = ref.get("scoring_mode", "survey")
    meta: dict[str, Any] = {
        "printed_blank": n,
        "printed_question": n,
        "scoring_mode": mode,
        "scored": False,
        "scoring_item_id": None,
        "question_tr": ref.get("prompt_tr"),
        "response_kind": ref.get("response_kind"),
    }
    if ref.get("options"):
        meta["allowed_responses"] = ref["options"]
    return meta


def _field_meta_ws10(field_id: str) -> dict[str, Any]:
    from ws10_validation import load_ws10_reference

    ref = load_ws10_reference()
    meta = ref["blank_map"].get(field_id, {})
    return {
        "printed_blank": meta.get("blank_number"),
        "scoring_mode": "fixed_exact",
        "scored": True,
        "scoring_item_id": field_id,
        "fixed_response": meta.get("response"),
        "printed_threshold": meta.get("printed_threshold"),
    }


def _field_meta_ws7(field_id: str) -> dict[str, Any]:
    if field_id.startswith("WS7_P1"):
        from ws7_validation import P1_ANSWERS

        return {
            "printed_blank": int(field_id.replace("WS7_P1_box", "")),
            "scoring_mode": "fixed_exact",
            "scored": True,
            "scoring_item_id": field_id,
            "fixed_response": P1_ANSWERS.get(field_id),
        }
    n = int(field_id.replace("WS7_B", ""))
    return {
        "printed_blank": n,
        "scoring_mode": "cross_worksheet" if n <= 3 else "descriptive",
        "scored": n <= 3,
        "scoring_item_id": field_id if n <= 3 else None,
        "depends_on": ["WS6"] if n <= 3 else None,
    }


def field_registry_entry(worksheet: str, field_id: str, rubric: dict[str, Any] | None = None) -> dict[str, Any]:
    """Metadata for one OCR/scoring field."""
    ws_meta = WORKSHEET_META.get(worksheet, {})
    entry: dict[str, Any] = {
        "field_id": field_id,
        "worksheet": worksheet,
        "pipeline_group": ws_meta.get("pipeline_group"),
        "reference": ws_meta.get("reference"),
        "validation_module": ws_meta.get("validation_module"),
    }

    if worksheet == "WS10":
        entry.update(_field_meta_ws10(field_id))
        return entry

    if worksheet == "WS7":
        entry.update(_field_meta_ws7(field_id))
        return entry

    if worksheet == "WS5":
        n = int(field_id.replace("WS5_B", ""))
        entry.update({
            "printed_blank": n,
            "scoring_mode": "computed",
            "scored": field_id in WS5_ROW_FOR_BLANK and WS5_ROW_FOR_BLANK[field_id] in set(
                scoring_item_ids("WS5")
            ),
            "scoring_item_id": WS5_ROW_FOR_BLANK.get(field_id),
            "cell_role": ("threshold", "correct", "errors", "mcr")[(n - 1) % 4]
            if n <= 24 else "final_choice",
        })
        return entry

    if worksheet == "WS6":
        n = int(field_id.replace("WS6_B", ""))
        item_id = WS6_FIELD_TO_SCORING_ITEM.get(field_id)
        entry.update({
            "printed_blank": n,
            "scoring_mode": "computed",
            "scored": item_id in set(scoring_item_ids("WS6")),
            "scoring_item_id": item_id,
        })
        return entry

    if worksheet == "WS1":
        n = _printed_blank_ws1(field_id)
        item_id = field_id
        item = (rubric or {}).get("items", {}).get(item_id, {})
        entry.update({
            "printed_blank": n,
            "scoring_mode": _scoring_mode_for_item(worksheet, item_id, item),
            "scored": True,
            "scoring_item_id": item_id,
        })
        return entry

    if worksheet in {"WS3", "WS4"}:
        n = int(field_id.split("_B")[1])
        item_id = field_id
        item = (rubric or {}).get("items", {}).get(item_id, {})
        entry.update({
            "printed_blank": n,
            "scoring_mode": _scoring_mode_for_item(worksheet, item_id, item),
            "scored": True,
            "scoring_item_id": item_id,
        })
        return entry

    if worksheet == "WS11":
        scored_set = set(scoring_item_ids("WS11"))
        item_id = field_id if field_id in scored_set else None
        item = (rubric or {}).get("items", {}).get(item_id or "", {})
        if field_id in ITEM_IDS_WS11_FEEDBACK:
            entry.update(_field_meta_ws11_feedback(field_id))
            return entry
        if field_id in ITEM_IDS_WS11_DESCRIPTIVE:
            mode = "descriptive"
            scored = False
        elif item_id:
            mode = _scoring_mode_for_item(worksheet, item_id, item)
            scored = True
        else:
            mode = "descriptive"
            scored = False
        entry.update({
            "scoring_mode": mode,
            "scored": scored,
            "scoring_item_id": item_id,
        })
        return entry

    if worksheet == "WS_DT":
        scored_set = set(scoring_item_ids("WS_DT"))
        item_id = field_id if field_id in scored_set else None
        item = (rubric or {}).get("items", {}).get(item_id or "", {})
        entry.update({
            "scoring_mode": _scoring_mode_for_item(worksheet, item_id or field_id, item) if item_id else "interpretive",
            "scored": bool(item_id),
            "scoring_item_id": item_id,
        })
        return entry

    entry.update({"scoring_mode": "interpretive", "scored": field_id in set(scoring_item_ids(worksheet))})
    return entry


def worksheet_field_ids(worksheet: str) -> list[str]:
    mapping = {
        "WS_DT": ITEM_IDS_DT,
        "WS1": ITEM_IDS_WS1,
        "WS3": ITEM_IDS_WS3,
        "WS4": ITEM_IDS_WS4,
        "WS5": ITEM_IDS_WS5,
        "WS6": ITEM_IDS_WS6,
        "WS7": ITEM_IDS_WS7,
        "WS10": ITEM_IDS_WS10,
        "WS11": ITEM_IDS_WS11_FEEDBACK + ITEM_IDS_WS11_COGNITIVE + ITEM_IDS_WS11_DESCRIPTIVE,
    }
    return list(mapping.get(worksheet, []))


@lru_cache(maxsize=16)
def build_worksheet_registry(worksheet: str) -> dict[str, Any]:
    """Full registry for one worksheet."""
    from pipeline_schema import load_rubric

    rubric = load_rubric(worksheet)
    fields = {
        fid: field_registry_entry(worksheet, fid, rubric)
        for fid in worksheet_field_ids(worksheet)
    }
    ws = WORKSHEET_META.get(worksheet, {})
    return {
        "worksheet": worksheet,
        "pipeline_group": ws.get("pipeline_group"),
        "reference": ws.get("reference"),
        "validation_module": ws.get("validation_module"),
        "score_script": ws.get("score_script"),
        "scoring_item_ids": scoring_item_ids(worksheet),
        "fields": fields,
    }


def enrich_extraction_field(
    worksheet: str,
    field: dict[str, Any],
    rubric: dict[str, Any],
) -> dict[str, Any]:
    """Add registry metadata to an extraction_schema field dict."""
    fid = field["field_id"]
    meta = field_registry_entry(worksheet, fid, rubric)
    out = dict(field)
    if meta.get("printed_blank") is not None:
        out["printed_blank"] = meta["printed_blank"]
    out["scoring_mode"] = meta.get("scoring_mode")
    out["scored"] = meta.get("scored", False)
    if meta.get("scoring_item_id"):
        out["scoring_item_id"] = meta["scoring_item_id"]
    if meta.get("fixed_response") is not None:
        out["fixed_response"] = meta["fixed_response"]
    if meta.get("cell_role"):
        out["cell_role"] = meta["cell_role"]
    if meta.get("depends_on"):
        out["depends_on"] = meta["depends_on"]
    if meta.get("question_tr"):
        out["question_tr"] = meta["question_tr"]
    if meta.get("response_kind"):
        out["response_kind"] = meta["response_kind"]
    if meta.get("allowed_responses"):
        out["allowed_responses"] = meta["allowed_responses"]
    hint = out.get("location_hint", "")
    if meta.get("printed_blank") and "Blank" not in hint and "Soru" not in hint:
        q = meta.get("question_tr") or hint
        out["location_hint"] = f"Printed question {meta['printed_blank']} — {q}".strip(" —")
    return out
