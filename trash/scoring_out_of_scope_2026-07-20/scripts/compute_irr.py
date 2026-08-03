#!/usr/bin/env python3
"""Compute inter-rater reliability from completed IRR coding sheet.

Reads calibration/irr_coding_sheet.csv (two rows per episode: Rater_1 + Rater_2).
Computes Cohen's κ and percentage agreement per behavior.

Output:
    calibration/irr_results.json

Usage:
    python scripts/compute_irr.py
    python scripts/compute_irr.py --dry-run   # validates sheet format only
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SHEET = REPO_ROOT / "calibration" / "irr_coding_sheet.csv"
OUT = REPO_ROOT / "calibration" / "irr_results.json"

BEHAVIORS = ["B0","B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12","B13"]
LEVELS = ["Deepen", "Acquire", "not_observed", "not_measurable"]
KAPPA_MIN = 0.70
AGREE_MIN = 0.80


def cohen_kappa_ordinal(rater1: list[str], rater2: list[str]) -> float:
    """Weighted Cohen's kappa (linear weights) for ordinal levels."""
    level_idx = {l: i for i, l in enumerate(LEVELS)}
    n = len(rater1)
    if n == 0:
        return 0.0
    # Build confusion matrix
    k = len(LEVELS)
    matrix = [[0] * k for _ in range(k)]
    for r1, r2 in zip(rater1, rater2):
        i = level_idx.get(r1, -1)
        j = level_idx.get(r2, -1)
        if i >= 0 and j >= 0:
            matrix[i][j] += 1
    # Unweighted kappa for simplicity (can extend to weighted)
    po = sum(matrix[i][i] for i in range(k)) / n
    row_sums = [sum(matrix[i]) for i in range(k)]
    col_sums = [sum(matrix[i][j] for i in range(k)) for j in range(k)]
    pe = sum(row_sums[i] * col_sums[i] for i in range(k)) / (n * n)
    if pe == 1.0:
        return 1.0
    return round((po - pe) / (1 - pe), 4)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute IRR from coding sheet")
    ap.add_argument("--dry-run", action="store_true", help="Validate format only")
    args = ap.parse_args()

    if not SHEET.is_file():
        print("ERROR: irr_coding_sheet.csv not found. Run sample_irr_units.py first.")
        return 1

    rows_by_episode: dict[str, dict[str, dict]] = defaultdict(dict)
    with SHEET.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ep_id = row["episode_id"]
            rater = row["rater_id"]
            rows_by_episode[ep_id][rater] = row

    paired = [
        (data["Rater_1"], data["Rater_2"])
        for ep_id, data in rows_by_episode.items()
        if "Rater_1" in data and "Rater_2" in data
    ]

    if not paired:
        print("No paired rows found. Sheet may be empty or not yet filled.")
        if args.dry_run:
            print("Dry run: sheet format appears valid.")
            return 0
        return 1

    if args.dry_run:
        print(f"Sheet has {len(paired)} paired episodes. Format OK.")
        return 0

    print(f"Computing IRR on {len(paired)} paired episodes...")

    per_behavior: dict[str, dict] = {}
    all_kappas: list[float] = []

    for b in BEHAVIORS:
        col = f"{b}_level"
        r1_vals: list[str] = []
        r2_vals: list[str] = []
        for r1_row, r2_row in paired:
            v1 = r1_row.get(col, "").strip()
            v2 = r2_row.get(col, "").strip()
            if v1 and v2:
                r1_vals.append(v1)
                r2_vals.append(v2)

        if not r1_vals:
            per_behavior[b] = {"n_episodes": 0, "kappa": None, "pct_agreement": None, "usable": False}
            continue

        agree = sum(1 for a, b_ in zip(r1_vals, r2_vals) if a == b_)
        pct = round(agree / len(r1_vals), 4)
        kappa = cohen_kappa_ordinal(r1_vals, r2_vals)
        all_kappas.append(kappa)

        per_behavior[b] = {
            "n_episodes": len(r1_vals),
            "kappa": kappa,
            "pct_agreement": pct,
            "usable": kappa >= KAPPA_MIN and pct >= AGREE_MIN,
        }

    macro_kappa = round(sum(all_kappas) / len(all_kappas), 4) if all_kappas else None
    usable_behaviors = [b for b, m in per_behavior.items() if m.get("usable")]

    print(f"\nPer-behavior IRR:")
    print(f"  {'Beh':<5} {'κ':>6} {'Agree':>7} {'Usable':>8}")
    for b in BEHAVIORS:
        m = per_behavior[b]
        k = f"{m['kappa']:.3f}" if m["kappa"] is not None else "  N/A"
        a = f"{m['pct_agreement']:.1%}" if m["pct_agreement"] is not None else "  N/A"
        u = "yes" if m.get("usable") else "no"
        print(f"  {b:<5} {k:>6} {a:>7} {u:>8}")

    print(f"\nMacro-κ: {macro_kappa}")
    print(f"Behaviors above threshold (κ≥{KAPPA_MIN}, agree≥{AGREE_MIN:.0%}): {usable_behaviors}")

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_paired_episodes": len(paired),
        "kappa_threshold": KAPPA_MIN,
        "agreement_threshold": AGREE_MIN,
        "macro_kappa": macro_kappa,
        "per_behavior": per_behavior,
        "usable_behaviors": usable_behaviors,
        "behaviors_needing_revision": [b for b in BEHAVIORS if not per_behavior.get(b, {}).get("usable")],
        "note": "debug_only_frame_metrics_excluded — this is the primary reliability metric for publication",
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nWritten → {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
