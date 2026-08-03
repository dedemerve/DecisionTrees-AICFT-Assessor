#!/usr/bin/env python3
"""LPRA — Learning Process Reconstruction Agent.

Reads the synchronized episode file (from log_synchronizer.py) and calls
the Claude API to reconstruct the student's complete learning process.

Usage:
    python scripts/lpra.py Marco --session-date 2026-04-21
    python scripts/lpra.py Marco --session-date 2026-04-21 --dry-run
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
LOGGER = logging.getLogger("lpra")

DEFAULT_PROMPT = REPO_ROOT / "prompts" / "LPRA_system_prompt.md"
DEFAULT_MODEL  = "claude-sonnet-5"

SESSION_AUDIO_ROOTS: dict[str, str] = {
    "2026-04-21": "codap_arbor_21april_audio",
    "2026-04-28": "codap_arbor_28april_audio",
}


# ─────────────────────────────────────────────────────────────
# I/O
# ─────────────────────────────────────────────────────────────

def load_episodes(student_id: str, session_date: str) -> tuple[dict[str, Any], Path]:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_learning_episodes.json"
    if not path.is_file():
        raise FileNotFoundError(f"Episode file not found: {path}. Run lesa.py and log_synchronizer.py first.")
    return json.loads(path.read_text(encoding="utf-8")), path


def load_efa_output(student_id: str, session_date: str) -> dict[str, Any] | None:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_evidence_packages.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_tee_output(student_id: str, session_date: str) -> dict[str, Any] | None:
    subdir = SESSION_AUDIO_ROOTS.get(session_date, "")
    path = REPO_ROOT / "data_sources_2026" / subdir / student_id / f"{student_id}_transcript_evidence.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def build_evidence_inventory(
    episodes: list[dict[str, Any]],
    tee: dict[str, Any] | None,
) -> dict[str, str]:
    has_logs = any(ep.get("log_events") for ep in episodes)
    verbal_status = "UNAVAILABLE"
    if tee is not None:
        verbal_status = "AVAILABLE" if tee.get("status") == "AVAILABLE" else "UNAVAILABLE"
    return {
        "frame_annotations": "AVAILABLE" if episodes else "UNAVAILABLE",
        "learning_episodes": "AVAILABLE" if episodes else "UNAVAILABLE",
        "interaction_logs": "AVAILABLE" if has_logs else "UNAVAILABLE",
        "transcript": verbal_status,
        "diarization": "UNAVAILABLE",
    }


def build_user_prompt(
    payload: dict[str, Any],
    tee: dict[str, Any] | None,
    efa: dict[str, Any] | None,
) -> str:
    episodes = payload.get("episodes", [])
    duration_s = 0
    if episodes:
        last = episodes[-1]
        duration_s = round((last["end_ms"]) / 1000, 1)

    inventory = build_evidence_inventory(episodes, tee)

    session_meta = {
        "student": payload.get("student_id"),
        "session_date": payload.get("session_date"),
        "total_duration_s": duration_s,
        "episode_count": len(episodes),
    }

    lines = [
        "## Evidence Inventory",
        json.dumps(inventory, indent=2),
        "",
        "## Session Metadata",
        json.dumps(session_meta, indent=2),
        "",
    ]

    if efa is not None:
        lines += [
            "## Evidence Packages (EFA output — use these for inference_chain)",
            json.dumps(efa.get("evidence_packages", []), indent=2, ensure_ascii=False),
        ]
    else:
        lines += [
            "## Learning Episodes",
            json.dumps(episodes, indent=2, ensure_ascii=False),
        ]

    lines += ["", "Reconstruct the complete learning process. Return JSON only."]
    return "\n".join(lines)


# ─────────────────────────────────────────────────────────────
# API call
# ─────────────────────────────────────────────────────────────

def call_lpra(system_prompt: str, user_prompt: str, model: str) -> dict[str, Any]:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
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
        raise ValueError("No text block in LPRA response")

    raw = text_block.text.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0]
    return json.loads(raw)


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="LPRA — Learning Process Reconstruction Agent")
    parser.add_argument("student", help="Student ID (e.g. Marco)")
    parser.add_argument("--session-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true", help="Print user prompt without calling API")
    args = parser.parse_args()

    payload, ep_path = load_episodes(args.student, args.session_date)
    LOGGER.info("Loaded %d episodes from %s", len(payload.get("episodes", [])), ep_path)

    tee = load_tee_output(args.student, args.session_date)
    if tee:
        LOGGER.info("TEE: status=%s  utterances=%d", tee.get("status"), tee.get("utterance_count", 0))
    else:
        LOGGER.info("TEE: no transcript_evidence.json found — transcript layer UNAVAILABLE")

    efa = load_efa_output(args.student, args.session_date)
    if efa:
        LOGGER.info("EFA: %d evidence packages loaded", efa.get("episode_count", 0))
    else:
        LOGGER.info("EFA: no evidence_packages.json found — falling back to raw episodes")

    system_prompt = args.prompt.read_text(encoding="utf-8")
    user_prompt = build_user_prompt(payload, tee, efa)

    if args.dry_run:
        print("=== USER PROMPT ===")
        print(user_prompt)
        return

    LOGGER.info("Calling LPRA (%s)...", args.model)
    result = call_lpra(system_prompt, user_prompt, args.model)

    # Inject episodes from payload so output is self-contained
    if "episodes" in result and not result["episodes"]:
        result["episodes"] = payload.get("episodes", [])

    inputs = ["frame_annotations", "learning_episodes", "codap_logs"]
    if efa:
        inputs.append("evidence_packages")
    if tee and tee.get("status") == "AVAILABLE":
        inputs.append("transcript")

    result["_lpra_meta"] = {
        "lpra_version": "v2.0",
        "model": args.model,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "prompt_file": str(args.prompt.relative_to(REPO_ROOT)),
        "efa_used": efa is not None,
        "inputs": inputs,
        "excluded_inputs": [x for x in ["transcript", "diarization"] if x not in inputs],
    }

    subdir = SESSION_AUDIO_ROOTS.get(args.session_date, "")
    out_dir = REPO_ROOT / "data_sources_2026" / subdir / args.student
    out_path = out_dir / f"{args.student}_learning_process_model.json"
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info("Written: %s", out_path)

    summary = result.get("session_summary", {})
    strategy = result.get("overall_strategy", {})
    ls = result.get("learning_summary", {})
    print(f"\nStudent:    {summary.get('student')}")
    print(f"Strategy:   {strategy.get('category')} ({strategy.get('confidence')})")
    print(f"Pattern:    {result.get('workflow_pattern', {}).get('pattern')}")
    print(f"Revisions:  {ls.get('revision_cycles')}  |  Evaluations: {ls.get('evaluation_cycles')}")
    print(f"Output:     {out_path}")


if __name__ == "__main__":
    main()
