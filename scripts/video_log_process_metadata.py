#!/usr/bin/env python3
"""Build log_process_metadata artifact — objective chronology video cannot supply.

See framework/VIDEO_PROCESS_CODEBOOK_v1.md and
schema/video_log_process_metadata.schema.json.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from codap_alignment import estimate_video_start_utc, meaningful_event_timestamps_s
from codap_log_window import load_log_dataframe, student_log_rows
from log_extractor import (
    _apply_overrides,
    _normalise_id,
    extract_log_features,
    resolve_identities,
)

SCHEMA_VERSION = "1.0"

VIDEO_CANNOT_DETERMINE: list[str] = [
    "metric_interpretation_quality_emit_is_not_inspection",
    "graph_reading_intent_and_cross_representation_use",
    "threshold_reasoning_intent",
    "class_label_semantics_understanding",
    "train_test_role_awareness_without_visible_cues",
    "threshold_transfer_reasoning",
    "comparative_model_evaluation_rationale",
    "integrated_metric_decision_rationale",
    "negative_evidence_no_metric_panel_inspection",
    "negative_evidence_no_graph_reading_despite_opportunity",
    "assistance_agency_peer_vs_instructor_vs_independent",
    "off_task_engagement_and_attention",
    "cognitive_load_hesitation_disorientation",
    "misconception_reasoning_vs_logged_values_alone",
    "verbatim_justification_and_argumentation",
]

LOG_CAN_CORROBORATE: list[str] = [
    "session_start_and_data_context",
    "target_selection_chronology",
    "predictor_drop_attribute_chronology",
    "threshold_change_chronology",
    "emit_presence_and_timing",
    "tree_depth_at_emit",
    "action_counts_and_timing",
    "model_configuration_at_emit",
    "train_test_dataset_switch_chronology",
    "tree_rebuild_and_refresh_events",
]

LOG_TO_PROCESS_DIRECT = {
    "drop_attribute": ["predictor_drop"],
    "emit_tree_data": ["emit_event"],
    "change_split_values": ["threshold_change"],
    "session_start": ["session_start"],
    "data_context_change": ["data_context"],
}


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _derive_log_behavior_presence(events: list[dict[str, Any]]) -> dict[str, Any]:
    behaviors: set[str] = set()
    prev_attr: str | None = None
    target_change_count = 0
    emit_count = 0
    depth2_emit_count = 0

    for ev in events:
        action = ev["action"]
        params = ev.get("params") or {}

        for tag in LOG_TO_PROCESS_DIRECT.get(action, []):
            behaviors.add(tag)

        if action == "emit_tree_data":
            emit_count += 1
            if params.get("depth", 0) >= 2:
                behaviors.add("depth_ge_2_at_emit")
                depth2_emit_count += 1

        if action == "set_dependent_variable":
            attr = params.get("attribute") or params.get("dependent_variable") or ""
            if attr != prev_attr:
                behaviors.add("target_selection")
                target_change_count += 1
                prev_attr = attr

    return {
        "behaviors": sorted(behaviors),
        "target_change_count": target_change_count,
        "emit_count": emit_count,
        "depth2_emit_count": depth2_emit_count,
        "metric_note": (
            "Metric interpretation cannot be derived from log. "
            "emit_tree_data carries accuracy but emission != inspection/interpretation."
        ),
    }


def _task4_from_log_features(features: dict[str, Any]) -> dict[str, Any]:
    snaps = features.get("emit_snapshots") or []
    depth2 = sum(1 for s in snaps if (s.get("depth") or 0) >= 2)
    first_emit_ms = snaps[0]["emitted_at_ms"] if snaps else None
    first_split_rows = [
        s for s in snaps
    ]
    _ = first_split_rows  # reserved for future split timing

    return {
        "time_to_first_target_ms": None,
        "time_to_first_split_ms": None,
        "time_to_first_emit_ms": first_emit_ms,
        "feature_change_count": features.get("feature_drop_count"),
        "unique_features_tried": features.get("unique_features_tried"),
        "threshold_change_count": features.get("threshold_change_count"),
        "unique_thresholds_tried": features.get("unique_thresholds_tried"),
        "emit_count": features.get("emit_count"),
        "valid_emit_count": features.get("valid_emit_count"),
        "max_tree_depth": features.get("max_tree_depth_reached"),
        "depth2_attempts": depth2,
        "tree_rebuild_count": features.get("refresh_count"),
        "dataset_switch_count": None,
        "comparison_cycles": None,
        "undo_count": None,
        "session_duration_minutes": features.get("session_duration_minutes"),
        "train_test_applied": features.get("train_test_applied"),
        "train_test_accuracy_gap": features.get("train_test_accuracy_gap"),
        "exploration_index": features.get("exploration_index"),
        "log_available_flag": True,
        "sync_error_ms": None,
        "frame_coverage_ratio": None,
    }


def _frame_coverage_summary(
    events: list[dict[str, Any]],
    frame_ts: list[float],
    *,
    cover_window_s: float = 30.0,
) -> dict[str, Any]:
    critical = {"drop_attribute", "emit_tree_data", "change_split_values", "set_dependent_variable"}
    if not frame_ts:
        return {
            "status": "partial",
            "critical_events_covered": 0,
            "critical_events_total": 0,
            "events_beyond_video_end": 0,
            "note": "No frame timestamps available for sync audit.",
        }

    video_end = max(frame_ts)
    covered = 0
    total = 0
    beyond = 0

    for ev in events:
        if ev["action"] not in critical:
            continue
        total += 1
        ts = ev["timestamp_s"]
        if ts > video_end:
            beyond += 1
            continue
        nearest = min(abs(ts - ft) for ft in frame_ts)
        if nearest <= cover_window_s:
            covered += 1

    status = "aligned" if total and covered / total >= 0.8 else "partial"
    if total == 0:
        status = "not_applicable"

    return {
        "status": status,
        "method": "wall_clock_frame_nearest",
        "sync_error_ms": None,
        "critical_events_covered": covered,
        "critical_events_total": total,
        "events_beyond_video_end": beyond,
        "note": None,
    }


def build_log_unavailable_metadata(
    student_id: str,
    cohort_year: int,
    *,
    audio_available: bool | None = None,
    video_duration_ms: int | None = None,
) -> dict[str, Any]:
    """2025 cohort: no CODAP event CSV — document gaps explicitly."""
    null_task4 = {k: None for k in (
        "time_to_first_target_ms", "time_to_first_split_ms", "time_to_first_emit_ms",
        "feature_change_count", "unique_features_tried", "threshold_change_count",
        "unique_thresholds_tried", "emit_count", "valid_emit_count", "max_tree_depth",
        "depth2_attempts", "tree_rebuild_count", "dataset_switch_count",
        "comparison_cycles", "undo_count", "session_duration_minutes",
        "train_test_applied", "train_test_accuracy_gap", "exploration_index",
        "log_available_flag", "sync_error_ms", "frame_coverage_ratio",
    )}
    null_task4["log_available_flag"] = False

    video_min = round(video_duration_ms / 60_000, 1) if video_duration_ms else None

    return {
        "$schema": "schema/video_log_process_metadata.schema.json",
        "artifact": "log_process_metadata",
        "student_id": student_id,
        "cohort_year": cohort_year,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso_now(),
        "log_available": False,
        "log_file_id": None,
        "interpretation_rule": (
            "Task-4 variables are null when event log is unavailable. "
            "Do not infer log-only chronology from video; use expert narrative "
            "and V-layer process codes with lowered confidence where needed."
        ),
        "modality_coverage": {
            "video": True,
            "expert_narrative": True,
            "audio_transcript": bool(audio_available),
            "event_log": False,
        },
        "video_cannot_determine": list(VIDEO_CANNOT_DETERMINE),
        "log_can_corroborate": list(LOG_CAN_CORROBORATE),
        "task4_process_variables": null_task4,
        "log_derived_features": None,
        "log_behavior_presence": None,
        "video_log_sync": {
            "status": "unavailable",
            "method": None,
            "sync_error_ms": None,
            "critical_events_covered": None,
            "critical_events_total": None,
            "events_beyond_video_end": 0,
            "note": (
                f"No CODAP event CSV for {cohort_year} cohort. "
                f"Video duration ~{video_min} min when known."
            ),
        },
        "analyst_flags": ["no_event_log_for_cohort"],
    }


def build_log_metadata_from_csv(
    student_id: str,
    cohort_year: int,
    log_csv: Path,
    *,
    session_date: str | None = None,
    video_path: Path | None = None,
    frame_timestamps_s: list[float] | None = None,
    audio_available: bool = False,
) -> dict[str, Any]:
    """2026+ cohort: full log-derived metadata and optional video sync audit."""
    log_df = load_log_dataframe(log_csv)
    identities = resolve_identities(log_df)
    canonical = None
    raw_ids: list[str] = []
    for cid, variants in identities.items():
        if student_id.casefold() in cid or cid in student_id.casefold():
            canonical = cid
            raw_ids = variants
            break
    if canonical is None:
        rows = student_log_rows(log_df, student_id)
        if rows.empty:
            meta = build_log_unavailable_metadata(student_id, cohort_year, audio_available=audio_available)
            meta["analyst_flags"] = [f"log_student_not_found:{log_csv.name}"]
            return meta
        canonical = student_id
        raw_ids = [student_id]

    log_df = log_df.copy()
    log_df["_canonical_id"] = log_df["student_id"].apply(
        lambda x: _apply_overrides(_normalise_id(str(x)))
    )

    features = extract_log_features(log_df, canonical, raw_ids, log_csv.stem)
    task4 = _task4_from_log_features(features)

    events = meaningful_event_timestamps_s(
        log_df, student_id, session_date=session_date or ""
    ) if session_date else []
    behavior_presence = _derive_log_behavior_presence(events) if events else None

    sync = {"status": "not_applicable", "note": "session_date not provided"}
    if session_date and frame_timestamps_s is not None:
        sync = _frame_coverage_summary(events, frame_timestamps_s)
        video_start, method = estimate_video_start_utc(
            video_path, log_df, student_id, session_date
        )
        if video_start:
            sync["method"] = method

    analyst_flags = list(features.get("analyst_flags") or [])
    if sync.get("status") == "partial":
        analyst_flags.append("log_video_sync_partial")

    return {
        "$schema": "schema/video_log_process_metadata.schema.json",
        "artifact": "log_process_metadata",
        "student_id": student_id,
        "cohort_year": cohort_year,
        "schema_version": SCHEMA_VERSION,
        "generated_at": _iso_now(),
        "log_available": True,
        "log_file_id": log_csv.stem,
        "interpretation_rule": (
            "Log supplies objective chronology and Task-4 counts. "
            "It cannot establish metric interpretation quality, comparative "
            "rationale, or negative visual evidence. Use log_behavior_presence "
            "only for action presence/absence and timing, not reasoning quality."
        ),
        "modality_coverage": {
            "video": video_path is not None and video_path.is_file(),
            "expert_narrative": False,
            "audio_transcript": audio_available,
            "event_log": True,
        },
        "video_cannot_determine": list(VIDEO_CANNOT_DETERMINE),
        "log_can_corroborate": list(LOG_CAN_CORROBORATE),
        "task4_process_variables": task4,
        "log_derived_features": _json_safe(features),
        "log_behavior_presence": behavior_presence,
        "video_log_sync": sync,
        "analyst_flags": analyst_flags,
    }


def _json_safe(obj: Any) -> Any:
    """Convert datetimes and other non-JSON types for serialization."""
    if isinstance(obj, dict):
        return {k: _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if hasattr(obj, "item"):
        try:
            return obj.item()
        except (ValueError, TypeError):
            pass
    return obj
