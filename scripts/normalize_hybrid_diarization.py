#!/usr/bin/env python3
"""Compact hybrid diarization JSON to v2 (timeline-only, no duplicate ASR text)."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from speaker_merge import get_hybrid_timeline
from transcript_quality import DEFAULT_AUDIO_ROOT, REPO_ROOT, format_timestamp

SCHEMA_VERSION = "hybrid_diarization_v2"
ROLE_ORDER = {"teacher": 0, "student": 1, "classmate": 2, "unknown": 3}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def speaker_rows(labeling: dict[str, Any], timeline: list[dict]) -> list[dict]:
    profiles = labeling.get("profiles") or {}
    speakers = labeling.get("speakers") or []
    seg_counts = Counter(str(s.get("speaker_id")) for s in timeline if s.get("speaker_id"))

    rows: list[dict] = []
    if speakers:
        for row in speakers:
            sid = row.get("speaker_id")
            if not sid:
                continue
            rows.append(
                {
                    "speaker_id": sid,
                    "role": row.get("role", "classmate"),
                    "confidence": round(float(row.get("confidence", 0.5)), 3),
                    "duration_seconds": round(float(row.get("duration_seconds", 0.0)), 2),
                    "segment_count": int(row.get("segment_count", seg_counts.get(sid, 0))),
                }
            )
    else:
        for sid, profile in profiles.items():
            rows.append(
                {
                    "speaker_id": sid,
                    "role": profile.get("resolved_role", "classmate"),
                    "confidence": round(float(profile.get("role_confidence", 0.5)), 3),
                    "duration_seconds": round(float(profile.get("total_duration", 0.0)), 2),
                    "segment_count": seg_counts.get(sid, 0),
                }
            )

    rows.sort(
        key=lambda r: (
            ROLE_ORDER.get(str(r.get("role")), 9),
            -float(r.get("duration_seconds", 0.0)),
            str(r.get("speaker_id")),
        )
    )
    return rows


def compact_timeline(raw_segments: list[dict]) -> list[dict]:
    out: list[dict] = []
    for seg in sorted(raw_segments, key=lambda s: float(s["start"])):
        start = round(float(seg["start"]), 3)
        end = round(float(seg["end"]), 3)
        speaker_id = seg.get("speaker_id")
        if not speaker_id:
            continue
        out.append(
            {
                "start": start,
                "end": end,
                "start_hms": seg.get("start_hms") or format_timestamp(start),
                "end_hms": seg.get("end_hms") or format_timestamp(end),
                "speaker_id": str(speaker_id),
            }
        )
    return out


def build_v2_hybrid_payload(
    *,
    student_id: str,
    source_audio: str,
    processed_at: str,
    status: str,
    duration_seconds: float,
    whisper_model: str,
    diarization_method: str,
    language: str,
    preprocess: dict[str, Any],
    teacher_speaker: str | None,
    focal_student_speaker: str | None,
    role_counts: dict[str, int],
    speaker_profiles: list[dict],
    timeline: list[dict],
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "description": (
            "Kim ne zaman konuştu (diarizasyon zaman çizelgesi). "
            "Metin için *_transcript_labeled.json kullanın; bu dosya yalnızca konuşmacı kümesi ve zaman damgalarını tutar."
        ),
        "student_id": student_id,
        "source_audio": source_audio,
        "processed_at": processed_at,
        "status": status,
        "duration_seconds": round(duration_seconds, 2),
        "pipeline": {
            "diarization": diarization_method,
            "asr": whisper_model,
            "language": language,
            "preprocess": preprocess,
        },
        "speaker_labeling": {
            "method": "hybrid_matrix_duration_and_lexical",
            "teacher_speaker": teacher_speaker,
            "focal_student_speaker": focal_student_speaker,
            "role_counts": role_counts,
            "speakers": speaker_profiles,
        },
        "timeline": timeline,
        "timeline_segment_count": len(timeline),
    }


def normalize_payload(hybrid: dict[str, Any]) -> dict[str, Any]:
    if hybrid.get("schema_version") == SCHEMA_VERSION:
        return hybrid

    labeling = hybrid.get("speaker_labeling") or {}
    model = hybrid.get("model") or {}
    preprocess = hybrid.get("preprocess") or {}
    timeline = compact_timeline(get_hybrid_timeline(hybrid))
    speakers = speaker_rows(labeling, timeline)

    role_counts = labeling.get("role_counts")
    if not role_counts:
        sid_role = {r["speaker_id"]: r["role"] for r in speakers}
        role_counts = dict(Counter(sid_role.get(s["speaker_id"], "classmate") for s in timeline))

    pipeline = hybrid.get("pipeline")
    if isinstance(pipeline, dict):
        diarization_method = pipeline.get("diarization", "unknown")
        asr_model = pipeline.get("asr", model.get("whisper", "unknown"))
        language = pipeline.get("language", model.get("language", "tr"))
    else:
        diarization_method = model.get("diarization", "unknown")
        asr_model = model.get("whisper", "unknown")
        language = model.get("language", "tr")

    return build_v2_hybrid_payload(
        student_id=hybrid.get("student_id"),
        source_audio=hybrid.get("source_audio"),
        processed_at=hybrid.get("processed_at") or datetime.now(timezone.utc).isoformat(),
        status=hybrid.get("status", "ok"),
        duration_seconds=float(hybrid.get("duration_seconds") or 0.0),
        whisper_model=asr_model,
        diarization_method=diarization_method,
        language=language,
        preprocess={
            "noise_reduction": preprocess.get("noise_reduction", "noisereduce_stationary"),
            "speech_fraction": preprocess.get("speech_fraction_rms") or preprocess.get("speech_fraction"),
        },
        teacher_speaker=labeling.get("teacher_speaker"),
        focal_student_speaker=labeling.get("focal_student_speaker"),
        role_counts=role_counts,
        speaker_profiles=speakers,
        timeline=timeline,
    )


def normalize_file(path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    before_bytes = path.stat().st_size
    hybrid = load_json(path)
    normalized = normalize_payload(hybrid)
    after_bytes = len(json.dumps(normalized, indent=2, ensure_ascii=False).encode("utf-8"))
    if not dry_run and hybrid.get("schema_version") != SCHEMA_VERSION:
        path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return {
        "path": str(path.relative_to(REPO_ROOT)),
        "before_bytes": before_bytes,
        "after_bytes": after_bytes,
        "timeline_segments": len(normalized.get("timeline") or []),
        "speaker_count": len((normalized.get("speaker_labeling") or {}).get("speakers") or []),
        "changed": hybrid.get("schema_version") != SCHEMA_VERSION,
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Normalize hybrid diarization JSON to compact v2.")
    p.add_argument("students", nargs="*", help="Student IDs (default: all with hybrid file)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    audio_root = args.audio_root.resolve()
    if args.students:
        paths = [audio_root / s / f"{s}_hybrid_diarization.json" for s in args.students]
    else:
        paths = sorted(audio_root.glob("*/*_hybrid_diarization.json"))

    rows: list[dict] = []
    for path in paths:
        if not path.is_file():
            print(f"[skip] missing {path.name}", file=sys.stderr)
            continue
        row = normalize_file(path, dry_run=args.dry_run)
        rows.append(row)
        tag = "dry" if args.dry_run else ("ok" if row["changed"] else "unchanged")
        print(
            f"[{tag}] {row['path']}: {row['before_bytes']:,} -> {row['after_bytes']:,} bytes | "
            f"{row['timeline_segments']} slices, {row['speaker_count']} speakers"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
