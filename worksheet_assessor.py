"""
worksheet_assessor.py
Phase 1 — Worksheet assessment agent using few-shot prompting.

Covers:
  - Worksheet DT (WS_DT, Sections A-G)
  - ProDaBi worksheets: WS1, WS3, WS4, WS5, WS6, WS7, WS10, WS11

Rubrics and item IDs are loaded from pipeline_schema.py (rubrics/*.json).

Assessment logic:
  - Binary correct / partial / wrong per item
  - LLM scores open-ended items using rubrics and few-shot examples
  - LLM never computes numerical fields; arithmetic is checked in Python
  - Output is a WorksheetAssessment Pydantic object per student
"""

from __future__ import annotations

import base64
import json
import re
from io import BytesIO
from pathlib import Path
from typing import Optional, Union

import anthropic
from PIL import Image
from pydantic import BaseModel, Field, field_validator, model_validator

from pipeline_schema import (
    get_assessor_rubric,
    is_interpretive_rubric_item,
    load_rubric,
    normalize_worksheet_id,
    rubric_item,
    scoring_item_ids,
)
from rubric_deterministic import score_any_of_tokens, score_unordered_token_set

# ---------------------------------------------------------------------------
# Pydantic output schema
# ---------------------------------------------------------------------------

CREDIT_LEVELS = ("full", "partial", "zero", "not_attempted")


class ItemScore(BaseModel):
    item_id: str  # e.g. "DT_A_Q2", "WS3_T1"
    credit: str  # one of CREDIT_LEVELS
    llm_rationale: str = Field(min_length=10)
    evidence_quote: str  # verbatim from student response, min 1 char
    flag: Optional[str] = None  # e.g. "numeric_mismatch", "contradicts_log"

    @model_validator(mode="after")
    def credit_must_be_valid(self) -> "ItemScore":
        if self.credit not in CREDIT_LEVELS:
            raise ValueError(f"credit must be one of {CREDIT_LEVELS}, got {self.credit!r}")
        return self


class WorksheetAssessment(BaseModel):
    candidate_id: str
    worksheet_id: str  # e.g. "DT", "WS1", "WS11"
    item_scores: list[ItemScore] = Field(min_length=1)
    overall_worksheet_credit: str  # "full" / "partial" / "zero" / "not_attempted"
    analyst_notes: Optional[str] = None

    @model_validator(mode="after")
    def overall_credit_is_valid(self) -> "WorksheetAssessment":
        if self.overall_worksheet_credit not in CREDIT_LEVELS:
            raise ValueError(f"overall_worksheet_credit invalid: {self.overall_worksheet_credit!r}")
        return self


# ---------------------------------------------------------------------------
# Decision tree structure extraction schema
# ---------------------------------------------------------------------------

TARGET_CLASSES = frozenset({"Recommendable", "Not Recommendable"})

KNOWN_FEATURES = frozenset({
    "Energy", "Fat", "Salt", "Protein", "Saturated Fat",
    "Carbohydrates", "Sugar", "Calories", "Sodium",
    "Fibre", "Price", "Taste Score",
})

# Bilingual / misspelling -> canonical English feature map (lowercase keys)
FEATURE_TR_TO_EN: dict[str, str] = {
    "enerji": "Energy",       "enerji kcal": "Energy",
    "yag": "Fat",             "yağ": "Fat",
    "tuz": "Salt",
    "protein": "Protein",
    "doymus yag": "Saturated Fat",  "doymuş yağ": "Saturated Fat",
    "karbonhidrat": "Carbohydrates", "karbonidrat": "Carbohydrates",
    "seker": "Sugar",         "şeker": "Sugar",
    "kalori": "Calories",
    "sodyum": "Sodium",
    # common abbreviations / misspellings
    "sgr": "Sugar",           "cal": "Calories",  "sod": "Sodium",
    "egnergy": "Energy",      "treshold": "Threshold",
}

LEGIBILITY_LEVELS = ("Low", "Medium", "High")
RESULT_NODE_CLASSES = frozenset(TARGET_CLASSES | {"Next Split Node"})


def _coerce_threshold(v: object) -> Optional[float]:
    """Convert threshold to float, handling Turkish comma decimals."""
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        normalized = str(v).replace(",", ".")
        try:
            return float(normalized)
        except ValueError:
            return None


def _normalize_target(v: object) -> Optional[str]:
    """Map raw target label to canonical form, case-insensitively."""
    if v is None:
        return None
    s = str(v).strip()
    for canonical in TARGET_CLASSES:
        if s.lower() == canonical.lower():
            return canonical
    return s


_RESULT_TR_ALTS: dict[str, str] = {
    "onerilir": "Recommendable",
    "önerilir": "Recommendable",
    "tavsiye edilebilir": "Recommendable",
    "tavsiye edilir": "Recommendable",
    "evet": "Recommendable",
    "onerilmez": "Not Recommendable",
    "önerilmez": "Not Recommendable",
    "tavsiye edilemez": "Not Recommendable",
    "hayir": "Not Recommendable",
    "hayır": "Not Recommendable",
}


def _normalize_result_node(v: object) -> Optional[str]:
    """Map raw result_node to a canonical value, including Turkish alternates."""
    if v is None:
        return None
    s = str(v).strip()
    sl = s.lower()
    for canonical in RESULT_NODE_CLASSES:
        if sl == canonical.lower():
            return canonical
    if sl in _RESULT_TR_ALTS:
        return _RESULT_TR_ALTS[sl]
    return s


def _normalize_path_direction(v: object) -> Optional[str]:
    """Normalize branch labels to 'True/Yes' or 'False/No'."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in {"true", "yes", "evet", "doğru", "dogru", "true/yes"}:
        return "True/Yes"
    if s in {"false", "no", "hayır", "hayir", "yanlış", "yanlis", "false/no"}:
        return "False/No"
    return None


# ---------------------------------------------------------------------------
# Pydantic models for decision tree extraction
# ---------------------------------------------------------------------------

class DataQuality(BaseModel):
    illegible_fields_found: bool = Field(
        description="True if any field was unreadable and set to null.",
    )
    bilingual_mapping_used: list[str] = Field(
        default_factory=list,
        description=(
            "Bilingual / misspelling corrections applied, "
            "e.g. 'karbonidrat -> Karbonhidrat', 'Sgr -> Sugar'."
        ),
    )


class RootNode(BaseModel):
    node_type: str = Field(
        default="Root",
        description="Node type label — always 'Root' for the root node.",
    )
    variable_feature: Optional[str] = Field(
        None,
        description="Extracted feature from KNOWN_FEATURES. Null if illegible.",
    )
    threshold_value: Optional[float] = Field(
        None,
        description="Numeric threshold at the root split. Null if absent or illegible.",
    )

    @field_validator("threshold_value", mode="before")
    @classmethod
    def coerce_threshold(cls, v: object) -> Optional[float]:
        return _coerce_threshold(v)


class SplitMetrics(BaseModel):
    mcr_rate: Optional[str] = Field(
        None,
        description="Misclassification rate annotated here, e.g. '3/12', '25%', '0.25'.",
    )
    accuracy_dogruluk: Optional[str] = Field(
        None,
        description="Accuracy metric if annotated, e.g. '0.75' or '75%'.",
    )
    impurity_info: Optional[str] = Field(
        None,
        description="Gini, Entropy, or Information Gain value if annotated.",
    )


class DecisionTreeSplit(BaseModel):
    level: int = Field(ge=1, description="Tree depth level: 1 = direct child of root.")
    parent_feature: Optional[str] = Field(
        None,
        description="The feature whose split produced this branch.",
    )
    path_direction: Optional[str] = Field(
        None,
        description="Branch label as written: 'True/Yes' or 'False/No'. Null if unlabelled.",
    )
    condition: Optional[str] = Field(
        None,
        description="Full condition string, e.g. 'Protein > 10'. Null if illegible.",
    )
    result_node: Optional[str] = Field(
        None,
        description=(
            "'Recommendable', 'Not Recommendable', or next split feature name. "
            "Null if illegible."
        ),
    )
    metrics: SplitMetrics = Field(
        default_factory=SplitMetrics,
        description="Performance metrics annotated on this branch.",
    )

    @field_validator("path_direction", mode="before")
    @classmethod
    def normalize_direction(cls, v: object) -> Optional[str]:
        return _normalize_path_direction(v)

    @field_validator("result_node", mode="before")
    @classmethod
    def normalize_result(cls, v: object) -> Optional[str]:
        return _normalize_result_node(v)


class TreeExtraction(BaseModel):
    root_node: RootNode
    splits: list[DecisionTreeSplit] = Field(
        default_factory=list,
        description="All splits ordered top-to-bottom, left branch first per level.",
    )

    @model_validator(mode="after")
    def validate_topology(self) -> "TreeExtraction":
        """Catch common structural errors the model might produce."""
        errors: list[str] = []

        # Level-1 splits must reference the root feature as parent
        root_feat = self.root_node.variable_feature
        for s in self.splits:
            if s.level == 1 and root_feat and s.parent_feature:
                if s.parent_feature.lower() != root_feat.lower():
                    errors.append(
                        f"level-1 split has parent_feature={s.parent_feature!r} "
                        f"but root is {root_feat!r}"
                    )

        # Every split whose result_node == "Next Split Node" must have
        # at least one level+1 split with the same parent_feature
        for s in self.splits:
            if s.result_node == "Next Split Node":
                deeper = [
                    x for x in self.splits
                    if x.level == s.level + 1
                    and (x.parent_feature or "").lower()
                    == (s.condition or "").split()[0].lower()
                ]
                if not deeper and s.condition:
                    # soft warning only — don't raise, just note it
                    pass

        if errors:
            raise ValueError("; ".join(errors))
        return self


class DecisionTreeExtraction(BaseModel):
    student_id: Optional[str] = Field(
        None,
        description="Student ID or pseudonym from worksheet header. Null if absent.",
    )
    data_quality: DataQuality = Field(
        description="Illegibility flag and bilingual correction audit trail.",
    )
    tree_extraction: TreeExtraction = Field(
        description="Root node and all splits with per-branch metrics.",
    )


# ---------------------------------------------------------------------------
# Post-extraction validation helpers
# ---------------------------------------------------------------------------

# Plausible threshold ranges per feature (min, max).
# Values outside these bounds are likely digit misreads.
_THRESHOLD_PLAUSIBLE_RANGES: dict[str, tuple[float, float]] = {
    "Energy":         (50.0,  900.0),
    "Calories":       (50.0,  900.0),
    "Fat":            (0.0,   80.0),
    "Saturated Fat":  (0.0,   40.0),
    "Carbohydrates":  (0.0,   120.0),
    "Sugar":          (0.0,   80.0),
    "Protein":        (0.0,   50.0),
    "Salt":           (0.0,   10.0),
    "Sodium":         (0.0,   3000.0),
    "Fibre":          (0.0,   30.0),
    "Price":          (0.0,   50.0),
    "Taste Score":    (0.0,   10.0),
}


def validate_extraction(ext: DecisionTreeExtraction) -> list[str]:
    """Return a list of structural / plausibility warnings (not errors).

    Does not modify the extraction — callers decide how to handle warnings.
    Typical use: attach to a pipeline log or surface in a review UI.
    """
    warnings: list[str] = []
    te = ext.tree_extraction
    root = te.root_node

    # 1. Root feature not in known dictionary
    if root.variable_feature and root.variable_feature not in KNOWN_FEATURES:
        warnings.append(
            f"root feature '{root.variable_feature}' not in KNOWN_FEATURES"
        )

    # 2. Threshold plausibility
    feat = root.variable_feature
    thresh = root.threshold_value
    if feat and thresh is not None and feat in _THRESHOLD_PLAUSIBLE_RANGES:
        lo, hi = _THRESHOLD_PLAUSIBLE_RANGES[feat]
        if not (lo <= thresh <= hi):
            warnings.append(
                f"root threshold {thresh} is outside plausible range [{lo}, {hi}] "
                f"for feature '{feat}' — possible digit misread"
            )

    # 3. Level-1 splits: check count (expected exactly 2 for binary tree)
    level1 = [s for s in te.splits if s.level == 1]
    if len(level1) == 1:
        warnings.append("only 1 level-1 split found — expected 2 for a binary tree")
    if len(level1) > 2:
        warnings.append(f"{len(level1)} level-1 splits found — expected 2 for a binary tree")

    # 4. Both branches have same path_direction
    directions = [s.path_direction for s in level1 if s.path_direction]
    if len(directions) == 2 and directions[0] == directions[1]:
        warnings.append(
            f"both level-1 splits have path_direction='{directions[0]}' — likely extraction error"
        )

    # 5. result_node = "Next Split Node" but no deeper split follows
    for s in te.splits:
        if s.result_node == "Next Split Node":
            next_level = s.level + 1
            has_deeper = any(x.level == next_level for x in te.splits)
            if not has_deeper:
                warnings.append(
                    f"split '{s.condition}' says 'Next Split Node' "
                    f"but no level-{next_level} splits found"
                )

    # 6. Leaf result in a non-terminal position (result_node is a leaf label
    #    but another split claims the same parent_feature at a deeper level)
    leaf_labels = TARGET_CLASSES
    for s in te.splits:
        if s.result_node in leaf_labels:
            spurious = [
                x for x in te.splits
                if x.level > s.level and x.parent_feature == s.parent_feature
            ]
            if spurious:
                warnings.append(
                    f"split '{s.condition}' terminates with '{s.result_node}' "
                    f"but deeper splits also reference parent_feature='{s.parent_feature}'"
                )

    # 7. illegible_fields_found is False but there are null result_nodes
    null_results = [s for s in te.splits if s.result_node is None]
    if null_results and not ext.data_quality.illegible_fields_found:
        warnings.append(
            f"{len(null_results)} split(s) have result_node=null "
            "but illegible_fields_found=False — flag should be True"
        )

    # 8. Prompt injection attempt in student_id or bilingual_mapping_used
    injection_keywords = {"ignore", "system", "forget", "override", "instructions"}
    sid = (ext.student_id or "").lower()
    if any(kw in sid for kw in injection_keywords):
        warnings.append(f"possible prompt injection in student_id: '{ext.student_id}'")

    for entry in ext.data_quality.bilingual_mapping_used:
        if any(kw in entry.lower() for kw in injection_keywords):
            warnings.append(f"possible prompt injection in bilingual_mapping_used: '{entry}'")

    return warnings


# ---------------------------------------------------------------------------
# Decision tree extraction prompt + function
# ---------------------------------------------------------------------------

_DT_EXTRACTION_SYSTEM = """ROLE: Elite Handwritten Text Recognition (HTR) and Educational Data Mining Specialist.
TASK: Digitize high school students' handwritten "Decision Trees for Classification" worksheets
with >95% accuracy on core domain terms. Students write in mixed Turkish and English.
You are a strict bilingual fuzzy-matching engine — never read characters in isolation.

════════════════════════════════════════════════
SECTION 1 — BILINGUAL DOMAIN DICTIONARY
════════════════════════════════════════════════
You are FORBIDDEN from generating any term outside this dictionary for key fields.
If a handwritten word cannot be matched to any entry, output null.

── Nutritional Features (Oznitelikler / Bagimsiz Degiskenler) ──
  Energy        <->  Enerji, Enerji kcal, Kalori
  Fat           <->  Yag
  Saturated Fat <->  Doymus Yag, Doy. Yag
  Carbohydrates <->  Karbonhidrat
  Sugar         <->  Seker
  Protein       <->  Protein
  Salt          <->  Tuz
  Sodium        <->  Sodyum
  Fibre         <->  Lif
  Calories      <->  Kalori (when used as a column name)
  Price         <->  Fiyat
  Taste Score   <->  Tat Puani

  Autocorrect these frequent misspellings and abbreviations:
    "karbonidrat" -> Carbohydrates  |  "egnergy"  -> Energy
    "treshold"    -> (threshold)    |  "Sgr"       -> Sugar
    "Cal"         -> Calories       |  "Sod"       -> Sodium
    "doymus yag"  -> Saturated Fat  |  "kok dugum" -> Root Node

── Tree Structure Terms (Agac Yapisi) ──
  Root Node          <->  Kok Dugum
  Decision Node      <->  Karar Dugumu, Ic Dugum, Internal Node
  Leaf Node          <->  Yaprak Dugum, Terminal Dugum, Terminal Node
  Branch             <->  Dal
  Split / Partition  <->  Bolunme / Ayirma
  Condition / Rule   <->  Kosul / Kural / Test
  True / Yes         <->  Dogru / Evet
  False / No         <->  Yanlis / Hayir

── Target Classifications (Yaprak Etiketleri — ONLY THESE TWO) ──
  "Recommendable"      <->  Onerilir, Tavsiye Edilebilir, Evet, Tavsiye Edilir
  "Not Recommendable"  <->  Onerilmez, Tavsiye Edilemez, Hayir

  If a branch leads to a deeper split node: result_node = "Next Split Node"

── Metrics (Degerlendirme Metrikleri) ──
  mcr_rate          <- MCR, Misclassification Rate, Hatali Siniflandirma Orani, Hata Orani
  accuracy_dogruluk <- Accuracy, Dogruluk, Acc
  impurity_info     <- Gini, Entropy, Information Gain, Bilgi Kazanci, Safsizlik
  Valid formats: fraction "3/12", percentage "25%", decimal "0.25"

════════════════════════════════════════════════
SECTION 2 — CHAIN-OF-THOUGHT PROCESSING PIPELINE
════════════════════════════════════════════════
Apply ALL five steps internally before producing any output:

STEP 1 — ISOLATE & IDENTIFY HIERARCHY
  Map the full visual tree structure first. Do not read any text yet.
  Identify: header region (student ID), root node box at top,
  internal split nodes, branch lines, and terminal leaf boxes.
  Note the tree depth (how many levels of splits exist).

STEP 2 — BILINGUAL FUZZY MATCH
  Read each text region in the context of its structural role:
    A term at a LEAF position     -> must resolve to a target classification.
    A term at a SPLIT NODE        -> must resolve to a feature name.
    A number next to feature name -> threshold value.
    A fraction/percentage near a node box -> a metric.
  Use the dictionary to map ambiguous strokes. If the closest dictionary
  match is visually plausible (>60% character overlap), use it and log the
  correction. If nothing matches, output null.

STEP 3 — PATH DIRECTION TRACKING
  For each branch line, check whether the student labeled it:
    True / Yes / Dogru / Evet  -> path_direction = "True/Yes"
    False / No / Yanlis / Hayir -> path_direction = "False/No"
    Unlabeled                   -> path_direction = null
  Record parent_feature for every split (the feature at the node above it).

STEP 4 — NUMERICAL EXTRACTION & DISAMBIGUATION
  a) Digit disambiguation:
       1 = single narrow vertical stroke, no serifs
       7 = vertical stroke with HORIZONTAL crossbar at top
       0 = tall oval, closed loop
       O = rounder, appears inside alphabetic words only
  b) Decimal separator: comma is valid in Turkish ("10,5" -> 10.5)
  c) Threshold vs metric disambiguation:
       A number directly after a feature name or inside a split node box
       -> threshold_value (integer or decimal, e.g. 8, 8.0, 10.5)
       A fraction, percentage, or decimal preceded by "MCR", "Hata", "Acc",
       "Dogruluk", or written below/beside a node box
       -> metric field (e.g. "3/12", "25%", "0.25")
  d) Single-digit threshold rule:
       If a number near a feature appears ambiguous between integer and decimal
       (e.g. "8" vs "0.8"), prefer the integer interpretation UNLESS the
       feature's known value range makes the integer implausible.
       Log the ambiguity in bilingual_mapping_used.

STEP 5 — CROSSED-OUT / BLANK / ILLEGIBLE HANDLING
  Completely blank field                               -> null
  Field crossed out with a single line (strikethrough) -> null
    Log: "crossed_out: <field_name>"
  Field written, crossed out, then rewritten           -> use REWRITTEN value
    Log: "revised: <field_name> old=<old_value> new=<new_value>"
  Field smudged but dictionary match >60% confidence   -> use match, log correction
  Field with <60% confidence and no plausible match    -> null
    Set illegible_fields_found = true

════════════════════════════════════════════════
SECTION 3 — OUTPUT RULES
════════════════════════════════════════════════
Return ONLY a valid raw JSON object.
No markdown code fences (no ```json).
No introductory text, no trailing explanation.
Include ALL split levels (level 1, 2, 3...) in the splits array.
For every split, always include parent_feature so tree topology can be reconstructed.
If ANY field was set to null, set data_quality.illegible_fields_found = true."""

_DT_EXTRACTION_USER_TEMPLATE = """Extract the complete decision tree structure from this handwritten worksheet image.

WHAT TO LOOK FOR:
  Student ID or pseudonym    -- usually top-left or top-right corner.
  Root node box              -- topmost split: feature name + threshold value.
  Branch labels              -- True/Yes or False/No (or Turkish) on each line.
  Split nodes                -- internal boxes at deeper levels: feature + threshold.
  Leaf boxes                 -- terminal labels: "Recommendable" or "Not Recommendable".
  Metric annotations         -- fractions, percentages, or decimals near any node or branch.

════════════════════════════════════════════════
FEW-SHOT EXAMPLES (study these before extracting)
════════════════════════════════════════════════

EXAMPLE A: simple 1-level tree
Handwriting: "Yag < 8  ->(Evet)->  Onerilir [MCR: 2/10]   ->(Hayir)->  Onerilmez"

{"student_id":null,"data_quality":{"illegible_fields_found":false,"bilingual_mapping_used":["Yag -> Fat","Onerilir -> Recommendable","Onerilmez -> Not Recommendable"]},"tree_extraction":{"root_node":{"node_type":"Root","variable_feature":"Fat","threshold_value":8.0},"splits":[{"level":1,"parent_feature":"Fat","path_direction":"True/Yes","condition":"Fat < 8.0","result_node":"Recommendable","metrics":{"mcr_rate":"2/10","accuracy_dogruluk":null,"impurity_info":null}},{"level":1,"parent_feature":"Fat","path_direction":"False/No","condition":"Fat >= 8.0","result_node":"Not Recommendable","metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}}]}}

EXAMPLE B: 2-level tree with deeper split
Handwriting:
  Root: "Seker > 10"
    Evet -> "Onerilmez" [Hata: 3/12]
    Hayir -> "Protein > 7"
               Dogru  -> "Onerilir"
               Yanlis -> "Onerilmez" [Acc: 0.75]

{"student_id":null,"data_quality":{"illegible_fields_found":false,"bilingual_mapping_used":["Seker -> Sugar","Onerilir -> Recommendable","Onerilmez -> Not Recommendable"]},"tree_extraction":{"root_node":{"node_type":"Root","variable_feature":"Sugar","threshold_value":10.0},"splits":[{"level":1,"parent_feature":"Sugar","path_direction":"True/Yes","condition":"Sugar > 10","result_node":"Not Recommendable","metrics":{"mcr_rate":"3/12","accuracy_dogruluk":null,"impurity_info":null}},{"level":1,"parent_feature":"Sugar","path_direction":"False/No","condition":"Sugar <= 10","result_node":"Next Split Node","metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}},{"level":2,"parent_feature":"Protein","path_direction":"True/Yes","condition":"Protein > 7","result_node":"Recommendable","metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}},{"level":2,"parent_feature":"Protein","path_direction":"False/No","condition":"Protein <= 7","result_node":"Not Recommendable","metrics":{"mcr_rate":null,"accuracy_dogruluk":"0.75","impurity_info":null}}]}}

EXAMPLE C: crossed-out threshold rewritten + misspelling
Handwriting: "karbonidrat > ~~5~~ 8  ->(Evet)-> Onerilir"
(threshold 5 is crossed out, rewritten as 8)

{"student_id":null,"data_quality":{"illegible_fields_found":false,"bilingual_mapping_used":["karbonidrat -> Carbohydrates","revised: threshold_value old=5 new=8","Onerilir -> Recommendable"]},"tree_extraction":{"root_node":{"node_type":"Root","variable_feature":"Carbohydrates","threshold_value":8.0},"splits":[{"level":1,"parent_feature":"Carbohydrates","path_direction":"True/Yes","condition":"Carbohydrates > 8.0","result_node":"Recommendable","metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}}]}}

EXAMPLE D: illegible leaf + digit ambiguity
Handwriting: "Tuz < 1  ->(?)-> [smudged leaf]   ->(Hayir)-> Onerilmez"
(left branch direction unreadable, left leaf smudged beyond recognition)

{"student_id":null,"data_quality":{"illegible_fields_found":true,"bilingual_mapping_used":["Tuz -> Salt","crossed_out: left_branch_path_direction","Onerilmez -> Not Recommendable"]},"tree_extraction":{"root_node":{"node_type":"Root","variable_feature":"Salt","threshold_value":1.0},"splits":[{"level":1,"parent_feature":"Salt","path_direction":null,"condition":"Salt < 1.0","result_node":null,"metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}},{"level":1,"parent_feature":"Salt","path_direction":"False/No","condition":"Salt >= 1.0","result_node":"Not Recommendable","metrics":{"mcr_rate":null,"accuracy_dogruluk":null,"impurity_info":null}}]}}

════════════════════════════════════════════════
NOW EXTRACT FROM THE WORKSHEET IMAGE ABOVE
════════════════════════════════════════════════
Return ONLY the raw JSON object. No markdown. No explanation."""


def _pil_to_base64(img: Image.Image, max_width: int = 1800) -> str:
    img = img.convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def extract_decision_tree_structure(
    client: anthropic.Anthropic,
    image: Union[Image.Image, Path, str],
    model: str = "claude-opus-4-8",
) -> DecisionTreeExtraction:
    """Extract decision tree structure from a handwritten worksheet image.

    Args:
        client: Anthropic client.
        image: A PIL Image, or a path to a JPEG/PNG file.
        model: Claude model ID. Defaults to claude-opus-4-8 for best HTR quality.

    Returns:
        DecisionTreeExtraction with root node, splits, MCR, and warnings.
    """
    if isinstance(image, (str, Path)):
        image = Image.open(image)

    b64 = _pil_to_base64(image)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        system=_DT_EXTRACTION_SYSTEM,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": b64,
                        },
                    },
                    {"type": "text", "text": _DT_EXTRACTION_USER_TEMPLATE},
                ],
            }
        ],
    )

    raw = response.content[0].text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    parsed = json.loads(raw)
    return DecisionTreeExtraction(**parsed)


# ---------------------------------------------------------------------------
# Rubric definitions
# ---------------------------------------------------------------------------
# Each rubric has:
#   prompt_description: what to tell the LLM about this item
# Rubric criteria are loaded from rubrics/<WS>_rubric.json via pipeline_schema.
# Few-shot examples below supplement LLM scoring for selected items.


# ---------------------------------------------------------------------------
# Few-shot examples
# ---------------------------------------------------------------------------
# Real prior-year student responses sourced from Code Schemes.xlsx
# (CODAP Analiz and Worksheet Analiz sheets, 2024-2025 cohort, n=30).
# Student pseudonyms are preserved from the original data.
# Responses are in Turkish — this is intentional and expected.
# ---------------------------------------------------------------------------

FEW_SHOT_EXAMPLES: dict[str, list[dict]] = {

    "DT_A_Q4": [
        {
            "student_response": (
                "Yağ değişkeni daha iyi bir sonuç çıkarmıştır. MCR ve sensitivity "
                "özelliklerine göre karar verdim."
            ),
            "credit": "full",
            "rationale": (
                "Data-driven: student explicitly names the metric criteria (MCR, sensitivity) "
                "used to select the variable. Not based on general knowledge."
            ),
        },
        {
            "student_response": (
                "Karbonhidrat en iyi performansı verdi. MCR'nin 0'a yaklaşmasına ve "
                "Sens'in 1'e yaklaşmasına dikkat ettim."
            ),
            "credit": "full",
            "rationale": (
                "Data-driven with specific metric targets: references MCR and sensitivity "
                "direction (toward 0 and 1 respectively). Clear performance-based justification."
            ),
        },
        {
            "student_response": "İlk değişkenim şeker çünkü yüksekse tercih edilmiyor.",
            "credit": "partial",
            "rationale": (
                "Names a variable but justification is general nutritional knowledge, "
                "not derived from observing the data distribution."
            ),
        },
        {
            "student_response": "Farklı değişkenler seçilmiş fakat neden bunların seçildiği açıklanmamış.",
            "credit": "zero",
            "rationale": "No justification provided — researcher note confirms no explanation given.",
        },
    ],

    "DT_C_Q2": [
        {
            "student_response": (
                "Eşik değer değiştikçe hatalı değişken sayısı yeni değere bağlı olarak "
                "artar ya da azalır."
            ),
            "credit": "full",
            "rationale": (
                "Correct mechanism: states that misclassification count increases or decreases "
                "depending on the new threshold value. Addresses direction."
            ),
        },
        {
            "student_response": (
                "Doğruluk değişir, bazı besinler sınıf atlar."
            ),
            "credit": "full",
            "rationale": (
                "Correct: accuracy changes and items switch class boundaries. "
                "Names the mechanism (class switching) explicitly."
            ),
        },
        {
            "student_response": "Eşik değerler çok etkiler.",
            "credit": "partial",
            "rationale": (
                "Correct direction but no explanation of how or why — "
                "statement is too vague to demonstrate understanding of the mechanism."
            ),
        },
        {
            "student_response": "Eşik değerlerin sınıflamayı nasıl etkilediğini gösteren açıklama yok.",
            "credit": "zero",
            "rationale": "Researcher confirmed no explanation present. Effectively blank.",
        },
    ],

    "DT_C_Q3": [
        {
            "student_response": (
                "200 kcal. Bu sonuca farklı değerler deneyerek ulaştım."
            ),
            "credit": "full",
            "rationale": (
                "Specific threshold value stated and search method described "
                "(tried different values). Both criteria met."
            ),
        },
        {
            "student_response": (
                "7 ile 10 arası aynı değerleri veriyor; MCR'leri aynı. "
                "Hata payı enerjiden daha az."
            ),
            "credit": "full",
            "rationale": (
                "Systematic search: identified that a range of thresholds give equal MCR, "
                "compared across variables. Evidences deliberate method."
            ),
        },
        {
            "student_response": (
                "Fat 22 eşik değeri en yüksek doğruluk oranı veriyor. "
                "Deneme-yanılma yöntemi ile ulaştım."
            ),
            "credit": "partial",
            "rationale": (
                "States threshold and method (trial-and-error) but does not describe "
                "any comparison or stopping criterion."
            ),
        },
        {
            "student_response": (
                "DT oluştururken grafik oluşturulsa da bu grafikler threshold belirlemede "
                "kullanılmamıştır. Zaten DT'de herhangi bir threshold value da değiştirilmemiş."
            ),
            "credit": "zero",
            "rationale": (
                "Researcher confirmed student did not change any threshold values — "
                "CODAP defaults used as-is. No search occurred."
            ),
        },
    ],

    "DT_E_Q1": [
        {
            "student_response": (
                "MCR daha önemli bence. Burada gıdaların değerlere göre tavsiye edilip "
                "edilmeyeceğini arıyoruz. Ana odağımız sınıflandırma."
            ),
            "credit": "full",
            "rationale": (
                "Names a specific metric (MCR) and ties it to the classification goal "
                "(recommendation decision). Justification is context-specific."
            ),
        },
        {
            "student_response": (
                "Duyarlılık önemli çünkü zararlıları yakalamaktadır."
            ),
            "credit": "full",
            "rationale": (
                "Names sensitivity and justifies with classification consequence "
                "(catching harmful items). Context-relevant reasoning."
            ),
        },
        {
            "student_response": "Duyarlılık olarak daha iyi çünkü daha yüksek.",
            "credit": "partial",
            "rationale": (
                "Names sensitivity but justification is circular "
                "('it's better because it's higher') — no reference to classification goal."
            ),
        },
        {
            "student_response": "Anlamadım?",
            "credit": "zero",
            "rationale": "Student explicitly states they did not understand the question.",
        },
    ],

    "DT_E_Q4": [
        {
            "student_response": (
                "Hayır, çok spesifik olarak ayarlanmış durumlar hariç hayır. "
                "Hatasız kul olmaz."
            ),
            "credit": "full",
            "rationale": (
                "Correct answer (No) with conceptual reason: "
                "perfection is impossible in the general case. "
                "Idiomatic expression confirms genuine understanding."
            ),
        },
        {
            "student_response": "Hayır, illa bir hata yapar.",
            "credit": "full",
            "rationale": (
                "Correct answer (No) — states errors are inevitable. "
                "Concise but conceptually sound."
            ),
        },
        {
            "student_response": "Hayır.",
            "credit": "partial",
            "rationale": "Correct answer (No) but no reason given.",
        },
        {
            "student_response": (
                "Hiç hata olmadan çok zor, ama daha uzun ağaçla olabilir."
            ),
            "credit": "zero",
            "rationale": (
                "Claims perfect classification is achievable with a longer tree — "
                "this is the overfitting misconception. Answer is incorrect."
            ),
        },
        {
            "student_response": (
                "Elbette mümkün ama dallanma çok."
            ),
            "credit": "zero",
            "rationale": (
                "Claims perfect classification is possible. "
                "Acknowledges it requires many branches but still affirms it is achievable."
            ),
        },
    ],

    "DT_F_Q2": [
        {
            "student_response": (
                "Emit sonucu eğitimden biraz düşük çıkar. "
                "Aşırı öğrenme varsa eğitimde çok iyi testte düşük olur. "
                "Gerçek performans test sonucuna göre olur."
            ),
            "credit": "full",
            "rationale": (
                "Correct direction (test lower than training), names overfitting explicitly, "
                "and states that test performance reflects true model quality. "
                "All three full-credit criteria met."
            ),
        },
        {
            "student_response": "Test verisindeki MCR daha yüksek.",
            "credit": "partial",
            "rationale": (
                "Correct direction (MCR higher = worse on test) with a numeric metric reference. "
                "No conceptual explanation for why the difference exists."
            ),
        },
        {
            "student_response": (
                "Test verisinde MCR ve sensitivity sonuçları daha iyi çıktı. "
                "Tavsiye edilebilir ve edilemez gıdaların sayısı değişti."
            ),
            "credit": "partial",
            "rationale": (
                "Notes a difference (test metrics better than training — unusual direction) "
                "but no conceptual explanation. Test-better result is atypical; "
                "flag for manual review if log data is available."
            ),
        },
        {
            "student_response": "Eğitim ve test veri setlerinin karşılaştırılması yapılmadı.",
            "credit": "zero",
            "rationale": (
                "Researcher confirmed no train/test comparison was performed. "
                "Section F was not completed."
            ),
        },
    ],

    "DT_G_Q1": [
        {
            "student_response": (
                "Sınırlar arasında belirli kalıplara sığmayı öğrendi."
            ),
            "credit": "full",
            "rationale": (
                "States the model learned patterns within boundaries — "
                "captures the core idea that the model learns decision rules from data."
            ),
        },
        {
            "student_response": "Sınıflandırmayı öğrendi.",
            "credit": "partial",
            "rationale": (
                "Correct category (classification) but very vague — "
                "does not specify what patterns or rules were learned from the data."
            ),
        },
        {
            "student_response": (
                "Kesinliğe ulaşana kadar bir yazılım DT oluşturmaya devam ettiğini yazmış."
            ),
            "credit": "zero",
            "rationale": (
                "Describes software behaviour, not what the model learned from data. "
                "Conflates model building process with model knowledge."
            ),
        },
    ],

    "DT_E_sensitivity": [
        {
            "student_response": "Duyarlılık: 0.613",
            "credit": "full",
            "rationale": (
                "Numeric value provided in decimal format. "
                "Formula verification and arithmetic check performed separately by Python."
            ),
        },
        {
            "student_response": "TP / (TP + FN) = 0.737",
            "credit": "full",
            "rationale": "Correct formula written out explicitly with computed value.",
        },
        {
            "student_response": "TP / total = 0.8",
            "credit": "partial",
            "rationale": (
                "Incorrect formula (divides by total instead of TP+FN) "
                "but shows awareness that sensitivity involves TP."
            ),
        },
        {
            "student_response": "",
            "credit": "not_attempted",
            "rationale": "Item left blank.",
        },
    ],

    "DT_E_MCR": [
        {
            "student_response": "(FP + FN) / toplam = 0.27",
            "credit": "full",
            "rationale": "Correct formula (errors divided by total) with computed value.",
        },
        {
            "student_response": "Hata oranı: 0.24",
            "credit": "partial",
            "rationale": "Value provided but no formula — cannot verify formula understanding.",
        },
        {
            "student_response": "",
            "credit": "not_attempted",
            "rationale": "Item left blank.",
        },
    ],

    "DT_D_Q4": [
        {
            "student_response": (
                "MCR ve sensitivity değerlerine bakarak. "
                "MCR 0'a yakın, Sensitivity 1'e yakın olduğunda yeterince iyi."
            ),
            "credit": "full",
            "rationale": (
                "Clear stopping criterion: dual metric thresholds (MCR near 0, Sensitivity near 1). "
                "Both performance metrics referenced with direction."
            ),
        },
        {
            "student_response": "0.18'den daha aşağıda olacağını düşünmüyorum.",
            "credit": "partial",
            "rationale": (
                "References an accuracy plateau as stopping criterion "
                "but only names MCR direction, not a paired metric check."
            ),
        },
        {
            "student_response": "Benim yaptığım bence yeterince iyi. Diğerlerini bilmiyorum.",
            "credit": "zero",
            "rationale": (
                "Subjective claim with no criterion. Cannot evaluate stopping decision "
                "without a reference metric or comparison."
            ),
        },
    ],

    "DT_B_Q4": [
        {
            "student_response": (
                "Doymuş yağ en iyi sonucu verdi. MCR ve sensitivity en iyisiydi."
            ),
            "credit": "full",
            "rationale": (
                "Names a specific variable and states the decision criterion "
                "(MCR and sensitivity). Both criteria for full credit are met."
            ),
        },
        {
            "student_response": "Enerji kcal sadece 1 misclassification eğer 250 kcal eşik değer olursa.",
            "credit": "full",
            "rationale": (
                "Names variable (energy) with specific threshold (250 kcal) and "
                "misclassification count (1). Clear metric-based criterion."
            ),
        },
        {
            "student_response": (
                "Fat 22 eşik değeri en yüksek doğruluk oranı veriyor."
            ),
            "credit": "partial",
            "rationale": (
                "Names variable and threshold but 'highest accuracy' is not tied to "
                "a specific MCR or sensitivity value — criterion is vague."
            ),
        },
        {
            "student_response": (
                "Fat ve Energy değişkenleri kullanıldı. Hangi DT'nin daha iyi olduğuna "
                "dair herhangi bir açıklama gözlemlenmedi."
            ),
            "credit": "zero",
            "rationale": "Researcher confirmed no comparison or selection criterion stated.",
        },
    ],

    "DT_D_Q2": [
        {
            "student_response": (
                "Fat eklenince MCR=0.325 ve Sens=1 oldu. İkinci seviyeye eklenen değişken "
                "sınıflandırmayı iyileştirdi."
            ),
            "credit": "full",
            "rationale": (
                "Numeric comparison provided (MCR and Sensitivity after adding second variable). "
                "States direction of improvement explicitly."
            ),
        },
        {
            "student_response": (
                "İkinci seviyeye eklenen değişkenin sınıflandırmayı biraz olsa da "
                "iyileştirdi. Eski MCR: 0.182 Sens: 0.684 Yeni MCR: 0.159 Sens: 0.895"
            ),
            "credit": "full",
            "rationale": (
                "Before/after comparison with specific metric values. "
                "Direction stated (improvement). All full-credit criteria met."
            ),
        },
        {
            "student_response": "İki seviyeli karar ağacının sınıflandırmayı iyileştirdiği belirtilmiş.",
            "credit": "partial",
            "rationale": "States improvement but no numeric comparison provided.",
        },
        {
            "student_response": (
                "Yalnızca tek seviyeli karar ağaçları kurduğu gözlendi. "
                "İki seviyeli yapı kurmaya dair herhangi bir uygulama bulunmadı."
            ),
            "credit": "zero",
            "rationale": "Student never built a two-level tree — researcher confirmed.",
        },
    ],

    "DT_A_Q2": [
        {
            "student_response": (
                "Grafikte ilgili değişkenin değerleri incelenmiş, movable value eklenmiş. "
                "Enerji ve doymuş yağ en iyi ayırt ediciler."
            ),
            "credit": "full",
            "rationale": (
                "Graph consulted (movable value technique) and specific variables named. "
                "Data-driven, not intuition-driven."
            ),
        },
        {
            "student_response": "Çalışma kağıdında genel kanaate ve verilere dayanarak feature'lar seçilmiştir.",
            "credit": "partial",
            "rationale": (
                "References data but also 'general opinion' — mixed evidence basis. "
                "No specific graph or distribution cited."
            ),
        },
        {
            "student_response": "Farklı değişkenleri sırasıyla deneme, karşılaştırma alanları boş.",
            "credit": "zero",
            "rationale": "Comparison fields left blank — researcher confirmed no data-based reasoning recorded.",
        },
    ],

    "DT_A_Q1": [
        {
            "student_response": (
                "Bence şeker ve yağ miktarı bir gıdanın tavsiye edilip edilmeyeceğini etkiler."
            ),
            "credit": "full",
            "rationale": (
                "Prior belief: names specific features before CODAP analysis. "
                "Baseline diagnostic — not Deepen evidence."
            ),
        },
        {
            "student_response": "Sağlıklı yiyecekler daha iyidir.",
            "credit": "zero",
            "rationale": "No dataset feature named — vague prior only.",
        },
    ],

    "DT_A_Q3": [
        {
            "student_response": (
                "Evet, şeker miktarı anlamlı bir fark gösterdi. Tavsiye edilen gıdalarda şeker "
                "değeri genellikle daha düşük."
            ),
            "credit": "full",
            "rationale": (
                "Affirms meaningful difference, names feature (sugar), and describes direction "
                "between classes from observed data."
            ),
        },
        {
            "student_response": "Evet fark var.",
            "credit": "partial",
            "rationale": "Acknowledges difference but no feature or direction described.",
        },
        {
            "student_response": "(bos)",
            "credit": "zero",
            "rationale": "Blank response.",
        },
    ],

    "WS11_Q11": [
        {
            "student_response": "2",
            "credit": "full",
            "rationale": (
                "WS11_Q11_2: correct position for 'arrange data by feature dimension' — "
                "procedural DT workflow step 2."
            ),
        },
        {
            "student_response": "4",
            "credit": "zero",
            "rationale": (
                "WS11_Q11_2: step 2 statement assigned position 4 — incorrect workflow order."
            ),
        },
        {
            "student_response": "",
            "credit": "zero",
            "rationale": "Blank ordering response — cannot evidence LO3.1.2 workflow understanding.",
        },
    ],

    "DT_G_Q2": [
        {
            "student_response": (
                "Hangi değişkenlerin önemli olduğunu, karar vermede nasıl kullanıldığını "
                "fark ettim. Ayrıca eşik değer kavramını anladım."
            ),
            "credit": "full",
            "rationale": (
                "Names specific concepts learned: feature importance, decision-making mechanism, "
                "threshold concept. Rich metacognitive reflection."
            ),
        },
        {
            "student_response": "Çok şey öğrendim, nasıl bir karar ağacı yapılacağını öğrendim.",
            "credit": "partial",
            "rationale": (
                "General reflection on learning how to build a tree — "
                "no specific concept named."
            ),
        },
        {
            "student_response": "",
            "credit": "not_attempted",
            "rationale": "Left blank.",
        },
    ],

    "DT_E_Q4": [
        {
            "student_response": (
                "Hayır, çok spesifik olarak ayarlanmış durumlar hariç hayır. "
                "Hatasız kul olmaz."
            ),
            "credit": "full",
            "rationale": (
                "Correct answer (No) with conceptual reason: "
                "perfection is impossible in the general case. "
                "Idiomatic expression confirms genuine understanding."
            ),
        },
        {
            "student_response": "Hayır, illa bir hata yapar.",
            "credit": "full",
            "rationale": (
                "Correct answer (No) — states errors are inevitable. "
                "Concise but conceptually sound."
            ),
        },
        {
            "student_response": "Hayır.",
            "credit": "partial",
            "rationale": "Correct answer (No) but no reason given.",
        },
        {
            "student_response": (
                "Hiç hata olmadan çok zor, ama daha uzun ağaçla olabilir."
            ),
            "credit": "zero",
            "rationale": (
                "Claims perfect classification is achievable with a longer tree — "
                "this is the overfitting misconception. Answer is incorrect."
            ),
        },
        {
            "student_response": (
                "Elbette mümkün ama dallanma çok."
            ),
            "credit": "zero",
            "rationale": (
                "Claims perfect classification is possible. "
                "Acknowledges it requires many branches but still affirms it is achievable."
            ),
        },
    ],
}


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert educational assessment researcher specialising in AI literacy
for pre-service teachers. You assess student worksheet responses against rubrics.

Your job:
1. Read the student response for each item.
2. Apply the rubric criteria provided.
3. Assign one of: "full", "partial", "zero", or "not_attempted".
4. Write a short rationale (1-2 sentences). Be specific about which criterion is met or missed.
5. Quote the most relevant phrase from the student response as evidence_quote.
   If the response is blank, write evidence_quote as "(blank)".

Rules:
- Never invent information not present in the student response.
- Never compute numeric values yourself. If a numeric answer is required, report what the student wrote.
- If a response is too vague to assign full credit but shows relevant understanding, assign partial.
- Flag contradictions with log data only when a log_context field is provided.

Respond ONLY with a valid JSON object matching this schema:
{
  "item_id": "string",
  "credit": "full" | "partial" | "zero" | "not_attempted",
  "llm_rationale": "string (min 10 chars)",
  "evidence_quote": "string",
  "flag": "string or null"
}"""


WS_DT_INTERPRETIVE_SUPPLEMENT = """
WS_DT interpretive scoring (applies to this item):
- There is NO single correct answer. Students choose their own variables, thresholds, and conclusions from CODAP.
- Score ONLY on whether rubric components are met (data reference, justification, metric use, reflection).
- NEVER penalize because the student's answer differs from the illustrative example (different feature names, thresholds, or metric values are expected).
- Partial credit when one of two components is present or reasoning is thin but on-topic.
- EMIT/numeric items are exceptions: check internal consistency of the student's own recorded numbers only.
"""


def _system_prompt_for_item(item_id: str, worksheet_id: str | None) -> str:
    ws = normalize_worksheet_id(worksheet_id) if worksheet_id else None
    if ws != "WS_DT":
        return SYSTEM_PROMPT
    rubric = load_rubric(ws)
    item = rubric_item(ws, item_id)
    if is_interpretive_rubric_item(item, rubric, item_id=item_id):
        return SYSTEM_PROMPT + WS_DT_INTERPRETIVE_SUPPLEMENT
    return SYSTEM_PROMPT


def _few_shot_parent_key(item_id: str) -> str | None:
    """Map WS11 sub-items to legacy few-shot parent keys when needed."""
    if item_id.startswith("WS11_Q10_"):
        return "WS11_Q10"
    if item_id.startswith("WS11_Q11_"):
        return "WS11_Q11"
    if item_id.startswith("WS11_Q12_"):
        return "WS11_Q12"
    return None


def _build_few_shot_block(item_id: str) -> str:
    examples = FEW_SHOT_EXAMPLES.get(item_id)
    if not examples:
        parent = _few_shot_parent_key(item_id)
        if parent:
            examples = FEW_SHOT_EXAMPLES.get(parent, [])
    if not examples:
        return ""
    lines = ["\n--- Few-shot examples for this item ---"]
    for i, ex in enumerate(examples, 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"Student response: {ex['student_response']}")
        lines.append(f"Credit: {ex['credit']}")
        lines.append(f"Rationale: {ex['rationale']}")
    lines.append("--- End of examples ---\n")
    return "\n".join(lines)


def _build_rubric_block(item_id: str, worksheet_id: str | None = None) -> str:
    worksheet = normalize_worksheet_id(worksheet_id) if worksheet_id else None
    rubric = get_assessor_rubric(item_id, worksheet)
    lines = [
        f"Item: {item_id}",
        f"Description: {rubric['prompt_description']}",
        "",
        "Full credit if:",
    ]
    for c in rubric["full_credit_criteria"]:
        lines.append(f"  - {c}")
    lines.append("Partial credit if:")
    for c in rubric["partial_credit_criteria"]:
        lines.append(f"  - {c}")
    lines.append("Zero credit if:")
    for c in rubric["zero_credit_criteria"]:
        lines.append(f"  - {c}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Arithmetic verifiers (Python, not LLM)
# ---------------------------------------------------------------------------

def _verify_sensitivity(tp: Optional[float], fn: Optional[float],
                         student_answer: Optional[float]) -> Optional[str]:
    """Returns a flag string if sensitivity answer is arithmetically wrong."""
    if tp is None or fn is None or student_answer is None:
        return None
    denominator = tp + fn
    if denominator == 0:
        return "sensitivity_denominator_zero"
    expected = tp / denominator
    if abs(expected - student_answer) > 0.01:
        return f"numeric_mismatch:expected_{expected:.3f}_got_{student_answer:.3f}"
    return None


def _verify_mcr(fp: Optional[float], fn: Optional[float],
                student_total: Optional[float], student_answer: Optional[float]) -> Optional[str]:
    """Returns a flag string if MCR answer is arithmetically wrong."""
    if any(v is None for v in (fp, fn, student_total, student_answer)):
        return None
    if student_total == 0:
        return "mcr_denominator_zero"
    expected = (fp + fn) / student_total
    if abs(expected - student_answer) > 0.01:
        return f"numeric_mismatch:expected_{expected:.3f}_got_{student_answer:.3f}"
    return None


# ---------------------------------------------------------------------------
# Core assessment function
# ---------------------------------------------------------------------------

def assess_item(
    client: anthropic.Anthropic,
    item_id: str,
    student_response: str,
    log_context: Optional[str] = None,
    model: str = "claude-sonnet-4-6",
    worksheet_id: str | None = None,
) -> ItemScore:
    """
    Assess one worksheet item for one student.

    Args:
        client: Anthropic client.
        item_id: Rubric key (e.g. "DT_A_Q2").
        student_response: Raw student response text.
        log_context: Optional log-derived facts (e.g. "final accuracy: 0.82, depth: 3").
            If provided, the LLM can cross-check student claims.
        model: Claude model ID to use.

    Returns:
        ItemScore with credit, rationale, evidence_quote, and optional flag.
    """
    rubric_block = _build_rubric_block(item_id, worksheet_id)
    few_shot_block = _build_few_shot_block(item_id)

    user_content_parts = [rubric_block, few_shot_block]
    if log_context:
        user_content_parts.append(f"\nLog-derived context for this student:\n{log_context}")
    user_content_parts.append(f"\nStudent response:\n{student_response.strip() or '(blank)'}")
    user_content_parts.append(f"\nNow assess item {item_id}. Return JSON only.")

    response = client.messages.create(
        model=model,
        max_tokens=512,
        system=_system_prompt_for_item(item_id, worksheet_id),
        messages=[{"role": "user", "content": "\n".join(user_content_parts)}],
    )

    raw = response.content[0].text.strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"assess_item: LLM returned non-JSON for {item_id!r}: {exc}\nraw={raw!r}"
        ) from exc

    parsed["item_id"] = item_id  # enforce correct item_id regardless of LLM output

    try:
        return ItemScore(**parsed)
    except Exception as exc:
        raise ValueError(
            f"assess_item: LLM output failed schema validation for {item_id!r}: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# Student-level worksheet runner
# ---------------------------------------------------------------------------

def assess_worksheet(
    client: anthropic.Anthropic,
    candidate_id: str,
    worksheet_id: str,
    responses: dict[str, str],
    log_contexts: Optional[dict[str, str]] = None,
    numeric_checks: Optional[dict] = None,
    model: str = "claude-sonnet-4-6",
) -> WorksheetAssessment:
    """
    Assess all items for one student's worksheet.

    Args:
        client: Anthropic client.
        candidate_id: Canonical student ID.
        worksheet_id: Worksheet identifier (e.g. "DT", "WS11").
        responses: {item_id: student_response_text}
        log_contexts: {item_id: log_context_string} — optional per-item log data.
        numeric_checks: Dict with keys matching arithmetic verifier signatures.
            Example for DT_E_sensitivity: {"tp": 14, "fn": 3, "answer": 0.824}
        model: Claude model ID.

    Returns:
        WorksheetAssessment object.
    """
    log_contexts = log_contexts or {}
    numeric_checks = numeric_checks or {}
    worksheet = normalize_worksheet_id(worksheet_id)
    rubric = load_rubric(worksheet)
    scored_ids = scoring_item_ids(worksheet)
    target_ids = [iid for iid in scored_ids if iid in responses]

    item_scores: list[ItemScore] = []

    for item_id in target_ids:
        response_text = responses[item_id]
        score = assess_item(
            client=client,
            item_id=item_id,
            student_response=response_text,
            log_context=log_contexts.get(item_id),
            model=model,
            worksheet_id=worksheet,
        )

        # Python arithmetic checks (override LLM on numerical items)
        if item_id == "DT_E_sensitivity" and "sensitivity" in numeric_checks:
            nc = numeric_checks["sensitivity"]
            flag = _verify_sensitivity(nc.get("tp"), nc.get("fn"), nc.get("answer"))
            if flag:
                score = score.model_copy(update={"flag": flag})

        if item_id == "DT_E_MCR" and "mcr" in numeric_checks:
            nc = numeric_checks["mcr"]
            flag = _verify_mcr(nc.get("fp"), nc.get("fn"), nc.get("total"), nc.get("answer"))
            if flag:
                score = score.model_copy(update={"flag": flag})

        item_rubric = rubric_item(worksheet, item_id)
        if item_rubric.get("check") == "unordered_token_set":
            det = score_unordered_token_set(response_text, item_rubric)
            score = score.model_copy(
                update={
                    "credit": det["credit"],
                    "flag": (
                        f"unordered_token_set:{det['matched_tokens']}/{det['need_tokens']}"
                        if det["credit"] != "full"
                        else None
                    ),
                }
            )
        elif item_rubric.get("check") == "any_of_tokens":
            det = score_any_of_tokens(response_text, item_rubric, rubric)
            score = score.model_copy(
                update={
                    "credit": det["credit"],
                    "flag": (
                        f"any_of_tokens:no_match"
                        if det["credit"] == "zero"
                        else None
                    ),
                }
            )

        item_scores.append(score)

    if not item_scores:
        raise ValueError(
            f"assess_worksheet: no rubric items found for worksheet_id={worksheet_id!r}. "
            f"Check that responses keys match scoring items for {worksheet!r}."
        )

    # Overall worksheet credit
    credits = [s.credit for s in item_scores]
    if all(c == "not_attempted" for c in credits):
        overall = "not_attempted"
    elif all(c in ("full", "not_attempted") for c in credits):
        overall = "full"
    elif all(c in ("zero", "not_attempted") for c in credits):
        overall = "zero"
    else:
        overall = "partial"

    return WorksheetAssessment(
        candidate_id=candidate_id,
        worksheet_id=worksheet_id,
        item_scores=item_scores,
        overall_worksheet_credit=overall,
    )


# ---------------------------------------------------------------------------
# Convenience: assess only the DT worksheet from a structured input dict
# ---------------------------------------------------------------------------

def assess_worksheet_dt(
    client: anthropic.Anthropic,
    candidate_id: str,
    responses: dict[str, str],
    log_features: Optional[dict] = None,
    model: str = "claude-sonnet-4-6",
) -> WorksheetAssessment:
    """
    Assess Worksheet DT with optional log cross-checking.

    log_features should be the LogDerivedFeatures dict for this student.
    Key fields used for cross-checking:
        final_accuracy, max_tree_depth_reached, train_test_applied,
        threshold_change_count, final_train_tp, final_train_fn, etc.
    """
    log_features = log_features or {}

    # Build per-item log contexts from log features
    log_contexts: dict[str, str] = {}

    if log_features:
        final_acc = log_features.get("final_accuracy")
        depth = log_features.get("max_tree_depth_reached")
        tca = log_features.get("train_test_applied")
        tc_count = log_features.get("threshold_change_count")
        tp = log_features.get("final_train_tp")
        tn = log_features.get("final_train_tn")
        fp = log_features.get("final_train_fp")
        fn = log_features.get("final_train_fn")

        if final_acc is not None:
            log_contexts["DT_D_Q2"] = f"Log: final_accuracy={final_acc}, max_depth={depth}"
            log_contexts["DT_E_Q1"] = f"Log: final_accuracy={final_acc}"
            log_contexts["DT_F_Q2"] = (
                f"Log: train_test_applied={tca}, final_accuracy={final_acc}"
            )

        if all(v is not None for v in (tp, tn, fp, fn)):
            log_contexts["DT_E_sensitivity"] = f"Log: TP={tp}, TN={tn}, FP={fp}, FN={fn}"
            log_contexts["DT_E_MCR"] = f"Log: TP={tp}, TN={tn}, FP={fp}, FN={fn}"

        if tc_count is not None:
            log_contexts["DT_C_Q3"] = f"Log: threshold_change_count={tc_count}"

    # Numeric checks for arithmetic verification
    numeric_checks: dict = {}
    tp, fn = log_features.get("final_train_tp"), log_features.get("final_train_fn")
    fp = log_features.get("final_train_fp")
    total = sum(
        v for v in [
            log_features.get("final_train_tp"),
            log_features.get("final_train_tn"),
            log_features.get("final_train_fp"),
            log_features.get("final_train_fn"),
        ] if v is not None
    ) or None

    if responses.get("DT_E_sensitivity"):
        try:
            answer = float(responses["DT_E_sensitivity"])
            numeric_checks["sensitivity"] = {"tp": tp, "fn": fn, "answer": answer}
        except (ValueError, TypeError):
            pass

    if responses.get("DT_E_MCR"):
        try:
            answer = float(responses["DT_E_MCR"])
            numeric_checks["mcr"] = {"fp": fp, "fn": fn, "total": total, "answer": answer}
        except (ValueError, TypeError):
            pass

    return assess_worksheet(
        client=client,
        candidate_id=candidate_id,
        worksheet_id="DT",
        responses=responses,
        log_contexts=log_contexts,
        numeric_checks=numeric_checks,
        model=model,
    )


# ---------------------------------------------------------------------------
# CLI entry point for single-student testing
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import os

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    # --- Smoke test: one student, two DT items ---
    test_responses = {
        "DT_A_Q4": (
            "I chose energy because in the scatter plot the recommended foods "
            "were clearly clustered below 200 kcal and the not-recommended ones above."
        ),
        "DT_C_Q2": "When I changed the threshold the accuracy went up or down.",
        "DT_E_Q4": "No, because some foods have similar nutrition but different labels.",
        "DT_F_Q2": (
            "Training accuracy was 0.82 and test accuracy was 0.74. The model was built "
            "on training data so it fits those examples better."
        ),
        "DT_G_Q1": "It learned which nutritional features separate recommended from not-recommended foods.",
    }

    test_log_features = {
        "final_accuracy": 0.82,
        "max_tree_depth_reached": 3,
        "train_test_applied": True,
        "threshold_change_count": 12,
        "final_train_tp": 21,
        "final_train_tn": 18,
        "final_train_fp": 5,
        "final_train_fn": 4,
    }

    result = assess_worksheet_dt(
        client=client,
        candidate_id="test_student",
        responses=test_responses,
        log_features=test_log_features,
    )

    print(result.model_dump_json(indent=2))
