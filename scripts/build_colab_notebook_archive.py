#!/usr/bin/env python3
"""Build anonymized public copies of the weekly Colab notebooks.

Reads the three Downloads folders, keeps the latest notebook for each
pseudonym, and writes public copies. The private inventory stays outside
the repository. Original files are not moved or deleted.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from anonymize_student_data import (  # noqa: E402
    PSEUDONYM_MAP,
    anonymize_text,
    pseudo_from_filename,
)

DOWNLOADS = Path("/Users/mrved/Downloads")
STAGES = [
    ("2 June", DOWNLOADS / "2 Haziran Gogle Colab Python"),
    ("12 May", DOWNLOADS / "12 Mayıs Google Colab Python "),
    ("5 May", DOWNLOADS / "5 Mayıs Google Colab Python"),
]
STUDENTS = [
    "Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel", "Marco", "Marcus",
    "Melinda", "Nadia", "Serena", "Shana", "Sheila", "Ulysses", "Zara",
]
ARCHIVE = ROOT / "data_sources_2026" / "Python Notebooks"
PUBLIC = ROOT / "mmla_explorer" / "site" / "downloads" / "notebooks"
INVENTORY = DOWNLOADS / "colab_notebook_inventory_private.json"
CATALOG = ROOT / "mmla_explorer" / "site" / "data" / "notebooks_public.js"

# The welcome example in the teacher notebook uses the instructor's given name.
INSTRUCTOR_GIVEN = "Merve"


def unique_prefixes() -> list[tuple[str, str]]:
    pairs = []
    items = list(PSEUDONYM_MAP.items())
    for real, pseudo in items:
        parts = real.split()
        if len(parts) < 3:
            continue
        prefix = " ".join(parts[:2])
        owners = {p for name, p in items if name.startswith(prefix)}
        if owners == {pseudo}:
            pairs.append((prefix, pseudo))
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    return pairs


PREFIXES = unique_prefixes()


def name_tokens() -> tuple[list[tuple[str, str]], list[str], list[str]]:
    """Unique name parts map to one pseudonym. A shared given name does not."""
    owners: dict[str, set[str]] = {}
    role: dict[str, str] = {}
    for real, pseudo in PSEUDONYM_MAP.items():
        parts = real.split()
        for i, tok in enumerate(parts):
            if len(tok) < 4:
                continue
            key = tok.casefold()
            owners.setdefault(key, set()).add(pseudo)
            role[key] = "first" if i == 0 else ("last" if i == len(parts) - 1 else "mid")
    unique = [
        (tok, next(iter(pseudos)))
        for tok, pseudos in owners.items()
        if len(pseudos) == 1 and tok.casefold() != INSTRUCTOR_GIVEN.casefold()
    ]
    unique.sort(key=lambda item: len(item[0]), reverse=True)
    shared_first = [tok for tok, pseudos in owners.items() if len(pseudos) > 1 and role[tok] == "first"]
    shared_other = [tok for tok, pseudos in owners.items() if len(pseudos) > 1 and role[tok] != "first"]
    return unique, shared_first, shared_other


UNIQUE_TOKENS, SHARED_FIRST, SHARED_OTHER = name_tokens()


def replace_token(text: str, needle: str, repl: str) -> str:
    """Replace a name even when Unicode casefolding changes its length."""
    needle_cf = needle.casefold()
    if needle_cf not in text.casefold():
        return text
    out = []
    i = 0
    n = len(text)
    while i < n:
        matched_end = None
        buf = ""
        for j in range(i, min(n, i + len(needle) + 6)):
            buf += text[j]
            folded = buf.casefold()
            if folded == needle_cf:
                before = text[i - 1] if i else ""
                after = text[j + 1] if j + 1 < n else ""
                if not (before.isalnum() or after.isalnum()):
                    matched_end = j
                break
            if len(folded) > len(needle_cf):
                break
        if matched_end is None:
            out.append(text[i])
            i += 1
        else:
            out.append(repl)
            i = matched_end + 1
    return "".join(out)


def contains_token(text: str, needle: str) -> bool:
    return replace_token(text, needle, "\u0000") != text


def scrub(text: str) -> str:
    if not isinstance(text, str) or not text:
        return text
    text = unicodedata.normalize("NFC", text)
    text = anonymize_text(text)
    for old, new in PREFIXES:
        text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    for tok, pseudo in UNIQUE_TOKENS:
        text = replace_token(text, tok, pseudo)
    for tok in SHARED_FIRST:
        text = replace_token(text, tok, "Classmate")
    text = re.sub(rf"\b{re.escape(INSTRUCTOR_GIVEN)}\b", "Instructor", text)
    return text


def walk(value):
    if isinstance(value, str):
        # Plot images are base64 and do not contain names as text.
        if len(value) > 500 and " " not in value[:300]:
            return value
        return scrub(value)
    if isinstance(value, list):
        return [walk(v) for v in value]
    if isinstance(value, dict):
        return {k: walk(v) for k, v in value.items()}
    return value


def load_notebook(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_bytes())
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return None
    if not isinstance(data, dict) or "cells" not in data:
        return None
    return data


def is_notebook(path: Path) -> bool:
    if path.suffix.lower() == ".ipynb":
        return True
    if path.suffix == "" and path.is_file():
        return load_notebook(path) is not None
    return False


def strip_accounts(nb: dict) -> int:
    """Remove Colab account names and user ids. Leave output stream names."""
    removed = 0

    def walk_meta(value):
        nonlocal removed
        if isinstance(value, dict):
            for key in ("displayName", "userId", "userEmail", "photoUrl"):
                if key in value:
                    value.pop(key)
                    removed += 1
            user = value.get("user")
            if isinstance(user, dict) and not user:
                value.pop("user")
            for item in value.values():
                walk_meta(item)
        elif isinstance(value, list):
            for item in value:
                walk_meta(item)

    walk_meta(nb.get("metadata"))
    for cell in nb.get("cells") or []:
        walk_meta(cell.get("metadata"))
    return removed


def prepare(nb: dict) -> tuple[dict, list[str]]:
    notes = []
    original = json.dumps(nb, ensure_ascii=False)
    cleaned = walk(nb)
    if strip_accounts(cleaned):
        notes.append("Removed Colab account names and user ids.")
    meta = cleaned.setdefault("metadata", {})
    colab = meta.get("colab")
    if isinstance(colab, dict) and "provenance" in colab:
        colab.pop("provenance", None)
        notes.append("Removed Colab provenance metadata.")
        if not colab:
            meta.pop("colab", None)
    if scrub(original) != original:
        notes.append("Replaced personal names in notebook text.")
    if any(tok in original.casefold() for tok in SHARED_FIRST):
        notes.append("Replaced a given name shared by two students with Classmate.")
    if INSTRUCTOR_GIVEN in original and INSTRUCTOR_GIVEN not in json.dumps(cleaned, ensure_ascii=False):
        notes.append("Replaced the instructor's given name in example text with Instructor.")
    return cleaned, notes


def residual_names(text: str) -> list[str]:
    folded = unicodedata.normalize("NFC", text).casefold()
    hits = []
    for real in list(PSEUDONYM_MAP) + [old for old, _ in PREFIXES]:
        if real.casefold() in folded:
            hits.append("mapped-name")
    for tok, _pseudo in UNIQUE_TOKENS:
        if contains_token(folded, tok):
            hits.append("name-token")
            break
    for tok in SHARED_FIRST + SHARED_OTHER:
        if contains_token(folded, tok):
            hits.append("shared-name")
            break
    if re.search(rf"\b{re.escape(INSTRUCTOR_GIVEN)}\b", text):
        hits.append("instructor-name")
    if "displayName" in text or "userId" in text:
        hits.append("account")
    if re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        hits.append("email")
    return hits


def main() -> None:
    example_hash = None
    by_stage: dict[str, dict[str, list[Path]]] = {}
    skipped = []
    for stage, folder in STAGES:
        grouped = defaultdict(list)
        if not folder.exists():
            raise SystemExit(f"Missing folder for {stage}")
        for path in sorted(folder.iterdir()):
            if path.name.startswith("."):
                continue
            if path.suffix.lower() == ".webm":
                skipped.append({"stage": stage, "kind": "recording", "bytes": path.stat().st_size})
                continue
            if not is_notebook(path):
                skipped.append({"stage": stage, "kind": "other", "suffix": path.suffix.lower()})
                continue
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            who = pseudo_from_filename(path)
            if who is None:
                if example_hash is None:
                    example_hash = digest
                skipped.append({"stage": stage, "kind": "unassigned", "same_as_example": digest == example_hash, "bytes": path.stat().st_size})
                continue
            if who not in STUDENTS:
                skipped.append({"stage": stage, "kind": "outside-cohort", "pseudo": who})
                continue
            grouped[who].append(path)
        by_stage[stage] = grouped

    # The identical unassigned notebooks are the teacher example. Confirm one hash.
    example_paths = []
    for stage, folder in STAGES:
        for path in folder.iterdir():
            if not is_notebook(path):
                continue
            if pseudo_from_filename(path) is None:
                example_paths.append(path)
    hashes = {hashlib.sha256(p.read_bytes()).hexdigest() for p in example_paths}
    teacher_src = next(DOWNLOADS.glob("Karar_*.ipynb"))

    selected = []
    inventory = []
    flagged = []
    for stage, _folder in STAGES:
        for who, paths in by_stage[stage].items():
            if any(item["pseudonym"] == who for item in selected):
                inventory.append({
                    "pseudonym": who,
                    "stage": stage,
                    "used": False,
                    "reason": "later stage already selected",
                    "files": [p.name for p in paths],
                })
                continue
            if len(paths) > 1:
                digests = {hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
                if len(digests) > 1:
                    flagged.append({"pseudonym": who, "stage": stage, "reason": "conflicting files in the same stage"})
                    inventory.append({
                        "pseudonym": who,
                        "stage": stage,
                        "used": False,
                        "reason": "conflicting files",
                        "files": [p.name for p in paths],
                    })
                    continue
            chosen = paths[0]
            selected.append({"pseudonym": who, "stage": stage, "path": chosen})
            inventory.append({
                "pseudonym": who,
                "stage": stage,
                "used": True,
                "files": [p.name for p in paths],
                "chosen": chosen.name,
            })

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    (ARCHIVE / "Teacher Instructions").mkdir(exist_ok=True)
    (ARCHIVE / "Student Notebooks").mkdir(exist_ok=True)
    PUBLIC.mkdir(parents=True, exist_ok=True)
    for old in PUBLIC.glob("*.ipynb"):
        old.unlink()

    redactions = []
    public_students = []
    for item in selected:
        nb = load_notebook(item["path"])
        cleaned, notes = prepare(nb)
        raw = json.dumps(cleaned, ensure_ascii=False)
        hits = residual_names(raw)
        if hits:
            flagged.append({"pseudonym": item["pseudonym"], "stage": item["stage"], "reason": ",".join(hits)})
            continue
        name = f"{item['pseudonym']}.ipynb"
        text = json.dumps(cleaned, ensure_ascii=False, indent=1)
        (ARCHIVE / "Student Notebooks" / name).write_text(text, encoding="utf-8")
        (PUBLIC / name).write_text(text, encoding="utf-8")
        same_example = hashlib.sha256(item["path"].read_bytes()).hexdigest() in hashes
        public_students.append({
            "pseudonym": item["pseudonym"],
            "stage": item["stage"],
            "file": f"downloads/notebooks/{name}",
            "same_as_teacher_example": same_example,
        })
        if notes or same_example:
            redactions.append({"pseudonym": item["pseudonym"], "notes": notes, "same_as_teacher_example": same_example})

    teacher_nb, teacher_notes = prepare(load_notebook(teacher_src))
    teacher_raw = json.dumps(teacher_nb, ensure_ascii=False)
    teacher_hits = residual_names(teacher_raw)
    teacher_public = not teacher_hits
    if teacher_public:
        teacher_text = json.dumps(teacher_nb, ensure_ascii=False, indent=1)
        (ARCHIVE / "Teacher Instructions" / "teacher_instructions.ipynb").write_text(teacher_text, encoding="utf-8")
        (PUBLIC / "teacher_instructions.ipynb").write_text(teacher_text, encoding="utf-8")
    else:
        flagged.append({"pseudonym": "teacher-instructions", "stage": "", "reason": ",".join(teacher_hits)})

    readme = f"""# Python notebooks

Anonymized copies of the weekly Google Colab notebooks. Original submissions stay in Downloads and are not changed.

## Purpose

These notebooks show non-major students learning to build a decision tree in Python. Each file is one student's most recent available notebook. Names are replaced by pseudonyms.

## Teacher instructions

`Teacher Instructions/teacher_instructions.ipynb` is the step-by-step notebook that sets out the activity: writing to the screen, using a library, getting to know the data, splitting training and test data, building a decision tree, and reading a one-level tree. Several identical copies of this file were in the weekly folders. One copy is kept here. The instructor's given name in the welcome example was replaced with "Instructor".

## Weekly sequence

1. **5 May** — earlier notebooks. Students start using Python and its libraries.
2. **12 May** — the decision-tree notebook, including a one-level tree.
3. **2 June** — the latest continuation of that notebook, where a student submitted one.

The activities build on one another. A later notebook is a newer copy of the same work, not a separate assignment merged into the earlier file.

## Selection

For each student the archive keeps one notebook: the 2 June file if it exists, otherwise 12 May, otherwise 5 May. Earlier files are not deleted. If a stage had two different notebooks and no later stage existed, that student would be held for review instead of an arbitrary choice. That case did not occur for the selected stage.

## Anonymization

Filenames and notebook text use the project's existing pseudonyms. A given name shared by two students is written as Classmate, because it cannot be assigned to one pseudonym. Colab account names, user ids, and provenance metadata are removed. A private inventory of the original filenames is stored outside this repository and is not part of the website.

## Dependency

The notebooks read `/content/Food_Dataset_Turkish.csv` in Colab. That file is not in this archive, and it has not been replaced with a different dataset.

## Not included

Screen recordings that were stored beside some notebooks are not part of this collection. Students with no file in these three folders are absent here, not represented by an empty notebook.
"""
    (ARCHIVE / "README.md").write_text(readme, encoding="utf-8")

    final_dir = ROOT / "data_sources_2026" / "Final Ödevi Dokümanları"
    final_public = PUBLIC / "final"
    final_public.mkdir(parents=True, exist_ok=True)
    for old in final_public.glob("*.ipynb"):
        old.unlink()
    final_rows = []
    for who in STUDENTS:
        src = final_dir / f"{who}.ipynb"
        if not src.exists():
            flagged.append({"pseudonym": who, "stage": "final", "reason": "no notebook file"})
            continue
        cleaned, notes = prepare(load_notebook(src))
        raw = json.dumps(cleaned, ensure_ascii=False)
        hits = residual_names(raw)
        if hits:
            flagged.append({"pseudonym": who, "stage": "final", "reason": ",".join(hits)})
            continue
        name = f"{who}.ipynb"
        (final_public / name).write_text(json.dumps(cleaned, ensure_ascii=False, indent=1), encoding="utf-8")
        final_rows.append({"pseudonym": who, "file": f"downloads/notebooks/final/{name}", "cells": len(cleaned.get("cells") or [])})
        if notes:
            redactions.append({"pseudonym": who, "stage": "final", "notes": notes})

    catalog = {
        "teacher": "downloads/notebooks/teacher_instructions.ipynb" if teacher_public else None,
        "students": public_students,
        "final": final_rows,
        "dependency": "/content/Food_Dataset_Turkish.csv",
        "final_dataset": "lizard_data.csv",
    }
    CATALOG.write_text("window.NOTEBOOKS = " + json.dumps(catalog, ensure_ascii=False, indent=2) + ";\n", encoding="utf-8")
    INVENTORY.write_text(json.dumps({
        "inventory": inventory,
        "flagged": flagged,
        "redactions": redactions,
        "unassigned_hashes": len(hashes),
        "skipped_recordings": sum(1 for s in skipped if s["kind"] == "recording"),
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    counts = {stage: len(paths) for stage, paths in by_stage.items()}
    print("found_students_by_stage", counts)
    print("selected", len(public_students), "flagged", len(flagged), "teacher", teacher_public)
    print("stages", {row["stage"]: sum(1 for r in public_students if r["stage"] == row["stage"]) for row in public_students})
    missing = [s for s in STUDENTS if s not in {r["pseudonym"] for r in public_students}]
    print("missing", missing)
    print("identical_to_example", [r["pseudonym"] for r in public_students if r["same_as_teacher_example"]])
    print("final_public", len(final_rows), "final_held", [row["pseudonym"] for row in flagged if row.get("stage") == "final"])


if __name__ == "__main__":
    main()
