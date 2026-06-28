"""
Lightweight milestone reporting — one human summary + one validation JSON per milestone.

Do not emit parallel audit shards (coverage matrices, duplicate-review JSON, etc.).
Summaries use validation status only.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = REPO_ROOT / "reports"


def validation_path(milestone: int) -> Path:
    return REPORTS_DIR / f"milestone{milestone}_validation.json"


def summary_path(milestone: int) -> Path:
    return REPORTS_DIR / f"milestone{milestone}_summary.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validation(milestone: int) -> dict[str, Any]:
    path = validation_path(milestone)
    if not path.exists():
        return {"milestone": milestone}
    return load_json(path)


def run_quiet_script(script: Path) -> int:
    """Run a repo script with --quiet; return exit code."""
    return subprocess.run(
        [sys.executable, str(script), "--quiet"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    ).returncode


def validation_status_label(status: str | None) -> str:
    """Display label for validator status in human summaries."""
    if status == "pass":
        return "PASS"
    if status == "fail":
        return "FAIL"
    return "UNKNOWN"


def ontology_version(doc: dict[str, Any], *, default: str = "1.0") -> str:
    """Canonical version string from a framework artifact (no freeze block)."""
    for key in ("framework_version", "mapping_schema_version", "policy_version"):
        value = doc.get(key)
        if value is not None:
            return str(value)
    return default

def write_validation(milestone: int, payload: dict[str, Any]) -> Path:
    """Write the single machine-readable validation artifact for a milestone."""
    out = dict(payload)
    out.setdefault("milestone", milestone)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = validation_path(milestone)
    path.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def write_summary(milestone: int, markdown: str) -> Path:
    """Write the single human-readable milestone summary (≈1 page)."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = summary_path(milestone)
    text = markdown if markdown.endswith("\n") else markdown + "\n"
    path.write_text(text, encoding="utf-8")
    return path


def patch_validation(milestone: int, patch: dict[str, Any]) -> Path:
    """Merge keys into an existing milestone validation file (or create minimal shell)."""
    existing = load_validation(milestone)
    existing.update(patch)
    return write_validation(milestone, existing)
