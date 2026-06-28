#!/usr/bin/env python3
"""
Build performance-based AI-CFT assessment framework artifacts (schema 2.0).

Writes:
  mappings/AICFT_assessment_framework.json  — canonical framework
  mappings/AICFT_LO_definitions.json        — competency-centric index
  mappings/<WS>_AICFT_mapping.json          — per-worksheet scorer views
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
MAPPINGS = REPO / "mappings"
FRAMEWORK_VERSION = "2.0"

WORKSHEET_PROFILES: dict[str, dict[str, str]] = {
    "WS1": {"Acquire": "primary", "Deepen": "none", "Create": "none"},
    "WS3": {"Acquire": "supporting", "Deepen": "primary", "Create": "none"},
    "WS4": {"Acquire": "none", "Deepen": "primary", "Create": "none"},
    "WS5": {"Acquire": "none", "Deepen": "primary", "Create": "none"},
    "WS6": {"Acquire": "none", "Deepen": "primary", "Create": "none"},
    "WS7": {"Acquire": "none", "Deepen": "primary", "Create": "none"},
    "WS10": {"Acquire": "none", "Deepen": "primary", "Create": "none"},
    "WS11": {"Acquire": "supporting", "Deepen": "primary", "Create": "none"},
    "WS_DT": {"Acquire": "supporting", "Deepen": "primary", "Create": "supporting"},
}

COMPETENCY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "LO3.1.1": {
        "title": "Basic AI techniques and applications — conceptual knowledge",
        "expected_level": "Acquire",
        "scope": (
            "Foundational vocabulary and concepts only: object, feature, label, dataset, "
            "decision, threshold, basic ML terminology. Recall and explain — not tool operation."
        ),
        "unesco_reference": "Aspect 3, Acquire — foundational conceptual knowledge of AI systems.",
        "primary_evidence": [
            "WS1 (definitions and terminology)",
            "DT Section E (sensitivity/MCR formulas as conceptual metrics)",
        ],
    },
    "LO3.1.2": {
        "title": "How AI works — foundational understanding",
        "expected_level": "Acquire",
        "scope": (
            "Explains what decision trees do, why data is needed, and distinguishes AI from "
            "non-AI approaches at a conceptual level."
        ),
        "unesco_reference": "Aspect 3, Acquire — understanding of how AI systems work.",
        "primary_evidence": [
            "WS11 Q9, Q10, Q12 (conceptual explanation items)",
        ],
    },
    "LO3.1.3": {
        "title": "Validated AI tool selection",
        "expected_level": "Acquire",
        "scope": (
            "Locates, validates, and selects appropriate AI tools (e.g. CODAP, Arbor, EMIT) "
            "for an educational data-analysis task."
        ),
        "unesco_reference": "Aspect 3, Acquire — locate and evaluate AI tools for educational use.",
        "primary_evidence": [
            "DT Section B (tool selection and setup)",
        ],
    },
    "LO3.2.1": {
        "title": "Evaluate → select → apply AI tools in educational context",
        "expected_level": "Deepen",
        "scope": (
            "Demonstrates evaluate → select → apply cycle: choose variables, build multiple "
            "models/trees, compare performance — not threshold arithmetic alone."
        ),
        "unesco_reference": "Aspect 3, Deepen — operate and apply AI tools in educational contexts.",
        "primary_evidence": [
            "DT Section B (three variables, three trees, performance comparison)",
        ],
    },
    "LO3.2.2": {
        "title": "Application skills — model behaviour and threshold reasoning",
        "expected_level": "Deepen",
        "scope": (
            "Apply, interpret, compare, justify: threshold application and optimization, "
            "decision-tree construction/representation, rule articulation, model behaviour."
        ),
        "unesco_reference": (
            "Aspect 3, Deepen — Application Skills: explain model behaviour, interpret results, "
            "evaluate parameters, select appropriate approaches."
        ),
        "primary_evidence": [
            "WS3 (threshold application)",
            "WS4 (best threshold search and justification)",
            "WS6 (decision tree construction and representation)",
            "WS7 (decision rules → natural language)",
            "WS10 (threshold optimization)",
            "WS11 Q8 (applied interpretation)",
        ],
    },
    "LO3.2.3": {
        "title": "Problem solving — iterative performance improvement",
        "expected_level": "Deepen",
        "scope": (
            "Real problem solving with iterative refinement: optimize thresholds, build "
            "multi-level trees, evaluate on test data, improve performance."
        ),
        "unesco_reference": "Aspect 3, Deepen — apply transferable knowledge to solve real problems.",
        "primary_evidence": [
            "DT Sections C–F (optimization, two-level tree, evaluation, test data)",
            "WS5 (parameter exploration — supporting evidence)",
        ],
    },
    "LO3.3.1": {
        "title": "Create — adapt AI-supported solutions",
        "expected_level": "Create",
        "scope": "Early indicators of designing or adapting AI-supported educational solutions.",
        "unesco_reference": "Aspect 3, Create — design and adapt AI-supported solutions.",
        "primary_evidence": [
            "DT Section F (weak Create indicator)",
        ],
    },
}


def comp(
    lo: str,
    strength: str,
    evidence_type: str,
    expected_level: str,
    rationale: str,
    *,
    role: str = "primary",
    portfolio_weight: str = "full",
) -> dict[str, Any]:
    return {
        "lo": lo,
        "strength": strength,
        "evidence_type": evidence_type,
        "expected_level": expected_level,
        "rationale": rationale,
        "role": role,
        "portfolio_weight": portfolio_weight,
    }


def ws1_mappings() -> dict[str, list[dict[str, Any]]]:
    base = "Learner recalls or explains foundational supervised-learning vocabulary."
    items = {}
    for bid in [f"WS1_B{i}" for i in range(1, 12)]:
        strength = "moderate" if bid == "WS1_B10" else "strong"
        items[bid] = [comp(
            "LO3.1.1", strength, "direct", "Acquire",
            f"{base} Item targets core terminology (object, feature, label, threshold, rule, "
            f"confusion-matrix terms, or decision-tree structure).",
        )]
    return items


def ws3_mappings() -> dict[str, list[dict[str, Any]]]:
    items = {}
    for bid in [f"WS3_B{i}" for i in range(1, 7)]:
        items[bid] = [comp(
            "LO3.2.2", "moderate", "direct", "Deepen",
            "Applies threshold values to classify items — demonstrates parameter application "
            "and interpretation of model decisions.",
        )]
    for bid in ("WS3_B7", "WS3_B8"):
        items[bid] = [comp(
            "LO3.2.2", "strong", "direct", "Deepen",
            "Applies and justifies threshold choices in a spreadsheet/tool context — "
            "requires evaluating trade-offs between sensitivity and misclassification.",
        )]
    return items


def ws4_mappings() -> dict[str, list[dict[str, Any]]]:
    return {
        f"WS4_B{i}": [comp(
            "LO3.2.2", "strong", "direct", "Deepen",
            "Searches, tests, or justifies threshold values — evaluates model behaviour "
            "and selects parameters based on performance evidence.",
        )]
        for i in range(1, 6)
    }


def ws5_mappings() -> dict[str, list[dict[str, Any]]]:
    items = {
        f"WS5_row{i}": [comp(
            "LO3.2.3", "moderate", "supporting", "Deepen",
            "Explores how parameter combinations (TP/FP/FN counts) affect MCR — "
            "iterative performance reasoning; supporting evidence for problem solving.",
            role="supporting",
        )]
        for i in range(1, 6)
    }
    items["WS5_B25"] = [
        comp(
            "LO3.2.3", "moderate", "direct", "Deepen",
            "Synthesizes row-level exploration into a justified parameter choice — "
            "demonstrates iterative refinement of model performance.",
        ),
        comp(
            "LO3.2.2", "weak", "supporting", "Deepen",
            "Interprets numeric relationships among confusion-matrix cells.",
            role="supporting",
        ),
    ]
    return items


def ws6_mappings() -> dict[str, list[dict[str, Any]]]:
    tree_items = {
        "WS6_tree_structure": ("strong", "direct", "Constructs or represents a complete decision tree from data."),
        "WS6_root_feature": ("moderate", "supporting", "Selects root split feature — model structure decision."),
        "WS6_root_threshold": ("moderate", "supporting", "Sets root threshold — parameter evaluation."),
        "WS6_inner_feature": ("moderate", "supporting", "Selects inner-node feature for tree refinement."),
        "WS6_inner_threshold": ("moderate", "supporting", "Sets inner-node threshold."),
        "WS6_root_labels": ("weak", "supporting", "Assigns class labels at root branches."),
        "WS6_inner_labels": ("weak", "supporting", "Assigns class labels at inner branches."),
        "WS6_leaves": ("weak", "supporting", "Specifies leaf outcomes completing tree representation."),
    }
    return {
        k: [comp("LO3.2.2", s, et, "Deepen", f"Decision-tree worksheet: {r}", role="primary" if s == "strong" else "supporting")]
        for k, (s, et, r) in tree_items.items()
    }


def ws7_mappings() -> dict[str, list[dict[str, Any]]]:
    items = {}
    for iid in ("WS7_P1_box1", "WS7_P1_box2", "WS7_P1_box3", "WS7_B1", "WS7_B2", "WS7_B3"):
        items[iid] = [comp(
            "LO3.2.2", "strong", "direct", "Deepen",
            "Matches or articulates decision rules in natural language — interprets model "
            "logic and path conditions demonstrated by the learner.",
        )]
    return items


def ws10_mappings() -> dict[str, list[dict[str, Any]]]:
    return {
        f"WS10_B{i}": [comp(
            "LO3.2.2", "strong", "direct", "Deepen",
            "Optimizes or evaluates threshold performance across numeric table rows — "
            "demonstrates parameter tuning and result interpretation.",
        )]
        for i in range(1, 9)
    }


def ws11_mappings() -> dict[str, list[dict[str, Any]]]:
    items: dict[str, list[dict[str, Any]]] = {}
    items["WS11_B8a"] = [comp(
        "LO3.2.2", "moderate", "direct", "Deepen",
        "Interprets model output or feedback in applied context (Q8 cluster).",
    )]
    items["WS11_B8b"] = [comp(
        "LO3.2.2", "strong", "direct", "Deepen",
        "Explains or justifies model behaviour from worksheet feedback (Q8).",
    )]
    items["WS11_B9"] = [comp(
        "LO3.1.2", "strong", "direct", "Acquire",
        "Explains foundational AI concept (why data / how models learn).",
    )]
    for i in range(1, 9):
        items[f"WS11_Q10_{i}"] = [comp(
            "LO3.1.2", "strong", "direct", "Acquire",
            "Conceptual explanation of AI/decision-tree behaviour (Q10).",
        )]
    for i in (2, 3, 4):
        items[f"WS11_Q11_{i}"] = [
            comp(
                "LO3.1.2", "moderate", "direct", "Acquire",
                "Orders procedural steps in decision-tree construction "
                "(select feature → arrange by dimension → find threshold → decide). "
                "Demonstrates workflow understanding, not vocabulary recall alone.",
            ),
            comp(
                "LO3.2.2", "weak", "supporting", "Deepen",
                "Connects ordered steps to applied model-building pipeline (Q11).",
                role="supporting",
            ),
        ]
    for i in range(1, 6):
        items[f"WS11_Q12_{i}"] = [comp(
            "LO3.1.2", "strong", "direct", "Acquire",
            "Explains what AI/decision trees do and why data matters (Q12).",
        )]
    return items


def ws_dt_mappings() -> dict[str, list[dict[str, Any]]]:
    items: dict[str, list[dict[str, Any]]] = {}

    items["DT_A_Q1"] = [comp(
        "LO3.1.1", "weak", "prior_belief", "Acquire",
        "Uninformed prior belief: names predictive feature(s) before CODAP analysis. "
        "Baseline diagnostic only — excluded from portfolio peak aggregation.",
        portfolio_weight="baseline",
    )]
    items["DT_A_Q2"] = [
        comp(
            "LO3.2.2", "moderate", "direct", "Deepen",
            "After CODAP exploration: names a feature and cites an observed data/graph pattern "
            "(not intuition alone) — early data-interpretation behaviour.",
        ),
        comp(
            "LO3.1.2", "weak", "supporting", "Acquire",
            "Links data exploration to how a model might use that feature.",
            role="supporting",
        ),
    ]
    items["DT_A_Q3"] = [
        comp(
            "LO3.2.2", "moderate", "direct", "Deepen",
            "Identifies a feature showing meaningful separation between recommended "
            "and not-recommended classes from explored data.",
        ),
    ]
    items["DT_A_Q4"] = [
        comp(
            "LO3.2.2", "strong", "direct", "Deepen",
            "Selects first split variable with explicit data-based justification "
            "(graph separation, class distinction) — precursor to model design.",
        ),
        comp(
            "LO3.2.1", "weak", "supporting", "Deepen",
            "Early evaluate→select step before full three-tree comparison in Section B.",
            role="supporting",
        ),
    ]

    items["DT_B_Q1"] = [comp(
        "LO3.1.3", "strong", "direct", "Acquire",
        "Selects and validates an appropriate AI tool (CODAP, Arbor, or EMIT) for the task.",
    )]
    for q in ("DT_B_Q2", "DT_B_Q3"):
        items[q] = [comp(
            "LO3.2.1", "moderate", "direct", "Deepen",
            "Builds decision trees with different variables — evaluate → select → apply cycle.",
        )]
    items["DT_B_Q4"] = [comp(
        "LO3.2.1", "strong", "direct", "Deepen",
        "Compares performance across three trees/variables — full evaluate-select-apply evidence.",
    )]

    for q in ("DT_C_Q1", "DT_C_Q2", "DT_C_Q3"):
        items[q] = [comp(
            "LO3.2.3", "strong", "direct", "Deepen",
            "Iterative threshold optimization on real data (Section C).",
        )]

    for q in ("DT_D_Q1", "DT_D_Q2", "DT_D_Q3", "DT_D_Q4"):
        items[q] = [comp(
            "LO3.2.3", "strong", "direct", "Deepen",
            "Constructs or refines a two-level decision tree — problem solving with model design.",
        )]

    items["DT_E_sensitivity"] = [comp(
        "LO3.1.1", "moderate", "direct", "Acquire",
        "Computes or states sensitivity formula — conceptual metric knowledge.",
    )]
    items["DT_E_MCR"] = [comp(
        "LO3.1.1", "moderate", "direct", "Acquire",
        "Computes or states MCR formula — conceptual metric knowledge.",
    )]
    for q in ("DT_E_Q1", "DT_E_Q2", "DT_E_Q3"):
        items[q] = [comp(
            "LO3.2.3", "strong", "direct", "Deepen",
            "Evaluates model performance and interprets confusion-matrix outcomes (Section E).",
        )]
    items["DT_E_Q4"] = [
        comp(
            "LO3.2.3", "strong", "direct", "Deepen",
            "Synthesizes evaluation into performance improvement decisions.",
        ),
        comp(
            "LO3.3.1", "weak", "supporting", "Create",
            "Early indicator of adapting model design based on evaluation.",
            role="supporting",
        ),
    ]

    items["DT_F_Q1"] = [comp(
        "LO3.2.3", "strong", "direct", "Deepen",
        "Applies model to test/holdout data — validates generalization.",
    )]
    items["DT_F_Q2"] = [
        comp(
            "LO3.2.3", "strong", "direct", "Deepen",
            "Interprets test-set results and proposes iterative improvements.",
        ),
        comp(
            "LO3.3.1", "weak", "supporting", "Create",
            "Weak Create indicator — adapts solution based on test evidence.",
            role="supporting",
        ),
    ]

    items["DT_G_Q1"] = [comp(
        "LO3.1.1", "weak", "reflective", "Acquire",
        "Metacognitive reflection on conceptual learning — portfolio diagnostic only.",
        role="supporting",
        portfolio_weight="diagnostic",
    )]
    items["DT_G_Q2"] = [comp(
        "LO3.2.2", "weak", "reflective", "Deepen",
        "Reflective summary of applied understanding — portfolio diagnostic only.",
        role="supporting",
        portfolio_weight="diagnostic",
    )]
    return items


ALL_WORKSHEET_ITEMS: dict[str, dict[str, list[dict[str, Any]]]] = {
    "WS1": ws1_mappings(),
    "WS3": ws3_mappings(),
    "WS4": ws4_mappings(),
    "WS5": ws5_mappings(),
    "WS6": ws6_mappings(),
    "WS7": ws7_mappings(),
    "WS10": ws10_mappings(),
    "WS11": ws11_mappings(),
    "WS_DT": ws_dt_mappings(),
}


EDGE_CASES: dict[str, Any] = {
    "WS11_Q11": {
        "section": "Q11 — decision tree construction step ordering",
        "items": ["WS11_Q11_2", "WS11_Q11_3", "WS11_Q11_4"],
        "guidance": (
            "Step 1 is pre-filled on the worksheet. Scored sub-items test procedural "
            "understanding of the DT workflow (LO3.1.2), not vocabulary recall (LO3.1.1)."
        ),
    },
    "DT_Section_A": {
        "section": "Section A — prior beliefs and first CODAP exploration",
        "items": ["DT_A_Q1", "DT_A_Q2", "DT_A_Q3", "DT_A_Q4"],
        "guidance": (
            "DT_A_Q1 is uninformed prior belief (portfolio_weight=baseline, excluded from peaks). "
            "DT_A_Q2–Q4 involve CODAP-guided interpretation and count toward LO3.2.2."
        ),
    },
    "DT_Section_G": {
        "section": "Section G — metacognitive reflection",
        "items": ["DT_G_Q1", "DT_G_Q2"],
        "guidance": (
            "Reflective items use portfolio_weight=diagnostic; they inform the researcher "
            "but do not drive AI-CFT level proposals."
        ),
    },
}


def build_framework() -> dict[str, Any]:
    items_flat: list[dict[str, Any]] = []
    for worksheet, item_map in ALL_WORKSHEET_ITEMS.items():
        for item_id, competencies in item_map.items():
            items_flat.append({
                "worksheet": worksheet,
                "item": item_id,
                "competencies": competencies,
            })

    return {
        "schema_version": FRAMEWORK_VERSION,
        "framework": "UNESCO AI Competency Framework for Teachers (AI-CFT) 2024",
        "aspect": "Aspect 3: AI foundations and applications",
        "design_principles": [
            "Competencies are inferred from observable learner performance, not worksheet identity.",
            "A single item may provide primary and supporting competency evidence.",
            "Evidence accumulates across worksheets; no single worksheet proves mastery.",
            "Mappings include rationale, strength ceiling, and evidence type for each competency.",
        ],
        "competency_levels": {
            "Acquire": "Identify, recall, recognize, explain basic concepts.",
            "Deepen": "Apply, evaluate, compare, select, justify, interpret, integrate, optimize.",
            "Create": "Design, adapt, customize, innovate AI-supported solutions.",
        },
        "worksheet_profiles": WORKSHEET_PROFILES,
        "competency_definitions": COMPETENCY_DEFINITIONS,
        "edge_cases": EDGE_CASES,
        "portfolio_aggregation": {
            "peak_includes": "competencies with portfolio_weight=full and evidence_type not prior_belief",
            "peak_excludes": "portfolio_weight baseline|diagnostic, evidence_type prior_belief|reflective (diagnostic only)",
        },
        "items": items_flat,
    }


def build_lo_definitions(framework: dict[str, Any]) -> dict[str, Any]:
  """Invert item-centric framework into competency-centric index."""
  by_lo: dict[str, list[dict[str, Any]]] = {lo: [] for lo in COMPETENCY_DEFINITIONS}
  for entry in framework["items"]:
      ws, item = entry["worksheet"], entry["item"]
      for cdef in entry["competencies"]:
          by_lo[cdef["lo"]].append({
              "worksheet": ws,
              "item": item,
              "evidence_type": cdef["evidence_type"],
              "strength": cdef["strength"],
              "expected_level": cdef["expected_level"],
              "rationale": cdef["rationale"],
              "role": cdef.get("role", "primary"),
              "portfolio_weight": cdef.get("portfolio_weight", "full"),
          })

  levels: dict[str, Any] = {}
  for level_name in ("Acquire", "Deepen", "Create"):
      los = {
          lo: {
              **COMPETENCY_DEFINITIONS[lo],
              "worksheet_evidence": sorted(
                  by_lo.get(lo, []),
                  key=lambda e: (e["worksheet"], e["item"]),
              ),
          }
          for lo in COMPETENCY_DEFINITIONS
          if COMPETENCY_DEFINITIONS[lo]["expected_level"] == level_name
          or (level_name == "Create" and lo == "LO3.3.1")
      }
      if level_name == "Acquire":
          los = {k: v for k, v in los.items() if v["expected_level"] == "Acquire"}
      elif level_name == "Deepen":
          los = {k: v for k, v in los.items() if v["expected_level"] == "Deepen"}
      elif level_name == "Create":
          los = {k: v for k, v in los.items() if k == "LO3.3.1"}
      levels[level_name] = {
          "level_description": framework["competency_levels"][level_name],
          "learning_objects": los,
      }

  return {
      "schema_version": FRAMEWORK_VERSION,
      "framework": framework["framework"],
      "aspect": framework["aspect"],
      "note": (
          "LO = Learning Object (AI-CFT competency). Performance-based assessment index "
          "derived from AICFT_assessment_framework.json. Evidence is observable behaviour, "
          "not worksheet-to-LO mechanical tagging."
      ),
      "levels": levels,
  }


def write_worksheet_mappings(framework: dict[str, Any]) -> None:
    by_ws: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for entry in framework["items"]:
        by_ws.setdefault(entry["worksheet"], {})[entry["item"]] = entry["competencies"]

    for worksheet, items in by_ws.items():
        out = {
            "schema_version": FRAMEWORK_VERSION,
            "worksheet": worksheet,
            "framework": framework["framework"],
            "note": (
                "Performance-based competency mapping. Strength is a ceiling on observed "
                "evidence_strength. Scorer must add item-specific rationale and confidence."
            ),
            "items": items,
        }
        path = MAPPINGS / f"{worksheet}_AICFT_mapping.json"
        path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    framework = build_framework()
    lo_defs = build_lo_definitions(framework)

    (MAPPINGS / "AICFT_assessment_framework.json").write_text(
        json.dumps(framework, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    (MAPPINGS / "AICFT_LO_definitions.json").write_text(
        json.dumps(lo_defs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
    )
    write_worksheet_mappings(framework)
    print(f"Wrote framework v{FRAMEWORK_VERSION}: {len(framework['items'])} items across {len(ALL_WORKSHEET_ITEMS)} worksheets")


if __name__ == "__main__":
    main()
