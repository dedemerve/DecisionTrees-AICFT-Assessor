#!/usr/bin/env python3
"""Finalize 2025 gold alignment: Word screenshot ↔ behavior = 100% GT.

Tier model (research-grade):
  GOLD  — expert Analysis.docx screenshot + coded behaviors from the same
          observation paragraph. Linked by document order (always exact).
  SILVER — video motion keyframe paired to that gold step, refined by:
            1) aspect-band dHash shortlist (top-K under monotonic prior)
            2) optional Anthropic Vision verification (when ANTHROPIC_API_KEY set)

Also emits per-frame silver labels: every extracted video frame inherits the
nearest gold step's behavior codes (100% frame coverage for sequence learning).

Usage:
  export ANTHROPIC_API_KEY=...
  python scripts/finalize_2025_gold_alignment.py Ally Barbara
  python scripts/finalize_2025_gold_alignment.py --all
"""

from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path(__file__).resolve().parent
OUT_ROOT = REPO_ROOT / "training_datasets" / "2025"
sys.path.insert(0, str(SCRIPTS))

from align_2025_frames_to_analysis import (  # noqa: E402
    BEHAVIOR_RULES,
    build_frame_index,
    code_behaviors,
    cognitive_from_codes,
    cost_matrix,
    detect_frozen_frame_index,
    lo_from_text,
    regularize_costs_temporal,
    seed_lock_assign,
    strategy_from_text,
    timestamp_for_frame,
)

LOGGER = logging.getLogger("finalize_2025_gold")
DEFAULT_VISION_MODEL = "claude-haiku-4-5-20251001"
TOP_K = 5


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def pil_b64_jpeg(path: Path, max_w: int = 1280) -> str:
    from PIL import Image

    im = Image.open(path).convert("RGB")
    if im.width > max_w:
        h = int(im.height * max_w / im.width)
        im = im.resize((max_w, h), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=85)
    return base64.standard_b64encode(buf.getvalue()).decode("ascii")


def vision_pick_frame(
    client: Any,
    model: str,
    *,
    observation: str,
    behaviors: list[str],
    shot_path: Path,
    candidate_paths: list[Path],
) -> dict[str, Any]:
    """Ask Vision which candidate video frame best matches the expert screenshot."""
    if not candidate_paths:
        return {"chosen_index": None, "confidence": "none", "reason": "no_candidates"}

    content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                "You are aligning an expert CODAP/Arbor observation screenshot to video keyframes.\n"
                "Image 1 = GOLD expert screenshot from the Word analysis document.\n"
                f"Observation text: {observation}\n"
                f"Coded behaviors: {behaviors}\n"
                f"Images 2..{len(candidate_paths)+1} = candidate video keyframes (same order).\n"
                "Pick the SINGLE best-matching video keyframe index (0-based among candidates).\n"
                "Match UI state (tree depth, graph axes, movable line, CTR), not wallpaper.\n"
                'Return ONLY JSON: {"chosen_index": int, "confidence": "high"|"medium"|"low", '
                '"reason": "short"}'
            ),
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": pil_b64_jpeg(shot_path),
            },
        },
    ]
    for p in candidate_paths:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": pil_b64_jpeg(p),
            },
        })

    resp = client.messages.create(
        model=model,
        max_tokens=300,
        messages=[{"role": "user", "content": content}],
    )
    text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    if not m:
        return {"chosen_index": 0, "confidence": "low", "reason": f"parse_fail:{text[:120]}"}
    try:
        data = json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"chosen_index": 0, "confidence": "low", "reason": f"json_fail:{text[:120]}"}
    idx = data.get("chosen_index")
    if not isinstance(idx, int) or idx < 0 or idx >= len(candidate_paths):
        idx = 0
        data["confidence"] = "low"
        data["reason"] = (data.get("reason") or "") + "|index_clamped"
    data["chosen_index"] = idx
    return data


def top_k_candidates(
    cost_row: list[int],
    assign_j: int | None,
    k: int = TOP_K,
    window: int = 12,
) -> list[int]:
    """Near the monotonic DP pick, take K lowest-cost frame indices."""
    m = len(cost_row)
    if m == 0:
        return []
    if assign_j is None:
        order = sorted(range(m), key=lambda j: cost_row[j])
        return order[:k]
    lo = max(0, assign_j - window)
    hi = min(m, assign_j + window + 1)
    local = list(range(lo, hi))
    local.sort(key=lambda j: cost_row[j])
    return local[:k]


def process_student(
    student_id: str,
    *,
    use_vision: bool,
    vision_model: str,
    client: Any | None,
) -> dict[str, Any]:
    out_dir = OUT_ROOT / student_id
    steps_path = out_dir / f"{student_id}_observation_steps.json"
    if not steps_path.is_file():
        from build_2025_mmla_training_dataset import process_student as rebuild
        rebuild(student_id)
    steps_doc = load_json(steps_path)
    steps = steps_doc.get("observation_steps") or []
    shots = {int(s["shot_index"]): s for s in (steps_doc.get("docx_screenshots") or []) if "shot_index" in s}
    manifest_path = out_dir / f"{student_id}_video_extraction_manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else None
    frame_index = build_frame_index(out_dir / f"{student_id}_frames")

    shot_paths: list[Path | None] = []
    for step in steps:
        si = step.get("docx_shot_index")
        meta = shots.get(si) if isinstance(si, int) else None
        shot_paths.append(out_dir / meta["path"] if meta else None)

    LOGGER.info("[%s] GOLD steps=%d shots; silver frames=%d", student_id, len(steps), len(frame_index))
    frozen = detect_frozen_frame_index(frame_index) if frame_index else False
    if frozen:
        LOGGER.warning("[%s] Frozen/still video detected — silver marked unavailable (GOLD unchanged)", student_id)

    # Cost matrix only for steps that have a gold screenshot (cached for reruns)
    shot_paths_for_cost: list[Path | None] = list(shot_paths)
    cost_cache = out_dir / f"{student_id}_silver_cost_matrix.json"
    raw_costs: list[list[int]]
    if frame_index and not frozen and cost_cache.is_file():
        try:
            cached = load_json(cost_cache)
            if (
                cached.get("n_steps") == len(steps)
                and cached.get("n_frames") == len(frame_index)
                and cached.get("frame_ids") == [fr["frame_id"] for fr in frame_index]
            ):
                raw_costs = cached["costs"]
                LOGGER.info("[%s] reused cached cost matrix %s", student_id, cost_cache.name)
            else:
                raise ValueError("cache shape mismatch")
        except Exception:
            raw_costs = cost_matrix(shot_paths_for_cost, frame_index)
            cost_cache.write_text(
                json.dumps({
                    "n_steps": len(steps),
                    "n_frames": len(frame_index),
                    "frame_ids": [fr["frame_id"] for fr in frame_index],
                    "costs": raw_costs,
                }),
                encoding="utf-8",
            )
    elif frame_index and not frozen:
        raw_costs = cost_matrix(shot_paths_for_cost, frame_index)
        cost_cache.write_text(
            json.dumps({
                "n_steps": len(steps),
                "n_frames": len(frame_index),
                "frame_ids": [fr["frame_id"] for fr in frame_index],
                "costs": raw_costs,
            }),
            encoding="utf-8",
        )
    else:
        raw_costs = [[] for _ in steps]
    has_cost_rows = bool(raw_costs) and any(bool(r) for r in raw_costs)
    reg_costs = (
        regularize_costs_temporal(raw_costs, temporal_weight=8.0)
        if has_cost_rows
        else raw_costs
    )
    # Seed-lock high/medium visual matches, then soft-unique temporal fill
    assign = (
        seed_lock_assign(raw_costs, reg_costs, lock_hamming=12, reuse_penalty=6.0)
        if frame_index and not frozen and has_cost_rows
        else [None] * len(steps)
    )

    gold_rows: list[dict[str, Any]] = []
    silver_conf: Counter[str] = Counter()
    behavior_hist: Counter[str] = Counter()

    for i, step in enumerate(steps):
        text = step["uzman_nitel_gözlemi"]
        behaviors = code_behaviors(text)
        codes = [b["code"] for b in behaviors]
        for c in codes:
            behavior_hist[c] += 1

        si = step.get("docx_shot_index")
        meta = shots.get(si) if isinstance(si, int) else None
        shot_rel = meta["path"] if meta else None
        shot_path = out_dir / shot_rel if shot_rel else None

        # --- GOLD (always 100% when shot exists) ---
        gold = {
            "tier": "GOLD",
            "certainty": "exact" if shot_rel else "text_only",
            "expert_screenshot": shot_rel,
            "uzman_nitel_gözlemi": text,
            "behavior_codes": behaviors,
            "behavior_code_list": codes,
            "bilişsel_davranış_kategorisi": cognitive_from_codes(
                codes, step.get("labels", {}).get("bilişsel_davranış_kategorisi", "EXPLORE")
            ),
            "pedagojik_strateji": strategy_from_text(text, codes),
            "unesco_ai_cft_level": lo_from_text(text, codes),
            "screen_change_learning": {
                "expected_visual_effects": [b["screen_change"] for b in behaviors if b.get("screen_change")],
                "primary_behavior": codes[0] if codes else None,
            },
        }

        # --- SILVER video ---
        silver: dict[str, Any] = {
            "tier": "SILVER",
            "matched_frame_id": None,
            "matched_frame_image": None,
            "timestamp_ms": None,
            "hamming": None,
            "confidence": "none",
            "method": None,
            "vision": None,
        }
        fj = assign[i] if i < len(assign) else None
        if frozen:
            silver = {
                "tier": "SILVER",
                "matched_frame_id": frame_index[0]["frame_id"] if frame_index else None,
                "matched_frame_image": (
                    f"{student_id}_frames/{frame_index[0]['path']}" if frame_index else None
                ),
                "timestamp_ms": 0 if frame_index else None,
                "hamming": None,
                "confidence": "unavailable",
                "method": "frozen_video_detected",
                "candidate_frame_ids": [],
                "vision": None,
                "note": "Source recording is a static still; do not use silver for training. GOLD screenshot is authoritative.",
            }
        elif frame_index and raw_costs and raw_costs[i] and shot_path and shot_path.is_file():
            cands = top_k_candidates([int(x) if x < 10**5 else 10**5 for x in raw_costs[i]], fj)
            chosen_j = cands[0] if cands else fj
            # Prefer regularized unique assign pick when available
            if fj is not None:
                chosen_j = fj
            method = "aspect_band_dhash+seed_lock_temporal"
            vision_meta = None
            if use_vision and client is not None and cands:
                cand_paths = [frame_index[j]["abs_path"] for j in cands]
                try:
                    vision_meta = vision_pick_frame(
                        client,
                        vision_model,
                        observation=text,
                        behaviors=codes,
                        shot_path=shot_path,
                        candidate_paths=cand_paths,
                    )
                    vi = vision_meta.get("chosen_index")
                    if isinstance(vi, int) and 0 <= vi < len(cands):
                        chosen_j = cands[vi]
                        method = "vision_verified_topk_band_dhash"
                except Exception as exc:
                    vision_meta = {"error": str(exc)}
                    LOGGER.warning("[%s] vision failed step %d: %s", student_id, step["step_index"], exc)

            fr = frame_index[chosen_j] if chosen_j is not None else None
            ham = int(raw_costs[i][chosen_j]) if chosen_j is not None else None
            conf = (
                (vision_meta or {}).get("confidence")
                if method.startswith("vision") and vision_meta and "confidence" in vision_meta
                else (
                    "high" if ham is not None and ham <= 8 else
                    "medium" if ham is not None and ham <= 12 else
                    "low" if ham is not None and ham <= 18 else
                    "weak"
                )
            )
            ts = timestamp_for_frame(manifest, fr["frame_id"]) if fr else None
            silver = {
                "tier": "SILVER",
                "matched_frame_id": fr["frame_id"] if fr else None,
                "matched_frame_image": f"{student_id}_frames/{fr['path']}" if fr else None,
                "timestamp_ms": int(round(ts * 1000)) if ts is not None else None,
                "hamming": ham,
                "confidence": conf,
                "method": method,
                "candidate_frame_ids": [frame_index[j]["frame_id"] for j in cands],
                "vision": vision_meta,
            }
        silver_conf[silver["confidence"]] += 1

        gold_rows.append({
            "training_sample_id": f"2025_{student_id}_gold_{step['step_index']:04d}",
            "metadata": {
                "cohort_year": 2025,
                "student_id": student_id,
                "observation_step_index": step["step_index"],
            },
            "gold": gold,
            "silver_video": silver,
            "ai_cft_evidence_justification": (
                f"GOLD exact: Word shot {shot_rel} ↔ behaviors {codes}. "
                f"SILVER video: {silver.get('matched_frame_id')} "
                f"({silver.get('method')}, conf={silver.get('confidence')}, d={silver.get('hamming')})."
            ),
        })

    # 100% frame coverage: every motion frame inherits nearest gold step by silver timestamp order.
    # Fallback: if silver anchors span < 30% of video duration (poor Vision coverage),
    # assign synthetic timestamps by distributing steps uniformly across the video.
    gold_by_ts: list[tuple[float, dict[str, Any]]] = []
    for row in gold_rows:
        ts = row["silver_video"].get("timestamp_ms")
        if ts is not None:
            gold_by_ts.append((ts / 1000.0, row))
    gold_by_ts.sort(key=lambda x: x[0])

    if manifest and gold_rows:
        all_frame_ts = [
            timestamp_for_frame(manifest, f["frame_id"])
            for f in frame_index
        ]
        video_end_s = max((t for t in all_frame_ts if t is not None), default=0.0)
        silver_span_s = (gold_by_ts[-1][0] - gold_by_ts[0][0]) if len(gold_by_ts) > 1 else 0.0
        low_coverage = video_end_s > 300 and (silver_span_s / video_end_s) < 0.30

        if low_coverage:
            n = len(gold_rows)
            LOGGER.warning(
                "[%s] Silver anchors span only %.0f%% of video (%.0fs/%.0fs); "
                "falling back to uniform step distribution for FBC.",
                student_id,
                100.0 * silver_span_s / video_end_s if video_end_s else 0,
                silver_span_s,
                video_end_s,
            )
            gold_by_ts = [
                (video_end_s * i / max(n - 1, 1), row)
                for i, row in enumerate(gold_rows)
            ]

    frame_labels: list[dict[str, Any]] = []
    for fr in frame_index:
        fid = fr["frame_id"]
        t = timestamp_for_frame(manifest, fid) or 0.0
        nearest = None
        if gold_by_ts:
            nearest = min(gold_by_ts, key=lambda gt: abs(gt[0] - t))[1]
        frame_labels.append({
            "frame_id": fid,
            "frame_image": f"{student_id}_frames/{fr['path']}",
            "timestamp_ms": int(round(t * 1000)),
            "inherited_from_step": (
                nearest["metadata"]["observation_step_index"] if nearest else None
            ),
            "behavior_code_list": (
                nearest["gold"]["behavior_code_list"] if nearest else []
            ),
            "expert_screenshot": (
                nearest["gold"]["expert_screenshot"] if nearest else None
            ),
            "label_source": "nearest_gold_silver_anchor" if nearest else "unlabeled",
        })

    payload = {
        "student_id": student_id,
        "cohort_year": 2025,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "standard": {
            "gold": "Word screenshot bound to nearest preceding observation paragraph (document-order exact)",
            "silver": "Video keyframe: seed-lock high/medium band-dHash, then soft-unique temporal fill (± optional Vision)",
            "frame_coverage": "Every motion frame inherits nearest gold behaviors",
            "frozen_video": "Silver marked unavailable; GOLD remains authoritative",
            "note": "Pixel-identical Word-crop ↔ full-HD frame is not assumed; GOLD is the authoritative visual GT.",
            "revision": "v2c_adjacency_gold+seed_lock_silver",
        },
        "vision_enabled": bool(use_vision and client is not None),
        "vision_model": vision_model if use_vision else None,
        "codebook": [c for c, _, _ in BEHAVIOR_RULES],
        "step_count": len(gold_rows),
        "gold_with_screenshot": sum(1 for r in gold_rows if r["gold"]["expert_screenshot"]),
        "silver_confidence_histogram": dict(silver_conf),
        "behavior_histogram": dict(behavior_hist),
        "alignments": gold_rows,
        "frame_behavior_coverage": frame_labels,
    }
    write_json(out_dir / f"{student_id}_gold_behavior_alignment.json", payload)
    write_jsonl(out_dir / f"{student_id}_gold_behavior_alignment.jsonl", gold_rows)
    write_jsonl(out_dir / f"{student_id}_frame_behavior_coverage.jsonl", frame_labels)

    summary = {
        "student_id": student_id,
        "status": "ok",
        "gold_steps": len(gold_rows),
        "gold_with_screenshot": payload["gold_with_screenshot"],
        "gold_screenshot_coverage_pct": round(
            100.0 * payload["gold_with_screenshot"] / max(len(gold_rows), 1), 1
        ),
        "frames_labeled": len(frame_labels),
        "silver_confidence_histogram": dict(silver_conf),
        "vision_enabled": payload["vision_enabled"],
    }
    LOGGER.info(
        "[%s] GOLD %d/%d screenshots exact; frames labeled %d; silver %s",
        student_id,
        summary["gold_with_screenshot"],
        summary["gold_steps"],
        summary["frames_labeled"],
        dict(silver_conf),
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("students", nargs="*")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--vision", action=argparse.BooleanOptionalAction, default=True)
    ap.add_argument("--model", default=DEFAULT_VISION_MODEL)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.all or not args.students:
        targets = [
            p.name for p in sorted(OUT_ROOT.iterdir())
            if p.is_dir() and (p / f"{p.name}_observation_steps.json").exists()
        ]
        if args.students:
            targets = args.students
    else:
        targets = args.students

    client = None
    use_vision = bool(args.vision)
    if use_vision:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            LOGGER.warning("ANTHROPIC_API_KEY missing — GOLD exact only; silver stays band-dHash")
            use_vision = False
        else:
            import anthropic
            client = anthropic.Anthropic(api_key=key)

    results = []
    for sid in targets:
        try:
            results.append(process_student(sid, use_vision=use_vision, vision_model=args.model, client=client))
        except Exception as exc:
            LOGGER.exception("[%s] failed", sid)
            results.append({"student_id": sid, "status": "error", "error": str(exc)})

    write_json(OUT_ROOT / "cohort_gold_behavior_alignment_summary.json", {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "students": results,
    })
    ok = sum(1 for r in results if r.get("status") == "ok")
    LOGGER.info("Done %d/%d", ok, len(results))

    # Process-only video analysis bundles (scoring out of scope)
    try:
        from build_video_analysis_bundle import process_student as build_video_bundle

        gaps_path = REPO_ROOT / "data_sources_2025" / "rubric_gaps_2025.json"
        gaps_doc = json.loads(gaps_path.read_text(encoding="utf-8")) if gaps_path.is_file() else {"gaps": []}
        bundled = 0
        for r in results:
            if r.get("status") != "ok":
                continue
            try:
                build_video_bundle(r["student_id"], gaps_doc)
                bundled += 1
            except Exception as exc:
                LOGGER.warning("[%s] video analysis bundle failed: %s", r["student_id"], exc)
        LOGGER.info("Video analysis bundles: %d/%d", bundled, ok)
    except Exception as exc:
        LOGGER.warning("Video analysis bundle step skipped: %s", exc)

    return 0 if ok == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
