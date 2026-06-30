#!/usr/bin/env python3
"""
Copy 2026 cohort folders into data_sources_2026 and anonymize filenames + text content.

Mapping is defined in PSEUDONYM_MAP (real name -> pseudonym). Does not modify frozen
cohorts unless run after unfreeze_data_sources.sh.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEST_ROOT = REPO / "data_sources_2026"

# Official mapping: real name -> pseudonym
PSEUDONYM_MAP: dict[str, str] = {
    "Şeyda Demirci": "Sheila",
    "Mahmut Öztürk": "Marco",
    "İrem İlze": "Iris",
    "Mahsum Yasan": "Marcus",
    "İkbal Balaban": "Isabel",
    "Ayşe Merve Karataş": "Amy",
    "Senanur Elhan Çiçek": "Serena",
    "İrem Damar": "Irma",
    "Sakine Kübra Çetin": "Kate",
    "Batuhan Özger": "Bruno",
    "Zeynep Ortakaya": "Zara",
    "Şeyma Peltek": "Shana",
    "Melike Öztürk": "Melinda",
    "Hatice Şennur Ayyıldız": "Helena",
    "Nisa Altaş": "Nadia",
    "Umut Uzun": "Ulysses",
}

EXTRA_ALIASES: dict[str, str] = {
    "şeyda": "Sheila",
    "sena çiçek": "Serena",
    "senanur elhan çiçek": "Serena",
    "senanur elhan cicek": "Serena",
    "hatice sennur ayyıldız": "Helena",
    "haticesennurayyıldız": "Helena",
    "mahmut öztürk": "Marco",
    "mahmut öztürkt": "Marco",
    "nisa altaş": "Nadia",
    "nİsa altaş": "Nadia",
    "umut-uzun": "Ulysses",
    "umut uzun": "Ulysses",
    "zeynep ortakaya": "Zara",
    "irem ilze": "Iris",
    "irem damar": "Irma",
    "ikbal balaban": "Isabel",
    "batuhan özger": "Bruno",
    "şeyma peltek": "Shana",
    "melike öztürk": "Melinda",
    "mahsum yasan": "Marcus",
    "ayşe merve karataş": "Amy",
    "ayşe merve karataş": "Amy",
}

SOURCE_FOLDERS: list[tuple[Path, str]] = [
    (Path("/Users/mrved/Downloads/Final Ödevi Dokümanları "), "Final Ödevi Dokümanları"),
    (Path("/Users/mrved/Downloads/21 Nisan CODAP Arbor Dosyası"), "21 Nisan CODAP Arbor Dosyası"),
    (Path("/Users/mrved/Downloads/28 Nisan CODAP Arbor Dosyası"), "28 Nisan CODAP Arbor Dosyası"),
    (Path("/Users/mrved/Downloads/5 Mayıs Colab Python Dosyası"), "5 Mayıs Colab Python Dosyası"),
]

TEXT_SUFFIXES = {".csv", ".json", ".ipynb", ".codap", ".txt", ".md", ".xml"}
BINARY_SKIP = {".pdf", ".webm", ".mp4", ".mov", ".avi", ".DS_Store"}


def normalize_key(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower()
    text = re.sub(r"[^a-z0-9ğüşıöç]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_replacements() -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for real, pseudo in PSEUDONYM_MAP.items():
        pairs.append((real, pseudo))
        pairs.append((real.lower(), pseudo))
        pairs.append((real.upper(), pseudo))
        nk = normalize_key(real)
        if nk:
            pairs.append((nk, pseudo))
    for alias, pseudo in EXTRA_ALIASES.items():
        pairs.append((alias, pseudo))
        pairs.append((alias.title(), pseudo))
    # Longest first to avoid partial clobber
    pairs.sort(key=lambda x: len(x[0]), reverse=True)
    # Deduplicate by pattern
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for old, new in pairs:
        if old not in seen:
            seen.add(old)
            out.append((old, new))
    return out


REPLACEMENTS = build_replacements()


def pseudo_lookup_from_name_fragment(text: str) -> str | None:
    key = normalize_key(text)
    if not key:
        return None
    # Direct alias hits longest-first (normalize both sides for Turkish chars)
    for alias, pseudo in sorted(EXTRA_ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        ak = normalize_key(alias)
        if ak and (ak in key or key in ak):
            return pseudo
    for real, pseudo in PSEUDONYM_MAP.items():
        nk = normalize_key(real)
        if nk and (nk in key or key in nk):
            return pseudo
        first = nk.split()[0] if nk else ""
        if first and len(first) >= 4 and first in key.split():
            return pseudo
    return None


def pseudo_from_filename(path: Path) -> str | None:
    stem = path.stem if path.suffix else path.name
    stem = re.sub(r"\s*\(\d+\)\s*$", "", stem)
    stem = re.sub(r"\s+\d+$", "", stem)  # irma damar 2
    stem = re.sub(r"\d{8,}", "", stem)  # student numbers
    return pseudo_lookup_from_name_fragment(stem)


def anonymize_text(content: str) -> str:
    out = content
    for old, new in REPLACEMENTS:
        if not old:
            continue
        out = out.replace(old, new)
        # case-insensitive pass for latin fragments
        try:
            pattern = re.compile(re.escape(old), re.IGNORECASE)
            out = pattern.sub(new, out)
        except re.error:
            pass
    return out


def anonymize_file_content(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in BINARY_SKIP or not suffix:
        # extensionless ipynb/json
        if path.name.startswith("."):
            return False
        try:
            raw = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return False
    elif suffix not in TEXT_SUFFIXES and suffix != "":
        return False
    else:
        raw = path.read_text(encoding="utf-8", errors="replace")
    new = anonymize_text(raw)
    if new != raw:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def target_name(path: Path, pseudo: str) -> str:
    suffix = path.suffix.lower()
    if not suffix:
        # infer ipynb
        try:
            head = path.read_text(encoding="utf-8", errors="replace")[:80]
            if "nbformat" in head:
                suffix = ".ipynb"
        except OSError:
            suffix = ".ipynb"
    # Preserve date tokens in codap filenames
    date_m = re.search(r"(\d{2}\.\d{2}\.\d{4})", path.name)
    if suffix == ".codap":
        if date_m:
            return f"{pseudo}_codap_{date_m.group(1)}{suffix}"
        # disambiguate duplicate irma files
        dup = re.search(r"\s+(\d+)\s*$", path.stem)
        if dup:
            return f"{pseudo}_{dup.group(1)}{suffix}"
        return f"{pseudo}{suffix}"
    if suffix == ".ipynb":
        return f"{pseudo}{suffix}"
    return f"{pseudo}{suffix}" if suffix else pseudo


def copy_sources() -> list[Path]:
    copied: list[Path] = []
    for src, dest_name in SOURCE_FOLDERS:
        if not src.is_dir():
            print(f"SKIP missing source: {src}")
            continue
        dest = DEST_ROOT / dest_name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(src, dest)
        print(f"Copied -> {dest.relative_to(REPO)}")
        copied.append(dest)
    return copied


def anonymize_tree(root: Path) -> tuple[int, int, list[str]]:
    renamed = 0
    edited = 0
    unmapped: list[str] = []
    files = sorted([p for p in root.rglob("*") if p.is_file() and p.name != ".DS_Store"])
    for path in files:
        pseudo = pseudo_from_filename(path)
        if not pseudo:
            unmapped.append(str(path.relative_to(root)))
            continue
        if anonymize_file_content(path):
            edited += 1
        new_name = target_name(path, pseudo)
        new_path = path.with_name(new_name)
        if new_path != path:
            if new_path.exists():
                stem, suf = new_path.stem, new_path.suffix
                i = 2
                while new_path.exists():
                    new_path = path.with_name(f"{stem}_{i}{suf}")
                    i += 1
            path.rename(new_path)
            renamed += 1
    return renamed, edited, unmapped


def main() -> None:
    if not DEST_ROOT.is_dir():
        raise SystemExit(f"Missing {DEST_ROOT}")
    copied = copy_sources()
    total_renamed = total_edited = 0
    all_unmapped: dict[str, list[str]] = {}
    for folder in copied:
        r, e, u = anonymize_tree(folder)
        total_renamed += r
        total_edited += e
        if u:
            all_unmapped[folder.name] = u
    print(f"Renamed: {total_renamed}, content-edited: {total_edited}")
    if all_unmapped:
        print("Unmapped files (review manually):")
        for folder, items in all_unmapped.items():
            print(f"  {folder}:")
            for item in items:
                print(f"    - {item}")


if __name__ == "__main__":
    main()
