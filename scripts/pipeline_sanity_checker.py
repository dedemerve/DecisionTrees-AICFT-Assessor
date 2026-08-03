#!/usr/bin/env python3
"""
pipeline_sanity_checker.py

Non-destructive pre-flight validation and stress-test for the MMLA pipeline.
Runs three diagnostic tracks and emits a production-readiness matrix to stdout.

Usage:
    python scripts/pipeline_sanity_checker.py [--audio-root PATH] [--video-root PATH]
                                               [--csv PATH] [--student STUDENT_ID]
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import traceback
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

# ── Paths ──────────────────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[1]

DEFAULT_AUDIO_ROOT = REPO / "data_sources_2026" / "codap_arbor_21april_audio"
DEFAULT_VIDEO_ROOT = REPO / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings"
DEFAULT_CSV_PATH   = (
    REPO
    / "data_sources_2026"
    / "All Documents"
    / "21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
)
DEFAULT_STUDENT    = "Amy"
SESSION_DATE       = "2026-04-21"

LOG_DIR  = REPO / "logs" / "pipeline_runs"
VENV     = REPO / ".venv" / "bin" / "python"
VENV_HYB = REPO / ".venv-hybrid" / "bin" / "python"

# ── Result container ───────────────────────────────────────────────────────────
@dataclass
class TestResult:
    name: str
    passed: bool = True
    details: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.passed = False
        self.details.append(f"FAIL: {msg}")

    def info(self, msg: str) -> None:
        self.details.append(f"  {msg}")

    def warn(self, msg: str) -> None:
        self.warnings.append(f"WARN: {msg}")


# ==============================================================================
# DIAGNOSTIC 1 — Schema & Dry-Run Integrity
# ==============================================================================

VISION_ASSESSMENT_SCHEMA: dict[str, Any] = {
    "student_id": str,
    "modality_status": str,
    "scoring_engine": str,
    "assessed_at": str,
    "calibrated_metrics": {
        "conceptual_score": float,
        "software_interaction_score": float,
        "argumentation_score": float,
        "final_weighted_index": float,
    },
    "weighting_matrix": {
        "conceptual": float,
        "software": float,
        "argumentation": float,
    },
    "verified_interaction_moments": list,
    "empirical_reliability_index": dict,
    "quantitative_summary": str,
}

MOMENT_SCHEMA: dict[str, Any] = {
    "timestamp_seconds": float,
    "frame_reference": str,
    "trigger": str,
    "transcript_text": str,
    "vision_verification": {
        "visual_evidence_found": bool,
        "screen_state_analysis": str,
        "cognitive_validity": str,
    },
}


def _build_dummy_assessment(student_id: str) -> dict:
    """Build a structurally complete dummy assessment mirroring the live contract."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "student_id": student_id,
        "modality_status": "full_multimodal_sync",
        "scoring_engine": "SANITY-CHECK-DRY-RUN-v1",
        "assessed_at": now,
        "calibrated_metrics": {
            "conceptual_score": 2.5,
            "software_interaction_score": 3.0,
            "argumentation_score": 1.5,
            "final_weighted_index": 2.42,
        },
        "weighting_matrix": {
            "conceptual": 0.45,
            "software": 0.35,
            "argumentation": 0.20,
        },
        "verified_interaction_moments": [
            {
                "timestamp_seconds": 120.0,
                "frame_reference": "frame_0001.jpg",
                "trigger": "student_speech_concept",
                "transcript_text": "Dry-run placeholder transcript.",
                "vision_verification": {
                    "visual_evidence_found": True,
                    "screen_state_analysis": "DRY-RUN: mock screen state analysis.",
                    "cognitive_validity": "DRY-RUN: mock cognitive validity statement.",
                },
            }
        ],
        "empirical_reliability_index": {
            "rule_lexical_baseline_available": False,
            "validation_gold_available": False,
            "cohen_kappa_vs_lexical_baseline": None,
            "cohen_kappa_vs_validation_gold": None,
            "per_dimension_kappa_vs_lexical": None,
            "vision_event_coverage": 1.0,
            "mean_visual_evidence_rate": 1.0,
            "events_vision_audited": 1,
        },
        "quantitative_summary": (
            "DRY-RUN: sanity checker mock assessment for 1 event."
        ),
    }


def _validate_schema(obj: Any, schema: Any, path: str = "root") -> list[str]:
    """Recursively check that obj satisfies schema. Returns list of violations."""
    errors: list[str] = []
    if isinstance(schema, dict):
        if not isinstance(obj, dict):
            errors.append(f"{path}: expected dict, got {type(obj).__name__}")
            return errors
        for key, val_schema in schema.items():
            if key not in obj:
                errors.append(f"{path}.{key}: missing key")
                continue
            errors.extend(_validate_schema(obj[key], val_schema, f"{path}.{key}"))
    elif isinstance(schema, type):
        if schema is float:
            if not isinstance(obj, (int, float)) or isinstance(obj, bool):
                errors.append(f"{path}: expected numeric, got {type(obj).__name__}")
        elif not isinstance(obj, schema):
            errors.append(f"{path}: expected {schema.__name__}, got {type(obj).__name__}")
    return errors


def run_diagnostic_1(
    student_id: str,
    audio_root: Path,
    result: TestResult,
) -> None:
    result.info(f"Student: {student_id}")

    # 1a. Load existing assessment from disk and validate its schema.
    assessment_path = audio_root / student_id / f"{student_id}_mmla_vision_assessment.json"
    if assessment_path.is_file():
        try:
            on_disk = json.loads(assessment_path.read_text(encoding="utf-8"))
            errs = _validate_schema(on_disk, VISION_ASSESSMENT_SCHEMA)
            if errs:
                for e in errs:
                    result.warn(f"Existing assessment schema: {e}")
                result.info(f"Existing assessment at {assessment_path.name}: schema has {len(errs)} warning(s)")
            else:
                result.info(f"Existing assessment at {assessment_path.name}: schema OK")
            # Validate each moment's structure
            moments: list[dict] = on_disk.get("verified_interaction_moments", [])
            moment_errs: list[str] = []
            for i, m in enumerate(moments[:5]):
                moment_errs.extend(_validate_schema(m, MOMENT_SCHEMA, f"moment[{i}]"))
            if moment_errs:
                for e in moment_errs:
                    result.warn(f"Moment schema: {e}")
            else:
                result.info(f"Verified {len(moments)} moment(s) — schema OK")
        except (json.JSONDecodeError, OSError) as exc:
            result.fail(f"Cannot read existing assessment: {exc}")
            return
    else:
        result.info("No existing assessment on disk — generating dry-run payload only")

    # 1b. Build dummy payload and write to a temp file to test JSON round-trip.
    dummy = _build_dummy_assessment(student_id)
    dummy_errs = _validate_schema(dummy, VISION_ASSESSMENT_SCHEMA)
    if dummy_errs:
        result.fail(f"Dummy payload violates schema: {dummy_errs}")
        return
    result.info("Dummy payload passes internal schema check")

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix="_dry_run_assessment.json",
        dir=LOG_DIR,
        delete=False,
        encoding="utf-8",
    ) as tmp:
        json.dump(dummy, tmp, ensure_ascii=False, indent=2)
        tmp_path = Path(tmp.name)

    # 1c. Read back and parse — verify JSON is not corrupted on write.
    try:
        readback = json.loads(tmp_path.read_text(encoding="utf-8"))
        rt_errs = _validate_schema(readback, VISION_ASSESSMENT_SCHEMA)
        if rt_errs:
            result.fail(f"Read-back schema violations after JSON round-trip: {rt_errs}")
        else:
            result.info(f"JSON round-trip to {tmp_path.name}: OK")
        file_size_kb = tmp_path.stat().st_size / 1024
        result.info(f"Temp file size: {file_size_kb:.1f} KB")
    except (json.JSONDecodeError, OSError) as exc:
        result.fail(f"JSON round-trip read-back failed: {exc}")
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass

    # 1d. Manifest integrity cross-check.
    manifest_path = audio_root / student_id / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        result.fail(f"Manifest not found: {manifest_path.name}")
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        frame_count = len(manifest.get("frames", []))
        task_activity = manifest.get("parameters", {}).get("task_activity", "unknown")
        result.info(f"Manifest: {frame_count} frames, task_activity={task_activity}")
        if frame_count == 0:
            result.fail("Manifest has zero frames — pipeline cannot proceed")
    except (json.JSONDecodeError, OSError) as exc:
        result.fail(f"Manifest unreadable: {exc}")


# ==============================================================================
# DIAGNOSTIC 2 — Cross-Venv Runtime Isolation
# ==============================================================================

def _probe_venv(python_bin: Path, label: str, result: TestResult) -> dict | None:
    """
    Subprocess probe: collect sys.version, sys.executable, and installed packages.
    Returns a dict with the probe data, or None on failure.
    """
    probe_code = textwrap.dedent("""\
        import sys, json, subprocess, os
        pkgs_raw = subprocess.check_output(
            [sys.executable, "-m", "pip", "list", "--format=json"],
            stderr=subprocess.DEVNULL,
        ).decode()
        pkgs = {p["name"].lower(): p["version"] for p in json.loads(pkgs_raw)}
        # cv2 ships under several pip names; resolve whichever is present
        cv2_ver = (
            pkgs.get("opencv-python")
            or pkgs.get("opencv-python-headless")
            or pkgs.get("opencv-contrib-python")
            or "MISSING"
        )
        print(json.dumps({
            "executable": sys.executable,
            "version": sys.version.split()[0],
            "key_packages": {
                k: pkgs.get(k, "MISSING")
                for k in ("anthropic", "openai", "torch", "transformers", "numpy", "scipy")
            },
            "cv2": cv2_ver,
            "total_packages": len(pkgs),
        }))
    """)
    try:
        out = subprocess.check_output(
            [str(python_bin), "-c", probe_code],
            stderr=subprocess.PIPE,
            timeout=60,
        )
        probe = json.loads(out.decode().strip())
        result.info(
            f"{label}: Python {probe['version']}, "
            f"{probe['total_packages']} packages installed"
        )
        for pkg, ver in probe["key_packages"].items():
            result.info(f"  {label} [{pkg}]: {ver}")
        result.info(f"  {label} [cv2]: {probe.get('cv2', 'MISSING')}")
        if probe["executable"] != str(python_bin):
            result.warn(
                f"{label}: sys.executable mismatch "
                f"(expected {python_bin}, got {probe['executable']})"
            )
        return probe
    except subprocess.TimeoutExpired:
        result.fail(f"{label}: probe timed out after 60s")
    except subprocess.CalledProcessError as exc:
        result.fail(
            f"{label}: probe subprocess exited {exc.returncode}: "
            f"{exc.stderr.decode(errors='replace')[:200]}"
        )
    except (json.JSONDecodeError, OSError) as exc:
        result.fail(f"{label}: probe output parse error: {exc}")
    return None


def run_diagnostic_2(result: TestResult) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    venv_log = LOG_DIR / "venv_sanity.log"

    probes: dict[str, dict | None] = {}

    for bin_path, label in [(VENV, ".venv"), (VENV_HYB, ".venv-hybrid")]:
        if not bin_path.is_file():
            result.fail(f"{label}: interpreter not found at {bin_path}")
            probes[label] = None
            continue
        probes[label] = _probe_venv(bin_path, label, result)

    # Cross-contamination check: the two executables must differ.
    p1, p2 = probes.get(".venv"), probes.get(".venv-hybrid")
    if p1 and p2:
        if p1["executable"] == p2["executable"]:
            result.fail(
                "Isolation breach: both venvs resolve to the same interpreter "
                f"({p1['executable']})"
            )
        else:
            result.info("sys.executable differs between venvs — isolation confirmed")

        # anthropic must be present in .venv-hybrid (vision pipeline requirement).
        hyb_anthropic = p2["key_packages"].get("anthropic", "MISSING")
        if hyb_anthropic == "MISSING":
            result.fail(
                ".venv-hybrid: 'anthropic' package missing — "
                "vision pipeline will fail at import time"
            )
        else:
            result.info(f".venv-hybrid: anthropic=={hyb_anthropic} — vision pipeline dependency OK")

        # cv2 must be resolvable in both venvs (pip name varies).
        cv_main = p1.get("cv2", "MISSING")
        cv_hyb  = p2.get("cv2", "MISSING")
        if cv_main == "MISSING" or cv_hyb == "MISSING":
            result.fail(
                f"cv2 not found in one or both venvs "
                f"(.venv={cv_main}, .venv-hybrid={cv_hyb}). "
                "Install: pip install opencv-python-headless"
            )
        else:
            result.info(f"cv2: .venv={cv_main}, .venv-hybrid={cv_hyb} — both OK")

    # Write structured log.
    log_payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "venv":        {"path": str(VENV),     "probe": p1},
        "venv_hybrid": {"path": str(VENV_HYB), "probe": p2},
        "isolation_confirmed": (
            p1 is not None
            and p2 is not None
            and p1["executable"] != p2["executable"]
        ),
    }
    try:
        venv_log.write_text(
            json.dumps(log_payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        result.info(f"Probe log written to {venv_log.relative_to(REPO)}")
    except OSError as exc:
        result.warn(f"Could not write venv_sanity.log: {exc}")


# ==============================================================================
# DIAGNOSTIC 3 — Log-to-FFmpeg Frame Extraction
# ==============================================================================

def _parse_first_n_timestamps(
    csv_path: Path,
    student_id: str,
    date_prefix: str,
    n: int = 2,
) -> list[float]:
    """Return up to n non-zero timestamp_ms values (as seconds) for the student."""
    timestamps: list[float] = []
    with csv_path.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            if not row.get("created_at", "").startswith(date_prefix):
                continue
            if row.get("student_id") != student_id:
                continue
            ms = int(row.get("timestamp_ms", 0) or 0)
            if ms > 0:
                timestamps.append(ms / 1000.0)
            if len(timestamps) >= n:
                break
    return timestamps


def _extract_frame_ffmpeg(
    video_path: Path,
    timestamp_s: float,
    output_path: Path,
) -> tuple[bool, str]:
    """
    Extract a single frame at timestamp_s from video_path via ffmpeg.
    Returns (success, message).
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-ss", f"{timestamp_s:.3f}",
        "-i", str(video_path),
        "-frames:v", "1",
        "-q:v", "2",
        str(output_path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return False, proc.stderr.decode(errors="replace").strip()[:300]
        return True, "ffmpeg OK"
    except FileNotFoundError:
        return False, "ffmpeg binary not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "ffmpeg timed out after 30s"


def _extract_frame_cv2(
    video_path: Path,
    timestamp_s: float,
    output_path: Path,
) -> tuple[bool, str]:
    """
    Fallback: extract a single frame via OpenCV at timestamp_s.
    Cap is released in a try-finally block regardless of outcome.
    """
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            return False, f"cv2.VideoCapture could not open {video_path.name}"
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 10000:
            # WebM with invalid FPS metadata — use set(CAP_PROP_POS_MSEC) directly
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0)
        else:
            frame_idx = int(timestamp_s * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret or frame is None:
            # Try seeking 10% into the video as a fallback position
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_s * 1000.0 + 1000)
            ret, frame = cap.read()
        if not ret or frame is None:
            return False, "cap.read() returned no frame at requested timestamp"
        success = cv2.imwrite(str(output_path), frame)
        if not success:
            return False, f"cv2.imwrite failed to write {output_path.name}"
        return True, "cv2 extraction OK"
    finally:
        cap.release()


def run_diagnostic_3(
    student_id: str,
    audio_root: Path,
    video_root: Path,
    csv_path: Path,
    result: TestResult,
) -> None:
    result.info(f"Student: {student_id}, session date: {SESSION_DATE}")

    # 3a. Parse timestamps from CSV.
    if not csv_path.is_file():
        result.fail(f"CSV not found: {csv_path}")
        return
    try:
        timestamps = _parse_first_n_timestamps(csv_path, student_id, SESSION_DATE, n=2)
    except Exception as exc:
        result.fail(f"CSV parse error: {exc}")
        return

    if not timestamps:
        result.fail(
            f"No non-zero timestamps found for {student_id} on {SESSION_DATE} in CSV"
        )
        return
    result.info(f"CSV timestamps (first {len(timestamps)}): {[f'{t:.3f}s' for t in timestamps]}")

    # 3b. Locate video file.
    video_path = video_root / f"{student_id}.webm"
    if not video_path.is_file():
        result.fail(f"Video not found: {video_path}")
        return
    video_size_mb = video_path.stat().st_size / (1024 * 1024)
    result.info(f"Video: {video_path.name} ({video_size_mb:.1f} MB)")

    # 3c. Extract frames, preferring ffmpeg with cv2 fallback.
    frames_ok = 0
    for i, ts in enumerate(timestamps):
        with tempfile.NamedTemporaryFile(
            suffix=f"_sanity_frame_{i}.jpg",
            dir=LOG_DIR,
            delete=False,
        ) as tmp:
            out_path = Path(tmp.name)

        extracted = False
        method_used = "none"
        try:
            ok, msg = _extract_frame_ffmpeg(video_path, ts, out_path)
            if ok:
                extracted = True
                method_used = "ffmpeg"
            else:
                result.warn(f"ffmpeg failed at t={ts:.3f}s ({msg}) — falling back to cv2")
                ok2, msg2 = _extract_frame_cv2(video_path, ts, out_path)
                if ok2:
                    extracted = True
                    method_used = "cv2"
                else:
                    result.fail(f"Frame extraction failed at t={ts:.3f}s: ffmpeg={msg} | cv2={msg2}")

            if extracted and out_path.is_file():
                file_size = out_path.stat().st_size
                if file_size == 0:
                    result.fail(f"Extracted frame at t={ts:.3f}s is 0 bytes (empty file)")
                    extracted = False
                else:
                    # 3d. Verify cv2.imread can decode the written image.
                    img = cv2.imread(str(out_path))
                    if img is None:
                        result.fail(
                            f"cv2.imread returned None for frame at t={ts:.3f}s "
                            f"({file_size} bytes — possibly truncated or corrupt)"
                        )
                        extracted = False
                    else:
                        h, w, c = img.shape
                        result.info(
                            f"t={ts:.3f}s: {w}x{h}px, {c}ch, "
                            f"{file_size/1024:.1f} KB [{method_used}] — OK"
                        )
                        frames_ok += 1
            elif extracted:
                result.fail(f"Frame output path missing after extraction at t={ts:.3f}s")

        finally:
            try:
                out_path.unlink(missing_ok=True)
            except OSError:
                pass

    if frames_ok == 0:
        result.fail("No frames were successfully extracted and verified")
    elif frames_ok < len(timestamps):
        result.warn(
            f"Only {frames_ok}/{len(timestamps)} frames passed verification "
            "(check video integrity)"
        )
    else:
        result.info(f"All {frames_ok}/{len(timestamps)} frames extracted and verified")

    # 3e. Sanity-check that extract_emit_frames.py is importable.
    emit_script = REPO / "scripts" / "extract_emit_frames.py"
    if not emit_script.is_file():
        result.fail(f"extract_emit_frames.py not found at {emit_script}")
    else:
        result.info(f"extract_emit_frames.py present ({emit_script.stat().st_size} bytes)")


# ==============================================================================
# Report printer
# ==============================================================================

def _status(ok: bool) -> str:
    return "PASS" if ok else "FAIL"


def print_report(tests: list[TestResult]) -> int:
    width = 72
    sep   = "=" * width
    dash  = "-" * width

    print()
    print(sep)
    print(f"{'MMLA PIPELINE SANITY REPORT':^{width}}")
    print(sep)
    for i, t in enumerate(tests, 1):
        label   = f" [TEST {i}] {t.name}:"
        verdict = f"[{_status(t.passed)}]"
        print(f"{label:<50} {verdict}")
        for line in t.details:
            print(f"   {line}")
        for line in t.warnings:
            print(f"   {line}")
    print(dash)
    all_passed = all(t.passed for t in tests)
    status_msg = "READY FOR PRODUCTION LAUNCH" if all_passed else "BLOCKING ERRORS FOUND"
    print(f" SYSTEM STATUS: [{status_msg}]")
    print(sep)
    print()
    return 0 if all_passed else 1


# ==============================================================================
# Entry point
# ==============================================================================

def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="MMLA pipeline sanity checker")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_ROOT)
    p.add_argument("--csv",        type=Path, default=DEFAULT_CSV_PATH)
    p.add_argument("--student",    default=DEFAULT_STUDENT)
    args = p.parse_args(argv)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    audio_root: Path = args.audio_root.resolve()
    video_root: Path = args.video_root.resolve()
    csv_path:   Path = args.csv.resolve()
    student:    str  = args.student

    tests: list[TestResult] = []

    # ── TEST 1 ─────────────────────────────────────────────────────────────────
    t1 = TestResult("Schema & Dry-Run Integrity")
    try:
        run_diagnostic_1(student, audio_root, t1)
    except Exception:
        t1.fail(f"Unhandled exception:\n{traceback.format_exc()}")
    tests.append(t1)

    # ── TEST 2 ─────────────────────────────────────────────────────────────────
    t2 = TestResult("Multi-Venv Runtime Isolation")
    try:
        run_diagnostic_2(t2)
    except Exception:
        t2.fail(f"Unhandled exception:\n{traceback.format_exc()}")
    tests.append(t2)

    # ── TEST 3 ─────────────────────────────────────────────────────────────────
    t3 = TestResult("Log-to-FFmpeg Frame Extraction")
    try:
        run_diagnostic_3(student, audio_root, video_root, csv_path, t3)
    except Exception:
        t3.fail(f"Unhandled exception:\n{traceback.format_exc()}")
    tests.append(t3)

    return print_report(tests)


if __name__ == "__main__":
    raise SystemExit(main())
