#!/usr/bin/env python3
"""Transcribe CODAP screen-recording audio with faster-whisper."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import (
    DEFAULT_AUDIO_ROOT,
    REPO_ROOT,
    analyze_audio,
    filter_segments,
    make_no_speech_payload,
    write_transcript_bundle,
)

DEFAULT_MODEL = "large-v3"
MLX_MODEL = "mlx-community/whisper-large-v3-mlx"
CODAP_INITIAL_PROMPT = (
    "Bu bir multimodal öğrenme analitiği ses kaydıdır. Öğrenci bilgisayar başında CODAP Arbor "
    "arayüzünü kullanarak karar ağacı tasarlamakta ve veri madenciliği yapmaktadır. "
    "Konuşmalar Türkçe ağırlıklıdır ancak feature, threshold, root node, confusion matrix, "
    "overfitting, underfitting, prediction ve emit gibi teknik terimler sıklıkla geçmektedir."
)
COLAB_INITIAL_PROMPT = (
    "Bu bir multimodal öğrenme analitiği ses kaydıdır. Öğrenci Google Colab üzerinde Python "
    "kodları yazmakta, veri analizi ve makine öğrenmesi çalışmaktadır. Konuşmalar Türkçe "
    "ağırlıklıdır; pandas, dataframe, sklearn, model, train, predict, feature, import, "
    "notebook ve hücre gibi terimler sıklıkla geçmektedir."
)


def repo_relative(path: Path) -> str:
    return str(path.resolve().relative_to(REPO_ROOT.resolve()))


def parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Transcribe student screen-recording audio.")
    p.add_argument("students", nargs="*", help="Student name(s); default = all with .wav")
    p.add_argument("--from", dest="from_student", metavar="NAME", help="From this student onward (A–Z)")
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument(
        "--backend",
        default="auto",
        choices=("auto", "mlx", "faster-whisper"),
        help="STT backend (auto = mlx on Apple Silicon, else faster-whisper)",
    )
    p.add_argument("--model", default=DEFAULT_MODEL, help=f"faster-whisper model (default: {DEFAULT_MODEL})")
    p.add_argument("--mlx-model", default=MLX_MODEL, help=f"mlx-whisper HF repo (default: {MLX_MODEL})")
    p.add_argument("--language", default="tr", help="Language code (default: tr)")
    p.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda", "mps"))
    p.add_argument("--compute-type", default="int8", help="CTranslate2 compute type (int8 on Apple Silicon)")
    p.add_argument(
        "--initial-prompt",
        default=CODAP_INITIAL_PROMPT,
        help="Whisper initial prompt (domain vocabulary)",
    )
    return p.parse_args(argv)


def resolve_backend(requested: str) -> str:
    if requested != "auto":
        return requested
    import platform

    if platform.machine() == "arm64" and platform.system() == "Darwin":
        try:
            import mlx_whisper  # noqa: F401

            return "mlx"
        except ImportError:
            pass
    return "faster-whisper"


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if torch.backends.mps.is_available():
            return "cpu"  # faster-whisper uses CTranslate2; MPS not supported — CPU int8 is stable
    except ImportError:
        pass
    return "cpu"


def student_dirs(audio_root: Path, args: argparse.Namespace) -> list[Path]:
    dirs = sorted(
        [d for d in audio_root.iterdir() if d.is_dir() and (d / f"{d.name}.wav").is_file()],
        key=lambda p: p.name.lower(),
    )
    if args.students:
        wanted = {s.lower() for s in args.students}
        dirs = [d for d in dirs if d.name.lower() in wanted]
    elif args.from_student:
        start = args.from_student.lower()
        dirs = [d for d in dirs if d.name.lower() >= start]
    return dirs


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def write_transcript_outputs(
    student_dir: Path,
    *,
    model_name: str,
    language: str,
    duration_seconds: float,
    segments: list[dict],
    audio_analysis: dict | None = None,
    hallucination_segments_removed: int = 0,
    status: str = "ok",
) -> Path:
    student_id = student_dir.name
    wav_path = student_dir / f"{student_id}.wav"
    payload = {
        "student_id": student_id,
        "source_audio": str(repo_relative(wav_path)),
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "language": language,
        "status": status,
        "duration_seconds": round(duration_seconds, 2),
        "segment_count": len(segments),
        "full_text": " ".join(seg["text"] for seg in segments),
        "segments": segments,
    }
    if audio_analysis:
        payload["audio_analysis"] = audio_analysis
    if hallucination_segments_removed:
        payload["qa"] = {"hallucination_segments_removed": hallucination_segments_removed}

    json_path, _, _ = write_transcript_bundle(student_dir, payload)
    print(
        f"  → {repo_relative(json_path)} "
        f"({len(segments)} segments, {duration_seconds/60:.1f} min, status={status})",
        flush=True,
    )
    return json_path


def transcribe_with_faster_whisper(
    student_dir: Path,
    *,
    model_name: str,
    language: str,
    device: str,
    compute_type: str,
    initial_prompt: str,
) -> Path:
    from faster_whisper import WhisperModel

    student_id = student_dir.name
    wav_path = student_dir / f"{student_id}.wav"

    print(f"Loading model {model_name!r} ({device}, {compute_type}) …", flush=True)
    model = WhisperModel(model_name, device=device, compute_type=compute_type)

    print(f"Transcribing {repo_relative(wav_path)} …", flush=True)
    segments_iter, info = model.transcribe(
        str(wav_path),
        language=language,
        initial_prompt=initial_prompt,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        beam_size=5,
        no_speech_threshold=0.6,
        condition_on_previous_text=False,
    )

    raw_segments: list[dict] = []
    for idx, seg in enumerate(segments_iter, 1):
        text = seg.text.strip()
        if not text:
            continue
        raw_segments.append(
            {
                "id": idx,
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "start_hms": format_timestamp(seg.start),
                "end_hms": format_timestamp(seg.end),
                "text": text,
            }
        )
        if idx % 50 == 0:
            print(f"  … {idx} segments ({seg.end:.0f}s)", flush=True)

    segments, removed = filter_segments(raw_segments)
    return write_transcript_outputs(
        student_dir,
        model_name=model_name,
        language=language,
        duration_seconds=info.duration,
        segments=segments,
        hallucination_segments_removed=removed,
    )


def transcribe_with_mlx(
    student_dir: Path,
    *,
    mlx_model: str,
    language: str,
    initial_prompt: str,
) -> Path:
    import mlx_whisper

    student_id = student_dir.name
    wav_path = student_dir / f"{student_id}.wav"

    print(f"Loading mlx model {mlx_model!r} …", flush=True)
    print(f"Transcribing {repo_relative(wav_path)} …", flush=True)
    result = mlx_whisper.transcribe(
        str(wav_path),
        path_or_hf_repo=mlx_model,
        language=language,
        initial_prompt=initial_prompt,
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        hallucination_silence_threshold=2.0,
        verbose=True,
    )

    raw_segments: list[dict] = []
    for idx, seg in enumerate(result.get("segments", []), 1):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        start = float(seg["start"])
        end = float(seg["end"])
        raw_segments.append(
            {
                "id": idx,
                "start": round(start, 2),
                "end": round(end, 2),
                "start_hms": format_timestamp(start),
                "end_hms": format_timestamp(end),
                "text": text,
            }
        )
        if idx % 50 == 0:
            print(f"  … {idx} segments ({end:.0f}s)", flush=True)

    segments, removed = filter_segments(raw_segments)
    duration_seconds = float(result.get("duration") or (segments[-1]["end"] if segments else 0.0))
    return write_transcript_outputs(
        student_dir,
        model_name=mlx_model,
        language=language,
        duration_seconds=duration_seconds,
        segments=segments,
        hallucination_segments_removed=removed,
    )


def transcribe_student(
    student_dir: Path,
    *,
    backend: str,
    model_name: str,
    mlx_model: str,
    language: str,
    device: str,
    compute_type: str,
    initial_prompt: str,
) -> Path:
    student_id = student_dir.name
    wav_path = student_dir / f"{student_id}.wav"
    audio = analyze_audio(wav_path)
    if audio.is_silent:
        print(
            f"  ! {student_id}: no speech detected in audio "
            f"(speech_fraction={audio.speech_fraction:.3f}); writing no_speech transcript",
            flush=True,
        )
        payload = make_no_speech_payload(
            student_id,
            str(repo_relative(wav_path)),
            audio,
            model=mlx_model if backend == "mlx" else model_name,
            language=language,
        )
        json_path, _, _ = write_transcript_bundle(student_dir, payload)
        return json_path

    if backend == "mlx":
        return transcribe_with_mlx(
            student_dir,
            mlx_model=mlx_model,
            language=language,
            initial_prompt=initial_prompt,
        )
    return transcribe_with_faster_whisper(
        student_dir,
        model_name=model_name,
        language=language,
        device=device,
        compute_type=compute_type,
        initial_prompt=initial_prompt,
    )


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    dirs = student_dirs(args.audio_root, args)
    if not dirs:
        print("No student audio folders found.", file=sys.stderr)
        return 1

    backend = resolve_backend(args.backend)
    device = resolve_device(args.device)
    print(f"Backend: {backend}", flush=True)
    for i, student_dir in enumerate(dirs, 1):
        print(f"[{i}/{len(dirs)}] {student_dir.name}", flush=True)
        transcribe_student(
            student_dir,
            backend=backend,
            model_name=args.model,
            mlx_model=args.mlx_model,
            language=args.language,
            device=device,
            compute_type=args.compute_type,
            initial_prompt=args.initial_prompt,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
