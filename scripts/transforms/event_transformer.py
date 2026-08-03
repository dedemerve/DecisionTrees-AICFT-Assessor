#!/usr/bin/env python3
"""Event transformer for anchor event normalization across sessions.

Protocol rule (EPISODE_SEGMENTATION_PROTOCOL_v1.md, line 115):
    "Anchor event EMIT_TREE is replaced by RUN_CELL for sessions where
    students run Python code to fit a tree."

This module applies that substitution and validates temporal consistency
against episode alignment data so the replacement is never silent.

Public API:
    process_anchor_events(events, session_type) -> list[dict]
    validate_anchor_alignment(events, episodes)  -> list[str]
    write_transform_audit(path, events, student_id, session_id)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("event_transformer")

COLAB_SESSION_TYPES = {"colab_05may", "colab", "jupyter", "python"}

_EMIT_TREE_TRIGGERS = {
    "emit_tree",
    "emit function",
    "tree generated",
    "tree re-generated",
    "colab_cell_execution_detected",
    "run_cell",
}


def _is_colab_context(event: dict[str, Any], session_type: str) -> bool:
    """Return True when the event belongs to a Colab/notebook session.

    Per-event session_type takes precedence over the batch-level argument so
    that mixed batches (e.g. a merged log of codap + colab events) are handled
    correctly.
    """
    per_event = (event.get("session_type") or event.get("source") or "").lower()
    if per_event:
        return per_event in COLAB_SESSION_TYPES
    return session_type.lower() in COLAB_SESSION_TYPES


def _looks_like_cell_run(event: dict[str, Any]) -> bool:
    """Heuristic: does this EMIT_TREE event represent a notebook cell execution?"""
    etype = (event.get("event_type") or event.get("type") or "").lower()
    label = (event.get("label") or event.get("description") or "").lower()

    if any(t in label for t in ("run_cell", "cell execution", "fit", "sklearn", "runcell")):
        return True
    if etype in ("colab_cell_execution_detected", "run_cell"):
        return True
    meta = event.get("metadata") or {}
    if meta.get("colab_layer") or meta.get("cell_index") is not None:
        return True
    return False


def process_anchor_events(
    events: list[dict[str, Any]],
    session_type: str = "",
) -> list[dict[str, Any]]:
    """Apply EMIT_TREE -> RUN_CELL substitution for Colab sessions.

    Args:
        events:       Raw event dicts (observation steps, log events, or
                      frame-level anchor annotations).
        session_type: Session identifier string — e.g. "colab_05may".
                      If omitted, per-event heuristics are used.

    Returns:
        New list of event dicts with transformations applied in-place copies.
        Untouched events are returned unchanged (same dict reference).
    """
    out: list[dict[str, Any]] = []

    for event in events:
        etype = (event.get("event_type") or event.get("type") or "").upper()

        if etype != "EMIT_TREE":
            out.append(event)
            continue

        if not (_is_colab_context(event, session_type) or _looks_like_cell_run(event)):
            out.append(event)
            continue

        transformed = {**event}
        transformed["event_type"] = "RUN_CELL"
        if "type" in transformed:
            transformed["type"] = "RUN_CELL"
        transformed["transformed_from"] = "EMIT_TREE"
        transformed["is_anchor_event"] = True
        transformed["transform_applied_at"] = datetime.now(timezone.utc).isoformat()

        log.info(
            "EMIT_TREE -> RUN_CELL at ts=%s (student=%s session=%s)",
            event.get("timestamp_ms", "?"),
            event.get("student_id", "?"),
            session_type or event.get("session_type", "?"),
        )
        out.append(transformed)

    transformed_count = sum(1 for e in out if e.get("transformed_from") == "EMIT_TREE")
    if transformed_count:
        log.info("Transformed %d EMIT_TREE -> RUN_CELL events", transformed_count)

    return out


def validate_anchor_alignment(
    events: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    tolerance_ms: int = 5000,
) -> list[str]:
    """Check that RUN_CELL anchors land within a known episode window.

    Args:
        events:       Transformed event list from process_anchor_events.
        episodes:     Episode dicts with start_ms / end_ms bounds.
        tolerance_ms: Grace window (ms) outside episode bounds still accepted.

    Returns:
        List of warning strings for events that fall outside all episodes.
        Empty list means alignment is clean.
    """
    warnings: list[str] = []
    run_cells = [e for e in events if (e.get("event_type") or e.get("type")) == "RUN_CELL"]

    for event in run_cells:
        ts = event.get("timestamp_ms")
        if ts is None:
            warnings.append(
                f"RUN_CELL event missing timestamp_ms (student={event.get('student_id', '?')})"
            )
            continue

        matched = any(
            (ep.get("start_ms") or 0) - tolerance_ms
            <= ts
            <= (ep.get("end_ms") or float("inf")) + tolerance_ms
            for ep in episodes
        )
        if not matched:
            warnings.append(
                f"RUN_CELL at {ts}ms has no matching episode window "
                f"(student={event.get('student_id', '?')})"
            )

    for w in warnings:
        log.warning("Alignment: %s", w)

    return warnings


def write_transform_audit(
    path: Path,
    events: list[dict[str, Any]],
    student_id: str,
    session_id: str,
) -> None:
    """Write audit trail of applied transformations to an intermediate file.

    Writes to:
        training_datasets/2026/{student}/{session}/intermediate/{student}_observation_steps.json
    in the ``anchor_transform_audit`` field (merged, not overwritten).
    """
    transformed = [e for e in events if e.get("transformed_from") == "EMIT_TREE"]
    if not transformed:
        return

    audit = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "student_id": student_id,
        "session_id": session_id,
        "transform_rule": "EMIT_TREE -> RUN_CELL (EPISODE_SEGMENTATION_PROTOCOL_v1 line 115)",
        "total_transformed": len(transformed),
        "events": [
            {
                "timestamp_ms": e.get("timestamp_ms"),
                "original_type": "EMIT_TREE",
                "new_type": "RUN_CELL",
                "transform_applied_at": e.get("transform_applied_at"),
            }
            for e in transformed
        ],
    }

    existing: dict[str, Any] = {}
    if path.is_file():
        try:
            existing = json.loads(path.read_text())
        except Exception:
            pass

    existing["anchor_transform_audit"] = audit
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(existing, indent=2, ensure_ascii=False))
    log.info("Audit trail written: %s", path)


# ---------------------------------------------------------------------------
# Unit test / smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    mock_events: list[dict[str, Any]] = [
        {
            "event_type": "EMIT_TREE",
            "timestamp_ms": 12000,
            "student_id": "Amy",
            "session_type": "colab_05may",
            "label": "Tree generated after cell run",
        },
        {
            "event_type": "EMIT_TREE",
            "timestamp_ms": 45000,
            "student_id": "Amy",
            "session_type": "colab_05may",
            "label": "colab_cell_execution_detected",
        },
        {
            "event_type": "EMIT_TREE",
            "timestamp_ms": 90000,
            "student_id": "Amy",
            "session_type": "codap_21apr",
            "label": "Emit function triggered",
        },
        {
            "event_type": "SET_TARGET",
            "timestamp_ms": 30000,
            "student_id": "Amy",
            "session_type": "colab_05may",
        },
    ]

    result = process_anchor_events(mock_events, session_type="colab_05may")

    run_cells = [e for e in result if (e.get("event_type") or "") == "RUN_CELL"]
    kept_emit = [e for e in result if (e.get("event_type") or "") == "EMIT_TREE"]
    assert len(run_cells) == 2, f"Expected 2 RUN_CELL, got {len(run_cells)}"
    assert len(kept_emit) == 1, f"Expected 1 un-transformed EMIT_TREE, got {len(kept_emit)}"
    assert all(e.get("transformed_from") == "EMIT_TREE" for e in run_cells)
    assert all(e.get("is_anchor_event") is True for e in run_cells)

    mock_episodes = [
        {"start_ms": 10000, "end_ms": 20000},
        {"start_ms": 40000, "end_ms": 50000},
    ]
    warnings = validate_anchor_alignment(result, mock_episodes, tolerance_ms=1000)
    assert warnings == [], f"Unexpected alignment warnings: {warnings}"

    print("All assertions passed.")
