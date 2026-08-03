#!/usr/bin/env python3
"""Hybrid local diarization for single-channel classroom screen recordings.

Five-layer pipeline:
  1. RMS silence gate + stationary noise reduction (noisereduce)
  2. WhisperX ASR + phoneme alignment (word-level timestamps)
  3. Speaker clustering (WhisperX DiarizationPipeline, token-free community model
     with optional local config, else spectral clustering fallback)
  4. Hybrid matrix role assignment (duration + lexical hooks + dialogue bridges)
  5. JSON output with globally resolved teacher / student / classmate roles

Dependencies (install once, fully local after model cache):
  pip install whisperx noisereduce librosa soundfile numpy pandas scikit-learn torch

Optional offline diarization (no HuggingFace token at runtime):
  Download pyannote community diarization assets and pass --diarization-config
  path/to/config.yaml with local model paths (see WhisperX / pyannote offline FAQ).

Usage:
  python scripts/hybrid_diarization.py Amy
  python scripts/hybrid_diarization.py --audio-root data_sources_2026/codap_arbor_21april_audio Amy Bruno
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from transcript_quality import (
    DEFAULT_AUDIO_ROOT,
    REPO_ROOT,
    filter_segments,
    format_timestamp,
    make_no_speech_payload,
)

LOGGER = logging.getLogger("hybrid_diarization")

# --- Audio pre-processing ----------------------------------------------------

TARGET_SAMPLE_RATE = 16_000
FRAME_LENGTH = 2048
HOP_LENGTH = 512
RMS_SILENCE_THRESHOLD = 0.004  # ~ -48 dBFS; catches Iris/Zara-style silent captures
MIN_SPEECH_FRACTION_RMS = 0.02
NOISE_REDUCE_PROP = 0.75

# --- WhisperX ----------------------------------------------------------------

DEFAULT_WHISPER_MODEL = "large-v3"
CODAP_INITIAL_PROMPT = (
    "Bu bir multimodal öğrenme analitiği ses kaydıdır. Öğrenci bilgisayar başında CODAP Arbor "
    "arayüzünü kullanarak karar ağacı tasarlamakta ve veri madenciliği yapmaktadır. "
    "Konuşmalar Türkçe ağırlıklıdır ancak feature, threshold, root node, confusion matrix, "
    "overfitting, underfitting, prediction ve emit gibi teknik terimler sıklıkla geçmektedir."
)
DEFAULT_DIARIZATION_MODEL = "pyannote/speaker-diarization-community-1"

# --- Hybrid role matrix ------------------------------------------------------

WEIGHT_DURATION = 0.40
WEIGHT_KEYWORDS = 0.40
WEIGHT_BRIDGES = 0.20

TEACHER_HOOKS = [
    re.compile(p, re.I)
    for p in [
        r"\barkadaşlar\b",
        r"\bşimdi\b",
        r"\bsoru\b",
        r"\bbakalım\b",
        r"\bödev\b",
        r"\bekran\b",
        r"\bgeçelim\b",
        r"\bsevgili arkadaşlar\b",
        r"\bbirinci soru\b",
        r"\bikinci soru\b",
        r"\bherkes\b",
        r"\btamam mı\b",
    ]
]

STUDENT_HOOKS = [
    re.compile(p, re.I)
    for p in [
        r"\bhocam\b",
        r"\bben\b",
        r"\byapamadım\b",
        r"\bçalışmıyor\b",
        r"\bbende\b",
        r"\bsilmeli\b",
        r"\byapamad",
        r"\banlamadım\b",
        r"\befendim\b",
        r"\bevet hocam\b",
    ]
]

BACKCHANNEL_PATTERN = re.compile(r"^(evet|tamam|hayır|ok|haa|hı|hıh|aa)\.?$", re.I)
LONG_TURN_SECONDS = 90.0
BRIDGE_MAX_SECONDS = 4.0
BRIDGE_MAX_WORDS = 6


@dataclass
class PreprocessResult:
    audio: np.ndarray
    sample_rate: int
    duration_seconds: float
    speech_fraction: float
    mean_rms: float
    denoised_path: Path | None
    is_silent: bool


@dataclass
class SpeakerProfile:
    speaker_id: str
    total_duration: float = 0.0
    teacher_hits: int = 0
    student_hits: int = 0
    bridge_student_score: float = 0.0
    segment_count: int = 0
    teacher_vote: float = 0.0
    student_vote: float = 0.0
    resolved_role: str = "classmate"
    role_confidence: float = 0.0


@dataclass
class HybridMatrixResult:
    profiles: dict[str, SpeakerProfile]
    teacher_speaker: str
    focal_student_speaker: str | None
    role_map: dict[str, str]
    confidence_map: dict[str, float]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Hybrid WhisperX + lexical diarization for classroom recordings.",
    )
    p.add_argument(
        "targets",
        nargs="*",
        help="Student ID(s) or path(s) to student folder / .wav file",
    )
    p.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    p.add_argument("--whisper-model", default=DEFAULT_WHISPER_MODEL)
    p.add_argument("--language", default="tr")
    p.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    p.add_argument("--compute-type", default="int8", help="WhisperX compute type (int8 on CPU/MPS hosts)")
    p.add_argument("--batch-size", type=int, default=8)
    p.add_argument(
        "--diarization-model",
        default=DEFAULT_DIARIZATION_MODEL,
        help="WhisperX/pyannote diarization model or local config.yaml path",
    )
    p.add_argument(
        "--diarization-config",
        type=Path,
        default=None,
        help="Local pyannote config.yaml (offline, no HF token at runtime)",
    )
    p.add_argument("--hf-token", default=os.environ.get("HF_TOKEN"))
    p.add_argument("--min-speakers", type=int, default=2)
    p.add_argument("--max-speakers", type=int, default=8)
    p.add_argument("--keep-preprocessed", action="store_true", help="Keep denoised WAV on disk")
    p.add_argument("--output-suffix", default="_hybrid_diarization")
    p.add_argument("--skip-existing", action="store_true", help="Skip students with existing hybrid output")
    p.add_argument(
        "--fuse-existing-transcript",
        action="store_true",
        help="Bind local diarization to existing *_transcript(_labeled).json timestamps/text (skip WhisperX ASR)",
    )
    p.add_argument(
        "--local-diarization-only",
        action="store_true",
        help="Force MFCC + agglomerative clustering fallback (no pyannote / WhisperX diarization)",
    )
    p.add_argument("-v", "--verbose", action="store_true")
    return p.parse_args(argv)


def repo_relative_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return str(resolved.relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(resolved)


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s [%(levelname)s] %(message)s")
    for noisy in ("numba", "matplotlib", "torio", "pyannote", "speechbrain", "fsspec"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def resolve_device(requested: str) -> str:
    if requested != "auto":
        return requested
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
    except ImportError:
        pass
    return "cpu"


def resolve_audio_path(target: str, audio_root: Path) -> tuple[Path, str]:
    path = Path(target)
    if path.is_file() and path.suffix.lower() == ".wav":
        return path, path.stem.split("_")[0] if "_" in path.stem else path.stem
    if path.is_dir():
        student_id = path.name
        wav = path / f"{student_id}.wav"
        if wav.is_file():
            return wav, student_id
        raise FileNotFoundError(f"No WAV in directory: {path}")
    student_id = path.name
    wav = audio_root / student_id / f"{student_id}.wav"
    if wav.is_file():
        return wav, student_id
    raise FileNotFoundError(f"WAV not found for target {target!r} -> {wav}")


def resolve_targets(args: argparse.Namespace) -> list[tuple[Path, str]]:
    if not args.targets:
        pairs: list[tuple[Path, str]] = []
        for student_dir in sorted(args.audio_root.iterdir(), key=lambda p: p.name.lower()):
            if not student_dir.is_dir():
                continue
            wav = student_dir / f"{student_dir.name}.wav"
            if wav.is_file():
                pairs.append((wav, student_dir.name))
        return pairs
    return [resolve_audio_path(t, args.audio_root) for t in args.targets]


def load_audio_mono(path: Path, sample_rate: int = TARGET_SAMPLE_RATE) -> tuple[np.ndarray, int]:
    import librosa

    audio, sr = librosa.load(str(path), sr=sample_rate, mono=True)
    return audio.astype(np.float32), sr


def compute_rms_profile(audio: np.ndarray, frame_length: int = FRAME_LENGTH, hop_length: int = HOP_LENGTH) -> np.ndarray:
    import librosa

    return librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]


def preprocess_audio(
    wav_path: Path,
    *,
    keep_preprocessed: bool,
    student_dir: Path,
) -> PreprocessResult:
    import noisereduce as nr

    audio, sr = load_audio_mono(wav_path)
    duration = len(audio) / sr if sr else 0.0
    rms = compute_rms_profile(audio)
    speech_frames = rms > RMS_SILENCE_THRESHOLD
    speech_fraction = float(np.mean(speech_frames)) if len(rms) else 0.0
    mean_rms = float(np.mean(rms)) if len(rms) else 0.0
    is_silent = speech_fraction < MIN_SPEECH_FRACTION_RMS or mean_rms < RMS_SILENCE_THRESHOLD / 2

    if is_silent:
        LOGGER.info(
            "%s: silent capture (speech_fraction=%.4f mean_rms=%.5f) — skipping heavy models",
            wav_path.name,
            speech_fraction,
            mean_rms,
        )
        return PreprocessResult(
            audio=audio,
            sample_rate=sr,
            duration_seconds=duration,
            speech_fraction=speech_fraction,
            mean_rms=mean_rms,
            denoised_path=None,
            is_silent=True,
        )

    LOGGER.info("%s: applying stationary noise reduction", wav_path.name)
    denoised = nr.reduce_noise(y=audio, sr=sr, stationary=True, prop_decrease=NOISE_REDUCE_PROP)

    denoised_path: Path | None
    if keep_preprocessed:
        denoised_path = student_dir / f"{student_dir.name}_preprocessed.wav"
        import soundfile as sf

        sf.write(str(denoised_path), denoised, sr, subtype="PCM_16")
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False, dir=student_dir)
        denoised_path = Path(tmp.name)
        tmp.close()
        import soundfile as sf

        sf.write(str(denoised_path), denoised, sr, subtype="PCM_16")

    return PreprocessResult(
        audio=denoised,
        sample_rate=sr,
        duration_seconds=duration,
        speech_fraction=speech_fraction,
        mean_rms=mean_rms,
        denoised_path=denoised_path,
        is_silent=False,
    )


def count_hooks(text: str, patterns: list[re.Pattern]) -> int:
    return sum(len(p.findall(text)) for p in patterns)


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def build_speaker_profiles(segments: list[dict]) -> dict[str, SpeakerProfile]:
    profiles: dict[str, SpeakerProfile] = {}
    ordered = sorted(segments, key=lambda s: float(s["start"]))

    for seg in ordered:
        speaker = str(seg.get("speaker") or seg.get("speaker_id") or "SPEAKER_UNKNOWN")
        if speaker not in profiles:
            profiles[speaker] = SpeakerProfile(speaker_id=speaker)
        profile = profiles[speaker]
        start, end = float(seg["start"]), float(seg["end"])
        duration = max(0.0, end - start)
        text = str(seg.get("text", ""))

        profile.total_duration += duration
        profile.segment_count += 1
        profile.teacher_hits += count_hooks(text, TEACHER_HOOKS)
        profile.student_hits += count_hooks(text, STUDENT_HOOKS)

    for idx, seg in enumerate(ordered):
        if idx == 0:
            continue
        prev = ordered[idx - 1]
        prev_dur = float(prev["end"]) - float(prev["start"])
        cur_dur = float(seg["end"]) - float(seg["start"])
        cur_text = str(seg.get("text", "")).strip()
        prev_sp = str(prev.get("speaker") or prev.get("speaker_id") or "")
        cur_sp = str(seg.get("speaker") or seg.get("speaker_id") or "")

        if (
            prev_sp
            and cur_sp
            and prev_sp != cur_sp
            and prev_dur >= LONG_TURN_SECONDS
            and cur_dur <= BRIDGE_MAX_SECONDS
            and word_count(cur_text) <= BRIDGE_MAX_WORDS
            and (BACKCHANNEL_PATTERN.match(cur_text) or count_hooks(cur_text, STUDENT_HOOKS) > 0)
        ):
            if cur_sp in profiles:
                profiles[cur_sp].bridge_student_score += 1.0 + (LONG_TURN_SECONDS / max(prev_dur, 1.0))

    return profiles


def _normalize_map(values: dict[str, float]) -> dict[str, float]:
    if not values:
        return {}
    max_val = max(values.values())
    if max_val <= 0:
        return {k: 0.0 for k in values}
    return {k: v / max_val for k, v in values.items()}


def compute_hybrid_role_matrix(profiles: dict[str, SpeakerProfile]) -> HybridMatrixResult:
    if not profiles:
        raise ValueError("No speaker profiles to score")

    duration_norm = _normalize_map({sid: p.total_duration for sid, p in profiles.items()})
    teacher_kw_norm = _normalize_map({sid: float(p.teacher_hits) for sid, p in profiles.items()})
    student_kw_norm = _normalize_map({sid: float(p.student_hits) for sid, p in profiles.items()})
    bridge_norm = _normalize_map({sid: p.bridge_student_score for sid, p in profiles.items()})

    for sid, profile in profiles.items():
        anti_bridge = 1.0 - bridge_norm.get(sid, 0.0)
        profile.teacher_vote = (
            WEIGHT_DURATION * duration_norm.get(sid, 0.0)
            + WEIGHT_KEYWORDS * teacher_kw_norm.get(sid, 0.0)
            + WEIGHT_BRIDGES * anti_bridge
        )
        profile.student_vote = (
            WEIGHT_DURATION * (1.0 - duration_norm.get(sid, 0.0))
            + WEIGHT_KEYWORDS * student_kw_norm.get(sid, 0.0)
            + WEIGHT_BRIDGES * bridge_norm.get(sid, 0.0)
        )

    teacher_speaker = max(profiles, key=lambda sid: profiles[sid].teacher_vote)
    remaining = [sid for sid in profiles if sid != teacher_speaker]
    focal_student = max(remaining, key=lambda sid: profiles[sid].student_vote) if remaining else None

    role_map: dict[str, str] = {}
    confidence_map: dict[str, float] = {}

    for sid, profile in profiles.items():
        if sid == teacher_speaker:
            profile.resolved_role = "teacher"
            profile.role_confidence = min(0.98, 0.55 + profile.teacher_vote * 0.45)
        elif sid == focal_student:
            profile.resolved_role = "student"
            profile.role_confidence = min(0.95, 0.50 + profile.student_vote * 0.45)
        else:
            profile.resolved_role = "classmate"
            profile.role_confidence = min(0.75, 0.35 + max(profile.teacher_vote, profile.student_vote) * 0.25)
        role_map[sid] = profile.resolved_role
        confidence_map[sid] = round(profile.role_confidence, 2)

    return HybridMatrixResult(
        profiles=profiles,
        teacher_speaker=teacher_speaker,
        focal_student_speaker=focal_student,
        role_map=role_map,
        confidence_map=confidence_map,
    )


def whisperx_transcribe_and_align(
    audio_path: Path,
    *,
    model_name: str,
    language: str,
    device: str,
    compute_type: str,
    batch_size: int,
) -> dict[str, Any]:
    import whisperx

    LOGGER.info("Loading WhisperX model %s on %s", model_name, device)
    model = whisperx.load_model(model_name, device=device, compute_type=compute_type, language=language)

    audio = whisperx.load_audio(str(audio_path))
    LOGGER.info("Transcribing %s", audio_path.name)
    result = model.transcribe(
        audio,
        batch_size=batch_size,
        language=language,
    )

    align_model, metadata = whisperx.load_align_model(language_code=language, device=device)
    LOGGER.info("Aligning word-level timestamps")
    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device,
        return_char_alignments=False,
    )
    return aligned


def init_diarization_pipeline(
    *,
    device: str,
    diarization_model: str,
    diarization_config: Path | None,
    hf_token: str | None,
):
    from whisperx.diarize import DiarizationPipeline

    model_ref = str(diarization_config) if diarization_config else diarization_model
    token = None if diarization_config else hf_token
    LOGGER.info("Loading diarization pipeline: %s (token=%s)", model_ref, "set" if token else "none")
    return DiarizationPipeline(model_name=model_ref, token=token, device=device)


def local_spectral_diarization(
    audio: np.ndarray,
    sample_rate: int,
    *,
    min_speakers: int,
    max_speakers: int,
) -> "Any":
    """Token-free fallback: energy VAD slices + MFCC clustering."""
    import librosa
    import pandas as pd
    from sklearn.cluster import AgglomerativeClustering

    intervals = librosa.effects.split(audio, top_db=28)
    if len(intervals) == 0:
        return pd.DataFrame(columns=["start", "end", "speaker"])

    embeddings: list[np.ndarray] = []
    meta: list[tuple[float, float]] = []
    for start_idx, end_idx in intervals:
        if end_idx - start_idx < sample_rate * 0.35:
            continue
        chunk = audio[start_idx:end_idx]
        mfcc = librosa.feature.mfcc(y=chunk, sr=sample_rate, n_mfcc=20)
        embeddings.append(np.mean(mfcc, axis=1))
        meta.append((start_idx / sample_rate, end_idx / sample_rate))

    if not embeddings:
        return pd.DataFrame(columns=["start", "end", "speaker"])

    x = np.vstack(embeddings)
    n_slices = len(embeddings)
    n_clusters = int(np.clip(round(np.sqrt(n_slices / 3)), min_speakers, max_speakers))
    n_clusters = int(np.clip(n_clusters, min_speakers, min(max_speakers, max(min_speakers, n_slices // 8))))
    labels = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(x)

    rows = [
        {"start": meta[i][0], "end": meta[i][1], "speaker": f"SPEAKER_{labels[i]:02d}"}
        for i in range(len(meta))
    ]
    LOGGER.warning(
        "Using local spectral clustering fallback (%d clusters, %d slices)",
        n_clusters,
        len(rows),
    )
    return pd.DataFrame(rows)


def load_existing_transcript_segments(student_dir: Path, student_id: str) -> tuple[list[dict], Path | None]:
    """Load ASR segments from existing transcript sidecars (labeled preferred)."""
    for name in (f"{student_id}_transcript_labeled.json", f"{student_id}_transcript.json"):
        path = student_dir / name
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("status") == "no_speech":
            return [], path
        segments: list[dict] = []
        for idx, seg in enumerate(payload.get("segments") or [], 1):
            text = str(seg.get("text", "")).strip()
            if not text:
                continue
            segments.append(
                {
                    "id": int(seg.get("id", idx)),
                    "start": float(seg["start"]),
                    "end": float(seg["end"]),
                    "text": text,
                }
            )
        return segments, path
    return [], None


def diarization_dataframe_to_slices(diarize_df: Any) -> list[dict]:
    slices: list[dict] = []
    for row in diarize_df.itertuples(index=False):
        speaker = getattr(row, "speaker", None)
        start = float(getattr(row, "start"))
        end = float(getattr(row, "end"))
        if not speaker or end <= start:
            continue
        slices.append(
            {
                "start": start,
                "end": end,
                "speaker_id": str(speaker),
            }
        )
    return sorted(slices, key=lambda s: float(s["start"]))


def bind_transcript_segments_to_diarization(
    transcript_segments: list[dict],
    diar_slices: list[dict],
) -> list[dict]:
    """Map existing transcript timestamps to clustered speaker_id values."""
    from speaker_merge import load_merge_rules, pick_speaker_id

    rules = load_merge_rules(None)
    bound: list[dict] = []
    for seg in transcript_segments:
        start = float(seg["start"])
        end = float(seg["end"])
        speaker_id, bind_confidence, bind_method = pick_speaker_id(start, end, diar_slices, rules)
        bound.append(
            {
                "id": seg["id"],
                "start": round(start, 2),
                "end": round(end, 2),
                "start_hms": format_timestamp(start),
                "end_hms": format_timestamp(end),
                "text": seg["text"],
                "speaker_id": speaker_id or "SPEAKER_UNKNOWN",
                "bind_confidence": round(float(bind_confidence), 3),
                "bind_method": bind_method,
            }
        )
    return bound


def release_runtime_memory() -> None:
    import gc

    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except ImportError:
        pass


def run_diarization(
    audio_path: Path,
    aligned_result: dict[str, Any],
    *,
    device: str,
    diarization_model: str,
    diarization_config: Path | None,
    hf_token: str | None,
    min_speakers: int,
    max_speakers: int,
    preprocessed: PreprocessResult,
) -> tuple[dict[str, Any], str]:
    import whisperx

    diarize_df = None
    method = "whisperx_pyannote"
    try:
        diarizer = init_diarization_pipeline(
            device=device,
            diarization_model=diarization_model,
            diarization_config=diarization_config,
            hf_token=hf_token,
        )
        LOGGER.info("Running WhisperX diarization")
        diarize_df = diarizer(
            str(audio_path),
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )
    except Exception as exc:
        LOGGER.warning("WhisperX diarization unavailable (%s); falling back to local clustering", exc)
        method = "local_spectral_clustering"
        diarize_df = local_spectral_diarization(
            preprocessed.audio,
            preprocessed.sample_rate,
            min_speakers=min_speakers,
            max_speakers=max_speakers,
        )

    return whisperx.assign_word_speakers(diarize_df, aligned_result, fill_nearest=True), method


def flatten_whisperx_segments(aligned_with_speakers: dict[str, Any]) -> list[dict]:
    """Collapse word-level speakers into segment records."""
    segments: list[dict] = []
    for idx, seg in enumerate(aligned_with_speakers.get("segments", []), 1):
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        speaker = seg.get("speaker")
        segments.append(
            {
                "id": idx,
                "start": round(float(seg["start"]), 2),
                "end": round(float(seg["end"]), 2),
                "start_hms": format_timestamp(float(seg["start"])),
                "end_hms": format_timestamp(float(seg["end"])),
                "text": text,
                "speaker_id": speaker,
            }
        )
    return segments


def apply_hybrid_roles(segments: list[dict], matrix: HybridMatrixResult) -> list[dict]:
    enriched: list[dict] = []
    for idx, seg in enumerate(segments, 1):
        speaker_id = str(seg.get("speaker_id") or "SPEAKER_UNKNOWN")
        role = matrix.role_map.get(speaker_id, "classmate")
        confidence = matrix.confidence_map.get(speaker_id, 0.5)
        enriched.append(
            {
                "id": seg.get("id", idx),
                "start": seg["start"],
                "end": seg["end"],
                "text": seg["text"],
                "speaker_id": speaker_id,
                "speaker_role": role,
                "speaker_confidence": confidence,
                "speaker_method": "hybrid_matrix_duration_and_lexical",
            }
        )
    return enriched


def write_no_speech_output(
    student_dir: Path,
    student_id: str,
    wav_path: Path,
    preprocess: PreprocessResult,
    *,
    output_suffix: str,
    whisper_model: str,
    language: str,
) -> Path:
    from transcript_quality import AudioAnalysis

    audio = AudioAnalysis(
        duration_seconds=preprocess.duration_seconds,
        mean_volume_db=None,
        silence_fraction=1.0 - preprocess.speech_fraction,
        speech_fraction=preprocess.speech_fraction,
    )
    payload = make_no_speech_payload(
        student_id,
        str(repo_relative_path(wav_path)),
        audio,
        model=f"hybrid/{whisper_model}",
        language=language,
    )
    payload["pipeline"] = "hybrid_diarization_v1"
    payload["preprocess"] = {
        "mean_rms": round(preprocess.mean_rms, 6),
        "speech_fraction_rms": round(preprocess.speech_fraction, 4),
        "status": "no_speech",
    }
    out_path = student_dir / f"{student_id}{output_suffix}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def write_hybrid_output(
    student_dir: Path,
    student_id: str,
    wav_path: Path,
    segments: list[dict],
    matrix: HybridMatrixResult,
    preprocess: PreprocessResult,
    *,
    output_suffix: str,
    whisper_model: str,
    language: str,
    diarization_method: str,
) -> Path:
    from normalize_hybrid_diarization import build_v2_hybrid_payload, compact_timeline

    role_counts: dict[str, int] = {}
    seg_counts: dict[str, int] = {}
    for seg in segments:
        role = seg["speaker_role"]
        role_counts[role] = role_counts.get(role, 0) + 1
        sid = str(seg.get("speaker_id") or "")
        if sid:
            seg_counts[sid] = seg_counts.get(sid, 0) + 1

    speaker_profiles = [
        {
            "speaker_id": sid,
            "role": p.resolved_role,
            "confidence": round(p.role_confidence, 3),
            "duration_seconds": round(p.total_duration, 2),
            "segment_count": seg_counts.get(sid, 0),
        }
        for sid, p in matrix.profiles.items()
    ]
    speaker_profiles.sort(
        key=lambda r: (
            {"teacher": 0, "student": 1, "classmate": 2}.get(r["role"], 9),
            -r["duration_seconds"],
            r["speaker_id"],
        )
    )

    payload = build_v2_hybrid_payload(
        student_id=student_id,
        source_audio=repo_relative_path(wav_path),
        processed_at=datetime.now(timezone.utc).isoformat(),
        status="ok",
        duration_seconds=preprocess.duration_seconds,
        whisper_model=whisper_model,
        diarization_method=diarization_method,
        language=language,
        preprocess={
            "noise_reduction": "noisereduce_stationary",
            "speech_fraction": round(preprocess.speech_fraction, 4),
        },
        teacher_speaker=matrix.teacher_speaker,
        focal_student_speaker=matrix.focal_student_speaker,
        role_counts=role_counts,
        speaker_profiles=speaker_profiles,
        timeline=compact_timeline(segments),
    )
    payload["segments"] = segments
    payload["segment_count"] = len(segments)
    if diarization_method == "local_spectral_clustering" and whisper_model.startswith("existing_"):
        payload["description"] = (
            "Mevcut transkript zaman damgaları + yerel MFCC kümeleme ile birleştirilmiş hibrit diarizasyon. "
            "Her segment: id, start, end, text, speaker_id, speaker_role, speaker_confidence, speaker_method."
        )

    out_path = student_dir / f"{student_id}{output_suffix}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path


def cleanup_temp(path: Path | None, keep: bool) -> None:
    if path and not keep and path.exists():
        try:
            path.unlink()
        except OSError:
            LOGGER.debug("Could not remove temp file %s", path)


def process_student_transcript_fusion(
    wav_path: Path,
    student_id: str,
    args: argparse.Namespace,
) -> Path:
    """Fuse existing transcript text/timestamps with local spectral diarization."""
    student_dir = wav_path.parent
    LOGGER.info("=== %s transcript fusion (%s) ===", student_id, wav_path.name)

    preprocess = preprocess_audio(
        wav_path,
        keep_preprocessed=args.keep_preprocessed,
        student_dir=student_dir,
    )

    if preprocess.is_silent:
        return write_no_speech_output(
            student_dir,
            student_id,
            wav_path,
            preprocess,
            output_suffix=args.output_suffix,
            whisper_model="existing_transcript_fusion",
            language=args.language,
        )

    transcript_segments, transcript_path = load_existing_transcript_segments(student_dir, student_id)
    if not transcript_segments:
        LOGGER.warning(
            "%s: no usable transcript segments%s — writing no_speech hybrid stub",
            student_id,
            f" ({transcript_path.name})" if transcript_path else "",
        )
        return write_no_speech_output(
            student_dir,
            student_id,
            wav_path,
            preprocess,
            output_suffix=args.output_suffix,
            whisper_model="existing_transcript_fusion",
            language=args.language,
        )

    LOGGER.info(
        "%s: fusing %d transcript segments from %s",
        student_id,
        len(transcript_segments),
        transcript_path.name if transcript_path else "unknown",
    )

    diarize_df = local_spectral_diarization(
        preprocess.audio,
        preprocess.sample_rate,
        min_speakers=args.min_speakers,
        max_speakers=args.max_speakers,
    )
    diar_slices = diarization_dataframe_to_slices(diarize_df)
    if not diar_slices:
        raise RuntimeError(f"{student_id}: local diarization produced zero slices")

    raw_segments = bind_transcript_segments_to_diarization(transcript_segments, diar_slices)
    segments, removed = filter_segments(raw_segments)
    if removed:
        LOGGER.info("%s: removed %d segments during QA filter", student_id, removed)

    profiles = build_speaker_profiles(segments)
    matrix = compute_hybrid_role_matrix(profiles)
    final_segments = apply_hybrid_roles(segments, matrix)

    out_path = write_hybrid_output(
        student_dir,
        student_id,
        wav_path,
        final_segments,
        matrix,
        preprocess,
        output_suffix=args.output_suffix,
        whisper_model="existing_transcript_fusion",
        language=args.language,
        diarization_method="local_spectral_clustering",
    )

    cleanup_temp(preprocess.denoised_path, keep=args.keep_preprocessed)
    LOGGER.info(
        "%s fusion done: %d segments | teacher=%s student=%s | roles=%s",
        student_id,
        len(final_segments),
        matrix.teacher_speaker,
        matrix.focal_student_speaker,
        {seg["speaker_role"] for seg in final_segments},
    )
    return out_path


def process_student(
    wav_path: Path,
    student_id: str,
    args: argparse.Namespace,
) -> Path:
    student_dir = wav_path.parent
    LOGGER.info("=== %s (%s) ===", student_id, wav_path.name)

    if args.fuse_existing_transcript:
        return process_student_transcript_fusion(wav_path, student_id, args)

    preprocess = preprocess_audio(
        wav_path,
        keep_preprocessed=args.keep_preprocessed,
        student_dir=student_dir,
    )

    if preprocess.is_silent:
        return write_no_speech_output(
            student_dir,
            student_id,
            wav_path,
            preprocess,
            output_suffix=args.output_suffix,
            whisper_model=args.whisper_model,
            language=args.language,
        )

    assert preprocess.denoised_path is not None
    audio_for_asr = preprocess.denoised_path
    device = resolve_device(args.device)
    diarization_method = "whisperx_pyannote"

    aligned = whisperx_transcribe_and_align(
        audio_for_asr,
        model_name=args.whisper_model,
        language=args.language,
        device=device,
        compute_type=args.compute_type,
        batch_size=args.batch_size,
    )
    try:
        diarized, diarization_method = run_diarization(
            audio_for_asr,
            aligned,
            device=device,
            diarization_model=args.diarization_model,
            diarization_config=args.diarization_config,
            hf_token=args.hf_token,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
            preprocessed=preprocess,
        )
    except Exception as exc:
        LOGGER.warning("Diarization merge failed (%s); using local clustering only", exc)
        diarization_method = "local_spectral_clustering"
        import whisperx

        diarize_df = local_spectral_diarization(
            preprocess.audio,
            preprocess.sample_rate,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
        )
        diarized = whisperx.assign_word_speakers(diarize_df, aligned, fill_nearest=True)

    raw_segments = flatten_whisperx_segments(diarized)
    segments, removed = filter_segments(raw_segments)
    if removed:
        LOGGER.info("Removed %d hallucinated segments during QA filter", removed)

    profiles = build_speaker_profiles(segments)
    matrix = compute_hybrid_role_matrix(profiles)
    final_segments = apply_hybrid_roles(segments, matrix)

    out_path = write_hybrid_output(
        student_dir,
        student_id,
        wav_path,
        final_segments,
        matrix,
        preprocess,
        output_suffix=args.output_suffix,
        whisper_model=args.whisper_model,
        language=args.language,
        diarization_method=diarization_method,
    )

    cleanup_temp(preprocess.denoised_path, keep=args.keep_preprocessed)
    LOGGER.info(
        "%s done: %d segments | teacher=%s student=%s | roles=%s",
        student_id,
        len(final_segments),
        matrix.teacher_speaker,
        matrix.focal_student_speaker,
        {seg["speaker_role"] for seg in final_segments},
    )
    return out_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    setup_logging(args.verbose)

    try:
        targets = resolve_targets(args)
    except FileNotFoundError as exc:
        LOGGER.error("%s", exc)
        return 1

    if not targets:
        LOGGER.error("No WAV targets found under %s", args.audio_root)
        return 1

    failures = 0
    for wav_path, student_id in targets:
        student_dir = wav_path.parent
        out_path = student_dir / f"{student_id}{args.output_suffix}.json"
        if args.skip_existing and out_path.is_file():
            LOGGER.info("Skipping %s (existing %s)", student_id, out_path.name)
            print(f"[skip] {student_id} -> {repo_relative_path(out_path)}")
            continue
        try:
            out = process_student(wav_path, student_id, args)
            print(f"[ok] {student_id} -> {repo_relative_path(out)}")
        except Exception as exc:
            failures += 1
            LOGGER.exception("%s failed: %s", student_id, exc)
        finally:
            release_runtime_memory()

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
