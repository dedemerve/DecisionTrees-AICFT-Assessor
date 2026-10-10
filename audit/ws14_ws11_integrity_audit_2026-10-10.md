# WS14 Completeness and WS11 Disposition Audit
**Date:** 2026-10-10  
**Scope:** WS14 extraction completeness, bridge correction impact, WS11 file disposition  
**Status:** Read-only investigation. No files modified.

---

## 1. WS14 Current State

### 1a. How the current WS14 files were created

All 15 `students/*/WS14/extraction.json` files were created by a prior **direct OCR pipeline run** (not the bridge), as shown by their metadata:

```
"stage": "extraction",
"ocr_model": "claude-sonnet-5",
"extracted_at": "2026-10-10T10:04:...",
"status": "fail"
```

That pipeline run set all 33 DTI_* items to `(not_extracted)`. There is no `bridged_from` field. The OCR pipeline could not extract content and produced a failed envelope.

### 1b. Item completeness

| Student | Items present | Missing | Not-extracted | Bridge would change |
|---|---|---|---|---|
| Amy | 33/33 | 0 | **33** | 33 values |
| Bruno | 33/33 | 0 | **33** | 33 values |
| Helena | 33/33 | 0 | **33** | 33 values |
| Iris | 33/33 | 0 | **33** | 33 values |
| Irma | 33/33 | 0 | **33** | 33 values |
| Isabel | 33/33 | 0 | **33** | 33 values |
| Marco | 33/33 | 0 | **33** | 33 values |
| Marcus | 33/33 | 0 | **33** | 33 values |
| Nadia | 33/33 | 0 | **33** | 33 values |
| Shana | 33/33 | 0 | **33** | 33 values |
| Sheila | 33/33 | 0 | **33** | 33 values |
| Ulysses | 33/33 | 0 | **33** | 33 values |
| Zara | 33/33 | 0 | **33** | 33 values |
| Melinda | 33/33 | 0 | **33** | 33 values |
| Serena | 33/33 | 0 | **33** | 33 values |

**Conclusion:** The keys DTI_17, DTI_21, DTI_23, DTI_24, DTI_33 are structurally present in all 15 files (0 missing keys) but carry `(not_extracted)` values, as do all other 28 items. The earlier concern about "5 missing items" was based on bridging the old `WS11` output, which did produce 33 real values — but into the wrong directory. The current `WS14` files are empty extraction stubs.

### 1c. What the corrected bridge would do

Dry-run of `bridge_ocr_output.py --worksheets WS14` confirms:

- Source: `ocr_output/{student}/{student}_Worksheet_Xeno.json`
- Output: 33 items, 33 non-empty, for all 15 students
- No new item keys — same 33 DTI_* keys already in the files
- Only effect: replaces 33 × 15 = 495 `(not_extracted)` values with real student responses
- Adds `bridged_from` and `bridged_at` metadata to each envelope
- Does not change `student_id`, `worksheet`, or any existing metadata

**The bridge update is value-only, not structural.** It is safe to apply once attribution is confirmed.

---

## 2. ws_snapshot Attribution Checklist for 6 Flagged Students

Six OCR files have an LLM-generated `ws_snapshot` narrative that names a different student. The extraction items and `page_notes` are internally consistent with the `student_id` field. The mismatch is in the narrative text only.

### Mismatch table

| File student_id | Student named in snapshot | DTI_01 value in file | Snapshot excerpt |
|---|---|---|---|
| **Marco** | Melinda | "15 tane vaka içermektedir. 12 tanesi hasta, 3 tanesi sağlıklıdır. %80'i hastadır." | "Melinda'nın veri seti 15 vaka içeriyor (12 hasta, 3 sağlıklı); mavi saçlı 3 vaka %0 hasta…" |
| **Nadia** | Marcus | "16 vaka, %62,5, çoğunluk hastadır" | "Marcus'un Xeno veri seti 16 vaka içeriyor (%62,5 hasta): 6 mavi saçlı (hepsi sağlıklı) ve 10 pembe saçlı…" |
| **Shana** | Sheila | "10 kişi var, %50'si hasta. Hasta ve sağlıklı oranı aynı" | "Sheila's Xeno dataset had 10 training cases with 50% sick, split cleanly by hair color…" |
| **Sheila** | Serena | "24 vaka içermekte %41.7 si hasta" | "Serena'nın Xeno veri setinde toplam 24 vaka bulunmakta (14 mavi saçlı, 10 pembe saçlı)…" |
| **Ulysses** | Shana | "22 vaka içermekte. %54,5 hasta. Hastaların yarıdan fazlası hasta" | "Shana'nın Xeno veri setinde toplam 22 vaka kök düğümde (%54,5 hasta), 10 mavi saçlı (%0 hasta) ve 12…" |
| **Serena** | Nadia | "Kök düğüm 26 vaka içermekte. %46,2 sick" | "Nadia's Xeno dataset had 26 cases at the root (%46,2 sick); the tree used hair color as predictor…" |

**Key observation:** In every case the snapshot narrative describes the same DTI_01 values that appear in the DTI extraction of that file. The mismatch is that the LLM used the wrong name in the narrative — the numbers were taken from the correct student's worksheet.

### Source-PDF verification checklist

For each flagged student, the researcher should:

1. Open `data_sources_2026/All Documents/07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf`
2. Locate the physical worksheet page belonging to the named student (by handwriting, name tag, seat position, or class roster)
3. Verify the root-node case count (DTI_01 value) against the value recorded below

| File student_id | DTI_01 to verify on physical page | DTI_18 (total N) | Additional check |
|---|---|---|---|
| Marco | 15 cases, 12 sick (80%) | 33 | Page_notes are blank — no distinguishing handwriting observations |
| Nadia | 16 cases, 62.5% sick | 16 | Page_notes mention strikethrough on page 4 and doodles in formula boxes |
| Shana | 10 cases, 50% sick | 20 | Page_notes: fast cursive handwriting, partly illegible metric table |
| Sheila | 24 cases, 41.7% sick | 24 | Page_notes: MCR table blank (page 9); silik (faded) scan areas |
| Ulysses | 22 cases, 54.5% sick | 32 | Page_notes: DTI_05 (row 5) left blank on page 4 |
| Serena | 26 cases, 46.2% sick (root count and confusion matrix N=37 inconsistent) | 37 | Root count (26) vs confusion matrix N (37) inconsistency noted in page_notes |

**PDF verification result (completed 2026-10-10):** All 6 students FAIL. Physical DTI_01 values do not match OCR DTI_01 values for any of the 6. Full cross-attribution confirmed — see `audit/ws14_recovery_plan_2026-10-10.md` Section 4.

**Consequence:** The bridge must NOT run for these 6 students. Their OCR source files are corrupted (contain data from wrong physical pages). Manual re-extraction from the source PDF is required.

---

## 3. WS11 File Inventory and Disposition

### 3a. Content summary

All 15 `students/*/WS11/extraction.json` files:

- Have `status: pass` and `bridged_from: ocr_output/{student}/{student}_Worksheet_Xeno.json`
- Contain 33 DTI_* items with real student values (not `not_extracted`)
- Are **byte-for-byte identical** to what `bridge_ocr_output.py --worksheets WS14` would produce
- Contain no unique information beyond what is in the original OCR files

### 3b. Comparison with WS14 source

| Dimension | WS11/extraction.json | WS14/extraction.json | OCR source |
|---|---|---|---|
| Item keys | DTI_01..DTI_33 (33) | DTI_01..DTI_33 (33) | DTI_01..DTI_33 (33) |
| Item values | Real OCR values | All `(not_extracted)` | Real values |
| Status | pass | fail | n/a |
| bridged_from | Xeno OCR file | absent | n/a |
| Unique data | **None** | **None** | Authoritative |

### 3c. Recommended disposition

**The WS11 files are fully reproducible bridge artifacts.** They contain no unique evidence. The authoritative source is `ocr_output/*/Worksheet_Xeno.json`.

Recommended sequence (do not execute yet):

1. Run `bridge_ocr_output.py --worksheets WS14` to populate WS14 with correct values.
2. Verify WS14 extractions match WS11 item-for-item (already confirmed in dry-run).
3. Only after WS14 is complete and researcher has reviewed the 6 attribution cases: quarantine the WS11 directories by renaming them to `WS11_MISLABELED_WAS_WS14/` or moving to an `archive/` subdirectory.
4. Do not delete the files at this stage — they serve as a cross-check until WS14 is fully operational.

**Current status: preserve. No action taken.**

---

## 4. Files Inspected (Read-Only)

| File | Finding |
|---|---|
| `students/*/WS14/extraction.json` (15 files) | All items `(not_extracted)`, status=fail, from pipeline OCR run |
| `students/*/WS11/extraction.json` (15 files) | 33 real values each, bridged from Xeno OCR, fully reproducible |
| `ocr_output/*/Worksheet_Xeno.json` (15 files) | Authoritative source; 33 DTI items with real content each |

No files were modified by this audit.
