#!/usr/bin/env python3
"""Move obsolete transcript sidecar files to macOS Trash (never rm)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"
LOG_PATH = REPO_ROOT / "logs" / "transcript_trash_manifest.json"

# Canonical outputs after speaker-labeling v2 split.
# Ham *_transcript.json is optional when *_transcript_labeled.json exists (same mlx text).
KEEP_PATTERNS = (
    "*_transcript_labeled.json",
)

# Regenerable sidecars from the pre-split / stale export pipeline.
TRASH_GLOBS = (
    "*_transcript.srt",
    "*_transcript.txt",
)


def move_to_trash(path: Path) -> None:
    """Move to macOS Trash without permanent deletion."""
    trash_dir = Path.home() / ".Trash"
    trash_dir.mkdir(exist_ok=True)
    target = trash_dir / path.name
    if target.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target = trash_dir / f"{path.stem}_{stamp}{path.suffix}"
    path.rename(target)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Move obsolete transcript sidecar files to Trash.")
    p.add_argument(
        "--audio-root",
        type=Path,
        default=AUDIO_ROOT,
        help="Student audio folder root (default: codap_arbor_21april_audio)",
    )
    p.add_argument(
        "--trash-ham-when-labeled",
        action="store_true",
        help="Also trash *_transcript.json when *_transcript_labeled.json exists",
    )
    p.add_argument(
        "--manifest",
        type=Path,
        help="Trash manifest path (default: logs/transcript_trash_manifest.json)",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    audio_root = args.audio_root.resolve()
    log_path = (args.manifest or LOG_PATH).resolve()

    if not audio_root.is_dir():
        print(f"[error] missing audio root: {audio_root}", file=sys.stderr)
        return 1

    ham_trash_glob = "*_transcript.json" if args.trash_ham_when_labeled else None
    to_trash: list[Path] = []
    kept: list[str] = []

    for student_dir in sorted(audio_root.iterdir()):
        if not student_dir.is_dir():
            continue
        labeled = list(student_dir.glob("*_transcript_labeled.json"))
        for pattern in TRASH_GLOBS:
            for path in sorted(student_dir.glob(pattern)):
                if path.is_file():
                    to_trash.append(path)
        if ham_trash_glob and labeled:
            for path in sorted(student_dir.glob(ham_trash_glob)):
                if path.is_file():
                    to_trash.append(path)
        for pattern in KEEP_PATTERNS:
            for path in sorted(student_dir.glob(pattern)):
                if path.is_file():
                    kept.append(str(path.relative_to(REPO_ROOT)))
        # Keep ham transcript when no labeled file exists
        if not labeled:
            for path in sorted(student_dir.glob("*_transcript.json")):
                if path.is_file():
                    kept.append(str(path.relative_to(REPO_ROOT)))

    if not to_trash:
        print("[trash] nothing to move")
        return 0

    moved: list[str] = []
    errors: list[dict] = []
    for path in to_trash:
        try:
            move_to_trash(path)
            moved.append(str(path.relative_to(REPO_ROOT)))
            print(f"[trash] {path.relative_to(REPO_ROOT)}")
        except OSError as exc:
            errors.append(
                {
                    "path": str(path.relative_to(REPO_ROOT)),
                    "error": str(exc).strip(),
                }
            )
            print(f"[error] {path.relative_to(REPO_ROOT)}: {exc}", file=sys.stderr)

    manifest = {
        "trashed_at": datetime.now(timezone.utc).isoformat(),
        "reason": (
            "Stale/regenerable transcript sidecars (.srt, .txt"
            + (", ham *_transcript.json when labeled exists" if args.trash_ham_when_labeled else "")
            + "). Canonical: *_transcript_labeled.json (speech) or *_transcript.json (no_speech)."
        ),
        "audio_root": str(audio_root.relative_to(REPO_ROOT)),
        "moved_to": str(Path.home() / ".Trash"),
        "moved_count": len(moved),
        "moved_files": moved,
        "kept_files_sample": kept[:10],
        "kept_count": len(kept),
        "errors": errors,
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[trash] manifest -> {log_path.relative_to(REPO_ROOT)}")
    print(f"[trash] moved {len(moved)} file(s); kept {len(kept)} canonical json file(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
