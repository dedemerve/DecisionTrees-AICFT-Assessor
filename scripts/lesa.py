#!/usr/bin/env python3
"""LESA — Learning Episode Segmentation Agent.

Groups consecutive frame annotations into coherent learning episodes.
An episode boundary is triggered when any of these change:
  1. dominant_behavior (primary_behavior)
  2. decision_tree_state  (derived via state machine)
  3. evaluation_strategy  (derived from accuracy + confusion matrix indicators)
  4. learning_objective   (derived from primary_behavior → objective mapping)

Minimum episode length: 2 frames. Single-frame noise is merged into
the preceding episode.

Usage:
    python scripts/lesa.py Marco --session-date 2026-04-21
    python scripts/lesa.py Marco --session-date 2026-04-21 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("lesa")

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
}

MIN_EPISODE_FRAMES = 2


# ─────────────────────────────────────────────────────────────
# State machine: decision_tree_state
# Priority: REFINING > EVALUATED > STRUCTURED > BUILDING > EMPTY
# ─────────────────────────────────────────────────────────────

def derive_tree_state(frame: dict[str, Any]) -> str:
    if frame.get("iterative_refinement"):
        return "REFINING"
    if frame.get("accuracy_visible") or frame.get("confusion_matrix_visible"):
        return "EVALUATED"
    if frame.get("tree_has_nodes") and frame.get("dependent_variable_set"):
        return "STRUCTURED"
    if frame.get("tree_has_nodes"):
        return "BUILDING"
    return "EMPTY"


# ─────────────────────────────────────────────────────────────
# Boundary signal: evaluation_strategy
# ─────────────────────────────────────────────────────────────

def derive_eval_strategy(frame: dict[str, Any]) -> str:
    acc = frame.get("accuracy_interpretation") or frame.get("accuracy_visible")
    cm = frame.get("confusion_matrix_reading") or frame.get("confusion_matrix_visible")
    if acc and cm:
        return "MULTI_METRIC"
    if cm:
        return "CONFUSION_MATRIX_ONLY"
    if acc:
        return "ACCURACY_ONLY"
    return "NONE"


# ─────────────────────────────────────────────────────────────
# Boundary signal: learning_objective
# ─────────────────────────────────────────────────────────────

_BEHAVIOR_TO_OBJECTIVE: dict[str, str] = {
    "EXPLORE_DATA":      "UNDERSTAND_DATA",
    "SELECT_TARGET":     "DEFINE_PROBLEM",
    "BUILD_TREE":        "CONSTRUCT_MODEL",
    "TUNE_THRESHOLD":    "OPTIMIZE_MODEL",
    "EVALUATE_MODEL":    "ASSESS_PERFORMANCE",
    "COMPARE_MODELS":    "COMPARE_ALTERNATIVES",
    "INTERPRET_RESULTS": "INTERPRET_FINDINGS",
    "IDLE_THINKING":     "REFLECT",
    "OFF_TASK":          "OFF_TASK",
}


def derive_objective(frame: dict[str, Any]) -> str:
    return _BEHAVIOR_TO_OBJECTIVE.get(frame.get("primary_behavior", ""), "UNKNOWN")


# ─────────────────────────────────────────────────────────────
# Episode boundary detection
# ─────────────────────────────────────────────────────────────

def boundary_key(frame: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        frame.get("primary_behavior", ""),
        derive_tree_state(frame),
        derive_eval_strategy(frame),
        derive_objective(frame),
    )


# ─────────────────────────────────────────────────────────────
# Segmentation
# ─────────────────────────────────────────────────────────────

def segment_episodes(frames: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not frames:
        return []

    groups: list[list[dict[str, Any]]] = []
    current_group: list[dict[str, Any]] = [frames[0]]
    current_key = boundary_key(frames[0])

    for frame in frames[1:]:
        key = boundary_key(frame)
        if key != current_key:
            groups.append(current_group)
            current_group = [frame]
            current_key = key
        else:
            current_group.append(frame)
    groups.append(current_group)

    # Merge single-frame groups into previous episode
    merged: list[list[dict[str, Any]]] = []
    for group in groups:
        if len(group) < MIN_EPISODE_FRAMES and merged:
            merged[-1].extend(group)
        else:
            merged.append(group)

    # Build episode records
    episodes: list[dict[str, Any]] = []
    for idx, group in enumerate(merged, start=1):
        first = group[0]
        last = group[-1]
        tree_state = derive_tree_state(first)
        eval_strategy = derive_eval_strategy(first)

        # dominant_behavior = most frequent primary_behavior in group
        behavior_counts: dict[str, int] = {}
        for f in group:
            b = f.get("primary_behavior", "")
            behavior_counts[b] = behavior_counts.get(b, 0) + 1
        dominant_behavior = max(behavior_counts, key=lambda k: behavior_counts[k])

        # confidence: lowest confidence in group
        conf_rank = {"HIGH": 2, "MEDIUM": 1, "LOW": 0}
        min_conf = min(group, key=lambda f: conf_rank.get(f.get("analysis_confidence", "LOW"), 0))
        episode_confidence = min_conf.get("analysis_confidence", "LOW")

        episode: dict[str, Any] = {
            "episode_id": f"EP{idx:02d}",
            "start_frame": first["frame_number"],
            "end_frame": last["frame_number"],
            "start_ms": first["timestamp_ms"],
            "end_ms": last["timestamp_ms"],
            "duration_s": round((last["timestamp_ms"] - first["timestamp_ms"]) / 1000, 1),
            "dominant_behavior": dominant_behavior,
            "learning_objective": derive_objective(first),
            "deepen_phase": first.get("deepen_phase", ""),
            "decision_tree_state": tree_state,
            "evaluation_strategy": eval_strategy,
            "frame_count": len(group),
            "frame_ids": [f["frame_number"] for f in group],
            "episode_confidence": episode_confidence,
            "log_events": [],
        }
        episodes.append(episode)

    return episodes


# ─────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────

def load_frames(student_id: str, session_date: str) -> list[dict[str, Any]]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date)
    if not subdir:
        raise ValueError(f"Unknown session_date: {session_date}")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_codap_frame_analyses.jsonl"
    if not path.is_file():
        raise FileNotFoundError(path)
    frames = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    return sorted(frames, key=lambda f: f["frame_number"])


def write_episodes(episodes: list[dict[str, Any]], student_id: str, session_date: str) -> Path:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    out_dir = REPO_ROOT / "data_sources_2026" / subdir / student_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{student_id}_learning_episodes.json"
    payload = {
        "schema_version": "lesa-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "session_date": session_date,
        "episode_count": len(episodes),
        "episodes": episodes,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="LESA — Learning Episode Segmentation Agent")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    frames = load_frames(args.student, args.session_date)
    LOGGER.info("Loaded %d frames for %s / %s", len(frames), args.student, args.session_date)

    episodes = segment_episodes(frames)
    LOGGER.info("Segmented into %d episodes", len(episodes))

    for ep in episodes:
        LOGGER.info(
            "  %s  frames=%d  %s → %s  [%s / %s / %s]",
            ep["episode_id"], ep["frame_count"],
            ep["dominant_behavior"], ep["learning_objective"],
            ep["decision_tree_state"], ep["evaluation_strategy"],
            ep["episode_confidence"],
        )

    if args.dry_run:
        print(json.dumps(episodes, indent=2, ensure_ascii=False))
        return

    out_path = write_episodes(episodes, args.student, args.session_date)
    LOGGER.info("Written: %s", out_path)


if __name__ == "__main__":
    main()
