#!/usr/bin/env python3
"""Seed Colab task guard templates from high-scoring May cohort frames."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from dynamic_video_analytics import ColabContentAnalyzer

AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "colab_python_audio"
OUT_DIR = REPO_ROOT / "calibration" / "colab_task_templates"
MAX_TEMPLATES = 8


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    candidates: list[tuple[int, Path, str]] = []

    for student_dir in sorted(AUDIO_ROOT.iterdir()):
        if not student_dir.is_dir():
            continue
        frames_dir = student_dir / f"{student_dir.name}_frames"
        if not frames_dir.is_dir():
            continue
        for frame_path in sorted(frames_dir.glob("frame_*.jpg")):
            bgr = cv2.imread(str(frame_path))
            if bgr is None:
                continue
            signals = ColabContentAnalyzer.analyze(bgr)
            if ColabContentAnalyzer.is_colab_task(signals):
                candidates.append((signals.content_score, frame_path, student_dir.name))

    candidates.sort(key=lambda row: row[0], reverse=True)
    selected = candidates[:MAX_TEMPLATES]
    if not selected:
        print("No Colab template candidates found.")
        return 1

    for idx, (score, src, student) in enumerate(selected, 1):
        dst = OUT_DIR / f"colab_{student}_{src.stem}_s{score}.jpg"
        shutil.copy2(src, dst)
        print(f"  {dst.name}  (score={score}, from {student})")

    print(f"Wrote {len(selected)} template(s) to {OUT_DIR.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
