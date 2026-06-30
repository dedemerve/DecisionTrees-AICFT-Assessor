# Research data protection

## Why GitHub push did not save your student files

Pushing `main` only uploads **git-tracked** files. Most raw research data in this repo is **intentionally not tracked**:

| Path | On GitHub? | Why |
|------|------------|-----|
| `data_sources_2026/All Documents/*.pdf` | Only if you `git add` them | PDFs are not in `.gitignore`, but were never committed |
| `data_sources_2026/**/*.webm` | **No** | `*.webm` in `.gitignore` (too large) |
| `data_sources_2025/**` videos | **No** | Same |
| `ocr_output/` | **No** | Entire folder in `.gitignore` |
| `students/<id>/` | Partial | Some JSON artifacts are tracked; not raw PDFs |

**Conclusion:** `git push` protected **code and rubrics**, not your anonymized PDFs or screen recordings.

## What was deleted by an agent (recoverable from git)

Commit `fb0c9ef` ran `git rm -r ocr_output/` — ~369 OCR page images and markers were removed from disk. They still exist in git history:

```bash
git checkout fb0c9ef^ -- ocr_output/
```

## What is not in git (Disk Drill / backup only)

`data_sources_2026/All Documents/` anonymized PDFs were never committed. Recovery options:

- Disk Drill / PhotoRec on the Mac volume
- iCloud Drive → Recently Deleted
- Any zip/USB copy from anonymization

## Prevent future loss

1. **Frozen folders (macOS):** `data_sources_2025/`, `data_sources_2026/`, and `answer_key_worksheets/` are locked with `chflags uchg`. See `.FROZEN` marker in each folder.

   ```bash
   bash scripts/freeze_data_sources.sh    # re-lock after changes
   bash scripts/unfreeze_data_sources.sh  # only when you must add/replace files
   ```

2. **Cursor rule:** `.cursor/rules/protect-research-data.mdc` — agents must not delete data paths
3. **Inventory manifest** (committed to git):

   ```bash
   python scripts/inventory_data_sources.py
   git add data_sources_2026/MANIFEST.json data_sources_2025/MANIFEST.json
   git commit -m "Update data source inventory manifest"
   ```

   The manifest lists filenames and sizes — if files disappear locally, git will show the diff.

3. **After recovering PDFs**, unfreeze first, copy files, then freeze again:

   ```bash
   bash scripts/unfreeze_data_sources.sh
   # copy PDFs into data_sources_2026/All Documents/
   bash scripts/freeze_data_sources.sh
   git add "data_sources_2026/All Documents/"
   git commit -m "Add anonymized student worksheet PDFs"
   ```

4. **Videos:** keep on external SSD; or use [Git LFS](https://git-lfs.com/) if you need cloud backup.

5. **Time Machine:** attach an external drive and enable Time Machine for future protection (does not restore past unbacked files).

## Do-not-delete layout

```
data_sources_2026/
  All Documents/          ← anonymized student PDFs (critical)
  * Screen Recordings/    ← .webm (local only, gitignored)
data_sources_2025/        ← prior cohort videos
ocr_output/               ← OCR page images (regenerable from PDFs if PDFs exist)
students/                 ← per-student pipeline JSON
```
