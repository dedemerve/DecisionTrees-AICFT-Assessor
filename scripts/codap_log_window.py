#!/usr/bin/env python3
"""Build ±10s CODAP Arbor log windows and session stats for frame-level vision analysis."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from log_extractor import (  # noqa: E402
    MEANINGFUL_ACTIONS,
    _apply_overrides,
    _is_valid_emit,
    _normalise_id,
    _parse_parameters,
    _session_duration_minutes,
)


def load_log_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    if "student_id" not in df.columns or "timestamp_ms" not in df.columns:
        raise ValueError(f"Log CSV missing required columns: {csv_path}")
    df = df.copy()
    df["_canonical_id"] = df["student_id"].apply(
        lambda x: _apply_overrides(_normalise_id(str(x)))
    )
    if "parameters" in df.columns:
        df["_params"] = df["parameters"].apply(_parse_parameters)
    else:
        df["_params"] = [{} for _ in range(len(df))]
    return df.sort_values("timestamp_ms").reset_index(drop=True)


def resolve_student_log_id(student_id: str) -> str:
    return _apply_overrides(_normalise_id(student_id))


def student_log_rows(df: pd.DataFrame, student_id: str) -> pd.DataFrame:
    canonical = resolve_student_log_id(student_id)
    rows = df[df["_canonical_id"] == canonical]
    if rows.empty:
        # Fallback: case-insensitive substring on raw student_id column
        needle = student_id.casefold()
        mask = df["student_id"].astype(str).str.casefold().str.contains(needle, regex=False)
        rows = df[mask]
    return rows.sort_values("timestamp_ms").reset_index(drop=True)


def format_log_line(row: pd.Series) -> str:
    ts = int(row["timestamp_ms"])
    action = str(row.get("action", "unknown"))
    params = row.get("_params") or {}
    if not isinstance(params, dict):
        params = _parse_parameters(str(params))
    return f"[t={ts}] {action} | {json.dumps(params, ensure_ascii=False)}"


def log_window_entries(
    df: pd.DataFrame,
    student_id: str,
    timestamp_ms: int,
    *,
    window_ms: int = 10_000,
) -> list[dict[str, Any]]:
    rows = student_log_rows(df, student_id)
    if rows.empty:
        return []
    lo = timestamp_ms - window_ms
    hi = timestamp_ms + window_ms
    window = rows[(rows["timestamp_ms"] >= lo) & (rows["timestamp_ms"] <= hi)]
    out: list[dict[str, Any]] = []
    for _, row in window.iterrows():
        params = row.get("_params") or {}
        if not isinstance(params, dict):
            params = _parse_parameters(str(params))
        out.append(
            {
                "timestamp_ms": int(row["timestamp_ms"]),
                "action": str(row.get("action", "")),
                "parameters": params,
                "line": format_log_line(row),
            }
        )
    return out


def log_window_text(
    df: pd.DataFrame,
    student_id: str,
    timestamp_ms: int,
    *,
    window_ms: int = 10_000,
) -> str:
    entries = log_window_entries(df, student_id, timestamp_ms, window_ms=window_ms)
    if not entries:
        return "(log yok — bu zaman penceresinde kayıt bulunamadı)"
    return "\n".join(e["line"] for e in entries)


def student_session_stats(df: pd.DataFrame, student_id: str) -> dict[str, Any]:
    rows = student_log_rows(df, student_id)
    if rows.empty:
        return {
            "total_emit_tree_data": 0,
            "last_accuracy": None,
            "max_duration_minutes": None,
            "total_actions": 0,
            "meaningful_actions": 0,
        }

    emit_rows = rows[rows["action"] == "emit_tree_data"]
    valid_emits = []
    for _, row in emit_rows.iterrows():
        params = row.get("_params") or {}
        if not isinstance(params, dict):
            params = _parse_parameters(str(params))
        if _is_valid_emit(params):
            valid_emits.append(params)

    last_accuracy = None
    if valid_emits:
        acc = valid_emits[-1].get("accuracy")
        if acc is not None:
            try:
                last_accuracy = float(acc)
            except (TypeError, ValueError):
                last_accuracy = None

    return {
        "total_emit_tree_data": int(len(emit_rows)),
        "last_accuracy": last_accuracy,
        "max_duration_minutes": round(_session_duration_minutes(rows), 1),
        "total_actions": int(len(rows)),
        "meaningful_actions": int(rows["action"].isin(MEANINGFUL_ACTIONS).sum()),
    }


def format_student_stats(stats: dict[str, Any]) -> str:
    acc = stats.get("last_accuracy")
    acc_str = f"{acc:.3f}" if isinstance(acc, (int, float)) else "bilinmiyor"
    dur = stats.get("max_duration_minutes")
    dur_str = f"{dur:.1f} dk" if isinstance(dur, (int, float)) else "bilinmiyor"
    return (
        f"- Toplam emit_tree_data: {stats.get('total_emit_tree_data', 0)}\n"
        f"- Son accuracy: {acc_str}\n"
        f"- Max süre: {dur_str}\n"
        f"- Toplam aksiyon: {stats.get('total_actions', 0)}"
    )
