#!/usr/bin/env python3
"""convert_frame_analyses.py — Convert codap_frame_analyses.json to final_scored.json format.

Reads the existing frame-level analyses (old schema: primary_behavior enum + boolean flags)
and deterministically maps them to B0–B13 behavior scores (new schema).

No API calls. Output is structurally identical to what mmla_scorer.py produces so
portfolio_builder can consume it unchanged.

Usage:
    python scripts/convert_frame_analyses.py --session 21apr --students Helena Iris
    python scripts/convert_frame_analyses.py --session 21apr   # all students with analyses
    python scripts/convert_frame_analyses.py --dry-run         # show what would be written
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import pipeline_schema as ps

DATA_ROOT = REPO_ROOT / "data_sources_2026"

SESSION_AUDIO_DIRS: dict[str, str] = {
    "21apr": "codap_arbor_21april_audio",
    "28apr": "codap_arbor_28april_audio",
}

CODAP_BEHAVIORS = [f"B{i}" for i in range(14)]  # B0–B13

# B14–B17 are colab_python only; always not_observed for codap_arbor
COLAB_ONLY = ["B14", "B15", "B16", "B17"]


# ---------------------------------------------------------------------------
# Frame-level behavior detection
# ---------------------------------------------------------------------------

def _triggered_behaviors(frame: dict) -> set[str]:
    """Return set of B-codes triggered by this frame."""
    pb = frame.get("primary_behavior", "")
    sb = frame.get("secondary_behavior", "")
    sc = frame.get("screen_context", "")
    dp = frame.get("deepen_phase", "")
    off = bool(frame.get("off_task", False))

    tree_has_nodes = bool(frame.get("tree_has_nodes", False))
    dep_var_set = bool(frame.get("dependent_variable_set", False))
    split_visible = bool(frame.get("split_values_visible", False))
    acc_visible = bool(frame.get("accuracy_visible", False))
    cm_visible = bool(frame.get("confusion_matrix_visible", False))

    sys_var = bool(frame.get("systematic_variable_selection", False))
    thr_reason = bool(frame.get("threshold_reasoning", False))
    acc_interp = bool(frame.get("accuracy_interpretation", False))
    overfit = bool(frame.get("overfitting_awareness", False))
    train_test = bool(frame.get("train_test_distinction", False))
    cm_read = bool(frame.get("confusion_matrix_reading", False))
    iter_ref = bool(frame.get("iterative_refinement", False))

    triggered: set[str] = set()

    # B0: veri yükleme ve inceleme
    if pb == "EXPLORE_DATA" or sc == "TABLE":
        triggered.add("B0")

    # B1: grafik oluşturma (EXPLORE_DATA in SETUP phase, not off-task)
    if pb == "EXPLORE_DATA" and dp == "SETUP" and not off:
        triggered.add("B1")

    # B2: movable value / threshold adjustment
    if thr_reason or pb == "TUNE_THRESHOLD":
        triggered.add("B2")

    # B3: hedef değişkeni belirleme
    if dep_var_set or sb == "SELECT_TARGET":
        triggered.add("B3")

    # B4: feature seçimi
    if sys_var:
        triggered.add("B4")

    # B5: sınıf tanımlama — no signal in schema, always absent
    # (not added)

    # B6: threshold seçimi
    if pb == "TUNE_THRESHOLD" or (split_visible and thr_reason):
        triggered.add("B6")

    # B7: model çalıştırma
    if tree_has_nodes or pb == "BUILD_TREE":
        triggered.add("B7")

    # B8: çıktı yorumlama
    if acc_interp or pb == "EVALUATE_MODEL":
        triggered.add("B8")

    # B9: train/test ayrımı
    if train_test:
        triggered.add("B9")

    # B10: çok katmanlı ağaç (depth 2+) — no reliable signal in schema; always absent
    # (iterative_refinement only means "tried again", not depth 2+)

    # B11: grafik tabanlı eşik optimizasyonu
    if thr_reason and iter_ref:
        triggered.add("B11")

    # B12: CTR yönetimi
    if cm_read or cm_visible:
        triggered.add("B12")

    # B13: sensitivity/MCR trade-off — only explicit overfitting_awareness signal
    # COMPARE_MODELS + cm_reading is Deepen, not Create
    if overfit:
        triggered.add("B13")

    return triggered


# ---------------------------------------------------------------------------
# Student-level aggregation
# ---------------------------------------------------------------------------

def convert_student(student: str, session: str) -> dict | None:
    """Read codap_frame_analyses.json, return final_scored.json dict."""
    audio_dir = DATA_ROOT / SESSION_AUDIO_DIRS[session] / student

    # Find frame analyses file (may have a version suffix)
    candidates = sorted(audio_dir.glob(f"{student}_codap_frame_analyses*.json"))
    if not candidates:
        print(f"  [{student}] No codap_frame_analyses.json found — skipping")
        return None

    src = candidates[-1]  # latest version
    raw = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        frames = raw
    elif isinstance(raw, dict) and "frame_analyses" in raw:
        frames = raw["frame_analyses"]
    else:
        print(f"  [{student}] Unexpected format in {src.name} — skipping")
        return None

    print(f"  [{student}] {src.name} — {len(frames)} frames")

    # Count triggered frames per behavior
    b_frame_counts: dict[str, int] = {b: 0 for b in CODAP_BEHAVIORS}
    confidence_votes: dict[str, list[str]] = {b: [] for b in CODAP_BEHAVIORS}

    for frame in frames:
        triggered = _triggered_behaviors(frame)
        raw_conf = (frame.get("analysis_confidence") or "MEDIUM").upper()
        conf_label = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}.get(raw_conf, "Medium")
        for b in triggered:
            if b in b_frame_counts:
                b_frame_counts[b] += 1
                confidence_votes[b].append(conf_label)

    # Build behaviors dict
    behaviors: dict[str, dict] = {}

    for b in CODAP_BEHAVIORS:
        count = b_frame_counts[b]
        if count == 0:
            behaviors[b] = {
                "decision": "not_observed",
                "level": None,
                "confidence": None,
            }
        else:
            # Majority confidence vote
            votes = confidence_votes[b]
            conf = max(set(votes), key=votes.count)
            behaviors[b] = {
                "decision": "observed",
                "level": "Deepen",
                "confidence": conf,
                "deepen_frame_count": count,
            }

    for b in COLAB_ONLY:
        behaviors[b] = {
            "decision": "not_observed",
            "level": None,
            "confidence": None,
        }

    return {
        "rubric_id": "codap_arbor_v4_candidate",
        "schema_version": "4.1",
        "student_id": student,
        "session_key": session,
        "audio_available": (audio_dir / f"{student}_transcript.json").exists()
            or bool(list(audio_dir.glob(f"{student}*transcript*.json"))),
        "scoring_note": "Converted from codap_frame_analyses.json via deterministic B-mapping. No API calls.",
        "behaviors": behaviors,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def find_students_with_analyses(session: str) -> list[str]:
    audio_root = DATA_ROOT / SESSION_AUDIO_DIRS[session]
    if not audio_root.exists():
        return []
    students = []
    for d in sorted(audio_root.iterdir()):
        if d.is_dir() and list(d.glob(f"{d.name}_codap_frame_analyses*.json")):
            students.append(d.name)
    return students


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert frame analyses to final_scored.json")
    parser.add_argument("--session", required=True, choices=("21apr", "28apr"))
    parser.add_argument("--students", nargs="*")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    students = args.students or find_students_with_analyses(args.session)
    if not students:
        print(f"No students with codap_frame_analyses for session {args.session}")
        sys.exit(1)

    print(f"Session  : {args.session}")
    print(f"Students : {students}")
    print(f"Dry run  : {args.dry_run}")
    print()

    log_dir = REPO_ROOT / "logs" / "pipeline_runs"
    log_dir.mkdir(parents=True, exist_ok=True)

    ok, skipped, failed = [], [], []

    for student in students:
        out_path = ps.mmla_final_scored_path(student, args.session)

        if out_path.exists():
            print(f"  [{student}] Already exists — skipping ({out_path})")
            skipped.append(student)
            continue

        result = convert_student(student, args.session)
        if result is None:
            failed.append(student)
            continue

        if args.dry_run:
            print(f"  [{student}] DRY RUN — would write {out_path}")
            b_summary = {b: d["decision"] for b, d in result["behaviors"].items() if b in CODAP_BEHAVIORS}
            observed = [b for b, d in b_summary.items() if d == "observed"]
            print(f"    Observed: {observed}")
            ok.append(student)
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"  [{student}] Written → {out_path}")
        ok.append(student)

    print(f"\nDone — {len(ok)} converted, {len(skipped)} skipped, {len(failed)} failed")


if __name__ == "__main__":
    main()
