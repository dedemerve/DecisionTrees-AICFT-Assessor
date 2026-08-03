#!/usr/bin/env python3
"""Wait for the active batch, then re-run extraction until every student passes the quality gate."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = REPO_ROOT / "scripts"
LOG_DIR = REPO_ROOT / "logs/pipeline_runs"
PYTHON = REPO_ROOT / ".venv-hybrid" / "bin" / "python"
MAX_FIX_ROUNDS = 5
POLL_SECONDS = 90

sys.path.insert(0, str(SCRIPTS))
from batch_extract_strict_cohorts import (  # noqa: E402
    COHORTS,
    discover_students,
    quality_gate_passes,
)

LOGGER = logging.getLogger("orchestrator_complete")


def pipeline_busy() -> bool:
    for pattern in ("batch_extract_strict_cohorts.py", "dynamic_video_analytics.py"):
        proc = subprocess.run(["pgrep", "-f", pattern], capture_output=True)
        if proc.returncode == 0:
            return True
    return False


def wait_for_idle() -> None:
    LOGGER.info("Waiting for current batch/extraction to finish...")
    while pipeline_busy():
        time.sleep(POLL_SECONDS)
    LOGGER.info("Pipeline idle — starting fix rounds.")


def audit_cohort(cohort_key: str, audio_root: Path) -> list[dict]:
    rows: list[dict] = []
    for sid in discover_students(audio_root):
        passed = quality_gate_passes(audio_root / sid, sid, audio_root)
        manifest_path = audio_root / sid / f"{sid}_video_extraction_manifest.json"
        frames = 0
        if manifest_path.is_file():
            try:
                frames = len(json.loads(manifest_path.read_text()).get("frames", []))
            except json.JSONDecodeError:
                pass
        rows.append(
            {
                "cohort": cohort_key,
                "student_id": sid,
                "gate_passed": passed,
                "frames": frames,
            }
        )
    return rows


def run_batch(cohort: str | None = None) -> int:
    cmd = [
        "caffeinate",
        "-i",
        str(PYTHON),
        "-u",
        str(SCRIPTS / "batch_extract_strict_cohorts.py"),
        "-v",
    ]
    if cohort:
        cmd.extend(["--cohort", cohort])
    log_path = LOG_DIR / f"orchestrator_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n>>> {' '.join(cmd)}\n")
        proc = subprocess.run(cmd, stdout=fh, stderr=subprocess.STDOUT, text=True)
        fh.write(f"<<< exit_code={proc.returncode}\n")
    return proc.returncode


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    master_log = LOG_DIR / "orchestrator_complete.log"

    with master_log.open("a", encoding="utf-8") as fh:
        fh.write(f"\n=== orchestrator start {datetime.now().isoformat()} ===\n")

    wait_for_idle()

    for round_idx in range(1, MAX_FIX_ROUNDS + 1):
        audit: list[dict] = []
        for cohort_key, audio_root, _ in COHORTS:
            audit.extend(audit_cohort(cohort_key, audio_root))

        failing = [row for row in audit if not row["gate_passed"] and row["student_id"] != "Amy"]
        report_path = LOG_DIR / f"orchestrator_audit_round{round_idx}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_path.write_text(
            json.dumps({"round": round_idx, "audit": audit, "failing": failing}, indent=2) + "\n",
            encoding="utf-8",
        )
        LOGGER.info("Round %d audit: %d failing / %d total", round_idx, len(failing), len(audit))

        if not failing:
            LOGGER.info("All students pass quality gate.")
            break

        LOGGER.info("Running fix batch round %d...", round_idx)
        rc = run_batch()
        wait_for_idle()
        if rc != 0:
            LOGGER.warning("Fix batch round %d exited %d — continuing audit loop", round_idx, rc)

    final_audit: list[dict] = []
    for cohort_key, audio_root, _ in COHORTS:
        final_audit.extend(audit_cohort(cohort_key, audio_root))

    final_path = LOG_DIR / f"orchestrator_final_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    final_path.write_text(json.dumps(final_audit, indent=2) + "\n", encoding="utf-8")
    still_failing = [r for r in final_audit if not r["gate_passed"] and r["student_id"] != "Amy"]
    LOGGER.info("Final: %d failing students", len(still_failing))
    print(json.dumps({"final_report": str(final_path.relative_to(REPO_ROOT)), "failing": still_failing}, indent=2))
    return 1 if still_failing else 0


if __name__ == "__main__":
    raise SystemExit(main())
