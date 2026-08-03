#!/usr/bin/env python3
"""Amy 432-frame MMLA quality audit: pHash delta analysis + diarization gap detection."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dynamic_video_analytics import NON_TASK_HASH_SIZE, frame_phash

AMY_DIR = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio" / "Amy"
FRAMES_DIR = AMY_DIR / "Amy_frames"
MANIFEST_PATH = AMY_DIR / "Amy_video_extraction_manifest.json"
DIARIZATION_PATH = AMY_DIR / "Amy_hybrid_diarization.json"
OUTPUT_DIR = REPO_ROOT / "students" / "Amy" / "mmla_quality_audit"
PHASH_THRESHOLD = 4
SAMPLE_EVERY = 15


@dataclass
class FrameMeta:
    frame_id: str
    timestamp_s: float
    trigger: str
    path: Path


def load_frames() -> list[FrameMeta]:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    frames: list[FrameMeta] = []
    for entry in manifest["frames"]:
        rel = entry["file_path"]
        path = REPO_ROOT / rel if not Path(rel).is_absolute() else Path(rel)
        frames.append(
            FrameMeta(
                frame_id=entry["frame_id"],
                timestamp_s=float(entry["source_timestamp_seconds"]),
                trigger=entry["extraction_trigger_reason"],
                path=path,
            )
        )
    frames.sort(key=lambda f: f.timestamp_s)
    return frames


def consecutive_phash_deltas(frames: list[FrameMeta]) -> dict[str, object]:
    hashes: list[object] = []
    for meta in frames:
        bgr = cv2.imread(str(meta.path))
        if bgr is None:
            raise FileNotFoundError(meta.path)
        hashes.append(frame_phash(bgr))

    distances: list[float] = []
    mid_timestamps: list[float] = []
    for idx in range(len(hashes) - 1):
        distances.append(float(hashes[idx] - hashes[idx + 1]))
        mid_timestamps.append((frames[idx].timestamp_s + frames[idx + 1].timestamp_s) / 2.0)

    dist_arr = np.array(distances, dtype=np.float64)
    ts_arr = np.array(mid_timestamps, dtype=np.float64)
    time_gaps = np.diff(np.array([f.timestamp_s for f in frames], dtype=np.float64))

    near_zero_runs: list[dict[str, float]] = []
    run_start: int | None = None
    for i, d in enumerate(distances):
        if d <= PHASH_THRESHOLD:
            if run_start is None:
                run_start = i
        elif run_start is not None:
            span = i - run_start
            if span >= 5:
                near_zero_runs.append(
                    {
                        "start_timestamp_s": mid_timestamps[run_start],
                        "end_timestamp_s": mid_timestamps[i - 1],
                        "consecutive_pairs": span,
                        "mean_distance": float(np.mean(distances[run_start:i])),
                    }
                )
            run_start = None
    if run_start is not None and len(distances) - run_start >= 5:
        near_zero_runs.append(
            {
                "start_timestamp_s": mid_timestamps[run_start],
                "end_timestamp_s": mid_timestamps[-1],
                "consecutive_pairs": len(distances) - run_start,
                "mean_distance": float(np.mean(distances[run_start:])),
            }
        )

    return {
        "distances": distances,
        "mid_timestamps": mid_timestamps,
        "time_gaps_s": time_gaps.tolist(),
        "stats": {
            "pair_count": len(distances),
            "mean": float(dist_arr.mean()),
            "median": float(np.median(dist_arr)),
            "std": float(dist_arr.std()),
            "min": float(dist_arr.min()),
            "max": float(dist_arr.max()),
            "pct_at_or_below_threshold": float(100.0 * np.mean(dist_arr <= PHASH_THRESHOLD)),
            "pct_above_threshold": float(100.0 * np.mean(dist_arr > PHASH_THRESHOLD)),
            "pct_above_8": float(100.0 * np.mean(dist_arr > 8)),
            "mean_time_gap_s": float(time_gaps.mean()),
            "median_time_gap_s": float(np.median(time_gaps)),
            "max_time_gap_s": float(time_gaps.max()),
        },
        "near_zero_runs": near_zero_runs,
    }


def plot_phash_delta(frames: list[FrameMeta], delta: dict[str, object], out_path: Path) -> None:
    ts = delta["mid_timestamps"]
    dist = delta["distances"]
    frame_ts = [f.timestamp_s for f in frames]

    fig, axes = plt.subplots(2, 1, figsize=(14, 8), sharex=False, gridspec_kw={"height_ratios": [3, 1]})

    ax0 = axes[0]
    ax0.plot(ts, dist, color="#2563eb", linewidth=0.9, alpha=0.85, label="pHash Hamming distance")
    ax0.axhline(PHASH_THRESHOLD, color="#dc2626", linestyle="--", linewidth=1.2, label=f"dedup threshold ({PHASH_THRESHOLD})")
    ax0.fill_between(ts, 0, dist, where=np.array(dist) > PHASH_THRESHOLD, color="#22c55e", alpha=0.12, label="information gain zone")
    ax0.set_ylabel("Hamming distance $d_H(f_t, f_{t+1})$")
    ax0.set_title("Amy CODAP Frame Set — Consecutive pHash Delta vs Time")
    ax0.legend(loc="upper right", fontsize=9)
    ax0.grid(True, alpha=0.25)
    ax0.set_ylim(bottom=-0.5)

    ax1 = axes[1]
    ax1.scatter(frame_ts, np.ones(len(frame_ts)), s=8, c="#7c3aed", alpha=0.7)
    ax1.set_yticks([])
    ax1.set_xlabel("Source timestamp (seconds)")
    ax1.set_title("Extracted frame timeline (432 keyframes)")
    ax1.grid(True, axis="x", alpha=0.25)

    fig.tight_layout()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def load_diarization_segments() -> list[dict[str, object]]:
    data = json.loads(DIARIZATION_PATH.read_text(encoding="utf-8"))
    return data.get("segments", data.get("utterances", []))


def gap_analysis(frames: list[FrameMeta], segments: list[dict[str, object]]) -> dict[str, object]:
    frame_ts = np.array([f.timestamp_s for f in frames], dtype=np.float64)
    student_segments = [
        s
        for s in segments
        if s.get("speaker_role") == "student" and float(s.get("end", 0)) - float(s.get("start", 0)) >= 3.0
    ]

    def nearest_frame_distance(t: float) -> float:
        return float(np.min(np.abs(frame_ts - t)))

    high_interaction_gaps: list[dict[str, object]] = []
    for seg in student_segments:
        start = float(seg["start"])
        end = float(seg["end"])
        duration = end - start
        if duration < 8.0:
            continue
        mask = (frame_ts >= start) & (frame_ts <= end)
        frames_in_window = int(mask.sum())
        if frames_in_window == 0:
            high_interaction_gaps.append(
                {
                    "start_s": start,
                    "end_s": end,
                    "duration_s": duration,
                    "text_preview": str(seg.get("text", ""))[:120],
                    "frames_in_window": 0,
                    "gap_type": "zero_coverage",
                }
            )
            continue
        window_ts = frame_ts[mask]
        if len(window_ts) >= 2:
            max_internal_gap = float(np.max(np.diff(window_ts)))
        else:
            max_internal_gap = duration
        if max_internal_gap > 45.0:
            high_interaction_gaps.append(
                {
                    "start_s": start,
                    "end_s": end,
                    "duration_s": duration,
                    "text_preview": str(seg.get("text", ""))[:120],
                    "frames_in_window": frames_in_window,
                    "max_internal_gap_s": max_internal_gap,
                    "gap_type": "sparse_coverage",
                }
            )

    codap_era_mask = (frame_ts >= 900) & (frame_ts <= 3600)
    codap_era_gaps = np.diff(frame_ts[codap_era_mask]) if codap_era_mask.sum() > 1 else np.array([])

    return {
        "student_segments_ge_8s": len([s for s in student_segments if float(s["end"]) - float(s["start"]) >= 8.0]),
        "zero_coverage_student_windows": [g for g in high_interaction_gaps if g["gap_type"] == "zero_coverage"],
        "sparse_coverage_student_windows": [g for g in high_interaction_gaps if g["gap_type"] == "sparse_coverage"],
        "codap_era_frame_count": int(codap_era_mask.sum()),
        "codap_era_max_gap_s": float(codap_era_gaps.max()) if codap_era_gaps.size else 0.0,
        "codap_era_mean_gap_s": float(codap_era_gaps.mean()) if codap_era_gaps.size else 0.0,
        "overall_max_gap_s": float(np.diff(frame_ts).max()) if len(frame_ts) > 1 else 0.0,
    }


def systematic_sample(frames: list[FrameMeta], every: int = SAMPLE_EVERY) -> list[FrameMeta]:
    sampled = [frames[i] for i in range(0, len(frames), every)]
    if frames[-1].frame_id != sampled[-1].frame_id:
        sampled.append(frames[-1])
    return sampled


def export_sample_manifest(sampled: list[FrameMeta], out_path: Path) -> None:
    payload = [
        {
            "frame_id": f.frame_id,
            "timestamp_s": f.timestamp_s,
            "trigger": f.trigger,
            "file_path": str(f.path.relative_to(REPO_ROOT)),
        }
        for f in sampled
    ]
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    frames = load_frames()
    if len(frames) != 432:
        print(f"WARNING: expected 432 frames, found {len(frames)}")

    delta = consecutive_phash_deltas(frames)
    chart_path = OUTPUT_DIR / "amy_phash_delta_analysis.png"
    plot_phash_delta(frames, delta, chart_path)

    segments = load_diarization_segments()
    gaps = gap_analysis(frames, segments)
    sampled = systematic_sample(frames)
    export_sample_manifest(sampled, OUTPUT_DIR / "qa_sample_manifest.json")

    report = {
        "frame_count": len(frames),
        "phash_delta": delta["stats"],
        "near_zero_runs": delta["near_zero_runs"],
        "gap_analysis": gaps,
        "qa_sample_count": len(sampled),
        "qa_sample_ids": [f.frame_id for f in sampled],
        "chart_path": str(chart_path.relative_to(REPO_ROOT)),
    }
    report_path = OUTPUT_DIR / "amy_frame_quality_audit_metrics.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nWrote chart: {chart_path}")
    print(f"Wrote metrics: {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
