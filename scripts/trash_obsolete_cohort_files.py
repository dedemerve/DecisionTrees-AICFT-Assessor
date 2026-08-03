#!/usr/bin/env python3
"""Move obsolete cohort audio/transcript artifacts to macOS Trash (never rm)."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"
LOG_PATH = REPO_ROOT / "logs" / "cohort_trash_manifest.json"
TRASH_DIR = Path.home() / ".Trash"


def move_to_trash(path: Path) -> Path:
  """Move file into ~/.Trash, never delete."""
  TRASH_DIR.mkdir(exist_ok=True)
  target = TRASH_DIR / path.name
  if target.exists():
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = TRASH_DIR / f"{path.stem}_{stamp}{path.suffix}"
  path.rename(target)
  return target


def is_no_speech_hybrid(path: Path) -> bool:
  try:
    payload = json.loads(path.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return False
  return payload.get("status") == "no_speech"


def collect_candidates(audio_root: Path) -> tuple[list[Path], list[str]]:
  trash: list[Path] = []
  keep: list[str] = []

  for student_dir in sorted(audio_root.iterdir()):
    if not student_dir.is_dir():
      continue
    student_id = student_dir.name

    for path in sorted(student_dir.iterdir()):
      if not path.is_file():
        continue
      name = path.name

      # Already handled / regenerable transcript sidecars
      if name.endswith("_transcript.srt") or name.endswith("_transcript.txt"):
        trash.append(path)
        continue

      # Duplicate: segments array is inside *_hybrid_diarization.json
      if name.endswith("_hybrid_diarization_segments.json"):
        trash.append(path)
        continue

      # Pipeline intermediates
      if name.endswith("_preprocessed.wav") or name.startswith("tmp") and name.endswith(".wav"):
        trash.append(path)
        continue

      # Empty no_speech diarization stubs
      if name.endswith("_hybrid_diarization.json") and is_no_speech_hybrid(path):
        trash.append(path)
        continue

      # Canonical / keep
      if name.endswith("_transcript.json") or name.endswith("_transcript_labeled.json"):
        keep.append(str(path.relative_to(REPO_ROOT)))
        continue
      if name.endswith("_hybrid_diarization.json"):
        keep.append(str(path.relative_to(REPO_ROOT)))
        continue
      if name.endswith(".wav") or name.endswith(".m4a"):
        keep.append(str(path.relative_to(REPO_ROOT)))
        continue

    # stray temp in student folder
    for path in student_dir.glob("tmp*.wav"):
      if path.is_file() and path not in trash:
        trash.append(path)

  # root junk
  ds = audio_root / ".DS_Store"
  if ds.is_file():
    trash.append(ds)

  # de-dupe while preserving order
  seen: set[Path] = set()
  unique_trash: list[Path] = []
  for path in trash:
    resolved = path.resolve()
    if resolved not in seen and path.is_file():
      seen.add(resolved)
      unique_trash.append(path)

  return unique_trash, keep


def main() -> int:
  if not AUDIO_ROOT.is_dir():
    print(f"[error] missing audio root: {AUDIO_ROOT}", file=sys.stderr)
    return 1

  candidates, kept = collect_candidates(AUDIO_ROOT)
  if not candidates:
    print("[trash] nothing to move")
    return 0

  moved: list[dict] = []
  errors: list[dict] = []

  for path in candidates:
    rel = str(path.relative_to(REPO_ROOT))
    try:
      dest = move_to_trash(path)
      moved.append({"from": rel, "to": str(dest)})
      print(f"[trash] {rel}")
    except OSError as exc:
      errors.append({"path": rel, "error": str(exc)})
      print(f"[error] {rel}: {exc}", file=sys.stderr)

  manifest = {
    "trashed_at": datetime.now(timezone.utc).isoformat(),
    "moved_to": str(TRASH_DIR),
    "moved_count": len(moved),
    "moved_files": moved,
    "kept_count": len(kept),
    "kept_files": kept,
    "categories": {
      "transcript_sidecars": "*.srt / *.txt",
      "duplicate_diarization": "*_hybrid_diarization_segments.json",
      "pipeline_temp_audio": "*_preprocessed.wav, tmp*.wav",
      "no_speech_hybrid_stubs": "*_hybrid_diarization.json with status=no_speech",
      "system_junk": ".DS_Store",
    },
    "errors": errors,
  }
  LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  LOG_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(f"[trash] manifest -> {LOG_PATH.relative_to(REPO_ROOT)}")
  print(f"[trash] moved {len(moved)} file(s); kept {len(kept)} canonical file(s)")
  return 1 if errors else 0


if __name__ == "__main__":
  raise SystemExit(main())
