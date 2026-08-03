#!/usr/bin/env python3
"""Generate observation_steps.json for students who have no usable notebook.

Sources used (in priority order):
  1. codap_frame_analyses.jsonl — AI-analyzed frames with behavioral classification
  2. b15_log.json votat_intervals — emit-level segmentation from log events
  3. b15_log.json summary stats — fallback stub with b15 context

Targets: Marco (all 3 sessions), Ulysses (all 3 sessions).

Usage:
    python scripts/build_missing_observation_steps.py
    python scripts/build_missing_observation_steps.py --dry-run
    python scripts/build_missing_observation_steps.py --student Marco
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import defaultdict
from datetime import datetime, timezone
from itertools import groupby
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
DATA = REPO / "data_sources_2026"
OUT  = REPO / "training_datasets" / "2026"

SESSION_DIRS = {
    "codap_21apr": "codap_arbor_21april_audio",
    "codap_28apr": "codap_arbor_28april_audio",
    "colab_05may": "colab_python_audio",
}

log = logging.getLogger("build_missing_obs")

# ── Behavior → cognitive label mapping ───────────────────────────────────────
_BEHAVIOR_TO_COGNITIVE = {
    "EXPLORE_DATA":       "EXPLORE",
    "SELECT_TARGET":      "EXPLORE",
    "ADD_SPLIT":          "EXPLORE",
    "NAVIGATE_TREE":      "EXPLORE",
    "EVALUATE_ACCURACY":  "EVALUATE",
    "TUNE_THRESHOLD":     "TUNE",
    "SEEK_HELP":          "EXPLORE",
    "IDLE_THINKING":      "EXPLORE",
    "STRUGGLE":           "EXPLORE",
    "EMIT_TREE":          "EVALUATE",
    "RUN_CELL":           "EVALUATE",
}

_BEHAVIOR_TO_PEDAGOGY = {
    "EXPLORE_DATA":       "Domain-knowledge driven",
    "SELECT_TARGET":      "Domain-knowledge driven",
    "ADD_SPLIT":          "Trial-and-error",
    "TUNE_THRESHOLD":     "Trial-and-error",
    "EVALUATE_ACCURACY":  "Domain-knowledge driven",
    "SEEK_HELP":          "Trial-and-error",
    "IDLE_THINKING":      "Domain-knowledge driven",
    "STRUGGLE":           "Trial-and-error",
    "EMIT_TREE":          "Domain-knowledge driven",
    "RUN_CELL":           "Trial-and-error",
}

_BEHAVIOR_TO_LO = {
    "EXPLORE_DATA":       "Acquire",
    "SELECT_TARGET":      "Acquire",
    "ADD_SPLIT":          "Acquire",
    "NAVIGATE_TREE":      "Acquire",
    "EVALUATE_ACCURACY":  "Deepen",
    "TUNE_THRESHOLD":     "Deepen",
    "SEEK_HELP":          "Acquire",
    "IDLE_THINKING":      "Acquire",
    "STRUGGLE":           "Acquire",
    "EMIT_TREE":          "Deepen",
    "RUN_CELL":           "Deepen",
}


def _step_from_frames(
    phase_label: str,
    frames: list[dict[str, Any]],
    step_index: int,
) -> dict[str, Any]:
    """Build one observation step from a group of frames with the same behavior."""
    first = frames[0]
    last  = frames[-1]
    ts_start = first.get("timestamp_ms", 0)
    ts_end   = last.get("timestamp_ms",  ts_start)

    # Collect UI notes and inferred actions across frames in this phase
    notes   = [f["log_visual_match"].get("inferred_action", "") for f in frames
               if f.get("log_visual_match", {}).get("inferred_action")]
    ui_text = [f["screen_state"].get("ui_notes", "") for f in frames
               if f.get("screen_state", {}).get("ui_notes")]

    # Build narrative from best-evidence frame (highest analysis_confidence)
    evidence_frames = [f for f in frames
                       if (f.get("frame_quality") or {}).get("analysis_confidence") == "high"]
    best = evidence_frames[0] if evidence_frames else first
    bc   = best.get("behavioral_classification") or {}
    narrative = bc.get("behavior_evidence") or ""
    if notes:
        narrative = notes[0]

    cognitive = _BEHAVIOR_TO_COGNITIVE.get(phase_label, "EXPLORE")
    pedagogy  = _BEHAVIOR_TO_PEDAGOGY.get(phase_label, "Domain-knowledge driven")
    lo_level  = _BEHAVIOR_TO_LO.get(phase_label, "Acquire")

    # Check flags across all frames
    any_struggle    = any((f.get("flags") or {}).get("technical_difficulty") for f in frames)
    any_misconc     = any((f.get("flags") or {}).get("misconception_detected") for f in frames)
    any_aha         = any((f.get("flags") or {}).get("aha_moment_candidate")    for f in frames)

    step: dict[str, Any] = {
        "step_index": step_index,
        "source_cell_type": "frame_analysis",
        "uzman_nitel_gozlemi": narrative,
        "labels": {
            "bilişsel_davranış_kategorisi": cognitive,
            "pedagojik_strateji": pedagogy,
            "unesco_ai_cft_level": lo_level,
        },
        "phase": phase_label,
        "frame_span": {
            "first_frame": first.get("frame_id") or first.get("frame_number"),
            "last_frame":  last.get("frame_id")  or last.get("frame_number"),
            "timestamp_start_ms": ts_start,
            "timestamp_end_ms":   ts_end,
            "frame_count":        len(frames),
        },
        "flags": {
            "technical_difficulty": any_struggle,
            "misconception_detected": any_misconc,
            "aha_moment_candidate": any_aha,
        },
        "sequence_pattern": None,
        "ai_cft_evidence_justification": (
            f"Derived from {len(frames)} AI-analyzed frames ({ts_start//1000}s–{ts_end//1000}s). "
            f"Primary behavior: {phase_label}. Source: codap_frame_analyses.jsonl."
        ),
    }
    return step


def _steps_from_frame_analyses(
    jsonl_path: Path,
    student: str,
    session: str,
) -> list[dict[str, Any]]:
    """Derive observation steps by grouping consecutive frames by behavioral phase."""
    frames = [json.loads(l) for l in jsonl_path.read_text().splitlines() if l.strip()]
    if not frames:
        return []

    # Group by primary_behavior phase transitions
    phases: list[tuple[str, list[dict[str, Any]]]] = []
    for label, group in groupby(
        frames,
        key=lambda f: (f.get("behavioral_classification") or {}).get("primary_behavior", "UNKNOWN")
    ):
        phases.append((label, list(group)))

    # Merge very short phases (< 3 frames) into adjacent phase
    merged: list[tuple[str, list[dict[str, Any]]]] = []
    for label, group in phases:
        if merged and len(group) < 3:
            prev_label, prev_group = merged[-1]
            merged[-1] = (prev_label, prev_group + group)
        else:
            merged.append((label, group))

    steps = []
    for i, (label, group) in enumerate(merged):
        steps.append(_step_from_frames(label, group, i))

    log.info(
        "%s/%s: %d frames → %d phases → %d observation steps (frame_analyses source)",
        student, session, len(frames), len(phases), len(steps)
    )
    return steps


def _steps_from_b15_log(
    log_path: Path,
    student: str,
    session: str,
    total_duration_ms: int | None = None,
) -> list[dict[str, Any]]:
    """Derive observation steps from votat_intervals in b15 log."""
    b15 = json.loads(log_path.read_text())
    intervals = b15.get("votat_intervals") or []
    total_emits: int = b15.get("total_emits") or 0
    b15_level: str = b15.get("b15_level") or "Unknown"
    b15_observed: bool = b15.get("b15_observed", False)

    if not intervals:
        # No intervals — create single summary step
        return [_b15_summary_step(b15, student, session, step_index=0)]

    steps = []
    for i, interval in enumerate(intervals):
        emit_a = interval.get("emit_a_ms") or 0
        emit_b = interval.get("emit_b_ms") or emit_a
        pred_changes = interval.get("predictor_changes", 0)
        thresh_changes = interval.get("threshold_changes", 0)
        is_votat = interval.get("is_votat", False)
        dim_changed = interval.get("dimension_changed", "unknown")

        if is_votat:
            if dim_changed == "predictor":
                behavior = "Farklı bir tahmin değişkeni seçildi (VOTAT - predictor change)"
                cognitive = "TUNE"
                lo = "Deepen"
            elif dim_changed == "threshold":
                behavior = "Eşik değeri değiştirildi (VOTAT - threshold change)"
                cognitive = "TUNE"
                lo = "Deepen"
            else:
                behavior = "VOTAT davranışı gözlemlendi (çoklu boyut değişimi)"
                cognitive = "EVALUATE"
                lo = "Deepen"
        else:
            behavior = (
                f"İki emit arasında değişken={pred_changes} eşik={thresh_changes} "
                f"değişim (VOTAT değil)"
            )
            cognitive = "EXPLORE"
            lo = "Acquire"

        step: dict[str, Any] = {
            "step_index": i,
            "source_cell_type": "b15_log_interval",
            "uzman_nitel_gozlemi": behavior,
            "labels": {
                "bilişsel_davranış_kategorisi": cognitive,
                "pedagojik_strateji": "Trial-and-error" if is_votat else "Domain-knowledge driven",
                "unesco_ai_cft_level": lo,
            },
            "emit_interval": {
                "emit_a_ms": emit_a,
                "emit_b_ms": emit_b,
                "duration_s": round((emit_b - emit_a) / 1000, 1),
                "predictor_changes": pred_changes,
                "threshold_changes": thresh_changes,
                "is_votat": is_votat,
                "dimension_changed": dim_changed,
            },
            "sequence_pattern": "VOTAT" if is_votat else None,
            "ai_cft_evidence_justification": (
                f"Derived from b15_log votat_interval {i}. "
                f"B15 level: {b15_level}, total_emits={total_emits}. "
                f"Source: {log_path.name}"
            ),
        }
        steps.append(step)

    # Add a final summary step for overall session context
    steps.append(_b15_summary_step(b15, student, session, step_index=len(steps)))

    log.info(
        "%s/%s: b15 log → %d votat_intervals → %d steps (b15_log source)",
        student, session, len(intervals), len(steps)
    )
    return steps


def _b15_summary_step(
    b15: dict[str, Any],
    student: str,
    session: str,
    step_index: int,
) -> dict[str, Any]:
    total_emits = b15.get("total_emits") or 0
    b15_level   = b15.get("b15_level") or "Unknown"
    b15_observed = b15.get("b15_observed", False)
    votat_rate  = b15.get("votat_rate") or 0.0
    max_consec  = b15.get("max_consecutive_votat") or 0

    narrative = (
        f"Oturum özeti: {total_emits} emit işlemi. "
        f"B15 davranışı {'gözlemlendi' if b15_observed else 'gözlemlenmedi'}. "
        f"Seviye: {b15_level}. VOTAT oranı: %{votat_rate*100:.0f}. "
        f"Maksimum ardışık VOTAT: {max_consec}."
    )
    cognitive = "EVALUATE" if b15_observed else "EXPLORE"
    lo = "Deepen" if b15_level in ("Deepen", "Create") else "Acquire"

    return {
        "step_index": step_index,
        "source_cell_type": "b15_log_summary",
        "uzman_nitel_gozlemi": narrative,
        "labels": {
            "bilişsel_davranış_kategorisi": cognitive,
            "pedagojik_strateji": "Domain-knowledge driven",
            "unesco_ai_cft_level": lo,
        },
        "b15_summary": {
            "total_emits": total_emits,
            "b15_observed": b15_observed,
            "b15_level": b15_level,
            "votat_rate": votat_rate,
            "max_consecutive_votat": max_consec,
        },
        "sequence_pattern": None,
        "ai_cft_evidence_justification": (
            f"Session-level b15 summary. Source: b15_log.json. "
            f"No notebook available for {student}/{session}."
        ),
    }


def _count_frames(student: str, session: str) -> int:
    dir_name = SESSION_DIRS.get(session, "")
    frames_dir = DATA / dir_name / student / f"{student}_frames"
    if not frames_dir.exists():
        return 0
    return len(list(frames_dir.glob("*.jpg")))


def _write_obs_steps(
    student: str,
    session: str,
    steps: list[dict[str, Any]],
    source_type: str,
    dry_run: bool,
) -> None:
    n_frames = _count_frames(student, session)
    out_dir  = OUT / student / session / "intermediate"
    out_path = out_dir / f"{student}_observation_steps.json"

    payload: dict[str, Any] = {
        "schema_version": "2026-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student,
        "session": session,
        "source_document": None,
        "source_type": source_type,
        "status": "derived_from_frame_analysis" if source_type == "frame_analysis" else "derived_from_b15_log",
        "observation_steps": steps,
        "step_count": len(steps),
        "frame_count": n_frames,
        "alignment_ready": len(steps) > 0 and n_frames > 0,
    }

    if dry_run:
        print(f"[DRY-RUN] {student}/{session}: {len(steps)} steps ({source_type}), {n_frames} frames")
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info(
        "Wrote %s: %d steps (%s), %d frames, alignment_ready=%s",
        out_path, len(steps), source_type, n_frames, payload["alignment_ready"]
    )


def process_student_session(
    student: str,
    session: str,
    dry_run: bool,
) -> dict[str, Any]:
    dir_name = SESSION_DIRS.get(session, "")
    student_dir = DATA / dir_name / student
    if not student_dir.exists():
        log.warning("%s/%s: source dir not found, skipping", student, session)
        return {"student": student, "session": session, "status": "no_source_dir"}

    # Priority 1: codap_frame_analyses.jsonl
    jsonl_path = student_dir / f"{student}_codap_frame_analyses.jsonl"
    if jsonl_path.is_file():
        lines = [l for l in jsonl_path.read_text().splitlines() if l.strip()]
        if lines:
            steps = _steps_from_frame_analyses(jsonl_path, student, session)
            _write_obs_steps(student, session, steps, "frame_analysis", dry_run)
            return {"student": student, "session": session, "status": "frame_analysis", "steps": len(steps)}

    # Priority 2: b15_log with votat_intervals
    b15_files = list(student_dir.glob("*_b15_log.json"))
    if b15_files:
        b15 = json.loads(b15_files[0].read_text())
        intervals = b15.get("votat_intervals") or []
        if intervals or b15.get("total_emits", 0) > 0:
            steps = _steps_from_b15_log(b15_files[0], student, session)
            _write_obs_steps(student, session, steps, "b15_log", dry_run)
            return {"student": student, "session": session, "status": "b15_log", "steps": len(steps)}

    # Fallback: minimal stub
    stub: dict[str, Any] = {
        "step_index": 0,
        "source_cell_type": "stub",
        "uzman_nitel_gozlemi": f"{student} için {session} oturumuna ait kaynak veri bulunamadı.",
        "labels": {
            "bilişsel_davranış_kategorisi": "EXPLORE",
            "pedagojik_strateji": "Domain-knowledge driven",
            "unesco_ai_cft_level": "Acquire",
        },
        "sequence_pattern": None,
        "ai_cft_evidence_justification": "No source data available. Manual review required.",
    }
    _write_obs_steps(student, session, [stub], "stub", dry_run)
    return {"student": student, "session": session, "status": "stub", "steps": 1}


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
    ap = argparse.ArgumentParser(description="Build observation_steps for notebook-less students")
    ap.add_argument("--student", nargs="+", default=["Marco", "Ulysses"])
    ap.add_argument("--session", nargs="+", default=list(SESSION_DIRS.keys()))
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    results = []
    for student in args.student:
        for session in args.session:
            r = process_student_session(student, session, args.dry_run)
            results.append(r)

    print(f"\nDone. {len(results)} sessions processed.")
    for r in results:
        print(f"  {r['student']}/{r['session']}: {r['status']}  steps={r.get('steps','?')}")


if __name__ == "__main__":
    main()
