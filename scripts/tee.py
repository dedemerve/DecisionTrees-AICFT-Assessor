#!/usr/bin/env python3
"""TEE — Transcript Evidence Extractor.

Extracts structured verbal evidence from a student transcript.
Handles all speech_status cases gracefully — never crashes on missing data.

Output: {student}_transcript_evidence.json

Usage:
    python scripts/tee.py Marco --session-date 2026-04-21
    python scripts/tee.py Marco --session-date 2026-04-21 --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import anthropic

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGGER = logging.getLogger("tee")

DEFAULT_PROMPT = REPO_ROOT / "prompts" / "TEE_system_prompt.md"
DEFAULT_MODEL  = "claude-sonnet-5"

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
    "2026-05-05": "colab_python_audio",
}

# Statuses that mean no speech is available
SILENT_STATUSES = {"silent_recording", "truncated_audio_track", "extraction_failed"}


# ─────────────────────────────────────────────────────────────
# Standard Evidence Layer envelope
# ─────────────────────────────────────────────────────────────

def unavailable_envelope(reason: str) -> dict[str, Any]:
    return {
        "layer": "VERBAL_EVIDENCE",
        "status": "UNAVAILABLE",
        "reason": reason,
        "utterance_count": 0,
        "evidence_count": 0,
        "utterances": [],
    }


def available_envelope(utterances: list[dict[str, Any]]) -> dict[str, Any]:
    evidence_count = sum(len(u.get("categories", [])) for u in utterances)
    return {
        "layer": "VERBAL_EVIDENCE",
        "status": "AVAILABLE",
        "reason": None,
        "utterance_count": len(utterances),
        "evidence_count": evidence_count,
        "utterances": utterances,
    }


# ─────────────────────────────────────────────────────────────
# Transcript loading
# ─────────────────────────────────────────────────────────────

def load_transcript(student_id: str, session_date: str) -> dict[str, Any] | None:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_transcript.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


# ─────────────────────────────────────────────────────────────
# API call
# ─────────────────────────────────────────────────────────────

def call_tee(system_prompt: str, transcript: dict[str, Any], model: str) -> list[dict[str, Any]]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    user_prompt = (
        "Extract verbal evidence from the following transcript.\n\n"
        + json.dumps({"segments": transcript.get("segments", [])}, ensure_ascii=False, indent=2)
        + "\n\nReturn JSON only."
    )

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        thinking={"type": "adaptive"},
        output_config={"effort": "low"},
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}],
    )
    text_block = next((b for b in response.content if hasattr(b, "text")), None)
    if text_block is None:
        raise ValueError("No text block in TEE response")

    raw = text_block.text.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]

    result = json.loads(raw)
    return result.get("utterances", [])


# ─────────────────────────────────────────────────────────────
# Main logic
# ─────────────────────────────────────────────────────────────

def run_tee(
    student_id: str,
    session_date: str,
    system_prompt: str,
    model: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    transcript = load_transcript(student_id, session_date)

    # Case 1: transcript file missing
    if transcript is None:
        LOGGER.warning("[%s] Transcript file not found", student_id)
        return unavailable_envelope("transcript_missing")

    speech_status = transcript.get("speech_status", "unknown")

    # Case 2: silent or failed recording
    if speech_status in SILENT_STATUSES or speech_status == "unknown":
        LOGGER.info("[%s] speech_status=%s — skipping API call", student_id, speech_status)
        return unavailable_envelope(speech_status)

    segments = transcript.get("segments", [])
    if not segments:
        LOGGER.info("[%s] No segments in transcript", student_id)
        return unavailable_envelope("no_segments")

    # Case 3: transcript available
    if dry_run:
        LOGGER.info("[%s] DRY-RUN: would extract evidence from %d segments", student_id, len(segments))
        return available_envelope([])

    LOGGER.info("[%s] Extracting verbal evidence from %d segments...", student_id, len(segments))
    utterances = call_tee(system_prompt, transcript, model)
    return available_envelope(utterances)


# ─────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────

def write_output(
    envelope: dict[str, Any],
    student_id: str,
    session_date: str,
    model: str,
    prompt_file: Path,
) -> Path:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    out_dir = REPO_ROOT / "data_sources_2026" / subdir / student_id
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{student_id}_transcript_evidence.json"

    payload = {
        "tee_version": "1.0",
        "student_id": student_id,
        "session_date": session_date,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "prompt_file": str(prompt_file.relative_to(REPO_ROOT)),
        **envelope,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="TEE — Transcript Evidence Extractor")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    system_prompt = args.prompt.read_text(encoding="utf-8")

    envelope = run_tee(
        args.student, args.session_date,
        system_prompt, args.model, dry_run=args.dry_run,
    )

    out_path = write_output(envelope, args.student, args.session_date, args.model, args.prompt)
    LOGGER.info("Written: %s", out_path)
    print(f"status={envelope['status']}  reason={envelope.get('reason')}  "
          f"utterances={envelope['utterance_count']}  evidence={envelope['evidence_count']}")


if __name__ == "__main__":
    main()
