#!/usr/bin/env python3
"""Automatic recalibration for students who fail the extraction quality gate.

For each failing student, diagnoses the root cause and takes the minimal
corrective action needed — then re-runs extraction and the gate.

Supported failure modes
-----------------------
pilot_export_exists
    All frames were rejected by the task-screen guard (CodapTaskGuard or
    ColabTaskGuard). Root cause: heuristic signals are calibrated to known
    students; a new student's screen layout produces different signal values.

    Fix: sample frames from the student's video, score each one against the
    heuristic analyzer, pick the N best-scoring frames (highest content_score
    that is still genuinely task-related), and add them as templates to
    calibration/colab_task_templates or calibration/codap_task_templates.
    Then re-run extraction so the guard can match the new layout.

codap_era_max_gap
    Frames exist but there is a gap > MAX_CODAP_GAP_S seconds between them
    during the core task window (900–3600 s). Caused by long idle periods or
    the student minimizing the app.

    Fix: re-run extraction with an increased --codap-gap-fill-seconds value
    to bridge the gap.  The value is set just high enough to cover the
    observed gap, capped at 600 s to prevent runaway fill.

Usage
-----
    python scripts/auto_recalibrate.py --cohort 05may
    python scripts/auto_recalibrate.py --cohort 05may Helena Sheila Zara
    python scripts/auto_recalibrate.py --cohort 05may Serena
    python scripts/auto_recalibrate.py --cohort all   # all cohorts, all students
"""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS   = REPO_ROOT / "scripts"
PYTHON    = REPO_ROOT / ".venv-hybrid" / "bin" / "python"
LOG_DIR   = REPO_ROOT / "logs" / "pipeline_runs"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO_ROOT))

from batch_extract_strict_cohorts import (   # noqa: E402
    COHORTS,
    COHORT_TASK_ACTIVITY,
    STRICT_VIDEO_ARGS,
    post_process,
    quality_gate_passes,
    video_args_for_cohort,
)
from dynamic_video_analytics import (        # noqa: E402
    CodapContentAnalyzer,
    ColabContentAnalyzer,
    DEFAULT_CODAP_TASK_TEMPLATE_DIR,
    DEFAULT_COLAB_TASK_TEMPLATE_DIR,
    frame_phash,
)

LOGGER = logging.getLogger("auto_recalibrate")

# ── constants ────────────────────────────────────────────────────────────────
SAMPLE_INTERVAL_S     = 60    # probe video every N seconds when sampling
TEMPLATES_PER_STUDENT = 4     # how many frames to add to calibration per student
MIN_CONTENT_SCORE     = 2     # preferred minimum heuristic score
MIN_CONTENT_SCORE_FALLBACK = 1  # fallback if nothing meets the preferred threshold
MAX_GAP_FILL_S        = 600   # hard cap on --codap-gap-fill-seconds override
GAP_FILL_MARGIN_S     = 30    # add this much margin on top of observed gap


# ── gate report helpers ──────────────────────────────────────────────────────

def read_gate_report(student_dir: Path, student_id: str) -> dict[str, Any]:
    """Return the most recent gate JSON report for a student, or {}."""
    manifest = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest.is_file():
        return {}
    mf = json.loads(manifest.read_text(encoding="utf-8"))
    return mf.get("gate_report") or {}


def blocker_names(gate_report: dict[str, Any]) -> list[str]:
    """Return names of failed checks from a gate report."""
    return [
        c["check"]
        for c in gate_report.get("checks", [])
        if not c.get("passed", True)
    ]


def max_gap_from_report(gate_report: dict[str, Any]) -> float | None:
    """Extract observed max gap (seconds) from gate report."""
    for c in gate_report.get("checks", []):
        if c.get("check") == "codap_era_max_gap":
            return c.get("max_gap_s")
    return None


# ── video sampling ───────────────────────────────────────────────────────────

def find_video(student_id: str, video_root: Path) -> Path | None:
    for ext in (".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"):
        p = video_root / f"{student_id}{ext}"
        if p.is_file():
            return p
    return None


def video_duration_s(video_path: Path) -> float:
    """Return video duration in seconds.

    webm files recorded by Chrome often omit the duration header. Fall back to
    probing streams, then to a decode scan of the last few seconds.
    """
    # 1. format duration
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=15,
        )
        d = json.loads(r.stdout)
        dur = d.get("format", {}).get("duration")
        if dur and dur != "N/A":
            return float(dur)
    except Exception:
        pass

    # 2. stream-level pts_time of the last packet (slow for large files — cap scan)
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-select_streams", "v:0",
             "-show_packets", "-print_format", "json",
             "-read_intervals", "%+#500",   # first 500 packets only
             str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        pkts = json.loads(r.stdout).get("packets", [])
        if pkts:
            last_pts = max(float(p.get("pts_time", 0)) for p in pkts if p.get("pts_time"))
            if last_pts > 0:
                return last_pts   # lower bound — good enough for sampling
    except Exception:
        pass

    # 3. use file size as a rough proxy (assume ~200 kbps video = 25 KB/s)
    try:
        size_bytes = video_path.stat().st_size
        return size_bytes / 25_000  # very rough but prevents 0-duration bail-out
    except Exception:
        return 0.0


def _extract_one_frame(video_path: Path, ts: float) -> np.ndarray | None:
    """Extract a single JPEG frame at ts seconds, return as BGR ndarray."""
    import tempfile, os
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-ss", f"{ts:.1f}", "-i", str(video_path),
             "-frames:v", "1", "-q:v", "5", tmp_path],
            capture_output=True, timeout=20,
        )
        if r.returncode == 0 and Path(tmp_path).stat().st_size > 500:
            return cv2.imread(tmp_path)
    except Exception:
        pass
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return None


def sample_frames_from_video(
    video_path: Path,
    duration_s: float,        # kept for API compatibility; used as max cap only
    interval_s: int = SAMPLE_INTERVAL_S,
    max_ts_s: int = 7200,     # never probe past 2 hours
) -> list[tuple[float, np.ndarray]]:
    """Extract one frame every interval_s seconds.

    Does not rely on duration_s for termination — keeps probing until ffmpeg
    fails to return a frame (i.e. past the end of the video). This is necessary
    for webm files recorded by Chrome, which often omit the duration header.

    Returns [(timestamp_s, bgr_ndarray), ...].
    """
    results: list[tuple[float, np.ndarray]] = []
    consecutive_failures = 0
    ts = interval_s
    while ts <= max_ts_s:
        bgr = _extract_one_frame(video_path, ts)
        if bgr is not None:
            results.append((ts, bgr))
            consecutive_failures = 0
        else:
            consecutive_failures += 1
            if consecutive_failures >= 3:
                # three misses in a row → past end of video
                break
        ts += interval_s
    return results


# ── template selection ───────────────────────────────────────────────────────

def score_frame_codap(bgr: np.ndarray) -> int:
    signals = CodapContentAnalyzer.analyze(bgr)
    return signals.content_score


def score_frame_colab(bgr: np.ndarray) -> int:
    signals = ColabContentAnalyzer.analyze(bgr)
    return signals.content_score


def existing_template_hashes(template_dir: Path) -> list[Any]:
    hashes = []
    for p in sorted(template_dir.iterdir()):
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            continue
        bgr = cv2.imread(str(p))
        if bgr is not None:
            hashes.append(frame_phash(bgr))
    return hashes


def is_duplicate(bgr: np.ndarray, existing_hashes: list[Any], threshold: int = 8) -> bool:
    h = frame_phash(bgr)
    return any(float(h - eh) <= threshold for eh in existing_hashes)


def add_templates_for_student(
    student_id: str,
    video_path: Path,
    template_dir: Path,
    task_activity: str,
    *,
    n: int = TEMPLATES_PER_STUDENT,
    dry_run: bool = False,
) -> list[Path]:
    """Sample video, pick best task-screen frames, copy to template_dir."""
    duration = video_duration_s(video_path)
    if duration < 10:
        LOGGER.warning("[%s] video too short (%.1fs) to sample", student_id, duration)
        return []

    score_fn = score_frame_colab if task_activity == "colab" else score_frame_codap

    LOGGER.info("[%s] sampling video (%.0fs) every %ds …",
                student_id, duration, SAMPLE_INTERVAL_S)
    frames = sample_frames_from_video(video_path, duration)
    if not frames:
        LOGGER.warning("[%s] no frames sampled from video", student_id)
        return []

    # score and filter — prefer MIN_CONTENT_SCORE, fall back to MIN_CONTENT_SCORE_FALLBACK
    scored_all = [(ts, bgr, score_fn(bgr)) for ts, bgr in frames]
    scored = [(ts, bgr, sc) for ts, bgr, sc in scored_all if sc >= MIN_CONTENT_SCORE]
    if not scored:
        scored = [(ts, bgr, sc) for ts, bgr, sc in scored_all
                  if sc >= MIN_CONTENT_SCORE_FALLBACK]
        if scored:
            LOGGER.info(
                "[%s] no frames scored >= %d; using fallback threshold %d "
                "(screen layout differs from calibration — adding for template coverage)",
                student_id, MIN_CONTENT_SCORE, MIN_CONTENT_SCORE_FALLBACK,
            )
        else:
            LOGGER.warning(
                "[%s] no frames scored >= %d — heuristic cannot identify task screen; "
                "manual review needed",
                student_id, MIN_CONTENT_SCORE_FALLBACK,
            )
            return []

    # sort by score descending, then deduplicate against existing templates
    scored.sort(key=lambda x: -x[2])
    existing = existing_template_hashes(template_dir)

    added: list[Path] = []
    for ts, bgr, sc in scored:
        if len(added) >= n:
            break
        if is_duplicate(bgr, existing + [frame_phash(b) for _, b, _ in
                                          [(0, cv2.imread(str(p)), 0)
                                           for p in added
                                           if False]]):  # inline dedup below
            continue
        # proper dedup: check against already-chosen bgrs
        chosen_hashes = [frame_phash(cv2.imread(str(p))) for p in added if p.is_file()]
        if is_duplicate(bgr, existing + chosen_hashes):
            continue

        stem = f"{student_id.lower()}_auto_{int(ts):05d}s_score{sc}"
        dest = template_dir / f"{stem}.jpg"
        if not dry_run:
            cv2.imwrite(str(dest), bgr, [cv2.IMWRITE_JPEG_QUALITY, 90])
            LOGGER.info("[%s] added template: %s (score=%d, t=%.0fs)",
                        student_id, dest.name, sc, ts)
        else:
            LOGGER.info("[%s] DRY-RUN would add: %s (score=%d, t=%.0fs)",
                        student_id, dest.name, sc, ts)
        added.append(dest)

    return added


# ── re-extraction ────────────────────────────────────────────────────────────

def reextract_student(
    cohort_key: str,
    student_id: str,
    audio_root: Path,
    video_root: Path,
    *,
    extra_args: list[str] | None = None,
    dry_run: bool = False,
) -> int:
    """Run dynamic_video_analytics for one student, return exit code."""
    student_dir = audio_root / student_id
    log_path = LOG_DIR / f"recal_{cohort_key}_{student_id}.log"
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # back up existing manifest before overwriting
    manifest = student_dir / f"{student_id}_video_extraction_manifest.json"
    if manifest.is_file():
        backup = student_dir / f"{student_id}_video_extraction_manifest.bak.json"
        shutil.copy2(manifest, backup)

    frames_dir = student_dir / f"{student_id}_frames"
    if not dry_run and frames_dir.is_dir():
        shutil.rmtree(frames_dir)

    extractor_script = (
        SCRIPTS / "colab_event_analytics.py"
        if cohort_key == "05may"
        else SCRIPTS / "dynamic_video_analytics.py"
    )
    cmd = [
        "caffeinate", "-i",
        str(PYTHON), "-u",
        str(extractor_script),
        student_id,
        "--audio-root", str(audio_root),
        "--video-root", str(video_root),
        *video_args_for_cohort(cohort_key),
        *(extra_args or []),
    ]

    if dry_run:
        LOGGER.info("[%s] DRY-RUN cmd: %s", student_id, " ".join(cmd))
        return 0

    LOGGER.info("[%s] re-extracting … log → %s", student_id, log_path.name)
    with log_path.open("w") as fh:
        fh.write(">>> " + " ".join(cmd) + "\n\n")
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT)
        proc.wait()
    rc = proc.returncode
    LOGGER.info("[%s] extraction exit_code=%d", student_id, rc)
    return rc


# ── per-student recalibration logic ─────────────────────────────────────────

def recalibrate_student(
    cohort_key: str,
    student_id: str,
    audio_root: Path,
    video_root: Path,
    *,
    dry_run: bool = False,
) -> dict[str, Any]:
    student_dir = audio_root / student_id
    task_activity = COHORT_TASK_ACTIVITY.get(cohort_key, "codap")
    template_dir = (
        DEFAULT_COLAB_TASK_TEMPLATE_DIR
        if task_activity == "colab"
        else DEFAULT_CODAP_TASK_TEMPLATE_DIR
    )

    # ── run gate to get current failure reasons ───────────────────────────
    gate_proc = subprocess.run(
        [str(PYTHON), str(SCRIPTS / "extraction_quality_gate.py"),
         student_id, "--audio-root", str(audio_root)],
        capture_output=True, text=True,
    )
    gate_passed = gate_proc.returncode == 0

    if gate_passed:
        LOGGER.info("[%s] gate already passes — nothing to do", student_id)
        return {"student_id": student_id, "action": "skipped", "reason": "gate_already_passes"}

    # gate stdout is a JSON report — parse it directly
    gate_report: dict[str, Any] = {}
    try:
        gate_report = json.loads(gate_proc.stdout)
    except Exception:
        pass

    blockers = blocker_names(gate_report)

    LOGGER.info("[%s] gate blockers: %s", student_id, blockers)
    result: dict[str, Any] = {"student_id": student_id, "blockers": blockers, "actions": []}

    extra_extraction_args: list[str] = []
    needs_reextract = False

    # ── FIX: pilot_export_exists — add templates ──────────────────────────
    if "pilot_export_exists" in blockers:
        video_path = find_video(student_id, video_root)
        if not video_path:
            LOGGER.error("[%s] no video file found in %s", student_id, video_root)
            result["actions"].append({"fix": "add_templates", "status": "error",
                                      "reason": "no_video_file"})
        else:
            added = add_templates_for_student(
                student_id, video_path, template_dir, task_activity,
                dry_run=dry_run,
            )
            if added:
                result["actions"].append({
                    "fix": "add_templates",
                    "status": "dry_run" if dry_run else "done",
                    "templates_added": [p.name for p in added],
                    "template_dir": str(template_dir.relative_to(REPO_ROOT)),
                })
                needs_reextract = True
            else:
                result["actions"].append({
                    "fix": "add_templates",
                    "status": "failed",
                    "reason": "no_frames_scored_above_threshold — "
                              "heuristic may not recognise this student's screen layout; "
                              "manual review needed",
                })

    # ── FIX: codap_era_max_gap — increase gap-fill ────────────────────────
    if "codap_era_max_gap" in blockers:
        observed_gap = max_gap_from_report(gate_report)
        if observed_gap is None:
            # fall back to parsing detail string from gate report checks
            for c in gate_report.get("checks", []):
                if c.get("check") == "codap_era_max_gap":
                    try:
                        observed_gap = float(str(c.get("detail", "")).split("max gap")[1].split("s")[0].strip())
                    except Exception:
                        pass
                    break

        if observed_gap:
            fill_s = min(int(observed_gap) + GAP_FILL_MARGIN_S, MAX_GAP_FILL_S)
            LOGGER.info("[%s] gap %.0fs → setting --codap-gap-fill-seconds %d",
                        student_id, observed_gap, fill_s)
            extra_extraction_args += ["--codap-gap-fill-seconds", str(fill_s)]
            result["actions"].append({
                "fix": "increase_gap_fill",
                "observed_gap_s": round(observed_gap, 1),
                "new_gap_fill_s": fill_s,
            })
            needs_reextract = True
        else:
            LOGGER.warning("[%s] codap_era_max_gap blocker but could not read observed gap",
                           student_id)
            result["actions"].append({
                "fix": "increase_gap_fill",
                "status": "failed",
                "reason": "could not determine observed gap from gate report",
            })

    # ── re-extraction ─────────────────────────────────────────────────────
    if needs_reextract:
        rc = reextract_student(
            cohort_key, student_id, audio_root, video_root,
            extra_args=extra_extraction_args, dry_run=dry_run,
        )
        if not dry_run:
            post = post_process(student_id, audio_root,
                                LOG_DIR / f"recal_{cohort_key}_{student_id}.log")
            gate_now_passes = quality_gate_passes(student_dir, student_id, audio_root)
            result["reextraction"] = {
                "exit_code": rc,
                "post": post,
                "gate_passes_after": gate_now_passes,
            }
            if gate_now_passes:
                LOGGER.info("[%s] RECALIBRATION SUCCESS — gate now passes", student_id)
            else:
                LOGGER.warning("[%s] gate still fails after recalibration", student_id)
        else:
            result["reextraction"] = {"dry_run": True, "extra_args": extra_extraction_args}

    return result


# ── main ─────────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Auto-recalibrate students who fail the extraction quality gate"
    )
    parser.add_argument("students", nargs="*",
                        help="Student IDs to recalibrate (default: all failing students)")
    parser.add_argument("--cohort",
                        choices=[c[0] for c in COHORTS] + ["all"],
                        default="all")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be done without writing anything")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    cohort_list = [c for c in COHORTS if args.cohort in ("all", c[0])]
    overall: list[dict[str, Any]] = []

    for cohort_key, audio_root, video_root in cohort_list:
        if args.students:
            targets = args.students
        else:
            # discover failing students automatically
            targets = []
            for child in sorted(audio_root.iterdir(), key=lambda p: p.name.lower()):
                if not child.is_dir():
                    continue
                sid = child.name
                if not (child / f"{sid}_video_extraction_manifest.json").is_file():
                    continue
                if not quality_gate_passes(child, sid, audio_root):
                    targets.append(sid)

        if not targets:
            LOGGER.info("[%s] no failing students found", cohort_key)
            continue

        LOGGER.info("[%s] recalibrating: %s", cohort_key, ", ".join(targets))

        for student_id in targets:
            student_dir = audio_root / student_id
            if not student_dir.is_dir():
                LOGGER.warning("[%s/%s] directory not found", cohort_key, student_id)
                continue
            result = recalibrate_student(
                cohort_key, student_id, audio_root, video_root,
                dry_run=args.dry_run,
            )
            result["cohort"] = cohort_key
            overall.append(result)

    # ── summary ──────────────────────────────────────────────────────────
    print("\n=== auto_recalibrate summary ===")
    for r in overall:
        sid   = r["student_id"]
        cohrt = r.get("cohort", "")
        reex  = r.get("reextraction", {})
        gate  = reex.get("gate_passes_after")
        if gate is True:
            status = "PASS"
        elif gate is False:
            status = "STILL FAIL"
        elif r.get("action") == "skipped":
            status = "SKIPPED (already passing)"
        elif args.dry_run:
            status = "DRY-RUN"
        else:
            status = "?"
        print(f"  {cohrt}/{sid}: {status}  blockers={r.get('blockers', [])}  "
              f"actions={[a.get('fix','?') for a in r.get('actions',[])]}")

    failed_after = [r for r in overall
                    if r.get("reextraction", {}).get("gate_passes_after") is False]
    if failed_after:
        print(f"\n{len(failed_after)} student(s) still failing — manual review needed.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
