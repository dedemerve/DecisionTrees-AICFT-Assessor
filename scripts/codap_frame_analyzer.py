#!/usr/bin/env python3
"""Per-frame CODAP Arbor vision analysis using MMLA_CODAP_video_system_prompt.md.

Produces structured JSON per keyframe (screen_state, behavioral_classification,
LO3 rubric, flags, frame_quality) for direct ingestion into the research database.

Key design decisions:
  - Log windows use created_at (UTC wall clock) for alignment, not timestamp_ms.
    CODAP's timestamp_ms resets on every page reload; created_at is stable.
  - Frame selection is log-anchored by default; --all-manifest-frames analyzes
    every already-extracted keyframe without a second API-side filter.
  - pixel_change_percentage from the extraction manifest is included in every
    prompt so the model has motion context for is_duplicate_candidate judgement.
  - All model outputs are validated against schema/codap_frame_analysis.schema.json
    before writing to disk. Validation failures are flagged but not fatal.
  - Durable persistence is mandatory for live runs: after every completed frame
    the analyzer atomically rewrites student_codap_frame_analyses.json and
    appends the same result to student_codap_frame_analyses.jsonl. Interrupted
    runs therefore never lose completed frames. Resume is the default unless
    --overwrite is passed.
  - --reextract triggers diarization + full_multimodal re-extraction for students
    whose manifests lack speech anchors but whose audio files are present.
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = Path(__file__).resolve().parent
for _p in (str(SCRIPTS_DIR), str(REPO_ROOT)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from codap_alignment import (  # noqa: E402
    estimate_video_start_utc,
    log_window_text_aligned,
    meaningful_event_timestamps_s,
)
from codap_log_window import (  # noqa: E402
    format_student_stats,
    load_log_dataframe,
    log_window_text,
    student_session_stats,
)
from multimodal_cognitive_assessor import DEFAULT_AUDIO_ROOT, load_json  # noqa: E402

LOGGER = logging.getLogger("codap_frame_analyzer")

DEFAULT_PROMPT = REPO_ROOT / "prompts" / "MMLA_CODAP_video_system_prompt.md"
DEFAULT_SCHEMA = REPO_ROOT / "schema" / "codap_frame_analysis.schema.json"
DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-5"
DEFAULT_MODEL_OPENAI = "gpt-4o"
DEFAULT_VIDEO_ROOT_28APR = REPO_ROOT / "data_sources_2026" / "28 April CODAP Arbor Screen Recordings"
DEFAULT_VIDEO_ROOT_21APR = REPO_ROOT / "data_sources_2026" / "21 April CODAP Arbor Screen Recordings"

SNAP_WINDOW_S = 30.0
GAP_FILL_SECONDS = 120.0


# ─────────────────────────────────────────────────────────────
# schema validation
# ─────────────────────────────────────────────────────────────

def load_output_schema(path: Path | None = None) -> dict[str, Any] | None:
    p = path or DEFAULT_SCHEMA
    if not p.is_file():
        LOGGER.warning("Output schema not found: %s — validation disabled", p)
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def validate_frame_analysis(
    data: dict[str, Any],
    schema: dict[str, Any] | None,
) -> list[str]:
    """Return list of validation error messages (empty = valid)."""
    if schema is None:
        return []
    try:
        import jsonschema
        v = jsonschema.Draft7Validator(schema)
        return [e.message for e in sorted(v.iter_errors(data), key=str)]
    except ImportError:
        LOGGER.warning("jsonschema not installed — skipping schema validation")
        return []


# ─────────────────────────────────────────────────────────────
# image helpers
# ─────────────────────────────────────────────────────────────

def pil_to_base64_jpeg(path: Path, max_width: int = 1600) -> str:
    from PIL import Image

    img = Image.open(path).convert("RGB")
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


# ─────────────────────────────────────────────────────────────
# prompt helpers
# ─────────────────────────────────────────────────────────────

def load_system_prompt(path: Path | None = None) -> str:
    prompt_path = path or DEFAULT_PROMPT
    if not prompt_path.is_file():
        raise FileNotFoundError(f"System prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")


def frame_number_from_id(frame_id: str) -> int:
    m = re.search(r"(\d+)$", frame_id)
    return int(m.group(1)) if m else 0


def build_user_prompt(
    *,
    student_id: str,
    session_label: str,
    frame_id: str,
    timestamp_ms: int,
    pixel_change_pct: float | None,
    log_window: str,
    stats_text: str,
) -> str:
    frame_num = frame_number_from_id(frame_id)
    motion_line = (
        f"HAREKET_YUZDESI: {pixel_change_pct:.2f}%\n"
        if pixel_change_pct is not None
        else ""
    )
    return (
        f"OGRENCI: {student_id}\n"
        f"OTURUM: {session_label}\n"
        f"KARE: {frame_num}\n"
        f"TIMESTAMP_MS: {timestamp_ms}\n"
        f"{motion_line}"
        f"\n"
        f"LOG_PENCERESI (+-10 sn):\n"
        f"{log_window}\n"
        f"\n"
        f"OGRENCI ISTATISTIKLERI:\n"
        f"{stats_text}\n"
        f"\n"
        f"[EKRAN GORUNTUSU]\n"
    )


# ─────────────────────────────────────────────────────────────
# frame selection
# ─────────────────────────────────────────────────────────────

def select_frames_log_anchored(
    manifest: dict[str, Any],
    log_df: Any | None,
    student_id: str,
    video_start_utc: Any | None,
    session_date: str,
    *,
    gap_fill_seconds: float = GAP_FILL_SECONDS,
    max_frames: int = 0,
) -> list[dict[str, Any]]:
    """Select manifest frames anchored to meaningful log events.

    Strategy:
      1. Snap each meaningful log event to its nearest manifest frame
         (within SNAP_WINDOW_S seconds).
      2. Fill gaps longer than gap_fill_seconds with uniformly spaced frames.
      3. If no log is available or alignment fails, fall back to uniform spread.
    """
    all_frames = sorted(
        manifest.get("frames", []),
        key=lambda f: float(f["source_timestamp_seconds"]),
    )
    if not all_frames:
        return []

    # Always include frames that were targeted at any log action (emit, contextual, etc.)
    forced_indices: set[int] = {
        i for i, f in enumerate(all_frames)
        if "_targeted" in (f.get("extraction_trigger_reason") or "")
        or (f.get("metrics") or {}).get("high_value_interaction_zone") is True
    }

    if log_df is None or video_start_utc is None:
        LOGGER.debug("[%s] No log/alignment — uniform spread", student_id)
        return _uniform_spread(all_frames, max_frames)

    events = meaningful_event_timestamps_s(
        log_df,
        student_id,
        video_start_utc,
        session_date=session_date,
    )
    if not events:
        LOGGER.debug("[%s] No anchor events — uniform spread", student_id)
        return _uniform_spread(all_frames, max_frames)

    frame_times = [float(f["source_timestamp_seconds"]) for f in all_frames]
    n = len(all_frames)
    selected: set[int] = set()

    for event in events:
        t = event["timestamp_s"]
        best_i = min(range(n), key=lambda i: abs(frame_times[i] - t))
        if abs(frame_times[best_i] - t) <= SNAP_WINDOW_S:
            selected.add(best_i)

    # Always keep targeted emit frames regardless of snap result
    selected |= forced_indices

    # Always include high-motion frames (log-independent screen changes).
    # These capture what the student did that left NO log trace — e.g. reading
    # output, scrolling, or any CODAP interaction not instrumented by Arbor.
    HIGH_MOTION_THRESHOLD = 5.0  # percent pixel change
    motion_indices: set[int] = set()
    for i, f in enumerate(all_frames):
        pct = (f.get("metrics") or f).get("pixel_change_percentage")
        if pct is not None and float(pct) >= HIGH_MOTION_THRESHOLD:
            motion_indices.add(i)
    selected |= motion_indices

    if not selected:
        LOGGER.debug("[%s] No events snapped to manifest — uniform spread", student_id)
        return _uniform_spread(all_frames, max_frames)

    # ensure first and last frame are always included as boundaries
    selected |= {0, n - 1}

    # gap fill between consecutive selected frames
    boundaries = sorted(selected)
    extra: set[int] = set()
    for a, b in zip(boundaries, boundaries[1:]):
        gap = frame_times[b] - frame_times[a]
        if gap > gap_fill_seconds:
            n_fill = max(1, int(gap / gap_fill_seconds) - 1)
            step = (b - a) / (n_fill + 1)
            for k in range(1, n_fill + 1):
                fill_i = min(int(round(a + k * step)), n - 1)
                extra.add(fill_i)
    selected |= extra

    result = [all_frames[i] for i in sorted(selected)]
    LOGGER.debug(
        "[%s] log-anchored: %d log events + %d high-motion -> %d frames selected "
        "(gap_fill adds %d, emit_targeted=%d)",
        student_id,
        len(events),
        len(motion_indices),
        len(result),
        len(extra),
        len(forced_indices),
    )

    if max_frames > 0 and len(result) > max_frames:
        result = _uniform_spread(result, max_frames)
    return result


def _uniform_spread(frames: list[dict[str, Any]], max_frames: int) -> list[dict[str, Any]]:
    if max_frames <= 0 or len(frames) <= max_frames:
        return frames
    if max_frames == 1:
        return [frames[len(frames) // 2]]
    step = (len(frames) - 1) / (max_frames - 1)
    indices = sorted({int(round(i * step)) for i in range(max_frames)})
    return [frames[i] for i in indices]


# ─────────────────────────────────────────────────────────────
# API clients
# ─────────────────────────────────────────────────────────────

def parse_analysis_json(raw: str) -> dict[str, Any]:
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


# Sonnet 5 pricing (per token)
_COST_INPUT_PER_TOKEN        = 3.0 / 1_000_000   # claude-sonnet-5 standard input
_COST_OUTPUT_PER_TOKEN       = 15.0 / 1_000_000  # claude-sonnet-5 output
_COST_CACHE_READ_PER_TOKEN   = 0.30 / 1_000_000  # cache read = 10% of input price
_COST_CACHE_WRITE_PER_TOKEN  = 3.75 / 1_000_000  # cache write = 125% of input price


def call_anthropic(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    image_b64: str,
    *,
    max_retries: int = 3,
) -> tuple[dict[str, Any], dict[str, int]]:
    """Returns (parsed_result, usage_dict) where usage has input_tokens/output_tokens."""
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=3000,
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_b64,
                                },
                            },
                            {"type": "text", "text": user_prompt},
                        ],
                    }
                ],
            )
            text_block = next((b for b in response.content if hasattr(b, "text")), None)
            if text_block is None:
                raise ValueError("No text block in response")
            usage = {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "cache_read_input_tokens": getattr(response.usage, "cache_read_input_tokens", 0) or 0,
                "cache_creation_input_tokens": getattr(response.usage, "cache_creation_input_tokens", 0) or 0,
            }
            return parse_analysis_json(text_block.text), usage
        except Exception as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"Anthropic analysis failed after {max_retries} attempts: {last_err}")


def call_openai(
    client: Any,
    model: str,
    system_prompt: str,
    user_prompt: str,
    image_b64: str,
    *,
    max_retries: int = 3,
) -> dict[str, Any]:
    data_url = f"data:image/jpeg;base64,{image_b64}"
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                max_tokens=2000,
                temperature=0.0,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "image_url", "image_url": {"url": data_url}},
                        ],
                    },
                ],
                response_format={"type": "json_object"},
            )
            raw = response.choices[0].message.content or "{}"
            return parse_analysis_json(raw)
        except Exception as exc:
            last_err = exc
            time.sleep(2**attempt)
    raise RuntimeError(f"OpenAI analysis failed after {max_retries} attempts: {last_err}")


def make_client(provider: str) -> tuple[Any, str]:
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY is not set")
        from openai import OpenAI
        return OpenAI(api_key=api_key), DEFAULT_MODEL_OPENAI
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY is not set")
    import anthropic
    return anthropic.Anthropic(api_key=api_key), DEFAULT_MODEL_ANTHROPIC


# ─────────────────────────────────────────────────────────────
# dry-run mock
# ─────────────────────────────────────────────────────────────

def mock_analysis(
    student_id: str,
    session_date: str,
    frame_entry: dict[str, Any],
) -> dict[str, Any]:
    ts_ms = int(round(float(frame_entry["source_timestamp_seconds"]) * 1000))
    return {
        "student_id": student_id,
        "session_date": session_date,
        "frame_number": frame_number_from_id(frame_entry["frame_id"]),
        "timestamp_ms": ts_ms,
        "screen_state": None,
        "log_visual_match": None,
        "behavioral_classification": None,
        "cognitive_indicators": None,
        "aicft_rubric": None,
        "flags": None,
        "frame_quality": {
            "is_transition_frame": False,
            "is_duplicate_candidate": False,
            "occlusion_present": False,
            "occlusion_note": None,
            "analysis_confidence": "low",
            "confidence_reason": "DRY_RUN — vision API not invoked.",
        },
        "_dry_run": True,
        "frame_id": frame_entry["frame_id"],
    }


# ─────────────────────────────────────────────────────────────
# re-extraction helpers
# ─────────────────────────────────────────────────────────────

def needs_reextraction(student_dir: Path, student_id: str) -> bool:
    """True if manifest exists but has no speech anchors and audio is present."""
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        m = load_json(manifest_path)
        summary = m.get("summary", {})
        has_speech = summary.get("speech_anchor_count", 0) > 0
        if has_speech:
            return False
        wav = student_dir / f"{student_id}.wav"
        return wav.is_file()
    except Exception:
        return False


def run_diarization(
    student_id: str,
    audio_root: Path,
    *,
    verbose: bool = False,
) -> bool:
    """Run hybrid_diarization.py for one student. Returns True on success."""
    diariz_path = SCRIPTS_DIR / "hybrid_diarization.py"
    if not diariz_path.is_file():
        LOGGER.error("hybrid_diarization.py not found: %s", diariz_path)
        return False
    cmd = [
        sys.executable, str(diariz_path),
        "--audio-root", str(audio_root),
        student_id,
    ]
    LOGGER.info("[%s] Running diarization: %s", student_id, " ".join(cmd))
    result = subprocess.run(cmd, capture_output=not verbose)
    if result.returncode != 0:
        LOGGER.error("[%s] Diarization failed (exit %d)", student_id, result.returncode)
        if not verbose and result.stderr:
            LOGGER.debug(result.stderr.decode(errors="replace")[-1000:])
        return False
    return True


def run_reextraction(
    student_id: str,
    audio_root: Path,
    video_root: Path | None,
    *,
    verbose: bool = False,
) -> bool:
    """Run dynamic_video_analytics.py for one student. Returns True on success."""
    dva_path = SCRIPTS_DIR / "dynamic_video_analytics.py"
    if not dva_path.is_file():
        LOGGER.error("dynamic_video_analytics.py not found: %s", dva_path)
        return False
    cmd = [
        sys.executable, str(dva_path),
        "--audio-root", str(audio_root),
        student_id,
    ]
    if video_root and video_root.is_dir():
        cmd += ["--video-root", str(video_root)]
    LOGGER.info("[%s] Re-extracting frames: %s", student_id, " ".join(cmd))
    result = subprocess.run(cmd, capture_output=not verbose)
    if result.returncode != 0:
        LOGGER.error("[%s] Re-extraction failed (exit %d)", student_id, result.returncode)
        if not verbose and result.stderr:
            LOGGER.debug(result.stderr.decode(errors="replace")[-1000:])
        return False
    return True


# ─────────────────────────────────────────────────────────────
# per-student analysis
# ─────────────────────────────────────────────────────────────

def _is_real_analysis(item: dict[str, Any]) -> bool:
    """True when an analysis entry is a real API result, not a dry-run placeholder."""
    return bool(item) and not item.get("_dry_run") and bool(item.get("frame_id"))


# Keys that appear only in the legacy nested schema (pre-flat-schema migration).
_OLD_SCHEMA_KEYS = frozenset({"screen_state", "behavioral_classification", "cognitive_indicators"})


def _is_old_schema_format(record: dict[str, Any]) -> bool:
    """True when a record uses the old nested schema format rather than the current flat schema."""
    return bool(_OLD_SCHEMA_KEYS & record.keys())


def _dedupe_analyses(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for item in items:
        if not isinstance(item, dict) or not _is_real_analysis(item):
            continue
        fid = str(item["frame_id"])
        if fid not in by_id:
            order.append(fid)
        by_id[fid] = item
    return [by_id[fid] for fid in order]


def jsonl_path_for(analysis_path: Path) -> Path:
    return analysis_path.with_suffix(analysis_path.suffix + "l")


def load_resume_analyses(path: Path) -> list[dict[str, Any]]:
    """Load previously completed frame analyses for resume.

    Prefer the aggregated JSON; if missing/empty/corrupt, rebuild from the
    append-only JSONL sidecar so interrupted runs remain recoverable.
    """
    loaded: list[dict[str, Any]] = []
    if path.is_file():
        try:
            data = load_json(path)
            loaded = [x for x in (data.get("frame_analyses") or []) if isinstance(x, dict)]
        except Exception as exc:
            LOGGER.warning("Could not read resume JSON %s: %s", path, exc)

    if not _dedupe_analyses(loaded):
        side = jsonl_path_for(path)
        if side.is_file():
            rows: list[dict[str, Any]] = []
            try:
                for line in side.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    rows.append(json.loads(line))
                loaded = rows
                LOGGER.info(
                    "Rebuilt %d frame analyse(s) from JSONL sidecar %s",
                    len(_dedupe_analyses(loaded)),
                    side.name,
                )
            except Exception as exc:
                LOGGER.warning("Could not read resume JSONL %s: %s", side, exc)

    deduped = _dedupe_analyses(loaded)

    old_format = [r for r in deduped if _is_old_schema_format(r)]
    if old_format:
        old_ids = [r["frame_id"] for r in old_format]
        LOGGER.warning(
            "Found %d record(s) in legacy nested schema format — these will be re-analyzed "
            "on this run. Frame IDs: %s",
            len(old_format),
            old_ids,
        )
        deduped = [r for r in deduped if not _is_old_schema_format(r)]

    return deduped


def ensure_jsonl_sidecar(analysis_path: Path, analyses: list[dict[str, Any]]) -> None:
    """If JSONL is missing, rebuild it from the in-memory analyses (one-time backfill)."""
    side = jsonl_path_for(analysis_path)
    if side.is_file() or not analyses:
        return
    side.parent.mkdir(parents=True, exist_ok=True)
    with side.open("w", encoding="utf-8") as fh:
        for item in analyses:
            fh.write(json.dumps(item, ensure_ascii=False) + "\n")
        fh.flush()
        os.fsync(fh.fileno())
    LOGGER.info(
        "Backfilled JSONL sidecar with %d frame(s) -> %s",
        len(analyses),
        side.name,
    )


def write_analysis_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    """Atomically rewrite the aggregated JSON with fsync durability."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    tmp.replace(path)


def append_frame_jsonl(path: Path, result: dict[str, Any]) -> None:
    """Append one completed frame result to the durable JSONL sidecar."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(result, ensure_ascii=False) + "\n"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(line)
        fh.flush()
        os.fsync(fh.fileno())


def persist_frame_result(
    analysis_path: Path,
    payload: dict[str, Any],
    result: dict[str, Any],
) -> None:
    """Always persist one frame to both JSONL and aggregated JSON."""
    append_frame_jsonl(jsonl_path_for(analysis_path), result)
    write_analysis_checkpoint(analysis_path, payload)


def analyze_student(
    student_dir: Path,
    student_id: str,
    *,
    session_date: str,
    session_label: str,
    log_df: Any | None,
    video_path: Path | None,
    system_prompt: str,
    output_schema: dict[str, Any] | None,
    provider: str,
    model_override: str | None,
    max_frames: int,
    dry_run: bool,
    all_manifest_frames: bool = False,
    output_path: Path | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    manifest_path = student_dir / f"{student_id}_video_extraction_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = load_json(manifest_path)

    frames_dir = student_dir / f"{student_id}_frames"
    if not frames_dir.is_dir():
        raise FileNotFoundError(frames_dir)

    # alignment
    video_start_utc, alignment_method = estimate_video_start_utc(
        video_path, log_df if log_df is not None else _empty_df(),
        student_id, session_date,
    )
    if video_start_utc is not None:
        LOGGER.info(
            "[%s] video_start_utc=%s (method=%s)",
            student_id, video_start_utc.isoformat(), alignment_method,
        )
    else:
        LOGGER.warning("[%s] video_start_utc unavailable — log windows will be empty", student_id)

    # session stats
    stats = (
        student_session_stats(log_df, student_id)
        if log_df is not None
        else {"total_emit_tree_data": 0, "last_accuracy": None, "max_duration_minutes": None, "total_actions": 0}
    )
    stats_text = format_student_stats(stats)

    # frame selection
    # Extract already chose meaningful keyframes. --all-manifest-frames skips the
    # second log-anchored filter and analyzes every manifest frame.
    if all_manifest_frames:
        selected = sorted(
            manifest.get("frames", []),
            key=lambda f: float(f["source_timestamp_seconds"]),
        )
        if max_frames > 0 and len(selected) > max_frames:
            selected = _uniform_spread(selected, max_frames)
        selection_mode = "all-manifest-frames"
    else:
        selected = select_frames_log_anchored(
            manifest,
            log_df,
            student_id,
            video_start_utc,
            session_date,
            gap_fill_seconds=GAP_FILL_SECONDS,
            max_frames=max_frames,
        )
        selection_mode = (
            "log-anchored"
            if (log_df is not None and video_start_utc is not None)
            else "uniform"
        )
    if not selected:
        raise ValueError(f"No frames selected for {student_id}")

    LOGGER.info(
        "[%s] %d frames selected from %d total (mode: %s)",
        student_id,
        len(selected),
        len(manifest.get("frames", [])),
        selection_mode,
    )

    if output_path is None and not dry_run:
        raise ValueError("output_path is required for live analysis so every frame can be persisted")

    client = None
    model = model_override or ""
    if not dry_run:
        client, model = make_client(provider)
        if model_override:
            model = model_override

    analyses: list[dict[str, Any]] = []
    done_ids: set[str] = set()
    if resume and output_path is not None and not dry_run:
        analyses = load_resume_analyses(output_path)
        done_ids = {str(a["frame_id"]) for a in analyses}
        if done_ids:
            ensure_jsonl_sidecar(output_path, analyses)
            LOGGER.info(
                "[%s] Resume: keeping %d completed frame(s) from disk, skipping those IDs",
                student_id,
                len(done_ids),
            )

    validation_errors_total = sum(1 for a in analyses if a.get("_validation_errors"))

    def _payload(*, in_progress: bool) -> dict[str, Any]:
        return {
            "student_id": student_id,
            "session_date": session_date,
            "session_label": session_label,
            "prompt_file": str(DEFAULT_PROMPT.relative_to(REPO_ROOT)),
            "provider": provider if not dry_run else "dry_run",
            "model": model if not dry_run else None,
            "assessed_at": datetime.now(timezone.utc).isoformat(),
            "alignment": {
                "video_start_utc": video_start_utc.isoformat() if video_start_utc else None,
                "method": alignment_method,
                "note": (
                    "video_start_utc is an approximation (first log event on session date). "
                    "Offset from actual recording start is unknown but typically < 60 s."
                ) if alignment_method == "first_log_event" else None,
            },
            "frame_selection": selection_mode if selection_mode != "uniform" else "uniform-spread",
            "frames_analyzed": len(analyses),
            "frames_selected": len(selected),
            "frames_total_in_manifest": len(manifest.get("frames", [])),
            "frames_with_validation_errors": validation_errors_total,
            "log_csv_used": log_df is not None,
            "session_stats": stats,
            "checkpoint": in_progress,
            "complete": (not in_progress) and len(analyses) >= len(selected),
            "frame_analyses": analyses,
        }

    cumulative_input_tokens  = 0
    cumulative_output_tokens = 0
    cumulative_cache_read    = 0
    cumulative_cost_usd      = 0.0

    for idx, entry in enumerate(selected, start=1):
        frame_id = entry["frame_id"]
        if frame_id in done_ids:
            LOGGER.info(
                "[%s] Frame %d/%d — %s skipped (already on disk)",
                student_id, idx, len(selected), frame_id,
            )
            continue

        # Prefer absolute file_path from manifest (supports redirected pilot frames)
        manifest_fp = entry.get("file_path")
        if manifest_fp:
            candidate = Path(manifest_fp)
            if not candidate.is_absolute():
                candidate = REPO_ROOT / candidate
            frame_path = candidate if candidate.is_file() else frames_dir / f"{frame_id}.jpg"
        else:
            frame_path = frames_dir / f"{frame_id}.jpg"
        if not frame_path.is_file():
            LOGGER.warning("[%s] Missing frame image: %s", student_id, frame_path)
            continue

        ts_s = float(entry["source_timestamp_seconds"])
        timestamp_ms = int(round(ts_s * 1000))
        pixel_change_pct: float | None = entry.get("metrics", {}).get("pixel_change_percentage")

        # aligned log window
        if log_df is not None and video_start_utc is not None:
            log_window = log_window_text_aligned(
                log_df,
                student_id,
                ts_s,
                video_start_utc,
                window_s=10.0,
                session_date=session_date,
            )
        elif log_df is not None:
            log_window = log_window_text(log_df, student_id, timestamp_ms)
        else:
            log_window = "(log CSV saglanmadi)"

        user_prompt = build_user_prompt(
            student_id=student_id,
            session_label=session_label,
            frame_id=frame_id,
            timestamp_ms=timestamp_ms,
            pixel_change_pct=pixel_change_pct,
            log_window=log_window,
            stats_text=stats_text,
        )

        LOGGER.info(
            "[%s] Frame %d/%d — %s @ %.1fs (pix_chg=%.1f%%)",
            student_id, idx, len(selected), frame_id, ts_s,
            pixel_change_pct if pixel_change_pct is not None else 0.0,
        )

        try:
            if dry_run:
                result = mock_analysis(student_id, session_date, entry)
                frame_usage: dict[str, int] = {}
            else:
                assert client is not None
                b64 = pil_to_base64_jpeg(frame_path)
                if provider == "openai":
                    result = call_openai(client, model, system_prompt, user_prompt, b64)
                    frame_usage = {}
                else:
                    result, frame_usage = call_anthropic(client, model, system_prompt, user_prompt, b64)
                    in_tok    = frame_usage.get("input_tokens", 0)
                    out_tok   = frame_usage.get("output_tokens", 0)
                    cache_read = frame_usage.get("cache_read_input_tokens", 0)
                    cache_write = frame_usage.get("cache_creation_input_tokens", 0)
                    frame_cost = (in_tok * _COST_INPUT_PER_TOKEN
                                  + out_tok * _COST_OUTPUT_PER_TOKEN
                                  + cache_read * _COST_CACHE_READ_PER_TOKEN
                                  + cache_write * _COST_CACHE_WRITE_PER_TOKEN)
                    cumulative_input_tokens  += in_tok
                    cumulative_output_tokens += out_tok
                    cumulative_cache_read    += cache_read
                    cumulative_cost_usd      += frame_cost
                    LOGGER.info(
                        "[COST] %d/%d  in=%d  out=%d  cache_read=%d  frame=$%.4f  total=$%.4f",
                        idx, len(selected), in_tok, out_tok, cache_read, frame_cost, cumulative_cost_usd,
                    )
        except Exception as _frame_exc:
            LOGGER.warning(
                "[%s] Frame %s failed (%s) — skipping and continuing",
                student_id, frame_id, _frame_exc,
            )
            if output_path is not None and not dry_run and analyses:
                write_analysis_checkpoint(output_path, _payload(in_progress=True))
            continue

        # inject pipeline metadata
        result.setdefault("student_id", student_id)
        result.setdefault("session_date", session_date)
        result.setdefault("frame_number", frame_number_from_id(frame_id))
        result.setdefault("timestamp_ms", timestamp_ms)
        result["frame_id"] = frame_id
        result["source_trigger"] = entry.get("extraction_trigger_reason")
        result["pixel_change_pct"] = pixel_change_pct

        # schema validation gate — log only, never persist errors in output
        errors = validate_frame_analysis(result, output_schema)
        if errors:
            validation_errors_total += 1
            LOGGER.warning(
                "[%s] Frame %s: %d schema error(s): %s",
                student_id, frame_id, len(errors), "; ".join(errors[:3]),
            )
        result.pop("_validation_errors", None)

        analyses.append(result)
        done_ids.add(frame_id)

        if output_path is not None and not dry_run:
            persist_frame_result(
                output_path,
                _payload(in_progress=True),
                result,
            )
            LOGGER.info(
                "[%s] Persisted %d/%d frame(s) -> %s",
                student_id,
                len(analyses),
                len(selected),
                output_path.name,
            )

    if cumulative_cost_usd > 0:
        LOGGER.info(
            "[COST SUMMARY] frames=%d  input_tokens=%d  output_tokens=%d  cache_read=%d  total=$%.4f USD",
            len(analyses), cumulative_input_tokens, cumulative_output_tokens, cumulative_cache_read, cumulative_cost_usd,
        )

    payload = _payload(in_progress=False)
    if output_path is not None and not dry_run:
        write_analysis_checkpoint(output_path, payload)
    return payload


def _empty_df() -> Any:
    import pandas as pd
    return pd.DataFrame(columns=["student_id", "timestamp_ms", "_canonical_id", "_params"])


# ─────────────────────────────────────────────────────────────
# discovery helpers
# ─────────────────────────────────────────────────────────────

def discover_students(audio_root: Path) -> list[str]:
    out: list[str] = []
    for child in sorted(audio_root.iterdir()):
        if child.is_dir() and (child / f"{child.name}_video_extraction_manifest.json").is_file():
            out.append(child.name)
    return out


def find_video_root(session_date: str) -> Path | None:
    date_to_root: dict[str, Path] = {
        "2026-04-28": DEFAULT_VIDEO_ROOT_28APR,
        "2026-04-21": DEFAULT_VIDEO_ROOT_21APR,
    }
    root = date_to_root.get(session_date)
    if root and root.is_dir():
        return root
    return None


def find_video_path(student_id: str, video_root: Path | None) -> Path | None:
    if video_root is None or not video_root.is_dir():
        return None
    for ext in (".webm", ".mp4", ".mkv", ".mov", ".m4v", ".avi", ".wmv", ".mpeg", ".mpg"):
        p = video_root / f"{student_id}{ext}"
        if p.is_file():
            return p
    return None


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CODAP Arbor per-frame vision analysis (LO3 rubric, aligned log windows)"
    )
    parser.add_argument("students", nargs="*", help="Student IDs (default: all with manifests)")
    parser.add_argument("--audio-root", type=Path, default=DEFAULT_AUDIO_ROOT)
    parser.add_argument("--video-root", type=Path, help="Directory with screen recording videos")
    parser.add_argument("--log-csv", type=Path, help="CODAP Arbor log CSV for aligned +-10s windows")
    parser.add_argument("--session-date", required=True, help="Session date YYYY-MM-DD")
    parser.add_argument("--session-label", help="Human session label (default: derived from date)")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--provider", choices=("anthropic", "openai"), default="anthropic")
    parser.add_argument("--model", help="Override default vision model")
    parser.add_argument(
        "--max-frames", type=int, default=0,
        help="Max frames per student (0 = all selected by the active selection mode)",
    )
    parser.add_argument(
        "--all-manifest-frames",
        action="store_true",
        help=(
            "Analyze every frame already present in the extraction manifest; "
            "skip the secondary log-anchored / uniform reselection"
        ),
    )
    parser.add_argument(
        "--resume",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Skip frame_ids already on disk and continue (default: true). "
            "Use --no-resume with --overwrite to start clean."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing JSON/JSONL for the student and start a fresh analysis",
    )
    parser.add_argument(
        "--reextract", action="store_true",
        help=(
            "For students with audio but no speech anchors: run diarization then "
            "re-extract frames in full_multimodal mode before analysis"
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-existing", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    system_prompt = load_system_prompt(args.prompt)
    output_schema = load_output_schema(args.schema)
    session_label = args.session_label or args.session_date.replace("-", "_") + "_CODAP"

    log_df = None
    if args.log_csv:
        log_path = args.log_csv.resolve()
        if not log_path.is_file():
            LOGGER.error("Log CSV not found: %s", log_path)
            return 1
        log_df = load_log_dataframe(log_path)
        LOGGER.info("Loaded log CSV: %s (%d rows)", log_path.name, len(log_df))
    else:
        LOGGER.warning(
            "No --log-csv provided. Log windows will be empty and frame selection "
            "will fall back to uniform spread."
        )

    audio_root = args.audio_root.resolve()
    video_root = args.video_root or find_video_root(args.session_date)

    targets = args.students or discover_students(audio_root)
    if not targets:
        LOGGER.error("No students with manifests under %s", audio_root)
        return 1

    exit_code = 0
    for student_id in targets:
        student_dir = audio_root / student_id

        # optional re-extraction
        if args.reextract and needs_reextraction(student_dir, student_id):
            LOGGER.info("[%s] Starting re-extraction (no speech anchors, audio present)", student_id)
            ok = run_diarization(student_id, audio_root, verbose=args.verbose)
            if ok:
                run_reextraction(student_id, audio_root, video_root, verbose=args.verbose)
            else:
                LOGGER.warning("[%s] Diarization failed — proceeding with existing manifest", student_id)

        out_path = student_dir / f"{student_id}_codap_frame_analyses.json"
        jsonl_path = jsonl_path_for(out_path)
        do_resume = bool(args.resume and not args.overwrite and not args.dry_run)

        if args.skip_existing and out_path.is_file() and not do_resume:
            LOGGER.info("Skipping %s — output exists", student_id)
            continue

        if args.overwrite and not args.dry_run:
            for p in (out_path, jsonl_path):
                if p.exists():
                    p.unlink()
                    LOGGER.info("[%s] Removed previous file: %s", student_id, p)

        video_path = find_video_path(student_id, video_root)
        if video_path:
            LOGGER.debug("[%s] video file: %s", student_id, video_path)
        else:
            LOGGER.debug("[%s] No video file found in %s", student_id, video_root)

        try:
            payload = analyze_student(
                student_dir,
                student_id,
                session_date=args.session_date,
                session_label=session_label,
                log_df=log_df,
                video_path=video_path,
                system_prompt=system_prompt,
                output_schema=output_schema,
                provider=args.provider,
                model_override=args.model,
                max_frames=args.max_frames,
                dry_run=args.dry_run,
                all_manifest_frames=args.all_manifest_frames,
                output_path=None if args.dry_run else out_path,
                resume=do_resume,
            )
        except Exception as exc:
            LOGGER.error("[%s] Analysis failed: %s", student_id, exc, exc_info=args.verbose)
            exit_code = 1
            continue

        if args.dry_run:
            LOGGER.info(
                "[%s] dry-run complete (%d mock frames); not writing %s",
                student_id,
                payload["frames_analyzed"],
                out_path,
            )
            continue

        # Final atomic rewrite (also done inside analyze_student; reaffirm complete=true).
        write_analysis_checkpoint(out_path, payload)
        val_warn = (
            f" ({payload['frames_with_validation_errors']} schema errors)"
            if payload["frames_with_validation_errors"]
            else ""
        )
        LOGGER.info(
            "Complete %s (%d/%d frames, selection=%s, align=%s%s) + %s",
            out_path,
            payload["frames_analyzed"],
            payload.get("frames_selected", payload["frames_analyzed"]),
            payload["frame_selection"],
            payload["alignment"]["method"],
            val_warn,
            jsonl_path.name,
        )

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
