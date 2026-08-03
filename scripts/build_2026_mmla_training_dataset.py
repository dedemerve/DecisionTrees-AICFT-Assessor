#!/usr/bin/env python3
"""Build 2026 MMLA observation_steps.json from student Jupyter notebooks.

Source documents for 2026 are .ipynb files in:
    data_sources_2026/Final Odevi Dokumanlari/<Student>.ipynb

There is no Analysis.docx for 2026 — students submitted Jupyter notebooks instead.
This script reads markdown cells from each notebook as observation step narratives,
applies the same rule-based label classification as the 2025 pipeline, and writes
observation_steps.json to the v2 training_datasets layout.

If a notebook is not found, the script writes a zero-step stub so downstream
scripts (finalize_2026_gold_alignment.py) can still run without crashing.

Output layout (v2):
    training_datasets/2026/{student}/{session}/intermediate/{student}_observation_steps.json

Sessions:
    codap_21apr   -- CODAP Arbor session, 21 April
    codap_28apr   -- CODAP Arbor session, 28 April
    colab_05may   -- Colab Python session, 5 May

Usage:
    python scripts/build_2026_mmla_training_dataset.py --student Amy --session codap_21apr
    python scripts/build_2026_mmla_training_dataset.py --all
    python scripts/build_2026_mmla_training_dataset.py --student Amy --session codap_21apr --dry-run
"""

from __future__ import annotations

import argparse
import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = REPO_ROOT / "data_sources_2026" / "Final Ödevi Dokümanları"
FRAMES_2026 = REPO_ROOT / "data_sources_2026"
OUT_ROOT = REPO_ROOT / "training_datasets" / "2026"

SESSIONS: list[str] = ["codap_21apr", "codap_28apr", "colab_05may"]

LOGGER = logging.getLogger("build_2026_mmla")

# ─────────────────────────────────────────────────────────────
# Label rules (reused from 2025, Turkish observation language)
# ─────────────────────────────────────────────────────────────

STRATEGY_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"rastgele|deneme yanılma|sırayla arttır|sırayla azalt|arttırılıp azalt", re.I), "Trial-and-error"),
    (re.compile(r"karar veremedim|hangisinin daha iyi|bilmiyorum", re.I), "Random guessing"),
    (re.compile(r"tuz|energy|enerji|protein|yağ|sugar|şeker|salt|fat|carbohydrate|doymuş|alan\s+bilgi|besin", re.I), "Domain-knowledge driven"),
]

COGNITIVE_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"yanlış|hata|confusion|kavram\s*yanıl|recommendable or not.*yanlış", re.I), "MISCONCEPTION"),
    (re.compile(r"MCR|sensitivity|accuracy|confusion matrix|Classification Tree Records|metrik|performans", re.I), "EVALUATE"),
    (re.compile(r"threshold|movable value|Depth\s*\d|sürüklenir.*Depth|emit function", re.I), "TUNE"),
    (re.compile(r"grafik oluşturulur|x-eksen|y-eksen|Choosy|training ve test|dataset yüklen|keşf|incelen", re.I), "EXPLORE"),
]

LO_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"MCR.*sensitivity|neden.*seç|gerekçe|karşılaştır.*model|daha iyi.*model", re.I), "Deepen"),
    (re.compile(r"yeni bir karar ağacı|kendi|bağımsız|genellem", re.I), "Create"),
    (re.compile(r"yüklenir|sürüklenir|Emit function|Depth 1", re.I), "Acquire"),
]


def classify_observation(text: str) -> dict[str, str]:
    strategy = "Domain-knowledge driven"
    for pat, label in STRATEGY_RULES:
        if pat.search(text):
            strategy = label
            break

    cognitive = "EXPLORE"
    for pat, label in COGNITIVE_RULES:
        if pat.search(text):
            cognitive = label
            break

    lo = "None"
    for pat, label in LO_RULES:
        if pat.search(text):
            lo = label
            break

    return {
        "bilişsel_davranış_kategorisi": cognitive,
        "pedagojik_strateji": strategy,
        "unesco_ai_cft_level": lo,
    }


def stamp_sequence_patterns(steps: list[dict[str, Any]]) -> None:
    cats = [s["labels"]["bilişsel_davranış_kategorisi"] for s in steps]
    for i, step in enumerate(steps):
        window = cats[max(0, i - 2) : i + 1]
        pattern = None
        if window == ["EXPLORE", "TUNE", "EVALUATE"]:
            pattern = "EXPLORE->TUNE->EVALUATE"
        elif len(window) >= 2 and window[-2:] == ["TUNE", "EVALUATE"]:
            pattern = "TUNE->EVALUATE"
        elif len(window) >= 2 and window[-2:] == ["EXPLORE", "TUNE"]:
            pattern = "EXPLORE->TUNE"
        step["sequence_pattern"] = pattern


# ─────────────────────────────────────────────────────────────
# Jupyter notebook parsing
# ─────────────────────────────────────────────────────────────

def parse_notebook(path: Path) -> list[dict[str, Any]]:
    """Extract observation steps from markdown cells of a Jupyter notebook.

    Markdown cells that are purely headings (# H1, ## H2) without body text
    are skipped. Code cells are ignored. Each substantive markdown block becomes
    one observation step.
    """
    nb = json.loads(path.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = []

    for cell in nb.get("cells", []):
        cell_type = cell.get("cell_type", "")
        if cell_type not in {"markdown", "raw"}:
            continue

        source_lines = cell.get("source", [])
        if isinstance(source_lines, str):
            source_lines = source_lines.splitlines(keepends=True)
        raw_text = "".join(source_lines).strip()

        if not raw_text:
            continue

        # Skip pure heading cells
        if re.match(r"^#{1,6}\s+\S+$", raw_text):
            continue

        # Strip markdown heading prefixes from the first line for display
        text = re.sub(r"^#{1,6}\s+", "", raw_text, count=1).strip()
        if not text:
            continue

        labels = classify_observation(text)
        step_idx = len(steps)
        steps.append({
            "step_index": step_idx,
            "source_cell_type": cell_type,
            "uzman_nitel_gozlemi": text,
            "labels": labels,
            "sequence_pattern": None,
            "ai_cft_evidence_justification": (
                f"Uzman gozlemi '{labels['bilişsel_davranış_kategorisi']}' "
                f"/ '{labels['pedagojik_strateji']}' / LO={labels['unesco_ai_cft_level']} "
                f"olarak kural tabanli eslendi; kaynak: ipynb markdown cell."
            ),
        })

    stamp_sequence_patterns(steps)
    return steps


def _stub_steps() -> list[dict[str, Any]]:
    return []


# ─────────────────────────────────────────────────────────────
# Frame manifest loading
# ─────────────────────────────────────────────────────────────

SESSION_FRAME_DIRS = {
    "codap_21apr": "codap_arbor_21april_audio",
    "codap_28apr": "codap_arbor_28april_audio",
    "colab_05may": "colab_python_audio",
}


def load_frame_manifest(student: str, session: str) -> dict[str, Any] | None:
    subdir = SESSION_FRAME_DIRS.get(session, "")
    if not subdir:
        return None
    manifest_path = (
        FRAMES_2026
        / subdir
        / student
        / f"{student}_video_extraction_manifest.json"
    )
    if not manifest_path.is_file():
        return None
    return json.loads(manifest_path.read_text(encoding="utf-8"))


def count_frames(student: str, session: str) -> int:
    subdir = SESSION_FRAME_DIRS.get(session, "")
    if not subdir:
        return 0
    frames_dir = FRAMES_2026 / subdir / student / f"{student}_frames"
    if not frames_dir.is_dir():
        return 0
    return len(sorted(frames_dir.glob("*.jpg")) + sorted(frames_dir.glob("*.png")))


# ─────────────────────────────────────────────────────────────
# Output building
# ─────────────────────────────────────────────────────────────

def build_output(
    student: str,
    session: str,
    steps: list[dict[str, Any]],
    source_path: Path | None,
    frame_manifest: dict[str, Any] | None,
    n_frames: int,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": "2026-v1",
        "generated_at": now,
        "student_id": student,
        "session": session,
        "source_document": str(source_path) if source_path else None,
        "source_type": "ipynb" if source_path else "stub",
        "status": None if source_path else "missing_notebook_source",
        "observation_steps": steps,
        "step_count": len(steps),
        "frame_count": n_frames,
        "frame_manifest_path": (
            str(
                FRAMES_2026
                / SESSION_FRAME_DIRS.get(session, "")
                / student
                / f"{student}_video_extraction_manifest.json"
            )
            if frame_manifest
            else None
        ),
        "alignment_ready": len(steps) > 0 and n_frames > 0,
    }


# ─────────────────────────────────────────────────────────────
# Per-student/session processing
# ─────────────────────────────────────────────────────────────

def process(student: str, session: str, dry_run: bool = False) -> None:
    out_dir = OUT_ROOT / student / session / "intermediate"
    out_path = out_dir / f"{student}_observation_steps.json"

    # Resolve notebook (shared across sessions — one notebook per student)
    notebook_path: Path | None = None
    candidate = NOTEBOOKS_DIR / f"{student}.ipynb"
    if candidate.is_file():
        notebook_path = candidate

    # Parse steps
    if notebook_path:
        LOGGER.info("Parsing notebook: %s", notebook_path)
        steps = parse_notebook(notebook_path)
    else:
        LOGGER.warning("No notebook found for %s — writing zero-step stub", student)
        steps = _stub_steps()

    # Frame info
    frame_manifest = load_frame_manifest(student, session)
    n_frames = count_frames(student, session)

    payload = build_output(student, session, steps, notebook_path, frame_manifest, n_frames)

    if dry_run:
        print(
            f"[DRY-RUN] {student}/{session}: {len(steps)} steps, {n_frames} frames → {out_path}"
        )
        return

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    LOGGER.info(
        "Wrote %s: %d steps, %d frames, alignment_ready=%s",
        out_path,
        len(steps),
        n_frames,
        payload["alignment_ready"],
    )
    print(f"  {student}/{session}: {len(steps)} steps, {n_frames} frames → {out_path}")


def discover_students() -> list[str]:
    students = sorted(
        p.stem for p in NOTEBOOKS_DIR.glob("*.ipynb") if p.is_file()
    )
    return students


# ─────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────

def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")

    parser = argparse.ArgumentParser(
        description="Build 2026 observation_steps.json from student Jupyter notebooks."
    )
    parser.add_argument(
        "--student", "-s",
        help="Pseudonym (e.g. Amy). Omit when using --all.",
    )
    parser.add_argument(
        "--session",
        choices=SESSIONS,
        help="Session ID. Required unless using --all.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_students",
        help="Process all students found in Final Odevi Dokumanlari/ for all sessions.",
    )
    parser.add_argument(
        "--cohort-dir",
        type=Path,
        default=None,
        help="Override NOTEBOOKS_DIR (for testing).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written, do not write files.",
    )
    args = parser.parse_args()

    global NOTEBOOKS_DIR
    if args.cohort_dir:
        NOTEBOOKS_DIR = args.cohort_dir

    if args.all_students:
        students = discover_students()
        if not students:
            LOGGER.warning("No .ipynb files found in %s", NOTEBOOKS_DIR)
        for stu in students:
            for ses in SESSIONS:
                process(stu, ses, dry_run=args.dry_run)
    else:
        if not args.student:
            parser.error("--student is required when not using --all")
        if not args.session:
            parser.error("--session is required when not using --all")
        process(args.student, args.session, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
