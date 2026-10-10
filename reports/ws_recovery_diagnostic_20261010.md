# Worksheet Recovery Diagnostic Report

**Date:** 2026-10-10  
**Prepared by:** Automated pipeline inspection  
**Scope:** WS11, WS12, WS13, WS14, WS3, WS4 (Amy / Marco gaps), WS5 (Sheila), WS6/WS7 (Melinda / Serena)

---

## Stage 1 — Source and Artifact Inventory

### PDF sources verified in `data_sources_2026/All Documents/`

| PDF filename | Maps to | Available |
|---|---|---|
| `24 Mart 2026 Çalışma Kâğıdı 1.pdf` | WS1 | YES |
| `24 Mart 2026 Çalışma Kâğıdı 3.pdf` | WS3 | YES |
| `24 Mart 2026 Çalışma Kâğıdı 4.pdf` | WS4 | YES |
| `24 Mart 2026 Çalışma Kâğıdı 5.pdf` | WS5 | YES |
| `31 Mart 2026 Çalışma Kâğıdı 6.pdf` | WS6 | YES |
| `31 Mart 2026 Çalışma Kâğıdı 7.pdf` | WS7 | YES |
| `31 Mart 2026 Çalışma Kâğıdı 10.pdf` | WS10 | YES |
| `31 Mart 2026 Çalışma Kâğıdı 12.pdf` | WS12 template | YES (template only, not student responses) |
| `21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf` | WS12 student responses | YES |
| `07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf` | WS13 | YES |
| `07 Nisan 2026 Çalışma Kâğıdı Titanic.pdf` | WS14 | YES |

**WS11 student PDF:** `data_sources_2025/Worksheet11_ Feedbacks.pdf` — EXISTS (in 2025 directory, 90 pages).  
**CONFIRMED:** pypdf inspection of this file found only 2025 cohort pseudonyms (Karl, Henry, etc.) on all pages. Zero 2026 cohort names found. The 2026 WS11 source material does not exist anywhere in the project. Existing zero-score `scoring.json` files for WS11 are void artifacts.

---

## Stage 2 — Per-Worksheet Diagnostic Classification

### WS13 (Xeno) — `EXT_OK_SCORE_MISSING`

**All 15 students.** Extraction complete, scoring.json absent.

- OCR json: EXISTS for all 15 (`ocr_output/<student>/<student>_Worksheet_Xeno.json`)
- extraction.json: EXISTS, status=pass, all items populated (82%–100% completion)
- scoring.json: MISSING for all 15
- Rubric: `rubrics/WS13_rubric.json` — 33 items, confirmed loadable
- Worksheets bundle: `worksheets/WS13/` — complete (rubric, schema, answer_key)
- **Root cause:** Scoring pipeline was never re-run after the WS_DT_XENO → WS13 rename
- **Classification:** Extraction available; scoring missing
- **Recovery path:** Run `python scripts/score_ws13_ws14.py --worksheet WS13` (requires ANTHROPIC_API_KEY)

### WS14 (Titanic) — `EXT_OK_SCORE_MISSING`

**All 15 students.** Same pattern as WS13.

- OCR json: EXISTS for all 15 (`ocr_output/<student>/<student>_Worksheet_Titanic.json`)
- extraction.json: EXISTS, status=pass, all items populated (26%–100%; Marco 26% and Ulysses 43% are notable low-completion students)
- scoring.json: MISSING for all 15
- Rubric: `rubrics/WS14_rubric.json` — 47 items, confirmed loadable
- **Classification:** Extraction available; scoring missing
- **Recovery path:** Run `python scripts/score_ws13_ws14.py --worksheet WS14` (requires ANTHROPIC_API_KEY)

### WS11 — `EXT_FAIL_NO_DATA` (13 students) / `NO_EXTRACTION_NO_OCR` (Melinda, Serena)

- OCR json: NONE in `ocr_output/` for any student
- extraction.json (13 students): EXISTS, status=fail, all 42 items = `(not_extracted)`
- scoring.json (13 students): EXISTS but total_score=0 / max_score=0 / all items zero — an artifact of scoring running on empty extraction; should be treated as void
- Melinda and Serena: No WS11 folder at all — consistent with their general absence from later worksheets (WS6/WS7/WS10 also missing)
- PDF source: `data_sources_2025/Worksheet11_ Feedbacks.pdf` EXISTS — but must verify that 2026 student pages are present before running OCR
- **Classification:** Source available (unverified for 2026 cohort pages); OCR extraction missing for all 13; Melinda and Serena: no worksheet administered (consistent pattern)
- **Recovery path blocker:** Verify that `Worksheet11_ Feedbacks.pdf` contains 2026 student responses. If confirmed: run OCR pipeline → run orchestrator `--llm-score` for WS11 items. If not confirmed: source is missing; report and stop.

### WS12 — `EXT_FAIL_NO_DATA` (13 students) / `NO_EXTRACTION_NO_OCR` (Melinda, Serena)

- OCR json: NONE in `ocr_output/` for any student
- extraction.json (13 students): EXISTS, status=fail, all 31 items = `(not_extracted)`
- scoring.json: MISSING for all (unlike WS11, scoring was never run)
- PDF source: `data_sources_2026/All Documents/21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf` EXISTS
- Item IDs: `DT_A_Q1`…`DT_G_Q2` — 31 items in both extraction_schema and rubric (consistent; no mapping conflict)
- Rubric: `rubrics/WS12_rubric.json` — 31 items, confirmed loadable. Note: `worksheets/WS12/` does NOT contain a `rubric.json` copy, but `rubrics/WS12_rubric.json` exists and is the authoritative file.
- Scoring path: `assess_worksheet_dt()` in `worksheet_assessor.py` (requires CODAP log features for cross-checking)
- **Classification:** Source available; OCR extraction missing for all 13 (Melinda/Serena: no worksheet administered, no log data).
- **Log features status (CONFIRMED):** `log_extractor.run()` against the April 21 Food CSV produces per-student records for all 13 active students. `final_accuracy` and `final_train_tp/tn/fp/fn` are derivable from `emit_snapshots` (last valid emit). All 13 students have non-zero emit counts. Melinda/Serena have 0 emits (consistent with no worksheet).
- **Recovery path blocker:** OCR must be run on `21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf` first. After OCR, run `python scripts/score_ws12.py` (script created and dry-run validated — bridges log features to `assess_worksheet_dt()` correctly). Requires ANTHROPIC_API_KEY.

### WS3 / WS4 — `EXT_FAIL_NO_DATA` despite OCR files existing (for non-Amy/Marco students)

- OCR json: EXISTS for 11/13 students (Amy and Marco missing)
- extraction.json: EXISTS for most students, status=fail, all items = `(not_extracted)`
- Confirmed data in OCR json: `Bruno_Worksheet3.json` contains real answers (e.g. "tavsiye edilemez")
- **Root cause:** The `extraction.json` items were never populated from the OCR output files. The site (`build_site_data.py`) reads `ocr_output/` directly via `read_ocr_worksheet()` and correctly displays the data. The scoring pipeline (`orchestrator.py`) reads from `extraction.json` which is empty.
- **Important:** The site data for WS3/WS4 is NOT broken — it reads directly from `ocr_output/` and shows real responses. Only the `extraction.json` pipeline artifacts are stale/empty.
- **Classification:** Output exists under alternate filename/location (ocr_output/ has data); extraction.json format mismatch; scoring blocked
- **Recovery path:** Create a migration script that reads `ocr_output/<student>/<student>_Worksheet3.json` and writes new extraction artifacts at a non-conflicting path (preserving original extraction.json unchanged), then run LLM scoring. Requires ANTHROPIC_API_KEY.

### Amy — WS1, WS3, WS4, WS5 (extraction.json fail, OCR json missing)

- WS1: extraction.json exists (status=fail, 0/11 items), no OCR json
- WS3: extraction.json exists (status=fail, 0/8 items), no OCR json
- WS4: extraction.json exists (status=fail, 0/5 items), no OCR json
- WS5: extraction.json exists (status=fail, 0/25 items), no OCR json
- All other worksheets (WS6, WS7, WS10, WS13, WS14): extraction complete and scored (WS13/WS14 pending scoring)
- **Classification:** Source material absent. `detect_student_page_ranges()` confirmed Amy's name is physically absent from all four combined class PDFs (WS1/WS3/WS4/WS5). Each PDF contains exactly 13 other students. This is not a pipeline error — Amy never submitted these worksheets.
- **Recovery path:** None. Do not attempt OCR. Do not create zero-score records.

### Marco — WS1, WS3, WS4, WS5 (same pattern as Amy)

- Same status as Amy for WS1/WS3/WS4/WS5
- **Classification:** Source material absent. `detect_student_page_ranges()` confirmed Marco is also physically absent from all four combined class PDFs.
- **Recovery path:** None. Same as Amy.

### Melinda and Serena — WS6, WS7, WS10, WS11, WS12 (no folder)

- WS1/WS3/WS4/WS5/WS13/WS14: extraction exists and passes
- WS6/WS7/WS10/WS11/WS12: no folder exists at all
- No OCR json in `ocr_output/` for WS6, WS7, WS10
- **Classification:** No worksheet administered, or data never collected — consistent across 5 worksheets (not a pipeline bug). This pattern suggests these students did not participate in the sessions requiring WS6/WS7/WS10/WS11/WS12.
- **Recovery path:** None — absence is consistent across multiple worksheets and both students. Do not create empty records.

### WS5 / Sheila — `REVIEW`

- extraction.json: status=partial, 7/25 items extracted
- scoring.json: total_score=0.0 / max_score (all items zero confidence)
- **Classification:** Partial extraction; scoring ran on incomplete data and produced zero. Needs researcher review of Sheila's WS5 submission.

### WS7 — `SCORE_ZERO_REVIEW` (Amy, Bruno, Helena, Marco, Marcus, Shana, Zara)

- extraction.json: status=pass, items extracted
- scoring.json: all item scores=0, all confidence=0
- **Classification:** Scoring artifact is stale or ran on mismatched data. Needs re-validation.

---

## Stage 3 — Artifacts Confirmed Unchanged

The following files were inspected but NOT modified during this diagnostic:

- All `students/*/WS*/extraction.json` files
- All `students/*/WS*/scoring.json` files
- All `ocr_output/*/` JSON files
- All source PDFs in `data_sources_2025/` and `data_sources_2026/`
- `worksheets/` and `rubrics/` bundles
- `mmla_explorer/` site files

---

## Stage 4 — Newly Created Files

- `scripts/score_ws13_ws14.py` — Scoring runner for WS13/WS14. Performs dry-run validation cleanly. Ready to run when ANTHROPIC_API_KEY is available. Does NOT touch any extraction.json.
- `scripts/score_ws12.py` — Scoring runner for WS12. Bridges log_extractor emit_snapshots to final_accuracy/final_train_* fields expected by assess_worksheet_dt(). Dry-run validated (13 students, log features confirmed). BLOCKED until OCR runs on the DT PDF. Does NOT touch any extraction.json.
- `scripts/recover_ws3_ws4_from_ocr.py` — Recovery script for WS3/WS4. Reads OCR json from ocr_output/, builds extraction_from_ocr.json (new file, never overwrites extraction.json), then runs LLM scoring. Dry-run validated: 13 students fully populated (8/8 WS3, 5/5 WS4). Amy/Marco skip (no OCR file). Existing void scoring.json are overwritten when --force is passed. Requires ANTHROPIC_API_KEY.

---

## Stage 5 — Recovery Priority and Blockers

| Priority | Task | Requires | Status |
|---|---|---|---|
| 1 | Run WS13/WS14 scoring (all 15 students) | ANTHROPIC_API_KEY | READY — run `python scripts/score_ws13_ws14.py` |
| 2 | WS11 — no 2026 source material | N/A | CONFIRMED BLOCKED — 2025-only PDF; no 2026 data exists |
| 3 | OCR for WS12 then score via assess_worksheet_dt | ANTHROPIC_API_KEY | BLOCKED on OCR; log features ready; run score_ws12.py after OCR |
| 4 | Amy/Marco WS1/WS3/WS4/WS5 | N/A | CONFIRMED BLOCKED — physically absent from all four PDFs |
| 5 | Re-score WS3/WS4 for 13 students from OCR output | ANTHROPIC_API_KEY | READY — run `python scripts/recover_ws3_ws4_from_ocr.py --force` |
| 6 | Review Sheila WS5 partial extraction | Researcher review | RESEARCHER ACTION NEEDED |
| 7 | Investigate WS7 all-zero scores for 7 students | Re-run orchestrator | PIPELINE ACTION — run `python orchestrator.py --all` |

---

## Stage 6 — Final Counts

| Worksheet | Complete | Score Missing | Extraction Fail | No Folder | Notes |
|---|---|---|---|---|---|
| WS1 | 13 | 0 | 2 (Amy, Marco) | 0 | |
| WS3 | 0 | 0 | 11 (stale ext) + 2 (no OCR) | 2 | OCR exists for 11; ext.json mismatch |
| WS4 | 0 | 0 | 11 (stale ext) + 2 (no OCR) | 2 | Same as WS3 |
| WS5 | 11 | 0 | 2 (Amy, Marco) | 2 | Sheila partial |
| WS6 | 13 | 0 | 0 | 2 | |
| WS7 | 8 | 0 | 0 | 2 | 5 zero-score need review |
| WS10 | 13 | 0 | 0 | 2 | |
| WS11 | 0 | 0 | 13 | 2 | OCR never ran; PDF source needs verification |
| WS12 | 0 | 0 | 13 | 2 | OCR never ran; scoring needs log features |
| WS13 | 0 | 15 | 0 | 0 | **Ready to score — run score_ws13_ws14.py** |
| WS14 | 0 | 15 | 0 | 0 | **Ready to score — run score_ws13_ws14.py** |
