"""
pipeline_schema.py

Single source of truth for worksheet item IDs, rubric/mapping paths, and
scored-vs-OCR field distinctions. Consumed by ocr_pipeline.py and
worksheet_assessor.py.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).parent
RUBRICS_DIR = REPO_ROOT / "rubrics"
WORKSHEETS_DIR = REPO_ROOT / "worksheets"
MAPPINGS_DIR = REPO_ROOT / "mappings"
SCHEMA_DIR = REPO_ROOT / "schema"

RUBRIC_SCHEMA_VERSION = "3.0"

# LO = Learning Object (AI-CFT competency object, e.g. LO3.1.1). JSON field: learning_objects.
LO_GLOSSARY = "Learning Object"

ARTIFACT_SCHEMA_VERSION = "3.0"
PORTFOLIO_SCHEMA_VERSION = "3.0"
FRAMEWORK_SCHEMA_VERSION = "2.0"

# Group B: deterministic Python validation before scoring (reviewer taxonomy).
WORKSHEETS_REQUIRING_VALIDATION = frozenset({"WS5", "WS6", "WS7"})

PIPELINE_STAGES = ("extraction", "validation", "scoring", "evidence", "summary")

# Semantic scoring must use components[].idea — not legacy keyword lists.
RUBRIC_LEGACY_KEYWORD_FIELDS = frozenset({
    "accepted_terms",
    "accepted_answers",
    "required_idea",
    "accepted_yes",
    "accepted_no",
    "accepted_positive",
    "accepted_negative",
    "accepted_terms_component_2",
    "accepted_operators",
})

# Deterministic checks that do not require components.
RUBRIC_DETERMINISTIC_CHECKS = frozenset({
    "formula",
    "numeric",
    "numeric_optimal",
    "numeric_value",
    "numeric_consistency",
    "emit_output",
    "emit_consistency",
    "row_consistency",
    "tree_validity",
    "threshold",
    "threshold_with_operator",
    "rule_consistency_with_WS6",
    "path_matching",
})

RUBRIC_DETERMINISTIC_EVALUATIONS = frozenset({
    "true_false",
    "ordering_step",
    "multiselect_subitem",
    "path_matching",
})

# ---------------------------------------------------------------------------
# OCR extraction item IDs (verbatim fields transcribed from worksheets)
# ---------------------------------------------------------------------------

ITEM_IDS_DT: list[str] = [
    "DT_A_Q1", "DT_A_Q2", "DT_A_Q3", "DT_A_Q4",
    "DT_B_Q1", "DT_B_Q2", "DT_B_Q3", "DT_B_Q4",
    "DT_C_Q1", "DT_C_Q2", "DT_C_Q3",
    "DT_D_Q1", "DT_D_Q2", "DT_D_Q3", "DT_D_Q4",
    "DT_E_sensitivity", "DT_E_MCR", "DT_E_Q1", "DT_E_Q2", "DT_E_Q3", "DT_E_Q4",
    "DT_F_Q1", "DT_F_Q2",
    "DT_G_Q1", "DT_G_Q2",
]

ITEM_IDS_WS1: list[str] = [f"WS1_B{i}" for i in range(1, 12)]
ITEM_IDS_WS3: list[str] = [f"WS3_B{i}" for i in range(1, 9)]
ITEM_IDS_WS4: list[str] = [f"WS4_B{i}" for i in range(1, 6)]
ITEM_IDS_WS5: list[str] = [f"WS5_B{i}" for i in range(1, 26)]
ITEM_IDS_WS6: list[str] = [f"WS6_B{i}" for i in range(1, 14)]
ITEM_IDS_WS7: list[str] = [f"WS7_B{i}" for i in range(1, 8)]
ITEM_IDS_WS10: list[str] = [f"WS10_B{i}" for i in range(1, 9)]

ITEM_IDS_WS11_REFLECTION: list[str] = [f"WS11_B{i}" for i in range(1, 8)]
ITEM_IDS_WS11_COGNITIVE: list[str] = (
    ["WS11_B8a", "WS11_B8b", "WS11_B9"]
    + [f"WS11_Q10_{i}" for i in range(1, 9)]
    + [f"WS11_Q11_{i}" for i in (2, 3, 4)]
    + [f"WS11_Q12_{i}" for i in range(1, 6)]
)
ITEM_IDS_WS11_DESCRIPTIVE: list[str] = (
    [f"WS11_L10_{i}" for i in range(1, 9)]
    + [f"WS11_L11_{i}" for i in range(1, 4)]
    + [f"WS11_L12_{i}" for i in range(1, 6)]
)
ITEM_IDS_WS11: list[str] = (
    ITEM_IDS_WS11_REFLECTION
    + ITEM_IDS_WS11_COGNITIVE
    + ITEM_IDS_WS11_DESCRIPTIVE
)

ITEM_IDS_WS: list[str] = (
    ITEM_IDS_WS1 + ITEM_IDS_WS3 + ITEM_IDS_WS4
    + ITEM_IDS_WS5 + ITEM_IDS_WS6 + ITEM_IDS_WS7 + ITEM_IDS_WS10
)

ALL_ITEM_IDS: list[str] = ITEM_IDS_DT + ITEM_IDS_WS + ITEM_IDS_WS11

PDF_ITEM_IDS: dict[str, list[str]] = {
    "WorksheetDT.pdf": ITEM_IDS_DT,
    "Worksheets1-10.pdf": ITEM_IDS_WS,
    "Worksheet11_ Feedbacks.pdf": ITEM_IDS_WS11,
}

WORKSHEET_ITEM_IDS: dict[str, list[str]] = {
    "WS_DT": ITEM_IDS_DT,
    "WS1": ITEM_IDS_WS1,
    "WS3": ITEM_IDS_WS3,
    "WS4": ITEM_IDS_WS4,
    "WS5": ITEM_IDS_WS5,
    "WS6": ITEM_IDS_WS6,
    "WS7": ITEM_IDS_WS7,
    "WS10": ITEM_IDS_WS10,
    "WS11": ITEM_IDS_WS11,
}

WORKSHEET_PDF_SOURCE: dict[str, str] = {
    "WS_DT": "WorksheetDT.pdf",
    "WS1": "Worksheets1-10.pdf",
    "WS3": "Worksheets1-10.pdf",
    "WS4": "Worksheets1-10.pdf",
    "WS5": "Worksheets1-10.pdf",
    "WS6": "Worksheets1-10.pdf",
    "WS7": "Worksheets1-10.pdf",
    "WS10": "Worksheets1-10.pdf",
    "WS11": "Worksheet11_ Feedbacks.pdf",
}

OCR_OUTPUT_DIR = REPO_ROOT / "ocr_output"
OCR_IMAGES_DIR = OCR_OUTPUT_DIR / "_images"
LAYOUT_ROIS_DIR = REPO_ROOT / "layout_rois"

PDF_PAGES_PER_STUDENT: dict[str, int] = {
    "WorksheetDT.pdf": 4,
    "Worksheets1-10.pdf": 6,
    "Worksheet11_ Feedbacks.pdf": 3,
}

# Fixed page order inside Worksheets1-10.pdf (ProDaBi v4; calibrated on _slot31_check).
# Page 1=WS7, 2=WS10, 3=WS1, 4=WS3, 5=WS4, 6=WS5.
WORKSHEETS_1_10_PAGE_INDEX: dict[str, int] = {
    "WS7": 1,
    "WS10": 2,
    "WS1": 3,
    "WS3": 4,
    "WS4": 5,
    "WS5": 6,
}

# WS6 (draw-your-own tree) is OCR-scored via blanks B1-B13 but the large drawing
# canvas is NOT on the 6-page class bundle in current scans. Use dt_vision_pipeline
# when a supplemental WS6 page image is available (layout manifest or explicit path).
WS6_DRAW_PAGE_INDEX: int | None = None

# Worksheets that benefit from OpenCV RoI isolation before HTR/scoring.
LAYOUT_ISOLATION_WORKSHEETS: frozenset[str] = frozenset({"WS5", "WS10", "WS6"})

WORKSHEET_DESCRIPTIVE_ONLY: dict[str, list[str]] = {
    "WS11": ITEM_IDS_WS11_REFLECTION + ITEM_IDS_WS11_DESCRIPTIVE,
}

# ---------------------------------------------------------------------------
# Scoring item IDs (keys in rubric + mapping + scoring output)
# ---------------------------------------------------------------------------

WORKSHEET_SCORING_ITEM_IDS: dict[str, list[str]] = {
    "WS_DT": ITEM_IDS_DT,
    "WS11": ITEM_IDS_WS11_COGNITIVE,
}


def rubric_bundle_path(worksheet: str) -> Path | None:
    """Return worksheets/<worksheet>/rubric.json when the Phase 2 bundle exists."""
    path = WORKSHEETS_DIR / worksheet / "rubric.json"
    return path if path.exists() else None


@lru_cache(maxsize=None)
def load_rubric(worksheet: str) -> dict[str, Any]:
    """Load worksheet bundle rubric, falling back to legacy rubrics/<worksheet>_rubric.json."""
    bundle = rubric_bundle_path(worksheet)
    if bundle is not None:
        return json.loads(bundle.read_text(encoding="utf-8"))
    path = RUBRICS_DIR / f"{worksheet}_rubric.json"
    if not path.exists():
        raise FileNotFoundError(f"Rubric not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_framework() -> dict[str, Any]:
    """Load mappings/AICFT_assessment_framework.json (performance-based competency framework)."""
    path = MAPPINGS_DIR / "AICFT_assessment_framework.json"
    if not path.exists():
        raise FileNotFoundError(f"Framework not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_mapping(worksheet: str) -> dict[str, Any]:
    """Load mappings/<worksheet>_AICFT_mapping.json."""
    path = MAPPINGS_DIR / f"{worksheet}_AICFT_mapping.json"
    if not path.exists():
        raise FileNotFoundError(f"Mapping not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def item_competencies(mapping: dict[str, Any], item_id: str) -> list[dict[str, Any]]:
    """Return competency priors for a worksheet item (schema 2.0 or legacy 1.x)."""
    raw = mapping.get("items", {}).get(item_id)
    if raw is None:
        return []
    if isinstance(raw, dict) and "competencies" in raw:
        return list(raw["competencies"])
    if isinstance(raw, list):
        out: list[dict[str, Any]] = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            out.append({
                "lo": entry.get("lo") or entry.get("LO", ""),
                "strength": entry.get("strength") or entry.get("weight", "moderate"),
                "evidence_type": entry.get("evidence_type", "direct"),
                "expected_level": entry.get("expected_level", "Deepen"),
                "rationale": entry.get("rationale", ""),
                "role": entry.get("role", "primary"),
                "portfolio_weight": entry.get("portfolio_weight", "full"),
            })
        return out
    return []


def competency_strength_ceiling(comp: dict[str, Any]) -> str:
    """Maximum observable evidence strength for a mapped competency."""
    return str(comp.get("strength") or comp.get("weight") or "moderate")


def framework_item_index(framework: dict[str, Any] | None = None) -> dict[tuple[str, str], list[dict[str, Any]]]:
    """Map (worksheet, item) → competency priors from assessment framework."""
    fw = framework or load_framework()
    index: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for entry in fw.get("items", []):
        key = (entry["worksheet"], entry["item"])
        index[key] = entry.get("competencies", [])
    return index


def competency_counts_toward_portfolio_peak(comp_prior: dict[str, Any]) -> bool:
    """Whether a mapped competency should affect LO peak_strength in portfolio rollup."""
    weight = comp_prior.get("portfolio_weight", "full")
    et = comp_prior.get("evidence_type", "direct")
    if weight == "baseline" or et == "prior_belief":
        return False
    if weight == "diagnostic" and et == "reflective":
        return False
    return True


def scoring_item_ids(worksheet: str) -> list[str]:
    """Return ordered scoring item keys for a worksheet."""
    if worksheet in WORKSHEET_SCORING_ITEM_IDS:
        return list(WORKSHEET_SCORING_ITEM_IDS[worksheet])
    rubric = load_rubric(worksheet)
    return list(rubric["items"].keys())


def validate_rubric_v3(rubric: dict[str, Any], source: str = "") -> list[str]:
    """Return a list of Schema 3.0 validation errors (empty if valid)."""
    prefix = f"{source}: " if source else ""
    errors: list[str] = []

    if rubric.get("schema_version") != RUBRIC_SCHEMA_VERSION:
        errors.append(f"{prefix}schema_version must be {RUBRIC_SCHEMA_VERSION!r}")

    worksheet = rubric.get("worksheet")
    if not worksheet:
        errors.append(f"{prefix}missing worksheet")

    items = rubric.get("items")
    if not isinstance(items, dict) or not items:
        errors.append(f"{prefix}items must be a non-empty object")
        return errors

    for item_id, item in items.items():
        if not isinstance(item, dict):
            errors.append(f"{prefix}{item_id}: item must be an object")
            continue
        if "max_score" not in item:
            errors.append(f"{prefix}{item_id}: missing max_score")

        legacy = RUBRIC_LEGACY_KEYWORD_FIELDS & item.keys()
        if legacy:
            allowed = legacy - {"accepted_forms"}
            if item.get("check") == "formula" and legacy == {"accepted_forms"}:
                allowed = set()
            if allowed:
                errors.append(
                    f"{prefix}{item_id}: legacy keyword fields {sorted(allowed)} "
                    "(use components[].idea instead)"
                )

        check = item.get("check")
        evaluation = item.get("evaluation")
        components = item.get("components")

        is_deterministic = (
            check in RUBRIC_DETERMINISTIC_CHECKS
            or evaluation in RUBRIC_DETERMINISTIC_EVALUATIONS
            or item.get("correct_answer") is not None
            or item.get("answer") is not None and check is not None
        )

        if not is_deterministic and not components:
            errors.append(
                f"{prefix}{item_id}: semantic item requires components[] "
                f"(evaluation={evaluation!r}, check={check!r})"
            )

        if components:
            for i, comp in enumerate(components):
                if not isinstance(comp, dict):
                    errors.append(f"{prefix}{item_id}: components[{i}] must be an object")
                    continue
                if not comp.get("id"):
                    errors.append(f"{prefix}{item_id}: components[{i}] missing id")
                if not comp.get("idea"):
                    errors.append(f"{prefix}{item_id}: components[{i}] missing idea")

    return errors


def validate_all_rubrics() -> list[str]:
    """Validate worksheet bundle rubrics and legacy rubrics/*_rubric.json files."""
    errors: list[str] = []
    seen: set[str] = set()
    if WORKSHEETS_DIR.is_dir():
        for bundle in sorted(WORKSHEETS_DIR.glob("WS*/rubric.json")):
            rubric = json.loads(bundle.read_text(encoding="utf-8"))
            ws = rubric.get("worksheet", bundle.parent.name)
            seen.add(ws)
            if rubric.get("curriculum_status") == "not_deployed":
                continue
            errors.extend(validate_rubric_v3(rubric, str(bundle.relative_to(REPO_ROOT))))
    for path in sorted(RUBRICS_DIR.glob("*_rubric.json")):
        rubric = json.loads(path.read_text(encoding="utf-8"))
        ws = rubric.get("worksheet", path.stem.replace("_rubric", ""))
        if ws in seen:
            continue
        errors.extend(validate_rubric_v3(rubric, path.name))
    return errors


def rubric_item(worksheet: str, item_id: str) -> dict[str, Any]:
    """Return one rubric item config."""
    items = load_rubric(worksheet)["items"]
    if item_id not in items:
        raise KeyError(f"No rubric item {item_id!r} in {worksheet}")
    return items[item_id]


def rubric_to_assessor_criteria(item_id: str, item: dict[str, Any]) -> dict[str, Any]:
    """
    Convert a rubric JSON item into worksheet_assessor prompt criteria.
    Returns dict with prompt_description, full/partial/zero_credit_criteria.
    """
    parts: list[str] = []
    evaluation = item.get("evaluation", "semantic")
    if item.get("statement"):
        parts.append(f"Statement: {item['statement']}")
    if item.get("note"):
        parts.append(item["note"])
    if item.get("example_answer"):
        parts.append(f"Example answer: {item['example_answer']}")

    full: list[str] = []
    partial: list[str] = []
    zero: list[str] = ["Blank or not attempted"]

    if evaluation in ("true_false",):
        full.append(f"Answer matches correct: {item.get('correct_answer')}")
        zero.append(f"Answer is {('Doğru' if item.get('correct_answer') == 'Yanlış' else 'Yanlış')}")

    elif evaluation in ("ordering_step",):
        full.append(f"Step position is {item.get('correct_answer')}")
        zero.append("Wrong step position")

    elif evaluation in ("multiselect_subitem",):
        if item.get("correct"):
            full.append("Student marks/selects this option (should be checked)")
            zero.append("Student leaves unchecked or marks incorrectly")
        else:
            full.append("Student does not select this option (should be unchecked)")
            zero.append("Student incorrectly selects this option")

    elif evaluation in ("classification",):
        if item.get("components"):
            need = item.get("need", 1)
            partial_on = item.get("partial_on", 0)
            for c in item["components"]:
                if c.get("required", True):
                    full.append(f"{c.get('id', 'label')}: {c.get('idea', '')}")
            if partial_on:
                partial.append(f"Partial if {partial_on} classification idea present")
        else:
            full.append("Correct classification label per rubric context")
        zero.append("Wrong classification")

    elif check in RUBRIC_DETERMINISTIC_CHECKS or evaluation in ("feature_name", "threshold", "leaf_labels", "branch_labels"):
        if item.get("components"):
            need = item.get("need", len(item["components"]))
            partial_on = item.get("partial_on", max(need - 1, 1))
            required = [c for c in item["components"] if c.get("required", True)]
            full.append(f"Includes {need} of {len(required)} required ideas:")
            for c in required:
                full.append(f"  - {c.get('id', 'component')}: {c.get('idea', '')}")
            partial.append(f"Includes {partial_on} of {need} required ideas")
            if item.get("partial_credit_rule"):
                partial.append(f"Partial rule: {item['partial_credit_rule']}")
        if item.get("check"):
            full.append(f"Passes deterministic check: {item['check']}")
        if item.get("fields"):
            full.append(f"Records fields: {', '.join(item['fields'])}")
        if item.get("formula_reference"):
            full.append(f"Formula: {item['formula_reference']}")
        if not full:
            partial.append("Partial structural or numeric match")
            zero.append("Missing or inconsistent values")

    elif evaluation in ("formula",) or item.get("check") == "formula":
        if item.get("answer"):
            full.append(f"Correct formula: {item['answer']}")
        if item.get("accepted_forms"):
            full.append(f"Accepted forms: {', '.join(item['accepted_forms'])}")
        partial.append("Related but incorrect formula")
        zero.append("Blank or completely wrong formula")

    elif item.get("components"):
        need = item.get("need", len(item["components"]))
        partial_on = item.get("partial_on", max(need - 1, 1))
        required = [c for c in item["components"] if c.get("required", True)]
        full.append(f"Includes {need} of {len(required)} required ideas:")
        for c in required:
            full.append(f"  - {c.get('id', 'component')}: {c.get('idea', '')}")
        partial.append(f"Includes {partial_on} of {need} required ideas")
        zero.append("No required ideas present")

    elif check or item.get("answer") is not None:
        if item.get("check"):
            full.append(f"Passes check: {check}")
        if item.get("answer") is not None:
            full.append(f"Expected answer: {item['answer']}")
        partial.append("Partial numeric or structural match")
        zero.append("Incorrect or missing value")

    else:
        full.append("Conceptually correct per rubric example and worksheet context")
        partial.append("Partial conceptual match")

    return {
        "prompt_description": f"Item {item_id} ({evaluation}). " + " ".join(parts),
        "full_credit_criteria": full,
        "partial_credit_criteria": partial,
        "zero_credit_criteria": zero,
    }


def get_assessor_rubric(item_id: str, worksheet: str | None = None) -> dict[str, Any]:
    """
    Resolve assessor rubric criteria for an item_id.
    worksheet may be inferred from item_id prefix when omitted.
    """
    ws = worksheet or _worksheet_from_item_id(item_id)
    return rubric_to_assessor_criteria(item_id, rubric_item(ws, item_id))


def _worksheet_from_item_id(item_id: str) -> str:
    if item_id.startswith("DT_"):
        return "WS_DT"
    if item_id.startswith("WS"):
        return item_id.split("_")[0]
    raise KeyError(f"Cannot infer worksheet from item_id: {item_id!r}")


def normalize_worksheet_id(worksheet_id: str) -> str:
    """Accept 'DT' or 'WS_DT' and return canonical worksheet label."""
    if worksheet_id in WORKSHEET_ITEM_IDS:
        return worksheet_id
    if worksheet_id == "DT":
        return "WS_DT"
    raise KeyError(f"Unknown worksheet_id: {worksheet_id!r}")


def pdf_to_images_stem(pdf_name: str) -> str:
    """Match ocr_pipeline.save_page_images folder naming."""
    return pdf_name.replace(" ", "_").replace(".pdf", "")


def slot_dir_for_student(student_key: str, pdf_name: str = "Worksheets1-10.pdf") -> Path | None:
    """
    Resolve dry_run image folder for a pseudonym or slot label.

    Checks, in order:
      1. ocr_output/_images/{pdf_stem}/{student_key}/page_*.jpg
      2. Marker file .{student_key}_{pdf_stem} -> slot_NN under pdf_stem
      3. ocr_output/{student_key}/_images/page_*.jpg
      4. Calibration folder ocr_output/_images/_slot31_check (Sample_Student)
    """
    pdf_stem = pdf_to_images_stem(pdf_name)
    base = OCR_IMAGES_DIR / pdf_stem

    direct = base / student_key
    if direct.is_dir() and any(direct.glob("page_*.jpg")):
        return direct

    marker = OCR_OUTPUT_DIR / f".{student_key}_{pdf_stem}"
    if marker.exists():
        try:
            slot_num = int(marker.read_text(encoding="utf-8").strip())
            slot_dir = base / f"slot_{slot_num:02d}"
            if slot_dir.is_dir():
                return slot_dir
        except ValueError:
            pass

    if student_key.startswith("slot_"):
        slot_dir = base / student_key
        if slot_dir.is_dir():
            return slot_dir

    student_images = OCR_OUTPUT_DIR / student_key / "_images"
    if student_images.is_dir() and any(student_images.glob("page_*.jpg")):
        return student_images

    if student_key == "Sample_Student":
        cal = OCR_IMAGES_DIR / "_slot31_check"
        if cal.is_dir() and any(cal.glob("page_*.jpg")):
            return cal

    return None


def worksheet_page_image(student_key: str, worksheet: str) -> Path | None:
    """Return the scanned page image path for a worksheet, if known and on disk."""
    ws = worksheet.upper()
    pdf = WORKSHEET_PDF_SOURCE.get(ws)
    if not pdf:
        return None

    if pdf == "Worksheets1-10.pdf":
        page_idx = WORKSHEETS_1_10_PAGE_INDEX.get(ws)
        if page_idx is None:
            return None
        slot_dir = slot_dir_for_student(student_key, pdf)
        if slot_dir is None:
            return None
        candidate = slot_dir / f"page_{page_idx}.jpg"
        return candidate if candidate.exists() else None

    return None


def layout_manifest_path(student_key: str, worksheet: str) -> Path:
    return LAYOUT_ROIS_DIR / student_key / f"{worksheet.upper()}_layout.json"
