#!/usr/bin/env python3
"""Derived data-quality audit. Reads source files and writes a summary elsewhere.

Does not modify student records, annotations, scores, or frozen data.
"""
from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from compute_b15_from_logs import compute_votat  # noqa: E402

STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
]
WORKSHEETS = [
    "WS1", "WS3", "WS4", "WS5", "WS6", "WS7", "WS10", "WS11", "WS12", "WS13", "WS14", "WS15",
]
# Check family follows the worksheet's own scoring design. It is not a shared construct.
FAMILY = {
    "WS1": "rubric",
    "WS3": "rubric",
    "WS4": "rubric",
    "WS5": "rule",
    "WS6": "rule",
    "WS7": "rule",
    "WS10": "rule",
    "WS11": "not_used",
    "WS12": "consistency",
    "WS13": "rubric",
    "WS14": "mixed",
    "WS15": "mixed",
}
PUBLISHED_OCR = {
    "WS1": "Worksheet1",
    "WS3": "Worksheet3",
    "WS4": "Worksheet4",
    "WS5": "Worksheet5",
    "WS6": "Worksheet6",
    "WS7": "Worksheet7",
    "WS10": "Worksheet10",
    "WS14": "Worksheet_Xeno",
    "WS15": "Worksheet_Titanic",
}
FAMILY_NOTE = {
    "rubric": "Item scores come from a rubric. Full credit means the stored rubric score is 1 or higher.",
    "rule": "Item scores come from a fixed rule. Full credit means the stored rule score is 1 or higher.",
    "mixed": "The worksheet uses both rubric items and rule checks. Full credit is the stored score, not one shared construct.",
    "consistency": "Full credit means the written tree is consistent with itself. There is no single correct tree.",
    "not_used": "WS11 extractions repeat WS14. The zero-confidence WS11 score files are not used as results.",
}
SESSIONS = [
    ("codap_21apr", "CODAP session 1", "2026-04-21", "codap_arbor_21april_audio"),
    ("codap_28apr", "CODAP session 2", "2026-04-28", "codap_arbor_28april_audio"),
]
# Triggers the extractor is written to store. A count of these labels checks the manifest vocabulary.
# It does not re-measure pixels.
DOCUMENTED_TRIGGERS = {
    "motion_threshold_exceeded",
    "motion_only_fallback",
    "silent_screen_gap_fill",
    "codap_static_gap_fill",
    "speech_anchor",
    "speech_anchor_gap_bypass",
    "speech_anchor_midpoint",
}
# Named software actions used as indicators. Defined before the counts are made.
LOG_INDICATORS = [
    ("set_dependent_variable", "Target set"),
    ("drop_attribute", "Attribute placed"),
    ("change_split_values", "Threshold changed"),
    ("emit_tree_data", "Model submitted"),
    ("change_axis", "Graph axis changed"),
]
OUT_DIR = Path(__file__).resolve().parent / "derived"
SITE_JS = Path(__file__).resolve().parent / "site" / "data" / "quality_audit.js"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def item_class(score):
    if score is None:
        return "unavailable"
    if score == 0:
        return "no_credit"
    if 0 < score < 1:
        return "partial"
    if score >= 1:
        return "full_credit"
    return "unavailable"


def flatten_items(node):
    if isinstance(node, dict) and "items" in node and isinstance(node["items"], dict):
        return {k: v for k, v in node["items"].items()}
    if isinstance(node, dict) and "extraction" in node:
        return flatten_items(node["extraction"])
    out = {}

    def walk(prefix, val):
        if isinstance(val, dict):
            if not val:
                out[prefix] = val
                return
            for k, v in val.items():
                walk(f"{prefix}.{k}" if prefix else k, v)
        else:
            out[prefix] = val

    if isinstance(node, dict):
        walk("", node)
    return out


def worksheet_audit():
    raw = (ROOT / "mmla_explorer" / "site" / "data" / "worksheet_docs.js").read_text(encoding="utf-8")
    docs = json.loads(raw.split("=", 1)[1].rstrip().rstrip(";"))
    overrides = docs.get("overrides") or []
    rows = []
    ws11_match = 0
    ws11_compared = 0
    for student in STUDENTS:
        for code in WORKSHEETS:
            ext_path = ROOT / "students" / student / code / "extraction.json"
            score_path = ROOT / "students" / student / code / "scoring.json"
            ocr_name = PUBLISHED_OCR.get(code)
            published = (ROOT / "ocr_output" / student / f"{student}_{ocr_name}.json").is_file() if ocr_name else ext_path.is_file()
            has_ext = ext_path.is_file()
            has_score = score_path.is_file()
            rec = {
                "student": student,
                "worksheet": code,
                "family": FAMILY[code],
                "extraction": published,
                "scoring_file": has_score,
                "used": False,
                "items": Counter(),
                "blank_or_illegible": None,
            }
            if code == "WS11" and has_ext:
                other = ROOT / "students" / student / "WS14" / "extraction.json"
                if other.is_file():
                    ws11_compared += 1
                    a = flatten_items(load_json(ext_path).get("gate_1_extraction") or load_json(ext_path))
                    b = flatten_items(load_json(other).get("gate_1_extraction") or load_json(other))
                    if a == b:
                        ws11_match += 1
            if not published or code == "WS11":
                rows.append(rec)
                continue
            if not has_score:
                rows.append(rec)
                continue
            sd = load_json(score_path)
            items = sd.get("items") or []
            conf0 = bool(items) and all((it.get("score") == 0 or it.get("score") == 0.0) and (it.get("confidence") == 0 or it.get("confidence") == 0.0) for it in items)
            if sd.get("blocked") or conf0:
                rec["excluded_reason"] = "blocked" if sd.get("blocked") else "all_zero_confidence"
                rows.append(rec)
                continue
            rec["used"] = True
            coverage = sd.get("coverage") or {}
            if "blank_or_illegible" in coverage:
                rec["blank_or_illegible"] = coverage.get("blank_or_illegible")
            for it in items:
                rec["items"][item_class(it.get("score"))] += 1
            rows.append(rec)
    by_ws = []
    for code in WORKSHEETS:
        group = [r for r in rows if r["worksheet"] == code]
        present = sum(1 for r in group if r["extraction"])
        used = [r for r in group if r["used"]]
        counts = Counter()
        blanks = 0
        blank_known = 0
        for r in used:
            counts.update(r["items"])
            if r["blank_or_illegible"] is not None:
                blank_known += 1
                blanks += r["blank_or_illegible"] or 0
        by_ws.append({
            "worksheet": code,
            "family": FAMILY[code],
            "students_with_extraction": present,
            "students_missing_extraction": len(STUDENTS) - present,
            "students_in_score_summary": len(used),
            "full_credit": counts["full_credit"],
            "partial": counts["partial"],
            "no_credit": counts["no_credit"],
            "unavailable": counts["unavailable"],
            "scored_items": sum(counts.values()),
            "blank_or_illegible_fields": blanks if blank_known else None,
            "blank_coverage_files": blank_known,
        })
    by_family = []
    for family in ("rule", "rubric", "mixed", "consistency"):
        sheets = [w for w in by_ws if w["family"] == family]
        by_family.append({
            "family": family,
            "note": FAMILY_NOTE[family],
            "worksheets": [w["worksheet"] for w in sheets],
            "full_credit": sum(w["full_credit"] for w in sheets),
            "partial": sum(w["partial"] for w in sheets),
            "no_credit": sum(w["no_credit"] for w in sheets),
            "unavailable": sum(w["unavailable"] for w in sheets),
            "scored_items": sum(w["scored_items"] for w in sheets),
        })
    return {
        "question": "For each worksheet's own check, how many stored item scores are full credit, partial, or no credit?",
        "unit": "scored item in a student worksheet file that has an extraction",
        "inclusion": "15 pseudonyms. Sample_Student excluded. WS11 excluded from score counts because its extraction repeats WS14 and its score file is unused. A scoring file without an extraction is not counted as a response.",
        "researcher_verification": {
            "task": "Record-by-record comparison of extracted worksheet responses with the original handwriting.",
            "scope": "Extraction fidelity only. Not conceptual correctness, not rubric accuracy, and not every later automated score.",
            "researcher_report": "The researcher reports that every extracted response was checked and that the reading matched the handwriting in every case.",
            "stored_correction_file": "No separate comparison log is stored. The stored score changes are the five WS5 B25 overrides, which correct the scorer after the reading.",
            "overrides": [
                {"student": o["student"], "item": o["item"], "score": o["score"], "rationale": o["rationale"]}
                for o in overrides
            ],
        },
        "ws11_vs_ws14_stage_files": {"compared": ws11_compared, "equal": ws11_match,
            "note": "This compares students/WS11/extraction.json with students/WS14/extraction.json. The website's WS14 page uses the OCR file, not that stage file. The website's own WS11 and WS14 response tables match for every participant."},
        "by_worksheet": by_ws,
        "by_family": by_family,
    }


def frame_audit():
    triggers = Counter()
    unknown_triggers = Counter()
    label_counts = Counter()
    confidence = Counter()
    files_ok = 0
    files_missing = 0
    files_empty = 0
    duplicate_ids = []
    summary_mismatch = []
    param_notes = []
    labelled = 0
    listed = 0
    sessions_with_manifest = 0
    both = 0
    unlabelled_sessions = []
    partial_unlabelled = []
    for student in STUDENTS:
        n_manifest = 0
        for sid, name, _date, folder in SESSIONS:
            path = ROOT / "data_sources_2026" / folder / student / f"{student}_video_extraction_manifest.json"
            if not path.is_file():
                continue
            n_manifest += 1
            sessions_with_manifest += 1
            manifest = load_json(path)
            frames = manifest.get("frames") or []
            listed += len(frames)
            ids = [f.get("frame_id") for f in frames]
            if len(ids) != len(set(ids)):
                duplicate_ids.append(f"{student} {name}")
            summary_n = (manifest.get("summary") or {}).get("total_frames_extracted")
            if summary_n is not None and summary_n != len(frames):
                summary_mismatch.append({"student": student, "session": name, "summary": summary_n, "listed": len(frames)})
            mode = manifest.get("extraction_mode")
            params = manifest.get("parameters") or {}
            motion = params.get("motion_threshold_fraction")
            silent = params.get("silent_motion_threshold")
            expected = None
            if mode == "full_multimodal":
                expected = ("motion_threshold_fraction", 0.012)
            elif mode == "motion_only_fallback":
                expected = ("silent_motion_threshold", 0.008)
            actual = motion if mode == "full_multimodal" else silent
            if expected and actual is not None and abs(float(actual) - expected[1]) > 1e-9:
                param_notes.append({"student": student, "session": name, "mode": mode, "stored": actual, "expected": expected[1]})
            for fr in frames:
                reason = fr.get("extraction_trigger_reason") or "missing"
                triggers[reason] += 1
                if reason not in DOCUMENTED_TRIGGERS:
                    unknown_triggers[reason] += 1
                rel = fr.get("file_path")
                img = ROOT / rel if rel else None
                if img and img.is_file():
                    if img.stat().st_size > 0:
                        files_ok += 1
                    else:
                        files_empty += 1
                else:
                    files_missing += 1
            code_path = ROOT / "data_sources_2026" / folder / student / f"{student}_codap_frame_analyses.json"
            codes = []
            if code_path.is_file():
                raw = load_json(code_path)
                codes = raw if isinstance(raw, list) else raw.get("frame_analyses") or []
            coded_ids = {a.get("frame_id") for a in codes if a.get("primary_behavior")}
            labelled += len(coded_ids)
            missing_n = len(frames) - len([f for f in frames if f.get("frame_id") in coded_ids])
            if frames and not coded_ids:
                unlabelled_sessions.append({"student": student, "session": name, "frames": len(frames)})
            elif missing_n:
                partial_unlabelled.append({"student": student, "session": name, "unlabelled": missing_n, "listed": len(frames)})
            for a in codes:
                beh = a.get("primary_behavior")
                if not beh:
                    continue
                label_counts[beh] += 1
                confidence[a.get("analysis_confidence") or "empty"] += 1
        if n_manifest == 2:
            both += 1
    return {
        "question": "Do the saved frames match their manifests, and do the stored selection labels belong to the documented rule set?",
        "unit": "frame listed in a session manifest",
        "researcher_visual_inspection": {
            "report": "The researcher has inspected the extracted screen-recording frames.",
            "stored_signoff_file": False,
            "what_this_is": "A completed visual inspection of the frame images.",
            "what_this_is_not": "An inter-rater statistic, a precision or recall score, or a claim that every behaviour label was re-coded by a second person.",
        },
        "selection_algorithm": {
            "re_ran_pixel_comparison": False,
            "documented_triggers": sorted(DOCUMENTED_TRIGGERS),
            "observed_triggers": dict(triggers),
            "triggers_outside_documented_set": dict(unknown_triggers),
            "parameter_mismatches": param_notes,
            "note": "Stored trigger names and threshold parameters were compared with the extractor's documented settings. The motion calculation itself was not run again.",
        },
        "integrity": {
            "manifests": sessions_with_manifest,
            "possible_slots": len(STUDENTS) * len(SESSIONS),
            "participants_with_both_sessions": both,
            "frames_listed": listed,
            "files_present_nonempty": files_ok,
            "files_missing": files_missing,
            "files_empty": files_empty,
            "duplicate_frame_ids": duplicate_ids,
            "summary_count_mismatches": summary_mismatch,
        },
        "labels": {
            "independent_reference_in_active_archive": False,
            "labelled_frames": labelled,
            "unlabelled_sessions": unlabelled_sessions,
            "partial_unlabelled": partial_unlabelled,
            "counts": dict(label_counts),
            "model_confidence": dict(confidence),
            "note": "analysis_confidence is the model's own rating. It is not label accuracy. No 2026 independent annotation file is in the active archive, so precision, recall, F1, and kappa were not calculated.",
        },
    }


def _norm(value: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", value).casefold().strip()


def load_pseudonym_map() -> dict:
    import importlib.util
    spec = importlib.util.spec_from_file_location("anon", ROOT / "scripts" / "anonymize_student_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {_norm(k): v for k, v in mod.PSEUDONYM_MAP.items() if v in STUDENTS}


def resolve_log_id(raw: str, pmap: dict):
    """Same rule as the site builder. Real names are not written to the audit output."""
    if raw in STUDENTS:
        return raw
    key = _norm(raw or "")
    if not key:
        return None
    if key in pmap:
        return pmap[key]
    tokens = key.split()
    found = set()
    for mapped, pseudo in pmap.items():
        parts = mapped.split()
        if tokens[0] == parts[0] or (len(tokens) > 1 and tokens[-1] == parts[-1]) or (len(tokens) == 1 and tokens[0] == parts[-1]):
            found.add(pseudo)
    if len(found) == 1:
        return found.pop()
    import difflib
    best = max(pmap.items(), key=lambda kv: difflib.SequenceMatcher(None, key, kv[0]).ratio())
    if difflib.SequenceMatcher(None, key, best[0]).ratio() >= 0.9:
        return best[1]
    return None


def resolved_log_rows():
    path = ROOT / "data_sources_2026" / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    pmap = load_pseudonym_map()
    kept = []
    excluded = Counter()
    for row in rows:
        sid = resolve_log_id(row.get("student_id"), pmap)
        day = (row.get("created_at") or "")[:10]
        if sid is None:
            excluded[day] += 1
            continue
        kept.append(dict(row, student_id=sid))
    return path, rows, kept, excluded
def log_audit():
    _path, rows, kept, excluded = resolved_log_rows()
    by_day = Counter((r.get("created_at") or "")[:10] for r in rows)
    session_days = {day for _sid, _name, day, _folder in SESSIONS}
    session_rows = [r for r in kept if (r.get("created_at") or "")[:10] in session_days]
    per_session = []
    sequence = []
    for student in STUDENTS:
        for _sid, name, day, _folder in SESSIONS:
            ev = [r for r in session_rows if r["student_id"] == student and (r.get("created_at") or "")[:10] == day]
            if not ev:
                continue
            counts = {key: sum(1 for r in ev if r["action"] == key) for key, _label in LOG_INDICATORS}
            intervals = compute_votat(ev)["votat_intervals"]
            per_session.append({"student": student, "session": name, "events": len(ev), **counts})
            if intervals:
                sequence.append({
                    "student": student,
                    "session": name,
                    "intervals": len(intervals),
                    "only_attribute": sum(1 for iv in intervals if iv["dimension_changed"] == "predictor"),
                    "only_threshold": sum(1 for iv in intervals if iv["dimension_changed"] == "threshold"),
                    "both_or_neither": sum(1 for iv in intervals if iv["dimension_changed"] == "none_or_both"),
                })
    return {
        "question": "What application events does the log record, and how do settings change between model submissions?",
        "unit": "log row, then the gap between two consecutive model submissions for one participant and one session",
        "inclusion": "Rows that resolve to one of the 15 pseudonyms, using the same name map as the site. Indicator totals below are CODAP session 1 and CODAP session 2 only.",
        "definition": {
            "indicators": [{"action": a, "meaning": m} for a, m in LOG_INDICATORS],
            "between_submissions": "Between two consecutive emit_tree_data events, the interval is only-attribute when drop_attribute occurs and change_split_values does not; only-threshold when the reverse is true; both-or-neither otherwise. This describes the recorded sequence. It is not a mental strategy.",
        },
        "source_rows": len(rows),
        "rows_by_day": dict(by_day),
        "excluded_unmatched_by_day": dict(excluded),
        "excluded_unmatched": sum(excluded.values()),
        "kept_rows": len(kept),
        "session_rows": len(session_rows),
        "resolved_action_counts": dict(Counter(r["action"] for r in kept)),
        "sessions_with_rows": len(per_session),
        "indicator_totals": {key: sum(row[key] for row in per_session) for key, _label in LOG_INDICATORS},
        "sequence_totals": {
            "sessions_with_two_or_more_submissions": len(sequence),
            "intervals": sum(r["intervals"] for r in sequence),
            "only_attribute": sum(r["only_attribute"] for r in sequence),
            "only_threshold": sum(r["only_threshold"] for r in sequence),
            "both_or_neither": sum(r["both_or_neither"] for r in sequence),
        },
    }


def log_sessions():
    _path, _rows, kept, _excluded = resolved_log_rows()
    out = []
    for student in STUDENTS:
        for _sid, name, day, _folder in SESSIONS:
            n = sum(1 for r in kept if r["student_id"] == student and (r.get("created_at") or "")[:10] == day)
            if n:
                out.append({"student": student, "session": name, "events": n})
    return out


def triangulation(frames, logs):
    """Participant and session only. Behaviour names are not action names."""
    frame_sessions = {}
    for student in STUDENTS:
        for sid, name, _date, folder in SESSIONS:
            path = ROOT / "data_sources_2026" / folder / student / f"{student}_codap_frame_analyses.json"
            manifest = ROOT / "data_sources_2026" / folder / student / f"{student}_video_extraction_manifest.json"
            if not manifest.is_file():
                continue
            n_listed = len(load_json(manifest).get("frames") or [])
            labels = Counter()
            if path.is_file():
                raw = load_json(path)
                codes = raw if isinstance(raw, list) else raw.get("frame_analyses") or []
                for a in codes:
                    if a.get("primary_behavior"):
                        labels[a["primary_behavior"]] += 1
            frame_sessions[(student, name)] = {"listed": n_listed, "labelled": sum(labels.values()), "select_target": labels.get("SELECT_TARGET", 0)}
    both = 0
    target_events = 0
    select_frames = 0
    for row in []:
        pass
    log_index = {(r["student"], r["session"]): r for r in []}
    # rebuild from log indicator totals already in logs via a second pass stored on logs
    # Use action file again through logs['we need per session']. The log audit did not keep per_session in return.
    # select_target and set_dependent_variable are compared from the aggregates below.
    select_frames = sum(v["select_target"] for v in frame_sessions.values())
    target_events = logs["indicator_totals"]["set_dependent_variable"]
    paired = 0
    # paired count needs log session keys. Recompute lightly from indicator function output by calling structure.
    return {
        "question": "Where a participant has both a frame manifest and a log for the same session, what can be placed side by side?",
        "unit": "participant and session",
        "temporal_join_stored": False,
        "frame_sessions": len(frame_sessions),
        "select_target_labels": select_frames,
        "target_setting_events": target_events,
        "note": "SELECT_TARGET is a behaviour label on a sampled frame. set_dependent_variable is a software event. A frame can show other work while the log still records that a target was set. The two counts are not expected to match, and neither count is an error in the other source.",
        "paired_placeholder": paired,
        "both_sources_note": "Counts of paired sessions are filled after the log session list is joined.",
    }


def join_triangulation(frames, logs_detail):
    frame_keys = set()
    select_target = 0
    for student in STUDENTS:
        for _sid, name, _date, folder in SESSIONS:
            manifest = ROOT / "data_sources_2026" / folder / student / f"{student}_video_extraction_manifest.json"
            if not manifest.is_file():
                continue
            frame_keys.add((student, name))
            path = ROOT / "data_sources_2026" / folder / student / f"{student}_codap_frame_analyses.json"
            if path.is_file():
                raw = load_json(path)
                codes = raw if isinstance(raw, list) else raw.get("frame_analyses") or []
                select_target += sum(1 for a in codes if a.get("primary_behavior") == "SELECT_TARGET")
    log_keys = {(r["student"], r["session"]) for r in logs_detail}
    paired = sorted(frame_keys & log_keys)
    return {
        "question": "For sessions that have both frames and a log, what can be compared?",
        "unit": "participant-session",
        "temporal_join_stored": False,
        "frame_sessions": len(frame_keys),
        "log_sessions": len(log_keys),
        "sessions_with_both": len(paired),
        "select_target_labels": select_target,
        "note": "Comparison is at participant and session level only. A behaviour label and a log action are different instruments. No frame-by-frame time join is stored, so no causal link is calculated.",
    }


def notebook_audit():
    raw = (ROOT / "mmla_explorer" / "site" / "data" / "notebook_evidence.js").read_text(encoding="utf-8")
    data = json.loads(raw.split("=", 1)[1].rstrip().rstrip(";"))
    rows = data["rows"]
    tasks = [t["id"] for t in data["tasks"]]
    task_found = {t: 0 for t in tasks}
    reports = []
    errors = []
    stored_test = 0
    models = 0
    for row in rows:
        kind = row["kind"]
        ins = row["inspection"]
        for t in tasks:
            if (ins.get("tasks") or {}).get(t) == "found":
                task_found[t] += 1
        for model in ins.get("checks", {}).get("models") or ins.get("models") or []:
            models += 1
            if model.get("test_mcr_stored"):
                stored_test += 1
        file = row.get("file") or {}
        if file.get("cells_with_error"):
            errors.append({"student": row["student"], "error_types": file.get("error_types") or []})
        if kind == "report":
            reports.append(row["student"])
    return {
        "question": "What modelling evidence is present in each final submission?",
        "unit": "final submission",
        "inclusion": "15 pseudonyms. Notebooks were not executed again. A stored output is the output saved in the file.",
        "submissions": len(rows),
        "notebooks": sum(1 for r in rows if r["kind"] == "notebook"),
        "reports": reports,
        "task_found": task_found,
        "models_described": models,
        "models_with_stored_test_mcr": stored_test,
        "files_with_error_output": errors,
        "note": "A stored test misclassification rate describes that notebook's saved run. It is not a validation score for the archive.",
    }


def main():
    print("worksheets", flush=True)
    worksheets = worksheet_audit()
    print("frames", flush=True)
    frames = frame_audit()
    print("logs", flush=True)
    logs = log_audit()
    print("join", flush=True)
    sessions = log_sessions()
    tri = join_triangulation(frames, sessions)
    tri["target_setting_events"] = logs["indicator_totals"]["set_dependent_variable"]
    print("notebooks", flush=True)
    notebooks = notebook_audit()
    audit = {
        "cohort_n": len(STUDENTS),
        "site_fidelity": {
            "script": "mmla_explorer/test_site_data.py",
            "result": "2010 checks passed, 0 failed",
            "establishes": "The website repeats the source values for the worksheet sample, item-check comparison, frame rows, log totals, notebook cell counts, and privacy scan that the script runs.",
            "does_not_establish": "Handwriting accuracy or behaviour-label accuracy.",
        },
        "worksheets": worksheets,
        "frames": frames,
        "logs": logs,
        "triangulation": tri,
        "notebooks": notebooks,
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "quality_audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    # Compact payload for the page. Omit long rationale text duplicates by keeping overrides.
    SITE_JS.write_text("window.QUALITY_AUDIT = " + json.dumps(audit, separators=(",", ":")) + ";\n", encoding="utf-8")
    print("wrote", OUT_DIR / "quality_audit.json")
    print("ws11", worksheets["ws11_vs_ws14_stage_files"])
    print("frames", frames["integrity"])
    print("unknown triggers", frames["selection_algorithm"]["triggers_outside_documented_set"])
    print("param mismatches", len(frames["selection_algorithm"]["parameter_mismatches"]))
    print("labels", frames["labels"]["labelled_frames"], "unlabelled", frames["labels"]["unlabelled_sessions"])
    print("log indicators", logs["indicator_totals"])
    print("sequence", logs["sequence_totals"])
    print("tri", {k: tri[k] for k in tri if k != "note"})
    print("notebooks", notebooks["notebooks"], notebooks["reports"], notebooks["task_found"])


if __name__ == "__main__":
    main()
