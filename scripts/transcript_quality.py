"""ASR transcript post-processor for Whisper screen-recording outputs.

Implements five anomaly classes:
  1. Silence/noise hallucinations (Chinese, Bational, filler phrases)
  2. Burst & chain repetitions
  3. Broken / inverted timestamps
  4. Ghost 30-second blocks
  5. Colloquial overlap preservation (Allah Allah, Dur dur, …)
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_AUDIO_ROOT = REPO_ROOT / "data_sources_2026" / "codap_arbor_21april_audio"

# --- Known toxic ASR outputs -------------------------------------------------

HALLUCINATION_TEXTS = {
    "altyazı m.k.",
    "altyazı mk",
    "subtitles by",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "www.",
    "izlediğiniz için teşekkürler",
    "izlediğiniz için teşekkür ederim",
    "chinese",
    "bational",
    "subtitle",
    "subtitles",
    "...",
    "b chinese",
}

HALLUCINATION_TOKENS = {
    "chinese",
    "bational",
    "subtitle",
    "subtitles",
    "müzik",
    "music",
}

# Short phrases Whisper emits on silence with no conversational support.
CONTEXTLESS_GHOST_PHRASES = {
    "ay yaparız.",
    "ay yaparız",
    "alabilir miyim?",
    "alabilir miyim",
    "kaydınızı kontrol edelim.",
    "kaydınızı kontrol edelim",
    "thank you for watching",
    "thanks for watching",
    "please subscribe",
    "izlediğiniz için teşekkür ederim",
    "izlediğiniz için teşekkürler",
}

# Valid once but hallucinated in rapid machine-like bursts.
BURST_PRONE_PHRASES = {
    "tamam",
    "tamam.",
    "evet",
    "evet.",
    "lütfen",
    "lütfen.",
    "ya",
    "ya.",
    "gördünüz mü?",
    "gördünüz mü",
    "değiştirelim mi?",
    "aşağı doğru.",
    "aşağı doğru",
    "bu arada.",
    "bu arada",
    "geldi.",
    "geldi",
    "yok.",
    "yok",
    "chinese",
    "bational",
    "genel olarak",
    "bational chinese",
    "chinese chinese",
    "altyazı m.k.",
}

# Natural colloquial repetition — never remove unless part of a long machine burst.
COLLOQUIAL_PRESERVE_PATTERNS = [
    re.compile(r"^allah\s+allah\.?$", re.I),
    re.compile(r"^dur\s+dur!?$", re.I),
    re.compile(r"^hayır\s+hayır\.?$", re.I),
    re.compile(r"^yok\s+yok\.?$", re.I),
    re.compile(r"^tamam\s+tamam\.?$", re.I),
    re.compile(r"^evet\s+evet\.?$", re.I),
    re.compile(r"^hocam\s+hocam\.?$", re.I),
]

HALLUCINATION_PATTERNS = [
    re.compile(r"^Altyazı\s+M\.?K\.?$", re.I),
    re.compile(r"^Chinese(\s+Chinese)*$", re.I),
    re.compile(r"^Bational(\s+(Chinese|Bational))*$", re.I),
    re.compile(r"^(ye\s+){3,}ye$", re.I),
    re.compile(r"^(köjü\s+){3,}köjü", re.I),
    re.compile(r"^(cost'?unu,?\s*){3,}", re.I),
    re.compile(r"^(tamam\.?\s*){2,}$", re.I),
    re.compile(r"^(evet\.?\s*){2,}$", re.I),
    re.compile(r"^(lütfen\.?\s*){2,}$", re.I),
    re.compile(r"^(aşağı doğru\.?\s*){2,}$", re.I),
    re.compile(r"^(bu arada\.?\s*){2,}$", re.I),
    re.compile(r"^(değiştirelim mi\?\s*){2,}$", re.I),
    re.compile(r"^(gördünüz mü\?\s*){2,}$", re.I),
    re.compile(r"^(yok\s+){3,}yok\.?$", re.I),
    re.compile(r"^E9(\.\s*){3,}E9", re.I),
    re.compile(r"^\.{3,}$"),
    re.compile(r"^B\s*Chinese$", re.I),
    re.compile(r"^[\W_]+$"),
]

BURST_MIN_RUN = 4
BURST_MAX_SEGMENT_SECONDS = 1.5
LONG_SEGMENT_SECONDS = 20.0
LONG_SEGMENT_MAX_CHARS = 50
LONG_SEGMENT_MAX_WORDS = 6
WHISPER_CHUNK_SECONDS = 30.0
WHISPER_CHUNK_TOLERANCE = 1.0
LONG_BURST_MIN_RUN = 2
LONG_BURST_MIN_SECONDS = 20.0
VACUUM_GAP_SECONDS = 12.0

SPEECH_SILENCE_THRESHOLD_DB = -35
MIN_SPEECH_FRACTION = 0.05
MIN_SEGMENTS_PER_MINUTE = 8
MAX_HALLUCINATION_FRACTION = 0.5


@dataclass
class AudioAnalysis:
    duration_seconds: float
    mean_volume_db: float | None
    silence_fraction: float
    speech_fraction: float

    @property
    def is_silent(self) -> bool:
        return self.speech_fraction < MIN_SPEECH_FRACTION


@dataclass
class TranscriptAssessment:
    student_id: str
    status: str
    segment_count: int
    duration_seconds: float
    coverage_percent: float
    segments_per_minute: float
    hallucination_fraction: float
    audio: AudioAnalysis
    issues: list[str]
    notes: list[str]


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}"


def ffprobe_duration(path: Path) -> float:
    result = subprocess.run(
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
        capture_output=True,
        text=True,
        check=False,
    )
    return float(result.stdout.strip()) if result.stdout.strip() else 0.0


def analyze_audio(wav_path: Path) -> AudioAnalysis:
    duration = ffprobe_duration(wav_path)
    volume = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", str(wav_path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
        check=False,
    )
    mean_match = re.search(r"mean_volume:\s*([-\d.]+)\s*dB", volume.stderr)
    mean_db = float(mean_match.group(1)) if mean_match else None

    silence_detect = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(wav_path),
            "-af",
            f"silencedetect=noise={SPEECH_SILENCE_THRESHOLD_DB}dB:d=2",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    silence_seconds = 0.0
    starts: list[float] = []
    for line in silence_detect.stderr.splitlines():
        if "silence_start:" in line:
            starts.append(float(line.split("silence_start: ")[1].split()[0]))
        if "silence_end:" in line:
            end = float(line.split("silence_end: ")[1].split("|")[0].strip())
            if starts:
                silence_seconds += end - starts.pop()

    silence_fraction = min(1.0, silence_seconds / duration) if duration else 1.0
    speech_fraction = max(0.0, 1.0 - silence_fraction)
    return AudioAnalysis(
        duration_seconds=duration,
        mean_volume_db=mean_db,
        silence_fraction=silence_fraction,
        speech_fraction=speech_fraction,
    )


def normalize_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def segment_duration(seg: dict) -> float:
    return float(seg["end"]) - float(seg["start"])


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def is_colloquial_preserved(text: str) -> bool:
    normalized = text.strip()
    return any(pattern.match(normalized) for pattern in COLLOQUIAL_PRESERVE_PATTERNS)


def is_repetitive_hallucination_text(text: str) -> bool:
    if is_colloquial_preserved(text):
        return False
    lowered = normalize_phrase(text)
    if lowered.count("chinese") >= 2:
        return True
    if lowered.count("bational") >= 2:
        return True
    if re.search(r"(ational){2,}", lowered):
        return True
    if re.search(r"(chinese\s+){2,}", lowered):
        return True
    words = re.findall(r"\w+", text, flags=re.UNICODE)
    if len(words) >= 12:
        unique_ratio = len({w.lower() for w in words}) / len(words)
        if unique_ratio < 0.2:
            return True
    return False


def is_hallucination_text(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    if is_colloquial_preserved(normalized):
        return False
    lowered = normalize_phrase(normalized)
    if lowered in HALLUCINATION_TEXTS or lowered in HALLUCINATION_TOKENS:
        return True
    if is_repetitive_hallucination_text(normalized):
        return True
    if re.search(r"\b(chinese|bational)\b", normalized, flags=re.I):
        return True
    return any(pattern.search(normalized) for pattern in HALLUCINATION_PATTERNS)


def is_invalid_timestamp(seg: dict) -> bool:
    return segment_duration(seg) <= 0


def seconds_per_word(seg: dict) -> float:
    words = max(word_count(str(seg.get("text", ""))), 1)
    return segment_duration(seg) / words


def gap_before(segments: list[dict], index: int) -> float:
    if index <= 0:
        return float("inf")
    return float(segments[index]["start"]) - float(segments[index - 1]["end"])


def gap_after(segments: list[dict], index: int) -> float:
    if index >= len(segments) - 1:
        return float("inf")
    return float(segments[index + 1]["start"]) - float(segments[index]["end"])


def is_contextless_ghost(seg: dict, *, gap_prev: float, gap_next: float) -> bool:
    text = normalize_phrase(str(seg.get("text", "")))
    if text not in CONTEXTLESS_GHOST_PHRASES:
        return False
    duration = segment_duration(seg)
    isolated = gap_prev >= VACUUM_GAP_SECONDS or gap_next >= VACUUM_GAP_SECONDS
    long_block = duration >= LONG_SEGMENT_SECONDS or abs(duration - WHISPER_CHUNK_SECONDS) <= WHISPER_CHUNK_TOLERANCE
    return isolated or long_block


def is_ghost_thirty_second_block(seg: dict) -> bool:
    duration = segment_duration(seg)
    if abs(duration - WHISPER_CHUNK_SECONDS) > WHISPER_CHUNK_TOLERANCE:
        return False
    text = str(seg.get("text", "")).strip()
    if is_colloquial_preserved(text):
        return False
    words = word_count(text)
    if is_hallucination_text(text):
        return True
    if words <= LONG_SEGMENT_MAX_WORDS and len(text) <= LONG_SEGMENT_MAX_CHARS:
        return True
    if is_repetitive_hallucination_text(text):
        return True
    if seconds_per_word(seg) >= 2.8 and words <= 12:
        return True
    return False


def is_long_sparse_hallucination(seg: dict) -> bool:
    text = str(seg.get("text", "")).strip()
    if not text or is_colloquial_preserved(text):
        return False
    duration = segment_duration(seg)
    words = word_count(text)
    lowered = normalize_phrase(text)

    if is_hallucination_text(text) and (duration >= 15 or words <= LONG_SEGMENT_MAX_WORDS):
        return True
    if duration < LONG_SEGMENT_SECONDS:
        return False
    if is_ghost_thirty_second_block(seg):
        return True
    if duration >= 24 and len(text) <= 45 and words <= LONG_SEGMENT_MAX_WORDS:
        return True
    if duration >= LONG_SEGMENT_SECONDS and seconds_per_word(seg) >= 2.8 and words <= 12:
        return True
    if is_repetitive_hallucination_text(text):
        return True
    if duration >= LONG_SEGMENT_SECONDS and lowered in BURST_PRONE_PHRASES:
        return True
    return False


def is_burst_hallucination_run(block: list[dict]) -> bool:
    if len(block) < BURST_MIN_RUN:
        return False
    phrase = normalize_phrase(str(block[0].get("text", "")))
    if is_colloquial_preserved(str(block[0].get("text", ""))):
        return False
    if phrase not in BURST_PRONE_PHRASES and phrase not in HALLUCINATION_TOKENS:
        return False
    durations = [segment_duration(seg) for seg in block]
    if max(durations) > BURST_MAX_SEGMENT_SECONDS:
        return False
    if sum(durations) / len(durations) > BURST_MAX_SEGMENT_SECONDS:
        return False
    return all(normalize_phrase(str(seg.get("text", ""))) == phrase for seg in block)


def find_identical_runs(
    segments: list[dict],
    *,
    min_run: int,
    predicate,
) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    idx = 0
    while idx < len(segments):
        phrase = normalize_phrase(str(segments[idx].get("text", "")))
        end = idx + 1
        while end < len(segments) and normalize_phrase(str(segments[end].get("text", ""))) == phrase:
            end += 1
        if end - idx >= min_run and predicate(segments[idx:end]):
            runs.append((idx, end))
        idx = end if end > idx + 1 else idx + 1
    return runs


def find_vacuum_runs(segments: list[dict]) -> list[tuple[int, int]]:
    """Drop hallucination chains that appear after a long silence gap."""
    drop: list[tuple[int, int]] = []
    idx = 0
    while idx < len(segments):
        gap = gap_before(segments, idx)
        if gap < VACUUM_GAP_SECONDS:
            idx += 1
            continue
        end = idx
        while end < len(segments):
            seg = segments[end]
            text = str(seg.get("text", "")).strip()
            if is_colloquial_preserved(text):
                break
            if not (
                is_hallucination_text(text)
                or is_contextless_ghost(seg, gap_prev=gap if end == idx else 0.0, gap_next=gap_after(segments, end))
                or is_ghost_thirty_second_block(seg)
                or is_long_sparse_hallucination(seg)
            ):
                break
            end += 1
        if end - idx >= 1:
            drop.append((idx, end))
        idx = max(end, idx + 1)
    return drop


def _renumber_segments(segments: list[dict]) -> list[dict]:
    renumbered: list[dict] = []
    for new_id, seg in enumerate(segments, 1):
        start = float(seg["start"])
        end = float(seg["end"])
        renumbered.append(
            {
                **seg,
                "id": new_id,
                "start": round(start, 2),
                "end": round(end, 2),
                "start_hms": format_timestamp(start),
                "end_hms": format_timestamp(end),
            }
        )
    return renumbered


def clean_segments(segments: list[dict]) -> tuple[list[dict], dict]:
    """Run the full ASR post-processing pipeline on a segment list."""
    stats = {
        "removed_silence_hallucination": 0,
        "removed_burst_runs": 0,
        "removed_chain_repetitions": 0,
        "removed_invalid_timestamp": 0,
        "removed_ghost_blocks": 0,
        "removed_vacuum_fillers": 0,
        "removed_contextless_ghosts": 0,
    }
    drop: set[int] = set()

    for start, end in find_identical_runs(segments, min_run=BURST_MIN_RUN, predicate=is_burst_hallucination_run):
        drop.update(range(start, end))
        stats["removed_burst_runs"] += end - start

    for start, end in find_identical_runs(
        segments,
        min_run=LONG_BURST_MIN_RUN,
        predicate=lambda block: all(segment_duration(seg) >= LONG_BURST_MIN_SECONDS for seg in block),
    ):
        drop.update(range(start, end))
        stats["removed_chain_repetitions"] += end - start

    for start, end in find_vacuum_runs(segments):
        drop.update(range(start, end))
        stats["removed_vacuum_fillers"] += end - start

    kept: list[dict] = []
    for idx, seg in enumerate(segments):
        if idx in drop:
            continue
        text = str(seg.get("text", "")).strip()
        gap_prev = gap_before(segments, idx)
        gap_next = gap_after(segments, idx)

        if is_invalid_timestamp(seg):
            stats["removed_invalid_timestamp"] += 1
            continue
        if is_ghost_thirty_second_block(seg):
            stats["removed_ghost_blocks"] += 1
            continue
        if is_long_sparse_hallucination(seg):
            stats["removed_ghost_blocks"] += 1
            continue
        if is_contextless_ghost(seg, gap_prev=gap_prev, gap_next=gap_next):
            stats["removed_contextless_ghosts"] += 1
            continue
        if is_hallucination_text(text):
            stats["removed_silence_hallucination"] += 1
            continue
        kept.append(seg)

    renumbered = _renumber_segments(kept)
    stats["removed_total"] = len(segments) - len(renumbered)
    return renumbered, stats


def filter_segments(segments: list[dict]) -> tuple[list[dict], int]:
    cleaned, stats = clean_segments(segments)
    return cleaned, stats["removed_total"]


def assess_transcript(student_id: str, transcript: dict, audio: AudioAnalysis) -> TranscriptAssessment:
    segments = transcript.get("segments", [])
    duration = transcript.get("duration_seconds") or audio.duration_seconds
    last_end = segments[-1]["end"] if segments else 0.0
    coverage = (last_end / duration * 100) if duration else 0.0
    segs_per_min = len(segments) / (duration / 60) if duration else 0.0
    hall_count = sum(1 for seg in segments if is_hallucination_text(str(seg.get("text", ""))))
    hall_fraction = hall_count / len(segments) if segments else 0.0

    issues: list[str] = []
    notes: list[str] = []

    if transcript.get("status") == "no_speech":
        note = transcript.get("speech_status_note")
        if note:
            notes.append(note)
        if audio.is_silent:
            issues.append("no_speech_in_audio")
        elif transcript.get("speech_status") == "truncated_audio_track":
            issues.append("truncated_audio_track")
        return TranscriptAssessment(
            student_id=student_id,
            status="no_speech",
            segment_count=len(segments),
            duration_seconds=duration,
            coverage_percent=round(coverage, 1),
            segments_per_minute=round(segs_per_min, 1),
            hallucination_fraction=round(hall_fraction, 3),
            audio=audio,
            issues=issues,
            notes=notes,
        )

    if audio.is_silent:
        issues.append("no_speech_in_audio")
        notes.append(
            "Kayıtta konuşma sesi yok; ekran kaydı yalnızca görüntü içeriyor veya mikrofon/sistem sesi yakalanmamış."
        )

    if hall_fraction >= MAX_HALLUCINATION_FRACTION and len(segments) > 0:
        issues.append("hallucinated_transcript")

    if not audio.is_silent and segs_per_min < MIN_SEGMENTS_PER_MINUTE:
        issues.append("too_few_segments")

    trailing_silence = duration - last_end
    if (
        duration
        and coverage < 80
        and trailing_silence > 120
        and segs_per_min < MIN_SEGMENTS_PER_MINUTE
    ):
        issues.append("incomplete_coverage")

    if audio.is_silent or (hall_fraction >= MAX_HALLUCINATION_FRACTION and len(segments) > 0):
        status = "no_speech"
    elif issues:
        status = "needs_review"
    else:
        status = "ok"

    return TranscriptAssessment(
        student_id=student_id,
        status=status,
        segment_count=len(segments),
        duration_seconds=duration,
        coverage_percent=round(coverage, 1),
        segments_per_minute=round(segs_per_min, 1),
        hallucination_fraction=round(hall_fraction, 3),
        audio=audio,
        issues=issues,
        notes=notes,
    )


def build_srt_lines(segments: list[dict]) -> list[str]:
    lines: list[str] = []
    for seg in segments:
        lines.append(str(seg["id"]))
        lines.append(
            f"{seg['start_hms'].replace('.', ',')} --> {seg['end_hms'].replace('.', ',')}"
        )
        lines.append(seg["text"])
        lines.append("")
    return lines


def write_transcript_bundle(
    student_dir: Path,
    payload: dict,
) -> tuple[Path, Path, Path]:
    student_id = student_dir.name
    json_path = student_dir / f"{student_id}_transcript.json"
    txt_path = student_dir / f"{student_id}_transcript.txt"
    srt_path = student_dir / f"{student_id}_transcript.srt"

    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    txt_path.write_text(payload.get("full_text", "") + ("\n" if payload.get("full_text") else ""), encoding="utf-8")
    srt_path.write_text("\n".join(build_srt_lines(payload.get("segments", []))) + "\n", encoding="utf-8")
    return json_path, txt_path, srt_path


def make_no_speech_payload(
    student_id: str,
    source_audio: str,
    audio: AudioAnalysis,
    *,
    model: str,
    language: str,
    previous_segment_count: int = 0,
) -> dict:
    return {
        "student_id": student_id,
        "source_audio": source_audio,
        "transcribed_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "language": language,
        "status": "no_speech",
        "speech_status": "silent_recording",
        "speech_status_note": (
            "Kayıtta konuşma sesi yok; ekran kaydı yalnızca görüntü içeriyor veya mikrofon/sistem sesi "
            "yakalanmamış. Whisper sessizlik üzerinde halüsinasyon üretti; transkript temizlendi."
        ),
        "duration_seconds": round(audio.duration_seconds, 2),
        "segment_count": 0,
        "full_text": "",
        "segments": [],
        "audio_analysis": {
            "mean_volume_db": audio.mean_volume_db,
            "silence_fraction": round(audio.silence_fraction, 4),
            "speech_fraction": round(audio.speech_fraction, 4),
        },
        "qa": {
            "previous_segment_count": previous_segment_count,
            "hallucination_segments_removed": previous_segment_count,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def make_clean_payload(
    transcript: dict,
    segments: list[dict],
    removed: int,
    audio: AudioAnalysis,
    clean_stats: dict | None = None,
) -> dict:
    payload = dict(transcript)
    payload["segments"] = segments
    payload["segment_count"] = len(segments)
    payload["full_text"] = " ".join(seg["text"] for seg in segments)
    payload["status"] = "ok"
    payload["audio_analysis"] = {
        "mean_volume_db": audio.mean_volume_db,
        "silence_fraction": round(audio.silence_fraction, 4),
        "speech_fraction": round(audio.speech_fraction, 4),
    }
    qa = {
        "hallucination_segments_removed": removed,
        "validated_at": datetime.now(timezone.utc).isoformat(),
    }
    if clean_stats:
        qa["cleaning"] = clean_stats
    payload["qa"] = qa
    return payload
