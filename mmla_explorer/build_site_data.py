#!/usr/bin/env python3
"""Build the data files for the MMLA Data Explorer website.

Reads only files that already exist in this repository and writes:
  mmla_explorer/site/data/core.js     cohort, students, worksheets, logs, notebooks
  mmla_explorer/site/data/frames.js   one row per extracted screen-recording frame
  mmla_explorer/site/thumbs/*.jpg     small sample thumbnails of extracted frames
  mmla_explorer/site/data/*.csv       downloadable data frames
  mmla_explorer/build_report.json     what was read, what was missing, sanity checks

Nothing is invented. When a file is missing, the value is null and the gap is
recorded. Every record keeps the repository path it came from.

Run from the repository root:
    python3 mmla_explorer/build_site_data.py
"""
from __future__ import annotations

import csv
import glob
import json
import math
import os
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "mmla_explorer" / "site"
DATA_OUT = OUT / "data"
THUMBS_OUT = OUT / "thumbs"
DS = ROOT / "data_sources_2026"

# The 15 pseudonymised participants of the 2026 cohort (Sample_Student is a template).
STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
]

# Display number used in the methods text -> internal folder/file key.
WORKSHEETS = [
    {"code": "WS1", "key": "WS1", "ocr": "Worksheet1", "raw": "24_mart_2026_çalışma_kâğıdı_1_raw.json"},
    {"code": "WS3", "key": "WS3", "ocr": "Worksheet3", "raw": None},
    {"code": "WS4", "key": "WS4", "ocr": "Worksheet4", "raw": None},
    {"code": "WS5", "key": "WS5", "ocr": "Worksheet5", "raw": "24_mart_2026_çalışma_kâğıdı_5_raw.json"},
    {"code": "WS6", "key": "WS6", "ocr": "Worksheet6", "raw": "31_mart_2026_çalışma_kâğıdı_6_raw.json"},
    {"code": "WS7", "key": "WS7", "ocr": "Worksheet7", "raw": "31_mart_2026_çalışma_kâğıdı_7_raw.json"},
    {"code": "WS10", "key": "WS10", "ocr": "Worksheet10", "raw": None},
    {"code": "WS11", "key": "WS11", "ocr": None, "raw": None},
    {"code": "WS12", "key": "WS12", "ocr": None, "raw": None},
    {"code": "WS13", "key": "WS13", "ocr": "Worksheet_Xeno", "raw": None},
    {"code": "WS14", "key": "WS14", "ocr": "Worksheet_Titanic", "raw": None},
]

SESSIONS = [
    {"id": "codap_21apr", "date": "2026-04-21", "label": "21 April · CODAP Arbor",
     "tool": "CODAP Arbor", "proc_dir": "codap_arbor_21april_audio",
     "video_dir": "21 April CODAP Arbor Screen Recordings"},
    {"id": "codap_28apr", "date": "2026-04-28", "label": "28 April · CODAP Arbor",
     "tool": "CODAP Arbor", "proc_dir": "codap_arbor_28april_audio",
     "video_dir": "28 April CODAP Arbor Screen Recordings"},
]

MODELLING_ACTIONS = [
    "emit_tree_data", "drop_attribute", "change_split_values",
    "change_tree_type", "change_dataset", "data_context_change",
]

THUMBS_PER_SESSION = 16

# Yes/no observation flags written by the frame coder (shown as on-screen evidence).
EVIDENCE_FLAGS = [
    "tree_has_nodes", "dependent_variable_set", "split_values_visible", "accuracy_visible",
    "confusion_matrix_visible", "systematic_variable_selection", "threshold_reasoning",
    "accuracy_interpretation", "overfitting_awareness", "train_test_distinction",
    "confusion_matrix_reading", "iterative_refinement", "technical_difficulty",
    "misconception_detected", "aha_moment_candidate", "is_transition_frame",
]

report: dict = {"generated_at": None, "missing": [], "notes": [], "checks": []}


def rel(p: Path | str) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def load_json(p: Path):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def missing(what: str, path: str | None = None):
    report["missing"].append({"what": what, "path": path})


# ---------------------------------------------------------------- inventory
def build_inventory() -> dict:
    man = load_json(DS / "MANIFEST.json")
    groups: dict[str, dict] = defaultdict(lambda: {"files": 0, "bytes": 0, "ext": Counter()})
    for f in man["files"]:
        top = f["path"].split("/")[0]
        g = groups[top]
        g["files"] += 1
        g["bytes"] += f["size_bytes"]
        g["ext"][Path(f["path"]).suffix.lower() or "(none)"] += 1
    return {
        "source": rel(DS / "MANIFEST.json"),
        "generated_at": man.get("generated_at"),
        "file_count": man.get("file_count"),
        "total_bytes": man.get("total_bytes"),
        "folders": [
            {"folder": k, "files": v["files"], "bytes": v["bytes"], "ext": dict(v["ext"])}
            for k, v in sorted(groups.items())
        ],
    }


# ---------------------------------------------------------------- worksheets
ITEM_ID = re.compile(r"^(WS\d+_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)?|DTI_\d+|DT_[A-Z]_\w+)$")
META_KEYS = {"student_name", "student_id", "worksheet", "ws_snapshot", "page_notes", "validation", "extraction"}


def flatten(obj, prefix=""):
    """Return a list of (path, scalar) leaves. Lists of scalars are joined."""
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.extend(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(obj, list):
        if all(not isinstance(x, (dict, list)) for x in obj):
            out.append((prefix, ", ".join("null" if x is None else str(x) for x in obj) if obj else "[]"))
        else:
            for i, x in enumerate(obj):
                tag = None
                if isinstance(x, dict):
                    tag = x.get("trial_id")
                out.extend(flatten(x, f"{prefix}[{tag if tag is not None else i + 1}]"))
    else:
        out.append((prefix, obj))
    return out


def scalar(v):
    if v is None or isinstance(v, (str, int, float, bool)):
        if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
            return None
        return v
    return str(v)


def collect_checks(val, prefix=""):
    """Find every dict inside a validation block that carries an is_correct flag."""
    rows, other = [], []
    if isinstance(val, dict):
        if "is_correct" in val or "is_leaf_counts_correct" in val:
            detail = {k: scalar(v) for k, v in val.items()
                      if k not in ("is_correct", "score", "error_flag", "note") and not isinstance(v, (dict, list))}
            flags = {k: v for k, v in val.items() if k.startswith("is_") and k != "is_correct"}
            correct = val.get("is_correct")
            if correct is None and flags:
                vals = [v for v in flags.values() if isinstance(v, bool)]
                correct = all(vals) if vals else None
            rows.append({
                "check": prefix,
                "correct": correct,
                "score": scalar(val.get("score")),
                "flag": scalar(val.get("error_flag")),
                "note": scalar(val.get("note")),
                "detail": detail,
            })
            return rows, other
        for k, v in val.items():
            r, o = collect_checks(v, f"{prefix}.{k}" if prefix else k)
            rows += r
            other += o
    elif isinstance(val, list):
        for i, x in enumerate(val):
            tag = x.get("trial_id") if isinstance(x, dict) else None
            r, o = collect_checks(x, f"{prefix}[{tag if tag is not None else i + 1}]")
            rows += r
            other += o
    else:
        other.append({"path": prefix, "value": scalar(val)})
    return rows, other


def item_of(path: str) -> str:
    for seg in re.split(r"[.\[\]]", path):
        if ITEM_ID.match(seg):
            return seg
    return path.split(".")[0]


def read_ocr_worksheet(student: str, ws: dict) -> dict | None:
    if not ws["ocr"]:
        return None
    p = ROOT / "ocr_output" / student / f"{student}_{ws['ocr']}.json"
    if not p.exists():
        missing(f"OCR file {ws['code']} for {student}", rel(p) if p.parent.exists() else str(p.relative_to(ROOT)))
        return None
    d = load_json(p)
    if "extraction" in d:
        ext = d["extraction"]
    else:
        ext = {k: v for k, v in d.items() if k not in META_KEYS}
    responses = [{"path": k, "item": item_of(k), "value": scalar(v)} for k, v in flatten(ext)]
    val = d.get("validation") or {}
    summary = None
    if isinstance(val, dict):
        summary = val.get("system_analytical_summary")
        val = {k: v for k, v in val.items() if k != "system_analytical_summary"}
    checks, other = collect_checks(val)
    # Raw (pre-normalisation) file, if the folder has one.
    raw_diff, raw_path = [], None
    if ws["raw"]:
        rp = ROOT / "ocr_output" / student / ws["raw"]
        if rp.exists():
            raw_path = rel(rp)
            rd = load_json(rp)
            rext = rd.get("extraction", {k: v for k, v in rd.items() if k not in META_KEYS})
            rflat = dict(flatten(rext))
            nflat = dict(flatten(ext))
            for k in sorted(set(rflat) | set(nflat)):
                a, b = rflat.get(k, "(absent)"), nflat.get(k, "(absent)")
                if str(a) != str(b):
                    raw_diff.append({"path": k, "raw": scalar(a), "normalized": scalar(b)})
    st = os.stat(p)
    return {
        "source": rel(p),
        "modified": datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d"),
        "responses": responses,
        "checks": checks,
        "other_validation": other,
        "snapshot": d.get("ws_snapshot"),
        "page_notes": d.get("page_notes"),
        "system_summary": summary,
        "raw_source": raw_path,
        "raw_diff": raw_diff,
    }


def read_stage_artifacts(student: str, ws: dict) -> dict:
    base = ROOT / "students" / student / ws["key"]
    out = {"folder": rel(base) if base.exists() else None}
    ep = base / "extraction.json"
    if ep.exists():
        d = load_json(ep)
        g = d.get("gate_1_extraction") or {}
        items = g.get("items") or {}
        n_ok = sum(1 for v in items.values() if v not in ("(not_extracted)", None, ""))
        out["extraction"] = {
            "source": rel(ep), "status": g.get("status"), "model": g.get("ocr_model"),
            "items_total": len(items), "items_with_value": n_ok, "pdf_source": d.get("pdf_source"),
        }
    sp = base / "scoring.json"
    if sp.exists():
        d = load_json(sp)
        items = d.get("items") or []
        conf0 = bool(items) and all((i.get("score") in (0, 0.0)) and (i.get("confidence") in (0, 0.0)) for i in items)
        out["scoring"] = {
            "source": rel(sp), "total": d.get("total_score"), "max": d.get("max_score"),
            "n_items": len(items), "n_review": sum(1 for i in items if i.get("review")),
            "all_zero_with_zero_confidence": conf0,
            "note": d.get("note") or d.get("revalidation_note"),
            "items": [{"item": i.get("item"), "score": i.get("score"), "confidence": i.get("confidence"),
                       "review": i.get("review")} for i in items],
        }
    vp = base / "validation.json"
    if vp.exists():
        d = load_json(vp)
        out["validation"] = {"source": rel(vp), "keys": list(d.keys())[:20]}
    return out


def build_worksheets() -> tuple[list, dict]:
    meta = []
    for ws in WORKSHEETS:
        sch = ROOT / "worksheets" / ws["key"] / "extraction_schema.json"
        n_fields = None
        if sch.exists():
            n_fields = len(load_json(sch).get("fields") or [])
        rub = ROOT / "rubrics" / f"{ws['key']}_rubric.json"
        title = None
        ak = ROOT / "answer_key_worksheets" / f"Worksheet {ws['code'][2:]}.pdf"
        if ak.exists():
            try:
                txt = subprocess.run(["pdftotext", "-l", "1", str(ak), "-"], capture_output=True, text=True).stdout
                lines = [l.strip() for l in txt.splitlines() if l.strip()]
                for l in lines[:4]:
                    if l.lower().startswith("worksheet"):
                        title = l
                        break
            except FileNotFoundError:
                pass
        fixed = {}
        if sch.exists():
            for fld in load_json(sch).get("fields") or []:
                if "fixed_response" in fld:
                    fixed[fld.get("scoring_item_id") or fld["field_id"]] = fld["fixed_response"]
        rubric_data = None
        if rub.exists():
            def _strip_ids(obj):
                if isinstance(obj, dict):
                    return {k: _strip_ids(v) for k, v in obj.items() if k != "student_id"}
                if isinstance(obj, list):
                    return [_strip_ids(x) for x in obj]
                return obj
            rubric_data = _strip_ids(load_json(rub))
        ak_web = f"downloads/answer_keys/Worksheet {ws['code'][2:]}.pdf" if ak.exists() else None
        meta.append({
            "code": ws["code"], "key": ws["key"], "fields_in_schema": n_fields,
            "fixed_responses": fixed,
            "schema": rel(sch) if sch.exists() else None,
            "rubric": rel(rub) if rub.exists() else None,
            "rubric_data": rubric_data,
            "answer_key": rel(ak) if ak.exists() else None,
            "answer_key_url": ak_web,
            "printed_title": title,
            "pipeline": "deterministic" if ws["code"] in ("WS5", "WS6", "WS7") else "llm_rubric",
        })
    per_student = {}
    for s in STUDENTS:
        per_student[s] = {}
        for ws in WORKSHEETS:
            per_student[s][ws["code"]] = {
                "ocr": read_ocr_worksheet(s, ws),
                "stage": read_stage_artifacts(s, ws),
                "scoring": read_scoring(s, ws),
            }
    return meta, per_student


def read_scoring(student: str, ws: dict) -> dict | None:
    """Read item-level rubric scores from scoring.json.  Returns None when the
    file is missing, blocked, or every item has score=0 with confidence=0 (i.e.
    the scoring stage ran but produced no real output)."""
    p = ROOT / "students" / student / ws["key"] / "scoring.json"
    if not p.exists():
        return None
    d = load_json(p)
    if d.get("blocked"):
        return None
    items = d.get("items") or []
    if items and all(i.get("score", 0) == 0 and i.get("confidence", 0) == 0 for i in items):
        return None
    return {
        "total_score": d.get("total_score"),
        "max_score": d.get("max_score"),
        "items": [
            {"item": i["item"], "score": i.get("score"), "max_score": _item_max(i["item"]),
             "confidence": i.get("confidence"), "review": i.get("review", False)}
            for i in items
        ],
        "source": rel(p),
    }


def _item_max(item_id: str) -> float | None:
    """Look up the maximum possible score for an item from its rubric."""
    ws_code = item_id.split("_")[0]
    rub = ROOT / "rubrics" / f"{ws_code}_rubric.json"
    if not rub.exists():
        return None
    d = load_json(rub)
    item = (d.get("items") or {}).get(item_id, {})
    rules = item.get("scoring_rules") or {}
    if not rules:
        return None
    return max(float(k) for k in rules)


# ---------------------------------------------------------------- screen recordings
def video_files() -> tuple[dict, dict]:
    """Sizes of the .webm recordings, plus the SHA-256 recorded in MANIFEST.json."""
    man = load_json(DS / "MANIFEST.json")
    out, sha = {}, {}
    for f in man["files"]:
        if f["path"].endswith(".webm"):
            folder, name = f["path"].split("/", 1)
            out[(folder, Path(name).stem)] = f["size_bytes"]
            sha[(folder, Path(name).stem)] = f["sha256"]
    return out, sha


def recording_durations() -> dict:
    out = {}
    for sess in SESSIONS:
        p = DS / sess["proc_dir"] / "manifest.json"
        if p.exists():
            for r in load_json(p).get("recordings") or []:
                out[(sess["id"], r["student_id"])] = {"duration_seconds": r.get("duration_seconds"),
                                                       "transcript_status": r.get("transcript_status"),
                                                       "source": rel(p)}
    return out


DURATION_CACHE = ROOT / "mmla_explorer" / "video_durations_cache.json"


def measured_duration(path: Path, size: int, cache: dict) -> float | None:
    """Duration read from the stream timestamps (webm headers carry none).
    Cached by path and size so that the 10 GB of video is read only once."""
    key = f"{rel(path)}|{size}"
    if key in cache:
        return cache[key]
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", str(path), "-map", "0:v:0", "-c", "copy", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.findall(r"time=(\d+):(\d+):([\d.]+)", r.stderr)
    val = None
    if m:
        hh, mm, ss = m[-1]
        val = round(int(hh) * 3600 + int(mm) * 60 + float(ss), 2)
    cache[key] = val
    return val


def load_gold(student: str, session_id: str) -> dict:
    """Expert observation steps matched to frames by the video pipeline
    (silver alignment, not a human-verified match)."""
    p = ROOT / "training_datasets" / "2026" / student / session_id / "annotations" / f"{student}_gold_behavior_alignment.v1.jsonl"
    out = {}
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        d = json.loads(line)
        sv = d.get("silver_video") or {}
        md = d.get("metadata") or {}
        fid = sv.get("matched_frame_id")
        if fid:
            out[fid] = {"step": md.get("observation_step_index"), "category": md.get("bilissel_davranis_kategorisi"),
                        "method": sv.get("alignment_method"), "confidence": sv.get("confidence"),
                        "note": md.get("uzman_nitel_gozlemi_snippet"), "frame": fid, "source": rel(p)}
    return out


def load_frame_analyses(p: Path):
    d = load_json(p)
    if isinstance(d, list):
        return d, {"format": "list"}
    meta = {k: v for k, v in d.items() if k != "frame_analyses"}
    meta["format"] = "object"
    return d.get("frame_analyses") or [], meta


def make_thumb(src: Path, dst: Path) -> bool:
    """Privacy-safe thumbnail: drop browser bar (tabs show document titles) and
    taskbar, then downscale and soften so that no on-screen text is readable."""
    if dst.exists():
        return True
    if not src.exists():
        return False
    vf = "crop=in_w:in_h*0.80:0:in_h*0.155,scale=360:-2,boxblur=1:1"
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-vf", vf,
                        "-q:v", "6", str(dst)], capture_output=True)
    return r.returncode == 0 and dst.exists()


def build_sessions() -> tuple[dict, list]:
    vids, shas = video_files()
    durations = recording_durations()
    by_hash: dict = defaultdict(list)
    for (folder, name), h in shas.items():
        sid = next((x["id"] for x in SESSIONS if x["video_dir"] == folder), None)
        if sid:
            by_hash[h].append(sid)
    cache = load_json(DURATION_CACHE) if DURATION_CACHE.exists() else {}
    sessions: dict = {s: {} for s in STUDENTS}
    frame_rows: list = []
    THUMBS_OUT.mkdir(parents=True, exist_ok=True)
    for sess in SESSIONS:
        for s in STUDENTS:
            rec = {
                "session": sess["id"],
                "video_bytes": vids.get((sess["video_dir"], s)),
                "video_path": f"data_sources_2026/{sess['video_dir']}/{s}.webm" if (sess["video_dir"], s) in vids else None,
                "video_sha256": shas.get((sess["video_dir"], s)),
                "recording": durations.get((sess["id"], s)),
            }
            vpath = DS / sess["video_dir"] / f"{s}.webm"
            if rec["video_bytes"]:
                rec["video_on_disk"] = vpath.exists()
                if vpath.exists():
                    rec["video_measured_seconds"] = measured_duration(vpath, rec["video_bytes"], cache)
                else:
                    report["notes"].append(f"{s} {sess['id']}: video listed in MANIFEST.json but not on disk")
            h = shas.get((sess["video_dir"], s))
            if h:
                same = sorted(x for x in by_hash[h] if x != sess["id"])
                if same:
                    rec["same_video_file_as"] = same
                    report["notes"].append(f"{s} {sess['id']}: video file is byte-identical to {same}")
            d = DS / sess["proc_dir"] / s
            vem_p = d / f"{s}_video_extraction_manifest.json"
            if not vem_p.exists():
                rec["manifest"] = None
                if rec["video_bytes"]:
                    missing(f"Frame manifest {sess['id']} for {s}", rel(vem_p) if d.exists() else None)
                sessions[s][sess["id"]] = rec
                continue
            vem = load_json(vem_p)
            frames = []
            for f in vem.get("frames") or []:
                f = dict(f)
                if "frame_id" not in f and f.get("frame_filename"):
                    # Frames appended by a later gap-fix run use a filename instead of an id.
                    f["frame_id"] = Path(f["frame_filename"]).stem
                    cand = [d / f"{s}_frames" / f["frame_filename"], d / f["frame_filename"]]
                    hit = next((c for c in cand if c.exists()), None)
                    f["file_path"] = rel(hit) if hit else None
                frames.append(f)
            frames.sort(key=lambda f: f["source_timestamp_seconds"])
            p = vem.get("parameters") or {}
            rec["manifest"] = {
                "source": rel(vem_p),
                "generated_at": vem.get("generated_at"),
                "extraction_mode": vem.get("extraction_mode"),
                "summary": vem.get("summary"),
                "modalities": vem.get("modalities"),
                "native_resolution": (vem.get("video_profile") or {}).get("native_resolution"),
                "profile_duration_seconds": (vem.get("video_profile") or {}).get("duration_seconds"),
                "parameters": {k: p.get(k) for k in (
                    "motion_threshold_fraction", "silent_motion_threshold", "codap_gap_fill_seconds",
                    "silent_screen_gap_fill_seconds", "speech_gap_bypass_seconds", "cooldown_ms",
                    "dedup_method", "phash_threshold", "filter_non_task_screens", "task_activity")},
                "frames": len(frames),
                "triggers": dict(Counter(f.get("extraction_trigger_reason") for f in frames)),
                "added_later": dict(Counter(f.get("added_by") for f in frames if f.get("added_by"))),
                "first_s": frames[0]["source_timestamp_seconds"] if frames else None,
                "last_s": frames[-1]["source_timestamp_seconds"] if frames else None,
            }
            # frame analyses (behaviour coding)
            fa_p = d / f"{s}_codap_frame_analyses.json"
            analyses, fa_meta = ([], None)
            if fa_p.exists():
                analyses, fa_meta = load_frame_analyses(fa_p)
                rec["coding"] = {
                    "source": rel(fa_p), "format": fa_meta.get("format"), "model": fa_meta.get("model"),
                    "prompt_file": fa_meta.get("prompt_file"), "prompt_version": fa_meta.get("prompt_version"),
                    "assessed_at": fa_meta.get("assessed_at"), "frames_coded": len(analyses),
                    "alignment": fa_meta.get("alignment"), "log_csv_used": fa_meta.get("log_csv_used"),
                    "post_processing": fa_meta.get("post_processing"),
                    "behaviors": dict(Counter(a.get("primary_behavior") for a in analyses)),
                    "secondary": dict(Counter(a.get("secondary_behavior") for a in analyses if a.get("secondary_behavior"))),
                    "screen_context": dict(Counter(a.get("screen_context") for a in analyses)),
                    "deepen_phase": dict(Counter(a.get("deepen_phase") for a in analyses)),
                    "confidence": dict(Counter(a.get("analysis_confidence") for a in analyses)),
                    "first_ms": analyses[0].get("timestamp_ms") if analyses else None,
                }
            else:
                rec["coding"] = None
            gold = load_gold(s, sess["id"])
            rec["expert_steps"] = list(gold.values())
            by_id = {a.get("frame_id"): a for a in analyses if a.get("frame_id")}
            by_ms = {a.get("timestamp_ms"): a for a in analyses}
            matched = 0
            # thumbnails: evenly spaced sample
            pick = set()
            if frames:
                n = min(THUMBS_PER_SESSION, len(frames))
                pick = {round(i * (len(frames) - 1) / max(1, n - 1)) for i in range(n)}
            thumbs = []
            for i, f in enumerate(frames):
                a = by_id.get(f["frame_id"]) or by_ms.get(round(f["source_timestamp_seconds"] * 1000))
                if a:
                    matched += 1
                m = f.get("metrics") or {}
                row = {
                    "s": s, "ss": sess["id"], "id": f["frame_id"],
                    "t": round(f["source_timestamp_seconds"], 1),
                    "tr": f.get("extraction_trigger_reason"),
                    "px": m.get("pixel_change_percentage"),
                    "sp": m.get("associated_speaker_role"),
                    "b": a.get("primary_behavior") if a else None,
                    "b2": a.get("secondary_behavior") if a else None,
                    "sc": a.get("screen_context") if a else None,
                    "ph": a.get("deepen_phase") if a else None,
                    "cf": a.get("analysis_confidence") if a else None,
                }
                if f.get("added_by"):
                    row["ab"] = f["added_by"]
                if a:
                    ev = [k for k in EVIDENCE_FLAGS if a.get(k) is True]
                    if ev:
                        row["ev"] = ev
                g = gold.get(f["frame_id"])
                if g:
                    row["gx"] = g
                if i in pick:
                    src = ROOT / f["file_path"] if f.get("file_path") else None
                    name = f"{s}_{sess['id']}_{f['frame_id']}.jpg"
                    if src is not None and make_thumb(src, THUMBS_OUT / name):
                        row["th"] = name
                        thumbs.append(name)
                    else:
                        missing(f"Frame image {f['frame_id']} ({sess['id']}, {s})", f.get("file_path"))
                frame_rows.append(row)
            if rec.get("coding"):
                rec["coding"]["frames_matched_to_manifest"] = matched
            length = rec.get("video_measured_seconds") or (rec.get("recording") or {}).get("duration_seconds")
            if frames and length:
                rec["frame_coverage"] = round(frames[-1]["source_timestamp_seconds"] / length, 3)
            rec["thumbs"] = thumbs
            # speech layer
            hd_p = d / f"{s}_hybrid_diarization.json"
            if hd_p.exists():
                hd = load_json(hd_p)
                sl = hd.get("speaker_labeling") or {}
                rec["speech"] = {
                    "source": rel(hd_p), "status": hd.get("status"),
                    "duration_seconds": hd.get("duration_seconds"),
                    "segments": hd.get("segment_count"),
                    "pipeline": hd.get("pipeline"),
                    "method": sl.get("method"),
                    "role_counts": sl.get("role_counts"),
                    "speakers": [{k: sp.get(k) for k in ("speaker_id", "role", "confidence", "duration_seconds", "segment_count")}
                                 for sp in (sl.get("speakers") or [])],
                }
            else:
                rec["speech"] = None
            # VOTAT file computed by the pipeline from the event log
            key = {"codap_21apr": "21apr", "codap_28apr": "28apr"}.get(sess["id"])
            if key:
                vp = d / f"{s}_{key}_b15_log.json"
                if vp.exists():
                    v = load_json(vp)
                    rec["votat"] = {"source": rel(vp), "votat_rate": v.get("votat_rate"),
                                    "total_emits": v.get("total_emits"),
                                    "intervals": len(v.get("votat_intervals") or []),
                                    "max_consecutive_votat": v.get("max_consecutive_votat"),
                                    "computed_at": v.get("computed_at"),
                                    "interval_rows": v.get("votat_intervals") or []}
            sessions[s][sess["id"]] = rec
    DURATION_CACHE.write_text(json.dumps(cache, indent=1), encoding="utf-8")
    return sessions, frame_rows


def build_episode_tables() -> dict:
    try:
        import pandas as pd
    except ImportError:
        report["notes"].append("pandas not available: parquet tables skipped")
        return {}
    out: dict = {}
    for s in STUDENTS:
        out[s] = {}
        for sess in SESSIONS:
            base = ROOT / "training_datasets" / "2026" / s / sess["id"] / "exports" / "tabular"
            rec = {}
            ep = base / f"{s}_episodes.parquet"
            if ep.exists():
                df = pd.read_parquet(ep)
                rec["episodes_source"] = rel(ep)
                rec["episodes"] = [{
                    "id": r.episode_id, "category": r.dominant_category,
                    "start_ms": int(r.start_ms) if r.start_ms == r.start_ms and r.start_ms is not None else None,
                    "end_ms": int(r.end_ms) if r.end_ms == r.end_ms and r.end_ms is not None else None,
                    "duration_ms": int(r.duration_ms) if r.duration_ms == r.duration_ms and r.duration_ms is not None else None,
                    "steps": int(r.step_count), "assistance": r.assistance_status,
                    "codes": [str(c) for c in (r.codes_observed if r.codes_observed is not None else [])],
                } for r in df.itertuples()]
            cp = base / f"{s}_episode_process_codes.parquet"
            if cp.exists():
                df = pd.read_parquet(cp)
                rec["codes_source"] = rel(cp)
                rec["code_rows"] = int(len(df))
                rec["code_decisions"] = {str(k): int(v) for k, v in df["decision"].value_counts().items()}
                obs = df[df["decision"] == "observed"]
                rec["codes_observed"] = sorted({f"{r.v_code}|{r.v_code_label}" for r in obs.itertuples()})
            fp = base / f"{s}_session_ml_features.parquet"
            if fp.exists():
                df = pd.read_parquet(fp)
                rec["features_source"] = rel(fp)
                row = df.iloc[0].to_dict()
                rec["features_true"] = sorted(k for k, v in row.items() if k.endswith("_present") and v is True)
                rec["features_columns"] = int(df.shape[1])
            if rec:
                out[s][sess["id"]] = rec
    return out


# ---------------------------------------------------------------- logs
def _norm(x: str) -> str:
    import unicodedata
    return unicodedata.normalize("NFC", x).casefold().strip()


def load_pseudonym_map() -> dict:
    """Official real name -> pseudonym map kept by the project (not copied here)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("anon", ROOT / "scripts" / "anonymize_student_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return {_norm(k): v for k, v in mod.PSEUDONYM_MAP.items() if v in STUDENTS}


def resolve_log_id(raw: str, pmap: dict) -> str | None:
    """Map a log session ID to a pseudonym.
    Pseudonyms pass through. Real names resolve via the official map: exact match,
    or a unique match on the first name or the surname. Middle names never match.
    Anything else (for example instructor IDs) returns None and is excluded."""
    if raw in STUDENTS:
        return raw
    k = _norm(raw or "")
    if not k:
        return None
    if k in pmap:
        return pmap[k]
    toks = k.split()
    cands = set()
    for key, pseudo in pmap.items():
        kt = key.split()
        if toks[0] == kt[0] or (len(toks) > 1 and toks[-1] == kt[-1]) or (len(toks) == 1 and toks[0] == kt[-1]):
            cands.add(pseudo)
    if len(cands) == 1:
        return cands.pop()
    import difflib
    best = max(pmap.items(), key=lambda kv: difflib.SequenceMatcher(None, k, kv[0]).ratio())
    if difflib.SequenceMatcher(None, k, best[0]).ratio() >= 0.9:
        return best[1]
    return None


def build_logs() -> dict:
    src = DS / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
    rows = list(csv.DictReader(open(src, encoding="utf-8")))
    allowed = set(STUDENTS)
    pmap = load_pseudonym_map()
    excluded = Counter()
    remapped = Counter()
    per: dict = defaultdict(list)
    for r in rows:
        raw = r.get("student_id")
        sid = resolve_log_id(raw, pmap)
        day = (r.get("created_at") or "")[:10]
        if sid is None:
            excluded[day] += 1
            continue
        if sid != raw:
            remapped[(sid, day)] += 1
        r = dict(r, student_id=sid)
        per[(sid, day)].append(r)
    # cross-check: the 21 April file is a prefix of the 28 April file
    other = {}
    for name in ("21 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv",
                 "07 Nisan 2026 CODAP Arbor Titanic Log File (anonymized).csv"):
        p = DS / "All Documents" / name
        with open(p, encoding="utf-8") as fh:
            other[name] = sum(1 for _ in fh) - 1
    days = Counter((r.get("created_at") or "")[:10] for r in rows)
    out = {
        "source": rel(src),
        "rows_total": len(rows),
        "rows_by_day": dict(sorted(days.items())),
        "rows_excluded_unmatched_by_day": dict(sorted(excluded.items())),
        "rows_remapped_to_pseudonym": [{"student": a, "date": b, "rows": n} for (a, b), n in sorted(remapped.items())],
        "other_files_row_counts": other,
        "per_student": {},
    }
    def ts(r):
        return datetime.fromisoformat(r["created_at"].replace("+00", "+00:00"))
    for (sid, day), rs in sorted(per.items()):
        rs.sort(key=ts)
        acts = Counter(r["action"] for r in rs)
        emits = []
        for r in rs:
            if r["action"] == "emit_tree_data":
                try:
                    pr = json.loads(r["parameters"])
                except json.JSONDecodeError:
                    pr = {}
                emits.append({"t": ts(r), "accuracy": pr.get("accuracy"), "depth": pr.get("depth"),
                              "dataset": pr.get("dataset"), "target": pr.get("dependent_variable"),
                              "TP": pr.get("TP"), "TN": pr.get("TN"), "FP": pr.get("FP"), "FN": pr.get("FN"),
                              "tree_type": pr.get("tree_type"), "nodes": pr.get("node_count")})
        drops = []
        for r in rs:
            if r["action"] == "drop_attribute":
                try:
                    drops.append(json.loads(r["parameters"]).get("attribute"))
                except json.JSONDecodeError:
                    pass
        t0 = ts(rs[0])
        accs = [e["accuracy"] for e in emits if isinstance(e["accuracy"], (int, float))]
        out["per_student"].setdefault(sid, {})[day] = {
            "events": len(rs),
            "first_event": rs[0]["created_at"][:19],
            "last_event": rs[-1]["created_at"][:19],
            "span_minutes": round((ts(rs[-1]) - t0).total_seconds() / 60, 1),
            "actions": dict(acts),
            "modelling_actions": {a: acts.get(a, 0) for a in MODELLING_ACTIONS},
            "emit_count": len(emits),
            "minutes_to_first_emit": round((emits[0]["t"] - t0).total_seconds() / 60, 1) if emits else None,
            "last_emit_accuracy": accs[-1] if accs else None,
            "accuracy_sd": round(statistics.pstdev(accs), 4) if len(accs) >= 2 else None,
            "predictor_drops": len(drops),
            "unique_attributes_dropped": sorted({a for a in drops if a}),
            "emits": [{k: (v.strftime("%H:%M:%S") if k == "t" else v) for k, v in e.items()} for e in emits],
        }
    out["delete_events_present"] = any("delete" in a.lower() for a in Counter(r["action"] for r in rows))
    out["action_types"] = dict(Counter(r["action"] for k, rs in per.items() for r in rs))
    return out


# ---------------------------------------------------------------- notebooks
def build_notebooks() -> dict:
    out = {}
    nb_dir = DS / "Final Ödevi Dokümanları"
    fl = ROOT / "worksheets" / "FINAL_LIZARD"
    for s in STUDENTS:
        rec = {}
        p = nb_dir / f"{s}.ipynb"
        if p.exists():
            nb = load_json(p)
            cells = nb.get("cells", [])
            code = [c for c in cells if c.get("cell_type") == "code"]
            md = [c for c in cells if c.get("cell_type") == "markdown"]
            counts = [c.get("execution_count") for c in code]
            ran = [c for c in counts if c is not None]
            decreases = sum(1 for a, b in zip(ran, ran[1:]) if b < a)
            err_cells = sum(1 for c in code if any(o.get("output_type") == "error" for o in c.get("outputs", [])))
            img_cells = sum(1 for c in code if any("image/png" in (o.get("data") or {}) for o in c.get("outputs", [])))
            empty_code = sum(1 for c in code if not "".join(c.get("source", [])).strip())
            src = "\n".join("".join(c.get("source", [])) for c in code)
            rec["file"] = {
                "source": rel(p), "cells": len(cells), "code_cells": len(code), "markdown_cells": len(md),
                "executed_code_cells": len(ran), "never_executed_code_cells": len(code) - len(ran),
                "empty_code_cells": empty_code,
                "execution_counts": counts, "max_execution_count": max(ran) if ran else None,
                "order_reversals": decreases,
                "cells_with_error_output": err_cells, "cells_with_image_output": img_cells,
                "uses": {
                    "lizard_data.csv": "lizard_data" in src,
                    "DecisionTreeClassifier": "DecisionTreeClassifier" in src,
                    "train_test_split": "train_test_split" in src,
                    "max_depth": "max_depth" in src,
                    "get_dummies": "get_dummies" in src,
                    "plot_tree": "plot_tree" in src,
                },
            }
        else:
            missing(f"Final project notebook for {s}", None)
        ep = fl / f"example_extracted_{s}.json"
        if ep.exists():
            d = load_json(ep)
            exps = d.get("dt_experiments") or []
            rec["extraction"] = {
                "source": rel(ep),
                "data_source_note": (d.get("data_source") or {}).get("data_source_note"),
                "models": (d.get("metadata") or {}).get("total_models_created"),
                "targets": [q.get("target_variable") for q in (d.get("formulated_research_questions") or [])],
                "questions_written": sum(1 for q in (d.get("formulated_research_questions") or []) if q.get("formulated_question")),
                "split": d.get("step3_split_global"),
                "experiments": [{
                    "target": e.get("target_variable"),
                    "features": (e.get("code_evidence") or {}).get("features_used"),
                    "checks": {k: v for k, v in (e.get("code_evidence") or {}).items() if isinstance(v, bool)},
                    "depth_min": (e.get("depth_search") or {}).get("depth_range_min"),
                    "depth_max": (e.get("depth_search") or {}).get("depth_range_max"),
                } for e in exps],
            }
        sp = fl / f"scoring_output_{s}.json"
        if sp.exists():
            d = load_json(sp)
            rec["scoring"] = {
                "source": rel(sp),
                "scored_by": (d.get("scoring_metadata") or {}).get("scored_by"),
                "rubric_version": (d.get("scoring_metadata") or {}).get("rubric_version"),
                "sections": {k: {"awarded": v.get("section_total_awarded"), "possible": v.get("section_total_possible")}
                             for k, v in (d.get("section_scores") or {}).items()},
            }
        out[s] = rec
    return out


# ---------------------------------------------------------------- codebook
def build_codebook() -> dict:
    p = ROOT / "prompts" / "MMLA_CODAP_video_system_prompt.md"
    return {"prompt_file": rel(p) if p.exists() else None,
            "prompt_lines": sum(1 for _ in open(p, encoding="utf-8")) if p.exists() else None}


def training_log_meta() -> dict:
    """What the training-bundle log metadata files say about event-log availability."""
    files = sorted(glob.glob(str(ROOT / "training_datasets" / "2026" / "*" / "*" / "metadata" / "*_log_process_metadata.json")))
    flags = Counter()
    note = None
    for f in files:
        d = load_json(Path(f))
        flags[str(d.get("log_available"))] += 1
        note = note or (d.get("video_log_sync") or {}).get("note")
    return {"files": len(files), "log_available_values": dict(flags), "example_note": note,
            "example_source": rel(files[0]) if files else None}


def build_downloads() -> dict:
    """Copy teaching materials that exist as files in the project into the site."""
    import shutil
    dl = OUT / "downloads"
    (dl / "worksheets").mkdir(parents=True, exist_ok=True)
    (dl / "answer_keys").mkdir(parents=True, exist_ok=True)
    out = {"worksheets": [], "cards": None}
    for ws in WORKSHEETS:
        ak = ROOT / "answer_key_worksheets" / f"Worksheet {ws['code'][2:]}.pdf"
        if ak.exists():
            dst = dl / "answer_keys" / f"Worksheet {ws['code'][2:]}.pdf"
            shutil.copyfile(ak, dst)
    for ws in WORKSHEETS:
        # Blank student editions, copied from the researcher's worksheet set.
        srcp = ROOT / "mmla_explorer" / "materials" / "worksheets" / f"{ws['code']}.pdf"
        if srcp.exists():
            dst = dl / "worksheets" / f"{ws['code']}.pdf"
            shutil.copyfile(srcp, dst)
            out["worksheets"].append({"code": ws["code"], "file": f"downloads/worksheets/{ws['code']}.pdf",
                                      "bytes": dst.stat().st_size, "source": rel(srcp)})
        else:
            missing(f"Worksheet PDF {ws['code']}", rel(srcp))
    cp = ROOT / "data" / "prodabi_food_cards.csv"
    if cp.exists():
        shutil.copyfile(cp, dl / "food_data_cards.csv")
        rows = list(csv.DictReader(open(cp, encoding="utf-8")))
        out["cards"] = {"file": "downloads/food_data_cards.csv", "source": rel(cp), "rows": rows,
                        "columns": list(rows[0].keys()) if rows else []}
    return out


def pdf_text(paths) -> str:
    txt = ""
    for p in paths:
        r = subprocess.run(["pdftotext", str(p), "-"], capture_output=True, text=True)
        txt += r.stdout
    return txt


# ---------------------------------------------------------------- checks
def privacy_scan(blob: str):
    """Fail if any full real name, or any real log ID, appears in the output.
    Single tokens (many Turkish names are also common words) are reported as
    warnings with their count so a person can review them."""
    low = _norm(blob)
    pmap = load_pseudonym_map()
    src = DS / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv"
    log_ids = {_norm(r.get("student_id") or "") for r in csv.DictReader(open(src, encoding="utf-8"))}
    full = {k for k in pmap} | {i for i in log_ids if i and i not in {_norm(x) for x in STUDENTS}}
    def present(t):
        return re.search(r"(?<![\w])" + re.escape(t) + r"(?![\w])", low) is not None
    full_hits = sum(1 for t in full if present(t))
    tokens = {t for k in full for t in k.split() if len(t) >= 3}
    token_hits = {t: len(re.findall(r"(?<![\w])" + re.escape(t) + r"(?![\w])", low)) for t in tokens}
    token_hits = {t: n for t, n in token_hits.items() if n}
    report["checks"].append({"check": "no full real names or real log IDs in output",
                             "names_checked": len(full), "passed": full_hits == 0, "hit_count": full_hits})
    report["checks"].append({"check": "single name tokens found (review: may be ordinary words)",
                             "tokens_checked": len(tokens), "tokens_found": len(token_hits),
                             "occurrences": sum(token_hits.values())})
    if full_hits:
        sys.exit(f"Privacy check failed: {full_hits} real name(s) found in output")


def main():
    DATA_OUT.mkdir(parents=True, exist_ok=True)
    report["generated_at"] = datetime.now().isoformat(timespec="seconds")
    inventory = build_inventory()
    ws_meta, ws_data = build_worksheets()
    sessions, frames = build_sessions()
    episodes = build_episode_tables()
    logs = build_logs()
    notebooks = build_notebooks()
    downloads = build_downloads()

    # Duplicate-session check (same coded frames in two sessions).
    for s in STUDENTS:
        a = [(r["t"], r["b"]) for r in frames if r["s"] == s and r["ss"] == "codap_21apr"]
        b = [(r["t"], r["b"]) for r in frames if r["s"] == s and r["ss"] == "codap_28apr"]
        if a and a == b:
            report["notes"].append(f"{s}: 21 April and 28 April frame lists are identical")
            for ss in ("codap_21apr", "codap_28apr"):
                sessions[s][ss]["identical_to_other_session"] = True

    core = {
        "built_at": report["generated_at"],
        "students": STUDENTS,
        "worksheets": ws_meta,
        "sessions_meta": SESSIONS,
        "inventory": inventory,
        "ws": ws_data,
        "sessions": sessions,
        "episodes": episodes,
        "logs": logs,
        "notebooks": notebooks,
        "codebook": build_codebook(),
        "frame_total": len(frames),
        "build": {"missing": report["missing"], "notes": report["notes"]},
        "thumbs_per_session": THUMBS_PER_SESSION,
        "downloads": downloads,
        "training_log_meta": training_log_meta(),
    }
    core_js = json.dumps(core, ensure_ascii=False, separators=(",", ":"), default=str)
    frames_js = json.dumps(frames, ensure_ascii=False, separators=(",", ":"))
    privacy_scan(core_js + frames_js)
    # Worksheet PDFs carry the researcher's own translation credit, so they are
    # checked against student names only.
    pdf_low = _norm(pdf_text(sorted((OUT / "downloads" / "worksheets").glob("*.pdf"))))
    pdf_hits = sum(1 for k in load_pseudonym_map()
                   if re.search(r"(?<![\w])" + re.escape(k) + r"(?![\w])", pdf_low))
    report["checks"].append({"check": "no student real names in worksheet PDFs", "passed": pdf_hits == 0, "hit_count": pdf_hits})
    if pdf_hits:
        sys.exit("Privacy check failed: a student name appears in a worksheet PDF")
    (DATA_OUT / "core.js").write_text("window.CORE=" + core_js + ";\n", encoding="utf-8")
    (DATA_OUT / "frames.js").write_text("window.FRAMES=" + frames_js + ";\n", encoding="utf-8")

    # Downloadable data frames.
    def write_csv(name, header, rows):
        with open(DATA_OUT / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)
    write_csv("frames.csv", ["student", "session", "frame_id", "time_s", "trigger", "pixel_change_pct",
                             "speaker_role", "primary_behavior", "secondary_behavior", "screen_context",
                             "deepen_phase", "confidence"],
              [[r["s"], r["ss"], r["id"], r["t"], r["tr"], r["px"], r["sp"], r["b"], r["b2"], r["sc"], r["ph"], r["cf"]]
               for r in frames])
    ws_rows = []
    for s in STUDENTS:
        for code, rec in ws_data[s].items():
            o = rec["ocr"]
            if not o:
                continue
            chk = {c["check"]: c for c in o["checks"]}
            for r in o["responses"]:
                c = chk.get(f"item_checks.{r['item']}") or {}
                ws_rows.append([s, code, r["item"], r["path"], r["value"], c.get("correct"), c.get("flag"), o["source"]])
    write_csv("worksheet_responses.csv", ["student", "worksheet", "item", "field_path", "extracted_value",
                                          "item_check_correct", "item_check_flag", "source_file"], ws_rows)
    log_rows = []
    for s, days in logs["per_student"].items():
        for day, v in days.items():
            log_rows.append([s, day, v["events"], v["span_minutes"], v["emit_count"], v["minutes_to_first_emit"],
                             v["last_emit_accuracy"], v["accuracy_sd"], v["predictor_drops"],
                             len(v["unique_attributes_dropped"])] + [v["modelling_actions"][a] for a in MODELLING_ACTIONS])
    write_csv("log_sessions.csv", ["student", "date", "events", "span_minutes", "emit_count", "minutes_to_first_emit",
                                   "last_emit_accuracy", "accuracy_sd", "predictor_drops", "unique_attributes"]
              + MODELLING_ACTIONS, log_rows)

    # Stamp asset links so browsers load the fresh build.
    idx = OUT / "index.html"
    if idx.exists():
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        html = re.sub(r"\?v=\w+", "?v=" + stamp, idx.read_text(encoding="utf-8"))
        idx.write_text(html, encoding="utf-8")

    ep_rows = []
    for st, sess_map in episodes.items():
        for sid, rec in sess_map.items():
            for e in rec.get("episodes") or []:
                ep_rows.append([st, sid, e["id"], e["category"], e["start_ms"], e["end_ms"], e["duration_ms"], e["steps"], e["assistance"]])
    write_csv("episodes.csv", ["student", "session", "episode_id", "category", "start_ms", "end_ms", "duration_ms",
                               "steps", "assistance"], ep_rows)

    report["counts"] = {
        "students": len(STUDENTS),
        "frames": len(frames),
        "frames_with_behavior": sum(1 for r in frames if r["b"]),
        "thumbnails": len(list(THUMBS_OUT.glob("*.jpg"))),
        "worksheet_ocr_files": sum(1 for s in STUDENTS for r in ws_data[s].values() if r["ocr"]),
        "worksheet_response_rows": len(ws_rows),
        "log_student_days": len(log_rows),
    }
    (ROOT / "mmla_explorer" / "build_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(report["counts"], indent=2))
    print("missing:", len(report["missing"]), "| notes:", report["notes"])


if __name__ == "__main__":
    main()
