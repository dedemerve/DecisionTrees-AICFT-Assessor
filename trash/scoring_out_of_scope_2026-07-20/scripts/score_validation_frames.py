#!/usr/bin/env python3
"""Run the CODAP Arbor scorer on the 2025 validation sample.

Loads calibration/validation_sample.json, sends each frame image to
Claude with the same system prompt used for 2026 scoring, and saves
Claude's raw B0-B17 scores alongside the gold labels.

Output:
    calibration/validation_raw_scores.json

Usage:
    python scripts/score_validation_frames.py
    python scripts/score_validation_frames.py --dry-run
    python scripts/score_validation_frames.py --limit 20
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import anthropic
from mmla_scorer import (
    _SYSTEM_CODAP,
    OUTPUT_SCHEMA_CODAP,
    DEFAULT_MODEL,
    encode_image,
    parse_json_response,
    _load_fewshot_block,
)

SAMPLE_FILE = REPO_ROOT / "calibration" / "validation_sample.json"
OUT_FILE = REPO_ROOT / "calibration" / "validation_raw_scores.json"

MAX_RETRIES = 3
RETRY_WAIT = 30

ALL_BEHAVIORS = [
    "B0","B1","B2","B3","B4","B5","B6","B7",
    "B8","B9","B10","B11","B12",
    "B15","B16","B17",
]


def build_prompt(frame: dict) -> list[dict]:
    fewshot = _load_fewshot_block("codap_arbor")
    text = (
        f"Frame ID: {frame['frame_id']}\n"
        f"Timestamp: {frame['timestamp_s']}s\n"
        f"Student: {frame['student_id']} (2025 calibration — Food Data / CODAP Arbor)\n\n"
        f"[TRANSCRIPT]\nnone — 2025 data has no audio\n\n"
        + fewshot
        + f"Apply the rubric to the screenshot and fill in this JSON schema:\n{OUTPUT_SCHEMA_CODAP}"
    )
    return [
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": encode_image(Path(frame["frame_image_path"])),
            },
        },
        {"type": "text", "text": text},
    ]


def score_frame(client: anthropic.Anthropic, frame: dict, model: str) -> dict | None:
    user_content = build_prompt(frame)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.messages.create(
                model=model,
                max_tokens=4096,
                system=_SYSTEM_CODAP,
                messages=[{"role": "user", "content": user_content}],
            )
            text_block = next((b for b in resp.content if b.type == "text"), None)
            if text_block:
                return parse_json_response(text_block.text)
        except anthropic.RateLimitError:
            if attempt < MAX_RETRIES:
                print(f"    Rate limit — waiting {RETRY_WAIT}s...")
                time.sleep(RETRY_WAIT)
        except Exception as exc:
            print(f"    API error (attempt {attempt}): {exc}")
            if attempt < MAX_RETRIES:
                time.sleep(5)
    return None


def dry_run_result(frame_id: str) -> dict:
    return {
        "frame_id": frame_id,
        "frame_description": "DRY RUN",
        "evidence_detection": {
            bid: {"score": 0, "evidence": "", "description": ""}
            for bid in ALL_BEHAVIORS
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Score 2025 validation frames")
    ap.add_argument("--dry-run", action="store_true", help="Skip API calls, use zero scores")
    ap.add_argument("--limit", type=int, help="Only score first N frames")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--resume", action="store_true", help="Skip already-scored frames")
    args = ap.parse_args()

    if not SAMPLE_FILE.is_file():
        print("ERROR: Run select_validation_frames.py first.")
        return 1

    sample = json.loads(SAMPLE_FILE.read_text(encoding="utf-8"))
    frames = sample["frames"]
    if args.limit:
        frames = frames[:args.limit]

    # Resume: load existing results
    existing: dict[str, dict] = {}
    if args.resume and OUT_FILE.is_file():
        prev = json.loads(OUT_FILE.read_text(encoding="utf-8"))
        existing = {r["frame_id"]: r for r in prev.get("results", [])}
        print(f"Resuming — {len(existing)} frames already scored.")

    client = None if args.dry_run else anthropic.Anthropic()
    results: list[dict] = list(existing.values())
    scored_ids = set(existing.keys())

    to_score = [f for f in frames if f["frame_id"] not in scored_ids]
    total = len(to_score)
    print(f"\nScoring {total} frames ({'DRY RUN' if args.dry_run else args.model})...\n")

    for i, frame in enumerate(to_score, 1):
        fid = frame["frame_id"]
        print(f"  [{i:3d}/{total}] {fid}", end="", flush=True)

        if args.dry_run:
            api_out = dry_run_result(fid)
        else:
            api_out = score_frame(client, frame, args.model)

        if api_out is None:
            print(" ✗ failed")
            continue

        # Extract claude scores per behavior
        claude_scores: dict[str, int] = {}
        for bid in ALL_BEHAVIORS:
            det = api_out.get("evidence_detection", {}).get(bid, {})
            s = int(det.get("score", 0))
            claude_scores[bid] = 1 if s == 2 else 0  # convert 0/2 → 0/1 for metrics

        result = {
            "frame_id": fid,
            "student_id": frame["student_id"],
            "timestamp_s": frame["timestamp_s"],
            "silver_confidence": frame.get("silver_confidence", "none"),
            "label_source": frame.get("label_source", ""),
            "gold_labels": frame["gold_labels"],        # expert: 0/1 per behavior
            "claude_scores": claude_scores,             # claude: 0/1 per behavior
            "frame_description": api_out.get("frame_description", ""),
            "claude_raw": api_out.get("evidence_detection", {}),
        }
        results.append(result)
        scored_ids.add(fid)

        n_positive = sum(frame["gold_labels"].get(b, 0) for b in ALL_BEHAVIORS)
        n_claude_pos = sum(claude_scores.values())
        print(f" gold={n_positive} claude={n_claude_pos} ✓")

        # Save after every 10 frames in case of interruption
        if i % 10 == 0:
            _save(results, sample, args.model, args.dry_run)

    _save(results, sample, args.model, args.dry_run)
    print(f"\nDone. {len(results)} frames scored → {OUT_FILE.relative_to(REPO_ROOT)}")
    return 0


def _save(results: list[dict], sample: dict, model: str, dry_run: bool) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": model,
        "dry_run": dry_run,
        "sample_source": "calibration/validation_sample.json",
        "total_frames": len(results),
        "target_behaviors": ALL_BEHAVIORS,
        "results": results,
    }
    OUT_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
