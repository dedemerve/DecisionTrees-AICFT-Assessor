"""
Score WS12 (two-level decision tree documentation) for all students.

Evaluation is purely on internal consistency — no canonical answer exists
(unplugged phase, 31 March 2026).

Field layout follows the printed form template (slots 1-14 + node counts):
  Slot 1   WS12_root_feature
  Slot 2   WS12_root_left_threshold   (e.g. "≤229")
  Slot 3   WS12_root_right_threshold  (complement, e.g. ">229")
  Slot 4   WS12_left_child_label      ("karar verildi" or next variable)
  Slot 4c  WS12_left_child_rec / notrec
  Slot 5   WS12_right_child_label
  Slot 5c  WS12_right_child_rec / notrec
  Slot 6   WS12_depth1_ll_threshold   ("N/A" when left child is leaf)
  Slot 7   WS12_depth1_lr_threshold   ("N/A" when left child is leaf)
  Slot 8   WS12_depth1_rl_threshold
  Slot 9   WS12_depth1_rr_threshold
  Slot 9L  WS12_leaf_ll_rec/notrec    ("N/A" when left child is leaf)
  Slot 10L WS12_leaf_lr_rec/notrec    ("N/A" when left child is leaf)
  Slot 11L WS12_leaf_rl_rec/notrec
  Slot 12L WS12_leaf_rr_rec/notrec
  Slot 13  WS12_train_errors
  Slot 14  WS12_test_errors

Rubric items:
  WS12_R1  Root split valid           (1 pt)
  WS12_R2  Complementary operators    (1 pt)
  WS12_R3  Left subtree complete      (1 pt)
  WS12_R4  Right subtree complete     (1 pt)
  WS12_R5  Node count conservation    (2 pt)
  WS12_R6  Training error consistent  (1 pt)
  WS12_R7  Test error recorded        (1 pt)
  Max: 8 pt

Usage:
    python scripts/score_ws12.py [--dry-run] [--students Amy Bruno ...]
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara",
    "Melinda", "Serena",
]

VALID_FEATURES = {
    "enerji", "energy", "kcal",
    "yağ", "yag", "fat",
    "doymuş yağ", "doymus yag", "saturated fat",
    "şeker", "seker", "sugar",
    "protein",
    "yaş", "yas", "age",
    "tuz", "sodyum", "sodium", "salt",
}

LEAF_LABELS = {"karar verildi", "karar verilmis", "decision made"}

COMPLEMENT_PAIRS = [
    ("≤", ">"), (">", "≤"),
    ("<", "≥"), ("≥", "<"),
    ("<=", ">"), (">=", "<"),
]


def _is_valid_feature(name: str | None) -> bool:
    return bool(name) and str(name).strip().lower() in VALID_FEATURES


def _is_leaf(label: str | None) -> bool:
    return bool(label) and str(label).strip().lower() in LEAF_LABELS


def _na(v) -> bool:
    return isinstance(v, str) and v.upper() == "N/A"


def _present(v) -> bool:
    return v is not None and not _na(v)


def _extract_op(threshold_str: str | None) -> str | None:
    if not threshold_str:
        return None
    s = str(threshold_str).strip()
    for op in ("≤", "≥", "<=", ">=", "<", ">"):
        if s.startswith(op):
            return op
    return None


def _operators_complementary(left: str | None, right: str | None) -> bool | None:
    if not left or not right:
        return None
    op_l = _extract_op(left)
    op_r = _extract_op(right)
    if not op_l or not op_r:
        return None
    return (op_l, op_r) in COMPLEMENT_PAIRS


def score_ws12(items: dict, student: str) -> dict:

    def result(item_id, score, conf, review=False, note=""):
        r: dict = {"item": item_id, "score": score, "confidence": conf, "review": review}
        if note:
            r["note"] = note
        return r

    results = []
    review_any = False

    # ------------------------------------------------------------------
    # WS12_R1 — root split: valid feature + threshold present
    # ------------------------------------------------------------------
    feat = items.get("WS12_root_feature")
    left_thr = items.get("WS12_root_left_threshold")

    feat_ok  = _is_valid_feature(feat)
    thr_ok   = _present(left_thr)

    if feat_ok and thr_ok:
        r1 = result("WS12_R1", 1.0, 1.0, note=f"feature={feat!r} threshold={left_thr!r}")
    elif feat_ok or thr_ok:
        r1 = result("WS12_R1", 0.5, 0.9, review=True,
                    note=f"partial: feature={feat_ok} threshold={thr_ok}")
        review_any = True
    else:
        r1 = result("WS12_R1", 0.0, 1.0, note="neither feature nor threshold")
    results.append(r1)

    # ------------------------------------------------------------------
    # WS12_R2 — complementary operator pair on root split
    # ------------------------------------------------------------------
    right_thr = items.get("WS12_root_right_threshold")
    comp = _operators_complementary(left_thr, right_thr)

    if comp is True:
        r2 = result("WS12_R2", 1.0, 1.0, note=f"ops: {_extract_op(left_thr)!r} / {_extract_op(right_thr)!r}")
    elif comp is False:
        r2 = result("WS12_R2", 0.0, 1.0, review=True,
                    note=f"non-complementary: {left_thr!r} / {right_thr!r}")
        review_any = True
    else:
        # cannot verify from text alone — flag for visual check
        r2 = result("WS12_R2", 1.0, 0.6, review=True,
                    note="operator extraction failed; visual verification required")
        review_any = True
    results.append(r2)

    # ------------------------------------------------------------------
    # WS12_R3 — left subtree complete
    # ------------------------------------------------------------------
    left_label   = items.get("WS12_left_child_label")
    left_rec     = items.get("WS12_left_child_rec")
    left_notrec  = items.get("WS12_left_child_notrec")

    left_is_leaf    = _is_leaf(left_label) or (
        _is_valid_feature(left_label) is False and _present(left_label))
    counts_present  = _present(left_rec) and _present(left_notrec)
    label_present   = _present(left_label)

    if counts_present and label_present:
        r3 = result("WS12_R3", 1.0, 1.0, note=f"label={left_label!r} counts={left_rec}/{left_notrec}")
    elif counts_present or label_present:
        r3 = result("WS12_R3", 0.5, 0.9, note="partial: " +
                    ("label present" if label_present else "counts present"))
    else:
        r3 = result("WS12_R3", 0.0, 1.0, review=True,
                    note="left child label and counts both missing")
        review_any = True
    results.append(r3)

    # ------------------------------------------------------------------
    # WS12_R4 — right subtree complete (feature + threshold + leaf counts)
    # ------------------------------------------------------------------
    right_label  = items.get("WS12_right_child_label")
    rl_thr       = items.get("WS12_depth1_rl_threshold")
    rr_thr       = items.get("WS12_depth1_rr_threshold")
    leaf_rl_rec  = items.get("WS12_leaf_rl_rec")
    leaf_rl_not  = items.get("WS12_leaf_rl_notrec")
    leaf_rr_rec  = items.get("WS12_leaf_rr_rec")
    leaf_rr_not  = items.get("WS12_leaf_rr_notrec")

    rf_ok        = _is_valid_feature(right_label)
    d1_thr_ok    = _present(rl_thr) and _present(rr_thr)
    leaves_ok    = all(_present(v) for v in [leaf_rl_rec, leaf_rl_not, leaf_rr_rec, leaf_rr_not])

    if rf_ok and d1_thr_ok and leaves_ok:
        r4 = result("WS12_R4", 1.0, 1.0, note=f"right={right_label!r} thr={rl_thr}/{rr_thr}")
    elif rf_ok and d1_thr_ok:
        r4 = result("WS12_R4", 0.5, 0.9, review=True,
                    note="right feature + threshold present but leaf counts missing")
        review_any = True
    elif rf_ok:
        r4 = result("WS12_R4", 0.5, 0.8, review=True,
                    note="right feature present but threshold/leaf counts missing")
        review_any = True
    else:
        r4 = result("WS12_R4", 0.0, 1.0, note="right child missing")
    results.append(r4)

    # ------------------------------------------------------------------
    # WS12_R5 — node count conservation (2 pts)
    # Sub A: right_child_total == sum of right subtree leaves
    # Sub B: overall total is positive and plausible
    # ------------------------------------------------------------------
    right_rec    = items.get("WS12_right_child_rec")
    right_notrec = items.get("WS12_right_child_notrec")

    r5_pts  = 0.0
    r5_rev  = False
    r5_notes = []

    # Sub A
    if (all(_present(v) for v in [right_rec, right_notrec,
                                   leaf_rl_rec, leaf_rl_not,
                                   leaf_rr_rec, leaf_rr_not])):
        node_total  = int(right_rec) + int(right_notrec)
        leaves_sum  = int(leaf_rl_rec) + int(leaf_rl_not) + int(leaf_rr_rec) + int(leaf_rr_not)
        if node_total == leaves_sum:
            r5_pts += 1.0
            r5_notes.append(f"right_node_sum ok ({node_total}={leaves_sum})")
        else:
            r5_notes.append(f"right_node_sum FAIL: node={node_total} leaves={leaves_sum}")
    else:
        r5_rev = True
        review_any = True
        r5_notes.append("right subtree counts incomplete — sum check skipped")

    # Sub B
    if (all(_present(v) for v in [left_rec, left_notrec, right_rec, right_notrec])):
        grand = int(left_rec) + int(left_notrec) + int(right_rec) + int(right_notrec)
        if grand > 0:
            r5_pts += 1.0
            r5_notes.append(f"grand_total plausible ({grand})")
        else:
            r5_notes.append("grand_total implausible (0)")
    else:
        r5_rev = True
        review_any = True
        r5_notes.append("node counts incomplete — total check skipped")

    results.append(result("WS12_R5", r5_pts, 0.7 if r5_rev else 1.0,
                          r5_rev, " | ".join(r5_notes)))

    # ------------------------------------------------------------------
    # WS12_R6 — training error count consistent
    # expected = sum of minority-class items at every leaf
    # Left leaf (if leaf): minority = min(left_rec, left_notrec)
    # Right leaves: minority = min(rl_rec, rl_not) + min(rr_rec, rr_not)
    # ------------------------------------------------------------------
    train_errors = items.get("WS12_train_errors")

    def minority(r, n):
        if _present(r) and _present(n):
            return min(int(r), int(n))
        return None

    left_min  = minority(left_rec, left_notrec)
    rl_min    = minority(leaf_rl_rec, leaf_rl_not)
    rr_min    = minority(leaf_rr_rec, leaf_rr_not)

    parts = [left_min, rl_min, rr_min]
    if None not in parts:
        expected_train = sum(parts)
    else:
        expected_train = None

    if _present(train_errors) and expected_train is not None:
        if int(train_errors) == expected_train:
            r6 = result("WS12_R6", 1.0, 1.0,
                        note=f"train_errors={train_errors} == expected={expected_train}")
        else:
            r6 = result("WS12_R6", 0.0, 1.0, review=True,
                        note=f"train_errors={train_errors} ≠ expected={expected_train}")
            review_any = True
    elif _present(train_errors) and int(train_errors) >= 0:
        r6 = result("WS12_R6", 1.0, 0.6, review=True,
                    note=f"train_errors={train_errors} present but cannot verify (leaf counts incomplete)")
        review_any = True
    else:
        r6 = result("WS12_R6", 0.0, 0.9, review=True,
                    note="train_errors blank or missing")
        review_any = True
    results.append(r6)

    # ------------------------------------------------------------------
    # WS12_R7 — test error recorded and plausible
    # ------------------------------------------------------------------
    test_errors = items.get("WS12_test_errors")
    if _present(test_errors) and 0 <= int(test_errors) <= 20:
        r7 = result("WS12_R7", 1.0, 1.0, note=f"test_errors={test_errors}")
    elif _present(test_errors):
        r7 = result("WS12_R7", 0.5, 0.7, review=True,
                    note=f"test_errors={test_errors} out of plausible range")
        review_any = True
    else:
        r7 = result("WS12_R7", 0.0, 1.0, note="test_errors blank or missing")
    results.append(r7)

    total = sum(r["score"] for r in results)
    return {
        "stage": "scoring",
        "student_id": student,
        "worksheet": "WS12",
        "blocked": False,
        "total_score": round(total, 2),
        "max_score": 8.0,
        "review_required": review_any,
        "items": results,
    }


def load_extraction(student: str) -> dict | None:
    p = REPO / "students" / student / "WS12" / "extraction.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def save_scoring(student: str, result: dict) -> None:
    (REPO / "students" / student / "WS12" / "scoring.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def score_student(student: str, dry_run: bool) -> str:
    ext = load_extraction(student)
    if ext is None:
        return "SKIP_NO_EXTRACTION"
    items = ext.get("gate_1_extraction", {}).get("items", {})
    if not items:
        return "SKIP_EMPTY_EXTRACTION"

    res = score_ws12(items, student)
    total, max_s = res["total_score"], res["max_score"]
    rev = " REVIEW" if res["review_required"] else ""
    tag = "DRY_RUN" if dry_run else "SCORED"
    if not dry_run:
        save_scoring(student, res)
    detail = "  ".join(f"{r['item']}:{r['score']:.1f}" for r in res["items"])
    return f"{tag}: {total:.1f}/{max_s:.1f}  [{detail}]{rev}"


def main():
    parser = argparse.ArgumentParser(description="Score WS12 internal consistency")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--students", nargs="+", default=None)
    args = parser.parse_args()

    students = args.students or ALL_STUDENTS
    if args.dry_run:
        print("\nDRY RUN — no files written.\n")

    completed = skipped = failed = 0
    for s in students:
        try:
            status = score_student(s, args.dry_run)
        except Exception as exc:
            status = f"ERROR: {exc}"
            failed += 1
        print(f"  {s:12s} WS12: {status}")
        if status.startswith("SCORED"):
            completed += 1
        elif status.startswith("SKIP"):
            skipped += 1

    print(f"\nCompleted: {completed}  Skipped: {skipped}  Failed: {failed}")


if __name__ == "__main__":
    main()
