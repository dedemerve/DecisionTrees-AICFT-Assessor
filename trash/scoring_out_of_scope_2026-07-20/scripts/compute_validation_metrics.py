#!/usr/bin/env python3
"""Compute inter-rater reliability between Claude scores and 2025 expert labels.

Metrics per behavior (binary: observed=1 / not_observed=0):
  - Cohen's kappa (κ)
  - Precision, Recall, F1
  - Confusion matrix (TP, FP, FN, TN)

Aggregate:
  - Macro-F1 across all behaviors
  - Weighted-F1 (by positive frequency)

Decision rule:
  - Macro-F1 ≥ 0.80 AND κ ≥ 0.60 → PROCEED to 2026 scoring
  - Otherwise → REFINE prompt (disagreement analysis shown)

Outputs:
  calibration/validation_metrics.json
  Printed report

Usage:
    python scripts/compute_validation_metrics.py
    python scripts/compute_validation_metrics.py --min-f1 0.75
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCORES_FILE = REPO_ROOT / "calibration" / "validation_raw_scores.json"
OUT_FILE = REPO_ROOT / "calibration" / "validation_metrics.json"

ALL_BEHAVIORS = [
    "B0","B1","B2","B3","B4","B5","B6","B7",
    "B8","B9","B10","B11","B12",
    "B15","B16","B17",
]

PROCEED_F1 = 0.80
PROCEED_KAPPA = 0.60


def cohen_kappa(tp: int, fp: int, fn: int, tn: int) -> float:
    n = tp + fp + fn + tn
    if n == 0:
        return 0.0
    p_o = (tp + tn) / n
    p_e = ((tp + fp) * (tp + fn) + (tn + fn) * (tn + fp)) / (n * n)
    if p_e == 1.0:
        return 1.0
    return round((p_o - p_e) / (1 - p_e), 4)


def f1(tp: int, fp: int, fn: int) -> float:
    denom = 2 * tp + fp + fn
    return round(2 * tp / denom, 4) if denom else 0.0


def precision(tp: int, fp: int) -> float:
    return round(tp / (tp + fp), 4) if (tp + fp) else 0.0


def recall(tp: int, fn: int) -> float:
    return round(tp / (tp + fn), 4) if (tp + fn) else 0.0


def compute_metrics(results: list[dict]) -> dict[str, dict]:
    metrics: dict[str, dict] = {}
    for bid in ALL_BEHAVIORS:
        tp = fp = fn = tn = 0
        for r in results:
            gold = r["gold_labels"].get(bid, 0)
            pred = r["claude_scores"].get(bid, 0)
            if gold == 1 and pred == 1:
                tp += 1
            elif gold == 0 and pred == 1:
                fp += 1
            elif gold == 1 and pred == 0:
                fn += 1
            else:
                tn += 1
        k = cohen_kappa(tp, fp, fn, tn)
        f = f1(tp, fp, fn)
        metrics[bid] = {
            "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision(tp, fp),
            "recall": recall(tp, fn),
            "f1": f,
            "kappa": k,
            "n_gold_positive": tp + fn,
            "n_claude_positive": tp + fp,
            "reliable": f >= PROCEED_F1 and k >= PROCEED_KAPPA,
        }
    return metrics


def disagreement_analysis(results: list[dict], bid: str) -> list[dict]:
    """Return frames where gold and Claude disagreed on this behavior."""
    errors: list[dict] = []
    for r in results:
        gold = r["gold_labels"].get(bid, 0)
        pred = r["claude_scores"].get(bid, 0)
        if gold != pred:
            raw = r.get("claude_raw", {}).get(bid, {})
            errors.append({
                "frame_id": r["frame_id"],
                "student_id": r["student_id"],
                "error_type": "FP" if pred == 1 else "FN",
                "gold": gold,
                "claude": pred,
                "silver_confidence": r.get("silver_confidence", "none"),
                "claude_evidence": raw.get("evidence", ""),
                "frame_description": r.get("frame_description", ""),
            })
    return errors


def print_report(
    metrics: dict[str, dict],
    results: list[dict],
    show_disagree: bool = True,
) -> None:
    n = len(results)
    print(f"\n{'='*70}")
    print(f"  2025 Validation Report — Claude vs Expert Labels")
    print(f"  Frames: {n}    Model: scored by Claude")
    print(f"{'='*70}\n")

    macro_f1 = round(sum(m["f1"] for m in metrics.values()) / len(metrics), 4)
    macro_k = round(sum(m["kappa"] for m in metrics.values()) / len(metrics), 4)
    weighted_f1 = 0.0
    total_pos = sum(m["n_gold_positive"] for m in metrics.values())
    if total_pos:
        weighted_f1 = round(sum(
            m["f1"] * m["n_gold_positive"] for m in metrics.values()
        ) / total_pos, 4)

    print(f"── Per-behavior metrics ─────────────────────────────────────────────")
    print(f"  {'Beh':<5} {'F1':>6} {'κ':>7} {'Prec':>7} {'Rec':>7} {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4}  Status")
    print(f"  {'-'*72}")
    for bid in ALL_BEHAVIORS:
        m = metrics[bid]
        ok = "✓ OK" if m["reliable"] else "✗ REFINE"
        if m["n_gold_positive"] == 0:
            ok = "— no positives"
        print(
            f"  {bid:<5} {m['f1']:>6.3f} {m['kappa']:>7.3f}"
            f" {m['precision']:>7.3f} {m['recall']:>7.3f}"
            f" {m['tp']:>4} {m['fp']:>4} {m['fn']:>4} {m['tn']:>4}  {ok}"
        )

    print()
    print(f"── Aggregate ────────────────────────────────────────────────────────")
    print(f"  Macro-F1:    {macro_f1:.3f}  (threshold: {PROCEED_F1})")
    print(f"  Weighted-F1: {weighted_f1:.3f}")
    print(f"  Macro-κ:     {macro_k:.3f}  (threshold: {PROCEED_KAPPA})")
    print()

    proceed = macro_f1 >= PROCEED_F1 and macro_k >= PROCEED_KAPPA
    if proceed:
        print("  ✅ VERDICT: PROCEED to 2026 scoring.")
        print(f"     Macro-F1={macro_f1:.3f} ≥ {PROCEED_F1} and κ={macro_k:.3f} ≥ {PROCEED_KAPPA}")
    else:
        print("  ⚠  VERDICT: REFINE prompt before scoring 2026.")
        failing = [bid for bid, m in metrics.items() if not m["reliable"] and m["n_gold_positive"] > 0]
        print(f"     Behaviors below threshold: {', '.join(failing)}")

    if show_disagree and not proceed:
        print()
        print("── Disagreement analysis (worst behaviors) ──────────────────────────")
        # Show top 3 worst behaviors
        worst = sorted(
            [(bid, m) for bid, m in metrics.items() if m["n_gold_positive"] > 0],
            key=lambda x: x[1]["f1"],
        )[:3]
        for bid, m in worst:
            errors = disagreement_analysis(results, bid)
            fn_cases = [e for e in errors if e["error_type"] == "FN"]
            fp_cases = [e for e in errors if e["error_type"] == "FP"]
            print(f"\n  {bid} — F1={m['f1']:.3f}  FN={m['fn']} (missed)  FP={m['fp']} (false alarm)")
            for case in fn_cases[:3]:
                print(f"    FN [{case['student_id']}] conf={case['silver_confidence']}")
                print(f"       Claude evidence: {case['claude_evidence'][:100] or '(empty)'}")
            for case in fp_cases[:3]:
                print(f"    FP [{case['student_id']}]")
                print(f"       Claude evidence: {case['claude_evidence'][:100]}")
    print()


def main() -> int:
    global PROCEED_F1, PROCEED_KAPPA
    ap = argparse.ArgumentParser(description="Compute validation metrics")
    ap.add_argument("--min-f1", type=float, default=PROCEED_F1)
    ap.add_argument("--min-kappa", type=float, default=PROCEED_KAPPA)
    ap.add_argument("--no-disagree", action="store_true")
    args = ap.parse_args()
    PROCEED_F1 = args.min_f1
    PROCEED_KAPPA = args.min_kappa

    if not SCORES_FILE.is_file():
        print("ERROR: Run score_validation_frames.py first.")
        return 1

    data = json.loads(SCORES_FILE.read_text(encoding="utf-8"))
    results = data["results"]

    if not results:
        print("No scored frames found.")
        return 1

    print(f"Loaded {len(results)} scored frames (model: {data.get('model','?')})")

    metrics = compute_metrics(results)
    print_report(metrics, results, show_disagree=not args.no_disagree)

    macro_f1 = round(sum(m["f1"] for m in metrics.values()) / len(metrics), 4)
    macro_k = round(sum(m["kappa"] for m in metrics.values()) / len(metrics), 4)
    proceed = macro_f1 >= PROCEED_F1 and macro_k >= PROCEED_KAPPA

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": data.get("model"),
        "n_frames": len(results),
        "macro_f1": macro_f1,
        "macro_kappa": macro_k,
        "proceed_threshold_f1": PROCEED_F1,
        "proceed_threshold_kappa": PROCEED_KAPPA,
        "verdict": "PROCEED" if proceed else "REFINE",
        "per_behavior": metrics,
        "disagreements": {
            bid: disagreement_analysis(results, bid)
            for bid in ALL_BEHAVIORS
        },
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote → {OUT_FILE.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
