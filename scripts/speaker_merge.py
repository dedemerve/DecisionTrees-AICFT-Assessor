"""Merge mlx transcripts with hybrid diarization speaker clusters (v2)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from speaker_role import (
    CLASSMATE_PATTERNS,
    STUDENT_PATTERNS,
    TEACHER_PATTERNS,
    classify_segment_text,
    pattern_score,
    word_count,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_RULES_PATH = REPO_ROOT / "calibration" / "speaker_merge_rules.json"

INSTRUCTIONAL_TEACHER_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bmakine\b",
        r"\böğrenme",
        r"\böğrencisi\b",
        r"\byapay zeka",
        r"\byakay zeka",
        r"\bveri\b",
        r"\bkarar ağac",
        r"\btavsiye edilebilir",
        r"\beğitim\b",
        r"\btest\b",
        r"\bemit\b",
        r"\bklasifikasyon\b",
        r"\bconfusion\b",
        r"\bsensitivity\b",
        r"\bduyarlık\b",
        r"\bölçüm\b",
        r"\bmodel\b",
        r"\bdeğişken\b",
        r"\bgrafik\b",
        r"\bkodep\b",
        r"\bcodap\b",
        r"\bçalışma kâğıdı\b",
        r"\bsoru\b",
        r"\barkadaşlar\b",
        r"\bşimdi\b",
        r"\bbakalım\b",
        r"\bgeçelim\b",
    ]
]

STRONG_TEACHER_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\barkadaşlar\b",
        r"\bsevgili arkadaşlar\b",
        r"\bherkes\b",
        r"\başlayalım\b",
        r"\bcevaplayın\b",
        r"\bbirinci soru\b",
        r"\bikinci soru\b",
        r"\btamam mı\b",
    ]
]

FOCAL_STUDENT_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"\bhocam\b",
        r"\bben\b",
        r"\bbenim\b",
        r"\byapamad",
        r"\bçalışmıyor\b",
        r"\banlamadım\b",
        r"\bbizde\b",
        r"\bbende\b",
        r"\bkanka\b",
        r"\bsoruyorum\b",
        r"\bevet hocam\b",
        r"\bgelmedi\b",
        r"\byardım\b",
        r"\bkodep\b",
        r"\bcodap\b",
        r"\bemit\b",
        r"\bgrafik\b",
    ]
]


@dataclass
class MergeRules:
    version: str = "2"
    max_gap_seconds: float = 18.0
    interpolate_max_gap_seconds: float = 35.0
    review_confidence_threshold: float = 0.5
    flag_unknown: bool = True
    flag_role_flips: bool = True
    hocam_max_words: int = 18
    hocam_teacher_pattern_max: int = 1
    instructional_weak_min: int = 2
    instructional_strong_min: int = 1
    instructional_strong_requires_teacher_patterns: int = 1
    monologue_min_words: int = 12
    bridge_gap_seconds: float = 8.0
    lecture_gap_seconds: float = 20.0
    lecture_sandwich_gap_seconds: float = 15.0
    classmate_name_patterns: list[re.Pattern] = field(default_factory=list)


@dataclass
class RoleMapping:
    teacher_speaker: str | None
    focal_speaker: str | None
    focal_pt_student_id: str
    speaker_roles: dict[str, str]


def load_merge_rules(path: Path | None = None) -> MergeRules:
    rules_path = path or DEFAULT_RULES_PATH
    if not rules_path.is_file():
        return MergeRules()
    raw = json.loads(rules_path.read_text(encoding="utf-8"))
    classmate_names = [
        re.compile(re.escape(name), re.I) for name in raw.get("classmate_name_patterns", [])
    ]
    pick = raw.get("diarization_pick", {})
    review = raw.get("review", {})
    focal = raw.get("focal_pt", {})
    teacher = raw.get("teacher", {})
    context = raw.get("context", {})
    return MergeRules(
        version=str(raw.get("version", "2")),
        max_gap_seconds=float(pick.get("max_gap_seconds", 18.0)),
        interpolate_max_gap_seconds=float(pick.get("interpolate_max_gap_seconds", 35.0)),
        review_confidence_threshold=float(review.get("confidence_threshold", 0.5)),
        flag_unknown=bool(review.get("flag_unknown", True)),
        flag_role_flips=bool(review.get("flag_role_flips", True)),
        hocam_max_words=int(focal.get("hocam_max_words", 18)),
        hocam_teacher_pattern_max=int(focal.get("hocam_teacher_pattern_max", 1)),
        instructional_weak_min=int(teacher.get("instructional_weak_min", 2)),
        instructional_strong_min=int(teacher.get("instructional_strong_min", 1)),
        instructional_strong_requires_teacher_patterns=int(
            teacher.get("instructional_strong_requires_teacher_patterns", 1)
        ),
        monologue_min_words=int(teacher.get("monologue_min_words", 12)),
        bridge_gap_seconds=float(context.get("bridge_gap_seconds", 8.0)),
        lecture_gap_seconds=float(context.get("lecture_gap_seconds", 20.0)),
        lecture_sandwich_gap_seconds=float(context.get("lecture_sandwich_gap_seconds", 15.0)),
        classmate_name_patterns=classmate_names or list(CLASSMATE_PATTERNS),
    )


def overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def get_hybrid_timeline(hybrid: dict[str, Any]) -> list[dict]:
    """Return diarization slices (v2 ``timeline`` or legacy ``segments``)."""
    timeline = hybrid.get("timeline")
    if timeline:
        return timeline
    return hybrid.get("segments") or []


def build_role_mapping(hybrid: dict[str, Any], focal_pt_student_id: str) -> RoleMapping:
    labeling = hybrid.get("speaker_labeling") or {}
    teacher = labeling.get("teacher_speaker")
    focal = labeling.get("focal_student_speaker")
    profiles = labeling.get("profiles") or {}
    speakers = labeling.get("speakers") or []

    speaker_roles: dict[str, str] = {}
    for sid, profile in profiles.items():
        speaker_roles[sid] = profile.get("resolved_role", "classmate")
    for row in speakers:
        sid = row.get("speaker_id")
        if sid:
            speaker_roles[sid] = row.get("role", speaker_roles.get(sid, "classmate"))

    if teacher:
        speaker_roles[teacher] = "teacher"
    if focal:
        speaker_roles[focal] = "student"

    return RoleMapping(
        teacher_speaker=teacher,
        focal_speaker=focal,
        focal_pt_student_id=focal_pt_student_id,
        speaker_roles=speaker_roles,
    )


def expand_diarization_timeline(
    diar_segments: list[dict],
    *,
    max_bridge_gap: float,
) -> list[dict]:
    """Bridge small gaps between same-speaker diarization slices."""
    if not diar_segments:
        return []
    ordered = sorted(diar_segments, key=lambda s: float(s["start"]))
    expanded: list[dict] = []
    for seg in ordered:
        expanded.append(dict(seg))
    for i in range(1, len(expanded)):
        prev = expanded[i - 1]
        cur = expanded[i]
        if prev.get("speaker_id") and prev.get("speaker_id") == cur.get("speaker_id"):
            gap = float(cur["start"]) - float(prev["end"])
            if 0 < gap <= max_bridge_gap:
                prev["end"] = cur["start"]
    return expanded


def pick_speaker_id(
    start: float,
    end: float,
    diar_segments: list[dict],
    rules: MergeRules,
) -> tuple[str | None, float, str]:
    """Return (speaker_id, confidence, method)."""
    timeline = expand_diarization_timeline(diar_segments, max_bridge_gap=rules.bridge_gap_seconds)
    best_id: str | None = None
    best_ov = 0.0
    seg_dur = max(0.01, end - start)

    for dseg in timeline:
        sid = dseg.get("speaker_id")
        if not sid:
            continue
        ov = overlap(start, end, float(dseg["start"]), float(dseg["end"]))
        if ov > best_ov:
            best_ov = ov
            best_id = sid

    if best_id and best_ov > 0:
        conf = min(0.95, 0.55 + (best_ov / seg_dur) * 0.4)
        return best_id, conf, "diarization_overlap"

    mid = (start + end) / 2.0
    nearest: tuple[str | None, float] = (None, rules.max_gap_seconds + 1.0)
    for dseg in timeline:
        sid = dseg.get("speaker_id")
        if not sid:
            continue
        dmid = (float(dseg["start"]) + float(dseg["end"])) / 2.0
        dist = abs(mid - dmid)
        if dist < nearest[1]:
            nearest = (sid, dist)

    if nearest[0] and nearest[1] <= rules.max_gap_seconds:
        conf = max(0.35, 0.65 - nearest[1] / rules.max_gap_seconds * 0.25)
        return nearest[0], conf, "diarization_nearest"

    # Gap interpolation between bracketing diarization segments
    before = None
    after = None
    for dseg in timeline:
        if float(dseg["end"]) <= mid:
            before = dseg
        if float(dseg["start"]) >= mid and after is None:
            after = dseg
            break
    if before and after:
        gap = float(after["start"]) - float(before["end"])
        if gap > 0 and gap <= rules.interpolate_max_gap_seconds:
            sid = before.get("speaker_id") or after.get("speaker_id")
            if sid:
                conf = max(0.3, 0.55 - gap / rules.interpolate_max_gap_seconds * 0.2)
                return sid, conf, "diarization_gap_interpolate"
    if before and (mid - float(before["end"])) <= rules.interpolate_max_gap_seconds:
        sid = before.get("speaker_id")
        if sid:
            return sid, 0.42, "diarization_tail_interpolate"
    if after and (float(after["start"]) - mid) <= rules.interpolate_max_gap_seconds:
        sid = after.get("speaker_id")
        if sid:
            return sid, 0.42, "diarization_head_interpolate"

    return None, 0.0, "unmapped"


def role_from_speaker(speaker_id: str | None, mapping: RoleMapping) -> tuple[str, float, str]:
    if not speaker_id:
        return "unknown", 0.0, "no_speaker"
    role = mapping.speaker_roles.get(speaker_id, "classmate")
    if speaker_id == mapping.teacher_speaker:
        return "teacher", 0.92, "cluster_teacher"
    if speaker_id == mapping.focal_speaker:
        return "student", 0.88, "cluster_focal_pt"
    return role, 0.6, "cluster_classmate"


def instructional_teacher_score(text: str) -> int:
    return pattern_score(text, INSTRUCTIONAL_TEACHER_PATTERNS)


def strong_teacher_score(text: str) -> int:
    return pattern_score(text, STRONG_TEACHER_PATTERNS)


def is_classmate_text(text: str, rules: MergeRules) -> bool:
    if pattern_score(text, rules.classmate_name_patterns) >= 1:
        return pattern_score(text, FOCAL_STUDENT_PATTERNS) == 0
    return pattern_score(text, CLASSMATE_PATTERNS) >= 1 and pattern_score(text, FOCAL_STUDENT_PATTERNS) == 0


def is_focal_student_text(text: str, rules: MergeRules) -> bool:
    if re.search(r"\bhocam\b", text, re.I) and word_count(text) <= rules.hocam_max_words:
        return pattern_score(text, TEACHER_PATTERNS) <= rules.hocam_teacher_pattern_max
    if pattern_score(text, FOCAL_STUDENT_PATTERNS) >= 1 and pattern_score(text, TEACHER_PATTERNS) == 0:
        return True
    label = classify_segment_text(text)
    return label.role == "student" and label.confidence >= 0.65


def is_likely_teacher_text(text: str, rules: MergeRules) -> bool:
    if is_focal_student_text(text, rules) or is_classmate_text(text, rules):
        return False
    if (
        instructional_teacher_score(text) >= rules.instructional_strong_min
        and pattern_score(text, TEACHER_PATTERNS) >= 1
        and pattern_score(text, STUDENT_PATTERNS) == 0
    ):
        return True
    if (
        instructional_teacher_score(text) >= rules.instructional_weak_min
        and word_count(text) >= rules.monologue_min_words
    ):
        return pattern_score(text, STUDENT_PATTERNS) == 0
    label = classify_segment_text(text)
    return label.role == "teacher" and label.confidence >= 0.72


def apply_review_flags(segments: list[dict], rules: MergeRules) -> list[dict]:
    out = [dict(s) for s in segments]
    n = len(out)
    for i, seg in enumerate(out):
        reasons: list[str] = []
        conf = float(seg.get("speaker_confidence", 0.0))
        role = str(seg.get("speaker_role", "unknown"))
        method = str(seg.get("speaker_method", ""))

        if conf < rules.review_confidence_threshold:
            reasons.append("low_confidence")
        if rules.flag_unknown and role == "unknown":
            reasons.append("unknown_role")
        if method in {"unmapped", "diarization_gap_interpolate", "diarization_tail_interpolate"}:
            reasons.append("diarization_gap")

        if rules.flag_role_flips and 0 < i < n - 1:
            prev_role = out[i - 1].get("speaker_role")
            next_role = out[i + 1].get("speaker_role")
            gap_prev = float(seg["start"]) - float(out[i - 1]["end"])
            gap_next = float(out[i + 1]["start"]) - float(seg["end"])
            if (
                prev_role == next_role
                and role != prev_role
                and prev_role in {"teacher", "student"}
                and gap_prev < 2.0
                and gap_next < 2.0
            ):
                reasons.append("role_flip_sandwich")

        if reasons:
            seg["needs_review"] = True
            seg["review_reason"] = ",".join(sorted(set(reasons)))
        else:
            seg["needs_review"] = False
            seg.pop("review_reason", None)
    return out


def merge_transcript_segments(
    transcript_segments: list[dict],
    hybrid_segments: list[dict],
    mapping: RoleMapping,
    rules: MergeRules | None = None,
) -> list[dict]:
    rules = rules or load_merge_rules()
    merged: list[dict] = []
    for seg in transcript_segments:
        start, end = float(seg["start"]), float(seg["end"])
        text = str(seg.get("text", ""))

        speaker_id, sp_conf, sp_method = pick_speaker_id(start, end, hybrid_segments, rules)
        role, role_conf, role_method = role_from_speaker(speaker_id, mapping)

        if is_classmate_text(text, rules):
            role = "classmate"
            role_conf = 0.7
            role_method = "text_classmate_name"
        elif is_focal_student_text(text, rules):
            role = "student"
            role_conf = 0.82
            role_method = "text_focal_pt_priority"
            if mapping.focal_speaker:
                speaker_id = mapping.focal_speaker
        elif (
            instructional_teacher_score(text) >= rules.instructional_strong_min
            and word_count(text) <= 6
            and pattern_score(text, STUDENT_PATTERNS) == 0
        ):
            role = "teacher"
            role_conf = 0.74
            role_method = "text_instructional_short"
            if mapping.teacher_speaker:
                speaker_id = mapping.teacher_speaker
        else:
            text_label = classify_segment_text(text)
            if role in {"classmate", "student", "unknown"} and speaker_id != mapping.teacher_speaker:
                if is_likely_teacher_text(text, rules):
                    role = "teacher"
                    role_conf = max(role_conf, 0.72)
                    role_method = "text_override_instructional"
                    if mapping.teacher_speaker:
                        speaker_id = mapping.teacher_speaker
                elif text_label.role != "unknown" and text_label.role != role:
                    if text_label.role == "teacher" and text_label.confidence >= role_conf:
                        role = text_label.role
                        role_conf = text_label.confidence
                        role_method = f"text_override_{text_label.method}"
                        if mapping.teacher_speaker:
                            speaker_id = mapping.teacher_speaker
                    elif role == "unknown":
                        role = text_label.role
                        role_conf = text_label.confidence
                        role_method = f"text_fallback_{text_label.method}"

            if role == "unknown" or sp_method == "unmapped":
                if text_label.role != "unknown":
                    role = text_label.role
                    role_conf = text_label.confidence
                    role_method = f"text_fallback_{text_label.method}"
                elif (
                    instructional_teacher_score(text) >= rules.instructional_strong_min
                    and word_count(text) >= 6
                ):
                    role = "teacher"
                    role_conf = 0.7
                    role_method = "text_instructional_fallback"
                elif pattern_score(text, FOCAL_STUDENT_PATTERNS) >= 1:
                    role = "student"
                    role_conf = 0.65
                    role_method = "text_focal_pt_fallback"

        if (
            role in {"classmate", "unknown"}
            and "interpolate" in sp_method
            and is_likely_teacher_text(text, rules)
        ):
            role = "teacher"
            role_conf = max(role_conf, 0.66)
            role_method = "text_override_interpolate_gap"
            if mapping.teacher_speaker:
                speaker_id = mapping.teacher_speaker

        merged.append(
            {
                **seg,
                "speaker_id": speaker_id,
                "speaker_role": role,
                "speaker_confidence": round(max(role_conf, sp_conf * 0.5), 2),
                "speaker_method": role_method if role != "unknown" else sp_method,
                "focal_pt_student_id": mapping.focal_pt_student_id if role == "student" else None,
            }
        )

    merged = propagate_context_roles(merged, mapping, rules)
    merged = propagate_instructional_runs(merged, mapping, rules)
    return apply_review_flags(merged, rules)


def propagate_instructional_runs(
    segments: list[dict], mapping: RoleMapping, rules: MergeRules
) -> list[dict]:
    if not segments:
        return segments
    out = [dict(s) for s in segments]
    n = len(out)

    for i, seg in enumerate(out):
        if seg.get("speaker_role") == "teacher":
            continue
        text = str(seg.get("text", ""))
        if is_focal_student_text(text, rules) or is_classmate_text(text, rules):
            continue

        prev_teacher = False
        next_teacher = False
        if i > 0:
            gap = float(seg["start"]) - float(out[i - 1]["end"])
            prev_teacher = out[i - 1].get("speaker_role") == "teacher" and gap < rules.lecture_gap_seconds
        if i + 1 < n:
            gap = float(out[i + 1]["start"]) - float(seg["end"])
            next_teacher = out[i + 1].get("speaker_role") == "teacher" and gap < rules.lecture_gap_seconds

        if prev_teacher and next_teacher:
            seg["speaker_role"] = "teacher"
            seg["speaker_confidence"] = 0.7
            seg["speaker_method"] = "lecture_run_bridge"
            if mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker
            continue

        if not is_likely_teacher_text(text, rules) and word_count(text) > 8:
            continue

        if prev_teacher or next_teacher or is_likely_teacher_text(text, rules):
            if is_likely_teacher_text(text, rules):
                seg["speaker_role"] = "teacher"
                seg["speaker_confidence"] = 0.68
                seg["speaker_method"] = "lecture_run_instructional"
            elif word_count(text) <= 8 and (prev_teacher or next_teacher):
                seg["speaker_role"] = "teacher"
                seg["speaker_confidence"] = 0.6
                seg["speaker_method"] = "lecture_run_short"
            if seg.get("speaker_role") == "teacher" and mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker

    for i, seg in enumerate(out):
        if seg.get("speaker_role") not in {"unknown", "classmate"}:
            continue
        if i == 0 or i + 1 >= n:
            continue
        if out[i - 1].get("speaker_role") != "teacher" or out[i + 1].get("speaker_role") != "teacher":
            continue
        gap_prev = float(seg["start"]) - float(out[i - 1]["end"])
        gap_next = float(out[i + 1]["start"]) - float(seg["end"])
        if gap_prev < rules.lecture_sandwich_gap_seconds and gap_next < rules.lecture_sandwich_gap_seconds:
            seg["speaker_role"] = "teacher"
            seg["speaker_confidence"] = 0.62
            seg["speaker_method"] = "lecture_gap_fill"
            if mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker

    return out


def propagate_context_roles(
    segments: list[dict], mapping: RoleMapping, rules: MergeRules
) -> list[dict]:
    if not segments:
        return segments

    out = [dict(s) for s in segments]
    n = len(out)

    for i, seg in enumerate(out):
        if seg.get("speaker_role") != "unknown":
            continue
        text = str(seg.get("text", ""))
        prev_role = out[i - 1].get("speaker_role") if i > 0 else None
        next_role = out[i + 1].get("speaker_role") if i + 1 < n else None
        prev_sid = out[i - 1].get("speaker_id") if i > 0 else None
        next_sid = out[i + 1].get("speaker_id") if i + 1 < n else None

        if prev_role == next_role and prev_role in {"teacher", "student", "classmate"}:
            gap_prev = float(seg["start"]) - float(out[i - 1]["end"]) if i > 0 else 999
            gap_next = float(out[i + 1]["start"]) - float(seg["end"]) if i + 1 < n else 999
            if gap_prev < rules.bridge_gap_seconds and gap_next < rules.bridge_gap_seconds:
                seg["speaker_role"] = prev_role
                seg["speaker_confidence"] = 0.62
                seg["speaker_method"] = "context_bridge_same_role"
                if prev_sid and prev_sid == next_sid:
                    seg["speaker_id"] = prev_sid
                continue

        if prev_role == "teacher" and instructional_teacher_score(text) >= 1:
            seg["speaker_role"] = "teacher"
            seg["speaker_confidence"] = 0.68
            seg["speaker_method"] = "context_after_teacher_instructional"
            if not seg.get("speaker_id") and mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker
            continue

        if prev_role == "teacher" and word_count(text) <= 4:
            if re.search(r"\b(evet|tamam|hayır|ok|hı|haa)\b", text, re.I):
                seg["speaker_role"] = "student"
                seg["speaker_confidence"] = 0.55
                seg["speaker_method"] = "context_backchannel"
                if mapping.focal_speaker:
                    seg["speaker_id"] = mapping.focal_speaker
                seg["focal_pt_student_id"] = mapping.focal_pt_student_id
            continue

        if (
            instructional_teacher_score(text) >= rules.instructional_weak_min
            and word_count(text) >= rules.monologue_min_words
        ):
            seg["speaker_role"] = "teacher"
            seg["speaker_confidence"] = 0.72
            seg["speaker_method"] = "context_instructional_monologue"
            if mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker

    for i, seg in enumerate(out):
        if seg.get("speaker_role") != "unknown":
            continue
        if word_count(str(seg.get("text", ""))) > 12:
            continue
        window = out[max(0, i - 3) : min(n, i + 4)]
        teacher_neighbors = sum(1 for s in window if s.get("speaker_role") == "teacher")
        if teacher_neighbors >= 4:
            seg["speaker_role"] = "teacher"
            seg["speaker_confidence"] = 0.58
            seg["speaker_method"] = "context_teacher_island"
            if mapping.teacher_speaker:
                seg["speaker_id"] = mapping.teacher_speaker

    for seg in out:
        if seg.get("speaker_role") != "unknown":
            if seg.get("speaker_role") == "student":
                seg["focal_pt_student_id"] = mapping.focal_pt_student_id
            continue
        sid = seg.get("speaker_id")
        if sid and sid not in (mapping.teacher_speaker, mapping.focal_speaker):
            seg["speaker_role"] = "classmate"
            seg["speaker_confidence"] = 0.45
            seg["speaker_method"] = "residual_classmate_cluster"
        elif sid == mapping.focal_speaker:
            seg["speaker_role"] = "student"
            seg["focal_pt_student_id"] = mapping.focal_pt_student_id
            seg["speaker_confidence"] = 0.75
            seg["speaker_method"] = "residual_focal_cluster"

    return out


def summarize_roles(segments: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for seg in segments:
        role = str(seg.get("speaker_role", "unknown"))
        counts[role] = counts.get(role, 0) + 1
    return counts


def count_needs_review(segments: list[dict]) -> int:
    return sum(1 for s in segments if s.get("needs_review"))
