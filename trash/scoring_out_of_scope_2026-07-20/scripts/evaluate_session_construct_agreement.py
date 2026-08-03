#!/usr/bin/env python3
"""Evaluate session-level construct agreement between automated scorer and expert.

For each student in irr_students, compares:
  - Expert session-level level (from construct_scores.json): Deepen/Acquire/not_observed
  - Automated scorer session-level level (from final_scored.json or aggregated frame scores)

Primary reliability metric for publication (RF11 remediation).
Frame-level F1 is debug only.

Output:
    calibration/session_validation_metrics.json

Usage:
    python scripts/evaluate_session_construct_agreement.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SPLITS = REPO_ROOT / "calibration" / "splits_2025.json"
CS_DIR = REPO_ROOT / "training_datasets" / "2025"
DATA_2026 = REPO_ROOT / "data_sources_2026"
OUT = REPO_ROOT / "calibration" / "session_validation_metrics.json"

CONSTRUCT_BEHAVIORS = [
    "B0","B1","B2","B3","B4","B5","B6","B7",
    "B8","B9","B10","B11","B12"
]

LEVEL_RANK = {"Deepen": 3, "Acquire": 2, "not_observed": 1, "not_measurable": 0, None: -1}


def load_expert_levels(student_id: str) -> dict[str, str]:
    cs_path = CS_DIR / student_id / f"{student_id}_construct_scores.json"
    if not cs_path.is_file():
        return {}
    cs = json.loads(cs_path.read_text(encoding="utf-8"))
    return {
        b: v.get("level", "not_observed")
        for b, v in cs.get("session_scores", {}).items()
        if b in CONSTRUCT_BEHAVIORS
    }


def load_scorer_levels(student_id: str) -> dict[str, str] | None:
    for session_dir in ["codap_arbor_21april_audio", "codap_arbor_28april_audio"]:
        path = DATA_2026 / session_dir / student_id / f"{student_id}_final_scored.json"
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            return {
                b: data.get("behaviors", {}).get(b, {}).get("level", "not_observed")
                for b in CONSTRUCT_BEHAVIORS
            }
    return None


def level_agreement(expert: str, scorer: str) -> str:
    if expert == scorer:
        return "exact"
    diff = abs(LEVEL_RANK.get(expert, 0) - LEVEL_RANK.get(scorer, 0))
    if diff == 1:
        return "adjacent"
    return "distant"


def main() -> int:
    splits = json.loads(SPLITS.read_text(encoding="utf-8"))
    eval_students = splits.get("internal_val_students", []) + splits.get("irr_students", [])

    per_behavior: dict[str, list[str]] = defaultdict(list)
    per_student: list[dict] = []
    students_with_scorer: list[str] = []

    for sid in eval_students:
        expert = load_expert_levels(sid)
        scorer = load_scorer_levels(sid)

        if not expert:
            print(f"  [{sid}] no expert construct_scores — skipped")
            continue
        if scorer is None:
            print(f"  [{sid}] no scorer output (2026 scoring not run) — expert levels logged only")
            student_record = {
                "student_id": sid,
                "scorer_available": False,
                "expert_levels": expert,
                "scorer_levels": None,
                "agreements": None,
            }
            per_student.append(student_record)
            continue

        students_with_scorer.append(sid)
        agreements: dict[str, str] = {}
        for b in CONSTRUCT_BEHAVIORS:
            e = expert.get(b, "not_observed")
            s = scorer.get(b, "not_observed")
            ag = level_agreement(e, s)
            agreements[b] = ag
            per_behavior[b].append(ag)

        student_record = {
            "student_id": sid,
            "scorer_available": True,
            "expert_levels": expert,
            "scorer_levels": scorer,
            "agreements": agreements,
        }
        per_student.append(student_record)
        print(f"  [{sid}] exact={sum(1 for v in agreements.values() if v=='exact')}/{len(CONSTRUCT_BEHAVIORS)}")

    # Aggregate
    behavior_metrics: dict[str, dict] = {}
    for b in CONSTRUCT_BEHAVIORS:
        ags = per_behavior.get(b, [])
        if not ags:
            behavior_metrics[b] = {"n": 0, "exact_rate": None, "adjacent_or_exact_rate": None}
            continue
        exact = sum(1 for a in ags if a == "exact")
        adj = sum(1 for a in ags if a in ("exact", "adjacent"))
        behavior_metrics[b] = {
            "n": len(ags),
            "exact_rate": round(exact / len(ags), 3),
            "adjacent_or_exact_rate": round(adj / len(ags), 3),
        }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "debug_only_note": (
            "Frame-level F1 metrics in validation_metrics.json are debug metrics only. "
            "This file contains the PRIMARY reliability metric: session-level level agreement."
        ),
        "n_students_evaluated": len(eval_students),
        "n_students_with_scorer": len(students_with_scorer),
        "warning": (
            "2026 scoring has not been run. Scorer levels unavailable for most students. "
            "Run mmla_scorer.py on 2026 sessions to populate this report."
        ) if not students_with_scorer else None,
        "per_student": per_student,
        "per_behavior": behavior_metrics,
    }

    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\nSession validation metrics → {OUT.relative_to(REPO_ROOT)}")
    if not students_with_scorer:
        print("NOTE: 2026 scoring needed for full session-level agreement. Run mmla_scorer.py first.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
