#!/usr/bin/env python3
"""Export lossless tabular views from process_codes.json.

Produces three tables per student and optional cohort merges for Hugging Face:

  episodes                 — 1 row / student × episode
  episode_process_codes    — 1 row / student × episode × v_code (full matrix)
  session_ml_features      — 1 row / student (wide ML flags)

Canonical nested JSON (process_codes.json) is unchanged; tables are projections.

Layout v1 (2025 flat):   <student>/<id>_process_codes.json  →  <student>/tabular/
Layout v2 (2026 layered): <student>/<session>/annotations/<id>_process_codes.v1.json
                          →  <student>/<session>/exports/tabular/

Usage:
  python scripts/export_process_codes_tables.py Ally
  python scripts/export_process_codes_tables.py --all-2025
  python scripts/export_process_codes_tables.py --all-2025 --cohort-parquet
  python scripts/export_process_codes_tables.py --year 2026 --all
  python scripts/export_process_codes_tables.py --year 2026 Amy --session codap_21apr
  python scripts/export_process_codes_tables.py --year 2026 --all --merge-cohort
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCRIPTS = Path(__file__).resolve().parent
REPO = SCRIPTS.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from video_process_codes import flatten_process_codes_tables

OUT_2025 = REPO / "training_datasets" / "2025"
OUT_2026 = REPO / "training_datasets" / "2026"
EXPORT_VERSION = "1.0"

_SKIP_DIRS = {"adjudication", "hf_export"}
LOGGER = logging.getLogger("export_process_codes_tables")

TABLE_NAMES = ("episodes", "episode_process_codes", "session_ml_features")
TABLE_GRAINS = {
    "episodes": "student_id × episode_id",
    "episode_process_codes": "student_id × episode_id × v_code",
    "session_ml_features": "student_id",
}
TABLE_KEYS = {
    "episodes": ["student_id", "cohort_year", "episode_id"],
    "episode_process_codes": ["row_id"],
    "session_ml_features": ["student_id", "cohort_year"],
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _serialize_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (list, dict)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("", encoding="utf-8")
        return
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for k in row:
            if k not in seen:
                seen.add(k)
                fieldnames.append(k)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: _serialize_cell(row.get(k)) for k in fieldnames})


def write_parquet(path: Path, rows: list[dict[str, Any]]) -> bool:
    try:
        import pandas as pd
        path.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows).to_parquet(path, index=False)
        return True
    except (ImportError, Exception):
        return False


def export_student_tables(
    student_id: str,
    student_dir: Path,
    *,
    write_parquet_files: bool = False,
    layout: str = "v1",
) -> dict[str, Any]:
    """Export tabular views for one student (or one student+session in v2).

    layout="v1"  — 2025 flat:   reads <student_dir>/<id>_process_codes.json
                                 writes <student_dir>/tabular/
    layout="v2"  — 2026 layered: reads <student_dir>/annotations/<id>_process_codes.v1.json
                                 writes <student_dir>/exports/tabular/
    """
    if layout == "v2":
        src = student_dir / "annotations" / f"{student_id}_process_codes.v1.json"
        tabular_dir = student_dir / "exports" / "tabular"
        rel_prefix = "exports/tabular"
    else:
        src = student_dir / f"{student_id}_process_codes.json"
        tabular_dir = student_dir / "tabular"
        rel_prefix = "tabular"

    if not src.is_file():
        raise FileNotFoundError(f"Missing {src}")

    doc = load_json(src)
    tables = flatten_process_codes_tables(doc)
    tabular_dir.mkdir(parents=True, exist_ok=True)

    manifest_tables: dict[str, Any] = {}
    for name in TABLE_NAMES:
        rows = tables[name]
        jsonl_name = f"{student_id}_{name}.jsonl"
        parquet_name = f"{student_id}_{name}.parquet"

        parquet_path = None
        if layout == "v2":
            # v2: parquet always written (no CSV)
            pq = tabular_dir / parquet_name
            if write_parquet(pq, rows):
                parquet_path = parquet_name
            manifest_tables[name] = {
                "grain": TABLE_GRAINS[name],
                "primary_key": TABLE_KEYS[name],
                "row_count": len(rows),
                "parquet": f"{rel_prefix}/{parquet_path}" if parquet_path else None,
            }
        else:
            # v1: jsonl + csv always; parquet optional
            csv_name = f"{student_id}_{name}.csv"
            write_jsonl(tabular_dir / jsonl_name, rows)
            write_csv(tabular_dir / csv_name, rows)
            if write_parquet_files:
                pq = tabular_dir / parquet_name
                if write_parquet(pq, rows):
                    parquet_path = parquet_name
            manifest_tables[name] = {
                "grain": TABLE_GRAINS[name],
                "primary_key": TABLE_KEYS[name],
                "row_count": len(rows),
                "jsonl": f"{rel_prefix}/{jsonl_name}",
                "csv": f"{rel_prefix}/{csv_name}",
                "parquet": f"{rel_prefix}/{parquet_path}" if parquet_path else None,
            }

    manifest = {
        "$schema": "schema/process_codes_tables.schema.json",
        "export_version": EXPORT_VERSION,
        "layout": layout,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_year": doc.get("cohort_year"),
        "student_id": student_id,
        "source_artifact": "process_codes",
        "source_file": src.name,
        "tables": manifest_tables,
    }
    if layout == "v2":
        manifest_path = student_dir / "metadata" / f"{student_id}_tables_manifest.json"
    else:
        manifest_path = tabular_dir / f"{student_id}_process_codes_tables_manifest.json"
    write_json(manifest_path, manifest)

    LOGGER.info(
        "[%s] tables — episodes=%d codes=%d session=1",
        student_id,
        len(tables["episodes"]),
        len(tables["episode_process_codes"]),
    )
    return manifest


def merge_cohort_tables(
    cohort_dir: Path,
    *,
    write_parquet_files: bool = False,
    layout: str = "v1",
    cohort_year: int = 2025,
) -> Path:
    """Merge per-student tabular files into cohort-level hf_export/.

    layout="v1": reads from <student>/tabular/*.jsonl (2025 flat)
    layout="v2": reads from <student>/<session>/exports/tabular/*.parquet (2026 layered)
    """
    export_dir = cohort_dir / "hf_export"
    export_dir.mkdir(parents=True, exist_ok=True)

    merged: dict[str, list[dict[str, Any]]] = {n: [] for n in TABLE_NAMES}
    source_count = 0

    if layout == "v2":
        # Enumerate <student>/<session> pairs
        for student_dir in sorted(cohort_dir.iterdir()):
            if not student_dir.is_dir() or student_dir.name in _SKIP_DIRS:
                continue
            for session_dir in sorted(student_dir.iterdir()):
                if not session_dir.is_dir() or session_dir.name == "metadata":
                    continue
                for name in TABLE_NAMES:
                    pq = session_dir / "exports" / "tabular" / f"{student_dir.name}_{name}.parquet"
                    if not pq.is_file():
                        continue
                    try:
                        import pandas as pd
                        for row in pd.read_parquet(str(pq)).to_dict(orient="records"):
                            merged[name].append(row)
                    except Exception as exc:
                        LOGGER.warning("Skip %s: %s", pq, exc)
                source_count += 1
    else:
        # v1: read jsonl from <student>/tabular/
        for student_dir in sorted(cohort_dir.iterdir()):
            if not student_dir.is_dir() or student_dir.name in _SKIP_DIRS:
                continue
            manifest_path = student_dir / "tabular" / f"{student_dir.name}_process_codes_tables_manifest.json"
            if not manifest_path.is_file():
                continue
            manifest = load_json(manifest_path)
            for name in TABLE_NAMES:
                rel = manifest["tables"][name].get("jsonl")
                if not rel:
                    continue
                jsonl_path = student_dir / rel
                if not jsonl_path.is_file():
                    continue
                with jsonl_path.open(encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            merged[name].append(json.loads(line))
            source_count += 1

    cohort_manifest: dict[str, Any] = {
        "$schema": "schema/process_codes_tables.schema.json",
        "export_version": EXPORT_VERSION,
        "layout": layout,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cohort_year": cohort_year,
        "source_artifact": "process_codes",
        "source_count": source_count,
        "tables": {},
    }

    for name in TABLE_NAMES:
        rows = merged[name]
        parquet_path = export_dir / f"{name}.parquet"
        pq_ok = write_parquet(parquet_path, rows)

        entry: dict[str, Any] = {
            "grain": TABLE_GRAINS[name],
            "primary_key": TABLE_KEYS[name],
            "row_count": len(rows),
            "parquet": parquet_path.name if pq_ok else None,
        }
        if layout == "v1":
            jsonl_path = export_dir / f"{name}.jsonl"
            csv_path = export_dir / f"{name}.csv"
            write_jsonl(jsonl_path, rows)
            write_csv(csv_path, rows)
            entry["jsonl"] = jsonl_path.name
            entry["csv"] = csv_path.name

        cohort_manifest["tables"][name] = entry

    out = export_dir / "process_codes_tables_cohort_manifest.json"
    write_json(out, cohort_manifest)
    LOGGER.info(
        "Cohort merge → %s (episodes=%d, codes=%d, sessions=%d)",
        export_dir,
        len(merged["episodes"]),
        len(merged["episode_process_codes"]),
        len(merged["session_ml_features"]),
    )
    return export_dir


def list_students_v1(cohort_dir: Path) -> list[str]:
    """List students in a v1 (flat) cohort dir that have process_codes.json."""
    return sorted(
        p.name
        for p in cohort_dir.iterdir()
        if p.is_dir()
        and p.name not in _SKIP_DIRS
        and (p / f"{p.name}_process_codes.json").is_file()
    )


# Keep old name for backward compat with build_video_analysis_bundle.py imports
list_2025_students = list_students_v1


def list_sessions_v2(cohort_dir: Path) -> list[tuple[str, str]]:
    """List (student_id, session_id) pairs in a v2 cohort dir with process_codes.v1.json."""
    pairs: list[tuple[str, str]] = []
    for student_dir in sorted(cohort_dir.iterdir()):
        if not student_dir.is_dir() or student_dir.name in _SKIP_DIRS:
            continue
        for session_dir in sorted(student_dir.iterdir()):
            if not session_dir.is_dir() or session_dir.name == "metadata":
                continue
            src = session_dir / "annotations" / f"{student_dir.name}_process_codes.v1.json"
            if src.is_file():
                pairs.append((student_dir.name, session_dir.name))
    return pairs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description="Export process_codes tabular views")
    ap.add_argument("students", nargs="*", help="Student IDs (all sessions exported unless --session given)")
    ap.add_argument("--year", type=int, default=2025, choices=[2025, 2026],
                    help="Cohort year (default: 2025)")
    ap.add_argument("--session", metavar="SESSION_ID",
                    help="Single session to export, e.g. codap_21apr (2026 only)")
    ap.add_argument("--all", dest="all_cohort", action="store_true",
                    help="Export all students/sessions in the cohort")
    ap.add_argument("--all-2025", action="store_true",
                    help="Shorthand for --year 2025 --all (backward compat)")
    ap.add_argument("--cohort-parquet", action="store_true",
                    help="Write parquet in v1 exports (v2 always writes parquet)")
    ap.add_argument("--merge-cohort", action="store_true",
                    help="Merge into hf_export/ after export")
    args = ap.parse_args()

    # Backward compat: --all-2025 implies --year 2025 --all
    if args.all_2025:
        args.year = 2025
        args.all_cohort = True

    cohort_dir = OUT_2025 if args.year == 2025 else OUT_2026
    layout = "v1" if args.year == 2025 else "v2"

    ok = 0

    if layout == "v1":
        students = list_students_v1(cohort_dir) if args.all_cohort else args.students
        if not students:
            ap.error("Provide student IDs, --all, or --all-2025")
        for sid in students:
            try:
                export_student_tables(
                    sid,
                    cohort_dir / sid,
                    write_parquet_files=args.cohort_parquet,
                    layout="v1",
                )
                ok += 1
            except Exception as exc:
                LOGGER.error("[%s] %s", sid, exc)
        if args.merge_cohort or args.all_cohort:
            merge_cohort_tables(cohort_dir, write_parquet_files=args.cohort_parquet,
                                layout="v1", cohort_year=2025)

    else:  # v2 / 2026
        if args.all_cohort:
            pairs = list_sessions_v2(cohort_dir)
        elif args.students:
            # Expand each student to its available sessions (or filter by --session)
            pairs = []
            for sid in args.students:
                student_dir = cohort_dir / sid
                if not student_dir.is_dir():
                    LOGGER.error("Student dir not found: %s", student_dir)
                    continue
                if args.session:
                    pairs.append((sid, args.session))
                else:
                    for sess_dir in sorted(student_dir.iterdir()):
                        if sess_dir.is_dir() and sess_dir.name != "metadata":
                            pairs.append((sid, sess_dir.name))
        else:
            ap.error("Provide student IDs, --all, or --all-2025")
            pairs = []

        for sid, session_id in pairs:
            session_dir = cohort_dir / sid / session_id
            try:
                export_student_tables(
                    sid,
                    session_dir,
                    write_parquet_files=True,
                    layout="v2",
                )
                ok += 1
            except Exception as exc:
                LOGGER.error("[%s/%s] %s", sid, session_id, exc)

        if args.merge_cohort or args.all_cohort:
            merge_cohort_tables(cohort_dir, write_parquet_files=True,
                                layout="v2", cohort_year=2026)

    LOGGER.info("Done %d/%d", ok, len(pairs) if layout == "v2" else len(students))


if __name__ == "__main__":
    main()
