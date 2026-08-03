#!/usr/bin/env python3
"""Batch strict MMLA video extraction for 21 April, 28 April, and 5 May cohorts."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"
PYTHON = REPO_ROOT / ".venv-hybrid" / "bin" / "python"

COHORTS: list[tuple[str, Path, Path]] = [
    (
        "21april",
        REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio",
        REPO_ROOT / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings",
    ),
    (
        "28april",
        REPO_ROOT / "data_sources_2026" / "codap_arbor_28april_audio",
        REPO_ROOT / "data_sources_2026" / "28 April CODAP Arbor Screen Recordings",
    ),
    (
        "05may",
        REPO_ROOT / "data_sources_2026" / "colab_python_audio",
        REPO_ROOT / "data_sources_2026" / "05 May Colab Python Screen Recordings",
    ),
]

COHORT_TASK_ACTIVITY = {
    "21april": "codap",
    "28april": "codap",
    "05may": "colab",
}

STRICT_VIDEO_ARGS = [
    "--enable-dedup",
    "True",
    "--dedup-method",
    "phash",
    "--phash-threshold",
    "4",
    "--filter-non-task-screens",
    "True",
    "--enable-codap-task-guard",
    "True",
    "--require-codap-content",
    "True",
    "--codap-task-phash-threshold",
    "12",
    "--cooldown-ms",
    "1000",
    "--speech-gap-bypass-seconds",
    "120",
    "--non-task-phash-threshold",
    "10",
    "--motion-threshold",
    "0.012",
    "--single-pass",
    "True",
    "--motion-preview-width",
    "960",
    "--silent-motion-threshold",
    "0.008",
    "--silent-screen-gap-fill-seconds",
    "90",
    "--codap-gap-fill-seconds",
    "90",
    "--compute-type",
    "int8",
    "-v",
]

sys.path.insert(0, str(SCRIPTS))
from dynamic_video_analytics import is_silent_screen_recording  # noqa: E402

LOGGER = logging.getLogger("batch_extract_strict")


def video_args_for_cohort(cohort_key: str) -> list[str]:
    return [
        *STRICT_VIDEO_ARGS,
        "--task-activity",
        COHORT_TASK_ACTIVITY.get(cohort_key, "codap"),
    ]


def strict_params_ok(manifest: dict, cohort_key: str | None = None) -> bool:
    params = manifest.get("parameters") or {}
    expected_activity = COHORT_TASK_ACTIVITY.get(cohort_key or "", "codap")
    return (
        params.get("codap_task_phash_threshold") == 12
        and params.get("cooldown_ms") == 1000
        and params.get("speech_gap_bypass_seconds") == 120
        and params.get("require_codap_content") is True
        and params.get("enable_codap_task_guard") is True
        and params.get("single_pass") is True
        and params.get("motion_preview_width") == 960
        and params.get("codap_gap_fill_seconds") == 90
        and params.get("silent_motion_threshold") == 0.008
        and params.get("silent_screen_gap_fill_seconds") == 90
        and params.get("task_activity") == expected_activity
    )


def quality_gate_passes(student_dir: Path, student_id: str, audio_root: Path) -> bool:
    proc = subprocess.run(
        [
            str(PYTHON),
            str(SCRIPTS / "extraction_quality_gate.py"),
            student_id,
            "--audio-root",
            str(audio_root),
        ],
        capture_output=True,
        text=True,
    )
    return proc.returncode == 0


def manifest_has_gap_fill(manifest: dict) -> bool:
    frames = manifest.get("frames") or []
    return any(
        f.get("extraction_trigger_reason") in ("silent_screen_gap_fill", "codap_static_gap_fill")
        for f in frames
    )


def discover_students(audio_root: Path) -> list[str]:
    out: list[str] = []
    for child in sorted(audio_root.iterdir(), key=lambda p: p.name.lower()):
        if child.is_dir() and any(child.glob("*.wav")):
            out.append(child.name)
    return out


def cohort_key_for_audio_root(audio_root: Path) -> str | None:
    for key, root, _ in COHORTS:
        if root == audio_root:
            return key
    return None


def needs_extraction(student_dir: Path, student_id: str, audio_root: Path) -> bool:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        return True
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return True
    frames = manifest.get("frames") or []
    if len(frames) < 30:
        return True
    cohort_key = cohort_key_for_audio_root(audio_root)
    if not strict_params_ok(manifest, cohort_key):
        return True
    if quality_gate_passes(student_dir, student_id, audio_root):
        if student_id == "Amy":
            return False
        if manifest_has_gap_fill(manifest):
            return False
    if is_silent_screen_recording(student_dir, student_id):
        if manifest.get("extraction_mode") == "motion_only_fallback" and not manifest_has_gap_fill(manifest):
            return True
    elif not manifest_has_gap_fill(manifest):
        return True
    if not quality_gate_passes(student_dir, student_id, audio_root):
        return True
    return False


def backup_artifacts(student_dir: Path, student_id: str) -> None:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    for suffix in ("_frames", "_frames_pilot", "_video_extraction_manifest.json", "_video_extraction_manifest_frames_pilot.json"):
        src = student_dir / f"{student_id}{suffix}"
        if src.exists():
            dst = student_dir / f"{student_id}{suffix}_prebatch_{stamp}"
            if src.is_dir():
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)


def run_cmd(cmd: list[str], log_path: Path) -> int:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n>>> {' '.join(cmd)}\n")
        fh.flush()
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True)
        fh.write(f"<<< exit_code={proc.returncode}\n")
    return proc.returncode


def post_process(student_id: str, audio_root: Path, log_path: Path) -> dict:
    steps = [
        [str(PYTHON), str(SCRIPTS / "prune_to_guard.py"), student_id, "--audio-root", str(audio_root)],
        [str(PYTHON), str(SCRIPTS / "post_hoc_refiner.py"), student_id, "--audio-root", str(audio_root)],
        [str(PYTHON), str(SCRIPTS / "extraction_quality_gate.py"), student_id, "--audio-root", str(audio_root)],
    ]
    results: dict[str, object] = {}
    for cmd in steps:
        rc = run_cmd(cmd, log_path)
        results[cmd[1].split("/")[-1]] = rc
        if rc != 0 and "extraction_quality_gate" in cmd[1]:
            results["gate_failed"] = True
    return results


def process_student(
    cohort_key: str,
    student_id: str,
    audio_root: Path,
    video_root: Path,
    *,
    dry_run: bool,
) -> dict:
    student_dir = audio_root / student_id
    log_path = LOG_DIR / f"batch_strict_{cohort_key}_{student_id}.log"

    if cohort_key == "21april" and student_id == "Amy":
        gate = subprocess.run(
            [str(PYTHON), str(SCRIPTS / "extraction_quality_gate.py"), "Amy", "--audio-root", str(audio_root)],
            capture_output=True,
            text=True,
        )
        if gate.returncode == 0:
            LOGGER.info("%s/%s: skip — strict Amy gate already passed", cohort_key, student_id)
            return {"student_id": student_id, "status": "skipped", "reason": "amy_gate_passed"}

    if not needs_extraction(student_dir, student_id, audio_root):
        LOGGER.info("%s/%s: skip — strict complete manifest", cohort_key, student_id)
        post = post_process(student_id, audio_root, log_path)
        return {"student_id": student_id, "status": "skipped", "reason": "strict_complete", "post": post}

    if dry_run:
        return {"student_id": student_id, "status": "dry_run", "would_extract": True}

    backup_artifacts(student_dir, student_id)
    frames_dir = student_dir / f"{student_id}_frames"
    if frames_dir.is_dir():
        shutil.rmtree(frames_dir)

    # Colab sessions use a dedicated event engine tuned to notebook geometry.
    # All other cohorts use the general dynamic_video_analytics extractor.
    extractor_script = (
        SCRIPTS / "colab_event_analytics.py"
        if cohort_key == "05may"
        else SCRIPTS / "dynamic_video_analytics.py"
    )
    cmd = [
        "caffeinate",
        "-i",
        str(PYTHON),
        "-u",
        str(extractor_script),
        student_id,
        "--audio-root",
        str(audio_root),
        "--video-root",
        str(video_root),
        *video_args_for_cohort(cohort_key),
    ]
    rc = run_cmd(cmd, log_path)
    post = post_process(student_id, audio_root, log_path)
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    frame_count = 0
    if manifest_path.is_file():
        try:
            frame_count = len(json.loads(manifest_path.read_text()).get("frames", []))
        except json.JSONDecodeError:
            pass
    gate_failed = bool(post.get("gate_failed"))
    status = "ok" if rc == 0 and frame_count > 0 and not gate_failed else "failed"
    return {
        "student_id": student_id,
        "status": status,
        "exit_code": rc,
        "frames": frame_count,
        "log": str(log_path.relative_to(REPO_ROOT)),
        "post": post,
        "gate_passed": not gate_failed,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Strict cohort video extraction batch")
    p.add_argument("--cohort", choices=[c[0] for c in COHORTS] + ["all"], default="all")
    p.add_argument("--student", action="append", dest="students")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-skip-strict-complete", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(message)s")

    selected = [c for c in COHORTS if args.cohort in ("all", c[0])]
    summary: list[dict] = []

    for cohort_key, audio_root, video_root in selected:
        students = args.students or discover_students(audio_root)
        LOGGER.info("Cohort %s: %d students", cohort_key, len(students))
        for student_id in students:
            result = process_student(
                cohort_key,
                student_id,
                audio_root,
                video_root,
                dry_run=args.dry_run,
            )
            result["cohort"] = cohort_key
            summary.append(result)
            LOGGER.info("Result: %s", json.dumps(result, ensure_ascii=False))

    report_path = LOG_DIR / f"batch_strict_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(report_path.relative_to(REPO_ROOT)), "results": summary}, indent=2))
    failed = [r for r in summary if r.get("status") == "failed" or not r.get("gate_passed", True)]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
