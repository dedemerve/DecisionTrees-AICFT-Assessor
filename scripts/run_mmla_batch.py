#!/usr/bin/env python3
"""run_mmla_batch.py — Process full cohort through MMLA scoring sequentially.

Skips students whose final_scored.json already exists.
Skips students whose frames directory is missing.
Resumes interrupted runs via the checkpoint JSONL.

Usage:
    python scripts/run_mmla_batch.py
    python scripts/run_mmla_batch.py --dry-run   # show plan without running
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"
DATA_ROOT = REPO_ROOT / "data_sources_2026"

PYTHON = REPO_ROOT / ".venv-hybrid" / "bin" / "python"
SCORER = REPO_ROOT / "scripts" / "run_mmla_scoring.py"

# Processing order: session -> students
BATCH: list[tuple[str, str]] = [
    # 21 April — Helena already running; rest follow
    ("21apr", "Iris"),
    ("21apr", "Irma"),
    ("21apr", "Isabel"),
    ("21apr", "Marco"),
    ("21apr", "Marcus"),
    ("21apr", "Nadia"),
    ("21apr", "Shana"),
    ("21apr", "Sheila"),
    ("21apr", "Zara"),
    # 28 April
    ("28apr", "Irma"),
    ("28apr", "Isabel"),
    ("28apr", "Marco"),
    ("28apr", "Melinda"),
    ("28apr", "Nadia"),
    ("28apr", "Serena"),
    ("28apr", "Zara"),
]

SESSION_AUDIO_DIRS = {
    "21apr": "codap_arbor_21april_audio",
    "28apr": "codap_arbor_28april_audio",
    "05may": "colab_may_audio",
}

SESSION_VIDEO_DIRS = {
    "21apr": "21 April CODAP Arbor Screen Recordings",
    "28apr": "28 April CODAP Arbor Screen Recordings",
}


def final_scored_path(student: str, session: str) -> Path:
    return LOG_DIR / f"{student}_{session}_final_scored.json"


def frames_dir(student: str, session: str) -> Path:
    audio_dir = DATA_ROOT / SESSION_AUDIO_DIRS[session] / student
    return audio_dir / f"{student}_frames"


def manifest_frame_count(student: str, session: str) -> int:
    """Return segment count from manifest (authoritative frame count for scoring)."""
    audio_dir = DATA_ROOT / SESSION_AUDIO_DIRS[session] / student
    manifest = audio_dir / f"{student}_video_extraction_manifest.json"
    if not manifest.exists():
        return 0
    try:
        m = json.loads(manifest.read_text(encoding="utf-8"))
        frames_key = "segments" if "codap" in SESSION_AUDIO_DIRS.get(session, "") else "frames"
        return len(m.get(frames_key, []))
    except Exception:
        return 0


def checkpoint_path(student: str, session: str) -> Path:
    return LOG_DIR / f"{student}_{session}_frames.jsonl"


def checkpoint_count(student: str, session: str) -> int:
    p = checkpoint_path(student, session)
    if not p.exists():
        return 0
    return sum(1 for _ in p.open(encoding="utf-8"))


def estimate_cost(frame_count: int, elapsed_s: float) -> str:
    """Rough cost estimate: Haiku input ~600tok + output ~420tok per frame."""
    input_cost = frame_count * 600 * 0.80 / 1_000_000   # $0.80/MTok input
    output_cost = frame_count * 420 * 4.00 / 1_000_000  # $4.00/MTok output
    return f"~${input_cost + output_cost:.2f}"


def run_student(session: str, student: str, dry_run: bool) -> dict:
    """Run scorer for one student. Returns result dict."""
    result = {
        "student": student,
        "session": session,
        "status": None,
        "frames": 0,
        "elapsed_min": 0.0,
        "cost": "?",
        "reason": "",
    }

    fs = final_scored_path(student, session)
    if fs.exists():
        result["status"] = "skipped"
        result["reason"] = "final_scored.json already exists"
        d = json.loads(fs.read_text(encoding="utf-8"))
        result["frames"] = d.get("frames_total", 0)
        return result

    fd = frames_dir(student, session)
    if not fd.exists() or not list(fd.glob("*.jpg")):
        result["status"] = "skipped"
        result["reason"] = "no frames directory"
        return result

    frame_count = manifest_frame_count(student, session) or len(list(fd.glob("*.jpg")))
    done_before = checkpoint_count(student, session)
    result["frames"] = frame_count

    if dry_run:
        result["status"] = "dry_run"
        result["reason"] = f"{frame_count} frames ({done_before} already in checkpoint)"
        return result

    t0 = time.monotonic()
    import os
    env = os.environ.copy()
    proc = subprocess.run(
        [str(PYTHON), str(SCORER), "--session", session, "--students", student],
        env=env,
    )
    elapsed = time.monotonic() - t0
    result["elapsed_min"] = elapsed / 60

    if proc.returncode == 0 and final_scored_path(student, session).exists():
        result["status"] = "ok"
        result["cost"] = estimate_cost(frame_count, elapsed)
    else:
        result["status"] = "failed"
        result["reason"] = f"exit code {proc.returncode}"

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Show plan without running")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — no API calls will be made\n")

    print(f"{'Student':<12} {'Session':<8} {'Plan'}")
    print("-" * 50)
    for session, student in BATCH:
        fs = final_scored_path(student, session)
        fd = frames_dir(student, session)
        ckpt = checkpoint_count(student, session)
        if fs.exists():
            status = "SKIP (done)"
        elif not fd.exists() or not list(fd.glob("*.jpg")):
            status = "SKIP (no frames)"
        else:
            frames = manifest_frame_count(student, session) or len(list(fd.glob("*.jpg")))
            status = f"RUN  ({frames} frames, {ckpt} in checkpoint)"
        print(f"  {student:<12} {session:<8} {status}")

    if args.dry_run:
        return

    print()
    t_batch_start = time.monotonic()
    results: list[dict] = []
    total_cost_usd = 0.0

    for session, student in BATCH:
        print(f"\n{'='*60}")
        print(f"  {student} ({session})")
        print(f"{'='*60}")
        r = run_student(session, student, dry_run=False)
        results.append(r)

        if r["status"] == "ok":
            cost_str = r["cost"]
            print(
                f"  {student}: {r['frames']} frames, "
                f"done in {r['elapsed_min']:.0f} min, "
                f"cost {cost_str}"
            )
            try:
                total_cost_usd += float(cost_str.replace("~$", ""))
            except ValueError:
                pass
        elif r["status"] == "skipped":
            print(f"  {student}: SKIPPED — {r['reason']}")
        else:
            print(f"  {student}: FAILED — {r['reason']}")

    batch_elapsed = (time.monotonic() - t_batch_start) / 60

    ok = [r for r in results if r["status"] == "ok"]
    skipped = [r for r in results if r["status"] == "skipped"]
    failed = [r for r in results if r["status"] == "failed"]

    print(f"\n{'='*60}")
    print(f"BATCH COMPLETE in {batch_elapsed:.0f} min")
    print(f"  Processed : {len(ok)}")
    print(f"  Skipped   : {len(skipped)}")
    print(f"  Failed    : {len(failed)}")
    print(f"  Est. cost : ~${total_cost_usd:.2f}")
    if failed:
        print(f"  Failed    : {[r['student'] for r in failed]}")


if __name__ == "__main__":
    main()
