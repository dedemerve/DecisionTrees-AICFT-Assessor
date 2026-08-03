"""
portfolio_builder.py — Merge worksheet, video, and colab LO evidence into one portfolio.

Inputs per student:
  outputs/ws_lo/<student_id>_ws_lo.json          (Task A output)
  logs/pipeline_runs/<student_id>_*_final_scored.json   (MMLA video sessions)
  logs/pipeline_runs/<student_id>_colab_scored.json     (Colab, if present)

Output:
  outputs/portfolios/<student_id>_portfolio.json

No numeric calculations are delegated to an LLM.
All score aggregation uses Python only.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

log = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).parent.parent.parent
WS_LO_DIR = REPO_ROOT / "outputs" / "ws_lo"
MMLA_DIR = REPO_ROOT / "logs" / "pipeline_runs"
PORTFOLIO_DIR = REPO_ROOT / "outputs" / "portfolios"

TOP_LEVEL_LOS = ("LO3.1", "LO3.2", "LO3.3")

EvidenceStrength = Literal["strong", "weak", "absent"]

_STRENGTH_ORDER: dict[str, int] = {"strong": 2, "weak": 1, "absent": 0}

# Confidence string thresholds for MMLA behaviors.
_CONFIDENCE_MAP: dict[str | None, float] = {
    "High": 0.90,
    "Medium": 0.60,
    "Low": 0.30,
    None: 0.0,
}
CONFIDENCE_THRESHOLD = 0.70

# Minimum observed frame count for a behavior to contribute to LO3.3 (Create).
# LO3.1 and LO3.2 have no minimum — even 1 frame counts.
LO3_CREATE_MIN_FRAMES = 3


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _merge_strength(a: EvidenceStrength, b: EvidenceStrength) -> EvidenceStrength:
    """Return the stronger of two evidence_strength values."""
    return a if _STRENGTH_ORDER.get(a, 0) >= _STRENGTH_ORDER.get(b, 0) else b


def _strongest(values: list[EvidenceStrength]) -> EvidenceStrength:
    result: EvidenceStrength = "absent"
    for v in values:
        result = _merge_strength(result, v)
    return result


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Source normalisers
# ---------------------------------------------------------------------------

_NormalisedSource = dict[str, Any]
# {
#   "source": "worksheet"|"video"|"colab",
#   "LO3.1": {"score": int, "max_score": int, "evidence_strength": str},
#   ...
# }


def normalise_ws_source(ws_lo: dict[str, Any]) -> _NormalisedSource:
    """Convert ws_lo JSON to the common normalised schema."""
    out: _NormalisedSource = {"source": "worksheet"}
    for lo in TOP_LEVEL_LOS:
        rec = ws_lo.get("lo_scores", {}).get(lo, {})
        out[lo] = {
            "score": float(rec.get("score", 0)),
            "max_score": float(rec.get("max_score", 0)),
            "evidence_strength": rec.get("evidence_strength", "absent"),
        }
    return out


def _behavior_confidence_numeric(confidence: str | None) -> float:
    """Map confidence string to numeric value."""
    return _CONFIDENCE_MAP.get(confidence, 0.0)


def normalise_video_source(
    final_scored_files: list[dict[str, Any]],
    source_label: str = "video",
) -> _NormalisedSource:
    """Convert one or more final_scored session dicts to the common schema.

    Uses MMLA_LO_TRIGGER_MAP from pipeline_schema to derive LO scores.
    Aggregates across sessions with OR logic (if any session triggers the LO,
    it is triggered in the merged result).
    """
    from pipeline_schema import MMLA_LO_TRIGGER_MAP, MMLA_SESSION_TYPES

    # Accumulate across sessions.
    lo_triggered: dict[str, bool] = {lo: False for lo in TOP_LEVEL_LOS}
    lo_all_high: dict[str, bool] = {lo: True for lo in TOP_LEVEL_LOS}
    lo_has_any: dict[str, bool] = {lo: False for lo in TOP_LEVEL_LOS}

    for session_data in final_scored_files:
        session_key = session_data.get("session_key", "")
        session_type = MMLA_SESSION_TYPES.get(session_key, "codap_arbor")
        trigger_map = MMLA_LO_TRIGGER_MAP.get(session_type, {})
        behaviors: dict[str, Any] = session_data.get("behaviors", {})

        for lo in TOP_LEVEL_LOS:
            trigger_behaviors = trigger_map.get(lo, [])
            for b_id in trigger_behaviors:
                b_rec = behaviors.get(b_id, {})
                decision = b_rec.get("decision", "not_observed")
                if decision == "observed":
                    frame_count = b_rec.get("deepen_frame_count", 1)
                    if lo == "LO3.3" and frame_count < LO3_CREATE_MIN_FRAMES:
                        continue
                    lo_triggered[lo] = True
                    lo_has_any[lo] = True
                    conf_str = b_rec.get("confidence")
                    conf_num = _behavior_confidence_numeric(conf_str)
                    if conf_num < CONFIDENCE_THRESHOLD:
                        lo_all_high[lo] = False

    out: _NormalisedSource = {"source": source_label}
    for lo in TOP_LEVEL_LOS:
        if lo_triggered[lo]:
            strength: EvidenceStrength = "strong" if lo_all_high[lo] else "weak"
        else:
            strength = "absent"
        out[lo] = {
            "score": 1 if lo_triggered[lo] else 0,
            "max_score": 1,
            "evidence_strength": strength,
        }
    return out


# ---------------------------------------------------------------------------
# Merge
# ---------------------------------------------------------------------------


def merge_sources(
    sources: list[_NormalisedSource],
) -> dict[str, Any]:
    """Merge normalised sources into per-LO merged profiles.

    For each LO: merged_score = MAX, merged_strength = strongest,
    primary_source = highest-scoring source.
    """
    merged: dict[str, Any] = {}
    source_labels = [s["source"] for s in sources]

    for lo in TOP_LEVEL_LOS:
        best_score: float = 0.0
        best_source: str = source_labels[0] if source_labels else "worksheet"
        strengths: list[EvidenceStrength] = []
        source_detail: dict[str, Any] = {}

        for src in sources:
            label = src["source"]
            rec = src.get(lo, {})
            sc = float(rec.get("score", 0))
            st: EvidenceStrength = rec.get("evidence_strength", "absent")
            source_detail[label] = {"score": sc, "strength": st}
            strengths.append(st)
            is_better = sc > best_score or (
                sc == best_score
                and _STRENGTH_ORDER.get(st, 0) > _STRENGTH_ORDER.get(
                    source_detail.get(best_source, {}).get("strength", "absent"), 0
                )
            )
            if is_better:
                best_score = sc
                best_source = label

        merged[lo] = {
            "merged_score": best_score,
            "merged_max": max(
                (float(s.get(lo, {}).get("max_score", 0)) for s in sources),
                default=0.0,
            ),
            "evidence_strength": _strongest(strengths),
            "primary_source": best_source,
            "source_detail": source_detail,
        }

    return merged


# ---------------------------------------------------------------------------
# AI-CFT level proposal
# ---------------------------------------------------------------------------


def propose_ai_cft_level(lo_profiles: dict[str, Any]) -> str:
    """Derive AI-CFT level proposal from merged LO evidence strengths.

    Rules (in order of precedence):
      "Create"               — all three LOs strong
      "Deepen"               — LO3.1 strong AND LO3.2 strong
      "Acquire"              — LO3.1 strong, LO3.2 weak or absent
      "Acquire (provisional)"— LO3.1 weak only
      "Insufficient evidence"— LO3.1 absent
    """
    s1 = lo_profiles.get("LO3.1", {}).get("evidence_strength", "absent")
    s2 = lo_profiles.get("LO3.2", {}).get("evidence_strength", "absent")
    s3 = lo_profiles.get("LO3.3", {}).get("evidence_strength", "absent")

    if s1 == "strong" and s2 == "strong" and s3 == "strong":
        return "Create"
    if s1 == "strong" and s2 == "strong":
        return "Deepen"
    if s1 == "strong":
        return "Acquire"
    if s1 == "weak":
        return "Acquire (provisional)"
    return "Insufficient evidence"


# ---------------------------------------------------------------------------
# Review flags
# ---------------------------------------------------------------------------


def collect_review_flags(
    lo_profiles: dict[str, Any],
    missing_sources: list[str],
    ws_lo: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Build review_flags list from available evidence signals."""
    flags: list[dict[str, Any]] = []

    for lo in TOP_LEVEL_LOS:
        rec = lo_profiles.get(lo, {})
        if rec.get("evidence_strength") == "weak":
            flags.append({
                "flag": "low_confidence_evidence",
                "lo": lo,
                "severity": "low",
            })

    if ws_lo:
        for lo in TOP_LEVEL_LOS:
            lo_rec = ws_lo.get("lo_scores", {}).get(lo, {})
            for item_id in lo_rec.get("review_flags", []):
                flags.append({
                    "flag": f"ws_review_item_{item_id}",
                    "lo": lo,
                    "severity": "medium",
                })

    # Hierarchical progression check: LO3.3 observed but a prerequisite is absent.
    # weak+weak is acceptable (both levels have partial evidence).
    # Flag only when LO3.3 is present (weak or strong) but LO3.1 or LO3.2 is absent entirely.
    lo31_strength = lo_profiles.get("LO3.1", {}).get("evidence_strength", "absent")
    lo32_strength = lo_profiles.get("LO3.2", {}).get("evidence_strength", "absent")
    lo33_strength = lo_profiles.get("LO3.3", {}).get("evidence_strength", "absent")
    if lo33_strength != "absent" and lo31_strength == "absent":
        flags.append({
            "flag": "lo3_hierarchy_skip",
            "detail": f"LO3.3={lo33_strength} but LO3.1=absent — Acquire evidence missing; priority review required",
            "severity": "high",
        })
    if lo33_strength != "absent" and lo32_strength == "absent":
        flags.append({
            "flag": "lo3_hierarchy_skip",
            "detail": f"LO3.3={lo33_strength} but LO3.2=absent — Deepen evidence missing; priority review required",
            "severity": "high",
        })
    # Separate flag for the weaker signal: LO3.3 strong but LO3.1 only weak
    if lo33_strength == "strong" and lo31_strength == "weak":
        flags.append({
            "flag": "lo3_hierarchy_gap",
            "detail": f"LO3.3=strong but LO3.1=weak — Create claim outpaces Acquire evidence; review recommended",
            "severity": "medium",
        })

    if "video" in missing_sources:
        flags.append({"flag": "no_video_data", "severity": "high"})
    if "colab" in missing_sources:
        flags.append({"flag": "no_colab_data", "severity": "medium"})

    return flags


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------


def build_portfolio(
    student_id: str,
    *,
    ws_lo_dir: Path | None = None,
    mmla_dir: Path | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    """Build portfolio JSON for one student. Returns the portfolio dict."""
    ws_lo_dir = ws_lo_dir or WS_LO_DIR
    mmla_dir = mmla_dir or MMLA_DIR

    sources: list[_NormalisedSource] = []
    missing_sources: list[str] = []
    modality_coverage: dict[str, bool] = {
        "worksheet": False,
        "video": False,
        "colab": False,
    }
    ws_lo_data: dict[str, Any] | None = None

    # --- Worksheet ---
    ws_lo_path = ws_lo_dir / f"{student_id}_ws_lo.json"
    if ws_lo_path.exists():
        ws_lo_data = json.loads(ws_lo_path.read_text(encoding="utf-8"))
        sources.append(normalise_ws_source(ws_lo_data))
        modality_coverage["worksheet"] = True
    else:
        log.warning("WS-LO file not found for %s — skipping worksheet source", student_id)
        missing_sources.append("worksheet")

    # --- MMLA video (codap_arbor sessions: 21apr, 28apr) ---
    video_files: list[dict[str, Any]] = []
    for session_key in ("21apr", "28apr"):
        p = mmla_dir / f"{student_id}_{session_key}_final_scored.json"
        if p.exists():
            video_files.append(json.loads(p.read_text(encoding="utf-8")))
    if video_files:
        sources.append(normalise_video_source(video_files, source_label="video"))
        modality_coverage["video"] = True
    else:
        log.info("No MMLA video data for %s", student_id)
        missing_sources.append("video")

    # --- Colab (05may session) ---
    colab_path = mmla_dir / f"{student_id}_colab_scored.json"
    if colab_path.exists():
        colab_data = json.loads(colab_path.read_text(encoding="utf-8"))
        sources.append(normalise_video_source([colab_data], source_label="colab"))
        modality_coverage["colab"] = True
    else:
        log.info("No colab data for %s", student_id)
        missing_sources.append("colab")

    if not sources:
        log.warning("No data sources available for %s", student_id)

    lo_profiles = merge_sources(sources) if sources else {
        lo: {
            "merged_score": 0.0,
            "merged_max": 0.0,
            "evidence_strength": "absent",
            "primary_source": "none",
            "source_detail": {},
        }
        for lo in TOP_LEVEL_LOS
    }

    ai_cft_proposal = propose_ai_cft_level(lo_profiles)
    review_flags = collect_review_flags(lo_profiles, missing_sources, ws_lo_data)

    return {
        "student_id": student_id,
        "generated_at": _now_iso(),
        "is_final": False,
        "missing_sources": missing_sources,
        "modality_coverage": modality_coverage,
        "lo_profiles": lo_profiles,
        "ai_cft_proposal": ai_cft_proposal,
        "review_flags": review_flags,
        "researcher_decision": {
            "final_level": None,
            "override_reason": None,
            "reviewed_by": None,
            "reviewed_at": None,
        },
    }


def save_portfolio(
    portfolio: dict[str, Any],
    *,
    output_dir: Path | None = None,
) -> Path:
    """Write portfolio JSON to outputs/portfolios/. Returns written path."""
    out_dir = output_dir or PORTFOLIO_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{portfolio['student_id']}_portfolio.json"
    path.write_text(
        json.dumps(portfolio, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def build_and_save_portfolio(
    student_id: str,
    *,
    ws_lo_dir: Path | None = None,
    mmla_dir: Path | None = None,
    output_dir: Path | None = None,
) -> tuple[dict[str, Any], Path]:
    """Build and write portfolio for one student. Returns (portfolio, path)."""
    portfolio = build_portfolio(
        student_id,
        ws_lo_dir=ws_lo_dir,
        mmla_dir=mmla_dir,
        output_dir=output_dir,
    )
    path = save_portfolio(portfolio, output_dir=output_dir)
    return portfolio, path
