# WS14 Recovery Plan
**Date:** 2026-10-10  
**Status:** Manual re-extraction complete (2026-10-10). All 6 flagged students have new `students/*/WS14/extraction.json` files created directly from physical PDF pages. Pre-scoring integrity checks passed for all 6. Bridge permanently blocked for these 6 students.

---

## 1. Bridge Skip/Overwrite Logic — Verified

The bridge's guard (in `bridge_student()`, lines 264–273 of `scripts/bridge_ocr_output.py`) is:

```python
if out_path.exists() and not force:
    existing_items = g1.get("items", {})
    already_filled = any(
        "(not_extracted)" not in str(v) and v
        for v in existing_items.values()
    )
    if already_filled:
        return "SKIP_ALREADY_FILLED"
```

**Behaviour confirmed against all 15 WS14 files:**

All 15 `students/*/WS14/extraction.json` files have every item set to `"(not_extracted)"`. Because no value passes the `already_filled` condition, **the bridge will proceed to write for all 15 students without `--force`**. No flag is needed to recover them.

This was verified by simulating the exact condition in Python against the live files.

---

## 2. Full 15-Student Verification Table

| Student | WS14 state | WS11 values | OCR id matches | Snapshot names student correctly | PDF check required |
|---|---|---|---|---|---|
| Amy | fail, 0/33 real | 33/33 real | Yes | Yes | **No** |
| Bruno | fail, 0/33 real | 33/33 real | Yes | Yes | **No** |
| Helena | fail, 0/33 real | 33/33 real | Yes | No (brief snapshot, no name in text) | **No** |
| Iris | fail, 0/33 real | 33/33 real | Yes | Yes | **No** |
| Irma | fail, 0/33 real | 33/33 real | Yes | No (brief snapshot, no name in text) | **No** |
| Isabel | fail, 0/33 real | 33/33 real | Yes | No (uses "Öğrenci" not name) | **No** |
| Marcus | fail, 0/33 real | 33/33 real | Yes | No (uses "Öğrenci" not name) | **No** |
| Melinda | fail, 0/33 real | 33/33 real | Yes | No (uses "Öğretmen adayı" not name) | **No** |
| Zara | fail, 0/33 real | 33/33 real | Yes | Yes | **No** |
| **Marco** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Melinda"** | **YES** |
| **Nadia** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Marcus"** | **YES** |
| **Shana** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Sheila"** | **YES** |
| **Sheila** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Serena"** | **YES** |
| **Ulysses** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Shana"** | **YES** |
| **Serena** | fail, 0/33 real | 33/33 real | Yes | **Snapshot names "Nadia"** | **YES** |

**Notes on "snapshot does not name student":** Helena, Irma, Isabel, Marcus, Melinda — their snapshots are either very short summary strings or use "Öğrenci"/"Öğretmen adayı" (student/teacher candidate) without any name. This is **not a mismatch** — the narrative simply didn't include the name. The `student_id` field in the OCR file is correct and DTI values are internally consistent. These 9 students do **not** require PDF verification.

---

## 3. Can the 6 Attribution Cases Be Verified From Artifacts Alone?

**Short answer: Partially, but not conclusively.**

### What the artifacts confirm

For all 6 flagged students, the `student_id` field in the OCR file matches the filename. The DTI_01 case counts are unique across all 15 students (no two students share the same count), making it unlikely that a mix-up occurred at the DTI-item level.

Additionally, the `page_notes` field contains student-specific physical observations that were recorded alongside the data extraction, suggesting the extractor was working from the correct physical page at the time.

### What the artifacts cannot confirm

The `ws_snapshot` field is an LLM-generated narrative. Its naming error means that at some point in the extraction pipeline, the wrong student name was used in the summary — but this could be a template substitution error rather than a page mix-up.

Without looking at the physical source PDF, it is not possible to rule out that pages were scanned in the wrong order or assigned to the wrong student pocket.

**Conclusion: Human inspection of the source PDF is required for the 6 flagged students. The artifacts are consistent with correct attribution but do not constitute independent verification.**

---

## 4. Source-PDF Verification Results (completed 2026-10-10)

PDF read directly. Page map confirmed: 10 pages per student, name in black box top-right of page 1.

| Student | PDF pages | PDF DTI_01 (physical page) | OCR DTI_01 (attributed file) | PASS/FAIL |
|---|---|---|---|---|
| **Marco** | pp. 71–80, DTI p74 | 10 cases, ~10% sick (1 sick, 9 healthy) | 15 cases, 80% sick | **FAIL** |
| **Nadia** | pp. 101–110, DTI p104 | 26 cases, 46.2% sick | 16 cases, 62.5% sick | **FAIL** |
| **Shana** | pp. 131–140, DTI p134 | 22 cases, 54.5% sick | 10 cases, 50% sick | **FAIL** |
| **Sheila** | pp. 121–130, DTI p124 | 10 cases, 50% sick | 24 cases, 41.7% sick | **FAIL** |
| **Ulysses** | pp. 81–90, DTI p84 | 30 cases, 33% sick | 22 cases, 54.5% sick | **FAIL** |
| **Serena** | pp. 111–120, DTI p114 | 24 cases, 41.7% sick | 26 cases, 46.2% sick | **FAIL** |

**All 6 students FAIL.** The OCR data in each student's `ocr_output/*/Worksheet_Xeno.json` was extracted from a different student's physical pages. The cross-attribution (inferred from snapshot names matching physical DTI values):

| OCR file (student_id) | Snapshot names | Physical source pages | Physical DTI_01 |
|---|---|---|---|
| `ocr_output/Marco/` | "Melinda" | pp. 61–70 (Melinda) | 15 cases, 80% sick |
| `ocr_output/Nadia/` | "Marcus" | pp. 91–100 (Marcus) | 16 cases, 62.5% sick |
| `ocr_output/Shana/` | "Sheila" | pp. 121–130 (Sheila) | 10 cases, 50% sick |
| `ocr_output/Sheila/` | "Serena" | pp. 111–120 (Serena) | 24 cases, 41.7% sick |
| `ocr_output/Ulysses/` | "Shana" | pp. 131–140 (Shana) | 22 cases, 54.5% sick |
| `ocr_output/Serena/` | "Nadia" | pp. 101–110 (Nadia) | 26 cases, 46.2% sick |

**Consequence: Bridging WS14 from these OCR files would write another student's data into each of the 6 flagged students' extraction files. The bridge must NOT run for these 6 students.**

Correct data for Marco and Ulysses (10 cases/~10% sick and 30 cases/33% sick respectively) is not present in any of the 15 OCR files — it was never extracted. Manual re-extraction or manual data entry from the physical PDF pages is required for all 6 students.

---

## 5. Dry-Run Recovery Plan

### Step 1 — Pre-flight dry run (already done, confirmed clean)

```bash
python scripts/bridge_ocr_output.py --worksheets WS14 --dry-run
```

Expected: 15 × "DRY_RUN: 33 items, 33 non-empty" — confirmed.

### Step 2 — Researcher completes PDF verification for the 6 flagged students

Use checklist in section 4 above. Record pass/fail per student.

### Step 3a — Run bridge for the 9 confirmed students (no PDF check needed)

After researcher approval, run with explicit student list:

```bash
python scripts/bridge_ocr_output.py \
    --worksheets WS14 \
    --students Amy Bruno Helena Iris Irma Isabel Marcus Melinda Zara
```

This writes 9 new `students/*/WS14/extraction.json` files from the Xeno OCR source. It does **not** affect WS11, WS13, WS_DT_INTRO, or any scoring files.

### Step 3b — Flagged students (BLOCKED — all 6 FAIL verification)

**Do not run the bridge for Marco, Nadia, Shana, Sheila, Ulysses, or Serena.**

Their `ocr_output/*/Worksheet_Xeno.json` files contain data extracted from the wrong physical pages. Running the bridge would populate WS14 with incorrect data. These 6 students require manual re-extraction directly from the source PDF (see Section 4 for page numbers and physical DTI values). This is a researcher task and cannot be automated from existing artifacts.

### Step 4 — Spot-check

After each run, verify one student's items match the WS11 values:

```python
# Confirm Amy WS14 items now match Amy WS11 items
import json
ws14 = json.load(open("students/Amy/WS14/extraction.json"))["gate_1_extraction"]["items"]
ws11 = json.load(open("students/Amy/WS11/extraction.json"))["gate_1_extraction"]["items"]
assert ws14 == ws11, "Mismatch"
```

### Step 5 — WS11 quarantine (separate future task, not yet)

Only after all WS14 files are confirmed. Do not execute now.

---

## 6. Files That Will Change

Only `students/*/WS14/extraction.json` (15 files, or fewer if some flagged students are deferred). The bridge creates a new envelope with `bridged_from`, `bridged_at`, `stage`, `student_id`, `worksheet`, and `gate_1_extraction.items`. The existing files — which are all-`(not_extracted)` pipeline stubs — will be fully replaced.

**Files NOT changed:** source OCR, WS11 extractions, WS13/WS_DT_INTRO extractions, all scoring files, rubrics, gold-standard data.
