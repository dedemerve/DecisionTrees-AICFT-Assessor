#!/usr/bin/env python3
"""Write MANIFEST.json inventories for data_sources_* (filenames + sizes only)."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COHORTS = ("data_sources_2025", "data_sources_2026")


def _file_entry(path: Path, root: Path) -> dict:
    rel = path.relative_to(root).as_posix()
    stat = path.stat()
    return {
        "path": rel,
        "size_bytes": stat.st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def inventory_cohort(name: str) -> dict:
    root = REPO / name
    files: list[dict] = []
    if root.is_dir():
        for path in sorted(root.rglob("*")):
            if path.is_file() and path.name != ".DS_Store":
                files.append(_file_entry(path, root))
    return {
        "cohort": name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "file_count": len(files),
        "total_bytes": sum(f["size_bytes"] for f in files),
        "files": files,
    }


def main() -> None:
    for name in COHORTS:
        doc = inventory_cohort(name)
        out = REPO / name / "MANIFEST.json"
        out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote {out.relative_to(REPO)} ({doc['file_count']} files, {doc['total_bytes']} bytes)")


if __name__ == "__main__":
    main()
