#!/usr/bin/env python3
"""Expert MMLA extraction quality gate for a single student frame set."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dynamic_video_analytics import (
    DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    DEFAULT_NON_TASK_TEMPLATE_DIR,
    CodapContentAnalyzer,
    ColabContentAnalyzer,
    NonTaskScreenFilter,
    TaskActivity,
    build_task_screen_guard,
    frame_kept_by_pipeline_guard,
    frame_phash,
    task_activity_from_params,
)

PHASH_THRESHOLD = 4
MIN_PILOT_CONTENT_SCORE = 4
MAX_CODAP_GAP_S  = 140
MAX_COLAB_GAP_S  = 360   # Colab: window-switch / thinking pauses are longer
MAX_NON_CODAP_IN_FULL = 0
MIN_PCT_PHASH_ABOVE_THRESHOLD = 65.0


@dataclass
class GateResult:
    passed: bool = True
    checks: list[dict[str, object]] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)

    def add(self, name: str, passed: bool, detail: str, **extra: object) -> None:
        row = {"check": name, "passed": passed, "detail": detail, **extra}
        self.checks.append(row)
        if not passed:
            self.passed = False
            self.blockers.append(f"{name}: {detail}")


def load_manifest(student_dir: Path, student_id: str) -> dict:
    path = student_dir / f"{student_id}_video_extraction_manifest.json"
    return json.loads(path.read_text(encoding="utf-8"))


def task_activity_from_manifest(params: dict) -> TaskActivity:
    return task_activity_from_params(params)


def frame_is_task(bgr: np.ndarray, task_guard, task_activity: TaskActivity) -> bool:
    if task_guard is not None:
        return task_guard.classify(bgr).is_task
    if task_activity == "colab":
        signals = ColabContentAnalyzer.analyze(bgr)
        return ColabContentAnalyzer.is_colab_task(signals)
    signals = CodapContentAnalyzer.analyze(bgr)
    return CodapContentAnalyzer.is_codap_task(signals)


def validate_student(student_dir: Path, student_id: str) -> GateResult:
    result = GateResult()
    manifest = load_manifest(student_dir, student_id)
    frames = sorted(manifest.get("frames", []), key=lambda e: e["source_timestamp_seconds"])
    params = manifest.get("parameters", {})
    task_activity = task_activity_from_manifest(params)

    task_guard = build_task_screen_guard(
        task_activity,
        codap_template_dir=DEFAULT_CODAP_TASK_TEMPLATE_DIR,
        colab_template_dir=DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    )
    filt = NonTaskScreenFilter(
        DEFAULT_NON_TASK_TEMPLATE_DIR,
        task_guard=task_guard,
        require_codap_content=True,
        phash_threshold=10,
    )

    non_task: list[str] = []
    would_skip: list[str] = []
    weak_template: list[str] = []
    hashes: list[object] = []
    timestamps: list[float] = []

    for entry in frames:
        path = REPO_ROOT / entry["file_path"]
        bgr = cv2.imread(str(path))
        if bgr is None:
            non_task.append(entry["frame_id"])
            continue

        trigger = entry.get("extraction_trigger_reason", "motion_threshold_exceeded")
        kept = frame_kept_by_pipeline_guard(
            bgr,
            filt=filt,
            task_guard=task_guard,
            trigger_reason=trigger,
            task_activity=task_activity,
        )
        if not kept:
            non_task.append(entry["frame_id"])
            would_skip.append(entry["frame_id"])

        guard_match = task_guard.classify(bgr) if task_guard else None
        if (
            guard_match
            and guard_match.reason.startswith(("template+content", "colab_template+content"))
            and task_activity != "colab"
        ):
            signals = CodapContentAnalyzer.analyze(bgr)
            if signals.content_score < MIN_PILOT_CONTENT_SCORE:
                weak_template.append(entry["frame_id"])

        hashes.append(frame_phash(bgr))
        timestamps.append(float(entry["source_timestamp_seconds"]))

    task_label = "Colab" if task_activity == "colab" else "CODAP"
    result.add(
        "no_non_codap_frames",
        len(non_task) == 0,
        f"{len(non_task)} non-{task_label} frames: {non_task[:8]}",
        offenders=non_task,
    )
    result.add(
        "no_would_skip_frames",
        len(would_skip) == 0,
        f"{len(would_skip)} frames fail current filter: {would_skip[:8]}",
        offenders=would_skip,
    )
    param_keys = [
        "codap_task_phash_threshold",
        "cooldown_ms",
        "speech_gap_bypass_seconds",
        "require_codap_content",
        "task_activity",
        "codap_gap_fill_seconds",
    ]
    param_snapshot = {key: params.get(key) for key in param_keys}
    result.add(
        "strict_guard_params",
        params.get("codap_task_phash_threshold") == 12
        and params.get("cooldown_ms") == 1000
        and params.get("speech_gap_bypass_seconds") == 120
        and params.get("require_codap_content") is True
        and params.get("task_activity") == task_activity,
        f"params={param_snapshot}",
    )

    if len(hashes) > 1:
        dist = np.array([float(hashes[i] - hashes[i + 1]) for i in range(len(hashes) - 1)])
        pct_above = float(100.0 * np.mean(dist > PHASH_THRESHOLD))
        result.add(
            "phash_information_gain",
            pct_above >= MIN_PCT_PHASH_ABOVE_THRESHOLD,
            f"{pct_above:.1f}% pairs > {PHASH_THRESHOLD} (min {MIN_PCT_PHASH_ABOVE_THRESHOLD}%)",
            pct_above=pct_above,
        )

    ts = np.array(sorted(timestamps))
    if ts.size > 1:
        codap_ts = ts[(ts >= 900) & (ts <= 3600)]
        if codap_ts.size > 1:
            max_gap = float(np.max(np.diff(codap_ts)))
            gap_limit = MAX_COLAB_GAP_S if task_activity == "colab" else MAX_CODAP_GAP_S
            result.add(
                "codap_era_max_gap",
                max_gap <= gap_limit,
                f"max gap {max_gap:.1f}s in 900-3600s (limit {gap_limit}s)",
                max_gap_s=max_gap,
            )

    pilot_dir = student_dir / f"{student_id}_frames_pilot"
    pilot_manifest = student_dir / f"{student_id}_video_extraction_manifest_frames_pilot.json"
    if pilot_manifest.is_file():
        pilot = json.loads(pilot_manifest.read_text(encoding="utf-8"))
        pilot_count = len(pilot.get("frames", []))
        rejected = pilot.get("refinement", {}).get("rejected_frame_count", 0)
        result.add(
            "pilot_export_exists",
            pilot_dir.is_dir() and pilot_count > 0,
            f"pilot={pilot_count}, rejected={rejected}",
            pilot_frames=pilot_count,
        )
        pilot_offenders = []
        for entry in pilot.get("frames", []):
            path = REPO_ROOT / entry["file_path"]
            bgr = cv2.imread(str(path))
            trigger = entry.get("extraction_trigger_reason", "motion_threshold_exceeded")
            if bgr is None or not frame_kept_by_pipeline_guard(
                bgr,
                filt=filt,
                task_guard=task_guard,
                trigger_reason=trigger,
                task_activity=task_activity,
            ):
                pilot_offenders.append(entry.get("pilot_frame_id", entry.get("frame_id")))
        result.add(
            "pilot_all_codap_guard",
            len(pilot_offenders) == 0,
            f"{len(pilot_offenders)} pilot offenders: {pilot_offenders[:5]}",
        )

    return result


def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="Expert MMLA extraction quality gate")
    p.add_argument("student_id", nargs="?", default="Amy")
    p.add_argument(
        "--audio-root",
        type=Path,
        default=REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio",
    )
    args = p.parse_args(argv)
    student_dir = args.audio_root.resolve() / args.student_id
    result = validate_student(student_dir, args.student_id)
    print(
        json.dumps(
            {
                "student_id": args.student_id,
                "passed": result.passed,
                "blockers": result.blockers,
                "checks": result.checks,
            },
            indent=2,
        )
    )
    return 0 if result.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
