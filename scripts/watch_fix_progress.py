#!/usr/bin/env python3
"""Canlı fix-job paneli — hangi öğrenci, hangi adım, kaç/13 bitti."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"
FIX_LOG = LOG_DIR / "fix_gate_failures_v3.log"
STATUS_FILE = LOG_DIR / "fix_gate_status.json"
DEFAULT_PLAN = LOG_DIR / "fix_gate_failures_plan_v3.json"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from batch_extract_strict_cohorts import COHORTS  # noqa: E402

COHORT_LABELS = {
    "21april": "21 Nisan",
    "28april": "28 Nisan",
    "05may": "5 Mayıs",
}

STEP_LABELS = {
    "dynamic_video_analytics.py": "1/3 Kare çıkarma",
    "prune_to_guard.py": "2/3 Guard temizliği",
    "post_hoc_refiner.py": "3/3 Pilot + gate",
    "extraction_quality_gate.py": "3/3 Kalite gate",
    "fix_gate_failures.py": "Koordinatör",
}


def load_plan(plan_path: Path) -> list[dict]:
    if not plan_path.is_file():
        return []
    return json.loads(plan_path.read_text(encoding="utf-8"))


def parse_fix_log_results() -> dict[tuple[str, str], dict]:
    out: dict[tuple[str, str], dict] = {}
    if not FIX_LOG.is_file():
        return out
    for line in FIX_LOG.read_text(encoding="utf-8", errors="replace").splitlines():
        if "Result:" not in line:
            continue
        try:
            payload = json.loads(line.split("Result:", 1)[1].strip())
            key = (payload.get("cohort", ""), payload.get("student_id", ""))
            out[key] = payload
        except json.JSONDecodeError:
            pass
    return out


def load_status_file() -> dict | None:
    if STATUS_FILE.is_file():
        try:
            return json.loads(STATUS_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return None


STEP_SCRIPTS = (
    "dynamic_video_analytics.py",
    "prune_to_guard.py",
    "post_hoc_refiner.py",
    "extraction_quality_gate.py",
)


def _parse_step_line(line: str, script: str) -> dict | None:
    if "caffeinate" in line and "python" not in line.split()[-1]:
        return None
    parts = line.strip().split(None, 1)
    if len(parts) < 2 or script not in parts[1]:
        return None
    tokens = parts[1].split()
    student_id = None
    cohort_key = None
    for i, t in enumerate(tokens):
        if t.endswith(script) and i + 1 < len(tokens):
            student_id = tokens[i + 1]
            break
    if "--audio-root" in tokens:
        ar = tokens[tokens.index("--audio-root") + 1]
        for ck, root, _ in COHORTS:
            if str(root) == ar or ar.endswith(root.name):
                cohort_key = ck
                break
    if not student_id:
        return None
    return {"student_id": student_id, "cohort": cohort_key, "step": script, "pid": parts[0]}


def active_student_process() -> dict | None:
    # Scan every pipeline step so the panel keeps tracking the student even
    # after frame extraction, during prune / gate / refine post-processing.
    for script in STEP_SCRIPTS:
        proc = subprocess.run(["pgrep", "-fl", script], capture_output=True, text=True)
        if proc.returncode != 0:
            continue
        for line in proc.stdout.splitlines():
            info = _parse_step_line(line, script)
            if info:
                return info
    return None


def tail_progress(cohort: str, student: str) -> dict[str, str]:
    log_path = LOG_DIR / f"batch_strict_{cohort}_{student}.log"
    if not log_path.is_file():
        return {}
    lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-60:]
    info: dict[str, str] = {}
    for line in reversed(lines):
        if "Combined-scan:" in line and "video_t" not in info:
            m = re.search(r"t=([\d.]+)s speech=(\d+) motion=(\d+) total=(\d+)", line)
            if m:
                info["video_t"] = m.group(1)
                info["total"] = m.group(4)
        if ("Fallback:" in line or "Motion:" in line or "Gap-fill:" in line or "Anchor:" in line) and "last_ts" not in info:
            m = re.search(r"@ ([\d.]+)s", line)
            if m:
                info["last_ts"] = m.group(1)
        if "Gap-fill:" in line and "gap_fills" not in info:
            info["gap_fills"] = str(int(info.get("gap_fills", "0")) + 1)
    gap_count = sum(1 for ln in lines if "Gap-fill:" in ln)
    if gap_count:
        info["gap_fills"] = str(gap_count)
    return info


def manifest_status(cohort: str, student: str) -> tuple[str, str]:
    """Fast status from manifest (no full gate CV pass)."""
    audio = next(r for c, r, _ in COHORTS if c == cohort)
    mp = audio / student / f"{student}_video_extraction_manifest.json"
    if not mp.is_file():
        return "bekliyor", ""
    try:
        m = json.loads(mp.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return "bekliyor", ""
    frames = m.get("frames") or []
    n = len(frames)
    gap_fill = sum(
        1 for f in frames
        if f.get("extraction_trigger_reason") in ("silent_screen_gap_fill", "codap_static_gap_fill")
    )
    ts = sorted(f["source_timestamp_seconds"] for f in frames)
    codap = [t for t in ts if 900 <= t <= 3600]
    max_gap = 0.0
    if len(codap) > 1:
        max_gap = max(codap[i + 1] - codap[i] for i in range(len(codap) - 1))
    detail = f"{n} kare"
    if gap_fill:
        detail += f", gap-fill={gap_fill}"
    if max_gap <= 140:
        return "TAMAM ✓", detail
    if gap_fill > 0 and max_gap <= 160:
        return "TAMAM ✓", detail  # borderline after fix
    if max_gap > 140:
        return "FAIL ✗", f"max boşluk {max_gap:.0f}s"
    return "bekliyor", detail


def render(plan_path: Path, interval: float, use_gate: bool) -> None:
    plan = load_plan(plan_path)
    total = len(plan)
    results = parse_fix_log_results()
    status = load_status_file()
    active = active_student_process()
    now = datetime.now().strftime("%H:%M:%S")

    lines: list[str] = []
    lines.append("")
    lines.append("╔" + "═" * 68 + "╗")
    lines.append(f"║  FIX JOB — Gate Fail Düzeltme          {now}  (her {interval:.0f}s)     ║")
    lines.append("╚" + "═" * 68 + "╝")

    # Which student is the job currently on? Students before it (in plan order)
    # have been reprocessed; students after it are still queued.
    active_idx = None
    if active:
        for i, row in enumerate(plan):
            if row["student"] == active.get("student_id") and row["cohort"] == active.get("cohort"):
                active_idx = i
                break

    # Set of students confirmed reprocessed via fix-log / status file.
    processed: set[tuple[str, str]] = set(results.keys())
    if status:
        for done in status.get("completed", []):
            processed.add((done.get("cohort"), done.get("student")))

    # Progress summary
    rows: list[tuple[str, str, str, str]] = []

    for i, row in enumerate(plan, 1):
        ck, sid = row["cohort"], row["student"]
        key = (ck, sid)
        state = "bekliyor"
        detail = ""

        if active and active.get("student_id") == sid and active.get("cohort") == ck:
            state = "çalışıyor"
            detail = STEP_LABELS.get(active.get("step", ""), active.get("step", ""))
        elif key in results:
            r = results[key]
            if r.get("gate_passed_after"):
                state = "TAMAM ✓"
                detail = f"{r.get('frames', '?')} kare"
            else:
                state = "FAIL ✗"
                detail = f"{r.get('frames', '?')} kare — hâlâ gate fail"
        else:
            # Reprocessed only if in confirmed set, or plan-position is before active.
            reprocessed = key in processed or (active_idx is not None and (i - 1) < active_idx)
            if reprocessed:
                mstate, mdetail = manifest_status(ck, sid)
                state, detail = mstate, mdetail
            else:
                state, detail = "bekliyor", "v3 sırada"

        marker = "  ← ŞİMDİ" if state == "çalışıyor" else ""
        rows.append((f"[{i:2}/{total}]", f"{COHORT_LABELS.get(ck, ck)}/{sid}", state, detail + marker))

    done_pass = sum(1 for _, _, s, _ in rows if s.startswith("TAMAM"))
    done_fail = sum(1 for _, _, s, _ in rows if s.startswith("FAIL"))
    done = done_pass + done_fail
    pct = int(100 * done / total) if total else 0
    bar_filled = pct // 5
    bar = "█" * bar_filled + "░" * (20 - bar_filled)

    lines.append("")
    lines.append(f"  İlerleme: [{bar}] {done}/{total} bitti  ({pct}%)")
    lines.append(f"  ✓ geçti: {done_pass}   ✗ hâlâ fail: {done_fail}   ○ kalan: {total - done}")
    lines.append("")

    # Active block
    if active:
        ck = active.get("cohort", "?")
        sid = active.get("student_id", "?")
        step = STEP_LABELS.get(active.get("step", ""), "?")
        lines.append("  ▶ ŞU AN")
        lines.append(f"    Öğrenci : {COHORT_LABELS.get(ck, ck)} / {sid}")
        lines.append(f"    Adım    : {step}")
        prog = tail_progress(ck, sid)
        if prog.get("video_t"):
            lines.append(f"    Video   : t={prog['video_t']}s   kaydedilen kare: {prog.get('total', '?')}")
        if prog.get("gap_fills"):
            lines.append(f"    Gap-fill: {prog['gap_fills']} kare (statik ekran doldurma)")
        if prog.get("last_ts"):
            lines.append(f"    Son kare: @ {prog['last_ts']}s")
        lines.append(f"    Log     : logs/pipeline_runs/batch_strict_{ck}_{sid}.log")
    elif done < total:
        lines.append("  ▶ ŞU AN: öğrenci geçişi / post-process bekleniyor...")
    else:
        lines.append("  ▶ Fix job tamamlandı.")

    lines.append("")
    lines.append("  SIRA LİSTESİ")
    lines.append("  " + "─" * 64)
    for idx, who, state, detail in rows:
        icon = {"bekliyor": "○", "çalışıyor": "▶", "TAMAM ✓": "✓", "FAIL ✗": "⚠"}.get(state.split()[0] if state else "", "?")
        if state.startswith("TAMAM"):
            icon = "✓"
        elif state.startswith("FAIL"):
            icon = "⚠"
        elif state == "çalışıyor":
            icon = "▶"
        else:
            icon = "○"
        lines.append(f"  {idx} {icon} {who:<28} {state:<10} {detail}")

    lines.append("")
    lines.append("  Not: fix_gate_failures.log öğrenci bitene kadar sessiz kalır.")
    lines.append("       Bu panel video ilerlemesini canlı gösterir. Çıkmak: Ctrl+C")
    lines.append("")

    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def main() -> int:
    p = argparse.ArgumentParser(description="Fix job canlı panel")
    p.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    p.add_argument("--interval", type=float, default=2.0)
    p.add_argument("--once", action="store_true")
    args = p.parse_args()
    try:
        while True:
            render(args.plan, args.interval, use_gate=False)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nPanel kapatıldı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
