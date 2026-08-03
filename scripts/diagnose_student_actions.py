#!/usr/bin/env python3
"""Diagnose what each student actually did: variable placements, threshold
decisions, and tree structure evolution — by cross-referencing log coordinates
with extracted frames.

Coordinate interpretation (empirically derived from data):
  position_y < 110  → root node (depth 0)
  position_y 110–190 → mid-level split (depth 1–2)
  position_y > 190  → leaf-level split (depth 3+)

  position_x encodes horizontal position within the DT panel.
  All observed drops are within x < 700 on a 1920px screen, confirming
  these coordinates are relative to the DT component, not the full screen.

Output per student:
  logs/diagnosis_<Student>_<date>.json  — full machine-readable timeline
  STDOUT                                — markdown summary table
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS_DIR  = REPO_ROOT / "logs"
sys.path.insert(0, str(REPO_ROOT / "scripts"))
sys.path.insert(0, str(REPO_ROOT))

from codap_alignment import (
    estimate_video_start_utc,
    meaningful_event_timestamps_s,
)
from codap_log_window import load_log_dataframe, student_log_rows
from log_extractor import _parse_parameters

import pandas as pd

# ── coordinate zone classifier ──────────────────────────────────────
def classify_drop_zone(position_x: float | None, position_y: float | None) -> str:
    """Infer tree position from drop coordinates."""
    if position_y is None:
        return "unknown"
    py = float(position_y)
    if py < 110:
        return "root_node"
    elif py < 190:
        return "mid_split"
    else:
        return "deep_split"


def depth_label(zone: str) -> str:
    return {"root_node": "depth-0 (root)",
            "mid_split":  "depth-1/2",
            "deep_split": "depth-3+",
            "unknown":    "?"}[zone]


# ── find nearest frame ───────────────────────────────────────────────
def nearest_frame(
    frame_ts_list: list[float],
    target_s: float,
    threshold_s: float = 20.0,
) -> tuple[float | None, float]:
    """Return (nearest_timestamp, distance). None if nothing within threshold."""
    if not frame_ts_list:
        return None, 9999.0
    nearest = min(frame_ts_list, key=lambda t: abs(t - target_s))
    dist = abs(nearest - target_s)
    if dist > threshold_s:
        return None, dist
    return nearest, dist


def frame_path_for_ts(
    frames: list[dict[str, Any]],
    target_ts: float,
    student_dir: Path,
    student_id: str,
) -> Path | None:
    """Return absolute path to frame file closest to target_ts."""
    best = min(frames, key=lambda f: abs(float(f["source_timestamp_seconds"]) - target_ts),
               default=None)
    if best is None:
        return None
    stored = best.get("file_path") or ""
    if stored:
        p = REPO_ROOT / stored
        if p.is_file():
            return p
    fid = best["frame_id"]
    p = student_dir / f"{student_id}_frames" / f"{fid}.jpg"
    return p if p.is_file() else None


# ── per-student diagnosis ────────────────────────────────────────────
def diagnose_student(
    student_id: str,
    student_dir: Path,
    log_df: pd.DataFrame,
    session_date: str,
) -> dict[str, Any]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        return {"student_id": student_id, "error": "no manifest"}

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    frames   = manifest.get("frames") or manifest.get("segments") or []
    frame_ts_list = [float(f["source_timestamp_seconds"]) for f in frames]

    video_start, method = estimate_video_start_utc(None, log_df, student_id, session_date)
    if not video_start:
        return {"student_id": student_id, "error": "no video_start"}

    # ── raw log rows for this student (undeduped) ────────────────────
    rows = student_log_rows(log_df, student_id).copy()
    rows["_dt"] = pd.to_datetime(rows["created_at"], utc=True)
    rows = rows[rows["_dt"].dt.date.astype(str) == session_date]
    rows["_t_s"] = rows["_dt"].apply(
        lambda x: max(0.0, x.timestamp() - video_start.timestamp())
    )

    # ── drop_attribute timeline ──────────────────────────────────────
    drops_raw = rows[rows["action"] == "drop_attribute"].copy()
    drops_raw["_params"] = drops_raw["parameters"].apply(
        lambda r: _parse_parameters(str(r)) if not isinstance(r, dict) else r
    )

    drop_timeline: list[dict[str, Any]] = []
    for _, row in drops_raw.iterrows():
        p   = row["_params"] if isinstance(row["_params"], dict) else {}
        t_s = float(row["_t_s"])
        px  = p.get("position_x")
        py  = p.get("position_y")
        zone = classify_drop_zone(px, py)
        nearest_ts, dist = nearest_frame(frame_ts_list, t_s)
        fp = frame_path_for_ts(frames, t_s, student_dir, student_id) if nearest_ts else None
        drop_timeline.append({
            "timestamp_s":   round(t_s, 1),
            "attribute":     p.get("attribute", "?"),
            "context":       p.get("context", "?"),
            "position_x":    px,
            "position_y":    py,
            "tree_zone":     zone,
            "tree_position": depth_label(zone),
            "nearest_frame_ts": round(nearest_ts, 1) if nearest_ts else None,
            "frame_distance_s": round(dist, 1),
            "frame_path":    str(fp.relative_to(REPO_ROOT)) if fp else None,
        })

    # ── change_split_values timeline (every settled threshold) ───────
    sv_raw = rows[rows["action"] == "change_split_values"].copy()
    sv_raw["_params"] = sv_raw["parameters"].apply(
        lambda r: _parse_parameters(str(r)) if not isinstance(r, dict) else r
    )

    # Keep settled (last) value per 2-second burst per attribute
    BURST_S = 2.0
    sv_settled: list[dict[str, Any]] = []
    last_attr_t: dict[str, float] = {}
    pending: dict[str, dict] = {}

    for _, row in sv_raw.sort_values("_t_s").iterrows():
        p    = row["_params"] if isinstance(row["_params"], dict) else {}
        t_s  = float(row["_t_s"])
        attr = p.get("attribute", "?")
        prev = last_attr_t.get(attr, -9999)
        if t_s - prev > BURST_S and attr in pending:
            sv_settled.append(pending[attr])
        pending[attr] = {
            "timestamp_s":   round(t_s, 1),
            "attribute":     attr,
            "new_value":     p.get("new_value"),
            "old_value":     p.get("old_value"),
            "operator":      p.get("operator"),
            "is_categorical": p.get("is_categorical"),
            "new_categories": p.get("new_categories"),
        }
        last_attr_t[attr] = t_s

    for entry in pending.values():
        sv_settled.append(entry)
    sv_settled.sort(key=lambda e: e["timestamp_s"])

    # attach nearest frame
    for entry in sv_settled:
        t_s = entry["timestamp_s"]
        nearest_ts, dist = nearest_frame(frame_ts_list, t_s)
        fp = frame_path_for_ts(frames, t_s, student_dir, student_id) if nearest_ts else None
        entry["nearest_frame_ts"]  = round(nearest_ts, 1) if nearest_ts else None
        entry["frame_distance_s"]  = round(dist, 1)
        entry["frame_path"]        = str(fp.relative_to(REPO_ROOT)) if fp else None

    # ── variable usage summary ───────────────────────────────────────
    attr_usage: dict[str, dict] = {}
    for d in drop_timeline:
        a = d["attribute"]
        if a not in attr_usage:
            attr_usage[a] = {"drop_count": 0, "zones": [], "contexts": set()}
        attr_usage[a]["drop_count"] += 1
        attr_usage[a]["zones"].append(d["tree_zone"])
        attr_usage[a]["contexts"].add(d["context"])

    attr_summary = []
    for attr, info in sorted(attr_usage.items(), key=lambda x: -x[1]["drop_count"]):
        from collections import Counter
        zone_dist = dict(Counter(info["zones"]))
        dominant = max(zone_dist, key=zone_dist.get)
        attr_summary.append({
            "attribute":    attr,
            "total_drops":  info["drop_count"],
            "primary_zone": depth_label(dominant),
            "zone_counts":  zone_dist,
            "datasets_used": sorted(info["contexts"]),
        })

    # ── threshold summary per attribute ─────────────────────────────
    thresh_summary: dict[str, dict] = {}
    for sv in sv_settled:
        a = sv["attribute"]
        if sv["is_categorical"]:
            continue
        if a not in thresh_summary:
            thresh_summary[a] = {"count": 0, "values": [], "min": None, "max": None}
        v = sv["new_value"]
        if v is not None:
            thresh_summary[a]["count"] += 1
            thresh_summary[a]["values"].append(v)
            cur_min = thresh_summary[a]["min"]
            cur_max = thresh_summary[a]["max"]
            thresh_summary[a]["min"] = v if cur_min is None else min(cur_min, v)
            thresh_summary[a]["max"] = v if cur_max is None else max(cur_max, v)

    return {
        "student_id":      student_id,
        "session_date":    session_date,
        "video_start_method": method,
        "total_frames":    len(frames),
        "attribute_usage_summary": attr_summary,
        "threshold_summary": [
            {"attribute": a, **v} for a, v in sorted(thresh_summary.items())
        ],
        "drop_timeline":   drop_timeline,
        "threshold_timeline": sv_settled,
    }


# ── markdown summary ─────────────────────────────────────────────────
def print_summary(result: dict[str, Any]) -> None:
    sid = result["student_id"]
    print(f"\n### {sid}")

    print(f"\n**Variable usage (drop_attribute):**")
    print(f"| Attribute | Drops | Primary position | Datasets |")
    print(f"|-----------|-------|-----------------|---------|")
    for row in result.get("attribute_usage_summary", []):
        datasets = ", ".join(d.split()[0] for d in row["datasets_used"])
        print(f"| {row['attribute']:<20} | {row['total_drops']:>5} | "
              f"{row['primary_zone']:<18} | {datasets} |")

    thresh = result.get("threshold_summary", [])
    if thresh:
        print(f"\n**Threshold adjustments (change_split_values — numeric only):**")
        print(f"| Attribute | Adjustments | Min value | Max value |")
        print(f"|-----------|-------------|-----------|-----------|")
        for row in thresh:
            print(f"| {row['attribute']:<22} | {row['count']:>11} | "
                  f"{row['min']:>9} | {row['max']:>9} |")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Diagnose student actions from log + frames")
    parser.add_argument("students", nargs="*")
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--session-date", required=True)
    parser.add_argument("--log-csv", type=Path)
    args = parser.parse_args(argv)

    LOG_CSVS = {
        "2026-04-21": REPO_ROOT / "data_sources_2026" / "All Documents" /
                      "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
        "2026-04-28": REPO_ROOT / "data_sources_2026" / "All Documents" /
                      "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
    }
    log_csv = args.log_csv or LOG_CSVS.get(args.session_date)
    if not log_csv or not log_csv.is_file():
        print(f"ERROR: log CSV not found for {args.session_date}", file=sys.stderr)
        return 1

    log_df = load_log_dataframe(log_csv)
    audio_root = args.audio_root.resolve()

    targets = args.students or [
        d.name for d in sorted(audio_root.iterdir())
        if d.is_dir() and (d / f"{d.name}_video_extraction_manifest.json").is_file()
    ]

    LOGS_DIR.mkdir(exist_ok=True)
    ts_str = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    for student_id in targets:
        student_dir = audio_root / student_id
        if not student_dir.is_dir():
            print(f"SKIP {student_id}: directory not found")
            continue

        result = diagnose_student(student_id, student_dir, log_df, args.session_date)
        if "error" in result:
            print(f"SKIP {student_id}: {result['error']}")
            continue

        out_path = LOGS_DIR / f"diagnosis_{student_id}_{ts_str}.json"
        out_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print_summary(result)
        print(f"\n  → saved: {out_path.relative_to(REPO_ROOT)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
