"""Speaker role inference for mixed classroom screen recordings.

Strategy (hybrid):
  1. Audio diarization (optional, pyannote) → speaker clusters by voice
  2. Role mapping → map clusters to teacher / focal_student / classmate
  3. Text cues → refine per-segment labels and confidence

Without diarization we can only guess from lexicon + turn shape (lower accuracy).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

TEACHER_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\barkadaşlar\b",
        r"\bsevgili arkadaşlar\b",
        r"\bşimdi\b",
        r"\bgeçelim\b",
        r"\bbakın\b",
        r"\blütfen\b",
        r"\bsoru\s+(diyor|şu)\b",
        r"\bbirinci soru\b",
        r"\bikinci soru\b",
        r"\bemit\b",
        r"\bkarar ağac",
        r"\bveri set",
        r"\beğitim (seti|grubu)\b",
        r"\btest (seti|grubu)\b",
        r"\bgrafik",
        r"\bkodep\b",
        r"\bherkes\b",
        r"\bsiz\b",
        r"\btamam mı\b",
        r"\bşimdi geldik\b",
        r"\başlayalım\b",
        r"\bcevaplayın\b",
        r"\byazın\b",
        r"\bdeneyin\b",
    ]
]

STUDENT_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bhocam\b",
        r"\bben\b",
        r"\bbenim\b",
        r"\byapamad",
        r"\bçalışmıyor\b",
        r"\bgelmedi\b",
        r"\bkanka\b",
        r"\bnasıl (yap|sile|ekle)",
        r"\bsorabilir miyim\b",
        r"\befendim\b",
        r"\bevet hocam\b",
        r"\bbende\b",
        r"\bbizde\b",
        r"\byardım\b",
        r"\banlamadım\b",
    ]
]

CLASSMATE_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bismim\b",
        r"\bismim neydi\b",
        r"\bayşe\b",
        r"\bzeynep\b",
        r"\birem\b",
        r"\bmerve\b",
    ]
]

TEACHER_MONOLOGUE_MIN_WORDS = 18
STUDENT_SHORT_MAX_WORDS = 14


@dataclass
class SpeakerLabel:
    role: str
    confidence: float
    method: str
    speaker_id: str | None = None
    notes: str = ""


def word_count(text: str) -> int:
    return len(re.findall(r"\w+", text, flags=re.UNICODE))


def pattern_score(text: str, patterns: list[re.Pattern]) -> int:
    return sum(len(p.findall(text)) for p in patterns)


def classify_segment_text(
    text: str,
    *,
    prev_role: str | None = None,
    next_role: str | None = None,
) -> SpeakerLabel:
    """Lexicon + turn-shape classifier. Best-effort without audio diarization."""
    normalized = text.strip()
    if not normalized:
        return SpeakerLabel("unknown", 0.0, "text_empty")

    words = word_count(normalized)
    t_score = pattern_score(normalized, TEACHER_PATTERNS)
    s_score = pattern_score(normalized, STUDENT_PATTERNS)
    c_score = pattern_score(normalized, CLASSMATE_PATTERNS)

    if c_score >= 1 and s_score == 0 and t_score == 0:
        return SpeakerLabel("classmate", 0.55, "text_classmate_name")

    if t_score >= 2 and words >= TEACHER_MONOLOGUE_MIN_WORDS:
        return SpeakerLabel("teacher", 0.85, "text_teacher_monologue")

    if t_score >= 1 and s_score == 0 and words >= 10:
        return SpeakerLabel("teacher", 0.72, "text_teacher_instructional")

    if re.search(r"\bhocam\b", normalized, re.I) and words <= STUDENT_SHORT_MAX_WORDS:
        return SpeakerLabel("student", 0.8, "text_student_hocam")

    if s_score >= 2 and t_score == 0:
        return SpeakerLabel("student", 0.75, "text_student_self_ref")

    if s_score >= 1 and t_score == 0 and words <= STUDENT_SHORT_MAX_WORDS:
        return SpeakerLabel("student", 0.65, "text_student_short")

    if t_score > s_score and t_score >= 1:
        return SpeakerLabel("teacher", 0.55, "text_teacher_weak")

    if s_score > t_score and s_score >= 1:
        return SpeakerLabel("student", 0.55, "text_student_weak")

    if prev_role == "teacher" and words <= 6 and re.search(r"\b(evet|tamam|hayır|ok)\b", normalized, re.I):
        return SpeakerLabel("student", 0.5, "text_backchannel_after_teacher")

    if prev_role == "student" and next_role == "teacher":
        return SpeakerLabel("student", 0.45, "text_context_bridge")

    return SpeakerLabel("unknown", 0.25, "text_ambiguous")


def label_segments_text(segments: list[dict]) -> list[dict]:
    """Add speaker_role fields using text-only classifier + local context."""
    preliminary = [classify_segment_text(str(s.get("text", ""))) for s in segments]
    enriched: list[dict] = []
    for i, seg in enumerate(segments):
        prev_role = preliminary[i - 1].role if i > 0 else None
        next_role = preliminary[i + 1].role if i + 1 < len(segments) else None
        label = classify_segment_text(str(seg.get("text", "")), prev_role=prev_role, next_role=next_role)
        enriched.append(
            {
                **seg,
                "speaker_role": label.role,
                "speaker_confidence": round(label.confidence, 2),
                "speaker_method": label.method,
            }
        )
    return enriched


def merge_diarization_labels(
    segments: list[dict],
    diarization_turns: list[dict],
    *,
    teacher_speaker: str,
    focal_student_speaker: str,
) -> list[dict]:
    """Map pyannote speaker ids onto transcript segments by temporal overlap."""
    role_map = {
        teacher_speaker: "teacher",
        focal_student_speaker: "student",
    }

    def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
        return max(0.0, min(a_end, b_end) - max(a_start, b_start))

    enriched: list[dict] = []
    for seg in segments:
        start = float(seg["start"])
        end = float(seg["end"])
        best_speaker = None
        best_overlap = 0.0
        for turn in diarization_turns:
            ov = overlap(start, end, float(turn["start"]), float(turn["end"]))
            if ov > best_overlap:
                best_overlap = ov
                best_speaker = turn["speaker"]
        role = role_map.get(best_speaker, "classmate" if best_speaker else "unknown")
        confidence = 0.9 if best_overlap > 0.3 else 0.5 if best_overlap > 0 else 0.2
        enriched.append(
            {
                **seg,
                "speaker_id": best_speaker,
                "speaker_role": role,
                "speaker_confidence": round(confidence, 2),
                "speaker_method": "diarization_overlap",
            }
        )
    return enriched


def identify_teacher_cluster(diarization_turns: list[dict], segments: list[dict]) -> str:
    """Pick the diarization cluster most likely to be the instructor."""
    if not diarization_turns:
        raise ValueError("No diarization turns")

    talk_time: dict[str, float] = {}
    text_hits: dict[str, int] = {}
    for turn in diarization_turns:
        sid = turn["speaker"]
        talk_time[sid] = talk_time.get(sid, 0.0) + float(turn["end"]) - float(turn["start"])

    for seg in segments:
        start, end = float(seg["start"]), float(seg["end"])
        text = str(seg.get("text", ""))
        if pattern_score(text, TEACHER_PATTERNS) == 0:
            continue
        best_speaker = None
        best_overlap = 0.0
        for turn in diarization_turns:
            ov = max(0.0, min(end, float(turn["end"])) - max(start, float(turn["start"])))
            if ov > best_overlap:
                best_overlap = ov
                best_speaker = turn["speaker"]
        if best_speaker:
            text_hits[best_speaker] = text_hits.get(best_speaker, 0) + 1

    ranked = sorted(
        talk_time,
        key=lambda sid: (text_hits.get(sid, 0), talk_time[sid]),
        reverse=True,
    )
    return ranked[0]


def identify_focal_student_cluster(
    diarization_turns: list[dict],
    segments: list[dict],
    *,
    teacher_speaker: str,
) -> str | None:
    """Second-most active cluster with student lexical cues, excluding teacher."""
    student_scores: dict[str, float] = {}
    for seg in segments:
        text = str(seg.get("text", ""))
        if pattern_score(text, STUDENT_PATTERNS) == 0:
            continue
        start, end = float(seg["start"]), float(seg["end"])
        for turn in diarization_turns:
            if turn["speaker"] == teacher_speaker:
                continue
            ov = max(0.0, min(end, float(turn["end"])) - max(start, float(turn["start"])))
            if ov > 0:
                student_scores[turn["speaker"]] = student_scores.get(turn["speaker"], 0.0) + ov
    if not student_scores:
        return None
    return max(student_scores, key=student_scores.get)
