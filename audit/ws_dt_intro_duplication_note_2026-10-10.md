# WS_DT_INTRO — Duplication Documentation Note
**Date:** 2026-10-10  
**Status:** Documentation only. No files deleted or rescored.

---

## Finding

All 15 `students/*/WS_DT_INTRO/extraction.json` files are **byte-identical** to the corresponding `students/*/WS13/extraction.json` files. Both derive from the same OCR source:

```
ocr_output/{student}/21-28_nisan_2026_çalışma_kâğıdı_dt_raw.json
```

Both directories contain 31 items keyed `DT_A_Q1..DT_G_Q2`.

### Evidence

- File sizes match across all 15 pairs.
- Item keys and values match exactly (Python `==` comparison, all 15 pairs).
- `bridged_from` field in both points to the same OCR source file.

### Why both exist

The bridge script previously ran for both `WS_DT_INTRO` and `WS13` worksheet configs, both pointing to `çalışma_kâğıdı_dt_raw.json`. This created two identical copies.

---

## Current State

| Directory | Files | Content | Scored? |
|---|---|---|---|
| `students/*/WS13/` | 15 extraction.json + 15 scoring.json | 31 DT items, real values | **Yes — all 15 students** |
| `students/*/WS_DT_INTRO/` | 15 extraction.json | 31 DT items, identical to WS13 | **No — not needed** |

---

## Recommendation

This is a documentation-only change. No file should be deleted or rescored at this stage.

**Suggested future action (researcher decision required):**

Option A — Keep as-is. The WS_DT_INTRO directories are harmless duplicates and serve as a historical record of how the worksheet was originally named in the pipeline. No action needed.

Option B — Add a `README.txt` or `DUPLICATE_OF_WS13.txt` marker file to each `WS_DT_INTRO/` directory explaining the duplication. This would prevent future confusion without deleting any data.

Option C — After all WS13 scoring is researcher-reviewed and finalized, remove the WS_DT_INTRO extraction files. The original OCR source files are not affected.

**Do not:** Create separate scores for WS_DT_INTRO. This would duplicate WS13 scores.

---

## Files Inspected (Read-Only)

`students/Amy/WS_DT_INTRO/extraction.json` through `students/Zara/WS_DT_INTRO/extraction.json` — 15 files, compared against corresponding WS13 files. No modifications made.
