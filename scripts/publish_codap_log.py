#!/usr/bin/env python3
"""Build the public CODAP log: CODAP session 1 and CODAP session 2 only.

Reads a raw or anonymized CODAP export, maps identifiers to the 15
pseudonyms, and writes hf_dataset_stage/codap_log/codap_log_anonymized.csv.
Rows dated 7 April, and any other date, are left out.

Usage:
  python3 scripts/publish_codap_log.py "/path/to/log.csv"
  python3 scripts/publish_codap_log.py "/path/to/log.csv" --upload
"""
from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from anonymize_student_data import anonymize_text, pseudo_lookup_from_name_fragment  # noqa: E402

STUDENTS = {
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
}
SESSION = {
    "2026-04-21": "CODAP session 1",
    "2026-04-28": "CODAP session 2",
}
OUT = ROOT / "hf_dataset_stage" / "codap_log" / "codap_log_anonymized.csv"
FIELDS = ["id", "student_id", "session", "action", "timestamp_ms", "parameters"]
HF_REPO = "dedemerve/DecisionTrees-AICFT-CODAP-Arbor-LogFile"


def build(src: Path) -> list[dict]:
    rows = []
    for row in csv.DictReader(open(src, encoding="utf-8")):
        day = (row.get("created_at") or "")[:10]
        session = SESSION.get(day)
        if not session:
            continue
        sid = row.get("student_id") or ""
        pseudo = sid if sid in STUDENTS else pseudo_lookup_from_name_fragment(sid)
        if pseudo not in STUDENTS:
            continue
        rows.append({
            "id": row.get("id") or "",
            "student_id": pseudo,
            "session": session,
            "action": row.get("action") or "",
            "timestamp_ms": row.get("timestamp_ms") or "",
            "parameters": anonymize_text(row.get("parameters") or ""),
        })
    return rows


def main() -> None:
    if len(sys.argv) < 2:
        sys.exit("Give the path to the CODAP log CSV.")
    src = Path(sys.argv[1]).expanduser()
    upload = "--upload" in sys.argv
    rows = build(src)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts = Counter(r["session"] for r in rows)
    print(f"Wrote {len(rows)} rows to {OUT}")
    for name in ("CODAP session 1", "CODAP session 2"):
        print(f"  {name}: {counts[name]}")
    if not upload:
        return
    try:
        from huggingface_hub import HfApi
    except ImportError:
        sys.exit("huggingface_hub is not installed.")
    api = HfApi()
    api.create_repo(repo_id=HF_REPO, repo_type="dataset", exist_ok=True)
    api.upload_folder(
        folder_path=str(OUT.parent),
        repo_id=HF_REPO,
        repo_type="dataset",
        commit_message="Publish CODAP session 1 and CODAP session 2 only",
    )
    print(f"Uploaded to https://huggingface.co/datasets/{HF_REPO}")


if __name__ == "__main__":
    main()
