#!/usr/bin/env python3
"""Unified MMLA master pipeline orchestrator.

Executes the full multimodal learning analytics workflow unattended:
  Stage 1 — Environmental sanitization & path discovery
  Stage 2 — Hybrid diarization (audio layer)
  Stage 3 — Dynamic video extraction with auto-resume recovery
  Stage 4 — Multimodal vision audit & metric alignment

Designed for Apple Silicon (M4) long-form CODAP/Colab screen recordings.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
DEFAULT_AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"
DEFAULT_VIDEO_ROOT = REPO_ROOT / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings"
PIPELINE_RUNS_DIR = REPO_ROOT / "logs" / "pipeline_runs"

RECOVERY_SLEEP_SECONDS = 5
DEFAULT_MAX_VIDEO_RETRIES = 100

LOGGER = logging.getLogger("run_mmla_pipeline")


@dataclass
class RuntimeEnvironment:
    repo_root: Path
    hybrid_python: Path
    vision_python: Path
    active_venv: str | None

    @property
    def video_python(self) -> Path:
        return self.hybrid_python


@dataclass
class StudentResult:
    student_id: str
    audio_status: str = "pending"
    video_status: str = "pending"
    vision_status: str = "pending"
    modality_status: str | None = None
    audio_seconds: float = 0.0
    video_attempts: int = 0
    errors: list[str] = field(default_factory=list)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def python_can_import(py: Path, module: str) -> bool:
    if not py.is_file():
        return False
    try:
        proc = subprocess.run(
            [str(py), "-c", f"import {module}"],
            capture_output=True,
            timeout=30,
        )
        return proc.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def resolve_runtime_environment() -> RuntimeEnvironment:
    """Pick stage-specific interpreters to avoid library cross-contamination."""
    hybrid_candidates = [
        REPO_ROOT / ".venv-hybrid" / "bin" / "python",
        Path(sys.executable),
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / "venv" / "bin" / "python",
    ]
    vision_candidates = [
        REPO_ROOT / ".venv" / "bin" / "python",
        Path(sys.executable),
        REPO_ROOT / ".venv-hybrid" / "bin" / "python",
        REPO_ROOT / "venv" / "bin" / "python",
    ]

    hybrid_python = next((p for p in hybrid_candidates if p.is_file()), Path(sys.executable))
    vision_python = next(
        (p for p in vision_candidates if python_can_import(p, "anthropic") or python_can_import(p, "openai")),
        hybrid_python,
    )
    if not python_can_import(vision_python, "anthropic") and not python_can_import(vision_python, "openai"):
        vision_python = hybrid_python

    active = os.environ.get("VIRTUAL_ENV")
    LOGGER.info(
        "Runtime: hybrid_python=%s vision_python=%s active_venv=%s",
        hybrid_python,
        vision_python,
        active or "(none)",
    )
    return RuntimeEnvironment(
        repo_root=REPO_ROOT,
        hybrid_python=hybrid_python.resolve(),
        vision_python=vision_python.resolve(),
        active_venv=active,
    )


def manifest_is_complete(manifest_path: Path) -> bool:
    if not manifest_path.is_file():
        return False
    try:
        payload = load_json(manifest_path)
    except json.JSONDecodeError:
        return False
    if payload.get("status") == "skipped":
        return False
    frames = payload.get("frames") or []
    if not frames:
        return False
    sample = frames[0]
    for key in ("frame_id", "source_timestamp_seconds", "extraction_trigger_reason", "file_path"):
        if key not in sample or sample[key] in (None, ""):
            return False
    return True


def vision_assessment_valid(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        doc = load_json(path)
    except json.JSONDecodeError:
        return False
    return bool(doc.get("calibrated_metrics"))


def hybrid_output_valid(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        doc = load_json(path)
    except json.JSONDecodeError:
        return False
    return "status" in doc and ("segments" in doc or doc.get("status") == "no_speech")


def discover_students(audio_root: Path, explicit: list[str] | None) -> list[str]:
    if explicit:
        return sorted(set(explicit), key=str.lower)
    students: list[str] = []
    for child in sorted(audio_root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir():
            continue
        sid = child.name
        if (child / f"{sid}.wav").is_file() or any(child.glob("*.wav")):
            students.append(sid)
    return students


def infer_cohort_id(audio_root: Path, override: str | None) -> str:
    if override:
        return override
    name = audio_root.name
    mapping = {
        "codap_arbor_21april_audio": "21 April CODAP",
        "colab_may_audio": "May Colab Python",
    }
    return mapping.get(name, name.replace("_", " ").title())


def is_no_speech_student(student_dir: Path, student_id: str) -> bool:
    for fname in (f"{student_id}_transcript.json", f"{student_id}_transcript_labeled.json"):
        path = student_dir / fname
        if path.is_file():
            try:
                if load_json(path).get("status") == "no_speech":
                    return True
            except json.JSONDecodeError:
                pass
    hybrid = student_dir / f"{student_id}_hybrid_diarization.json"
    if hybrid.is_file():
        try:
            if load_json(hybrid).get("status") == "no_speech":
                return True
        except json.JSONDecodeError:
            pass
    return False


def record_system_telemetry(log_path: Path, label: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"----- {stamp} [{label}] -----\n")
        for cmd in (["uptime"], ["vm_stat"]):
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                fh.write(proc.stdout or proc.stderr or "")
            except (subprocess.TimeoutExpired, OSError) as exc:
                fh.write(f"{cmd[0]} failed: {exc}\n")
        fh.write("\n")


def run_subprocess(
    cmd: list[str],
    *,
    log_path: Path,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env.setdefault("PYTHONUNBUFFERED", "1")

    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n>>> {' '.join(cmd)}\n")
        fh.flush()
        proc = subprocess.run(
            cmd,
            stdout=fh,
            stderr=subprocess.STDOUT,
            text=True,
            env=merged_env,
            timeout=timeout,
        )
        fh.write(f"<<< exit_code={proc.returncode}\n")
    return proc


def stage_audio(
    env: RuntimeEnvironment,
    student_dir: Path,
    student_id: str,
    audio_root: Path,
    *,
    skip_completed: bool,
    force_audio: bool,
    run_log: Path,
) -> tuple[str, float]:
    hybrid_path = student_dir / f"{student_id}_hybrid_diarization.json"
    t0 = time.monotonic()

    if skip_completed and not force_audio and hybrid_output_valid(hybrid_path):
        status = "no_speech" if is_no_speech_student(student_dir, student_id) else "skipped"
        LOGGER.info("[%s] Stage 2 audio: skip-completed (%s)", student_id, status)
        return status if status == "no_speech" else "skipped", time.monotonic() - t0

    if is_no_speech_student(student_dir, student_id) and hybrid_output_valid(hybrid_path) and not force_audio:
        LOGGER.info("[%s] Stage 2 audio: no_speech hybrid already present", student_id)
        return "no_speech", time.monotonic() - t0

    cmd = [
        str(env.hybrid_python),
        str(SCRIPTS_DIR / "hybrid_diarization.py"),
        student_id,
        "--audio-root",
        str(audio_root),
        "--fuse-existing-transcript",
        "--local-diarization-only",
        "--device",
        "cpu",
        "--compute-type",
        "int8",
        "-v",
    ]
    if skip_completed and not force_audio:
        cmd.append("--skip-existing")

    student_log = run_log.parent / f"{student_id}_stage2_audio.log"
    proc = run_subprocess(cmd, log_path=student_log)

    elapsed = time.monotonic() - t0
    if not hybrid_output_valid(hybrid_path):
        if proc.returncode != 0:
            return "failed", elapsed
        return "failed", elapsed

    if is_no_speech_student(student_dir, student_id):
        LOGGER.info("[%s] Stage 2 audio: no_speech template in %.2fs", student_id, elapsed)
        return "no_speech", elapsed

    LOGGER.info("[%s] Stage 2 audio: ok in %.1fs", student_id, elapsed)
    return "ok", elapsed


def stage_video_with_recovery(
    env: RuntimeEnvironment,
    student_dir: Path,
    student_id: str,
    audio_root: Path,
    video_root: Path,
    *,
    skip_completed: bool,
    max_retries: int,
    run_log: Path,
) -> tuple[str, int]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"

    if skip_completed and manifest_is_complete(manifest_path):
        modality = read_modality_status(manifest_path)
        LOGGER.info("[%s] Stage 3 video: skip-completed (%s)", student_id, modality)
        return "skipped", 0

    attempts = 0
    student_log = run_log.parent / f"{student_id}_stage3_video.log"

    while attempts < max_retries:
        attempts += 1
        cmd = [
            str(env.video_python),
            str(SCRIPTS_DIR / "dynamic_video_analytics.py"),
            student_id,
            "--audio-root",
            str(audio_root),
            "--video-root",
            str(video_root),
            "--compute-type",
            "int8",
            "--skip-existing",
            "-v",
        ]
        proc = run_subprocess(cmd, log_path=student_log)

        if manifest_is_complete(manifest_path):
            modality = read_modality_status(manifest_path)
            LOGGER.info(
                "[%s] Stage 3 video: complete after %d attempt(s) — %s",
                student_id,
                attempts,
                modality,
            )
            return modality, attempts

        exit_code = proc.returncode
        oom_like = exit_code in (-9, 137, 139, 11)
        LOGGER.warning(
            "[%s] Stage 3 video: attempt %d failed (exit=%s oom_like=%s) — recovery in %ds",
            student_id,
            attempts,
            exit_code,
            oom_like,
            RECOVERY_SLEEP_SECONDS,
        )
        record_system_telemetry(run_log.parent / "recovery_telemetry.log", f"{student_id}_video_attempt_{attempts}")
        time.sleep(RECOVERY_SLEEP_SECONDS)

    return "failed", attempts


def read_modality_status(manifest_path: Path) -> str:
    try:
        payload = load_json(manifest_path)
    except (json.JSONDecodeError, OSError):
        return "failed"
    mode = payload.get("extraction_mode", "")
    if mode == "full_multimodal":
        return "full_multimodal_sync"
    if mode == "motion_only_fallback":
        return "motion_only_fallback"
    return str(mode or "unknown")


def stage_vision(
    env: RuntimeEnvironment,
    student_dir: Path,
    student_id: str,
    audio_root: Path,
    *,
    provider: str,
    max_vision_events: int,
    skip_completed: bool,
    vision_dry_run: bool,
    run_log: Path,
) -> str:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    vision_path = student_dir / f"{student_id}_mmla_vision_assessment.json"

    if not manifest_is_complete(manifest_path):
        LOGGER.warning("[%s] Stage 4 vision: blocked — manifest incomplete", student_id)
        return "blocked"

    if skip_completed and vision_assessment_valid(vision_path):
        LOGGER.info("[%s] Stage 4 vision: skip-completed", student_id)
        return "skipped"

    cmd = [
        str(env.vision_python),
        str(SCRIPTS_DIR / "multimodal_vision_assessor.py"),
        "--audio-root",
        str(audio_root),
        "--student",
        student_id,
        "--provider",
        provider,
        "--max-events",
        str(max_vision_events),
    ]
    if vision_dry_run:
        cmd.append("--dry-run")
    if skip_completed:
        cmd.append("--skip-existing")

    student_log = run_log.parent / f"{student_id}_stage4_vision.log"
    proc = run_subprocess(cmd, log_path=student_log, timeout=3600)

    if vision_assessment_valid(vision_path):
        LOGGER.info("[%s] Stage 4 vision: ok", student_id)
        return "ok"
    if proc.returncode != 0:
        return "failed"
    return "failed"


def process_student(
    env: RuntimeEnvironment,
    student_id: str,
    audio_root: Path,
    video_root: Path,
    args: argparse.Namespace,
    run_log: Path,
) -> StudentResult:
    result = StudentResult(student_id=student_id)
    student_dir = audio_root / student_id

    if not student_dir.is_dir():
        result.audio_status = "failed"
        result.errors.append(f"student directory missing: {student_dir}")
        return result

    LOGGER.info("=" * 60)
    LOGGER.info("PIPELINE START: %s", student_id)
    LOGGER.info("=" * 60)

    try:
        if not args.skip_audio:
            audio_status, audio_secs = stage_audio(
                env,
                student_dir,
                student_id,
                audio_root,
                skip_completed=args.skip_completed,
                force_audio=args.force_audio,
                run_log=run_log,
            )
            result.audio_status = audio_status
            result.audio_seconds = round(audio_secs, 2)
        else:
            result.audio_status = "skipped"

        if not args.skip_video:
            video_status, attempts = stage_video_with_recovery(
                env,
                student_dir,
                student_id,
                audio_root,
                video_root,
                skip_completed=args.skip_completed,
                max_retries=args.max_video_retries,
                run_log=run_log,
            )
            result.video_attempts = attempts
            if video_status in ("full_multimodal_sync", "motion_only_fallback"):
                result.video_status = "ok"
                result.modality_status = video_status
            elif video_status == "skipped":
                result.video_status = "skipped"
                manifest = student_dir / f"{student_id}_video_extraction_manifest.json"
                if manifest.is_file():
                    result.modality_status = read_modality_status(manifest)
            else:
                result.video_status = video_status
        else:
            result.video_status = "skipped"

        if not args.skip_vision:
            vision_status = stage_vision(
                env,
                student_dir,
                student_id,
                audio_root,
                provider=args.provider,
                max_vision_events=args.max_vision_events,
                skip_completed=args.skip_completed,
                vision_dry_run=args.vision_dry_run,
                run_log=run_log,
            )
            result.vision_status = vision_status
            vision_path = student_dir / f"{student_id}_mmla_vision_assessment.json"
            if vision_path.is_file():
                try:
                    result.modality_status = load_json(vision_path).get("modality_status", result.modality_status)
                except json.JSONDecodeError:
                    pass
        else:
            result.vision_status = "skipped"

    except Exception as exc:
        LOGGER.error("[%s] pipeline exception: %s", student_id, exc)
        if args.verbose:
            LOGGER.debug(traceback.format_exc())
        result.errors.append(str(exc))
        if result.audio_status == "pending":
            result.audio_status = "failed"
        if result.video_status == "pending":
            result.video_status = "failed"
        if result.vision_status == "pending":
            result.vision_status = "failed"

    LOGGER.info(
        "PIPELINE END: %s audio=%s video=%s vision=%s modality=%s",
        student_id,
        result.audio_status,
        result.video_status,
        result.vision_status,
        result.modality_status,
    )
    return result


def compile_cohort_report(
    *,
    cohort_id: str,
    students: list[str],
    results: list[StudentResult],
    audio_root: Path,
    provider: str,
    timestamp: str,
) -> dict[str, Any]:
    multimodal = 0
    motion_only = 0
    failed = 0

    conceptual_vals: list[float] = []
    software_vals: list[float] = []
    argumentation_vals: list[float] = []
    kappa_vals: list[float] = []

    for res in results:
        if res.video_status == "failed" or res.vision_status == "failed":
            failed += 1
        modality = res.modality_status
        if modality == "full_multimodal_sync":
            multimodal += 1
        elif modality == "motion_only_fallback":
            motion_only += 1

    for student_id in students:
        vision_path = audio_root / student_id / f"{student_id}_mmla_vision_assessment.json"
        if not vision_assessment_valid(vision_path):
            continue
        doc = load_json(vision_path)
        metrics = doc.get("calibrated_metrics", {})
        if metrics.get("conceptual_score") is not None:
            conceptual_vals.append(float(metrics["conceptual_score"]))
        if metrics.get("software_interaction_score") is not None:
            software_vals.append(float(metrics["software_interaction_score"]))
        arg = metrics.get("argumentation_score")
        if arg is not None:
            argumentation_vals.append(float(arg))
        reliability = doc.get("empirical_reliability_index", {})
        kappa = reliability.get("cohen_kappa_vs_lexical_baseline")
        if kappa is not None:
            kappa_vals.append(float(kappa))

    def mean(vals: list[float]) -> float | None:
        return round(sum(vals) / len(vals), 2) if vals else None

    vision_engine = "Claude-3.5-Sonnet" if provider == "anthropic" else "GPT-4o"

    return {
        "pipeline_run_metadata": {
            "cohort_id": cohort_id,
            "timestamp": timestamp,
            "engine_configuration": {
                "audio": "local_mfcc_clustering",
                "vision": vision_engine,
            },
        },
        "execution_metrics": {
            "total_students_detected": len(students),
            "completed_multimodal_sync": multimodal,
            "completed_motion_only_fallback": motion_only,
            "failed_pipelines": failed,
            "per_student": [
                {
                    "student_id": r.student_id,
                    "audio_status": r.audio_status,
                    "video_status": r.video_status,
                    "vision_status": r.vision_status,
                    "modality_status": r.modality_status,
                    "video_attempts": r.video_attempts,
                    "errors": r.errors,
                }
                for r in results
            ],
        },
        "cohort_cognitive_averages": {
            "mean_conceptual_score": mean(conceptual_vals),
            "mean_software_interaction_score": mean(software_vals),
            "mean_argumentation_score": mean(argumentation_vals),
            "average_cohens_kappa_vs_lexical": mean(kappa_vals),
            "vision_assessments_count": len(conceptual_vals),
        },
    }


def print_cohort_dashboard(report: dict[str, Any]) -> None:
    meta = report["pipeline_run_metadata"]
    exec_m = report["execution_metrics"]
    cog = report["cohort_cognitive_averages"]

    def fmt(val: Any) -> str:
        if val is None:
            return "—"
        if isinstance(val, float):
            return f"{val:.2f}"
        return str(val)

    width = 72
    print()
    print("=" * width)
    print("  MMLA COHORT PIPELINE DASHBOARD".center(width))
    print("=" * width)
    print(f"  Cohort:     {meta['cohort_id']}")
    print(f"  Timestamp:  {meta['timestamp']}")
    print(f"  Audio:      {meta['engine_configuration']['audio']}")
    print(f"  Vision:     {meta['engine_configuration']['vision']}")
    print("-" * width)
    print("  EXECUTION METRICS")
    print(f"    Students detected:        {exec_m['total_students_detected']}")
    print(f"    Multimodal sync:          {exec_m['completed_multimodal_sync']}")
    print(f"    Motion-only fallback:     {exec_m['completed_motion_only_fallback']}")
    print(f"    Failed pipelines:         {exec_m['failed_pipelines']}")
    print("-" * width)
    print("  COHORT COGNITIVE AVERAGES (vision-assessed)")
    print(f"    Mean conceptual:          {fmt(cog['mean_conceptual_score'])}")
    print(f"    Mean software interaction: {fmt(cog['mean_software_interaction_score'])}")
    print(f"    Mean argumentation:       {fmt(cog['mean_argumentation_score'])}")
    print(f"    Avg Cohen's κ vs lexical: {fmt(cog['average_cohens_kappa_vs_lexical'])}")
    print(f"    Vision assessments:       {cog.get('vision_assessments_count', 0)}")
    print("-" * width)
    print("  PER-STUDENT STATUS")
    for row in exec_m.get("per_student", []):
        err = f" ERR={row['errors'][0]}" if row.get("errors") else ""
        print(
            f"    {row['student_id']:<10} "
            f"audio={row['audio_status']:<8} "
            f"video={row['video_status']:<8} "
            f"vision={row['vision_status']:<8} "
            f"modality={row.get('modality_status') or '—'}{err}"
        )
    print("=" * width)
    print()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Master MMLA pipeline orchestrator (audio → video → vision)",
    )
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT)
    p.add_argument("--student", action="append", dest="students", help="Student pseudonym (repeatable)")
    p.add_argument("--cohort-id", help="Human-readable cohort label for telemetry report")
    p.add_argument("--provider", choices=("anthropic", "openai"), default="anthropic")
    p.add_argument("--max-vision-events", type=int, default=12)
    p.add_argument("--max-video-retries", type=int, default=DEFAULT_MAX_VIDEO_RETRIES)
    p.add_argument("--skip-completed", action="store_true", help="Skip stages with valid artifacts")
    p.add_argument("--force-audio", action="store_true", help="Re-run hybrid diarization even if output exists")
    p.add_argument("--skip-audio", action="store_true")
    p.add_argument("--skip-video", action="store_true")
    p.add_argument("--skip-vision", action="store_true")
    p.add_argument("--vision-dry-run", action="store_true", help="Vision stage without cloud API calls")
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    timestamp = utc_now_iso()
    PIPELINE_RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_slug = timestamp.replace(":", "").replace("-", "")
    run_log = PIPELINE_RUNS_DIR / f"run_{run_slug}.log"

    audio_root = args.audio_root.resolve()
    video_root = args.video_root.resolve()
    cohort_id = infer_cohort_id(audio_root, args.cohort_id)

    if not audio_root.is_dir():
        LOGGER.error("audio-root does not exist: %s", audio_root)
        return 1

    env = resolve_runtime_environment()
    students = discover_students(audio_root, args.students)
    if not students:
        LOGGER.error("No students discovered under %s", audio_root)
        return 1

    LOGGER.info("Cohort=%s students=%d audio_root=%s video_root=%s", cohort_id, len(students), audio_root, video_root)
    LOGGER.info("Master run log: %s", run_log)

    with run_log.open("w", encoding="utf-8") as fh:
        fh.write(
            json.dumps(
                {
                    "started_at": timestamp,
                    "cohort_id": cohort_id,
                    "students": students,
                    "hybrid_python": str(env.hybrid_python),
                    "vision_python": str(env.vision_python),
                    "args": vars(args),
                },
                indent=2,
                default=str,
            )
            + "\n"
        )

    results: list[StudentResult] = []
    for student_id in students:
        results.append(
            process_student(env, student_id, audio_root, video_root, args, run_log)
        )

    report = compile_cohort_report(
        cohort_id=cohort_id,
        students=students,
        results=results,
        audio_root=audio_root,
        provider=args.provider,
        timestamp=timestamp,
    )

    report_path = PIPELINE_RUNS_DIR / f"global_cohort_report_{run_slug}.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    LOGGER.info("Global cohort report: %s", report_path)

    print_cohort_dashboard(report)

    failed = report["execution_metrics"]["failed_pipelines"]
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
