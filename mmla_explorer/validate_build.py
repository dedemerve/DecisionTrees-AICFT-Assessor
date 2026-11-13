#!/usr/bin/env python3
"""Validates the site data files produced by build_site_data.py.

Checks that required keys are present and counts are sane.
Run after every build:
    python3 mmla_explorer/validate_build.py

Exits 1 if any check fails so CI can catch broken builds.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "mmla_explorer" / "site"
DATA = SITE / "data"
BUILD_REPORT = ROOT / "mmla_explorer" / "build_report.json"

EXPECTED_STUDENTS = 15
EXPECTED_WORKSHEETS = ["WS1", "WS3", "WS4", "WS5", "WS6", "WS7",
                        "WS10", "WS12", "WS13", "WS14", "WS15"]

passed = 0
failed = 0


def check(condition: bool, label: str, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  ok  {label}")
    else:
        failed += 1
        msg = f"  FAIL  {label}"
        if detail:
            msg += f": {detail}"
        print(msg)


def load_js_global(path: Path, varname: str) -> object:
    """Extract the JSON value assigned to window.VARNAME in a JS data file."""
    text = path.read_text(encoding="utf-8")
    m = re.match(rf"window\.{varname}\s*=\s*(.+);\s*$", text, re.DOTALL)
    if not m:
        raise ValueError(f"Cannot parse {path.name}: expected window.{varname}=...")
    return json.loads(m.group(1))


def validate_core() -> None:
    print("core.js")
    path = DATA / "core.js"
    check(path.exists(), "file exists")
    if not path.exists():
        return
    core = load_js_global(path, "CORE")
    top = set(core.keys())
    for key in ("built_at", "students", "worksheets", "ws", "sessions", "logs", "notebooks"):
        check(key in top, f"has '{key}' key")
    students = core.get("students") or []
    check(len(students) == EXPECTED_STUDENTS,
          f"student count = {EXPECTED_STUDENTS}", f"got {len(students)}")
    ws = core.get("ws") or {}
    # ws is keyed by student index, each value is dict of WS codes
    ws_codes: set[str] = set()
    for student_ws in ws.values():
        ws_codes.update(student_ws.keys())
    for code in EXPECTED_WORKSHEETS:
        check(code in ws_codes, f"worksheet {code} present in ws data")
    check(bool(core.get("built_at")), "built_at is set")


def validate_frames() -> None:
    print("frames.js")
    path = DATA / "frames.js"
    check(path.exists(), "file exists")
    if not path.exists():
        return
    frames = load_js_global(path, "FRAMES")
    check(isinstance(frames, list), "is a list")
    check(len(frames) > 0, f"non-empty ({len(frames)} rows)")
    if frames:
        required = {"id", "s", "t"}
        sample = set(frames[0].keys())
        for k in required:
            check(k in sample, f"frame row has '{k}' key")


def validate_score_extra() -> None:
    print("score_extra.js")
    path = DATA / "score_extra.js"
    check(path.exists(), "file exists")
    if not path.exists():
        return
    se = load_js_global(path, "SCORE_EXTRA")
    check(isinstance(se, dict), "is a dict")
    for k in ("notes", "status"):
        check(k in se, f"has '{k}' key")


def validate_index_html() -> None:
    print("index.html")
    path = SITE / "index.html"
    check(path.exists(), "file exists")
    if not path.exists():
        return
    html = path.read_text(encoding="utf-8")
    check("?v=" in html, "version stamp present in asset URLs")
    check("window.CORE" not in html, "CORE data loaded via external script, not inline")
    check('<main id="app"' in html, "app mount point present")


def validate_build_report() -> None:
    print("build_report.json")
    check(BUILD_REPORT.exists(), "file exists")
    if not BUILD_REPORT.exists():
        return
    report = json.loads(BUILD_REPORT.read_text(encoding="utf-8"))
    checks = report.get("checks") or []
    failing = [c for c in checks if not c.get("passed", True)]
    check(len(failing) == 0, "all build checks passed",
          f"{len(failing)} failed: {[c['check'] for c in failing]}")
    counts = report.get("counts") or {}
    check(counts.get("students", 0) == EXPECTED_STUDENTS,
          f"build_report student count = {EXPECTED_STUDENTS}")
    check(counts.get("frames", 0) > 0,
          f"build_report frame count > 0 ({counts.get('frames', 0)})")


def main() -> None:
    print("=== validate_build.py ===\n")
    validate_core()
    print()
    validate_frames()
    print()
    validate_score_extra()
    print()
    validate_index_html()
    print()
    validate_build_report()
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
