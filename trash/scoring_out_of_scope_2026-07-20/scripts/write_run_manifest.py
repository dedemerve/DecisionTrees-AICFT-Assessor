#!/usr/bin/env python3
"""Write a scoring run manifest for provenance tracking (RF10 remediation).

Call this at the end of any automated scoring or validation script.

Usage:
    python scripts/write_run_manifest.py \\
        --run-id 2026-07-20-validation \\
        --model claude-haiku-4-5-20251001 \\
        --n-frames 219 \\
        --purpose validation \\
        --output calibration/validation_raw_scores.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_DIR = REPO_ROOT / "calibration" / "runs"
PROMPT_SOURCE = REPO_ROOT / "mmla_scorer.py"


def get_git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=REPO_ROOT, text=True
        ).strip()
    except Exception:
        return "unknown"


def sha256_of_prompt(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
        import re
        # Extract only the _SYSTEM_CODAP string block
        m = re.search(r'_SYSTEM_CODAP\s*=\s*"""(.*?)"""', text, re.DOTALL)
        content = m.group(1) if m else text
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    except Exception:
        return "unknown"


def main() -> int:
    ap = argparse.ArgumentParser(description="Write scoring run manifest")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--n-frames", type=int, required=True)
    ap.add_argument("--purpose", choices=["validation", "2026_scoring", "fewshot_selection", "irr_check"], required=True)
    ap.add_argument("--output", required=True, help="Output file (repo-relative)")
    ap.add_argument("--script", default="unknown")
    ap.add_argument("--notes", default="")
    args = ap.parse_args()

    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    manifest = {
        "run_id": args.run_id,
        "model_id": args.model,
        "prompt_path": "mmla_scorer.py (_SYSTEM_CODAP)",
        "prompt_sha256": sha256_of_prompt(PROMPT_SOURCE),
        "temperature": 1.0,
        "n_frames": args.n_frames,
        "git_commit": get_git_commit(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "script": args.script,
        "purpose": args.purpose,
        "output_file": args.output,
        "notes": args.notes,
    }

    out = RUNS_DIR / f"{args.run_id}.json"
    out.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Run manifest written → {out.relative_to(REPO_ROOT)}")
    print(f"  model: {manifest['model_id']}")
    print(f"  prompt_sha256: {manifest['prompt_sha256']}")
    print(f"  git_commit: {manifest['git_commit']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
