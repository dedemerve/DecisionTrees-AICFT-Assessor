"""
Central behaviour-opportunity definitions for worksheet bundles.

Maps rubric item IDs to Observable Behaviour (OB_*) candidates only.
No ILO, Domain, or AI-CFT references are permitted in this module.
"""

from __future__ import annotations

from typing import Any

OB_REF = "framework/Observable_Behaviours.json"

# Deployed ProDaBi unplugged worksheets with legacy rubrics in rubrics/.
DEPLOYED_WORKSHEETS: frozenset[str] = frozenset(
    {"WS1", "WS3", "WS4", "WS5", "WS6", "WS7", "WS10", "WS11"}
)

NOT_DEPLOYED_WORKSHEETS: frozenset[str] = frozenset({"WS2", "WS8", "WS9"})

ALL_WORKSHEETS: tuple[str, ...] = tuple(
    f"WS{i}" for i in range(1, 12)
)

BUNDLE_FILES: tuple[str, ...] = (
    "extraction_schema.json",
    "rubric.json",
    "behaviour_opportunities.json",
    "validity_notes.json",
    "answer_key.json",
)

FORBIDDEN_SUBSTRINGS: tuple[str, ...] = (
    "lo3",
    "ilo_id",
    "learning_object",
    "domain_id",
    "ai_cft",
    "ai-cft",
    "competency",
    "maps_to",
    "may_contribute_to",
    "may_indicate",
)


def _opp(
    behaviour_id: str,
    *,
    role: str = "primary",
    evidence_mode: str = "direct",
    rationale: str,
) -> dict[str, str]:
    return {
        "behaviour_id": behaviour_id,
        "role": role,
        "evidence_mode": evidence_mode,
        "rationale": rationale,
    }


def _item(
    opportunities: list[dict[str, str]],
    extraction_fields: list[str] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"opportunities": opportunities}
    if extraction_fields:
        out["extraction_fields"] = extraction_fields
    return out


# ---------------------------------------------------------------------------
# Per-worksheet behaviour opportunity maps (rubric item key → OB candidates)
# ---------------------------------------------------------------------------

BEHAVIOUR_MAP: dict[str, dict[str, dict[str, Any]]] = {
    "WS1": {
        "WS1_B1": _item([_opp("OB_CON_001", rationale="Defines instance/object vocabulary.")]),
        "WS1_B2": _item([_opp("OB_CON_001", rationale="Defines measurable feature vocabulary.")]),
        "WS1_B3": _item([_opp("OB_CON_001", rationale="Defines class label / target vocabulary.")]),
        "WS1_B4": _item([_opp("OB_CON_002", rationale="Defines threshold as a splitting boundary.")]),
        "WS1_B5": _item([_opp("OB_CON_001", rationale="Defines if-then decision rule vocabulary.")]),
        "WS1_B6": _item([
            _opp("OB_CON_005", rationale="Defines true positive (TP) confusion-matrix cell."),
            _opp("OB_CON_006", role="secondary", evidence_mode="indirect",
                 rationale="TP sits within broader confusion-matrix understanding."),
        ]),
        "WS1_B7": _item([
            _opp("OB_CON_005", rationale="Defines false positive (FP) confusion-matrix cell."),
            _opp("OB_CON_006", role="secondary", evidence_mode="indirect",
                 rationale="FP contrasts predicted vs actual outcomes."),
        ]),
        "WS1_B8": _item([_opp("OB_CON_005", rationale="Recalls sensitivity formula TP/(TP+FN).")]),
        "WS1_B9": _item([_opp("OB_CON_005", rationale="Recalls misclassification rate formula.")]),
        "WS1_B10": _item([_opp("OB_CON_003", rationale="Defines overfitting as poor generalization.")]),
        "WS1_B11": _item([_opp("OB_CON_004", rationale="Defines decision tree structure and data-driven learning.")]),
    },
    "WS3": {
        "WS3_B1": _item([_opp("OB_PRO_001", rationale="Applies Leo's rule to classify instance 1."),
                         _opp("OB_PRO_006", role="secondary", evidence_mode="direct",
                              rationale="Assigns recommended/not-recommended label.")]),
        "WS3_B2": _item([_opp("OB_PRO_001", rationale="Justifies classification using feature value."),
                         _opp("OB_STR_001", role="secondary", evidence_mode="direct",
                              rationale="Links feature to threshold comparison in reasoning.")]),
        "WS3_B3": _item([_opp("OB_PRO_001", rationale="Applies Leo's rule to classify instance 2."),
                         _opp("OB_PRO_006", role="secondary", evidence_mode="direct",
                              rationale="Assigns recommended label.")]),
        "WS3_B4": _item([_opp("OB_PRO_001", rationale="Justifies recommended classification."),
                         _opp("OB_STR_001", role="secondary", evidence_mode="direct",
                              rationale="Threshold comparison in verbal reasoning.")]),
        "WS3_B5": _item([_opp("OB_PRO_001", rationale="Applies Leo's rule to classify instance 3."),
                         _opp("OB_PRO_006", role="secondary", evidence_mode="direct",
                              rationale="Assigns not-recommended label.")]),
        "WS3_B6": _item([_opp("OB_PRO_001", rationale="Justifies not-recommended classification."),
                         _opp("OB_STR_001", role="secondary", evidence_mode="direct",
                              rationale="Feature-threshold reasoning statement.")]),
        "WS3_B7": _item([_opp("OB_PRO_007", rationale="Student sets energy threshold with operator."),
                         _opp("OB_STR_002", role="secondary", evidence_mode="direct",
                              rationale="Threshold direction encodes split semantics.")]),
        "WS3_B8": _item([_opp("OB_PRO_007", rationale="Complementary threshold branch for energy feature."),
                         _opp("OB_STR_002", role="secondary", evidence_mode="direct",
                              rationale="Operator direction must pair with B7.")]),
    },
    "WS4": {
        "WS4_B1": _item([_opp("OB_PRO_007", rationale="Selects numeric threshold from grid."),
                         _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                              rationale="Threshold choice informed by error grid.")]),
        "WS4_B2": _item([_opp("OB_STR_003", rationale="States MCR-minimization as selection criterion.")]),
        "WS4_B3": _item([_opp("OB_STR_003", rationale="Compares two threshold candidates using MCR."),
                         _opp("OB_REF_003", role="secondary", evidence_mode="direct",
                              rationale="Evaluates comparative claim about thresholds.")]),
        "WS4_B4": _item([_opp("OB_CON_005", rationale="States MCR formula deterministically.")]),
        "WS4_B5": _item([_opp("OB_REF_002", rationale="Evaluates peer statement about threshold optimality.")]),
    },
    "WS5": {
        "WS5_row1": _item([_opp("OB_PRO_007", rationale="Threshold expression in grid row 1."),
                           _opp("OB_PRO_008", role="secondary", evidence_mode="direct",
                                rationale="Correct/error counts for row 1."),
                           _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                                rationale="MCR consistency for row 1.")]),
        "WS5_row2": _item([_opp("OB_PRO_007", rationale="Threshold expression in grid row 2."),
                           _opp("OB_PRO_008", role="secondary", evidence_mode="direct",
                                rationale="Correct/error counts for row 2."),
                           _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                                rationale="MCR consistency for row 2.")]),
        "WS5_row3": _item([_opp("OB_PRO_007", rationale="Threshold expression in grid row 3."),
                           _opp("OB_PRO_008", role="secondary", evidence_mode="direct",
                                rationale="Correct/error counts for row 3."),
                           _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                                rationale="MCR consistency for row 3.")]),
        "WS5_row4": _item([_opp("OB_PRO_007", rationale="Threshold expression in grid row 4."),
                           _opp("OB_PRO_008", role="secondary", evidence_mode="direct",
                                rationale="Correct/error counts for row 4."),
                           _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                                rationale="MCR consistency for row 4.")]),
        "WS5_row5": _item([_opp("OB_PRO_007", rationale="Threshold expression in grid row 5."),
                           _opp("OB_PRO_008", role="secondary", evidence_mode="direct",
                                rationale="Correct/error counts for row 5."),
                           _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                                rationale="MCR consistency for row 5.")]),
        "WS5_B25": _item([_opp("OB_PRO_007", rationale="Final threshold choice from experiment."),
                          _opp("OB_STR_001", role="secondary", evidence_mode="direct",
                               rationale="Data-based justification for chosen threshold.")],
                         extraction_fields=["WS5_B25"]),
    },
    "WS6": {
        "WS6_root_feature": _item([_opp("OB_PRO_002", rationale="Selects root split feature.")],
                                  extraction_fields=["WS6_B1"]),
        "WS6_root_threshold": _item([_opp("OB_PRO_007", rationale="Root threshold with operator."),
                                     _opp("OB_STR_002", role="secondary", evidence_mode="direct",
                                          rationale="Split direction at root.")],
                                    extraction_fields=["WS6_B2"]),
        "WS6_root_labels": _item([_opp("OB_PRO_003", rationale="Branch labels at root node.")],
                                   extraction_fields=["WS6_B3", "WS6_B4"]),
        "WS6_inner_feature": _item([_opp("OB_PRO_002", rationale="Inner-node feature distinct from root.")],
                                   extraction_fields=["WS6_B6"]),
        "WS6_inner_threshold": _item([_opp("OB_PRO_007", rationale="Inner-node threshold with operator."),
                                      _opp("OB_STR_002", role="secondary", evidence_mode="direct",
                                           rationale="Inner split direction.")],
                                     extraction_fields=["WS6_B7"]),
        "WS6_inner_labels": _item([_opp("OB_PRO_003", rationale="Branch labels at inner node.")],
                                    extraction_fields=["WS6_B8", "WS6_B9"]),
        "WS6_leaves": _item([_opp("OB_PRO_006", rationale="Leaf class labels on tree paths."),
                             _opp("OB_PRO_004", role="secondary", evidence_mode="direct",
                                  rationale="Leaf labels consistent with path logic.")],
                            extraction_fields=["WS6_B5", "WS6_B10", "WS6_B11", "WS6_B12", "WS6_B13"]),
        "WS6_tree_structure": _item([_opp("OB_PRO_005", rationale="Holistic tree validity (depth, features, leaves)."),
                                     _opp("OB_STR_004", role="secondary", evidence_mode="direct",
                                          rationale="Structural coherence of drawn tree.")]),
    },
    "WS7": {
        "WS7_P1_box1": _item([_opp("OB_PRO_003", rationale="Matches given rule to tree path A/B/C.")],
                             extraction_fields=["WS7_P1_box1"]),
        "WS7_P1_box2": _item([_opp("OB_PRO_003", rationale="Matches given rule to tree path.")],
                             extraction_fields=["WS7_P1_box2"]),
        "WS7_P1_box3": _item([_opp("OB_PRO_003", rationale="Matches given rule to tree path.")],
                             extraction_fields=["WS7_P1_box3"]),
        "WS7_B1": _item([_opp("OB_PRO_009", rationale="Writes if-then rule consistent with WS6 tree path."),
                         _opp("OB_STR_006", role="secondary", evidence_mode="direct",
                              rationale="Rule encodes feature, operator, and conclusion.")],
                        extraction_fields=["WS7_B1"]),
        "WS7_B2": _item([_opp("OB_PRO_009", rationale="Second path rule consistent with WS6 tree."),
                         _opp("OB_STR_006", role="secondary", evidence_mode="direct",
                              rationale="Conditional structure for path B.")],
                        extraction_fields=["WS7_B2"]),
        "WS7_B3": _item([_opp("OB_PRO_009", rationale="Third path rule consistent with WS6 tree."),
                         _opp("OB_STR_006", role="secondary", evidence_mode="direct",
                              rationale="Conditional structure for path C.")],
                        extraction_fields=["WS7_B3"]),
    },
    "WS10": {
        "WS10_B1": _item([_opp("OB_PRO_007", rationale="Computes midpoint threshold from sorted values.")]),
        "WS10_B2": _item([_opp("OB_STR_003", rationale="Counts midpoint candidates in threshold grid.")]),
        "WS10_B3": _item([_opp("OB_PRO_007", rationale="Midpoint computation in energy dataset.")]),
        "WS10_B4": _item([_opp("OB_PRO_008", rationale="Misclassification count at a threshold row.")]),
        "WS10_B5": _item([_opp("OB_PRO_007", rationale="Selects minimum-MCR optimal threshold."),
                          _opp("OB_STR_003", role="secondary", evidence_mode="direct",
                               rationale="Optimal threshold from error analysis.")]),
        "WS10_B6": _item([_opp("OB_PRO_008", rationale="Open numeric row — count/MCR consistency."),
                          _opp("OB_STR_003", role="secondary", evidence_mode="indirect",
                               rationale="Row arithmetic coherence.")]),
        "WS10_B7": _item([_opp("OB_PRO_008", rationale="Open numeric answer in threshold experiment.")]),
        "WS10_B8": _item([_opp("OB_PRO_007", rationale="Confirms optimal threshold selection."),
                          _opp("OB_STR_001", role="secondary", evidence_mode="direct",
                               rationale="Justification tied to minimum MCR.")]),
    },
    "WS11": {
        "WS11_B8a": _item([_opp("OB_PRO_001", rationale="Classifies instance using peer tree."),
                           _opp("OB_PRO_006", role="secondary", evidence_mode="direct",
                                rationale="Not-recommended label assignment.")]),
        "WS11_B8b": _item([_opp("OB_PRO_009", rationale="States if-then rule for classification path."),
                           _opp("OB_STR_006", role="secondary", evidence_mode="direct",
                                rationale="Conditional rule structure.")]),
        "WS11_B9": _item([_opp("OB_CON_004", rationale="Defines decision tree concept."),
                          _opp("OB_REF_001", role="secondary", evidence_mode="direct",
                               rationale="Reflective definition of model type.")]),
        "WS11_Q10_1": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 1.")]),
        "WS11_Q10_2": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 2.")]),
        "WS11_Q10_3": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 3.")]),
        "WS11_Q10_4": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 4.")]),
        "WS11_Q10_5": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 5.")]),
        "WS11_Q10_6": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 6.")]),
        "WS11_Q10_7": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 7.")]),
        "WS11_Q10_8": _item([_opp("OB_REF_001", rationale="True/false on model purpose statement 8.")]),
        "WS11_Q11_2": _item([_opp("OB_STR_007", rationale="Ordering step 2 in tree-building procedure.")]),
        "WS11_Q11_3": _item([_opp("OB_STR_007", rationale="Ordering step 3 in tree-building procedure.")]),
        "WS11_Q11_4": _item([_opp("OB_STR_007", rationale="Ordering step 4 in tree-building procedure.")]),
        "WS11_Q12_1": _item([_opp("OB_REF_003", rationale="Multiselect: identifies valid tree-building actions.")]),
        "WS11_Q12_2": _item([_opp("OB_REF_003", rationale="Multiselect: identifies valid tree-building actions.")]),
        "WS11_Q12_3": _item([_opp("OB_REF_003", rationale="Multiselect: identifies valid tree-building actions.")]),
        "WS11_Q12_4": _item([_opp("OB_REF_003", rationale="Multiselect: identifies valid tree-building actions.")]),
        "WS11_Q12_5": _item([_opp("OB_REF_003", rationale="Multiselect: identifies valid tree-building actions.")]),
    },
}


VALIDITY_NOTES: dict[str, dict[str, Any]] = {
    "WS1": {
        "construct_threats": [
            "Terminology recall may conflate vocabulary with procedural competence.",
            "Formula items (B8, B9) test recall, not application to a dataset.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "No authentic data manipulation; definitions only.",
            "Turkish/English synonym acceptance required for fair OCR scoring.",
        ],
        "cross_worksheet_dependencies": [],
    },
    "WS3": {
        "construct_threats": [
            "Part 1 applies a fixed peer rule; does not test independent rule invention.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "B7/B8 threshold values are student-chosen; no single numeric key.",
        ],
        "cross_worksheet_dependencies": [],
    },
    "WS4": {
        "construct_threats": [
            "Visual circle task is not text-extractable; omitted from OCR pipeline.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "B1 may have multiple tied optimal thresholds.",
            "B3 requires comparative reasoning, not a single numeric answer.",
        ],
        "cross_worksheet_dependencies": [],
    },
    "WS5": {
        "construct_threats": [
            "Grid filling is procedural; partial credit on operator errors may mask conceptual gaps.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "Row-level scoring aggregates four cells; cell-level evidence is not separately scored.",
            "Dataset size N=10 is fixed in rubric metadata.",
        ],
        "cross_worksheet_dependencies": [],
    },
    "WS6": {
        "construct_threats": [
            "Drawn tree quality depends on OCR field capture fidelity.",
            "Holistic tree_structure item may double-count leaf/threshold errors.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "13 OCR fields may not capture full spatial tree layout.",
        ],
        "cross_worksheet_dependencies": [
            {"depends_on": "WS7", "reason": "WS7 rules are graded for consistency with this tree."},
        ],
    },
    "WS7": {
        "construct_threats": [
            "Part 1 path matching uses a fixed sample tree, not the student's WS6 tree.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "B4–B7 marked not_applicable when tree has only three leaf paths.",
        ],
        "cross_worksheet_dependencies": [
            {"depends_on": "WS6", "reason": "B1–B3 rules must be consistent with student's WS6 tree."},
        ],
    },
    "WS10": {
        "construct_threats": [
            "Numeric table region may be blocked if OCR fails to capture grid.",
        ],
        "leakage_risks": [],
        "evidence_limitations": [
            "B6/B7 are open numeric responses with consistency checks only.",
            "Optimal threshold 408 is dataset-specific.",
        ],
        "cross_worksheet_dependencies": [],
    },
    "WS11": {
        "construct_threats": [
            "Reflection and Likert items are descriptive_only; must not infer competence.",
        ],
        "leakage_risks": [
            "Demographic items (L12) must never enter behaviour or ILO inference.",
        ],
        "evidence_limitations": [
            "Only cognitive scored items (B8a, B8b, B9, Q10, Q11, Q12) produce behaviour evidence.",
        ],
        "cross_worksheet_dependencies": [],
        "descriptive_only_items": [
            "WS11_B1", "WS11_B2", "WS11_B3", "WS11_B4", "WS11_B5", "WS11_B6", "WS11_B7",
            "WS11_L10", "WS11_L11", "WS11_L12",
        ],
    },
    "WS2": {
        "construct_threats": [],
        "leakage_risks": [],
        "evidence_limitations": [
            "WS2 is not present in the ProDaBi unplugged worksheet corpus (v1).",
            "Bundle scaffold reserved for future curriculum alignment.",
        ],
        "cross_worksheet_dependencies": [],
        "note": "curriculum_status=not_deployed",
    },
    "WS8": {
        "construct_threats": [],
        "leakage_risks": [],
        "evidence_limitations": [
            "WS8 is not present in the ProDaBi unplugged worksheet corpus (v1).",
            "Bundle scaffold reserved for future curriculum alignment.",
        ],
        "cross_worksheet_dependencies": [],
        "note": "curriculum_status=not_deployed",
    },
    "WS9": {
        "construct_threats": [],
        "leakage_risks": [],
        "evidence_limitations": [
            "WS9 is not present in the ProDaBi unplugged worksheet corpus (v1).",
            "Bundle scaffold reserved for future curriculum alignment.",
        ],
        "cross_worksheet_dependencies": [],
        "note": "curriculum_status=not_deployed",
    },
}


EXTRACTION_NOTES: dict[str, str] = {
    "WS1": "Eleven free-text definition fields (WS1_B1–B11).",
    "WS3": "Eight response fields; B7/B8 are threshold expressions.",
    "WS4": "Five text fields; visual circle task excluded from extraction.",
    "WS5": "Twenty-five table cells (B1–B25) plus six aggregate row keys.",
    "WS6": "Thirteen structured tree fields (WS6_B1–B13).",
    "WS7": "Three path-match boxes (P1) plus up to three rule fields (B1–B3).",
    "WS10": "Eight numeric/table fields; blocked if table region missing.",
    "WS11": "Mixed reflection, cognitive, and descriptive fields; score only cognitive subset.",
}
