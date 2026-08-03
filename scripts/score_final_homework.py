#!/usr/bin/env python3
"""Score Final Ödevi Dokümanları (.ipynb) against the colab_rubric B1-B17 behaviors.

Each notebook is parsed directly (no OCR needed — we have the actual source).
Deterministic rules are applied for B1-B13, B15-B16, B17.
B14 (output interpretation) is scored from markdown written-answer cells via Claude API.

Usage:
    python scripts/score_final_homework.py                        # all notebooks
    python scripts/score_final_homework.py Amy Bruno              # specific students
    python scripts/score_final_homework.py --dry-run              # no API calls
    python scripts/score_final_homework.py --no-llm               # skip B14 LLM scoring

Outputs per student:
    data_sources_2026/Final Ödevi Dokümanları/{ID}_homework_score.json

Cohort summary:
    data_sources_2026/Final Ödevi Dokümanları/cohort_homework_summary.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
HW_DIR    = REPO_ROOT / "data_sources_2026" / "Final Ödevi Dokümanları"
SCORE_DIR = REPO_ROOT / "data_sources_2026" / "homework_scores"
RUBRIC    = REPO_ROOT / "trash" / "scoring_out_of_scope_2026-07-20" / "calibration" / "colab_rubric.json"

LOGGER = logging.getLogger("score_final_homework")


# ─────────────────────────────────────────────────────────────
# Notebook parsing
# ─────────────────────────────────────────────────────────────

def load_notebook(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def extract_cells(nb: dict) -> list[dict[str, Any]]:
    """Return list of {type, source, outputs, has_error, output_text, has_display}."""
    result = []
    for cell in nb.get("cells", []):
        ctype = cell.get("cell_type", "")
        source = "".join(cell.get("source", []))
        outputs = cell.get("outputs", [])
        has_error = any(o.get("output_type") == "error" for o in outputs)
        output_text = "\n".join(
            "".join(o.get("text", []))
            for o in outputs
            if o.get("text")
        )
        # Also capture execute_result text
        for o in outputs:
            if o.get("output_type") == "execute_result":
                d = o.get("data", {})
                txt = "".join(d.get("text/plain", []))
                output_text += "\n" + txt
        has_display = any(
            o.get("output_type") in ("display_data", "execute_result")
            and "image/png" in o.get("data", {})
            for o in outputs
        )
        result.append({
            "type": ctype,
            "source": source,
            "outputs": outputs,
            "has_error": has_error,
            "output_text": output_text.strip(),
            "has_display": has_display,
        })
    return result


def all_code_source(cells: list[dict]) -> str:
    return "\n".join(c["source"] for c in cells if c["type"] == "code")


def all_code_output(cells: list[dict]) -> str:
    return "\n".join(c["output_text"] for c in cells if c["type"] == "code")


def all_markdown(cells: list[dict]) -> str:
    return "\n".join(c["source"] for c in cells if c["type"] == "markdown")


def cell_ran_successfully(cell: dict) -> bool:
    """True if code cell produced output or has outputs without error."""
    return not cell["has_error"] and bool(cell["outputs"])


# ─────────────────────────────────────────────────────────────
# Deterministic behavior detection (B1-B13, B15-B17)
# ─────────────────────────────────────────────────────────────

def detect_behaviors(cells: list[dict]) -> dict[str, dict]:
    """Apply rubric evidence rules directly on notebook content."""

    code_src = all_code_source(cells)
    code_out = all_code_output(cells)
    md_text  = all_markdown(cells)
    all_text = code_src + "\n" + code_out + "\n" + md_text

    results: dict[str, dict] = {}

    def hit(behavior_id: str, triggered: bool, evidence: str) -> None:
        results[behavior_id] = {"triggered": triggered, "evidence": evidence}

    # B1 — Library import
    imports = re.findall(r"^(import\s+\S+|from\s+\S+\s+import\s+\S+)", code_src, re.MULTILINE)
    hit("B1", bool(imports), f"Found imports: {imports[:5]}" if imports else "No import statements found")

    # B2 — Data loading
    load_fns = re.findall(r"pd\.read_(?:csv|excel|json|parquet|table)\([^)]*\)", code_src)
    has_df_assign = bool(re.search(r"\bdf\s*=", code_src))
    hit("B2", bool(load_fns) or has_df_assign,
        f"load calls: {load_fns[:2]}" if load_fns else ("DataFrame assignment found" if has_df_assign else "No data loading found"))

    # B3 — Data exploration
    explore_fns = re.findall(r"\.(head|tail|info|describe|shape|value_counts|dtypes|nunique)\b", code_src)
    # At least one must have output
    explore_cells = [c for c in cells if c["type"] == "code"
                     and re.search(r"\.(head|tail|info|describe|shape|value_counts|dtypes)\b", c["source"])
                     and c["output_text"]]
    hit("B3", bool(explore_cells),
        f"Exploration functions with output: {explore_fns[:4]}" if explore_cells else "No executed exploration functions found")

    # B4 — Data cleaning (dropna / fillna / isnull / replace)
    clean_fns = re.findall(r"\.(dropna|fillna|isnull|notnull|replace)\(", code_src)
    # Also check for filter conditions
    filter_expr = re.findall(r"df\[df\[", code_src)
    hit("B4", bool(clean_fns) or bool(filter_expr),
        f"Cleaning ops: {clean_fns[:3]}" if clean_fns else (
            "Filter expression found" if filter_expr else "No data cleaning detected"))

    # B5 — X, y split
    x_assign = bool(re.search(r"\bX\s*=\s*df\[|X\s*=\s*pd\.get_dummies|X_\w+\s*=", code_src))
    y_assign = bool(re.search(r"\by\s*=\s*df\[|\by\s*=\s*df\.", code_src))
    hit("B5", x_assign and y_assign,
        "X and y assignments found" if (x_assign and y_assign) else
        f"X={x_assign}, y={y_assign}")

    # B6 — train_test_split
    tts = re.findall(r"train_test_split\([^)]*\)", code_src)
    tts_cells = [c for c in cells if c["type"] == "code" and "train_test_split" in c["source"]]
    hit("B6", bool(tts), f"train_test_split call found: {tts[0][:60]!r}" if tts else "No train_test_split found")

    # B7_lo32 — at least one hyperparameter explicitly set in DTC
    hp_patterns = r"(?:max_depth|min_samples_split|min_samples_leaf|criterion|max_features)\s*="
    dtc_calls   = re.findall(r"DecisionTreeClassifier\([^)]*\)", code_src, re.DOTALL)
    dtc_with_hp = [c for c in dtc_calls if re.search(hp_patterns, c)]
    hit("B7_lo32", bool(dtc_with_hp),
        f"DTC with explicit hyperparams: {dtc_with_hp[0][:80]!r}" if dtc_with_hp else
        "DecisionTreeClassifier called without explicit hyperparameters")

    # B7_lo33 — multiple models with different hyperparameter values (loop or repeated calls)
    depth_values = re.findall(r"max_depth\s*=\s*(\d+)", code_src)
    has_depth_loop = bool(re.search(r"for\s+\w+\s+in\s+(?:range|derinlikler|depths)", code_src))
    has_grid_search = "GridSearchCV" in code_src
    unique_depths = set(depth_values)
    hit("B7_lo33", (len(unique_depths) > 1) or has_depth_loop or has_grid_search,
        f"Multiple depth values: {sorted(unique_depths)}" if len(unique_depths) > 1 else
        ("Depth loop found" if has_depth_loop else
         ("GridSearchCV found" if has_grid_search else "Only single depth value used")))

    # B8 — single-level tree (max_depth=1)
    depth1 = bool(re.search(r"max_depth\s*=\s*1\b", code_src))
    hit("B8", depth1, "max_depth=1 found" if depth1 else "No max_depth=1 found")

    # B9 — multi-level tree (max_depth >= 2 or no max_depth)
    depth_multi = bool(re.search(r"max_depth\s*=\s*[2-9]\d*", code_src))
    no_depth    = bool(re.search(r"DecisionTreeClassifier\(\s*\)", code_src))
    hit("B9", depth_multi or no_depth,
        f"max_depth >= 2 found" if depth_multi else
        ("Unconstrained DTC found" if no_depth else "No multi-level tree found"))

    # B10 — optimal depth search (loop over depths or repeated model+metric)
    hit("B10", has_depth_loop or has_grid_search,
        "Depth loop / grid search found" if (has_depth_loop or has_grid_search) else
        "No systematic depth search found")

    # B11 — model.fit
    fit_calls = re.findall(r"\w+\.fit\(\s*X_\w+\s*,\s*y_\w+\s*\)", code_src)
    fit_cells = [c for c in cells if c["type"] == "code" and ".fit(" in c["source"] and not c["has_error"]]
    hit("B11", bool(fit_cells), f"fit calls found: {fit_calls[:2]}" if fit_calls else "No .fit() calls found")

    # B12 — model.predict / predict_proba
    pred_calls = re.findall(r"\w+\.predict(?:_proba)?\(\s*X_\w+\s*\)", code_src)
    hit("B12", bool(pred_calls), f"predict calls: {pred_calls[:2]}" if pred_calls else "No .predict() calls found")

    # B13 — metric computation with output
    metric_patterns = r"accuracy_score|confusion_matrix|classification_report|f1_score|precision_score|recall_score"
    metric_cells = [c for c in cells if c["type"] == "code"
                    and re.search(metric_patterns, c["source"])
                    and c["output_text"]]
    # Also check if MCR/accuracy values appear in outputs
    has_numeric_metric = bool(re.search(r"\b0\.\d{2,}", code_out))
    hit("B13", bool(metric_cells) or has_numeric_metric,
        f"Metric functions with output: {len(metric_cells)}" if metric_cells else
        ("Numeric metrics in output" if has_numeric_metric else "No metric computation found"))

    # B14 — output interpretation (written answers in markdown)
    # Look for specific numeric references to accuracy/MCR in markdown
    md_with_metric_ref = re.findall(
        r"(?:0\.\d{2,}|%\s*\d+|\d+\s*%|MCR|doğruluk|accuracy|başarı|hata\s*oran)",
        md_text, re.IGNORECASE
    )
    specific_class_ref = re.findall(
        r"(?:Anolis|Uta|Sceloporus|Yer|Kaya|Ağaç|Erkek|Dişi)\s+(?:sınıfı|türü|yaşam|için)",
        md_text, re.IGNORECASE
    )
    hit("B14", bool(md_with_metric_ref) or bool(specific_class_ref),
        f"Metric references in markdown: {md_with_metric_ref[:3]}" if md_with_metric_ref else
        (f"Class-specific references: {specific_class_ref[:2]}" if specific_class_ref else
         "No specific metric or class references in written answers"))

    # B15_lo31 — error visible in output AND discussed
    error_cells = [c for c in cells if c["type"] == "code" and c["has_error"]]
    error_mentioned_in_md = bool(re.search(r"hata|error|traceback", md_text, re.IGNORECASE))
    hit("B15_lo31", bool(error_cells) and error_mentioned_in_md,
        f"Error cells: {len(error_cells)}; mentioned in markdown" if (error_cells and error_mentioned_in_md) else
        f"Errors in code: {len(error_cells)}; mentioned in MD: {error_mentioned_in_md}")

    # B15_lo33 — error followed by fix (error cell then successful cell on same pattern)
    fixed = False
    for i, cell in enumerate(cells):
        if cell["type"] == "code" and cell["has_error"]:
            for j in range(i + 1, min(i + 4, len(cells))):
                if cells[j]["type"] == "code" and not cells[j]["has_error"] and cells[j]["output_text"]:
                    fixed = True
                    break
    hit("B15_lo33", fixed,
        "Error→fix→success pattern found" if fixed else "No error recovery pattern found")

    # B16 — tree visualization
    viz_fns = re.findall(r"plot_tree|export_graphviz|dtreeviz", code_src)
    viz_with_output = [c for c in cells if c["type"] == "code"
                       and re.search(r"plot_tree|export_graphviz|dtreeviz", c["source"])
                       and c["has_display"]]
    hit("B16", bool(viz_with_output),
        f"Visualization with output: {len(viz_with_output)} cells" if viz_with_output else
        ("Viz functions found but no display output" if viz_fns else "No tree visualization found"))

    # B17_lo31 — train vs test scores discussed in MD
    both_scores_in_md = bool(re.search(
        r"(?:eğitim|train).*?(?:test|doğruluk)|(?:test).*?(?:eğitim|train).*?(?:fark|ayrıl|over)",
        md_text, re.IGNORECASE | re.DOTALL
    ))
    overfit_keyword = bool(re.search(r"overfitting|aşırı\s*(?:uyum|öğren)|overfit", md_text, re.IGNORECASE))
    hit("B17_lo31", both_scores_in_md or overfit_keyword,
        "Train/test discussion in markdown found" if (both_scores_in_md or overfit_keyword) else
        "No train/test comparison discussion in markdown")

    # B17_lo33 — both train and test scores computed in code
    train_score = bool(re.search(r"score\(X_(?:train|egitim|eg)\b|accuracy_score\(y_(?:train|egitim)", code_src))
    test_score  = bool(re.search(r"score\(X_(?:test)\b|accuracy_score\(y_(?:test)\b", code_src))
    # Also check for paired numeric output (train: X.XX, test: X.XX)
    paired_output = bool(re.search(r"(?:eğitim|train)\w*\s*(?:mcr|accuracy|doğruluk)[^0-9]*0\.\d{2}", code_out, re.IGNORECASE))
    hit("B17_lo33", (train_score and test_score) or paired_output,
        "Both train and test metrics computed" if (train_score and test_score) else
        ("Paired train/test output found" if paired_output else "Only one of train/test metrics found"))

    return results


# ─────────────────────────────────────────────────────────────
# LO summary
# ─────────────────────────────────────────────────────────────

def compute_lo_summary(behaviors: dict[str, dict]) -> dict[str, dict]:
    def triggered(bid: str) -> bool:
        return behaviors.get(bid, {}).get("triggered", False)

    lo31_behaviors = [b for b in ["B3", "B14", "B15_lo31", "B17_lo31"] if triggered(b)]
    lo32_behaviors = [b for b in ["B1", "B2", "B4", "B5", "B6", "B7_lo32", "B8", "B9", "B11", "B12", "B16"] if triggered(b)]
    lo33_behaviors = [b for b in ["B7_lo33", "B10", "B13", "B15_lo33", "B17_lo33"] if triggered(b)]

    return {
        "LO3.1": {
            "status": "Triggered" if lo31_behaviors else "Not Triggered",
            "level": "Create",
            "triggering_behaviors": lo31_behaviors,
        },
        "LO3.2": {
            "status": "Triggered" if lo32_behaviors else "Not Triggered",
            "level": "Create",
            "triggering_behaviors": lo32_behaviors,
        },
        "LO3.3": {
            "status": "Triggered" if lo33_behaviors else "Not Triggered",
            "level": "Create",
            "triggering_behaviors": lo33_behaviors,
        },
    }


# ─────────────────────────────────────────────────────────────
# Extract quantitative results from notebook
# ─────────────────────────────────────────────────────────────

def extract_metrics(cells: list[dict]) -> dict[str, Any]:
    """Pull numeric results: accuracy/MCR values, chosen depths, target variables."""
    code_out = all_code_output(cells)
    code_src = all_code_source(cells)

    # MCR / accuracy values in outputs
    mcr_values = re.findall(r"(?:MCR|hata|Test\s+Hatas[ıi])[^\d]*([0-9]\.[0-9]{2,4})", code_out, re.IGNORECASE)
    acc_values = re.findall(r"(?:[Tt]est\s+(?:Doğruluk|Accuracy)|Test\s+Score)[^\d]*([0-9]\.[0-9]{2,4})", code_out, re.IGNORECASE)
    # Fallback: grab all 0.XXX values from outputs
    all_decimals = re.findall(r"\b(0\.[0-9]{2,4})\b", code_out)

    # Chosen optimum depths
    opt_depths = re.findall(r"(?:optimum_derinlik|optimal_depth|best_depth)[^\d]*(\d+)", code_src, re.IGNORECASE)

    # Target variables
    targets = re.findall(r"hedef_degisken\s*=\s*['\"](\w+)['\"]|y\s*=\s*df\[['\"](\w+)['\"]\]", code_src)
    targets_flat = [t for pair in targets for t in pair if t]

    # Number of trees built
    n_models = len(re.findall(r"DecisionTreeClassifier\(", code_src))

    # Root nodes (from tree interpretations in markdown)
    root_mentions = re.findall(r"kök düğüm\w*\s+(?:de|da|ise)?\s*(\w+)", all_code_output(cells) + all_markdown(cells), re.IGNORECASE)

    return {
        "mcr_values_in_output": mcr_values[:6],
        "accuracy_values_in_output": acc_values[:6],
        "sample_decimal_outputs": list(dict.fromkeys(all_decimals))[:10],
        "optimum_depths_chosen": list(dict.fromkeys(opt_depths)),
        "target_variables": list(dict.fromkeys(targets_flat)),
        "n_decision_trees_built": n_models,
        "root_node_mentions": root_mentions[:4],
    }


# ─────────────────────────────────────────────────────────────
# Written-answer quality (LLM scoring — B14 deep)
# ─────────────────────────────────────────────────────────────

WRITTEN_ANSWER_PROMPT = """You are an expert educational assessor for a machine learning course.

The student completed a Jupyter notebook homework assignment on decision trees using a lizard dataset.
Below are the student's written answers (from markdown cells) in Turkish.

Evaluate the quality of the written explanations across four dimensions, each scored 0-2:
  0 = absent or entirely generic
  1 = present but superficial
  2 = specific, evidence-based, demonstrates understanding

Dimensions:
1. overfitting_understanding: Does the student explain overfitting using train vs test error gap? (not just "hata arttı")
2. depth_selection_reasoning: Does the student justify their chosen max_depth with concrete numerical evidence?
3. variable_interpretation: Does the student explain WHY a specific feature is the root node (biological/domain reasoning)?
4. class_imbalance_awareness: Does the student connect class imbalance to model performance differences?

Respond ONLY with valid JSON. No markdown fences. No other text.
{
  "overfitting_understanding": {"score": 0-2, "evidence": "quote or observation"},
  "depth_selection_reasoning": {"score": 0-2, "evidence": "quote or observation"},
  "variable_interpretation": {"score": 0-2, "evidence": "quote or observation"},
  "class_imbalance_awareness": {"score": 0-2, "evidence": "quote or observation"},
  "total": 0-8,
  "overall_comment": "one sentence"
}

Student written answers:
"""


def score_written_answers_llm(md_text: str, api_key: str) -> dict[str, Any]:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        prompt_text = WRITTEN_ANSWER_PROMPT + md_text[:6000]
        msg = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=800,
            messages=[{"role": "user", "content": prompt_text}],
        )
        raw = msg.content[0].text.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        raw = raw.strip()
        if not raw:
            return {"error": "Empty response from LLM"}
        return json.loads(raw)
    except Exception as exc:
        LOGGER.warning("LLM scoring failed: %s", exc)
        return {"error": str(exc)}


# ─────────────────────────────────────────────────────────────
# Per-student scoring
# ─────────────────────────────────────────────────────────────

def score_student(nb_path: Path, *, api_key: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    student_id = nb_path.stem
    LOGGER.info("[%s] Scoring ...", student_id)

    nb    = load_notebook(nb_path)
    cells = extract_cells(nb)

    behaviors = detect_behaviors(cells)
    lo_summary = compute_lo_summary(behaviors)
    metrics    = extract_metrics(cells)

    n_triggered = sum(1 for b in behaviors.values() if b.get("triggered"))
    n_total     = len(behaviors)

    # Written answer scoring
    md_text = all_markdown(cells)
    written_score: dict[str, Any] = {"skipped": True, "reason": "dry_run or no_llm"}
    if api_key and not dry_run:
        written_score = score_written_answers_llm(md_text, api_key)

    # Notebook health
    code_cells = [c for c in cells if c["type"] == "code"]
    executed   = [c for c in code_cells if c["outputs"]]
    error_cells = [c for c in code_cells if c["has_error"]]

    return {
        "student_id": student_id,
        "scored_at": datetime.now(timezone.utc).isoformat(),
        "notebook_health": {
            "total_cells": len(cells),
            "code_cells": len(code_cells),
            "markdown_cells": len([c for c in cells if c["type"] == "markdown"]),
            "executed_code_cells": len(executed),
            "error_cells": len(error_cells),
            "has_plot_outputs": any(c["has_display"] for c in cells),
        },
        "behaviors": behaviors,
        "behaviors_triggered": n_triggered,
        "behaviors_total": n_total,
        "coverage_pct": round(100 * n_triggered / n_total, 1),
        "learning_outcomes": lo_summary,
        "quantitative_metrics": metrics,
        "written_answer_quality": written_score,
    }


# ─────────────────────────────────────────────────────────────
# Cohort summary
# ─────────────────────────────────────────────────────────────

def build_cohort_summary(scores: list[dict]) -> dict[str, Any]:
    behavior_ids = list(scores[0]["behaviors"].keys()) if scores else []

    behavior_rates = {}
    for bid in behavior_ids:
        triggered_count = sum(1 for s in scores if s["behaviors"].get(bid, {}).get("triggered"))
        behavior_rates[bid] = {
            "triggered_n": triggered_count,
            "triggered_pct": round(100 * triggered_count / len(scores), 1) if scores else 0,
        }

    lo_rates = {}
    for lo in ["LO3.1", "LO3.2", "LO3.3"]:
        n = sum(1 for s in scores if s["learning_outcomes"].get(lo, {}).get("status") == "Triggered")
        lo_rates[lo] = {"triggered_n": n, "triggered_pct": round(100 * n / len(scores), 1) if scores else 0}

    avg_coverage = round(sum(s["coverage_pct"] for s in scores) / len(scores), 1) if scores else 0

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_students": len(scores),
        "students": [s["student_id"] for s in scores],
        "avg_behavior_coverage_pct": avg_coverage,
        "per_student_coverage": {s["student_id"]: s["coverage_pct"] for s in scores},
        "behavior_trigger_rates": behavior_rates,
        "lo_trigger_rates": lo_rates,
    }


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score Final Ödevi notebooks against colab rubric")
    parser.add_argument("students", nargs="*", help="Student IDs (default: all)")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls; detect behaviors only")
    parser.add_argument("--no-llm", action="store_true", help="Skip written-answer LLM scoring")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(message)s",
    )

    api_key: str | None = None
    if not args.dry_run and not args.no_llm:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            LOGGER.warning("ANTHROPIC_API_KEY not set — written-answer LLM scoring will be skipped")

    notebooks = sorted(HW_DIR.glob("*.ipynb"))
    if args.students:
        notebooks = [nb for nb in notebooks if nb.stem in args.students]

    if not notebooks:
        LOGGER.error("No notebooks found under %s", HW_DIR)
        return 1

    SCORE_DIR.mkdir(parents=True, exist_ok=True)
    LOGGER.info("Scoring %d notebook(s) → %s", len(notebooks), SCORE_DIR)

    all_scores: list[dict] = []
    for nb_path in notebooks:
        try:
            result = score_student(nb_path, api_key=api_key, dry_run=args.dry_run)
            out_path = SCORE_DIR / f"{nb_path.stem}_homework_score.json"
            out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            LOGGER.info("[%s] → %s  behaviors=%d/%d (%.0f%%)  LO3.1=%s LO3.2=%s LO3.3=%s",
                        result["student_id"],
                        out_path.name,
                        result["behaviors_triggered"],
                        result["behaviors_total"],
                        result["coverage_pct"],
                        result["learning_outcomes"]["LO3.1"]["status"],
                        result["learning_outcomes"]["LO3.2"]["status"],
                        result["learning_outcomes"]["LO3.3"]["status"],
                        )
            all_scores.append(result)
        except Exception as exc:
            LOGGER.error("[%s] Failed: %s", nb_path.stem, exc, exc_info=True)

    if all_scores:
        summary = build_cohort_summary(all_scores)
        summary_path = SCORE_DIR / "cohort_homework_summary.json"
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("Cohort summary → %s", summary_path.name)
        LOGGER.info("Avg behavior coverage: %.1f%%", summary["avg_behavior_coverage_pct"])

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
