#!/usr/bin/env python3
"""Re-run strict extraction for students with silent screen recordings (no captured audio)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

from batch_extract_strict_cohorts import COHORTS, discover_students
from dynamic_video_analytics import is_silent_screen_recording


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Re-extract silent screen-recording students")
    p.add_argument("--cohort", choices=[c[0] for c in COHORTS] + ["all"], default="all")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    selected = [c for c in COHORTS if args.cohort in ("all", c[0])]
    targets: list[tuple[str, str, Path, Path]] = []
    for cohort_key, audio_root, video_root in selected:
        for sid in discover_students(audio_root):
            if is_silent_screen_recording(audio_root / sid, sid):
                targets.append((cohort_key, sid, audio_root, video_root))

    if not targets:
        print("No silent screen-recording students found.")
        return 0

    print(f"Silent students to re-extract ({len(targets)}):")
    for cohort_key, sid, _, _ in targets:
        print(f"  {cohort_key}: {sid}")

    if args.dry_run:
        return 0

    for cohort_key, sid, audio_root, video_root in targets:
        cmd = [
            str(REPO_ROOT / ".venv-hybrid" / "bin" / "python"),
            str(SCRIPTS / "batch_extract_strict_cohorts.py"),
            "--cohort",
            cohort_key,
            "--student",
            sid,
            "-v",
        ]
        print(f"\n>>> {' '.join(cmd)}")
        rc = subprocess.call(cmd)
        if rc != 0:
            print(f"FAILED: {sid} exit={rc}", file=sys.stderr)
            return rc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
