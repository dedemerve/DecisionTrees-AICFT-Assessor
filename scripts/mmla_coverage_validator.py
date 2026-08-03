#!/usr/bin/env python3
"""
mmla_coverage_validator.py  —  Production-grade MMLA Pipeline QA Engine v2

Two-track verification architecture:

  Track A — CODAP Log-to-Frame Coverage Audit (deterministic + hybrid)
    Evaluates frame extraction recall against ground-truth CODAP interaction
    logs via dual-mode temporal matching:
      • Strict match  : |T_frame - T_log| ≤ 1.0 s
      • Hybrid match  : |T_frame - T_log| ≤ 5.0 s  AND  focal student was
                        speaking within that exact timeline segment.
    Cohort-date isolation: rows not matching the active session date are
    purged before any metric computation.

  Track B — Colab Visual Cue & Distribution Audit (heuristic)
    Density anomaly detection, scroll-noise clustering, and ROI sensitivity
    simulation for logless Colab sessions.  Includes the "Shana Guard":
    corrupt video-stream durations are overridden from transcript max when
    the discrepancy exceeds 50%.

Outputs:
  - Aligned Markdown grid → stdout
  - logs/pipeline_runs/qa_coverage_report_{cohort_label}.json
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np

# ─────────────────────────────────────────────────────────────────────────────
# REPOSITORY PATHS
# ─────────────────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR   = REPO_ROOT / "logs" / "pipeline_runs"
ALL_DOCS  = REPO_ROOT / "data_sources_2026" / "All Documents"

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

TARGET_ACTIONS: frozenset[str] = frozenset(
    {"emit_tree_data", "drop_attribute", "change_axis"}
)

STRICT_WINDOW_S:   float = 1.0    # ±1 s  — strict match
HYBRID_WINDOW_S:   float = 5.0    # ±5 s  — hybrid match (needs speech anchor)
BURST_GAP_S:       float = 5.0    # events ≤ 5 s apart belong to one burst cluster
HYBRID_PASS_RATIO: float = 0.85   # ≥ 85 % hybrid coverage → PASS

LOW_DENSITY_MIN_DURATION_S: float = 1800.0   # 30 min minimum to check density
LOW_DENSITY_MIN_FRAMES:     int   = 15
DURATION_DISCREPANCY_RATIO: float = 1.5      # transcript > video * 1.5 → override

SCROLL_DELTA_MS:          float = 500.0   # consecutive frames within 500 ms
SCROLL_GLOBAL_CHANGE_PCT: float = 30.0    # pixel-change % to flag as scroll
SENSITIVITY_WINDOW_S:     float = 5.0     # ROI simulation look-ahead
SENSITIVITY_LOW_DELTA:    float = 0.001   # 0.1 % normalised editor delta

# Cohort calendar dates for CSV row isolation
_COHORT_DATE_MAP: dict[str, str] = {
    "21april": "2026-04-21",
    "28april": "2026-04-28",
}

# Identity resolution: normalised raw CSV student_id → pseudonym directory name
_TURKISH_I_MAP = str.maketrans({"İ": "i", "I": "ı"})

IDENTITY_OVERRIDES: dict[str, Optional[str]] = {
    "sena çiçek":             "Serena",
    "senanur elhan çiçek":    "Serena",
    "hatice sennur ayyıldız": "Helena",
    "hatice şennur ayyıldız": "Helena",
    "şeyda":                  "Sheila",
    "şeyma peltelk":          "Shana",
    "şeyma peltek":           "Shana",
    "merve":                  None,   # instructor account
    "sahal":                  None,   # instructor account
    "melinda":                None,   # no screen recording
}

# ─────────────────────────────────────────────────────────────────────────────
# LOGGING
# ─────────────────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s.%(msecs)03d [%(levelname)-5s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
LOGGER = logging.getLogger("mmla_coverage_validator")


def _info(msg: str)  -> None: LOGGER.info("[QA-AUDIT-INFO]  %s", msg)
def _warn(msg: str)  -> None: LOGGER.warning("[QA-AUDIT-WARN]  %s", msg)
def _error(msg: str) -> None: LOGGER.error("[QA-AUDIT-ERROR] %s", msg)


# ─────────────────────────────────────────────────────────────────────────────
# RESULT DATA-STRUCTURES
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CodapStudentResult:
    student_id:          str
    environment:         str   = "CODAP"
    total_log_events:    int   = 0
    actual_frames:       int   = 0
    strict_matches:      int   = 0   # |delta| ≤ 1.0 s
    hybrid_matches:      int   = 0   # |delta| ≤ 5.0 s + speech anchor
    dropped_events:      int   = 0   # matched neither strict nor hybrid
    hybrid_coverage:     float = 0.0
    burst_clusters:      int   = 0
    blindspots:          list[dict] = field(default_factory=list)
    grade:               str   = "SKIP"
    notes:               list[str]  = field(default_factory=list)


@dataclass
class ColabStudentResult:
    student_id:                  str
    environment:                 str   = "Colab"
    duration_seconds:            float = 0.0
    duration_source:             str   = "manifest"
    actual_frames:               int   = 0
    low_density_flag:            bool  = False
    scroll_noise_clusters:       list[dict] = field(default_factory=list)
    scroll_noise_pct:            float = 0.0
    sensitivity_audit_notes:     list[str]  = field(default_factory=list)
    grade:                       str   = "SKIP"
    notes:                       list[str]  = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def _normalise_id(raw: str) -> str:
    s = raw.translate(_TURKISH_I_MAP).lower()
    return unicodedata.normalize("NFC", s).strip()


def _resolve_pseudonym(raw_id: str) -> Optional[str]:
    """Return canonical pseudonym or None if excluded."""
    key = _normalise_id(raw_id)
    if key in IDENTITY_OVERRIDES:
        return IDENTITY_OVERRIDES[key]
    return raw_id.strip().title()


def _load_json(path: Path, label: str) -> Optional[dict]:
    if not path.is_file():
        _warn(f"{label}: file not found — {path}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _error(f"{label}: JSON parse error — {exc}")
        return None


def _frame_timestamps(manifest: dict) -> np.ndarray:
    ts = [
        float(f["source_timestamp_seconds"])
        for f in manifest.get("frames", [])
    ]
    return np.array(ts, dtype=np.float64)


def _manifest_video_duration(manifest: dict) -> float:
    return float(
        (manifest.get("video_profile") or {}).get("duration_seconds", 0.0)
    )


def _transcript_max_ts(transcript: Optional[dict]) -> float:
    """Return the maximum segment end timestamp from a transcript, or 0."""
    if transcript is None:
        return 0.0
    segs = transcript.get("segments") or []
    if not segs:
        return float(transcript.get("duration_seconds", 0.0))
    return float(max(s.get("end", 0.0) for s in segs))


def _find_video(student_id: str, video_root: Path) -> Optional[Path]:
    for ext in (".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"):
        p = video_root / f"{student_id}{ext}"
        if p.is_file():
            return p
    return None


def _infer_cohort_label(audio_root: Path) -> str:
    name = audio_root.name.lower()
    if "21april" in name: return "21april"
    if "28april" in name: return "28april"
    if "colab"   in name or "may" in name: return "05may"
    return "unknown"


def _infer_environment(audio_root: Path, forced: str) -> str:
    if forced != "auto":
        return forced
    label = _infer_cohort_label(audio_root)
    return "colab" if label == "05may" else "codap"


def _discover_students(audio_root: Path) -> list[str]:
    found: list[str] = []
    for p in sorted(audio_root.iterdir(), key=lambda x: x.name.lower()):
        if not p.is_dir():
            continue
        has_audio    = any(p.glob("*.wav")) or any(p.glob("*.m4a"))
        has_manifest = any(p.glob("*_video_extraction_manifest.json"))
        if has_audio or has_manifest:
            found.append(p.name)
    return found


# ─────────────────────────────────────────────────────────────────────────────
# SPEECH INTERVAL LOADER
# ─────────────────────────────────────────────────────────────────────────────

def _load_student_speech_intervals(
    student_dir: Path,
    student_id:  str,
) -> list[tuple[float, float]]:
    """
    Load transcript segments where the focal student was speaking.
    Returns list of (start_s, end_s) tuples.
    Falls back to empty list when transcript is absent or has no segments.
    """
    path = student_dir / f"{student_id}_transcript_labeled.json"
    transcript = _load_json(path, f"{student_id}/transcript")
    if transcript is None:
        return []
    segs = transcript.get("segments") or []
    intervals: list[tuple[float, float]] = []
    for seg in segs:
        role    = seg.get("speaker_role", "")
        focal   = seg.get("focal_pt_student_id")
        # Accept student-role segments specifically labelled for this student,
        # or unlabelled student segments (focal_pt_student_id is None) as a
        # conservative fallback when diarization did not assign focal IDs.
        if role == "student" and (focal == student_id or focal is None):
            start = float(seg.get("start", 0.0))
            end   = float(seg.get("end",   0.0))
            if end > start:
                intervals.append((start, end))
    _info(
        f"{student_id}: loaded {len(intervals)} student-speech intervals "
        f"from transcript"
    )
    return intervals


def _speech_in_window(
    t_start:   float,
    t_end:     float,
    intervals: list[tuple[float, float]],
) -> bool:
    """Return True if any speech interval overlaps [t_start, t_end]."""
    for seg_start, seg_end in intervals:
        if seg_start <= t_end and seg_end >= t_start:
            return True
    return False


# ─────────────────────────────────────────────────────────────────────────────
# CODAP CSV PARSER
# ─────────────────────────────────────────────────────────────────────────────

def _parse_codap_csv(
    csv_path:    Path,
    date_filter: Optional[str],
) -> dict[str, list[dict]]:
    """
    Parse a CODAP interaction log CSV.

    date_filter: ISO date prefix, e.g. "2026-04-21".  Rows whose created_at
    does not start with this prefix are silently discarded.  This enforces
    strict cohort-session isolation when a master CSV accumulates multiple
    calendar dates (e.g. April 7 + April 21 in the same file).

    Returns: canonical_pseudonym → [{action, timestamp_s}, …]
    """
    events_by_student: dict[str, list[dict]] = {}
    rows_accepted = 0
    rows_skipped  = 0

    try:
        with csv_path.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                if row.get("action") not in TARGET_ACTIONS:
                    continue

                created_at = row.get("created_at", "")
                if date_filter and not created_at.startswith(date_filter):
                    rows_skipped += 1
                    continue

                raw_id = row.get("student_id", "").strip()
                pseudonym = _resolve_pseudonym(raw_id)
                if pseudonym is None:
                    continue

                try:
                    ts_s = float(row["timestamp_ms"]) / 1000.0
                except (ValueError, KeyError):
                    _warn(
                        f"Cannot parse timestamp_ms in row id={row.get('id')} "
                        f"— skipping"
                    )
                    continue

                events_by_student.setdefault(pseudonym, []).append(
                    {"action": row["action"], "timestamp_s": ts_s}
                )
                rows_accepted += 1

    except OSError as exc:
        _error(f"Cannot open CSV {csv_path}: {exc}")
        return events_by_student

    _info(
        f"{csv_path.name}: accepted={rows_accepted} "
        f"date-filtered={rows_skipped} "
        f"(date_filter={date_filter!r})"
    )
    return events_by_student


# ─────────────────────────────────────────────────────────────────────────────
# BURST CLUSTERING
# ─────────────────────────────────────────────────────────────────────────────

def _cluster_events(events: list[dict]) -> list[list[dict]]:
    """
    Group sorted events into burst clusters.  Two events belong to the same
    cluster when the gap between them is ≤ BURST_GAP_S.
    """
    if not events:
        return []
    sorted_evts = sorted(events, key=lambda e: e["timestamp_s"])
    clusters: list[list[dict]] = [[sorted_evts[0]]]
    for evt in sorted_evts[1:]:
        if evt["timestamp_s"] - clusters[-1][-1]["timestamp_s"] <= BURST_GAP_S:
            clusters[-1].append(evt)
        else:
            clusters.append([evt])
    return clusters


# ─────────────────────────────────────────────────────────────────────────────
# MATCH LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def _classify_event(
    ts_log:   float,
    frame_ts: np.ndarray,
    speech:   list[tuple[float, float]],
) -> str:
    """
    Classify one log event against extracted frames + speech intervals.

    Returns:
        "strict"  — a frame within ±STRICT_WINDOW_S
        "hybrid"  — a frame within ±HYBRID_WINDOW_S  AND speech in that window
        "missed"  — no qualifying frame
    """
    if frame_ts.size == 0:
        return "missed"

    # Strict match
    strict_deltas = np.abs(frame_ts - ts_log)
    if np.any(strict_deltas <= STRICT_WINDOW_S):
        return "strict"

    # Hybrid match: frame within ±5 s
    hybrid_mask = strict_deltas <= HYBRID_WINDOW_S
    if not np.any(hybrid_mask):
        return "missed"

    # At least one frame in the ±5 s window — check for speech anchor
    window_start = ts_log - HYBRID_WINDOW_S
    window_end   = ts_log + HYBRID_WINDOW_S
    if _speech_in_window(window_start, window_end, speech):
        return "hybrid"

    return "missed"


# ─────────────────────────────────────────────────────────────────────────────
# TRACK A — CODAP AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def _infer_session_date(audio_root: Path) -> Optional[str]:
    label = _infer_cohort_label(audio_root)
    return _COHORT_DATE_MAP.get(label)


def run_codap_audit(
    audio_root: Path,
    csv_paths:  list[Path],
    students:   list[str],
) -> list[CodapStudentResult]:
    """
    Full CODAP coverage audit with burst-aware hybrid matching.
    """
    date_filter = _infer_session_date(audio_root)
    if date_filter:
        _info(f"Cohort date filter: {date_filter}")
    else:
        _warn(
            "No cohort date inferred from audio_root — "
            "all CSV rows included (may mix sessions)"
        )

    # Aggregate events across all supplied CSVs
    all_events: dict[str, list[dict]] = {}
    for csv_path in csv_paths:
        _info(f"Parsing CODAP CSV: {csv_path.name}")
        for pseudonym, evts in _parse_codap_csv(csv_path, date_filter).items():
            all_events.setdefault(pseudonym, []).extend(evts)

    results: list[CodapStudentResult] = []

    for student_id in students:
        student_dir = audio_root / student_id
        manifest = _load_json(
            student_dir / f"{student_id}_video_extraction_manifest.json",
            f"{student_id}/manifest",
        )
        res = CodapStudentResult(student_id=student_id)

        if manifest is None:
            res.grade = "FAIL"
            res.notes.append("manifest_missing")
            results.append(res)
            continue

        frame_ts = _frame_timestamps(manifest)
        res.actual_frames = int(frame_ts.size)

        log_events = all_events.get(student_id, [])
        if not log_events:
            _warn(f"{student_id}: no TARGET_ACTIONS in CSV — CODAP audit skipped")
            res.grade = "SKIP"
            res.notes.append("no_log_events_found")
            results.append(res)
            continue

        res.total_log_events = len(log_events)

        # Load student speech intervals for hybrid matching
        speech_intervals = _load_student_speech_intervals(student_dir, student_id)

        # Cluster events into bursts
        clusters = _cluster_events(log_events)
        res.burst_clusters = len(clusters)
        _info(
            f"{student_id}: {res.total_log_events} events → "
            f"{res.burst_clusters} burst clusters | "
            f"{res.actual_frames} frames | "
            f"{len(speech_intervals)} speech intervals"
        )

        # Classify every event
        strict_count = 0
        hybrid_count = 0
        missed_count = 0
        blindspots:   list[dict] = []

        for evt in log_events:
            ts_log     = evt["timestamp_s"]
            verdict    = _classify_event(ts_log, frame_ts, speech_intervals)

            if verdict == "strict":
                strict_count += 1
            elif verdict == "hybrid":
                hybrid_count += 1
            else:
                missed_count += 1
                nearest_delta: Optional[float] = (
                    float(np.min(np.abs(frame_ts - ts_log)))
                    if frame_ts.size > 0
                    else None
                )
                blindspots.append(
                    {
                        "action":            evt["action"],
                        "timestamp_s":       round(ts_log, 3),
                        "nearest_delta_s":   (
                            round(nearest_delta, 3)
                            if nearest_delta is not None
                            else None
                        ),
                        "speech_in_5s_window": _speech_in_window(
                            ts_log - HYBRID_WINDOW_S,
                            ts_log + HYBRID_WINDOW_S,
                            speech_intervals,
                        ),
                    }
                )

        res.strict_matches  = strict_count
        res.hybrid_matches  = hybrid_count
        res.dropped_events  = missed_count
        res.blindspots      = blindspots

        total_matched = strict_count + hybrid_count
        res.hybrid_coverage = (
            total_matched / res.total_log_events
            if res.total_log_events > 0
            else 1.0
        )

        # Grading
        emit_missed = sum(
            1 for b in blindspots if b["action"] == "emit_tree_data"
        )
        if res.hybrid_coverage >= HYBRID_PASS_RATIO:
            res.grade = "PASS"
        elif res.hybrid_coverage >= 0.65:
            res.grade = "WARN"
            res.notes.append(
                f"hybrid_coverage={res.hybrid_coverage:.1%} below 85 % threshold"
            )
        else:
            res.grade = "FAIL"
            res.notes.append(
                f"hybrid_coverage={res.hybrid_coverage:.1%} critically low"
            )
        if emit_missed > 0:
            tag = f"{emit_missed} emit_tree_data event(s) uncaptured"
            if res.grade == "PASS":
                res.grade = "WARN"
            res.notes.append(tag)

        _info(
            f"{student_id}: strict={strict_count} hybrid={hybrid_count} "
            f"missed={missed_count} coverage={res.hybrid_coverage:.1%} "
            f"grade={res.grade}"
        )
        results.append(res)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# SCROLL NOISE DETECTOR
# ─────────────────────────────────────────────────────────────────────────────

def _detect_scroll_noise(
    frames: list[dict],
) -> tuple[list[dict], float]:
    """
    Identify temporal clusters where consecutive frames are ≤ SCROLL_DELTA_MS
    apart AND both frames exceed SCROLL_GLOBAL_CHANGE_PCT pixel change.

    Returns (cluster_list, pct_bloated).
    """
    total = len(frames)
    if total < 2:
        return [], 0.0

    bloated_indices: set[int] = set()
    clusters: list[dict] = []
    i = 0

    while i < total - 1:
        ts_a    = float(frames[i]["source_timestamp_seconds"])
        ts_b    = float(frames[i + 1]["source_timestamp_seconds"])
        delta_ms = (ts_b - ts_a) * 1000.0

        if delta_ms > SCROLL_DELTA_MS:
            i += 1
            continue

        pct_a = float(
            (frames[i].get("metrics") or {}).get("pixel_change_percentage", 0.0)
        )
        pct_b = float(
            (frames[i + 1].get("metrics") or {}).get("pixel_change_percentage", 0.0)
        )

        if not (pct_a > SCROLL_GLOBAL_CHANGE_PCT and pct_b > SCROLL_GLOBAL_CHANGE_PCT):
            i += 1
            continue

        # Begin cluster
        cluster_start = i
        bloated_indices.add(i)
        bloated_indices.add(i + 1)
        j = i + 1

        while j < total - 1:
            ts_j     = float(frames[j]["source_timestamp_seconds"])
            ts_j1    = float(frames[j + 1]["source_timestamp_seconds"])
            d_ms     = (ts_j1 - ts_j) * 1000.0
            pct_next = float(
                (frames[j + 1].get("metrics") or {}).get(
                    "pixel_change_percentage", 0.0
                )
            )
            if d_ms <= SCROLL_DELTA_MS and pct_next > SCROLL_GLOBAL_CHANGE_PCT:
                bloated_indices.add(j + 1)
                j += 1
            else:
                break

        clusters.append(
            {
                "start_index":     cluster_start,
                "end_index":       j,
                "frame_count":     j - cluster_start + 1,
                "start_ts_s":      round(ts_a, 3),
                "end_ts_s":        round(float(frames[j]["source_timestamp_seconds"]), 3),
                "flag":            "HIGH_DENSITY_SCROLLING_NOISE",
            }
        )
        i = j + 1

    pct_bloated = (len(bloated_indices) / total * 100.0) if total > 0 else 0.0
    return clusters, round(pct_bloated, 2)


# ─────────────────────────────────────────────────────────────────────────────
# ROI SENSITIVITY SIMULATION
# ─────────────────────────────────────────────────────────────────────────────

def _run_sensitivity_simulation(
    student_id:   str,
    frame_entry:  dict,
    video_path:   Path,
) -> list[str]:
    """
    Load the video at frame_entry's timestamp, split into ROI zones
    (code-editor band vs. output pane), run cv2.absdiff over
    SENSITIVITY_WINDOW_S seconds, and report reclassification potential
    at SENSITIVITY_LOW_DELTA.

    All video capture resources are released inside a try-finally block
    to prevent memory leaks on Apple Silicon unified memory.
    """
    notes: list[str] = []
    ts_anchor = float(frame_entry["source_timestamp_seconds"])

    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            notes.append(
                f"sim_skipped: cv2 cannot open {video_path.name}"
            )
            return notes

        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 120:
            fps = 30.0

        cap.set(cv2.CAP_PROP_POS_MSEC, ts_anchor * 1000.0)
        ret, anchor_bgr = cap.read()
        if not ret:
            notes.append(
                f"sim_skipped: cannot read frame at t={ts_anchor:.1f}s"
            )
            return notes

        h, w = anchor_bgr.shape[:2]

        # Colab ROI layout
        # Editor band  : rows 8–92 %,  cols 15–96 %
        # Output pane  : rows 75–100 %, cols 0–100 %
        er0 = int(h * 0.08);  er1 = int(h * 0.92)
        ec0 = int(w * 0.15);  ec1 = int(w * 0.96)
        or0 = int(h * 0.75);  or1 = h
        oc0 = 0;               oc1 = w

        anchor_gray   = cv2.cvtColor(anchor_bgr, cv2.COLOR_BGR2GRAY)
        anchor_editor = anchor_gray[er0:er1, ec0:ec1]
        anchor_output = anchor_gray[or0:or1, oc0:oc1]

        editor_deltas: list[float] = []
        output_deltas: list[float] = []
        global_deltas: list[float] = []
        frames_sampled = 0
        end_ts_s = ts_anchor + SENSITIVITY_WINDOW_S

        while True:
            ret, next_bgr = cap.read()
            if not ret:
                break
            pos_s = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if pos_s > end_ts_s:
                break

            next_gray = cv2.cvtColor(next_bgr, cv2.COLOR_BGR2GRAY)

            diff_global = cv2.absdiff(anchor_gray, next_gray)
            global_deltas.append(
                float(np.count_nonzero(diff_global > 25)) / diff_global.size
            )

            editor_crop = next_gray[er0:er1, ec0:ec1]
            diff_editor = cv2.absdiff(anchor_editor, editor_crop)
            editor_deltas.append(
                float(np.count_nonzero(diff_editor > 25)) / diff_editor.size
            )

            output_crop = next_gray[or0:or1, oc0:oc1]
            diff_output = cv2.absdiff(anchor_output, output_crop)
            output_deltas.append(
                float(np.count_nonzero(diff_output > 25)) / diff_output.size
            )

            frames_sampled += 1

    finally:
        cap.release()

    if not editor_deltas:
        notes.append(
            f"sim_complete: no frames found in "
            f"{SENSITIVITY_WINDOW_S:.0f}s window after t={ts_anchor:.1f}s"
        )
        return notes

    mean_editor = float(np.mean(editor_deltas))
    mean_output = float(np.mean(output_deltas))
    mean_global = float(np.mean(global_deltas))
    max_editor  = float(np.max(editor_deltas))

    notes.append(
        f"anchor_t={ts_anchor:.1f}s "
        f"window={SENSITIVITY_WINDOW_S:.0f}s "
        f"frames_sampled={frames_sampled}"
    )
    notes.append(
        f"mean_editor_delta={mean_editor:.5f}  "
        f"mean_output_delta={mean_output:.5f}  "
        f"mean_global_delta={mean_global:.5f}"
    )

    would_reclassify = max_editor >= SENSITIVITY_LOW_DELTA
    notes.append(
        f"max_editor_delta={max_editor:.5f}  "
        f"sensitivity_threshold={SENSITIVITY_LOW_DELTA:.4f}  "
        f"would_reclassify={would_reclassify}"
    )

    if would_reclassify and mean_editor < 0.012:
        notes.append(
            "LOW_SENSITIVITY_FINDING: sub-threshold editor activity detected "
            f"(mean_editor={mean_editor:.5f} < 0.012) — lowering local delta "
            "to 0.1 % would capture additional typing frames in this session"
        )
    else:
        notes.append(
            "sensitivity_conclusion: current motion threshold is adequate; "
            "no reclassification benefit at 0.1 % local delta"
        )

    return notes


# ─────────────────────────────────────────────────────────────────────────────
# TRACK B — COLAB AUDIT
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_effective_duration(
    student_id:  str,
    student_dir: Path,
    manifest:    dict,
) -> tuple[float, str]:
    """
    Determine the effective session duration.

    Priority:
      1. Cross-check manifest video_profile.duration_seconds against
         transcript max segment end (the Shana Guard).
         If transcript_max > video_duration * DURATION_DISCREPANCY_RATIO,
         override with transcript_max and report source as "transcript".
      2. Fall back to manifest video_profile.duration_seconds.
      3. Use last extracted frame timestamp when video_profile is 0.

    Returns (duration_seconds, source_label).
    """
    manifest_dur = _manifest_video_duration(manifest)

    # Try loading the transcript for this student
    transcript_path = student_dir / f"{student_id}_transcript_labeled.json"
    if not transcript_path.is_file():
        transcript_path = student_dir / f"{student_id}_transcript.json"
    transcript = _load_json(transcript_path, f"{student_id}/transcript")
    transcript_max = _transcript_max_ts(transcript)

    if (
        transcript_max > 0
        and manifest_dur > 0
        and transcript_max > manifest_dur * DURATION_DISCREPANCY_RATIO
    ):
        _warn(
            f"{student_id}: Shana Guard triggered — "
            f"manifest_duration={manifest_dur:.0f}s "
            f"transcript_max={transcript_max:.0f}s "
            f"(ratio={transcript_max/manifest_dur:.1f}×) — "
            f"overriding with transcript timeline"
        )
        return transcript_max, "transcript_override"

    if manifest_dur > 0:
        return manifest_dur, "manifest"

    # Last-resort: derive from last frame timestamp
    frames = manifest.get("frames", [])
    if frames:
        last_ts = max(
            float(f["source_timestamp_seconds"]) for f in frames
        )
        _warn(
            f"{student_id}: video_profile.duration_seconds=0 — "
            f"using last frame timestamp ({last_ts:.0f}s) as duration proxy"
        )
        return last_ts, "last_frame_proxy"

    return 0.0, "unknown"


def run_colab_audit(
    audio_root: Path,
    video_root: Optional[Path],
    students:   list[str],
) -> list[ColabStudentResult]:
    """
    Colab session audit: density anomaly, scroll noise, ROI sensitivity.
    _calibration_sim_done is a local variable — no global bleed between runs.
    """
    results: list[ColabStudentResult] = []
    _calibration_sim_done = False   # local to this invocation

    for student_id in students:
        student_dir = audio_root / student_id
        manifest = _load_json(
            student_dir / f"{student_id}_video_extraction_manifest.json",
            f"{student_id}/manifest",
        )
        res = ColabStudentResult(student_id=student_id)

        if manifest is None:
            res.grade = "FAIL"
            res.notes.append("manifest_missing")
            results.append(res)
            continue

        frames = sorted(
            manifest.get("frames", []),
            key=lambda f: float(f["source_timestamp_seconds"]),
        )
        res.actual_frames = len(frames)

        # ── Effective Duration (Shana Guard) ──────────────────────────────────
        effective_dur, dur_source = _resolve_effective_duration(
            student_id, student_dir, manifest
        )
        res.duration_seconds = effective_dur
        res.duration_source  = dur_source

        _info(
            f"{student_id}: frames={res.actual_frames}  "
            f"duration={effective_dur:.0f}s ({dur_source})"
        )

        # ── Density Anomaly Detector ──────────────────────────────────────────
        if (
            effective_dur >= LOW_DENSITY_MIN_DURATION_S
            and res.actual_frames < LOW_DENSITY_MIN_FRAMES
        ):
            res.low_density_flag = True
            res.notes.append(
                f"LOW_DENSITY_POTENTIAL_DATA_LOSS: "
                f"{res.actual_frames} frames for "
                f"{effective_dur / 60:.1f} min session"
            )
            _warn(
                f"{student_id}: LOW_DENSITY — "
                f"{res.actual_frames} frames / {effective_dur/60:.1f} min"
            )

        # ── Scrolling Noise Detector ──────────────────────────────────────────
        scroll_clusters, scroll_pct = _detect_scroll_noise(frames)
        res.scroll_noise_clusters = scroll_clusters
        res.scroll_noise_pct      = scroll_pct
        if scroll_clusters:
            res.notes.append(
                f"HIGH_DENSITY_SCROLLING_NOISE: "
                f"{len(scroll_clusters)} cluster(s), "
                f"{scroll_pct:.1f}% of frames bloated"
            )
            _warn(
                f"{student_id}: {len(scroll_clusters)} scroll cluster(s), "
                f"{scroll_pct:.1f}% bloated"
            )

        # ── ROI Sensitivity Simulation ────────────────────────────────────────
        # Always runs for low-density sessions (diagnostic).
        # Runs exactly once for non-low-density sessions (calibration probe).
        run_sim = res.low_density_flag or (
            not _calibration_sim_done and video_root is not None and frames
        )
        if run_sim and video_root is not None and frames:
            video_path = _find_video(student_id, video_root)
            if video_path is not None:
                target_frame = frames[len(frames) // 2]
                sim_label = "sensitivity" if res.low_density_flag else "calibration"
                _info(
                    f"{student_id}: ROI {sim_label} sim at "
                    f"t={target_frame['source_timestamp_seconds']:.1f}s"
                )
                sim_notes = _run_sensitivity_simulation(
                    student_id, target_frame, video_path
                )
                res.sensitivity_audit_notes.extend(sim_notes)
                if not res.low_density_flag:
                    _calibration_sim_done = True
            else:
                res.sensitivity_audit_notes.append(
                    f"sim_skipped: video file not found in {video_root}"
                )

        # ── Grade ─────────────────────────────────────────────────────────────
        if res.actual_frames == 0:
            res.grade = "FAIL"
            res.notes.append("zero_frames_extracted")
        elif res.low_density_flag:
            low_sens = any(
                "LOW_SENSITIVITY_FINDING" in n
                for n in res.sensitivity_audit_notes
            )
            res.grade = "FAIL" if low_sens else "WARN"
        elif scroll_clusters and scroll_pct > 20.0:
            res.grade = "WARN"
            res.notes.append(f"excessive_scroll_noise: {scroll_pct:.1f}%")
        else:
            res.grade = "PASS"

        _info(
            f"{student_id}: grade={res.grade}  "
            f"low_density={res.low_density_flag}  "
            f"scroll_clusters={len(scroll_clusters)}"
        )
        results.append(res)

    return results


# ─────────────────────────────────────────────────────────────────────────────
# STDOUT TABLE
# ─────────────────────────────────────────────────────────────────────────────

_GRADE_BADGE = {
    "PASS": "✔ PASS",
    "WARN": "⚠ WARN",
    "FAIL": "✘ FAIL",
    "SKIP": "– SKIP",
}

_COL = {
    "student":  14,
    "env":       6,
    "expected": 10,
    "frames":    8,
    "strict":    8,
    "hybrid":    8,
    "dropped":   8,
    "status":   10,
}


def _table_row(*cells: str) -> str:
    widths = list(_COL.values())
    parts = [c.ljust(widths[i]) for i, c in enumerate(cells)]
    return " ".join(parts)


def _render_table(
    codap_results: list[CodapStudentResult],
    colab_results: list[ColabStudentResult],
) -> str:
    header = _table_row(
        "Student", "Env", "Expected", "Frames",
        "Strict(1s)", "Hybr(5s)", "Dropped", "Status",
    )
    sep = "─" * len(header)
    rows = [sep, header, sep]

    for r in codap_results:
        rows.append(
            _table_row(
                r.student_id,
                "CODAP",
                str(r.total_log_events),
                str(r.actual_frames),
                str(r.strict_matches),
                str(r.hybrid_matches),
                str(r.dropped_events),
                _GRADE_BADGE.get(r.grade, r.grade),
            )
        )

    if codap_results and colab_results:
        rows.append(sep)

    for r in colab_results:
        density_tag = f"{r.actual_frames}/{r.duration_seconds/60:.0f}min"
        rows.append(
            _table_row(
                r.student_id,
                "Colab",
                density_tag,
                str(r.actual_frames),
                "–",
                "–",
                f"{r.scroll_noise_pct:.1f}%scroll",
                _GRADE_BADGE.get(r.grade, r.grade),
            )
        )

    rows.append(sep)
    return "\n".join(rows)


# ─────────────────────────────────────────────────────────────────────────────
# JSON REPORT BUILDER
# ─────────────────────────────────────────────────────────────────────────────

def _build_json_report(
    codap_results: list[CodapStudentResult],
    colab_results: list[ColabStudentResult],
    audio_root:    Path,
    csv_paths:     list[Path],
) -> dict:
    import datetime

    codap_payload: list[dict] = []
    for r in codap_results:
        codap_payload.append(
            {
                "student_id":        r.student_id,
                "environment":       r.environment,
                "total_log_events":  r.total_log_events,
                "actual_frames":     r.actual_frames,
                "strict_matches":    r.strict_matches,
                "hybrid_matches":    r.hybrid_matches,
                "dropped_events":    r.dropped_events,
                "hybrid_coverage":   round(r.hybrid_coverage, 6),
                "burst_clusters":    r.burst_clusters,
                "blindspots":        r.blindspots,
                "grade":             r.grade,
                "notes":             r.notes,
            }
        )

    colab_payload: list[dict] = []
    for r in colab_results:
        colab_payload.append(
            {
                "student_id":              r.student_id,
                "environment":             r.environment,
                "duration_seconds":        round(r.duration_seconds, 3),
                "duration_source":         r.duration_source,
                "actual_frames":           r.actual_frames,
                "low_density_flag":        r.low_density_flag,
                "scroll_noise_clusters":   r.scroll_noise_clusters,
                "scroll_noise_pct":        r.scroll_noise_pct,
                "sensitivity_audit_notes": r.sensitivity_audit_notes,
                "grade":                   r.grade,
                "notes":                   r.notes,
            }
        )

    all_grades = [r.grade for r in codap_results] + [r.grade for r in colab_results]
    overall = (
        "FAIL" if "FAIL" in all_grades
        else "WARN" if "WARN" in all_grades
        else "PASS" if all_grades
        else "SKIP"
    )

    codap_g = [r.grade for r in codap_results]
    colab_g = [r.grade for r in colab_results]

    return {
        "schema_version": "2.0",
        "generated_at":   datetime.datetime.now().isoformat(),
        "audio_root":     str(audio_root),
        "csv_sources":    [str(p) for p in csv_paths],
        "overall_grade":  overall,
        "codap_audit":    codap_payload,
        "colab_audit":    colab_payload,
        "summary": {
            "codap_students":   len(codap_results),
            "codap_pass":       codap_g.count("PASS"),
            "codap_warn":       codap_g.count("WARN"),
            "codap_fail":       codap_g.count("FAIL"),
            "codap_skip":       codap_g.count("SKIP"),
            "colab_students":   len(colab_results),
            "colab_pass":       colab_g.count("PASS"),
            "colab_warn":       colab_g.count("WARN"),
            "colab_fail":       colab_g.count("FAIL"),
            "hybrid_pass_threshold_pct": int(HYBRID_PASS_RATIO * 100),
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# OUTPUT PATH AUTO-DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def _default_output_path(audio_root: Path, provided: Optional[Path]) -> Path:
    if provided is not None:
        return provided
    label = _infer_cohort_label(audio_root)
    return LOG_DIR / f"qa_coverage_report_{label}.json"


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=(
            "MMLA Pipeline Coverage Validator v2 — "
            "CODAP burst-aware hybrid audit + Colab heuristic audit"
        )
    )
    p.add_argument(
        "--audio-root", type=Path, required=True,
        help="Cohort audio+manifest root (one sub-dir per student).",
    )
    p.add_argument(
        "--codap-logs-dir", type=Path, default=None,
        help="Directory containing CODAP interaction log CSV files.",
    )
    p.add_argument(
        "--video-root", type=Path, default=None,
        help="Directory containing raw video files (for ROI simulation).",
    )
    p.add_argument(
        "--environment", choices=["codap", "colab", "auto"], default="auto",
        help="Force environment type (default: auto-detect from path).",
    )
    p.add_argument(
        "--student", action="append", dest="students",
        metavar="STUDENT_ID",
        help="Restrict audit to specific student(s). Repeatable.",
    )
    p.add_argument(
        "--output", type=Path, default=None,
        help="JSON report output path (auto-derived from cohort if omitted).",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)

    if args.verbose:
        LOGGER.setLevel(logging.DEBUG)

    audio_root: Path = args.audio_root.resolve()
    if not audio_root.is_dir():
        _error(f"--audio-root does not exist: {audio_root}")
        return 1

    students = args.students or _discover_students(audio_root)
    if not students:
        _error(f"No students discovered in {audio_root}")
        return 1

    environment = _infer_environment(audio_root, args.environment)
    _info(f"Audio root  : {audio_root}")
    _info(f"Environment : {environment}")
    _info(f"Students    : {students}")

    # ── Run appropriate audit track ───────────────────────────────────────────
    codap_results: list[CodapStudentResult] = []
    colab_results: list[ColabStudentResult] = []
    csv_paths:     list[Path]               = []

    if environment == "codap":
        if args.codap_logs_dir:
            logs_dir  = args.codap_logs_dir.resolve()
            csv_paths = sorted(logs_dir.glob("*.csv"))
        else:
            # Auto-locate CSVs from All Documents matching cohort
            label = _infer_cohort_label(audio_root)
            if ALL_DOCS.is_dir():
                if label == "21april":
                    csv_paths = sorted(ALL_DOCS.glob("*21*Nisan*.csv"))
                elif label == "28april":
                    csv_paths = sorted(ALL_DOCS.glob("*28*Nisan*.csv"))
                else:
                    csv_paths = sorted(ALL_DOCS.glob("*.csv"))

        if not csv_paths:
            _error(
                "No CODAP CSV logs found. "
                "Provide --codap-logs-dir or ensure "
                "data_sources_2026/All Documents contains the CSVs."
            )
            return 1

        codap_results = run_codap_audit(audio_root, csv_paths, students)

    elif environment == "colab":
        video_root: Optional[Path] = None
        if args.video_root:
            video_root = args.video_root.resolve()
        else:
            default_vr = (
                REPO_ROOT / "data_sources_2026"
                / "05 May Colab Python Screen Recordings"
            )
            if default_vr.is_dir():
                video_root = default_vr
                _info(f"Auto-detected video root: {video_root}")
        colab_results = run_colab_audit(audio_root, video_root, students)

    # ── Print table ───────────────────────────────────────────────────────────
    table = _render_table(codap_results, colab_results)
    print("\nMMLA COVERAGE VALIDATION REPORT  (v2 — Burst-Aware + Shana Guard)")
    print("=" * 80)
    print(table)

    all_grades = (
        [r.grade for r in codap_results]
        + [r.grade for r in colab_results]
    )
    overall = (
        "FAIL" if "FAIL" in all_grades
        else "WARN" if "WARN" in all_grades
        else "PASS" if all_grades
        else "SKIP"
    )
    print(f"\nOverall Pipeline Grade : {_GRADE_BADGE.get(overall, overall)}")

    if codap_results:
        total_events   = sum(r.total_log_events for r in codap_results)
        total_strict   = sum(r.strict_matches   for r in codap_results)
        total_hybrid   = sum(r.hybrid_matches   for r in codap_results)
        total_dropped  = sum(r.dropped_events   for r in codap_results)
        total_matched  = total_strict + total_hybrid
        ratio          = total_matched / total_events if total_events else 0.0
        print(
            f"CODAP Hybrid Coverage  : {total_matched}/{total_events} "
            f"({ratio:.1%})  |  strict={total_strict}  "
            f"hybrid={total_hybrid}  dropped={total_dropped}"
        )

    if colab_results:
        low_d    = sum(1 for r in colab_results if r.low_density_flag)
        scroll_n = sum(len(r.scroll_noise_clusters) for r in colab_results)
        print(
            f"Colab Summary          : {len(colab_results)} students  |  "
            f"low-density flags={low_d}  |  scroll clusters={scroll_n}"
        )

    print()

    # ── Write JSON report ─────────────────────────────────────────────────────
    report  = _build_json_report(codap_results, colab_results, audio_root, csv_paths)
    outpath = _default_output_path(audio_root, args.output)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    outpath.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    _info(f"JSON report → {outpath}")

    return 0 if overall in ("PASS", "WARN", "SKIP") else 1


if __name__ == "__main__":
    raise SystemExit(main())
