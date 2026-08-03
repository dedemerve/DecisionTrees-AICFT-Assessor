#!/usr/bin/env python3
"""Build calibration dataset v2 from v1 with RF01/RF02/RF03/RF09 fixes.

Changes from v1:
- All frame_image_path values converted to repo-relative (RF09)
- label_status field added: always step_inherited_indicator (RF01)
- rubric_behaviors limited to B0-B12; B13 tracked via b13_status (RF03)
- B15/B16/B17 moved to process_flags, removed from rubric_behaviors (RF02)
- silver_confidence field added per frame
- schema_version bumped to 2.0
- provenance block with label_policy warning

Usage:
    python scripts/build_2025_calibration_dataset_v2.py
    python scripts/build_2025_calibration_dataset_v2.py --validate
"""

from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_PATH = REPO_ROOT / "calibration" / "2025_calibration_dataset.json"
V2_PATH = REPO_ROOT / "calibration" / "2025_calibration_dataset_v2.json"
SCHEMA_PATH = REPO_ROOT / "schema" / "calibration_dataset_v2.schema.json"
SPLITS_PATH = REPO_ROOT / "calibration" / "splits_2025.json"

CONSTRUCT_BEHAVIORS = {"B0","B1","B2","B3","B4","B5","B6","B7","B8","B9","B10","B11","B12"}
PROCESS_FLAGS_MAP = {
    "b15_votat":        "B15_votat_log",
    "b16_error_recovery": "B16_error_recovery",
    "b17_planning":     "B17_planning",
}

LABEL_POLICY = (
    "step_inherited_indicator — NOT gold-standard. Labels propagated from expert "
    "step alignments via nearest-step matching. Independent adjudication not performed."
)


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def to_relative(abs_path: str) -> str:
    p = Path(abs_path)
    try:
        return str(p.relative_to(REPO_ROOT))
    except ValueError:
        return abs_path


def load_splits() -> dict[str, str]:
    if not SPLITS_PATH.is_file():
        return {}
    splits = json.loads(SPLITS_PATH.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for role, students in splits.items():
        if role in ("fewshot_students", "irr_students", "internal_val_students"):
            label = role.replace("_students", "").replace("_", "_")
            for sid in students:
                mapping[sid] = label
    return mapping


def migrate_frame(frame: dict, split_map: dict[str, str]) -> dict:
    old_behaviors: list[str] = frame.get("rubric_behaviors", [])

    construct_behaviors = [b for b in old_behaviors if b in CONSTRUCT_BEHAVIORS]

    # B13 status
    if "B13" in old_behaviors:
        b13_status = "coded_present"
    else:
        b13_status = "not_measurable_no_transcript"

    # Process flags from v1 boolean fields
    process_flags = {}
    for v1_key, v2_key in PROCESS_FLAGS_MAP.items():
        val = frame.get(v1_key)
        process_flags[v2_key] = bool(val) if val is not None else None

    # Repo-relative path
    abs_path = frame.get("frame_image_path", "")
    rel_path = to_relative(abs_path)

    new_frame = {
        "frame_id": frame["frame_id"],
        "student_id": frame["student_id"],
        "timestamp_s": frame.get("timestamp_s", 0.0),
        "frame_image_path": rel_path,
        "label_status": "step_inherited_indicator",
        "inherited_from_step": frame.get("inherited_from_step"),
        "silver_confidence": frame.get("silver_confidence", "none"),
        "expert_screenshot": frame.get("expert_screenshot", False),
        "rubric_behaviors": construct_behaviors,
        "b13_status": b13_status,
        "process_flags": process_flags,
        "codebook_codes": frame.get("codebook_codes"),
        "label_source": frame.get("label_source", "nearest_gold_silver_anchor"),
    }
    return new_frame


def validate_frame(frame: dict) -> list[str]:
    errors: list[str] = []
    path = frame.get("frame_image_path", "")
    if path.startswith("/"):
        errors.append(f"Absolute path: {path}")
    invalid_behaviors = [b for b in frame.get("rubric_behaviors", []) if b not in CONSTRUCT_BEHAVIORS]
    if invalid_behaviors:
        errors.append(f"Non-construct behaviors in rubric_behaviors: {invalid_behaviors}")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description="Build calibration dataset v2")
    ap.add_argument("--validate", action="store_true", help="Validate output only")
    args = ap.parse_args()

    if not V1_PATH.is_file():
        print(f"ERROR: v1 not found at {V1_PATH.relative_to(REPO_ROOT)}")
        return 1

    v1 = json.loads(V1_PATH.read_text(encoding="utf-8"))
    split_map = load_splits()

    students_v2 = {}
    for sid, meta in v1.get("students", {}).items():
        students_v2[sid] = {
            **meta,
            "split_role": split_map.get(sid, "unassigned"),
        }

    frames_v2 = []
    errors_total: list[str] = []
    for frame in v1["frames"]:
        new_frame = migrate_frame(frame, split_map)
        errs = validate_frame(new_frame)
        if errs:
            errors_total.extend([f"[{new_frame['frame_id']}] {e}" for e in errs])
        frames_v2.append(new_frame)

    if errors_total:
        print(f"VALIDATION ERRORS ({len(errors_total)}):")
        for e in errors_total[:20]:
            print(f"  {e}")
        return 1

    # Build behavior positive counts for construct behaviors only
    beh_counts = {b: sum(1 for f in frames_v2 if b in f["rubric_behaviors"]) for b in sorted(CONSTRUCT_BEHAVIORS)}
    b13_counts = {}
    for status in ("coded_present", "coded_absent", "not_measurable_no_transcript", "not_coded"):
        b13_counts[status] = sum(1 for f in frames_v2 if f["b13_status"] == status)

    process_counts = {
        "B15_votat_log_true": sum(1 for f in frames_v2 if f["process_flags"].get("B15_votat_log")),
        "B16_error_recovery_true": sum(1 for f in frames_v2 if f["process_flags"].get("B16_error_recovery")),
        "B17_planning_true": sum(1 for f in frames_v2 if f["process_flags"].get("B17_planning")),
    }

    payload = {
        "schema_version": "2.0",
        "provenance": {
            "source_script": "scripts/build_2025_calibration_dataset_v2.py",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "git_commit_hint": get_git_commit(),
            "label_policy": LABEL_POLICY,
            "migrated_from": "calibration/2025_calibration_dataset.json (v1)",
        },
        "label_warning": (
            "ALL frame labels are step_inherited_indicator. "
            "No independent double-coding has been performed. "
            "Do not report these as gold-standard labels in publications."
        ),
        "students": students_v2,
        "summary": {
            "total_frames": len(frames_v2),
            "n_students": len(students_v2),
            "construct_behavior_positive_counts": beh_counts,
            "b13_status_counts": b13_counts,
            "process_flag_true_counts": process_counts,
            "absolute_path_count": 0,
            "label_status_counts": {"step_inherited_indicator": len(frames_v2)},
        },
        "frames": frames_v2,
    }

    if args.validate:
        print("Validation passed. Not writing file (--validate mode).")
        print(f"  Frames: {len(frames_v2)}")
        print(f"  Absolute paths: 0")
        return 0

    V2_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Written → {V2_PATH.relative_to(REPO_ROOT)}")
    print(f"  Frames: {len(frames_v2)}")
    print(f"  Students: {len(students_v2)}")
    print(f"  Absolute paths: 0 (RF09 fixed)")
    print(f"  B15/B16/B17 removed from rubric_behaviors (RF02 fixed)")
    print(f"  B13 tracked via b13_status (RF03 addressed)")
    print(f"  label_status: step_inherited_indicator for all (RF01 disclosed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
