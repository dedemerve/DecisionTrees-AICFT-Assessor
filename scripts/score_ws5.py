"""
Score WS5 (threshold-search grid + final decision) for all students.

The bridge stores trial data as WS5_trial_N_* keys. The rubric rows expect
WS5_B1..B12 (threshold/correct/errors/mcr for each of 3 trials) and WS5_B25
(final decision). This script remaps before scoring.

Usage:
    python scripts/score_ws5.py [--dry-run] [--students Amy Bruno ...]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
SITE = REPO / ".venv" / "lib"
for p in SITE.glob("python*/site-packages"):
    sys.path.insert(0, str(p))

from pipeline_integration import score_ws5_deterministic
from student_bundle import load_artifact, save_scoring_bundle
from ws5_validation import validate_ws5_extraction

STUDENTS_DIR = REPO / "students"
ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara",
    "Melinda", "Serena",
]

DATASET_SIZE = 11
ROW_CELL_KEYS = [
    ("WS5_B1",  "WS5_B2",  "WS5_B3",  "WS5_B4"),   # row1
    ("WS5_B5",  "WS5_B6",  "WS5_B7",  "WS5_B8"),   # row2
    ("WS5_B9",  "WS5_B10", "WS5_B11", "WS5_B12"),  # row3
]


def remap_to_rubric_cells(items: dict[str, str]) -> dict[str, str]:
    """Convert WS5_trial_N_* bridge keys to WS5_B1..B12 rubric cell keys."""
    out: dict[str, str] = {}

    for n in range(1, 4):
        tk, ck, ek, mk = ROW_CELL_KEYS[n - 1]
        feature   = items.get(f"WS5_trial_{n}_feature", "(not_extracted)")
        left_op   = items.get(f"WS5_trial_{n}_left_op", "(not_extracted)")
        left_thr  = items.get(f"WS5_trial_{n}_left_threshold", "(not_extracted)")
        errors    = items.get(f"WS5_trial_{n}_errors", "(not_extracted)")
        mcr       = items.get(f"WS5_trial_{n}_mcr", "(not_extracted)")

        sentinel = "(not_extracted)"

        if feature == sentinel or left_op == sentinel or left_thr == sentinel:
            out[tk] = sentinel
            out[ck] = sentinel
            out[ek] = sentinel
            out[mk] = sentinel
            continue

        out[tk] = f"{feature} {left_op} {left_thr}"

        if errors != sentinel:
            try:
                err_int = int(float(errors))
                out[ek] = str(err_int)
                out[ck] = str(DATASET_SIZE - err_int)
                if mcr == sentinel:
                    out[mk] = str(round(err_int / DATASET_SIZE, 4))
                else:
                    out[mk] = mcr
            except ValueError:
                out[ek] = errors
                out[ck] = sentinel
                out[mk] = mcr if mcr != sentinel else sentinel
        else:
            out[ek] = sentinel
            out[ck] = sentinel
            out[mk] = mcr if mcr != sentinel else sentinel

    # Final decision (B25)
    out["WS5_B25"] = items.get("WS5_final_decision", "(not_extracted)")

    return out


def score_student(student: str, dry_run: bool) -> str:
    ext = load_artifact(student, "WS5", "extraction")
    if ext is None:
        return "SKIP_NO_EXTRACTION"

    items = ext.get("gate_1_extraction", {}).get("items", {})
    if not items or all("(not_extracted)" in str(v) for v in items.values()):
        return "SKIP_EMPTY_EXTRACTION"

    if "WS5__WRONG_WORKSHEET" in items:
        return "SKIP_WRONG_WORKSHEET"

    responses = remap_to_rubric_cells(items)

    from pipeline_schema import load_rubric
    rubric = load_rubric("WS5")
    validation = validate_ws5_extraction(responses, rubric)

    result = score_ws5_deterministic(responses, student, validation=validation)

    total = result.get("total_score", 0.0)
    max_s = result.get("max_score", 4.0)
    review_items = [r["item"] for r in result["items"] if r.get("review")]

    if dry_run:
        item_lines = "  ".join(
            f"{r['item']}:{r['score']:.1f}" for r in result["items"]
        )
        rev = f" REVIEW:{review_items}" if review_items else ""
        return f"DRY_RUN: {total:.1f}/{max_s:.1f}  [{item_lines}]{rev}"

    save_scoring_bundle(student, "WS5", result)
    rev = f" REVIEW:{review_items}" if review_items else ""
    return f"SCORED: {total:.1f}/{max_s:.1f}{rev}"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--students", nargs="+", default=None)
    args = parser.parse_args()

    students = args.students or ALL_STUDENTS
    if args.dry_run:
        print("\nDRY RUN -- no files will be written.\n")

    completed = skipped = failed = review = 0
    for s in students:
        try:
            status = score_student(s, args.dry_run)
        except Exception as exc:
            status = f"ERROR: {exc}"
            failed += 1
        print(f"  {s:12s} WS5: {status}")
        if status.startswith("SCORED"):
            completed += 1
            if "REVIEW" in status:
                review += 1
        elif status.startswith("DRY_RUN"):
            completed += 1
        elif status.startswith("SKIP"):
            skipped += 1
        else:
            failed += 1

    print(f"\nDone. completed={completed} skipped={skipped} failed={failed} review_flagged={review}")


if __name__ == "__main__":
    main()
