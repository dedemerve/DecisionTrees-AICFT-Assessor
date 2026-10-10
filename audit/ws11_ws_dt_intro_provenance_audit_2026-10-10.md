# Provenance & Attribution Audit: WS11 and WS_DT_INTRO
**Date:** 2026-10-10  
**Scope:** WS11 (Worksheet_Xeno OCR files) and WS_DT_INTRO (21-28 Nisan DT files)  
**Purpose:** Investigation-only. No scoring performed. No frozen or gold-standard files modified.

---

## 1. Source Files Inspected

| File / Directory | Role |
|---|---|
| `ocr_output/*/Amy..Zara_Worksheet_Xeno.json` (15 files) | Per-student Xeno OCR extractions |
| `data_sources_2026/All Documents/07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf` | Source PDF for Xeno worksheet (48 MB, dated Jun 30 2026) |
| `data_sources_2025/Worksheet11_ Feedbacks.pdf` | 2025-cohort WS11 (read-only, FROZEN) |
| `ocr_output/*/21-28_nisan_2026_çalışma_kâğıdı_dt_raw.json` (15 files) | Per-student DT_INTRO extractions |
| `data_sources_2026/All Documents/21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf` | Source PDF for DT worksheet (22 MB, dated Jul 1 2026) |
| `rubrics/WS11_rubric.json` | WS11 expected item structure |
| `rubrics/WS14_rubric.json` | WS14 expected item structure |
| `rubrics/WS13_rubric.json` | WS13 expected item structure (DT_A_Q* items) |
| `students/*/WS11/extraction.json` (15 files) | What was bridged into WS11 directories |
| `students/*/WS13/extraction.json` (15 files) | Existing WS13 extractions |
| `students/*/WS_DT_INTRO/extraction.json` (15 files) | What was bridged into WS_DT_INTRO directories |

---

## 2. WS11 — Provenance Findings

### 2a. Critical mismatch: Xeno data is WS14, not WS11

The `Worksheet_Xeno.json` OCR files contain:
- Top-level field `"worksheet": "WS14"` (not WS11)
- Extraction items keyed `DTI_01..DTI_33`

The WS11 rubric (`rubrics/WS11_rubric.json`) defines an entirely different instrument:
- `ANKET_BOLUMU` (Q1–Q7, self-report survey, no score)
- `WS11_8a` — classification question from a food label
- `WS11_8b` — rule identification
- `WS11_Q10` — 8-item true/false grid
- `WS11_Q11` — 4-step ordering task
- `WS11_Q12` — 5-item boolean grid

No OCR file for any 2026 student contains these items. The bridge script incorrectly mapped `Worksheet_Xeno` → `students/*/WS11/`. The `students/*/WS11/extraction.json` files contain **WS14 data mislabeled as WS11**.

### 2b. The 2025 WS11 file

`data_sources_2025/Worksheet11_Feedbacks.pdf` is in the FROZEN 2025 cohort directory with different student pseudonyms (Ally, Barbara, Bob, Boris, …). It is not a 2026 source.

There is no 2026 WS11 (cognitive test) PDF or OCR output in the repository.

### 2c. Individual student attribution of Xeno/WS14 data

Each `{Student}_Worksheet_Xeno.json` file has `"student_id"` matching the filename. All 15 files show:
- Genuinely different DTI_01 case counts (10 to 37)
- Different threshold choices and confusion matrix values
- Student-specific `page_notes` describing physical handwriting observations

**DTI_01 case counts (root node training set size):**

| Student | Cases (DTI_01) | N (DTI_18) | WS14 attribution |
|---|---|---|---|
| Amy | 10 | 30 | Confirmed |
| Bruno | 26 | 26 | Confirmed |
| Helena | 10 | 20 | Confirmed |
| Iris | 37 | 37 | Confirmed |
| Irma | 10 | 30 | Confirmed |
| Isabel | 10 | 20 | Confirmed |
| Marco | 15 | 33 | Confirmed (see note) |
| Marcus | 10 | 20 | Confirmed |
| Nadia | 16 | 16 | Confirmed |
| Shana | 10 | 20 | Confirmed |
| Sheila | 24 | 24 | Confirmed |
| Ulysses | 22 | 32 | Confirmed |
| Zara | 10 | 25 | Confirmed |
| Melinda | 30 | 110 | Confirmed |
| Serena | 26 | 37 | Confirmed (see note) |

### 2d. ws_snapshot name mismatch — 6 files

Six files have `ws_snapshot` narratives that mention a different student's name:

| File (student_id) | Student named in snapshot | Explanation |
|---|---|---|
| Marco | "Melinda" | Narrative LLM error; DTI values and page_notes consistent with Marco |
| Nadia | "Marcus" | Narrative LLM error |
| Shana | "Sheila" | Narrative LLM error |
| Sheila | "Serena" | Narrative LLM error |
| Ulysses | "Shana" | Narrative LLM error |
| Serena | "Nadia" | Narrative LLM error |

**Evidence that DTI extraction is correctly attributed despite snapshot naming errors:**
1. Each file has `student_id` set to the filename student.
2. Each file has genuinely different DTI_01 content (no duplicates across all 15).
3. `page_notes` contain student-specific physical observations (e.g., Serena's notes describe an inconsistency between root count and confusion matrix N, which is confirmed by her own DTI values: DTI_01=26, DTI_18=37).

The ws_snapshot is an LLM-generated narrative field. The naming errors in this field do not affect the extraction data. However, this cannot be verified against the source PDF pages without manual page-by-page comparison.

**Status of 6 mismatched students:** PLAUSIBLE but not independently verified against source PDF.

---

## 3. WS_DT_INTRO — Attribution Findings

### 3a. Files are student-specific, not a shared class file

The `21-28_nisan_2026_çalışma_kâğıdı_dt_raw.json` files vary in size (1591–2668 bytes) and all have different content. DTI_A_Q1 values differ across all 15 students. These are individual student responses extracted from the DT worksheet.

### 3b. WS_DT_INTRO is byte-identical to WS13

Comparing `students/*/WS13/extraction.json` with `students/*/WS_DT_INTRO/extraction.json` for all 15 students:

- Both have 31 items keyed `DT_A_Q1..DT_G_Q2`
- All 15 student pairs are **byte-identical** (0 differences)
- Both source from the same OCR file: `21-28_nisan_2026_çalışma_kâğıdı_dt_raw.json`

**The `WS_DT_INTRO` directory is a duplicate of the `WS13` directory.** There is no additional data to extract or score.

### 3c. WS13 scoring status

| Student | WS13 scored? | Total |
|---|---|---|
| Amy | Yes | 9.0/31 |
| Bruno | Yes | 13.5/31 |
| Helena | Yes | 8.5/31 |
| Iris | Yes | 11.0/31 |
| Irma | Yes | 12.0/31 |
| Isabel | Yes | 14.5/31 |
| Marco | Yes | 7.5/31 |
| Marcus | Yes | 6.0/31 |
| Nadia | Yes | 13.0/31 |
| Shana | Yes | 8.5/31 |
| Sheila | Yes | 9.0/31 |
| Ulysses | Yes | 11.5/31 |
| Zara | Yes | 13.0/31 |
| **Melinda** | **Missing** | — |
| **Serena** | **Missing** | — |

---

## 4. Confirmed / Unresolved / Unsupported Cases

### WS11

| Status | Students | Finding |
|---|---|---|
| **Unsupported** | All 15 | No 2026 WS11 (cognitive test) OCR data exists. The WS11 rubric items are not present in any 2026 OCR file. |
| **Mislabeled** | All 15 | `students/*/WS11/extraction.json` contains WS14 data. The bridge mapped the wrong worksheet. |
| **Confirmed (WS14)** | Amy, Bruno, Helena, Iris, Irma, Isabel, Marcus, Shana, Zara, Melinda | ws_snapshot attribution matches student_id |
| **Plausible (WS14)** | Marco, Nadia, Shana, Sheila, Ulysses, Serena | ws_snapshot names a different student; DTI data and page_notes are internally consistent with the file's student_id but cannot be independently verified without source PDF comparison |

### WS_DT_INTRO

| Status | Students | Finding |
|---|---|---|
| **Confirmed duplicate** | All 15 | WS_DT_INTRO extraction == WS13 extraction. No new data. |
| **WS13 scored** | Amy, Bruno, Helena, Iris, Irma, Isabel, Marco, Marcus, Nadia, Shana, Sheila, Ulysses, Zara | Already scored. |
| **WS13 missing score** | Melinda, Serena | WS13 extraction exists; scoring not yet run. |

---

## 5. Ready for Scoring?

### WS11: **No.**

Reasons:
1. No 2026 WS11 cognitive-test OCR data exists in this repository.
2. The `students/*/WS11/extraction.json` files contain WS14 data, not WS11 data.
3. WS11 is an interpretive instrument (survey + cognitive test) — exact-match scoring cannot substitute for its rubric.
4. Even if the Xeno/WS14 data were correctly labeled, WS14 scoring has not been implemented yet.

### WS_DT_INTRO: **No — and not needed.**

Reasons:
1. WS_DT_INTRO is identical to WS13 for all 15 students.
2. WS13 is already scored for 13 students.
3. Scoring WS_DT_INTRO would produce duplicate results.

---

## 6. Recommended Next Actions

### For WS11:
1. **Search for 2026 WS11 source material.** Check `data_sources_2026/All Documents/` — no "Worksheet 11" or equivalent cognitive test PDF exists there. If it was not collected in 2026, mark WS11 as **not administered to 2026 cohort**.
2. **Correct the bridge mapping.** The `WS11` pattern in `bridge_ocr_output.py` should map to `WS14`, not `WS11`. The `students/*/WS11/extraction.json` files should be moved or relabeled.
3. **Resolve the 6 ws_snapshot mismatches.** Manually compare the 6 affected students' DTI data against the source PDF (`07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf`) to confirm page-to-student mapping. Do not score WS14 for those students until confirmed.
4. **Do not score WS14** in this pipeline until the rubric is validated and the attribution for the 6 flagged students is resolved.

### For WS_DT_INTRO:
1. **Score WS13 for Melinda and Serena.** Their extraction data is in both `students/Melinda/WS13/extraction.json` and `students/Melinda/WS_DT_INTRO/extraction.json` (identical). The existing `score_ws13.py` script should be run for those two students.
2. **Remove or mark WS_DT_INTRO as redundant.** The directory serves no additional purpose.
3. **Do not create separate WS_DT_INTRO scores** — this would duplicate WS13.

---

## 7. Files NOT Modified by This Audit

This investigation is read-only. The following were inspected but not changed:
- All `ocr_output/*/` files
- All `students/*/WS11/` files
- All `students/*/WS_DT_INTRO/` files
- All `data_sources_2025/` files (FROZEN)
- All `data_sources_2026/` files
- All rubric files
