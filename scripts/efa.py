#!/usr/bin/env python3
"""EFA — Evidence Fusion Agent.

Deterministic aggregator. No API call.

Reads frame annotations, learning episodes (with log events), and TEE output.
For each episode, packages all available evidence into a single evidence bundle.

Output: {student}_evidence_packages.json

Usage:
    python scripts/efa.py Marco --session-date 2026-04-21
"""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("efa")

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
}


# ─────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────

def load_frames(student_id: str, session_date: str) -> list[dict[str, Any]]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_codap_frame_analyses.jsonl"
    if not path.is_file():
        raise FileNotFoundError(f"Frame JSONL not found: {path}")
    frames = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            frames.append(json.loads(line))
    LOGGER.info("Loaded %d frames", len(frames))
    return frames


def load_episodes(student_id: str, session_date: str) -> tuple[dict[str, Any], Path]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_learning_episodes.json"
    if not path.is_file():
        raise FileNotFoundError(f"Episode file not found: {path}. Run lesa.py and log_synchronizer.py first.")
    return json.loads(path.read_text(encoding="utf-8")), path


def load_tee(student_id: str, session_date: str) -> dict[str, Any] | None:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_transcript_evidence.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────
# Log event summary
# ─────────────────────────────────────────────────────────────

def summarize_log_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    for e in events:
        t = e.get("event_type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1
    return {
        "event_count": len(events),
        "event_type_counts": dict(sorted(type_counts.items(), key=lambda x: -x[1])),
        "events": events,
    }


# ─────────────────────────────────────────────────────────────
# Frame summary for an episode
# ─────────────────────────────────────────────────────────────

BOOLEAN_INDICATORS = [
    "tree_has_nodes", "dependent_variable_set", "split_values_visible",
    "accuracy_visible", "confusion_matrix_visible",
    "systematic_variable_selection", "threshold_reasoning",
    "accuracy_interpretation", "overfitting_awareness",
    "train_test_distinction", "confusion_matrix_reading",
    "iterative_refinement", "off_task", "technical_difficulty",
    "misconception_detected", "aha_moment_candidate",
]


def summarize_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    if not frames:
        return {"frame_count": 0, "frames": [], "signal_summary": {}}

    signal_summary: dict[str, Any] = {}
    for key in BOOLEAN_INDICATORS:
        true_frames = [f["frame_number"] for f in frames if f.get(key)]
        if true_frames:
            signal_summary[key] = true_frames

    behavior_counts: dict[str, int] = {}
    for f in frames:
        b = f.get("primary_behavior", "UNKNOWN")
        behavior_counts[b] = behavior_counts.get(b, 0) + 1

    phases = list(dict.fromkeys(f.get("deepen_phase") for f in frames if f.get("deepen_phase")))

    return {
        "frame_count": len(frames),
        "frame_numbers": [f["frame_number"] for f in frames],
        "timestamp_range_ms": [frames[0]["timestamp_ms"], frames[-1]["timestamp_ms"]],
        "deepen_phases": phases,
        "behavior_counts": behavior_counts,
        "signal_summary": signal_summary,
        "frames": frames,
    }


# ─────────────────────────────────────────────────────────────
# TEE evidence for an episode time window
# ─────────────────────────────────────────────────────────────

def filter_verbal_evidence(
    tee: dict[str, Any] | None,
    start_ms: int,
    end_ms: int,
) -> dict[str, Any]:
    if tee is None or tee.get("status") != "AVAILABLE":
        status = tee.get("status", "UNAVAILABLE") if tee else "UNAVAILABLE"
        reason = tee.get("reason", "no_tee_file") if tee else "no_tee_file"
        return {"status": status, "reason": reason, "utterances": []}

    start_s = start_ms / 1000.0
    end_s = end_ms / 1000.0
    utterances = [
        u for u in tee.get("utterances", [])
        if u.get("timestamp_start", 0) >= start_s and u.get("timestamp_end", 0) <= end_s
    ]
    return {"status": "AVAILABLE", "reason": None, "utterances": utterances}


# ─────────────────────────────────────────────────────────────
# Core fusion
# ─────────────────────────────────────────────────────────────

def fuse_episode(
    episode: dict[str, Any],
    frames: list[dict[str, Any]],
    tee: dict[str, Any] | None,
) -> dict[str, Any]:
    start_ms = episode["start_ms"]
    end_ms = episode["end_ms"]

    episode_frames = [
        f for f in frames
        if start_ms <= f.get("timestamp_ms", 0) <= end_ms
    ]

    log_summary = summarize_log_events(episode.get("log_events", []))
    frame_summary = summarize_frames(episode_frames)
    verbal = filter_verbal_evidence(tee, start_ms, end_ms)

    return {
        "episode_id": episode["episode_id"],
        "time_window": {"start_ms": start_ms, "end_ms": end_ms},
        "dominant_behavior": episode.get("dominant_behavior"),
        "decision_tree_state": episode.get("decision_tree_state"),
        "evaluation_strategy": episode.get("evaluation_strategy"),
        "learning_objective": episode.get("learning_objective"),
        "frame_evidence": frame_summary,
        "log_evidence": log_summary,
        "verbal_evidence": verbal,
        "metrics": None,
    }


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="EFA — Evidence Fusion Agent")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    frames = load_frames(args.student, args.session_date)
    payload, ep_path = load_episodes(args.student, args.session_date)
    tee = load_tee(args.student, args.session_date)

    if tee:
        LOGGER.info("TEE: status=%s", tee.get("status"))
    else:
        LOGGER.info("TEE: not found — verbal evidence UNAVAILABLE")

    episodes = payload.get("episodes", [])
    packages = [fuse_episode(ep, frames, tee) for ep in episodes]

    LOGGER.info("Fused %d evidence packages", len(packages))
    for pkg in packages:
        LOGGER.info(
            "  %s: frames=%d  log_events=%d  utterances=%d",
            pkg["episode_id"],
            pkg["frame_evidence"]["frame_count"],
            pkg["log_evidence"]["event_count"],
            len(pkg["verbal_evidence"]["utterances"]),
        )

    subdir = SESSION_AUDIO_ROOTS.get(args.session_date, "")
    out_dir = REPO_ROOT / "data_sources_2026" / subdir / args.student
    out_path = out_dir / f"{args.student}_evidence_packages.json"

    output = {
        "efa_version": "1.0",
        "student_id": args.student,
        "session_date": args.session_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "episode_count": len(packages),
        "evidence_packages": packages,
    }
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Written: %s", out_path)


if __name__ == "__main__":
    main()
