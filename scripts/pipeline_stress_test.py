#!/usr/bin/env python3
"""
pipeline_stress_test.py

Two-track stress and red-team test suite for the MMLA pipeline.

  Track A — API Resilience
    A1: 429 rate-limit  → retry exhaust → RuntimeError raised, no crash
    A2: 503 transient   → retry succeeds on 3rd attempt
    A3: Malformed JSON  → parse_analysis_json raises, retry loop catches it
    A4: Network timeout → socket.timeout propagates through retry correctly
    A5: Empty response  → blank string handled by parse_analysis_json

  Track B — Degenerate Input
    B1: Zero-frame manifest         → pipeline skips gracefully
    B2: Unlabeled transcript only   → speech intervals return [] (no crash)
    B3: Truncated video (Shana 572s)→ frame extraction beyond duration is handled
    B4: None video_duration_seconds → Shana Guard fallback does not divide-by-zero
    B5: Corrupt JSON manifest       → IOError/JSONDecodeError caught upstream

Usage:
    python scripts/pipeline_stress_test.py [--audio-root PATH] [--video-root PATH]
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import socket
import sys
import tempfile
import textwrap
import traceback
import types
import unittest.mock as mock
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ── Repo root on path ──────────────────────────────────────────────────────────
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

DEFAULT_AUDIO_21    = REPO / "data_sources_2026" / "codap_arbor_21april_audio"
DEFAULT_VIDEO_21    = REPO / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings"
DEFAULT_COLAB_AUDIO = REPO / "data_sources_2026" / "colab_python_audio"
LOG_DIR             = REPO / "logs" / "pipeline_runs"


# ── Result container ───────────────────────────────────────────────────────────
@dataclass
class CaseResult:
    id: str
    desc: str
    passed: bool = True
    notes: list[str] = field(default_factory=list)

    def ok(self, msg: str)   -> None: self.notes.append(f"  OK  {msg}")
    def fail(self, msg: str) -> None:
        self.passed = False
        self.notes.append(f" FAIL {msg}")
    def info(self, msg: str) -> None: self.notes.append(f"      {msg}")


# ── Module loader helper ───────────────────────────────────────────────────────
def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    mod  = importlib.util.module_from_spec(spec)           # type: ignore[arg-type]
    # Must register before exec_module so @dataclass can resolve cls.__module__
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)                       # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(name, None)
        raise
    return mod


# ==============================================================================
# TRACK A — API Resilience
# ==============================================================================

def _load_analyzer() -> types.ModuleType:
    return _load_module(
        "codap_frame_analyzer",
        REPO / "scripts" / "codap_frame_analyzer.py",
    )


class _FakeResponse:
    """Minimal stand-in for anthropic.types.Message."""
    def __init__(self, text: str):
        self.content = [types.SimpleNamespace(text=text)]


def _good_payload() -> str:
    return json.dumps({
        "visual_evidence_found": True,
        "screen_state_analysis": "stress-test OK",
        "cognitive_validity":    "stress-test OK",
    })


def run_a1_rate_limit_exhausted(cr: CaseResult) -> None:
    """Every attempt raises a 429-like exception. RuntimeError must surface."""
    mod = _load_analyzer()

    class FakeClient:
        def __init__(self): self.messages = self
        def create(self, **_):
            raise Exception("status_code=429 rate_limit_error")

    try:
        mod.call_anthropic(FakeClient(), "claude-sonnet-5", "sys", "usr", "aabb")
        cr.fail("RuntimeError was NOT raised — exhausted retries silently swallowed")
    except RuntimeError as exc:
        if "failed after" in str(exc):
            cr.ok(f"RuntimeError raised correctly: {exc}")
        else:
            cr.fail(f"Unexpected RuntimeError message: {exc}")
    except Exception as exc:
        cr.fail(f"Wrong exception type ({type(exc).__name__}): {exc}")


def run_a2_transient_503(cr: CaseResult) -> None:
    """First two calls raise 503; third succeeds. Must return parsed dict."""
    mod = _load_analyzer()
    attempts = {"n": 0}

    class FakeClient:
        def __init__(self): self.messages = self
        def create(self, **_):
            attempts["n"] += 1
            if attempts["n"] < 3:
                raise Exception("status_code=503 overloaded")
            return _FakeResponse(_good_payload())

    try:
        result = mod.call_anthropic(
            FakeClient(), "claude-sonnet-5", "sys", "usr", "aabb",
            max_retries=5,
        )
        if isinstance(result, dict) and result.get("visual_evidence_found") is True:
            cr.ok(f"Recovered after {attempts['n']} attempts, result dict OK")
        else:
            cr.fail(f"Unexpected return value: {result!r}")
    except Exception as exc:
        cr.fail(f"Should have recovered but raised {type(exc).__name__}: {exc}")


def run_a3_malformed_json(cr: CaseResult) -> None:
    """API returns unparseable text every attempt. RuntimeError must surface."""
    mod = _load_analyzer()

    class FakeClient:
        def __init__(self): self.messages = self
        def create(self, **_):
            return _FakeResponse("This is not JSON at all ¯\\_(ツ)_/¯")

    try:
        mod.call_anthropic(FakeClient(), "claude-sonnet-5", "sys", "usr", "aabb",
                           max_retries=2)
        cr.fail("RuntimeError was NOT raised on malformed JSON")
    except RuntimeError as exc:
        cr.ok(f"RuntimeError raised after malformed JSON: {exc}")
    except json.JSONDecodeError as exc:
        cr.fail(f"Raw JSONDecodeError escaped retry loop: {exc}")


def run_a4_network_timeout(cr: CaseResult) -> None:
    """socket.timeout on every attempt must result in RuntimeError, not hang."""
    mod = _load_analyzer()

    class FakeClient:
        def __init__(self): self.messages = self
        def create(self, **_):
            raise socket.timeout("timed out")

    try:
        mod.call_anthropic(FakeClient(), "claude-sonnet-5", "sys", "usr", "aabb",
                           max_retries=2)
        cr.fail("RuntimeError was NOT raised on timeout")
    except RuntimeError as exc:
        cr.ok(f"RuntimeError raised on timeout: {exc}")


def run_a5_empty_response(cr: CaseResult) -> None:
    """API returns empty string. parse_analysis_json must raise, retry catches."""
    mod = _load_analyzer()

    class FakeClient:
        def __init__(self): self.messages = self
        def create(self, **_):
            return _FakeResponse("")

    try:
        mod.call_anthropic(FakeClient(), "claude-sonnet-5", "sys", "usr", "aabb",
                           max_retries=2)
        cr.fail("RuntimeError was NOT raised on empty response")
    except RuntimeError as exc:
        cr.ok(f"RuntimeError raised on empty response: {exc}")


# ==============================================================================
# TRACK B — Degenerate Input
# ==============================================================================

def _load_validator() -> types.ModuleType:
    return _load_module(
        "mmla_coverage_validator",
        REPO / "scripts" / "mmla_coverage_validator.py",
    )


def run_b1_zero_frame_manifest(cr: CaseResult) -> None:
    """
    A manifest with frames=[] must not crash the coverage validator.
    We create a temp student dir with a zero-frame manifest and call
    _load_student_speech_intervals + the manifest loader.
    """
    mod = _load_validator()

    with tempfile.TemporaryDirectory(prefix="stress_b1_") as tmpdir:
        student_id = "GhostStudent"
        sdir = Path(tmpdir) / student_id
        sdir.mkdir()

        manifest = {
            "parameters": {"task_activity": "codap"},
            "frames": [],
            "summary": {
                "speech_anchor_count": 0,
                "total_frames_extracted": 0,
            },
        }
        (sdir / f"{student_id}_video_extraction_manifest.json").write_text(
            json.dumps(manifest), encoding="utf-8"
        )

        try:
            intervals = mod._load_student_speech_intervals(sdir, student_id)
            cr.ok(f"_load_student_speech_intervals returned {intervals!r} (no crash)")
        except Exception as exc:
            cr.fail(f"Crashed on missing transcript: {exc}")
            return

        # Verify _parse_codap_csv handles a student with zero rows safely.
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8"
        ) as tmp_csv:
            tmp_csv.write("id,created_at,student_id,action,timestamp_ms,parameters,raw_data\n")
            tmp_csv_path = Path(tmp_csv.name)

        try:
            events = mod._parse_codap_csv(tmp_csv_path, date_filter="2026-04-21")
            student_events = [e for e in events if e.get("student_id") == student_id]
            cr.ok(f"_parse_codap_csv returned {len(student_events)} events for zero-row student")
        except Exception as exc:
            cr.fail(f"_parse_codap_csv crashed on empty CSV: {exc}")
        finally:
            tmp_csv_path.unlink(missing_ok=True)


def run_b2_unlabeled_transcript_only(cr: CaseResult) -> None:
    """
    Students with only _transcript.json (no _transcript_labeled.json)
    must return an empty speech-interval list, not raise.
    Covers Ulysses and Irma.
    """
    mod = _load_validator()

    for student_id in ("Ulysses", "Irma"):
        student_dir = DEFAULT_AUDIO_21 / student_id
        if not student_dir.is_dir():
            cr.info(f"{student_id}: directory not found — skipped")
            continue

        labeled_path = student_dir / f"{student_id}_transcript_labeled.json"
        plain_path   = student_dir / f"{student_id}_transcript.json"

        if labeled_path.is_file():
            cr.info(f"{student_id}: labeled transcript exists (not a degenerate case)")
            continue
        if not plain_path.is_file():
            cr.info(f"{student_id}: no transcript at all — skipped")
            continue

        try:
            intervals = mod._load_student_speech_intervals(student_dir, student_id)
            if isinstance(intervals, list):
                cr.ok(
                    f"{student_id}: returned {len(intervals)} intervals from "
                    "unlabeled-only transcript (no crash)"
                )
            else:
                cr.fail(f"{student_id}: returned non-list {type(intervals).__name__}")
        except Exception as exc:
            cr.fail(f"{student_id}: raised {type(exc).__name__}: {exc}")


def run_b3_truncated_video_frame_extraction(cr: CaseResult) -> None:
    """
    Shana's video is only 572s. Requesting a frame beyond that duration
    (e.g., t=3600s) must not crash — ffmpeg returns error, cv2 fallback
    returns None or an empty frame. Neither should raise uncaught.
    """
    import cv2 as _cv2

    video_candidates = [
        REPO / "data_sources_2026" / "colab_python_audio" / "Shana" / "Shana_transcoded.webm",
        REPO / "data_sources_2026" / "colab_python_audio" / "Shana" / "Shana.webm",
        DEFAULT_AUDIO_21 / "Shana" / "Shana.webm",
    ]
    video_path = next((p for p in video_candidates if p.is_file()), None)

    if video_path is None:
        cr.info("Shana video not found in any expected location — skipped")
        return

    cr.info(f"Using video: {video_path.name} ({video_path.stat().st_size / 1024**2:.1f} MB)")

    beyond_duration_ts = 3900.0  # well past 572s

    cap = _cv2.VideoCapture(str(video_path))
    try:
        cap.set(_cv2.CAP_PROP_POS_MSEC, beyond_duration_ts * 1000.0)
        ret, frame = cap.read()
        if ret and frame is not None:
            cr.ok(
                f"cv2 read at t={beyond_duration_ts}s returned a frame "
                f"({frame.shape}) — decoder may have wrapped; not a crash"
            )
        else:
            cr.ok(
                f"cv2 read at t={beyond_duration_ts}s returned (ret={ret}, frame=None) "
                "— beyond-duration seek handled gracefully"
            )
    except Exception as exc:
        cr.fail(f"cv2 raised uncaught exception at beyond-duration seek: {exc}")
    finally:
        cap.release()


def run_b4_none_duration_shana_guard(cr: CaseResult) -> None:
    """
    Shana manifests have video_duration_seconds=None.
    _resolve_effective_duration must not divide-by-zero or crash.
    """
    mod = _load_validator()

    for cohort_dir in (DEFAULT_AUDIO_21, DEFAULT_COLAB_AUDIO):
        student_dir = cohort_dir / "Shana"
        if not student_dir.is_dir():
            continue

        manifest_path = student_dir / "Shana_video_extraction_manifest.json"
        if not manifest_path.is_file():
            continue

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("video_duration_seconds") is not None:
            cr.info(
                f"Shana manifest at {cohort_dir.name} has duration="
                f"{manifest['video_duration_seconds']} — not None, skipping"
            )
            continue

        cr.info(f"Testing Shana Guard with None duration in {cohort_dir.name}")

        try:
            dur = mod._resolve_effective_duration("Shana", student_dir, manifest)
            cr.ok(
                f"_resolve_effective_duration returned {dur!r} "
                f"for None duration (no crash)"
            )
        except ZeroDivisionError as exc:
            cr.fail(f"ZeroDivisionError in Shana Guard: {exc}")
        except Exception as exc:
            cr.fail(f"Unexpected {type(exc).__name__}: {exc}")
        break
    else:
        cr.info("No Shana manifest with None duration found — skipped")


def run_b5_corrupt_json_manifest(cr: CaseResult) -> None:
    """
    A manifest with truncated / invalid JSON must raise a clean error,
    not produce a silent empty frame list or cause a downstream KeyError.
    """
    mod = _load_validator()

    with tempfile.TemporaryDirectory(prefix="stress_b5_") as tmpdir:
        student_id = "CorruptStudent"
        sdir = Path(tmpdir) / student_id
        sdir.mkdir()

        corrupt_path = sdir / f"{student_id}_video_extraction_manifest.json"
        corrupt_path.write_text('{"frames": [{"ts": 1.0', encoding="utf-8")

        try:
            # _load_json is the internal helper used throughout the validator
            result = mod._load_json(corrupt_path, "corrupt manifest")
            if result is None:
                cr.ok("_load_json returned None for corrupt JSON (graceful fallback)")
            else:
                cr.fail(f"_load_json returned {result!r} instead of None for corrupt JSON")
        except json.JSONDecodeError:
            cr.ok("json.JSONDecodeError raised and surfaced (acceptable — caller must handle)")
        except Exception as exc:
            cr.fail(f"Unexpected {type(exc).__name__}: {exc}")


# ==============================================================================
# Report
# ==============================================================================

def print_report(tracks: dict[str, list[CaseResult]]) -> int:
    width = 72
    sep   = "=" * width
    dash  = "-" * width

    print()
    print(sep)
    print(f"{'MMLA PIPELINE STRESS & RED-TEAM REPORT':^{width}}")
    print(sep)

    all_passed = True
    for track_label, cases in tracks.items():
        print(f"\n  {track_label}")
        print(f"  {'—' * (width - 4)}")
        for cr in cases:
            verdict = "PASS" if cr.passed else "FAIL"
            print(f"  [{cr.id}] {cr.desc:<44} [{verdict}]")
            for line in cr.notes:
                print(f"  {line}")
            if not cr.passed:
                all_passed = False

    print()
    print(dash)
    status = "ALL STRESS SCENARIOS HANDLED CORRECTLY" if all_passed else "STRESS FAILURES DETECTED — REVIEW BEFORE LAUNCH"
    print(f" OVERALL: [{status}]")
    print(sep)
    print()
    return 0 if all_passed else 1


# ==============================================================================
# Entry point
# ==============================================================================

def main(argv: list[str] | None = None) -> int:
    import argparse

    p = argparse.ArgumentParser(description="MMLA pipeline stress & red-team tests")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_21)
    p.add_argument("--video-root", type=Path, default=DEFAULT_VIDEO_21)
    p.parse_args(argv)

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    track_a: list[CaseResult] = []
    track_b: list[CaseResult] = []

    def run(cr: CaseResult, fn, cases: list) -> None:
        try:
            fn(cr)
        except Exception:
            cr.fail(f"Unhandled exception in test harness:\n{traceback.format_exc()}")
        cases.append(cr)

    # ── Track A ────────────────────────────────────────────────────────────────
    run(CaseResult("A1", "429 rate-limit → retry exhausted → RuntimeError"),
        run_a1_rate_limit_exhausted, track_a)
    run(CaseResult("A2", "503 transient × 2 → recovery on 3rd attempt"),
        run_a2_transient_503, track_a)
    run(CaseResult("A3", "Malformed JSON response → RuntimeError"),
        run_a3_malformed_json, track_a)
    run(CaseResult("A4", "Network timeout → RuntimeError (no hang)"),
        run_a4_network_timeout, track_a)
    run(CaseResult("A5", "Empty API response → RuntimeError"),
        run_a5_empty_response, track_a)

    # ── Track B ────────────────────────────────────────────────────────────────
    run(CaseResult("B1", "Zero-frame manifest → graceful skip"),
        run_b1_zero_frame_manifest, track_b)
    run(CaseResult("B2", "Unlabeled transcript only (Ulysses/Irma) → [] intervals"),
        run_b2_unlabeled_transcript_only, track_b)
    run(CaseResult("B3", "Truncated video beyond duration seek (Shana 572s)"),
        run_b3_truncated_video_frame_extraction, track_b)
    run(CaseResult("B4", "None video_duration_seconds → Shana Guard safe"),
        run_b4_none_duration_shana_guard, track_b)
    run(CaseResult("B5", "Corrupt JSON manifest → clean error, no silent pass"),
        run_b5_corrupt_json_manifest, track_b)

    return print_report({
        "Track A — API Resilience (5 cases)":   track_a,
        "Track B — Degenerate Input (5 cases)": track_b,
    })


if __name__ == "__main__":
    raise SystemExit(main())
