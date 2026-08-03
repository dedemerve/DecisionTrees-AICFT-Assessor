#!/usr/bin/env python3
"""Audit and finalize May Colab Python screen-recording cohort artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import REPO_ROOT, analyze_audio, ffprobe_duration

COHORT_ID = "colab_may_2026"
SOURCE_DIR = REPO_ROOT / "data_sources_2026" / "05 May Colab Python Screen Recordings"
AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "colab_may_audio"

RECORDING_CONTEXT = {
    "cohort_id": COHORT_ID,
    "activity": "Google Colab Python",
    "session_date": "2026-05",
    "source_dir": "data_sources_2026/05 May Colab Python Screen Recordings",
    "audio_root": "data_sources_2026/colab_may_audio",
}


def probe_video_duration(path: Path) -> float | None:
    if not path.is_file():
        return None
    try:
        out = subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            text=True,
        ).strip()
        return round(float(out), 2)
    except (subprocess.CalledProcessError, ValueError):
        return None


def file_sha256_prefix(path: Path, nbytes: int = 1_000_000) -> str | None:
    if not path.is_file():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        h.update(f.read(nbytes))
    return h.hexdigest()[:16]


def ensure_shana_placeholder() -> dict:
    student_dir = AUDIO_ROOT / "Shana"
    student_dir.mkdir(parents=True, exist_ok=True)
    src = SOURCE_DIR / "Shana.webm"
    link = student_dir / "Shana.webm"
    if not link.exists() and src.is_file():
        link.symlink_to(src.resolve())

    payload = {
        "student_id": "Shana",
        "status": "extraction_failed",
        "source_video": str(src.relative_to(REPO_ROOT)) if src.is_file() else None,
        "error": "corrupt_or_invalid_webm",
        "detail": "EBML/WebM header missing; ffmpeg cannot decode. File type shows raw data, not video/webm.",
        "source_bytes": src.stat().st_size if src.is_file() else None,
        "sha256_prefix_first_1mb": file_sha256_prefix(src),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "action_required": "Re-upload valid Shana.webm screen recording from backup or student device.",
    }
    out = student_dir / "Shana_extraction_error.json"
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Stub so validation reports extraction_failed instead of missing_files
    stub = {
        "student_id": "Shana",
        "status": "no_speech",
        "speech_status": "extraction_failed",
        "speech_status_note": payload["detail"],
        "segment_count": 0,
        "segments": [],
        "full_text": "",
        "recording_context": {**RECORDING_CONTEXT, "student_id": "Shana", "pipeline_status": "extraction_failed"},
    }
    (student_dir / "Shana_transcript.json").write_text(
        json.dumps(stub, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def patch_transcript_metadata(student_dir: Path, audio_flags: dict) -> dict:
    student_id = student_dir.name
    transcript_path = student_dir / f"{student_id}_transcript.json"
    labeled_path = student_dir / f"{student_id}_transcript_labeled.json"
    changes: list[str] = []

    for path in (transcript_path, labeled_path):
        if not path.is_file():
            continue
        data = json.loads(path.read_text(encoding="utf-8"))
        before = json.dumps(data.get("recording_context"), sort_keys=True)
        ctx = dict(RECORDING_CONTEXT)
        ctx["student_id"] = student_id
        ctx.update(audio_flags)
        data["recording_context"] = ctx
        if path == labeled_path and "speaker_labeling" in data:
            data["speaker_labeling"]["cohort_id"] = COHORT_ID
        after = json.dumps(data.get("recording_context"), sort_keys=True)
        if before != after:
            path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            changes.append(path.name)

    return {"student_id": student_id, "patched_files": changes}


def audit_student(student_dir: Path) -> dict:
    student_id = student_dir.name
    wav = student_dir / f"{student_id}.wav"
    video = student_dir / f"{student_id}.video.webm"
    transcript = student_dir / f"{student_id}_transcript.json"
    labeled = student_dir / f"{student_id}_transcript_labeled.json"
    hybrid = student_dir / f"{student_id}_hybrid_diarization.json"
    webm_link = student_dir / f"{student_id}.webm"

    if student_id == "Shana" and not wav.is_file():
        err_path = student_dir / f"{student_id}_extraction_error.json"
        err = json.loads(err_path.read_text(encoding="utf-8")) if err_path.is_file() else {}
        return {
            "student_id": student_id,
            "pipeline_status": "extraction_failed",
            "error": err.get("error"),
            "files": {"extraction_error": err_path.is_file()},
        }

    row: dict = {
        "student_id": student_id,
        "has_wav": wav.is_file(),
        "has_m4a": (student_dir / f"{student_id}.m4a").is_file(),
        "has_video": video.is_file(),
        "has_webm_link": webm_link.is_symlink() or webm_link.is_file(),
        "has_transcript": transcript.is_file(),
        "has_labeled": labeled.is_file(),
        "has_hybrid": hybrid.is_file(),
    }

    if wav.is_file():
        audio = analyze_audio(wav)
        wav_dur = ffprobe_duration(wav) or 0.0
        vid_dur = probe_video_duration(video) or probe_video_duration(webm_link)
        row["audio_duration_min"] = round(wav_dur / 60, 1)
        row["video_duration_min"] = round(vid_dur / 60, 1) if vid_dur else None
        row["speech_fraction"] = round(audio.speech_fraction, 4)
        row["mean_volume_db"] = audio.mean_volume_db
        row["is_silent"] = audio.is_silent
        if vid_dur and wav_dur and vid_dur > wav_dur * 1.5:
            row["audio_track_issue"] = "truncated_or_missing"
            row["audio_track_note"] = (
                f"Video ~{vid_dur/60:.0f} dk; çıkarılan ses izi ~{wav_dur/60:.1f} dk — "
                "kayıt sırasında ses yakalanmamış veya ses izi kesilmiş."
            )

    if transcript.is_file():
        t = json.loads(transcript.read_text(encoding="utf-8"))
        row["transcript_status"] = t.get("status")
        row["segment_count"] = len(t.get("segments") or [])
        row["speech_status"] = t.get("speech_status")
    elif labeled.is_file():
        t = json.loads(labeled.read_text(encoding="utf-8"))
        row["transcript_status"] = t.get("status", "ok")
        row["segment_count"] = len(t.get("segments") or [])
        row["speech_status"] = t.get("speech_status")

    if labeled.is_file():
        l = json.loads(labeled.read_text(encoding="utf-8"))
        sl = l.get("speaker_labeling") or {}
        row["labeled_segments"] = len(l.get("segments") or [])
        row["role_counts"] = sl.get("role_counts")
        row["needs_review_count"] = sl.get("needs_review_count")

    if row.get("transcript_status") == "ok" and row.get("has_labeled"):
        row["pipeline_status"] = "complete"
        row["canonical_transcript"] = f"{student_id}_transcript_labeled.json"
    elif row.get("transcript_status") == "no_speech":
        row["pipeline_status"] = "no_speech"
        row["canonical_transcript"] = f"{student_id}_transcript.json"
    elif row.get("transcript_status") == "ok":
        row["pipeline_status"] = "transcribed_unlabeled"
        row["canonical_transcript"] = f"{student_id}_transcript.json"
    else:
        row["pipeline_status"] = "incomplete"

    # Required file checks
    required_speech = ["wav", "m4a", "video", "webm_link", "labeled", "hybrid"]
    required_silent = ["wav", "m4a", "video", "webm_link", "transcript"]
    if row.get("pipeline_status") == "complete" and not row.get("has_transcript"):
        # Ham mlx transcript optional when labeled canonical file exists.
        pass
    elif row.get("pipeline_status") == "no_speech" and not row.get("has_transcript"):
        row["pipeline_status"] = "incomplete"
    req = required_speech if row.get("pipeline_status") == "complete" else required_silent
    missing = [k for k in req if not row.get(f"has_{k}")]
    if missing:
        row["missing_artifacts"] = missing

    return row


def rebuild_manifest(students: list[dict]) -> None:
    recordings = []
    errors = []
    for row in students:
        if row.get("pipeline_status") == "extraction_failed":
            errors.append(
                {
                    "student_id": row["student_id"],
                    "source_video": "Shana.webm",
                    "error": row.get("error", "extraction_failed"),
                }
            )
            continue
        sid = row["student_id"]
        sd = AUDIO_ROOT / sid
        recordings.append(
            {
                "student_id": sid,
                "source_video": f"{sid}.webm",
                "source_link": str((sd / f"{sid}.webm").relative_to(REPO_ROOT))
                if (sd / f"{sid}.webm").exists()
                else None,
                "duration_seconds": ffprobe_duration(sd / f"{sid}.wav"),
                "video_duration_seconds": probe_video_duration(sd / f"{sid}.video.webm"),
                "wav": str((sd / f"{sid}.wav").relative_to(REPO_ROOT)),
                "m4a": str((sd / f"{sid}.m4a").relative_to(REPO_ROOT)),
                "video": str((sd / f"{sid}.video.webm").relative_to(REPO_ROOT)),
                "pipeline_status": row.get("pipeline_status"),
                "transcript_status": row.get("transcript_status"),
                "canonical_transcript": row.get("canonical_transcript"),
                "speech_fraction": row.get("speech_fraction"),
                "audio_track_issue": row.get("audio_track_issue"),
            }
        )

    manifest = {
        "finalized_at": datetime.now(timezone.utc).isoformat(),
        "cohort_id": COHORT_ID,
        "source_dir": str(SOURCE_DIR.relative_to(REPO_ROOT)),
        "output_dir": str(AUDIO_ROOT.relative_to(REPO_ROOT)),
        "layout": "per student: .wav, .m4a, .video.webm, symlink .webm, transcript JSON",
        "recordings": recordings,
        "errors": errors,
        "summary": {
            "total_source_students": 11,
            "extracted_ok": len(recordings),
            "extraction_failed": len(errors),
            "speech_complete": sum(1 for r in students if r.get("pipeline_status") == "complete"),
            "no_speech": sum(1 for r in students if r.get("pipeline_status") == "no_speech"),
        },
    }
    (AUDIO_ROOT / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_readme(students: list[dict]) -> None:
    speech = [r for r in students if r.get("pipeline_status") == "complete"]
    silent = [r for r in students if r.get("pipeline_status") == "no_speech"]
    failed = [r for r in students if r.get("pipeline_status") == "extraction_failed"]
    lines = [
        "# colab_may_audio — May 2026 Colab Python cohort",
        "",
        "Processed artifacts from `05 May Colab Python Screen Recordings/`.",
        "",
        "## Canonical transcripts",
        "",
        "| Durum | Öğrenciler | Dosya |",
        "|-------|------------|-------|",
        f"| Konuşma + speaker labels | {', '.join(r['student_id'] for r in speech) or '—'} | `*_transcript_labeled.json` |",
        f"| Sessiz kayıt | {', '.join(r['student_id'] for r in silent) or '—'} | `*_transcript.json` (`no_speech`) |",
        f"| Çıkarma hatası | {', '.join(r['student_id'] for r in failed) or '—'} | `*_extraction_error.json` |",
        "",
        "## Per-student layout",
        "",
        "- `{Student}/{Student}.wav` — 16 kHz mono (STT)",
        "- `{Student}/{Student}.m4a` — AAC copy",
        "- `{Student}/{Student}.video.webm` — video-only (ses ayrılmış)",
        "- `{Student}/{Student}.webm` — symlink to source recording",
        "",
        "## Reports",
        "",
        "- `manifest.json` — extraction + pipeline status",
        "- `transcript_validation_report.json` — QA validation",
        "- `pipeline_status.json` — cohort audit snapshot",
        "",
        "## Regenerate",
        "",
        "```bash",
        "./scripts/run_colab_may_pipeline.sh          # full pipeline",
        "./scripts/run_colab_may_pipeline.sh Shana      # single student (after fix)",
        "python scripts/finalize_colab_may_cohort.py    # audit + metadata patch",
        "```",
        "",
    ]
    (AUDIO_ROOT / "README.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Finalize May Colab cohort artifacts.")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    ensure_shana_placeholder()

    students: list[dict] = []
    patches: list[dict] = []
    for student_dir in sorted(AUDIO_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not student_dir.is_dir():
            continue
        row = audit_student(student_dir)
        students.append(row)
        audio_flags = {
            k: row[k]
            for k in (
                "speech_fraction",
                "mean_volume_db",
                "is_silent",
                "audio_track_issue",
                "audio_track_note",
                "pipeline_status",
            )
            if k in row
        }
        patches.append(patch_transcript_metadata(student_dir, audio_flags))

    rebuild_manifest(students)
    write_readme(students)

    status_path = AUDIO_ROOT / "pipeline_status.json"
    status_path.write_text(
        json.dumps(
            {
                "audited_at": datetime.now(timezone.utc).isoformat(),
                "cohort_id": COHORT_ID,
                "students": students,
                "metadata_patches": patches,
                "summary": {
                    "complete": sum(1 for s in students if s.get("pipeline_status") == "complete"),
                    "no_speech": sum(1 for s in students if s.get("pipeline_status") == "no_speech"),
                    "extraction_failed": sum(
                        1 for s in students if s.get("pipeline_status") == "extraction_failed"
                    ),
                    "incomplete": sum(
                        1 for s in students if s.get("pipeline_status") not in {
                            "complete",
                            "no_speech",
                            "extraction_failed",
                        }
                    ),
                },
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    if not args.skip_validate:
        subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "validate_screen_recording_transcripts.py"),
                "--audio-root",
                str(AUDIO_ROOT),
                "--report",
                str(AUDIO_ROOT / "transcript_validation_report.json"),
            ],
            check=False,
        )

    print(f"[finalize] pipeline_status -> {status_path.relative_to(REPO_ROOT)}")
    for row in students:
        print(
            f"  {row['student_id']:<8} {row.get('pipeline_status','?'):<20} "
            f"segs={row.get('segment_count', row.get('labeled_segments', '-'))}"
        )
    issues = [s for s in students if s.get("missing_artifacts") or s.get("pipeline_status") == "incomplete"]
    if issues:
        print(f"[finalize] {len(issues)} student(s) need attention", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
