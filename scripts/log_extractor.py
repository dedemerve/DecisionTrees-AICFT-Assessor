#!/usr/bin/env python3
"""CODAP Arbor event log feature extraction.

Shared by video_log_process_metadata.py and codap_log_window.py.
Handles CODAP Arbor event CSVs with columns: student_id, timestamp_ms, action, parameters.
All public functions are null-safe: pass None or an empty DataFrame and get back
empty-but-valid structures.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

# ── Public constant ────────────────────────────────────────────────────────────

MEANINGFUL_ACTIONS: set[str] = {
    "emit_tree_data",
    "drop_attribute",
    "change_split_values",
    "set_dependent_variable",
    "session_start",
    "data_context_change",
    "refresh_decision_tree",
    "assign_leaf_label",
    "import_tree",
    "delete_tree",
    "train_test_split",
    "change_threshold",
    "update_movable_value",
}

# Student-name normalisation overrides.
# Maps a normalised variant → canonical pseudonym.
_OVERRIDES: dict[str, str] = {}


# ── Private helpers ────────────────────────────────────────────────────────────

def _normalise_id(x: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces."""
    return re.sub(r"\s+", " ", str(x).strip().lower())


def _apply_overrides(normalised: str) -> str:
    """Return the canonical pseudonym for a normalised ID, or the ID itself."""
    return _OVERRIDES.get(normalised, normalised)


def _parse_parameters(params: Any) -> dict[str, Any]:
    """Parse a JSON string or pass-through a dict; return {} on failure."""
    if isinstance(params, dict):
        return params
    if params is None or (isinstance(params, float) and str(params) == "nan"):
        return {}
    try:
        result = json.loads(str(params))
        return result if isinstance(result, dict) else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        return {}


def _is_valid_emit(row: pd.Series) -> bool:
    """Return True for emit_tree_data rows that carry usable accuracy data."""
    if row.get("action") != "emit_tree_data":
        return False
    params = row.get("_params") or {}
    accuracy = params.get("accuracy")
    if accuracy is None:
        return False
    try:
        v = float(accuracy)
        return 0.0 <= v <= 1.0
    except (TypeError, ValueError):
        return False


def _session_duration_minutes(
    df: pd.DataFrame | None,
    student_id: str,
) -> float | None:
    """Compute session duration in minutes from first to last event."""
    if df is None or df.empty:
        return None
    canonical = _apply_overrides(_normalise_id(student_id))
    rows = df[df.get("_canonical_id", pd.Series(dtype=str)) == canonical]
    if rows.empty:
        rows = df
    ts = rows["timestamp_ms"].dropna()
    if len(ts) < 2:
        return None
    return round((ts.max() - ts.min()) / 60_000, 2)


# ── Public API ─────────────────────────────────────────────────────────────────

def resolve_identities(df: pd.DataFrame | None) -> dict[str, list[str]]:
    """Return {canonical_id: [raw_id_variants]} found in the log DataFrame.

    If df is None or has no student_id column, returns {}.
    """
    if df is None or df.empty or "student_id" not in df.columns:
        return {}
    result: dict[str, list[str]] = {}
    for raw in df["student_id"].dropna().unique():
        canonical = _apply_overrides(_normalise_id(str(raw)))
        result.setdefault(canonical, [])
        if str(raw) not in result[canonical]:
            result[canonical].append(str(raw))
    return result


def extract_log_features(
    df: pd.DataFrame | None,
    canonical_id: str,
    raw_ids: list[str],
    log_stem: str = "",
) -> dict[str, Any]:
    """Extract ML-ready features from a CODAP Arbor event log DataFrame.

    Parameters
    ----------
    df:           Full log DataFrame (student_id, timestamp_ms, action, _params).
                  May be None or empty — all features will be None with imputed_flag=True.
    canonical_id: Normalised student pseudonym (from resolve_identities).
    raw_ids:      Raw name variants for this student.
    log_stem:     Log filename stem for provenance.

    Returns a flat dict of feature values and metadata.
    """
    base: dict[str, Any] = {
        "log_stem": log_stem,
        "canonical_id": canonical_id,
        "imputed_flag": False,
        "analyst_flags": [],
    }

    if df is None or df.empty:
        return _null_features(base, reason="empty_dataframe")

    # Filter to this student's rows
    if "_canonical_id" in df.columns:
        rows = df[df["_canonical_id"] == canonical_id].copy()
    else:
        mask = df["student_id"].astype(str).apply(
            lambda x: _apply_overrides(_normalise_id(x)) == canonical_id
        )
        rows = df[mask].copy()

    if rows.empty:
        return _null_features(base, reason=f"student_not_found:{canonical_id}")

    # Ensure _params is parsed
    if "_params" not in rows.columns:
        rows["_params"] = rows.get("parameters", pd.Series(dtype=object)).apply(
            _parse_parameters
        )

    rows = rows.sort_values("timestamp_ms").reset_index(drop=True)
    ts = rows["timestamp_ms"]

    # ── Timing ────────────────────────────────────────────────────────────────
    duration_ms = float(ts.max() - ts.min()) if len(ts) >= 2 else None
    duration_min = round(duration_ms / 60_000, 2) if duration_ms else None

    # ── Emit events ───────────────────────────────────────────────────────────
    emit_rows = rows[rows["action"] == "emit_tree_data"].copy()
    valid_emit_rows = emit_rows[emit_rows.apply(_is_valid_emit, axis=1)]
    emit_count = len(emit_rows)
    valid_emit_count = len(valid_emit_rows)

    emit_snapshots: list[dict[str, Any]] = []
    for _, r in valid_emit_rows.iterrows():
        p = r["_params"]
        emit_snapshots.append({
            "emitted_at_ms": int(r["timestamp_ms"]),
            "accuracy": p.get("accuracy"),
            "depth": p.get("depth") or p.get("maxDepth"),
            "node_count": p.get("nodeCount") or p.get("node_count"),
            "predictor": p.get("predictor") or p.get("splitAttribute"),
        })

    max_depth = max(
        (s["depth"] for s in emit_snapshots if s["depth"] is not None), default=None
    )

    # ── Feature (predictor) changes ───────────────────────────────────────────
    drop_rows = rows[rows["action"].isin({"drop_attribute", "drag_attribute"})]
    feature_change_count = len(drop_rows)
    unique_features: set[str] = set()
    for _, r in drop_rows.iterrows():
        attr = (r["_params"].get("attribute") or r["_params"].get("predictor") or "")
        if attr:
            unique_features.add(str(attr))

    # ── Threshold changes ─────────────────────────────────────────────────────
    thresh_rows = rows[rows["action"].isin({
        "change_split_values", "change_threshold", "update_movable_value"
    })]
    threshold_change_count = len(thresh_rows)
    unique_thresholds: set[float] = set()
    for _, r in thresh_rows.iterrows():
        val = r["_params"].get("value") or r["_params"].get("splitValue")
        try:
            unique_thresholds.add(float(val))
        except (TypeError, ValueError):
            pass

    # ── Refresh / rebuild ─────────────────────────────────────────────────────
    refresh_count = len(rows[rows["action"].isin({
        "refresh_decision_tree", "delete_tree", "import_tree"
    })])

    # ── Train/test split ──────────────────────────────────────────────────────
    split_rows = rows[rows["action"] == "train_test_split"]
    train_test_applied = len(split_rows) > 0

    # ── Accuracy progression for train/test gap ───────────────────────────────
    accuracy_vals = [s["accuracy"] for s in emit_snapshots if s["accuracy"] is not None]
    train_test_accuracy_gap = None
    if len(accuracy_vals) >= 2:
        train_test_accuracy_gap = round(float(max(accuracy_vals) - min(accuracy_vals)), 4)

    # ── Exploration index (unique features tried / emit count) ────────────────
    exploration_index = None
    if emit_count > 0:
        exploration_index = round(len(unique_features) / emit_count, 3)

    # ── Analyst flags ─────────────────────────────────────────────────────────
    analyst_flags: list[str] = []
    if valid_emit_count == 0:
        analyst_flags.append("no_valid_emits")
    if feature_change_count == 0:
        analyst_flags.append("no_predictor_changes")
    if not train_test_applied:
        analyst_flags.append("no_train_test_split_detected")

    return {
        **base,
        "imputed_flag": False,
        "session_duration_minutes": duration_min,
        "emit_count": emit_count,
        "valid_emit_count": valid_emit_count,
        "emit_snapshots": emit_snapshots,
        "max_tree_depth_reached": max_depth,
        "feature_drop_count": feature_change_count,
        "unique_features_tried": sorted(unique_features),
        "threshold_change_count": threshold_change_count,
        "unique_thresholds_tried": sorted(unique_thresholds),
        "refresh_count": refresh_count,
        "train_test_applied": train_test_applied,
        "train_test_accuracy_gap": train_test_accuracy_gap,
        "exploration_index": exploration_index,
        "analyst_flags": analyst_flags,
    }


# ── Internal null-features helper ─────────────────────────────────────────────

def _null_features(base: dict[str, Any], reason: str) -> dict[str, Any]:
    base["imputed_flag"] = True
    base["analyst_flags"] = [f"log_features_null:{reason}"]
    null_keys = [
        "session_duration_minutes", "emit_count", "valid_emit_count", "emit_snapshots",
        "max_tree_depth_reached", "feature_drop_count", "unique_features_tried",
        "threshold_change_count", "unique_thresholds_tried", "refresh_count",
        "train_test_applied", "train_test_accuracy_gap", "exploration_index",
    ]
    return {**base, **{k: None for k in null_keys}}


# ── Self-test ──────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("log_extractor self-test")

    # Test with None input
    r = extract_log_features(None, "amy", ["Amy"], "test_null")
    assert r["imputed_flag"] is True
    print("  null input → imputed_flag=True OK")

    # Test with minimal mock DataFrame
    mock_df = pd.DataFrame([
        {"student_id": "Amy", "timestamp_ms": 1000, "action": "session_start", "parameters": "{}"},
        {"student_id": "Amy", "timestamp_ms": 60000, "action": "drop_attribute",
         "parameters": '{"attribute": "Energy"}'},
        {"student_id": "Amy", "timestamp_ms": 120000, "action": "emit_tree_data",
         "parameters": '{"accuracy": 0.72, "depth": 2, "nodeCount": 3}'},
        {"student_id": "Amy", "timestamp_ms": 180000, "action": "emit_tree_data",
         "parameters": '{"accuracy": 0.81, "depth": 3, "nodeCount": 5}'},
        {"student_id": "Bob", "timestamp_ms": 5000, "action": "session_start", "parameters": "{}"},
    ])
    mock_df["_params"] = mock_df["parameters"].apply(_parse_parameters)
    mock_df["_canonical_id"] = mock_df["student_id"].apply(
        lambda x: _apply_overrides(_normalise_id(x))
    )

    ids = resolve_identities(mock_df)
    assert "amy" in ids and "bob" in ids
    print(f"  resolve_identities → {list(ids.keys())} OK")

    feats = extract_log_features(mock_df, "amy", ["Amy"], "test_mock")
    assert feats["emit_count"] == 2
    assert feats["valid_emit_count"] == 2
    assert feats["feature_drop_count"] == 1
    assert feats["session_duration_minutes"] is not None
    print(f"  extract_log_features → emit={feats['emit_count']} depth={feats['max_tree_depth_reached']} OK")

    dur = _session_duration_minutes(mock_df, "Amy")
    assert dur is not None
    print(f"  _session_duration_minutes → {dur} min OK")

    print("All self-tests passed.")
