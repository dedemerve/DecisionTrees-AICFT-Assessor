#!/usr/bin/env python3
"""Fidelity tests for the MMLA Data Explorer.

Re-reads the original project files independently of build_site_data.py and
compares them with what the website shows. Run after every build:
    python3 mmla_explorer/test_site_data.py
"""
from __future__ import annotations

import csv
import glob
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "mmla_explorer" / "site"
DS = ROOT / "data_sources_2026"
random.seed(2026)

failures: list[str] = []
passed = 0


def check(cond: bool, msg: str):
    global passed
    if cond:
        passed += 1
    else:
        failures.append(msg)


def load_js(name: str, var: str):
    txt = (SITE / "data" / name).read_text(encoding="utf-8")
    prefix = f"window.{var}="
    assert txt.startswith(prefix)
    return json.loads(txt[len(prefix):].rstrip().rstrip(";"))


C = load_js("core.js", "CORE")
F = load_js("frames.js", "FRAMES")
STUDENTS = C["students"]

# 1. Participants: only the 15 pseudonyms, no template student.
check(len(STUDENTS) == 15 and "Sample_Student" not in STUDENTS, "student list")

# 2. Worksheet values: random sample compared with the source JSON.
rows = list(csv.DictReader(open(SITE / "data" / "worksheet_responses.csv", encoding="utf-8")))
for r in random.sample(rows, 60):
    src = json.load(open(ROOT / r["source_file"], encoding="utf-8"))
    node = src.get("extraction", src)
    ok = True
    for part in re.findall(r"[^.\[\]]+|\[[^\]]+\]", r["field_path"]):
        if part.startswith("["):
            key = part[1:-1]
            lst = node
            match = [x for x in lst if isinstance(x, dict) and str(x.get("trial_id")) == key]
            node = match[0] if match else lst[int(key) - 1]
        else:
            node = node[part]
    if isinstance(node, list):
        node = ", ".join("null" if x is None else str(x) for x in node) if node else "[]"
    expect = "" if node is None else str(node)
    check(expect == r["extracted_value"], f"worksheet value {r['student']} {r['worksheet']} {r['field_path']}: {expect!r} != {r['extracted_value']!r}")

# 3. Item checks shown on the site match the source validation block.
for s in random.sample(STUDENTS, 8):
    for code, rec in C["ws"][s].items():
        o = rec["ocr"]
        if not o:
            continue
        src = json.load(open(ROOT / o["source"], encoding="utf-8"))
        ic = (src.get("validation") or {}).get("item_checks") or {}
        for c in o["checks"]:
            if c["check"].startswith("item_checks."):
                k = c["check"].split(".", 1)[1]
                check(ic.get(k, {}).get("is_correct") == c["correct"], f"item check {s} {code} {k}")

# 4. Frames: counts per session equal manifest frame counts; random rows match manifest + coding.
by_sess = Counter((f["s"], f["ss"]) for f in F)
proc = {"codap_21apr": "codap_arbor_21april_audio", "codap_28apr": "codap_arbor_28april_audio", "colab_05may": "colab_python_audio"}
for (s, ss), n in by_sess.items():
    m = json.load(open(DS / proc[ss] / s / f"{s}_video_extraction_manifest.json"))
    check(len(m["frames"]) == n, f"frame count {s} {ss}")
for f in random.sample([x for x in F if x["b"]], 80):
    fa = json.load(open(DS / proc[f["ss"]] / f["s"] / f"{f['s']}_codap_frame_analyses.json"))
    lst = fa if isinstance(fa, list) else fa["frame_analyses"]
    hit = [a for a in lst if a.get("frame_id") == f["id"]]
    check(bool(hit) and hit[0]["primary_behavior"] == f["b"] and hit[0].get("screen_context") == f["sc"],
          f"frame coding {f['s']} {f['ss']} {f['id']}")
    m = json.load(open(DS / proc[f["ss"]] / f["s"] / f"{f['s']}_video_extraction_manifest.json"))
    mf = [x for x in m["frames"] if x.get("frame_id") == f["id"]]
    check(bool(mf) and round(mf[0]["source_timestamp_seconds"], 1) == f["t"] and mf[0]["extraction_trigger_reason"] == f["tr"],
          f"frame manifest {f['s']} {f['ss']} {f['id']}")

# 5. Every thumbnail referenced exists.
for f in F:
    if f.get("th"):
        check((SITE / "thumbs" / f["th"]).exists(), f"thumbnail {f['th']}")

# 6. Logs: per-student daily event counts recomputed from the raw CSV.
raw = list(csv.DictReader(open(DS / "All Documents" / "28 Nisan 2026 CODAP Arbor Food Log File (anonymized).csv", encoding="utf-8")))
direct = Counter((r["student_id"], r["created_at"][:10]) for r in raw if r["student_id"] in STUDENTS)
for s, days in C["logs"]["per_student"].items():
    for d, v in days.items():
        remap = sum(x["rows"] for x in C["logs"]["rows_remapped_to_pseudonym"] if x["student"] == s and x["date"] == d)
        check(v["events"] == direct[(s, d)] + remap, f"log events {s} {d}")
        emits = sum(1 for r in raw if r["action"] == "emit_tree_data" and r["created_at"][:10] == d and r["student_id"] == s)
        check(v["emit_count"] >= emits, f"log emits {s} {d}")
total_kept = sum(v["events"] for d in C["logs"]["per_student"].values() for v in d.values())
excluded = sum(C["logs"]["rows_excluded_unmatched_by_day"].values())
check(total_kept + excluded == len(raw), "log rows add up")
check(excluded == 7, f"expected 7 instructor rows removed, got {excluded}")

# 7. VOTAT shown equals the pipeline file.
for s in STUDENTS:
    for ss in ("codap_21apr", "codap_28apr"):
        v = C["sessions"][s][ss].get("votat")
        if v:
            src = json.load(open(ROOT / v["source"]))
            check(src["votat_rate"] == v["votat_rate"], f"votat {s} {ss}")

# 8. Notebooks: structure recomputed.
for s in STUDENTS:
    n = (C["notebooks"].get(s) or {}).get("file")
    if not n:
        continue
    nb = json.load(open(ROOT / n["source"], encoding="utf-8"))
    code = [c for c in nb["cells"] if c["cell_type"] == "code"]
    check(len(nb["cells"]) == n["cells"] and len(code) == n["code_cells"], f"notebook cells {s}")
    check([c.get("execution_count") for c in code] == n["execution_counts"], f"notebook exec counts {s}")

# 9. Duplicate videos really share a hash in MANIFEST.json.
man = {f["path"]: f["sha256"] for f in json.load(open(DS / "MANIFEST.json"))["files"]}
for s in STUDENTS:
    for ss, rec in C["sessions"][s].items():
        for other in rec.get("same_video_file_as") or []:
            a = rec["video_sha256"]
            b = C["sessions"][s][other]["video_sha256"]
            check(a == b and a in man.values(), f"duplicate claim {s} {ss}/{other}")

# 10. Privacy: no real name from the official map in any site file.
import importlib.util
import unicodedata
spec = importlib.util.spec_from_file_location("anon", ROOT / "scripts" / "anonymize_student_data.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
norm = lambda x: unicodedata.normalize("NFC", x).casefold()
names = [norm(k) for k in mod.PSEUDONYM_MAP]
surnames = {n.split()[-1] for n in names}
blob = ""
for p in list((SITE / "data").glob("*")) + [SITE / "index.html", SITE / "assets" / "app.js"]:
    blob += norm(p.read_text(encoding="utf-8"))
for n in names:
    check(re.search(r"(?<![\w])" + re.escape(n) + r"(?![\w])", blob) is None, "a full real name appears in the site")
for sn in surnames:
    check(re.search(r"(?<![\w])" + re.escape(sn) + r"(?![\w])", blob) is None, "a real surname appears in the site")

print(f"{passed} checks passed, {len(failures)} failed")
for f in failures[:40]:
    print("FAIL", f)
sys.exit(1 if failures else 0)
