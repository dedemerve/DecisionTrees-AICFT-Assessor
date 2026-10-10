"""
Bridge old ocr_output/ JSON files into students/*/WS*/extraction.json format.

Each ocr_output file has rich structured content from an earlier extraction
pipeline. This script reads those files and writes them into the gate-envelope
format that student_bundle.extraction_responses() expects:

    {
        "stage": "extraction",
        "student_id": "...",
        "worksheet": "...",
        "gate_1_extraction": {
            "status": "pass",
            "items": { "<item_id>": "<value>", ... }
        }
    }

The original ocr_output files are NEVER modified or deleted.
Existing extraction.json files that already have non-empty items are skipped
unless --force is passed.

Usage:
    python scripts/bridge_ocr_output.py [--worksheets WS6 WS7 ...] [--force] [--dry-run]
"""

import argparse
import json
import logging
import pathlib
import sys
from datetime import datetime, timezone

REPO = pathlib.Path(__file__).resolve().parent.parent
STUDENTS_DIR = REPO / "students"
OCR_DIR = REPO / "ocr_output"

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

ALL_STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
    "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara",
    "Melinda", "Serena",
]


def _find_ocr_file(student: str, patterns: list[str]) -> pathlib.Path | None:
    ocr_dir = OCR_DIR / student
    if not ocr_dir.exists():
        return None
    for pat in patterns:
        hits = list(ocr_dir.glob(f"*{pat}"))
        if hits:
            return hits[0]
    return None


def _flatten(obj, prefix="", out=None):
    """Recursively flatten a nested dict into dot-separated keys."""
    if out is None:
        out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            _flatten(v, f"{prefix}{k}.", out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _flatten(v, f"{prefix}{i}.", out)
    else:
        key = prefix.rstrip(".")
        out[key] = obj
    return out


def extract_ws5(raw: dict) -> dict:
    """WS5: threshold-search trials + final decision.

    Preserves all leaf-count and error-count fields that ws5_validation
    needs for row_consistency scoring, plus the final decision text.
    """
    ext = raw.get("extraction", {})
    trials = ext.get("trials", [])
    items = {}
    for trial in trials:
        tid = trial.get("trial_id", "?")
        def _s(v):
            return str(v) if v is not None else "(not_extracted)"
        items[f"WS5_trial_{tid}_feature"]          = _s(trial.get("parsed_feature"))
        items[f"WS5_trial_{tid}_left_op"]          = _s(trial.get("left_operator"))
        items[f"WS5_trial_{tid}_left_threshold"]   = _s(trial.get("left_threshold"))
        items[f"WS5_trial_{tid}_right_op"]         = _s(trial.get("right_operator"))
        items[f"WS5_trial_{tid}_right_threshold"]  = _s(trial.get("right_threshold"))
        items[f"WS5_trial_{tid}_left_rec"]         = _s(trial.get("left_leaf_recommended"))
        items[f"WS5_trial_{tid}_left_not_rec"]     = _s(trial.get("left_leaf_not_recommended"))
        items[f"WS5_trial_{tid}_right_rec"]        = _s(trial.get("right_leaf_recommended"))
        items[f"WS5_trial_{tid}_right_not_rec"]    = _s(trial.get("right_leaf_not_recommended"))
        items[f"WS5_trial_{tid}_errors"]           = _s(trial.get("student_error_count"))
        items[f"WS5_trial_{tid}_mcr"]              = _s(trial.get("student_mcr"))
    fd = ext.get("final_decision_raw")
    items["WS5_final_decision"] = str(fd) if fd else "(not_extracted)"
    return items


def extract_ws6(raw: dict) -> tuple[dict, dict]:
    """WS6: return (items, extra_gate1_fields).

    worksheet_validation.build_technical_validation reads gate_1_extraction
    .tree_structure directly (not from items), so we must preserve the nested
    tree_structure at gate_1_extraction level.  items carries flat leaf values
    for extraction_responses(); extra carries the original nested structure.
    """
    ext = raw.get("extraction", {})
    tree = ext.get("tree_structure", {})
    items = {}
    for node_key, node in tree.items():
        if not isinstance(node, dict):
            items[f"WS6_{node_key}"] = str(node)
            continue
        for field, val in node.items():
            items[f"WS6_{node_key}_{field}"] = str(val) if val is not None else "(not_extracted)"
    if not items:
        items["WS6_B1"] = "(not_extracted)"
    return items, {"tree_structure": tree}


def extract_ws7(raw: dict) -> tuple[dict, dict]:
    """WS7: map ocr tree_structure to both rubric IDs and validation IDs.

    Rubric scoring uses WS7_1..7; ws7_validation.validate_ws7_extraction
    expects WS7_P1_box1..3 (path letters) and WS7_B1..3 (rule text).
    Both sets are included so each system finds what it looks for.

    Rubric items:
      WS7_1 = depth_0 left threshold (e.g. "< 180")
      WS7_2 = depth_0 right threshold (e.g. "> 180")
      WS7_3 = depth_1 inner left threshold (e.g. "< 7,7")
      WS7_4 = depth_1 inner right threshold (e.g. "> 7,7")
      WS7_5/WS7_P1_box1 = rule_1_box path letter (expected B)
      WS7_6/WS7_P1_box2 = rule_2_box path letter (expected A)
      WS7_7/WS7_P1_box3 = rule_3_box path letter (expected C)
    ws7_validation also expects WS7_B1..3 (rule-text blanks).
    """
    ext = raw.get("extraction", {})
    tree = ext.get("tree_structure", {})
    rules = ext.get("rule_matching", {})
    d0 = tree.get("depth_0", {})
    d1 = tree.get("depth_1", {})
    inner = d1.get("right_child", {}) if isinstance(d1, dict) else {}

    def fmt_threshold(op, val):
        if op is None and val is None:
            return "(not_extracted)"
        op_str = op or ""
        val_str = str(val).replace(".", ",") if val is not None else ""
        return f"{op_str} {val_str}".strip() or "(not_extracted)"

    def rule_box(key):
        v = rules.get(key)
        return str(v) if v else "(not_extracted)"

    items = {
        # Rubric threshold items
        "WS7_1": fmt_threshold(d0.get("left_operator"), d0.get("left_threshold_value")),
        "WS7_2": fmt_threshold(d0.get("right_operator"), d0.get("right_threshold_value")),
        "WS7_3": fmt_threshold(inner.get("left_operator"), inner.get("left_threshold_value")),
        "WS7_4": fmt_threshold(inner.get("right_operator"), inner.get("right_threshold_value")),
        # Rubric path-letter items (WS7_5..7) AND validation aliases (WS7_P1_box*)
        "WS7_5":       rule_box("rule_1_box"),
        "WS7_P1_box1": rule_box("rule_1_box"),
        "WS7_6":       rule_box("rule_2_box"),
        "WS7_P1_box2": rule_box("rule_2_box"),
        "WS7_7":       rule_box("rule_3_box"),
        "WS7_P1_box3": rule_box("rule_3_box"),
        # Rule-text blanks expected by ws7_validation (students usually left blank)
        "WS7_B1": "(not_extracted)",
        "WS7_B2": "(not_extracted)",
        "WS7_B3": "(not_extracted)",
    }
    return items, {"tree_structure": tree}


def extract_ws10(raw: dict) -> dict:
    """WS10: threshold error table.

    Rubric items WS10_B1..B7 = error counts per threshold row.
    WS10_B8 = student's optimal threshold selection (numeric value).

    Melinda/Serena have Worksheet_Titanic.json (a different worksheet).
    The bridge returns a sentinel item so the caller can detect this.
    """
    ext = raw.get("extraction", {})
    # Detect Titanic worksheet -- it has titanic_vs1_egitim instead of threshold_error_table
    if "titanic_vs1_egitim" in ext:
        return {"WS10__WRONG_WORKSHEET": "Titanic worksheet -- not WS10"}

    table = ext.get("threshold_error_table", {})
    items = {}
    for item_id, cell in table.items():
        # item_id is already WS10_B1..B7 -- extract just the error count
        val = cell.get("error_count_parsed") if isinstance(cell, dict) else cell
        items[item_id] = str(val) if val is not None else "(not_extracted)"

    # WS10_B8 = optimal threshold value
    opt = ext.get("optimal_threshold", {})
    opt_val = opt.get("value_parsed") if isinstance(opt, dict) else opt
    items["WS10_B8"] = str(opt_val) if opt_val is not None else "(not_extracted)"

    return items or {"WS10_B1": "(not_extracted)"}


def extract_ws11(raw: dict) -> dict:
    """WS11: Xeno worksheet -- items keyed DTI_xx inside extraction."""
    ext = raw.get("extraction", {})
    items = {}
    for k, v in ext.items():
        items[k] = str(v) if v is not None else "(not_extracted)"
    return items or {"DTI_01": "(not_extracted)"}


def extract_ws_dt_intro(raw: dict) -> dict:
    """WS_DT_INTRO: flat DT_A_Q1..DT_B_Qx keys at top level."""
    items = {}
    for k, v in raw.items():
        if k.startswith("DT_"):
            items[k] = str(v) if v is not None else "(not_extracted)"
    return items or {"DT_A_Q1": "(not_extracted)"}


WORKSHEET_CONFIG = {
    "WS5": {
        "patterns": ["_Worksheet5.json", "çalışma_kâğıdı_5_raw.json"],
        "extractor": extract_ws5,
    },
    "WS6": {
        "patterns": ["_Worksheet6.json", "çalışma_kâğıdı_6_raw.json"],
        "extractor": extract_ws6,
    },
    "WS7": {
        "patterns": ["_Worksheet7.json", "çalışma_kâğıdı_7_raw.json"],
        "extractor": extract_ws7,
    },
    "WS10": {
        "patterns": ["_Worksheet10.json", "_Worksheet_Titanic.json"],
        "extractor": extract_ws10,
    },
    "WS14": {
        "patterns": ["_Worksheet_Xeno.json"],
        "extractor": extract_ws11,
    },
    "WS_DT_INTRO": {
        "patterns": ["çalışma_kâğıdı_dt_raw.json"],
        "extractor": extract_ws_dt_intro,
    },
}


def bridge_student(student: str, ws: str, cfg: dict, dry_run: bool, force: bool) -> str:
    ocr_file = _find_ocr_file(student, cfg["patterns"])
    if ocr_file is None:
        return "SKIP_NO_OCR_FILE"

    out_dir = STUDENTS_DIR / student / ws
    out_path = out_dir / "extraction.json"

    if out_path.exists() and not force:
        existing = json.loads(out_path.read_text())
        g1 = existing.get("gate_1_extraction", {})
        existing_items = g1.get("items", {})
        already_filled = any(
            "(not_extracted)" not in str(v) and v
            for v in existing_items.values()
        )
        if already_filled:
            return "SKIP_ALREADY_FILLED"

    raw = json.loads(ocr_file.read_text(encoding="utf-8"))
    result = cfg["extractor"](raw)
    if isinstance(result, tuple):
        items, extra_gate1 = result
    else:
        items, extra_gate1 = result, {}

    non_empty = sum(1 for v in items.values() if "(not_extracted)" not in str(v) and v)

    if dry_run:
        return f"DRY_RUN: {len(items)} items, {non_empty} non-empty, src={ocr_file.name}"

    envelope = {
        "stage": "extraction",
        "student_id": student,
        "worksheet": ws,
        "gate_1_extraction": {
            "status": "pass" if non_empty > 0 else "fail",
            "bridged_from": str(ocr_file.relative_to(REPO)),
            "bridged_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
            **extra_gate1,
        },
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(envelope, ensure_ascii=False, indent=2), encoding="utf-8")
    return f"BRIDGED: {len(items)} items, {non_empty} non-empty"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--worksheets", nargs="+", default=list(WORKSHEET_CONFIG.keys()))
    parser.add_argument("--students", nargs="+", default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    students = args.students or ALL_STUDENTS
    unknown_ws = [w for w in args.worksheets if w not in WORKSHEET_CONFIG]
    if unknown_ws:
        log.error("Unknown worksheets: %s", unknown_ws)
        sys.exit(1)

    if args.dry_run:
        print("\nDRY RUN -- no files will be written.\n")

    bridged = skipped = errors = 0
    for ws in args.worksheets:
        cfg = WORKSHEET_CONFIG[ws]
        for student in students:
            try:
                status = bridge_student(student, ws, cfg, args.dry_run, args.force)
            except Exception as exc:
                status = f"ERROR: {exc}"
                log.exception("%s %s failed", student, ws)
                errors += 1
            if status.startswith("BRIDGED") or status.startswith("DRY_RUN"):
                bridged += 1
            else:
                skipped += 1
            print(f"  {student:12s} {ws:15s}: {status}")

    print(f"\nDone. bridged={bridged} skipped={skipped} errors={errors}")


if __name__ == "__main__":
    main()
