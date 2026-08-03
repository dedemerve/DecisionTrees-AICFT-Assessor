#!/usr/bin/env python3
"""Re-extract every student that fails the extraction quality gate (v2 gap-fill params)."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
LOG_DIR = REPO_ROOT / "logs" / "pipeline_runs"
PYTHON = REPO_ROOT / ".venv-hybrid" / "bin" / "python"
STATUS_FILE = LOG_DIR / "fix_gate_status.json"

sys.path.insert(0, str(SCRIPTS))
from batch_extract_strict_cohorts import COHORTS, discover_students, process_student, quality_gate_passes  # noqa: E402

LOGGER = logging.getLogger("fix_gate_failures")


def audit_failures(skip_audit: Path | None = None) -> list[tuple[str, str, Path, Path, list[str]]]:
    if skip_audit and skip_audit.is_file():
        rows = json.loads(skip_audit.read_text(encoding="utf-8"))
        cohort_map = {c[0]: (c[1], c[2]) for c in COHORTS}
        out: list[tuple[str, str, Path, Path, list[str]]] = []
        for row in rows:
            ck = row["cohort"]
            sid = row["student"]
            audio_root, video_root = cohort_map[ck]
            out.append((ck, sid, audio_root, video_root, row.get("blockers", [])))
        return out

    failing: list[tuple[str, str, Path, Path, list[str]]] = []
    for cohort_key, audio_root, video_root in COHORTS:
        for sid in discover_students(audio_root):
            if cohort_key == "21april" and sid == "Amy":
                continue
            student_dir = audio_root / sid
            if quality_gate_passes(student_dir, sid, audio_root):
                continue
            proc = subprocess.run(
                [str(PYTHON), str(SCRIPTS / "extraction_quality_gate.py"), sid, "--audio-root", str(audio_root)],
                capture_output=True,
                text=True,
            )
            blockers: list[str] = []
            try:
                blockers = json.loads(proc.stdout).get("blockers", [])
            except json.JSONDecodeError:
                blockers = [proc.stderr or proc.stdout or "unknown"]
            failing.append((cohort_key, sid, audio_root, video_root, blockers))
    return failing


def main() -> int:
    p = argparse.ArgumentParser(description="Re-extract gate-failing students")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--plan", type=Path, help="JSON plan from a prior audit (skip re-scan)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    print("fix_gate_failures: starting", flush=True)
    failing = audit_failures(args.plan)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    plan_path = LOG_DIR / f"fix_gate_failures_plan_{stamp}.json"
    plan_path.write_text(
        json.dumps([{"cohort": c, "student": s, "blockers": b} for c, s, _, _, b in failing], indent=2) + "\n",
        encoding="utf-8",
    )
    LOGGER.info("Gate failures: %d — plan %s", len(failing), plan_path.relative_to(REPO_ROOT))

    if not failing:
        print(json.dumps({"status": "all_pass", "plan": str(plan_path.relative_to(REPO_ROOT))}, indent=2))
        return 0

    for cohort_key, sid, blockers in [(c, s, b) for c, s, _, _, b in failing]:
        LOGGER.info("  %s/%s: %s", cohort_key, sid, "; ".join(blockers))

    if args.dry_run:
        return 0

    results: list[dict] = []
    total = len(failing)
    for idx, (cohort_key, sid, audio_root, video_root, blockers) in enumerate(failing, 1):
        LOGGER.info("=== FIX [%d/%d] %s/%s ===", idx, total, cohort_key, sid)
        status_payload = {
            "started_at": datetime.now().isoformat(),
            "current": f"{cohort_key}/{sid}",
            "index": idx,
            "total": total,
            "completed": [r for r in results],
        }
        STATUS_FILE.write_text(json.dumps(status_payload, indent=2) + "\n", encoding="utf-8")

        result = process_student(cohort_key, sid, audio_root, video_root, dry_run=False)
        result["cohort"] = cohort_key
        result["prior_blockers"] = blockers
        passed = quality_gate_passes(audio_root / sid, sid, audio_root)
        result["gate_passed_after"] = passed
        results.append(result)

        verdict = "PASS ✓" if passed else "FAIL ✗"
        LOGGER.info(
            "BİTTİ [%d/%d] %s/%s → %s | %s kare | gate_after=%s",
            idx, total, cohort_key, sid, verdict, result.get("frames", "?"), passed,
        )
        LOGGER.info("Result: %s", json.dumps(result, ensure_ascii=False))

        status_payload["completed"].append({
            "cohort": cohort_key,
            "student": sid,
            "frames": result.get("frames"),
            "gate_passed": passed,
        })
        status_payload["current"] = None
        STATUS_FILE.write_text(json.dumps(status_payload, indent=2) + "\n", encoding="utf-8")

    report_path = LOG_DIR / f"fix_gate_failures_report_{stamp}.json"
    report_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    still_failing = [r for r in results if not r.get("gate_passed_after")]
    print(
        json.dumps(
            {
                "report": str(report_path.relative_to(REPO_ROOT)),
                "fixed": len(results) - len(still_failing),
                "still_failing": still_failing,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 1 if still_failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
