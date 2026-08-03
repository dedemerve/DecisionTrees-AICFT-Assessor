#!/usr/bin/env python3
"""Live dashboard: which cohort/student/script is running in the extraction pipeline."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"
BATCH_LOG = LOG_DIR / "batch_strict_fast.log"
ORCH_LOG = LOG_DIR / "orchestrator_complete.log"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
from batch_extract_strict_cohorts import COHORTS, discover_students  # noqa: E402

COHORT_LABELS = {
    "21april": "21 Nisan CODAP",
    "28april": "28 Nisan CODAP",
    "05may": "5 Mayıs Colab",
}

SCRIPT_LABELS = {
    "dynamic_video_analytics.py": "Frame çıkarma",
    "prune_to_guard.py": "Guard temizliği",
    "post_hoc_refiner.py": "Pilot export",
    "extraction_quality_gate.py": "Kalite gate",
    "batch_extract_strict_cohorts.py": "Batch koordinatör",
    "orchestrator_complete_extraction.py": "Orchestrator (fix turu)",
    "reextract_silent_students.py": "Sessiz kayıt yeniden çıkarma",
}

STATUS_ICON = {
    "pending": "○",
    "running": "▶",
    "ok": "✓",
    "gate_fail": "⚠",
    "skipped": "—",
    "failed": "✗",
}


@dataclass
class ActiveProcess:
    pid: int
    script: str
    student_id: str | None
    cohort_key: str | None
    audio_root: str | None
    extra: str


@dataclass
class StudentResult:
    cohort: str
    student_id: str
    status: str
    frames: int | None = None
    gate_failed: bool | None = None
    reason: str | None = None


def pgrep_lines(pattern: str) -> list[str]:
    proc = subprocess.run(["pgrep", "-fl", pattern], capture_output=True, text=True)
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def parse_process_line(line: str) -> ActiveProcess | None:
    m = re.match(r"^(\d+)\s+(.+)$", line)
    if not m:
        return None
    pid = int(m.group(1))
    cmd = m.group(2)
    if "caffeinate" in cmd and "python" not in cmd.split()[-1]:
        return None

    script = "unknown"
    for key in SCRIPT_LABELS:
        if key in cmd:
            script = key
            break

    student_id: str | None = None
    audio_root: str | None = None
    cohort_key: str | None = None

    if script == "dynamic_video_analytics.py":
        parts = cmd.split()
        for i, part in enumerate(parts):
            if part.endswith("dynamic_video_analytics.py") and i + 1 < len(parts):
                student_id = parts[i + 1]
                break
        if "--audio-root" in parts:
            i = parts.index("--audio-root")
            audio_root = parts[i + 1]
    elif script in ("prune_to_guard.py", "post_hoc_refiner.py", "extraction_quality_gate.py"):
        parts = cmd.split()
        for i, part in enumerate(parts):
            if part.endswith(script) and i + 1 < len(parts):
                student_id = parts[i + 1]
                break
        if "--audio-root" in parts:
            i = parts.index("--audio-root")
            audio_root = parts[i + 1]

    if audio_root:
        for key, root, _ in COHORTS:
            if str(root) == audio_root or audio_root.endswith(root.name):
                cohort_key = key
                break

    return ActiveProcess(
        pid=pid,
        script=script,
        student_id=student_id,
        cohort_key=cohort_key,
        audio_root=audio_root,
        extra=cmd[:120],
    )


def collect_active_processes() -> list[ActiveProcess]:
    seen_pids: set[int] = set()
    out: list[ActiveProcess] = []
    patterns = [
        "dynamic_video_analytics.py",
        "batch_extract_strict_cohorts.py",
        "orchestrator_complete_extraction.py",
        "prune_to_guard.py",
        "post_hoc_refiner.py",
        "extraction_quality_gate.py",
        "reextract_silent_students.py",
    ]
    for pattern in patterns:
        for line in pgrep_lines(pattern):
            proc = parse_process_line(line)
            if proc and proc.pid not in seen_pids:
                if proc.script == "unknown":
                    continue
                seen_pids.add(proc.pid)
                out.append(proc)
    priority = {
        "dynamic_video_analytics.py": 0,
        "prune_to_guard.py": 1,
        "post_hoc_refiner.py": 2,
        "extraction_quality_gate.py": 3,
        "batch_extract_strict_cohorts.py": 4,
        "orchestrator_complete_extraction.py": 5,
        "reextract_silent_students.py": 6,
    }
    out.sort(key=lambda p: priority.get(p.script, 99))
    return out


def parse_batch_results() -> dict[tuple[str, str], StudentResult]:
    results: dict[tuple[str, str], StudentResult] = {}
    if not BATCH_LOG.is_file():
        return results
    text = BATCH_LOG.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        if "Result:" not in line:
            continue
        try:
            payload = json.loads(line.split("Result:", 1)[1].strip())
        except json.JSONDecodeError:
            continue
        cohort = payload.get("cohort", "")
        sid = payload.get("student_id", "")
        if not cohort or not sid:
            continue
        gate_failed = bool((payload.get("post") or {}).get("gate_failed"))
        status = payload.get("status", "unknown")
        if status == "skipped":
            disp = "skipped"
        elif gate_failed:
            disp = "gate_fail"
        elif status == "failed":
            disp = "failed"
        elif status == "ok":
            disp = "ok"
        else:
            disp = status
        reason = payload.get("reason")
        if reason == "amy_gate_passed":
            reason = "Amy referans"
        results[(cohort, sid)] = StudentResult(
            cohort=cohort,
            student_id=sid,
            status=disp,
            frames=payload.get("frames"),
            gate_failed=gate_failed,
            reason=reason,
        )
    return results


def tail_student_log(cohort: str, student_id: str, n: int = 80) -> list[str]:
    path = LOG_DIR / f"batch_strict_{cohort}_{student_id}.log"
    if not path.is_file():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    return lines[-n:]


def parse_log_progress(lines: list[str]) -> dict[str, str]:
    info: dict[str, str] = {}
    for line in reversed(lines):
        if "Combined-scan:" in line and "video_t" not in info:
            m = re.search(r"t=([\d.]+)s speech=(\d+) motion=(\d+) total=(\d+)", line)
            if m:
                info["video_t"] = m.group(1)
                info["speech"] = m.group(2)
                info["motion"] = m.group(3)
                info["frames_saved"] = m.group(4)
        if ("Fallback:" in line or "Motion:" in line or "Anchor:" in line or "Gap-fill:" in line) and "last_frame" not in info:
            m = re.search(r"(frame_\d+) @ ([\d.]+)s", line)
            if m:
                info["last_frame"] = m.group(1)
                info["last_ts"] = m.group(2)
        if "duration" in line.lower() and "video_duration" not in info:
            m = re.search(r"duration[=:\s]+([\d.]+)s", line, re.I)
            if m:
                info["video_duration"] = m.group(1)
        if info.keys() >= {"video_t", "last_frame", "frames_saved"}:
            break

    manifest_frames = 0
    for line in reversed(lines):
        m = re.search(r"Wrote manifest.*\((\d+) frames\)", line)
        if m:
            info["manifest_frames"] = m.group(1)
            break
        if "total=" in line and "frames_saved" not in info:
            m = re.search(r"total=(\d+)", line)
            if m:
                manifest_frames = max(manifest_frames, int(m.group(1)))

    frames_dir_count = None
    for line in reversed(lines):
        if "Saved keyframe" in line or "frames extracted" in line.lower():
            break
    return info


def orchestrator_status() -> str | None:
    if not ORCH_LOG.is_file():
        return None
    lines = ORCH_LOG.read_text(encoding="utf-8", errors="replace").splitlines()
    for line in reversed(lines[-30:]):
        if "Waiting for current batch" in line:
            return "Batch bitmesini bekliyor"
        if "Pipeline idle" in line:
            return "Fix turu başlıyor"
        if "Round" in line and "audit" in line:
            return line.split(" ", 3)[-1] if " " in line else line
        if "Running fix batch" in line:
            return "Fix batch çalışıyor"
        if "All students pass" in line:
            return "Tüm öğrenciler gate geçti"
    return None


def student_display_status(
    cohort_key: str,
    student_id: str,
    batch_results: dict[tuple[str, str], StudentResult],
    active: list[ActiveProcess],
) -> tuple[str, str]:
    key = (cohort_key, student_id)
    for proc in active:
        if proc.student_id == student_id and proc.cohort_key == cohort_key:
            label = SCRIPT_LABELS.get(proc.script, proc.script)
            return "running", label
    if key in batch_results:
        r = batch_results[key]
        if r.reason in ("Amy referans", "amy_gate_passed"):
            return "skipped", "Amy referans"
        detail = {
            "ok": "gate OK",
            "gate_fail": "gate FAIL — orchestrator düzeltecek",
            "skipped": r.reason or "atlandı",
            "failed": "hata",
        }.get(r.status, r.status)
        return r.status, detail
    return "pending", ""


def render(refresh_s: float) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    active = collect_active_processes()
    batch_results = parse_batch_results()
    orch = orchestrator_status()

    # Primary worker = frame extraction or post step with student
    primary = next((p for p in active if p.student_id), None)
    batch_running = any(p.script == "batch_extract_strict_cohorts.py" for p in active)
    orch_running = any(p.script == "orchestrator_complete_extraction.py" for p in active)

    lines: list[str] = []
    lines.append("")
    lines.append("═" * 72)
    lines.append(f"  MMLA Extraction İlerleme   │  {now}   │  yenileme: {refresh_s:.0f}s")
    lines.append("═" * 72)

    if not active and not batch_results:
        lines.append("")
        lines.append("  Hiç aktif process yok. Batch başlatmak için:")
        lines.append("  caffeinate -i .venv-hybrid/bin/python -u scripts/batch_extract_strict_cohorts.py -v")
        lines.append("")
        print("\n".join(lines))
        return

    lines.append("")
    lines.append("  AKTİF PROCESS")
    lines.append("  " + "─" * 68)
    if primary:
        cohort_label = COHORT_LABELS.get(primary.cohort_key or "", primary.cohort_key or "?")
        script_label = SCRIPT_LABELS.get(primary.script, primary.script)
        lines.append(f"  ▶ Öğrenci   : {primary.student_id or '—'}  ({cohort_label})")
        lines.append(f"    Script    : {script_label}")
        lines.append(f"    PID       : {primary.pid}")
        if primary.audio_root:
            rel = Path(primary.audio_root).relative_to(REPO_ROOT) if primary.audio_root.startswith(str(REPO_ROOT)) else primary.audio_root
            lines.append(f"    Klasör    : {rel}")
        log_lines = tail_student_log(primary.cohort_key or "", primary.student_id or "")
        prog = parse_log_progress(log_lines)
        if prog.get("video_t"):
            dur = prog.get("video_duration", "?")
            pct = ""
            try:
                t = float(prog["video_t"])
                d = float(dur) if dur != "?" else 0
                if d > 0:
                    pct = f"  ({100 * t / d:.1f}%)"
            except ValueError:
                pass
            lines.append(f"    Video     : t={prog['video_t']}s / {dur}s{pct}")
        if prog.get("frames_saved"):
            lines.append(f"    Kareler   : {prog['frames_saved']} kaydedildi (log)")
        if prog.get("last_frame"):
            lines.append(f"    Son kare  : {prog['last_frame']} @ {prog.get('last_ts', '?')}s")
        log_path = LOG_DIR / f"batch_strict_{primary.cohort_key}_{primary.student_id}.log"
        if log_path.is_file():
            lines.append(f"    Log       : {log_path.relative_to(REPO_ROOT)}")
    elif batch_running:
        lines.append("  ▶ Batch koordinatör çalışıyor (öğrenci geçişi / bekleme)")
    elif orch_running:
        lines.append(f"  ▶ Orchestrator: {orch or 'çalışıyor'}")
    else:
        lines.append("  (şu an öğrenci bazlı işlem yok)")

    for proc in active:
        if proc is primary:
            continue
        label = SCRIPT_LABELS.get(proc.script, proc.script)
        who = f" — {proc.student_id}" if proc.student_id else ""
        lines.append(f"  · {label}{who}  [PID {proc.pid}]")

    if orch and not orch_running:
        lines.append(f"  · Orchestrator durumu: {orch}")

    lines.append("")
    lines.append("  KOORT TABLOSU")
    lines.append("  " + "─" * 68)

    total_done = 0
    total_all = 0
    for cohort_key, audio_root, _ in COHORTS:
        students = discover_students(audio_root)
        total_all += len(students)
        done = 0
        lines.append("")
        lines.append(f"  {COHORT_LABELS.get(cohort_key, cohort_key)}  ({cohort_key})")
        for sid in students:
            st, detail = student_display_status(cohort_key, sid, batch_results, active)
            icon = STATUS_ICON.get(st, "?")
            r = batch_results.get((cohort_key, sid))
            frame_note = ""
            if r and r.frames is not None and st != "running":
                frame_note = f"  {r.frames} kare"
            elif st == "running":
                ll = tail_student_log(cohort_key, sid, 40)
                pg = parse_log_progress(ll)
                if pg.get("frames_saved"):
                    frame_note = f"  ~{pg['frames_saved']} kare"
                elif pg.get("last_frame"):
                    frame_note = f"  {pg['last_frame']}"
            if st == "running":
                line_detail = detail
            elif detail and not detail.startswith("("):
                line_detail = detail.strip()
            else:
                line_detail = {
                    "pending": "bekliyor",
                    "ok": "gate OK",
                    "gate_fail": "gate FAIL — orchestrator düzeltecek",
                    "skipped": "atlandı",
                    "failed": "hata",
                }.get(st, st)
            if st in ("ok", "skipped", "gate_fail", "failed"):
                done += 1
            marker = " ← ŞİMDİ" if primary and primary.student_id == sid and primary.cohort_key == cohort_key else ""
            lines.append(f"    {icon} {sid:<12}{frame_note:<10}  {line_detail}{marker}")
        total_done += done
        lines.append(f"    └─ tamamlanan: {done}/{len(students)}")

    lines.append("")
    lines.append(f"  Genel: {total_done}/{total_all} öğrenci işlendi (batch log)")
    lines.append("")
    lines.append("  Çıkmak: Ctrl+C")
    lines.append("═" * 72)

    # Clear screen
    sys.stdout.write("\033[2J\033[H")
    sys.stdout.write("\n".join(lines) + "\n")
    sys.stdout.flush()


def main() -> int:
    p = argparse.ArgumentParser(description="Canlı extraction ilerleme paneli")
    p.add_argument("--interval", type=float, default=3.0, help="Yenileme aralığı (saniye)")
    p.add_argument("--once", action="store_true", help="Tek seferlik göster, çık")
    args = p.parse_args()

    try:
        while True:
            render(args.interval)
            if args.once:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nİzleme durduruldu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
