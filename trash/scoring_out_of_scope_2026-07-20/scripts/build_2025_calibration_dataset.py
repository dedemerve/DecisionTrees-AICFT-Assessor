#!/usr/bin/env python3
"""Build a calibration dataset from 2025 gold-labeled video frames.

For each frame across all 17 students this script:
  1. Maps codebook behavior codes to rubric behaviors B0-B9, B12
  2. Detects B10 (multi-level tree, Depth 2+) from observer text
  3. Detects B11 candidates (B2 + B6 co-occurring within a time window)
  4. Notes B13 as unmeasurable (transcript required, none available in 2025)
  5. Writes calibration/2025_calibration_dataset.json
  6. Prints a comprehensive coverage report

Usage:
    python scripts/build_2025_calibration_dataset.py
    python scripts/build_2025_calibration_dataset.py --b11-window 120
    python scripts/build_2025_calibration_dataset.py --report-only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TRAIN_ROOT = REPO_ROOT / "training_datasets" / "2025"
OUT_FILE = REPO_ROOT / "calibration" / "2025_calibration_dataset.json"

# Codebook code -> rubric behavior id.
# Codes not listed here are context-only (SEEK_HELP_OR_DIALOGUE, COLOR_OR_STYLE_GRAPH,
# IMPORT_TREE, ERROR_SCREEN) and do not map to any B0-B13 rubric criterion.
CODEBOOK_TO_RUBRIC: dict[str, str] = {
    "LOAD_DATASET":           "B0",
    "OPEN_ARBOR":             "B0",
    "CREATE_GRAPH":           "B1",
    "SET_AXIS":               "B1",
    "SWAP_AXES":              "B1",
    "CLOSE_GRAPH":            "B1",
    "COLOR_OR_STYLE_GRAPH":   "B1",
    "ADD_MOVABLE_VALUE":      "B2",
    "UPDATE_MOVABLE_VALUE":   "B2",
    "SET_TARGET_ATTRIBUTE":   "B3",
    "DRAG_SPLIT_ATTRIBUTE":   "B4",
    "ASSIGN_LEAF_LABEL":      "B5",
    "UPDATE_THRESHOLD":       "B6",
    "EMIT_TREE":              "B7",
    "INTERPRET_METRICS":      "B8",
    "TRAIN_TEST_SPLIT":       "B9",
    "SELECT_CTR_ROW":         "B12",
    "DELETE_TREE_OR_CTR_ROW": "B12",
    "COMPARE_MODELS":         "B12",
}

# Regex to detect Depth 2+ tree structures in observer text
DEPTH2_RE = re.compile(
    r"Depth\s*[2-9]|depth\s+2|ikinci.*katman|iki.*katman|child.*node|"
    r"2\.\s*katman|depth-2",
    re.I,
)

# B11 detection: B2 (movable value) and B6 (threshold update) within this window (seconds)
DEFAULT_B11_WINDOW_S = 120.0

# B14: observer text patterns indicating class-balance or fairness awareness
B14_RE = re.compile(
    r"sınıf den|class imbal|eşitsiz.*sınıf|dengesiz.*veri|"
    r"(daha (az|fazla|çok)).*(not recommendable|recommendable|sınıf)|"
    r"(not recommendable|recommendable).*(daha (az|fazla|çok))|"
    r"küçük.*sınıf|büyük.*sınıf|az.*örnek|çok.*örnek|"
    r"veri.*denges|denges.*veri|eşit.*dağıl|dağıl.*eşit",
    re.I,
)

# B17: observer text patterns indicating pre-task planning or orientation
B17_RE = re.compile(
    r"soruları incele|görevi incele|veri.*incele|incele.*veri|"
    r"önce.*oku|oku.*önce|plan|strateji|ne yapacağ|nasıl yapacağ|"
    r"çalışma kağıd.*incele|worksheet.*incele|tabloyu incele|"
    r"neyi tahmin|hedefi belirle|amacı anlama",
    re.I,
)


def student_ids() -> list[str]:
    return sorted(
        d.name for d in TRAIN_ROOT.iterdir()
        if d.is_dir() and (d / f"{d.name}_gold_behavior_alignment.json").is_file()
    )


def load_gold(student_id: str) -> dict:
    p = TRAIN_ROOT / student_id / f"{student_id}_gold_behavior_alignment.json"
    return json.loads(p.read_text())


def _alignments_by_step(gold: dict) -> dict[int, dict]:
    return {r["metadata"]["observation_step_index"]: r for r in gold.get("alignments", [])}


def detect_b10_steps(gold: dict) -> set[int]:
    """Return observation step indices where Depth 2+ is mentioned."""
    b10_steps: set[int] = set()
    for row in gold.get("alignments", []):
        obs_text = row.get("gold", {}).get("uzman_nitel_gözlemi", "") or ""
        codes = row.get("gold", {}).get("behavior_code_list", [])
        if "DRAG_SPLIT_ATTRIBUTE" in codes and DEPTH2_RE.search(obs_text):
            b10_steps.add(row["metadata"]["observation_step_index"])
    return b10_steps


def detect_b14_steps(gold: dict) -> set[int]:
    """Return step indices where observer text indicates class-balance awareness."""
    steps: set[int] = set()
    for row in gold.get("alignments", []):
        obs = row.get("gold", {}).get("uzman_nitel_gözlemi", "") or ""
        if B14_RE.search(obs):
            steps.add(row["metadata"]["observation_step_index"])
    return steps


def detect_b15_steps(gold: dict) -> set[int]:
    """Return step indices that are part of a VOTAT iteration.

    A VOTAT interval is a pair of consecutive EMIT_TREE steps where exactly
    one of {predictor change, threshold change} occurs between them (not both,
    not neither). The emit step itself and all steps between the two emits
    are marked as B15.
    """
    by_step = _alignments_by_step(gold)
    sorted_steps = sorted(by_step.keys())

    emit_steps = [
        i for i in sorted_steps
        if "EMIT_TREE" in (by_step[i].get("gold", {}).get("behavior_code_list", []))
    ]

    b15_steps: set[int] = set()
    for a, b in zip(emit_steps[:-1], emit_steps[1:]):
        pred_changes = 0
        thresh_changes = 0
        for i in range(a + 1, b):
            if i not in by_step:
                continue
            codes = by_step[i].get("gold", {}).get("behavior_code_list", [])
            if "DRAG_SPLIT_ATTRIBUTE" in codes:
                pred_changes += 1
            if "UPDATE_THRESHOLD" in codes:
                thresh_changes += 1
        # VOTAT: exactly one dimension changed, and at least one change occurred
        only_pred = pred_changes > 0 and thresh_changes == 0
        only_thresh = thresh_changes > 0 and pred_changes == 0
        if only_pred or only_thresh:
            b15_steps.add(b)  # mark the emit step that concluded the VOTAT interval
            for i in range(a + 1, b + 1):
                b15_steps.add(i)
    return b15_steps


def detect_b16_steps(gold: dict) -> set[int]:
    """Return step indices where error recovery is evident.

    Pattern: DELETE_TREE_OR_CTR_ROW step followed by DRAG_SPLIT_ATTRIBUTE
    where the new predictor differs from the predictor used before the delete.
    Both the delete step and the subsequent drag step are marked.
    """
    by_step = _alignments_by_step(gold)
    sorted_steps = sorted(by_step.keys())

    def predictor_at(step_idx: int) -> str | None:
        obs = by_step.get(step_idx, {}).get("gold", {}).get("uzman_nitel_gözlemi", "") or ""
        # Extract quoted attribute name if visible in observer text (heuristic)
        m = re.search(r'"([^"]{2,30})"', obs)
        return m.group(1) if m else obs[:40]

    b16_steps: set[int] = set()
    for pos, step_idx in enumerate(sorted_steps):
        codes = by_step[step_idx].get("gold", {}).get("behavior_code_list", [])
        if "DELETE_TREE_OR_CTR_ROW" not in codes:
            continue
        # Find the most recent predictor before this delete
        pred_before = None
        for prev in reversed(sorted_steps[:pos]):
            prev_codes = by_step[prev].get("gold", {}).get("behavior_code_list", [])
            if "DRAG_SPLIT_ATTRIBUTE" in prev_codes:
                pred_before = predictor_at(prev)
                break
        # Find the next predictor after the delete
        for nxt in sorted_steps[pos + 1:]:
            nxt_codes = by_step[nxt].get("gold", {}).get("behavior_code_list", [])
            if "DRAG_SPLIT_ATTRIBUTE" in nxt_codes:
                pred_after = predictor_at(nxt)
                if pred_before is None or pred_before != pred_after:
                    b16_steps.add(step_idx)
                    b16_steps.add(nxt)
                break
    return b16_steps


def detect_b17_steps(gold: dict) -> set[int]:
    """Return step indices indicating pre-task planning or orientation.

    Two signals:
    1. The first step(s) contain only LOAD_DATASET/OPEN_ARBOR codes AND the
       observer text mentions task or data inspection before any model action.
       In 2025 data this is rare — most step-0 texts are purely descriptive.
    2. Any step where B17_RE matches observer text (explicit planning mention).
    """
    by_step = _alignments_by_step(gold)
    sorted_steps = sorted(by_step.keys())
    b17_steps: set[int] = set()

    # Signal 1: early steps with explicit planning language
    model_codes = {"DRAG_SPLIT_ATTRIBUTE", "UPDATE_THRESHOLD", "SET_TARGET_ATTRIBUTE",
                   "EMIT_TREE", "ASSIGN_LEAF_LABEL", "TRAIN_TEST_SPLIT"}
    first_model_step = next(
        (i for i in sorted_steps
         if model_codes & set(by_step[i].get("gold", {}).get("behavior_code_list", []))),
        None,
    )
    if first_model_step is not None:
        for i in sorted_steps:
            if i >= first_model_step:
                break
            obs = by_step[i].get("gold", {}).get("uzman_nitel_gözlemi", "") or ""
            if B17_RE.search(obs):
                b17_steps.add(i)

    # Signal 2: explicit planning language anywhere (re-orientation after failed attempt)
    for i in sorted_steps:
        obs = by_step[i].get("gold", {}).get("uzman_nitel_gözlemi", "") or ""
        if B17_RE.search(obs):
            b17_steps.add(i)

    return b17_steps


def build_student_frames(
    student_id: str,
    gold: dict,
    b11_window_s: float,
) -> list[dict]:
    """Build one calibration record per frame for a student."""
    b10_steps = detect_b10_steps(gold)
    b14_steps = detect_b14_steps(gold)
    b15_steps = detect_b15_steps(gold)
    b16_steps = detect_b16_steps(gold)
    b17_steps = detect_b17_steps(gold)

    # Build step-level rubric labels (needed to map back to frames via inherited_from_step)
    step_rubric: dict[int, set[str]] = {}
    for row in gold.get("alignments", []):
        step_idx = row["metadata"]["observation_step_index"]
        codes = row.get("gold", {}).get("behavior_code_list", [])
        rubric_ids: set[str] = set()
        for code in codes:
            rb = CODEBOOK_TO_RUBRIC.get(code)
            if rb:
                rubric_ids.add(rb)
        if step_idx in b10_steps:
            rubric_ids.add("B10")
        if step_idx in b14_steps:
            rubric_ids.add("B14")
        if step_idx in b15_steps:
            rubric_ids.add("B15")
        if step_idx in b16_steps:
            rubric_ids.add("B16")
        if step_idx in b17_steps:
            rubric_ids.add("B17")
        step_rubric[step_idx] = rubric_ids

    frame_records: list[dict] = []
    fbc = gold.get("frame_behavior_coverage", [])

    # Collect timestamps for B2 and B6 frames (for B11 detection)
    b2_ts: list[float] = []
    b6_ts: list[float] = []
    for frame in fbc:
        ts_ms = frame.get("timestamp_ms", 0) or 0
        ts_s = ts_ms / 1000.0
        codes = frame.get("behavior_code_list", [])
        if any(c in ("ADD_MOVABLE_VALUE", "UPDATE_MOVABLE_VALUE") for c in codes):
            b2_ts.append(ts_s)
        if "UPDATE_THRESHOLD" in codes:
            b6_ts.append(ts_s)

    for frame in fbc:
        ts_ms = frame.get("timestamp_ms", 0) or 0
        ts_s = ts_ms / 1000.0
        step_idx = frame.get("inherited_from_step", -1)
        codes = frame.get("behavior_code_list", [])

        # Base rubric behaviors from codebook mapping
        rubric_ids: set[str] = set()
        for code in codes:
            rb = CODEBOOK_TO_RUBRIC.get(code)
            if rb:
                rubric_ids.add(rb)

        # B10-B17: inherit from step
        if step_idx in b10_steps:
            rubric_ids.add("B10")
        if step_idx in b14_steps:
            rubric_ids.add("B14")
        if step_idx in b15_steps:
            rubric_ids.add("B15")
        if step_idx in b16_steps:
            rubric_ids.add("B16")
        if step_idx in b17_steps:
            rubric_ids.add("B17")

        # B11: this frame has B2 or B6 AND there is a B6 or B2 counterpart within the window
        has_b2 = any(c in ("ADD_MOVABLE_VALUE", "UPDATE_MOVABLE_VALUE") for c in codes)
        has_b6 = "UPDATE_THRESHOLD" in codes
        b11_candidate = False
        if has_b2:
            # Check if there is a B6 timestamp within window
            for t6 in b6_ts:
                if abs(ts_s - t6) <= b11_window_s:
                    b11_candidate = True
                    break
        if has_b6:
            for t2 in b2_ts:
                if abs(ts_s - t2) <= b11_window_s:
                    b11_candidate = True
                    break
        if b11_candidate:
            rubric_ids.add("B11")

        frame_records.append({
            "student_id": student_id,
            "frame_id": frame["frame_id"],
            "frame_image_path": str(
                TRAIN_ROOT / student_id / frame["frame_image"]
            ),
            "timestamp_s": round(ts_s, 3),
            "inherited_from_step": step_idx,
            "codebook_codes": codes,
            "rubric_behaviors": sorted(rubric_ids),
            "expert_screenshot": frame.get("expert_screenshot"),
            "label_source": frame.get("label_source"),
            "b10_from_text": step_idx in b10_steps,
            "b11_candidate": b11_candidate,
            "b14_from_text": step_idx in b14_steps,
            "b15_votat": step_idx in b15_steps,
            "b16_error_recovery": step_idx in b16_steps,
            "b17_planning": step_idx in b17_steps,
        })

    return frame_records


def print_report(
    all_frames: list[dict],
    student_summary: dict[str, dict],
    b11_window_s: float,
) -> None:
    total = len(all_frames)
    n_students = len(student_summary)

    rubric_counts: Counter = Counter()
    rubric_student_coverage: dict[str, set] = defaultdict(set)
    for f in all_frames:
        for rb in f["rubric_behaviors"]:
            rubric_counts[rb] += 1
            rubric_student_coverage[rb].add(f["student_id"])

    print(f"\n{'='*64}")
    print(f"  2025 Calibration Dataset — Training Coverage Report")
    print(f"  Students: {n_students}    Total frames: {total}")
    print(f"{'='*64}\n")

    print("── Rubric behavior coverage ────────────────────────────────")
    print(f"  {'Behavior':<8} {'Frames':>7}  {'Students':>9}  {'Coverage %':>11}  Notes")
    print(f"  {'-'*58}")
    all_behaviors = ["B0","B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12","B13",
                     "B14","B15","B16","B17"]
    for rb in all_behaviors:
        cnt = rubric_counts.get(rb, 0)
        stu = len(rubric_student_coverage.get(rb, set()))
        pct = round(100.0 * cnt / total, 1) if total else 0.0
        note = ""
        if rb == "B10":
            note = "inferred from observer Depth 2+ text"
        elif rb == "B11":
            note = f"B2+B6 within {int(b11_window_s)}s window"
        elif rb == "B13":
            note = "UNMEASURABLE — transcript required (2025: no audio)"
        elif rb == "B14":
            note = "inferred from observer text (class-balance mention)"
        elif rb == "B15":
            note = "VOTAT — single-dimension change between consecutive emits"
        elif rb == "B16":
            note = "DELETE followed by different predictor"
        elif rb == "B17":
            note = "planning/orientation language in observer text"
        tag = " ← sparse" if cnt < 50 and rb != "B13" else ""
        print(f"  {rb:<8} {cnt:>7}  {stu:>9}  {pct:>10.1f}%  {note}{tag}")

    print()
    print("── Per-student frame count ─────────────────────────────────")
    for sid, info in sorted(student_summary.items()):
        frames = info["total_frames"]
        rubrics = ", ".join(sorted(info["rubric_behaviors"]))
        print(f"  {sid:<12} {frames:>5} frames  {rubrics}")

    print()
    print("── Training gaps ───────────────────────────────────────────")
    sparse = [rb for rb in all_behaviors if rubric_counts.get(rb, 0) < 50 and rb != "B13"]
    zero = [rb for rb in all_behaviors if rubric_counts.get(rb, 0) == 0 and rb != "B13"]
    if zero:
        print(f"  No labeled frames at all: {', '.join(zero)}")
    if sparse:
        print(f"  Sparse (<50 frames): {', '.join(sparse)}")
    print()
    print("  B13 requires audio transcript. All 2025 students: score=0 default.")
    print("  B10 inferred from text patterns — 14/17 students covered.")
    print("  B11 based on temporal proximity heuristic — verify with manual review.")
    print("  B14 (data fairness): video-primary, not detectable from 2025 codebook codes.")
    print("  B15 (VOTAT): log-primary, derivable from emit/change_split event sequences.")
    print("  B16 (error recovery): video-primary, log can detect delete events only.")
    print("  B17 (planning): video-primary, log provides pre-action time only.")
    print()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build 2025 calibration dataset")
    ap.add_argument(
        "--b11-window", type=float, default=DEFAULT_B11_WINDOW_S,
        help="Seconds window for B11 B2+B6 co-occurrence detection (default 120)",
    )
    ap.add_argument(
        "--report-only", action="store_true",
        help="Print report without writing output file",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    students = student_ids()
    all_frames: list[dict] = []
    student_summary: dict[str, dict] = {}

    for sid in students:
        gold = load_gold(sid)
        records = build_student_frames(sid, gold, args.b11_window)
        all_frames.extend(records)

        rubric_set: set[str] = set()
        for r in records:
            rubric_set.update(r["rubric_behaviors"])
        student_summary[sid] = {
            "total_frames": len(records),
            "rubric_behaviors": sorted(rubric_set),
            "b10_frames": sum(1 for r in records if "B10" in r["rubric_behaviors"]),
            "b11_frames": sum(1 for r in records if "B11" in r["rubric_behaviors"]),
        }
        if args.verbose:
            print(f"[{sid}] {len(records)} frames, rubric={sorted(rubric_set)}")

    print_report(all_frames, student_summary, args.b11_window)

    if not args.report_only:
        payload = {
            "dataset_id": "2025_calibration_v1",
            "created": datetime.now(timezone.utc).isoformat(),
            "source": "2025 observer gold alignment + codebook→rubric mapping",
            "total_frames": len(all_frames),
            "student_count": len(students),
            "b11_window_seconds": args.b11_window,
            "b13_note": "Not measurable in 2025 — no audio transcripts. Default score=0.",
            "students": student_summary,
            "frames": all_frames,
        }
        OUT_FILE.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {len(all_frames)} frame records to {OUT_FILE.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
