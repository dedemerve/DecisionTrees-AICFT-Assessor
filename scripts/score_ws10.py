"""
Score WS10 (energy threshold error table) for all students.

Rubric items WS10_B1..B7 = misclassification counts per threshold row.
WS10_B8 = optimal threshold value (expected 408).

Usage:
    python scripts/score_ws10.py [--dry-run] [--students Amy Bruno ...]
"""

from __future__ import annotations

import argparse
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
SITE = REPO / ".venv" / "lib"
for p in SITE.glob("python*/site-packages"):
    sys.path.insert(0, str(p))

from pipeline_integration import score_ws10_deterministic
from student_bundle import load_artifact, save_scoring_bundle

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara",
    "Melinda", "Serena",
]


def score_student(student: str, dry_run: bool) -> str:
    ext = load_artifact(student, "WS10", "extraction")
    if ext is None:
        return "SKIP_NO_EXTRACTION"

    items = ext.get("gate_1_extraction", {}).get("items", {})
    if not items:
        return "SKIP_EMPTY_EXTRACTION"

    if "WS10__WRONG_WORKSHEET" in items:
        return "SKIP_WRONG_WORKSHEET"

    result = score_ws10_deterministic(items, student)
    total = result.get("total_score", 0.0)
    max_s = result.get("max_score", 8.0)
    review_items = [r["item"] for r in result["items"] if r.get("review")]

    if dry_run:
        item_lines = "  ".join(
            f"{r['item']}:{r['score']:.1f}" for r in result["items"]
        )
        rev = f" REVIEW:{review_items}" if review_items else ""
        return f"DRY_RUN: {total:.1f}/{max_s:.1f}  [{item_lines}]{rev}"

    save_scoring_bundle(student, "WS10", result)
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
        print(f"  {s:12s} WS10: {status}")
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
