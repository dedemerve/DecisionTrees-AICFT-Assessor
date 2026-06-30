# data_sources_2026 — 2026 cohort raw research data

**Do not delete, move, or “clean up” this folder.** Cursor agents and scripts must not run `rm` or `git rm` here without explicit researcher approval.

## Layout

| Subfolder | Contents |
|-----------|----------|
| `All Documents/` | Anonymized student worksheet PDFs (pseudonym filenames) |
| `21 April CODAP Arbor Screen Recordings/` | `.webm` per student |
| `28 April CODAP Arbor Screen Recordings/` | `.webm` per student |
| `05 May Colab Python Screen Recordings/` | `.webm` per student |

## Git / GitHub

- **PDFs** in `All Documents/` are not gitignored — commit them after recovery so GitHub has a copy.
- **Videos** (`.webm`) are gitignored (size) — keep a local or external backup.

## Inventory

Run from repo root:

```bash
python scripts/inventory_data_sources.py
```

Committed manifest: `data_sources_2026/MANIFEST.json`
