#!/usr/bin/env python3
"""LPG — Learning Process Graph builder.

Deterministic. No API call.

Converts an LPRA learning_process_model.json into a graph structure
compatible with process mining, Petri net, and state-transition analysis.

Nodes   = learning episodes
Edges   = transitions between episodes
Subgraph = intra-episode micro-cycles detected from log event sequences

Output: {student}_learning_process_graph.json

Usage:
    python scripts/lpg.py Marco --session-date 2026-04-21
"""

from __future__ import annotations

import argparse
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("lpg")

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
}

# Events that signal a model-change action
MODIFICATION_EVENTS = {
    "attribute_swap", "set_dependent_variable", "set_split_value",
    "add_attribute", "remove_attribute", "clear_tree",
}
# Events that signal an evaluation action
EVALUATION_EVENTS = {
    "emit_tree_data", "read_accuracy", "read_confusion_matrix",
}


# ─────────────────────────────────────────────────────────────
# Loaders
# ─────────────────────────────────────────────────────────────

def load_lpra(student_id: str, session_date: str) -> tuple[dict[str, Any], Path]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_learning_process_model.json"
    if not path.is_file():
        raise FileNotFoundError(f"LPRA output not found: {path}. Run lpra.py first.")
    return json.loads(path.read_text(encoding="utf-8")), path


def load_episodes(student_id: str, session_date: str) -> list[dict[str, Any]]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_learning_episodes.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("episodes", [])


# ─────────────────────────────────────────────────────────────
# Graph node construction
# ─────────────────────────────────────────────────────────────

def build_node(episode: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": episode["episode_id"],
        "label": episode.get("dominant_behavior", "UNKNOWN"),
        "learning_objective": episode.get("learning_objective"),
        "decision_tree_state": episode.get("decision_tree_state"),
        "evaluation_strategy": episode.get("evaluation_strategy"),
        "deepen_phase": episode.get("deepen_phase"),
        "start_ms": episode["start_ms"],
        "end_ms": episode["end_ms"],
        "duration_ms": episode["end_ms"] - episode["start_ms"],
        "frame_count": episode.get("frame_count", 0),
        "log_event_count": len(episode.get("log_events", [])),
    }


# ─────────────────────────────────────────────────────────────
# Edge construction from LPRA transitions
# ─────────────────────────────────────────────────────────────

def build_edges(transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = []
    for t in transitions:
        edges.append({
            "from": t.get("from_episode"),
            "to": t.get("to_episode"),
            "type": t.get("transition_type", "OTHER"),
            "trigger": t.get("trigger"),
        })
    return edges


# ─────────────────────────────────────────────────────────────
# Micro-cycle detection within an episode's log events
# ─────────────────────────────────────────────────────────────

def detect_micro_cycles(log_events: list[dict[str, Any]]) -> dict[str, Any]:
    """Detect MODIFY → EVALUATE cycles in log event sequence."""
    cycles: list[dict[str, Any]] = []
    i = 0
    events = log_events
    while i < len(events):
        et = events[i].get("event_type", "")
        if et in MODIFICATION_EVENTS:
            # Look for a following evaluation event
            j = i + 1
            while j < len(events) and events[j].get("event_type") not in EVALUATION_EVENTS and j - i < 10:
                j += 1
            if j < len(events) and events[j].get("event_type") in EVALUATION_EVENTS:
                cycles.append({
                    "modify_event": et,
                    "modify_offset_ms": events[i].get("offset_ms"),
                    "evaluate_event": events[j].get("event_type"),
                    "evaluate_offset_ms": events[j].get("offset_ms"),
                })
                i = j + 1
                continue
        i += 1

    modify_counts = Counter(c["modify_event"] for c in cycles)
    eval_counts = Counter(c["evaluate_event"] for c in cycles)

    return {
        "cycle_count": len(cycles),
        "modify_event_counts": dict(modify_counts),
        "evaluate_event_counts": dict(eval_counts),
        "cycles": cycles,
    }


# ─────────────────────────────────────────────────────────────
# Process sequence
# ─────────────────────────────────────────────────────────────

def build_process_sequence(episodes: list[dict[str, Any]]) -> list[str]:
    return [ep["episode_id"] for ep in episodes]


# ─────────────────────────────────────────────────────────────
# State transition table
# ─────────────────────────────────────────────────────────────

def build_state_transitions(episodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    transitions = []
    for i in range(len(episodes) - 1):
        a = episodes[i]
        b = episodes[i + 1]
        transitions.append({
            "from_episode": a["episode_id"],
            "from_state": a.get("decision_tree_state"),
            "from_behavior": a.get("dominant_behavior"),
            "to_episode": b["episode_id"],
            "to_state": b.get("decision_tree_state"),
            "to_behavior": b.get("dominant_behavior"),
            "boundary_ms": a["end_ms"],
        })
    return transitions


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="LPG — Learning Process Graph builder")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    args = parser.parse_args()

    lpra, _ = load_lpra(args.student, args.session_date)
    episodes = load_episodes(args.student, args.session_date)

    nodes = [build_node(ep) for ep in episodes]
    edges = build_edges(lpra.get("strategy_transitions", []))
    process_sequence = build_process_sequence(episodes)
    state_transitions = build_state_transitions(episodes)

    # Micro-cycle analysis per episode
    episode_micro_cycles = []
    for ep in episodes:
        mc = detect_micro_cycles(ep.get("log_events", []))
        episode_micro_cycles.append({
            "episode_id": ep["episode_id"],
            "micro_cycles": mc,
        })
        if mc["cycle_count"] > 0:
            LOGGER.info("  %s: %d MODIFY→EVALUATE micro-cycles", ep["episode_id"], mc["cycle_count"])

    total_cycles = sum(e["micro_cycles"]["cycle_count"] for e in episode_micro_cycles)

    graph = {
        "lpg_version": "1.0",
        "student_id": args.student,
        "session_date": args.session_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_lpra_version": lpra.get("_lpra_meta", {}).get("lpra_version"),
        "workflow_pattern": lpra.get("workflow_pattern", {}).get("pattern"),
        "overall_strategy": lpra.get("overall_strategy", {}).get("category"),
        "graph": {
            "node_count": len(nodes),
            "edge_count": len(edges),
            "nodes": nodes,
            "edges": edges,
        },
        "process_sequence": process_sequence,
        "state_transitions": state_transitions,
        "micro_cycle_analysis": {
            "total_micro_cycles": total_cycles,
            "by_episode": episode_micro_cycles,
        },
        "petri_net_hints": {
            "places": [f"after_{ep['episode_id']}" for ep in episodes],
            "transitions": [
                f"{t['from_episode']}_to_{t['to_episode']}" for t in state_transitions
            ],
            "initial_marking": process_sequence[0] if process_sequence else None,
            "final_marking": process_sequence[-1] if process_sequence else None,
        },
    }

    subdir = SESSION_AUDIO_ROOTS.get(args.session_date, "")
    out_dir = REPO_ROOT / "data_sources_2026" / subdir / args.student
    out_path = out_dir / f"{args.student}_learning_process_graph.json"
    out_path.write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")

    LOGGER.info("Written: %s", out_path)
    print(f"\nNodes:         {len(nodes)}")
    print(f"Edges:         {len(edges)}")
    print(f"Micro-cycles:  {total_cycles}")
    print(f"Pattern:       {graph['workflow_pattern']}")
    print(f"Output:        {out_path}")


if __name__ == "__main__":
    main()
