"""
ocr_pipeline.py

Transcribes handwritten Turkish pre-service teacher worksheets using Claude vision,
maps each answer to a rubric item_id, and saves a single student bundle JSON
that feeds directly into worksheet_assessor.py.

Modes
-----
dry_run   No API calls. Converts PDFs to images, saves for inspection.
          python ocr_pipeline.py dry_run [WorksheetDT.pdf ...]

pilot     One student from one PDF. Prints item-by-item response summary.
          python ocr_pipeline.py pilot WorksheetDT.pdf 0
          (student_index is the 0-based position among detect_student_page_ranges()
          groups for that PDF — page spans vary per student, see dry_run output.)

validate  Human-readable review of a student's bundle (combined responses).
          python ocr_pipeline.py validate Daniella

full      Process all three PDFs. Skips students already processed (resume-safe).
          python ocr_pipeline.py

Output per student
------------------
students/{student_key}/
  WS1.json, WS3.json, ... WS_DT.json   — per-worksheet pipeline sections
  portfolio.json                       — AI-CFT rollup
  worksheet_dt_raw.json
  worksheets_1_10_raw.json
  worksheet11__feedbacks_raw.json
  _images/                 -- page images saved by dry_run only

Student key
-----------
Names from Claude are normalized: stripped, title-cased, spaces → underscores.
"daniella", "DANIELLA", "Daniella" all resolve to the same key "Daniella".
Keys are stable across PDF runs so the same student's data always merges correctly.

data_sufficiency encoding
-------------------------
Sentinel values:
  (bos)               student left the field blank
  (okunamiyor)        text is present but illegible
  (missing)           Claude did not return this key
  (not_extracted)     PDF was not processed for this student
  (transcription_error) API call failed for this PDF
Any other value is a real answer. is_answered() encodes this contract.
"""

from __future__ import annotations

import base64
import json
import os
import re
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Optional

import anthropic
from datetime import datetime, timezone
from pdf2image import convert_from_path
from PIL import Image, ImageEnhance, ImageFilter

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

DATA_DIR = Path(__file__).parent / "data_sources_2026" / "All Documents"
OUT_DIR = Path(__file__).parent / "ocr_output"
OUT_DIR.mkdir(exist_ok=True)

DPI = 300  # raised from 200; improves handwriting legibility

PAGES_PER_STUDENT: dict[str, int] = {
    # 2025
    "WorksheetDT.pdf": 4,
    "Worksheets1-10.pdf": 6,
    "Worksheet11_ Feedbacks.pdf": 3,
    # 2026 — per-worksheet PDFs
    "21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf": 4,
    "24 Mart 2026 Çalışma Kâğıdı 1.pdf": 1,
    "24 Mart 2026 Çalışma Kâğıdı 3.pdf": 1,
    "24 Mart 2026 Çalışma Kâğıdı 4.pdf": 1,
    "24 Mart 2026 Çalışma Kâğıdı 5.pdf": 1,
    "31 Mart 2026 Çalışma Kâğıdı 6.pdf": 1,
    "31 Mart 2026 Çalışma Kâğıdı 7.pdf": 1,
    "31 Mart 2026 Çalışma Kâğıdı 10.pdf": 1,
    "07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf": 10,
    "07 Nisan 2026 Çalışma Kâğıdı Titanic.pdf": 10,
}

# ---------------------------------------------------------------------------
# Student pseudonyms — canonical identifiers used as directory keys
# ---------------------------------------------------------------------------

# Complete pseudonym list provided by researcher.
# These are the only valid student keys; Claude-extracted names are matched against this set.
KNOWN_PSEUDONYMS: frozenset[str] = frozenset({
    # 2026 cohort (15 students)
    "Amy", "Bruno", "Helena", "Isabel", "Irma", "Iris",
    "Marco", "Marcus", "Melinda", "Nadia", "Serena",
    "Sheila", "Shana", "Ulysses", "Zara",
    # 2025 cohort (kept for validate mode on archived data)
    "Ozzy", "Ally", "Bella", "Bob", "Daisy", "Daniella", "David",
    "Eliot", "Henry", "Irene", "Karl", "Michael", "Mike",
    "Nicolas", "Zabby", "Adam", "Eddy", "Aden", "Barbara", "Boris",
    "Calvin", "Darby", "Demi", "Daryl", "Edgar", "Frank", "Felicity",
    "Kim", "Sabrina",
})

# Page groups are detected from each PDF's embedded name-banner text layer
# (see detect_student_page_ranges), not from a fixed page count. PAGES_PER_STUDENT
# below is kept only as an expected-span hint for flagging anomalous groups.

NO_ANSWER_SENTINELS: frozenset[str] = frozenset({
    "(bos)", "(okunamiyor)", "(missing)", "(not_extracted)", "(transcription_error)",
})

from pipeline_schema import (
    ALL_ITEM_IDS,
    ITEM_IDS_DT,
    ITEM_IDS_WS,
    ITEM_IDS_WS1,
    ITEM_IDS_WS11,
    PDF_ITEM_IDS,
    WORKSHEET_ITEM_IDS,
    WORKSHEET_PDF_SOURCE,
    WORKSHEETS_1_10_PAGE_INDEX,
    calibration_bundle_dir,
    layout_manifest_path,
    pdf_to_images_stem,
)

OCR_OUTPUT_DIR = Path(__file__).parent / "ocr_output"

# ---------------------------------------------------------------------------
# Item ID master list — defined in pipeline_schema.py (single source of truth)
# ---------------------------------------------------------------------------

# WS6 uses dt_vision_pipeline for structural tree extraction in addition to text OCR.
WS6_VISION_ENABLED: bool = True

# ---------------------------------------------------------------------------
# Vision prompts
# ---------------------------------------------------------------------------

_HANDWRITING_INSTRUCTION = """HANDWRITING READING — read carefully before transcribing:

1. These pages are handwritten by Turkish pre-service teachers. Writing style varies from neat to
   very fast and cursive. Assume every filled field contains a real answer unless physically blank.

2. Turkish character restoration — pre-service teachers often skip diacritics when writing fast.
   Restore unambiguously:
   c  → ç   (e.g. "cok" = "çok", "kac" = "kaç")
   s  → ş   (e.g. "su" context-dependent; "seker" = "şeker", "esik" = "eşik")
   g  → ğ   (e.g. "agac" = "ağaç", "degisken" = "değişken", "ogrenci" = "öğrenci")
   u  → ü   (e.g. "gul" = "gül", "ustte" = "üstte")
   o  → ö   (e.g. "ozellik" = "özellik", "once" = "önce")
   i  → ı   (e.g. "kisi" = "kişi" or "kısı" — use context)
   If the domain word is technical (MCR, sensitivity, threshold, eşik, değişken, doğruluk,
   duyarlılık, hata oranı) restore it fully even if written informally.

3. Numbers — common misreads in fast handwriting:
   0 vs O: in numeric contexts always read as zero
   1 vs l/I: in formulas/equations always read as one
   7 vs 1: 7 has a horizontal stroke; 1 does not
   Decimal separator: Turkish pre-service teachers use comma (0,82) not period — transcribe as written.

4. Struck-through / overwritten text: transcribe only the FINAL version (what is not crossed out).
   If both old and new are readable, use the new; note it as "[corrected: old → new]".

5. Symbols and layout marks:
   Arrow (→ or drawn): write [arrow]
   Circle around a number or letter: write [circled: X]
   Underline for emphasis: transcribe the underlined text normally (do not mark it)
   Formula fraction (numerator over denominator): write as "numerator / denominator"

6. Marginal additions: if a pre-service teacher wrote something in the margin clearly belonging to an answer,
   include it at the end of that answer, separated by " | "."""

_SENTINEL_INSTRUCTION = """BLANK / ILLEGIBLE FIELDS — strict rules:
- Pre-service teacher left the field completely empty (no marks at all): write exactly (bos)
- There is handwriting but it is physically unreadable after careful inspection: write exactly (okunamiyor)
- NEVER guess, paraphrase, or invent content for blank or illegible fields.
- Do NOT write a translation. Transcribe Turkish text as Turkish."""

_NAME_INSTRUCTION = """PRE-SERVICE TEACHER PSEUDONYM — this is critical for file organization:
The pre-service teacher's pseudonym (nickname) is written at the top of the FIRST page, usually in a
"Name:" or "Ad:" or "Öğretmen Adayı:" field, or freely at the top of the page.
These are single English-style nicknames such as: Amy, Bruno, Helena, Isabel, Irma, Iris,
Marco, Marcus, Melinda, Nadia, Serena, Sheila, Shana, Ulysses, Zara.
Read the name exactly as written. If unclear, read the closest match from this list."""

PROMPT_DT = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe one pre-service teacher's completed CODAP Arbor decision tree worksheet.

You will receive 4 page images belonging to ONE pre-service teacher (one pseudonym folder). Treat all 4 pages as one document.
The worksheet has 7 sections labelled A through G (4 pages total).

CRITICAL — printed question numbers do NOT always equal rubric item suffixes.
Use the section headings and question text below to assign each answer to the correct key.
Never shift an answer from one section into another item_id.

Page layout (typical):
  Page 1 — Section A (Q1–Q4), Section B begins (Q1–Q2)
  Page 2 — Section B continues (Q3–Q4), Section C (action + Q2–Q3), Section D begins (Q1)
  Page 3 — Section D continues (Q2–Q4), Section E (metric blanks + Q1–Q3)
  Page 4 — Section E Q4, Section F (test EMIT Q1–Q2), Section G (reflection Q1–Q2)

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WHAT TO EXTRACT — return exactly these JSON keys with verbatim pre-service teacher answers:

"student_name"
  The pseudonym written at the top of page 1.

--- SECTION A (prior beliefs and data exploration) ---
"DT_A_Q1"  Section A Q1 — which variable(s) might predict recommendation BEFORE analysis (prior belief).
"DT_A_Q2"  Section A Q2 — which variable(s) affect recommendation based on data/graphs explored in CODAP.
"DT_A_Q3"  Section A Q3 — is there a meaningful difference between recommended and not-recommended foods? Explain.
"DT_A_Q4"  Section A Q4 — which variable would you use FIRST in a model AND why (both choice and justification).

--- SECTION B (three single-level trees) ---
"DT_B_Q1"  Section B Q1 — EMIT output after first single-variable tree (variable, threshold, TP, FP, TN, FN, metrics).
"DT_B_Q2"  Section B Q2 — EMIT output after second single-variable tree (different variable from B_Q1).
"DT_B_Q3"  Section B Q3 — EMIT output after third single-variable tree (different variable from B_Q1 and B_Q2).
"DT_B_Q4"  Section B Q4 — which variable performed best and what criteria were used to decide.

--- SECTION C (threshold tuning on best single-level tree) ---
"DT_C_Q1"  Section C action block — EMIT output after recalling the best tree and varying its threshold.
             Look for recorded counts/metrics near the Section C instructions, before printed Q2.
"DT_C_Q2"  Section C printed Q2 — how changing threshold values affects tree performance.
"DT_C_Q3"  Section C printed Q3 — which threshold value best separates classes and how you found it.

--- SECTION D (two-level tree) ---
"DT_D_Q1"  Section D action block — EMIT output after adding a second variable to create a 2-level tree.
"DT_D_Q2"  Section D printed Q2 — did the second variable improve classification? How?
"DT_D_Q3"  Section D printed Q3 — which variable combination gave the best result?
"DT_D_Q4"  Section D printed Q4 — how did you decide you reached the best tree (stopping criterion)?

--- SECTION E (evaluate best 2-level tree) ---
"DT_E_TP"                  Section E — true positive (TP) definition if written on the sheet.
"DT_E_FP"                  Section E — false positive (FP) definition if written on the sheet.
"DT_E_sensitivity_formula" Section E — sensitivity formula as text (e.g. TP/(TP+FN)).
"DT_E_MCR_formula"         Section E — MCR formula as text (e.g. (FP+FN)/N).
"DT_E_sensitivity"         Numeric sensitivity (duyarlılık) value filled in the Section E metric blank.
"DT_E_MCR"                 Numeric MCR (hata oranı) value filled in the Section E metric blank.
"DT_E_Q1"  Section E Q1 — which metric matters most for this model's purpose and why.
"DT_E_Q2"  Section E Q2 — did the model make more false positives or false negatives?
"DT_E_Q3"  Section E Q3 — when should software stop building the tree?
"DT_E_Q4"  Section E Q4 — can decision trees achieve perfect classification (zero errors)? Answer + reason.

--- SECTION F (apply tree to test data) ---
"DT_F_Q1"  Section F Q1 — EMIT output when applying the best tree to the TEST dataset.
"DT_F_Q2"  Section F Q2 — compare test vs training performance; explain any difference (overfitting).

--- SECTION G (reflection) ---
"DT_G_overfitting"    Section G — overfitting definition if written on the sheet.
"DT_G_DT_definition"  Section G — decision tree definition if written on the sheet.
"DT_G_Q1"  Section G Q1 — what did the decision tree MODEL learn from the data?
"DT_G_Q2"  Section G Q2 — what did the pre-service teacher learn while building decision trees?

"page_notes"
  Brief note about image quality, pages that were very hard to read, or unusual layout.
  Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "DT_A_Q1": "...",
  "DT_A_Q2": "...",
  "DT_A_Q3": "...",
  "DT_A_Q4": "...",
  "DT_B_Q1": "...",
  "DT_B_Q2": "...",
  "DT_B_Q3": "...",
  "DT_B_Q4": "...",
  "DT_C_Q1": "...",
  "DT_C_Q2": "...",
  "DT_C_Q3": "...",
  "DT_D_Q1": "...",
  "DT_D_Q2": "...",
  "DT_D_Q3": "...",
  "DT_D_Q4": "...",
  "DT_E_TP": "...",
  "DT_E_FP": "...",
  "DT_E_sensitivity_formula": "...",
  "DT_E_MCR_formula": "...",
  "DT_E_sensitivity": "...",
  "DT_E_MCR": "...",
  "DT_E_Q1": "...",
  "DT_E_Q2": "...",
  "DT_E_Q3": "...",
  "DT_E_Q4": "...",
  "DT_F_Q1": "...",
  "DT_F_Q2": "...",
  "DT_G_overfitting": "...",
  "DT_G_DT_definition": "...",
  "DT_G_Q1": "...",
  "DT_G_Q2": "...",
  "page_notes": "..."
}}"""

PROMPT_WS = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe every blank from ProDaBi decision tree worksheets WS1, WS3, WS4, WS5,
WS6, WS7, and WS10. You will receive multiple page images belonging to ONE pre-service teacher (one pseudonym folder).

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET STRUCTURE — each worksheet is a printed form with numbered blanks.
Read each worksheet header and its numbered blanks. Extract exactly what the pre-service teacher wrote
in each blank. Do not interpret or summarise — transcribe verbatim.

BLANKS TO EXTRACT:

--- WORKSHEET 1: Önemli Terimler (Important Terms) ---
WS1 has eleven numbered items (printed 1–11): diagram callouts 1–4 and paragraph fill-ins 5–11.
Transcribe short answers verbatim — not full definitions.
"WS1_B1"  Item 1 (diagram) — etiket / label for recommendation outcome (e.g. tavsiye edilemez)
"WS1_B2"  Item 2 (diagram) — nesne (object); may point to Fındıklı Gofret
"WS1_B3"  Item 3 (diagram) — özellik / karakteristik / değişken (nutrient-name column)
"WS1_B4"  Item 4 (diagram) — değer / özelliğin değeri (numeric value column)
"WS1_B5"  Item 5 (paragraph) — nesne
"WS1_B6"  Item 6 (paragraph) — nesne
"WS1_B7"  Item 7 (paragraph) — özellik / karakteristik / değişken
"WS1_B8"  Item 8 (paragraph) — feature count (7 or yedi only)
"WS1_B9"  Item 9 (paragraph) — list of nutrient/feature names from the table
"WS1_B10" Item 10 (paragraph) — example food object name (e.g. Fındıklı Gofret)
"WS1_B11" Item 11 (paragraph) — etiket / etiket olarak (label role for recommendation)

--- WORKSHEET 3: Eşik Uygulama (Applying Thresholds) ---
WS3 has 8 blanks. Pre-service teachers apply a threshold rule to classify foods as recommended/not.
"WS3_B1"  Blank 1 — first classification result or rule
"WS3_B2"  Blank 2
"WS3_B3"  Blank 3
"WS3_B4"  Blank 4
"WS3_B5"  Blank 5
"WS3_B6"  Blank 6
"WS3_B7"  Blank 7 — likely involves threshold notation (≤, ≥, <, >)
"WS3_B8"  Blank 8 — likely involves threshold notation

--- WORKSHEET 4: En İyi Eşik (Best Threshold) ---
WS4 has 5 blanks aligned to threshold-search tasks on food cards.
"WS4_B1"  Blank 1 — new threshold line between avocado and french fries (visual or written)
"WS4_B2"  Blank 2 — four misclassified foods marked or written (jelibon, kraker, yulaf, avokado)
"WS4_B3"  Blank 3 — states misclassification decreased after new threshold
"WS4_B4"  Blank 4 — agrees Pia is haklı because apple and raspberry jam have same fat value
"WS4_B5"  Blank 5 — energy threshold learned (numeric, 160–2223 range)

--- WORKSHEET 5: Eşik Dene (Try Thresholds — 25 blanks) ---
WS5 grid on 11 ProDaBi food data cards (salatalık … sütlü çikolata). Each filled row
uses four cells: threshold expression, correct count, error count, MCR (errors/11).
Rows map B1–B4 (row 1), B5–B8 (row 2), … B21–B24 (optional row 6); B25 = final choice.
Transcribe threshold operators EXACTLY as written (≤, ≥, <, >, <=, >=) — do not normalise.
Counts and MCR are integers/decimals only (no formulas).
"WS5_B1"  Blank 1
"WS5_B2"  Blank 2
"WS5_B3"  Blank 3
"WS5_B4"  Blank 4
"WS5_B5"  Blank 5
"WS5_B6"  Blank 6
"WS5_B7"  Blank 7
"WS5_B8"  Blank 8
"WS5_B9"  Blank 9
"WS5_B10" Blank 10
"WS5_B11" Blank 11
"WS5_B12" Blank 12
"WS5_B13" Blank 13
"WS5_B14" Blank 14
"WS5_B15" Blank 15
"WS5_B16" Blank 16
"WS5_B17" Blank 17
"WS5_B18" Blank 18
"WS5_B19" Blank 19
"WS5_B20" Blank 20
"WS5_B21" Blank 21
"WS5_B22" Blank 22
"WS5_B23" Blank 23
"WS5_B24" Blank 24
"WS5_B25" Blank 25 — final choice: threshold with lowest yanlış sınıflandırma count from grid

--- WORKSHEET 6: Karar Ağacı Çiz (Draw a Decision Tree — 13 blanks) ---
WS6: two-level decision tree on the same 11 ProDaBi food cards as WS5.
Transcribe labels, thresholds, and leaf class names exactly (≤, ≥, <, >).
"WS6_B1"  Blank 1 — root node feature (şeker, yağ, enerji, …)
"WS6_B2"  Blank 2 — root threshold with operator (transcribe ≤, ≥, <, > exactly as written)
"WS6_B3"  Blank 3 — evet branch label (e.g. evet (≤ 10))
"WS6_B4"  Blank 4 — hayır branch label (e.g. hayır (> 10) or hayır (≥ 10))
"WS6_B5"  Blank 5 — optional leaf (e.g. on evet branch without inner split)
"WS6_B6"  Blank 6 — inner-node feature on evet subtree (must differ from B1)
"WS6_B7"  Blank 7 — inner-node threshold with operator (transcribe exactly)
"WS6_B8"  Blank 8 — inner evet branch label
"WS6_B9"  Blank 9 — inner hayır branch label
"WS6_B10" Blank 10 — inner left leaf (tavsiye edilir / edilmez)
"WS6_B11" Blank 11 — inner right leaf
"WS6_B12" Blank 12 — optional extra leaf
"WS6_B13" Blank 13 — right-subtree leaf (hayır branch from root)

--- WORKSHEET 7: Karar Kuralları (Decision Rules) ---
WS7 has two parts on the worksheet. Transcribe exactly — do not normalize operators.

Part 1 — path matching (rows 5–7 next to printed rules): single letter A, B, or C.
"WS7_P1_box1"  Part 1 box for printed rule row 5 — letter A/B/C
"WS7_P1_box2"  Part 1 box for printed rule row 6 — letter A/B/C
"WS7_P1_box3"  Part 1 box for printed rule row 7 — letter A/B/C

Part 2 — if-then rules consistent with the pre-service teacher's WS6 tree (page 2 or lower section).
Transcribe full rules verbatim including ≤, ≥, <, >.
"WS7_B1"  Rule for WS6 leaf path 1
"WS7_B2"  Rule for WS6 leaf path 2
"WS7_B3"  Rule for WS6 leaf path 3
"WS7_B4"  Optional extra rule slot (often blank)
"WS7_B5"  Optional extra rule slot
"WS7_B6"  Optional extra rule slot
"WS7_B7"  Optional extra rule slot

--- WORKSHEET 10: Sistematik Eşik (Systematic Threshold — 8 numbered blanks) ---
WS10: printed blank numbers 1–8 (red on form). Transcribe only the HANDWRITTEN numeric
response next to each blank number — not the printed threshold column to the left.
"WS10_B1"  Blank 1 — pre-service teacher response (yanlış sınıflandırma count, table row 1)
"WS10_B2"  Blank 2 — pre-service teacher response (table row 2)
"WS10_B3"  Blank 3 — pre-service teacher response (table row 3)
"WS10_B4"  Blank 4 — pre-service teacher response (table row 4)
"WS10_B5"  Blank 5 — pre-service teacher response (table row 5)
"WS10_B6"  Blank 6 — pre-service teacher response (table row 6)
"WS10_B7"  Blank 7 — pre-service teacher response (table row 7)
"WS10_B8"  Blank 8 — optimum eşik değer (line below table: "Optimum eşik değer şudur:")

--- WORKSHEET SNAPSHOT ---
"ws_snapshot"
  Write 2-3 sentences summarising what this pre-service teacher's worksheets REVEAL about their
  understanding of decision trees. Focus on:
  - Completion level (which worksheets are fully vs. partially answered)
  - Key strengths visible from their written responses
  - Recurring errors or gaps (e.g. always omits inequality direction, only writes numbers
    without context, leaves threshold questions blank)
  - Notable features (e.g. "uses both English and Turkish terms", "writes complete sentences")
  This snapshot is for the researcher — be specific and evidence-based, not generic.

"page_notes"
  Brief note about scan quality, pages that were very hard to read, or unusual layout.
  Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS1_B1": "...", "WS1_B2": "...", "WS1_B3": "...", "WS1_B4": "...",
  "WS1_B5": "...", "WS1_B6": "...", "WS1_B7": "...", "WS1_B8": "...",
  "WS1_B9": "...", "WS1_B10": "...", "WS1_B11": "...",
  "WS3_B1": "...", "WS3_B2": "...", "WS3_B3": "...", "WS3_B4": "...",
  "WS3_B5": "...", "WS3_B6": "...", "WS3_B7": "...", "WS3_B8": "...",
  "WS4_B1": "...", "WS4_B2": "...", "WS4_B3": "...", "WS4_B4": "...", "WS4_B5": "...",
  "WS5_B1": "...", "WS5_B2": "...", "WS5_B3": "...", "WS5_B4": "...", "WS5_B5": "...",
  "WS5_B6": "...", "WS5_B7": "...", "WS5_B8": "...", "WS5_B9": "...", "WS5_B10": "...",
  "WS5_B11": "...", "WS5_B12": "...", "WS5_B13": "...", "WS5_B14": "...", "WS5_B15": "...",
  "WS5_B16": "...", "WS5_B17": "...", "WS5_B18": "...", "WS5_B19": "...", "WS5_B20": "...",
  "WS5_B21": "...", "WS5_B22": "...", "WS5_B23": "...", "WS5_B24": "...", "WS5_B25": "...",
  "WS6_B1": "...", "WS6_B2": "...", "WS6_B3": "...", "WS6_B4": "...", "WS6_B5": "...",
  "WS6_B6": "...", "WS6_B7": "...", "WS6_B8": "...", "WS6_B9": "...", "WS6_B10": "...",
  "WS6_B11": "...", "WS6_B12": "...", "WS6_B13": "...",
  "WS7_P1_box1": "...", "WS7_P1_box2": "...", "WS7_P1_box3": "...",
  "WS7_B1": "...", "WS7_B2": "...", "WS7_B3": "...", "WS7_B4": "...",
  "WS7_B5": "...", "WS7_B6": "...", "WS7_B7": "...",
  "WS10_B1": "...", "WS10_B2": "...", "WS10_B3": "...", "WS10_B4": "...",
  "WS10_B5": "...", "WS10_B6": "...", "WS10_B7": "...", "WS10_B8": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_WS11 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe every blank from Worksheet 11 (evaluation + feedback form).

You will receive multiple page images belonging to ONE pre-service teacher (one pseudonym folder).

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET 11 STRUCTURE:
- Printed questions 1–7 (B1–B7): NO correct answer — transcribe pre-service teacher marks/text verbatim
  - B1 Q1: lesson satisfaction — tick one of: Çok iyi, İyi, Ortalama, Kötü, Çok kötü; optional Açıklama text
  - B2 Q2: recommend to friends — Evet, Hayır, Bilmiyorum; optional Açıklama
  - B3 Q3: difficulty — Çok kolay, Kolay, Orta, Zor, Çok zor; optional Açıklama
  - B4 Q4: can explain how a DT works — Evet or Hayır (checkbox)
  - B5 Q5: enjoyment of food topic — Çok, İyi, Ortalama, Az, Çok Az; optional Açıklama
  - B6 Q6: age — handwritten number (Kaç yaşındasın)
  - B7 Q7: gender — Erkek or Kız (checkbox)
  Format each B1–B5 response as: "<selected option>" or "<option>; Açıklama: <text>" when explanation is written.
- Blanks B8a, B8b: classification task
- Blank B9: open-ended definition
- Likert group L10 (8 items): pre-service teachers CIRCLE a number 1-5 on a printed scale
- Likert group L11 (3 items): same format
- Group L12 (5 items): self-assessment / additional items

For Likert/circled-number items, transcribe the number the pre-service teacher circled.
If the scale shows options and the pre-service teacher ticked/circled one, write just that value.
If the pre-service teacher wrote text instead of circling, transcribe the text.

BLANKS TO EXTRACT:

"student_name"

--- Printed questions 1–7 (no correct answer) ---
"WS11_B1"  Q1 — lesson satisfaction (checkbox + optional Açıklama)
"WS11_B2"  Q2 — recommend to friends (Evet/Hayır/Bilmiyorum + optional Açıklama)
"WS11_B3"  Q3 — difficulty rating (Çok kolay…Çok zor + optional Açıklama)
"WS11_B4"  Q4 — can explain how a decision tree works (Evet or Hayır)
"WS11_B5"  Q5 — enjoyment of food topic (Çok…Çok Az + optional Açıklama)
"WS11_B6"  Q6 — age (Kaç yaşındasın)
"WS11_B7"  Q7 — gender (Erkek or Kız)

--- Classification and definition task ---
"WS11_B8a" Blank 8a — classify a food item using the printed decision tree (pre-service teacher's result)
"WS11_B8b" Blank 8b — write the decision RULE used for 8a (the if-then path the pre-service teacher traced)
"WS11_B9"  Blank 9 — define a decision tree in the pre-service teacher's own words (full written text)

--- Q10: true/false sub-items (8 statements; transcribe Doğru or Yanlış per row) ---
"WS11_Q10_1" through "WS11_Q10_8" — one answer per statement row

--- Q11: ordering steps 2-4 (step 1 is pre-printed; transcribe the number 2, 3, or 4 the pre-service teacher wrote) ---
"WS11_Q11_2"  Step 2 position
"WS11_Q11_3"  Step 3 position
"WS11_Q11_4"  Step 4 position

--- Q12: multiselect sub-items (transcribe checked/unchecked or mark presence) ---
"WS11_Q12_1" through "WS11_Q12_5" — one entry per option row

--- Likert group 10 (items 10.1 – 10.8) ---
Each is a 1-5 scale item. Transcribe the circled/ticked number exactly.
"WS11_L10_1"  Item 10.1 — circled scale value (1-5)
"WS11_L10_2"  Item 10.2
"WS11_L10_3"  Item 10.3
"WS11_L10_4"  Item 10.4
"WS11_L10_5"  Item 10.5
"WS11_L10_6"  Item 10.6
"WS11_L10_7"  Item 10.7
"WS11_L10_8"  Item 10.8

--- Likert group 11 (items 11.1 – 11.3) ---
"WS11_L11_1"  Item 11.1 — circled scale value
"WS11_L11_2"  Item 11.2
"WS11_L11_3"  Item 11.3

--- Group 12 (items 12.1 – 12.5, may include demographic or self-assessment) ---
"WS11_L12_1"  Item 12.1 — selected or written value
"WS11_L12_2"  Item 12.2
"WS11_L12_3"  Item 12.3
"WS11_L12_4"  Item 12.4
"WS11_L12_5"  Item 12.5

--- Snapshot ---
"ws_snapshot"
  Write 2-3 sentences summarising what Worksheet 11 reveals about this pre-service teacher.
  Note whether Q1–Q7 were filled, engagement with cognitive items (B8–Q12), and quality of B9.
  Do not score or judge Q1–Q7 — they are survey/demographic only.

"page_notes"
  Brief note about scan quality or layout issues. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS11_B1": "...", "WS11_B2": "...", "WS11_B3": "...", "WS11_B4": "...",
  "WS11_B5": "...", "WS11_B6": "...", "WS11_B7": "...",
  "WS11_B8a": "...", "WS11_B8b": "...", "WS11_B9": "...",
  "WS11_Q10_1": "...", "WS11_Q10_2": "...", "WS11_Q10_3": "...", "WS11_Q10_4": "...",
  "WS11_Q10_5": "...", "WS11_Q10_6": "...", "WS11_Q10_7": "...", "WS11_Q10_8": "...",
  "WS11_Q11_2": "...", "WS11_Q11_3": "...", "WS11_Q11_4": "...",
  "WS11_Q12_1": "...", "WS11_Q12_2": "...", "WS11_Q12_3": "...", "WS11_Q12_4": "...",
  "WS11_Q12_5": "...",
  "WS11_L10_1": "...", "WS11_L10_2": "...", "WS11_L10_3": "...", "WS11_L10_4": "...",
  "WS11_L10_5": "...", "WS11_L10_6": "...", "WS11_L10_7": "...", "WS11_L10_8": "...",
  "WS11_L11_1": "...", "WS11_L11_2": "...", "WS11_L11_3": "...",
  "WS11_L12_1": "...", "WS11_L12_2": "...", "WS11_L12_3": "...",
  "WS11_L12_4": "...", "WS11_L12_5": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_WS1 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe every blank from Worksheet 1 (Önemli Terimler — Important Terms).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET 1 STRUCTURE — 11 numbered blanks on one page:
Items 1-4 are diagram callout arrows pointing to four DISTINCT parts of a sample food data table.
Items 5-11 are fill-in-the-blank sentences in a paragraph about decision tree vocabulary.

=== GUARDRAIL 1 — DIAGRAM ARROW ASSIGNMENT (most common error source) ===
The diagram has printed arrow numbers (1, 2, 3, 4). The student writes one handwritten word next
to each arrow. Assign the word physically next to arrow N to WS1_BN.
- Do NOT reorder answers based on what you expect each term to mean.
- Do NOT swap B3 and B4 even if the words seem semantically reversed.
- If a student wrote the same word next to two different arrows, transcribe it twice.
- The same term (e.g. "özellik") appearing twice is a student error — transcribe it faithfully.

=== GUARDRAIL 2 — TRANSCRIBE ONLY HANDWRITTEN INK, NOT PRINTED TEXT ===
The worksheet has printed labels near the arrows (e.g. a printed "(tavsiye edilemez)" caption,
printed column headers, printed question numbers). These are part of the form design.
Transcribe ONLY what the student wrote by hand. If the student wrote "Etiket" and the printed
form nearby says "(tavsiye edilemez)", return only "Etiket" — not "Etiket (tavsiye edilemez)".

=== GUARDRAIL 3 — PARAGRAPH BLANK NUMBERING (B5-B11) ===
The paragraph has 7 printed blank slots numbered 5 through 11. Read left-to-right, top-to-bottom.
Each blank slot has exactly one student answer (or is empty). Assign them in printed order.
- If a blank is empty (no ink at all), return (bos).
- If there is ink but it is illegible, return (okunamiyor).
- Do NOT skip a blank because it "doesn't fit" the expected answer — transcribe what is there.
- B9 asks for a LIST of nutrient names. If the student wrote full sentences instead of names,
  transcribe the full sentences verbatim — do not summarize or extract just the names.

=== GUARDRAIL 4 — ws_snapshot LANGUAGE ===
Write ws_snapshot in Turkish only. Do not mix Turkish and English.

BLANKS TO EXTRACT:
"WS1_B1"  Handwritten word next to printed arrow 1 in the diagram.
"WS1_B2"  Handwritten word next to printed arrow 2 in the diagram.
"WS1_B3"  Handwritten word next to printed arrow 3 in the diagram.
"WS1_B4"  Handwritten word next to printed arrow 4 in the diagram.
"WS1_B5"  Paragraph blank 5 — student's handwritten answer (expected: nesne or similar)
"WS1_B6"  Paragraph blank 6 — student's handwritten answer
"WS1_B7"  Paragraph blank 7 — student's handwritten answer
"WS1_B8"  Paragraph blank 8 — student's handwritten answer (expected: a number or term)
"WS1_B9"  Paragraph blank 9 — full handwritten content (nutrient names or sentences)
"WS1_B10" Paragraph blank 10 — student's handwritten answer (expected: a food name)
"WS1_B11" Paragraph blank 11 — student's handwritten answer (expected: etiket or similar)

"ws_snapshot"
  2-3 Türkçe cümle: hangi terimleri kullandı, eksik/hatalı yerler, dikkat çekici örüntüler.

"page_notes"
  Brief note about scan quality or layout issues. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS1_B1": "...", "WS1_B2": "...", "WS1_B3": "...", "WS1_B4": "...",
  "WS1_B5": "...", "WS1_B6": "...", "WS1_B7": "...", "WS1_B8": "...",
  "WS1_B9": "...", "WS1_B10": "...", "WS1_B11": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_WS3 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe every blank from Worksheet 3 (Eşik Değerleri Bir Karar Kuralında Uygulamak).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET 3 STRUCTURE — 8 blanks:
Three food items (Patlamış Mısır, Elma, Patates Kızartması) each have two blanks:
  - An ODD blank (B1, B3, B5): the classification label the student assigned (tavsiye edilir/edilemez)
  - An EVEN blank (B2, B4, B6): the mathematical reason (a comparison like "23 > 8")
Then two blanks (B7, B8) for a threshold rule on a new variable (Enerji).

=== GUARDRAIL 1 — LABEL SUFFIX READING — CRITICAL ===
The recommendation label has two opposite forms that look similar in fast handwriting:
  "tavsiye edilir"    = recommended      (suffix: -ir)
  "tavsiye edilebilir"= recommended      (suffix: -ebilir)  ← same meaning as edilir
  "tavsiye edilemez"  = NOT recommended  (suffix: -emez)
  "tavsiye edilmez"   = NOT recommended  (suffix: -mez)

The pairs "-ebilir" vs "-emez" and "-ir" vs "-mez" are the most confusable in fast handwriting.
Read the FINAL syllable before the period or line end very carefully.
  "-bilir" ending → recommended group
  "-emez" or "-mez" ending → NOT recommended group

Do NOT infer the label from the mathematical expression in the next blank.
If B1 says "tavsiye edilebilir" but B2 says "23 > 8" (which implies not recommended),
transcribe B1 as written — it is a student error, not your misread to fix.

Variant spellings:
  recommended group:     tavsiye edilir, tavsiye edilebilir, önerilir, uygun, yeşil
  not-recommended group: tavsiye edilemez, tavsiye edilmez, önerilmez, uygun değil, kırmızı

=== GUARDRAIL 2 — MATHEMATICAL OPERATORS: STRICT VS NON-STRICT ARE DIFFERENT ===
In B2, B4, B6, B7, B8 the student writes a comparison expression.

The four operator symbols are DISTINCT and non-interchangeable:
  <   strict less-than        (angle only — NO bar below)
  ≤   less-than-or-equal      (angle WITH a horizontal bar below, or explicitly written as <=)
  >   strict greater-than     (angle only — NO bar below)
  ≥   greater-than-or-equal   (angle WITH a horizontal bar below, or explicitly written as >=)

PROCEDURE — apply to every comparison blank, one at a time:
STEP 1: Find the angle mark in the ink.
STEP 2: Look directly below the angle tip. Is there a separate horizontal stroke?
  YES, a stroke is clearly present   → write ≤ (or ≥)
  NO stroke at all                   → write < (or >)
  CANNOT TELL with confidence        → write your best reading AND add to page_notes:
                                       "[B? operatör belirsiz: < veya ≤ olabilir]"
STEP 3: Write the operator. Move to the next blank. Do not revisit.

THIS IS MANDATORY: If you write < or > without a page_notes flag, you are claiming that
you clearly saw NO bar. If you write ≤ or ≥ without a page_notes flag, you are claiming
that you clearly SAW a bar. Never omit the flag when you are not certain.

Do NOT infer the operator from the expected answer, the other blanks, or mathematical logic.
Do NOT assume consistency — each blank is independent.
A student may write ≤ in B4 and < in B7. That is a valid combination. Transcribe both exactly.

FORBIDDEN — these substitutions are never allowed, even if the result seems more "correct":
  ≥ or ≥ → >   (removing a bar that is there)
  ≤ or ≤ → <   (removing a bar that is there)
  < → ≤        (adding a bar that is not there)
  > → ≥        (adding a bar that is not there)

Handwriting shapes: a C, L, or ( used in a comparison reads as <; a ), 7, or V reads as >.
If the symbol is completely unreadable, write "(okunamiyor)" and add "[B? okunamayan operatör]".

=== GUARDRAIL 3 — B7 AND B8 CROSS-REFERENCE: TRANSCRIBE, DO NOT FIX ===
B7 is the left-branch threshold rule and B8 is the right-branch threshold rule.
A correct student uses THE SAME number in B7 and B8 with opposite operators.
If the student used DIFFERENT numbers in B7 and B8, transcribe both exactly as written.
Do NOT silently change a number to make B7 and B8 consistent — that is a student error
the researcher needs to see. You may note the inconsistency in page_notes if useful.

=== GUARDRAIL 4 — SPATIAL ANCHOR MATCHING ===
Each blank is anchored to a printed food name (Patlamış Mısır, Elma, Patates Kızartması).
If a student's handwriting drifts to the wrong line, use the nearest printed food name as anchor.
  B1, B2 → Patlamış Mısır row
  B3, B4 → Elma row
  B5, B6 → Patates Kızartması row
  B7, B8 → Enerji threshold section (bottom of page)

BLANKS TO EXTRACT:
"WS3_B1"  Patlamış Mısır — classification label (tavsiye edilir / edilemez variant)
"WS3_B2"  Patlamış Mısır — mathematical reason. Transcribe verbatim. Both "23 > 8" and
          "8 < 23" are equally valid — do NOT flag reversed operand order as an error.
"WS3_B3"  Elma — classification label
"WS3_B4"  Elma — mathematical reason. Both "0,2 < 8" and "8 > 0,2" are equally valid.
"WS3_B5"  Patates Kızartması — classification label
"WS3_B6"  Patates Kızartması — mathematical reason. Both "14 > 8" and "8 < 14" are equally valid.
"WS3_B7"  Enerji left-branch rule — transcribe operator + number exactly as written
"WS3_B8"  Enerji right-branch rule — transcribe operator + number exactly as written

"ws_snapshot"
  2-3 Türkçe cümle: etiketleri doğru mu belirlemiş, matematiksel ifadeleri doğru mu yazmış,
  B7-B8 eşik sayıları tutarlı mı, dikkat çekici örüntüler.
  KURAL 1: Yalnızca WS3'te geçen gıda adlarını kullan: Patlamış Mısır, Elma, Patates Kızartması.
  Başka gıda adı (Domates, Salatalık, vb.) YAZMA — bunlar bu sayfada yoktur.
  KURAL 2: Operatör tercihini (< vs ≤, > vs ≥) eleştirme. Öğrencinin yazdığı ne ise onu gözlemle,
  "tercih etmemiş" veya "daha doğru olurdu" gibi değerlendirme yorumu yapma.
  KURAL 3 — B7/B8 EŞİTLİK KONTROLÜ: B7 ve B8'de kullanılan operatörlere bak.
  Eğer ikisi de eşitliksiz operatör içeriyorsa (yani hem B7 hem B8'de sadece < veya > varsa,
  hiçbirinde ≤ veya ≥ yoksa), snapshot'a şunu ekle:
  "B7 ve B8'de eşitlik işareti kullanılmamış; tam olarak [eşik sayısı] kcal değerindeki
  bir gıdanın hangi dala atanacağı belirsizdir."
  Eğer B7 veya B8'de ≤ ya da ≥ varsa bu uyarıyı EKLEME.

"page_notes"
  Brief note about scan quality, illegible operators, or B7/B8 inconsistency. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS3_B1": "...", "WS3_B2": "...", "WS3_B3": "...", "WS3_B4": "...",
  "WS3_B5": "...", "WS3_B6": "...", "WS3_B7": "...", "WS3_B8": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_WS4 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: extract five response fields from Worksheet 4 (En İyi Eşik Değer Aranıyor).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

WORKSHEET 4 OVERVIEW:
Students work with 11 ProDaBi food cards sorted by fat content (left = low fat, right = high fat).
Leo's original threshold (3g fat) misclassifies 4 cards. Students must:
  Task 1 (B2): identify the 4 misclassified cards
  Task 2 (B1, B3): draw a better threshold line and explain why it is better
  Task 3 (B4): evaluate Pia's claim about equal fat values
  Task 4 (B5): state the best energy threshold learned from the deck

FOOD CARDS ON THE PAGE (in approximate left-to-right fat order):
  salatalık (0.1g), patates (0.1g), elma (0.2g), ahududu reçeli (0.2g),
  yulaf (7.0g), kraker (3.0g), avokado (13.0g), jelibon (0.1g),
  sütlü çikolata (29.5g), patates kızartması (14.0g), patlamış mısır (23.0g)

=== FIELD B2 — MISCLASSIFIED FOOD DETECTION ===
Students mark the 4 misclassified cards in ONE of three ways:
  (a) TEXT: They write the food names (Turkish or English) somewhere on the page.
  (b) VISUAL CIRCLE: They draw a loop, oval, or circle around the card image/sticker
      or around the card's label area. The circle may be faint or rough.
  (c) BOTH: They both circle and write the names.

VISUAL CIRCLE DETECTION PROCEDURE:
  STEP 1: Scan the food card row for any closed loop, oval, or enclosing mark
          drawn around a card image, sticker, or name label.
  STEP 2: For each marked card, identify the food name by its position in the row
          and any visible label text inside or near the mark.
  STEP 3: A mark counts as a circle even if it is rough, overlapping card edges,
          or only partially closed — as long as the intent is to enclose that card.
  STEP 4: Report each identified food in "circled_cards" using the canonical
          Turkish name: jelibon, kraker, yulaf, avokado, elma, ahududu reçeli,
          salatalık, patates, sütlü çikolata, patates kızartması, patlamış mısır.

NULL RULES:
  - circled_cards: [] (empty list) if no circles detected
  - written_foods: null if no text response found
  - foods_parsed: unified list from both sources; null if neither found

=== FIELD B1 — THRESHOLD LINE ===
Student may draw a vertical line between avocado (13g) and french fries (14g),
OR write a numeric value such as "13.5".
Capture both: placement_description (what you see) and threshold_value_parsed (float if present, else null).

=== FIELD B4 — PIA EVALUATION ===
Student states whether Pia is right or wrong. Full credit requires:
  - Agreement: "haklı", "evet", "doğru", or equivalent
  - Reasoning: apple (elma) and raspberry jam (ahududu reçeli) have the same fat value (0.2g)
Set agrees_with_pia: true / false / null (if unclear).

"ws_snapshot": 2-3 sentences describing what you SEE on the page for each task.
  Do NOT judge correctness.
"page_notes": circle ambiguities, illegible names, threshold ambiguities, or "(bos)" if none.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_id": "...",
  "worksheet": "WS4",
  "ws_snapshot": "...",
  "page_notes": "...",
  "extraction": {{
    "WS4_B1": {{
      "threshold_value_raw": "...",
      "threshold_value_parsed": 0.0,
      "placement_description": "..."
    }},
    "WS4_B2": {{
      "detection_method": "text",
      "circled_cards": [],
      "written_foods": "...",
      "foods_parsed": ["..."]
    }},
    "WS4_B3": {{
      "response_raw": "..."
    }},
    "WS4_B4": {{
      "agrees_with_pia": true,
      "response_raw": "..."
    }},
    "WS4_B5": {{
      "threshold_value_raw": "...",
      "threshold_value_parsed": 0.0
    }}
  }}
}}"""

PROMPT_WS5 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: extract the threshold-experiment grid and final decision from Worksheet 5
(Eşik Değerleri Deneyin — Try Out Threshold Values).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET 5 STRUCTURE:
The page contains a grid with up to 3 trial rows (Deneme 1, Deneme 2, Deneme 3).
Each row has:
  - Variable name (değişken): e.g. "yağ", "şeker", "enerji", "protein", "tuz"
  - Left branch (evet / tavsiye edilir): operator + threshold value
  - Right branch (hayır / tavsiye edilemez): operator + threshold value
  - Error count (Yanlış sınıflandırma sayısı): how many of the 11 food cards were misclassified
Below the grid the student writes their FINAL DECISION.

=== GUARDRAIL 1 — OPERATOR TRANSCRIPTION (BAR CHECK) ===
Read each operator independently using the bar-check procedure.
Apply to BOTH left and right branch operators.

STEP 1: Find the angle mark in the ink.
STEP 2: Look directly below the angle tip for a horizontal stroke.
  Clearly present → ≤ or ≥   (write as <= or >=)
  Clearly absent  → < or >
  CANNOT TELL    → transcribe best guess AND add to page_notes:
                   "[Deneme N left/right operatör belirsiz: < veya ≤ olabilir]"

CRITICAL — THE BAR IS OFTEN WRITTEN VERY SMALL:
A thin visible line counts as a bar. Prefer ≤ or ≥ when a stroke is detectable.
Only write < or > when there is clearly NO stroke below the angle.
Do NOT infer one branch's operator from the other.

FORBIDDEN substitutions:
  ≤ → <   FORBIDDEN
  ≥ → >   FORBIDDEN
  < → ≤   FORBIDDEN
  > → ≥   FORBIDDEN

=== GUARDRAIL 2 — COUNTS ===
Transcribe student_error_count exactly as written. Do NOT recompute.
If blank, write null.

=== GUARDRAIL 3 — TRIAL COUNT ===
Include only trials where the student wrote something. Do not add empty trials.

=== GUARDRAIL 4 — FINAL DECISION ===
final_decision_raw: verbatim text from the bottom paragraph. Write null if blank.

"page_notes"
  Operator ambiguities, faint ink, missing cells. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_id": "...",
  "worksheet": "WS5",
  "page_notes": "...",
  "extraction": {{
    "trials": [
      {{
        "trial_id": 1,
        "parsed_feature": "...",
        "left_operator": "...",
        "left_threshold": 0.0,
        "left_leaf_recommended": 0,
        "left_leaf_not_recommended": 0,
        "right_operator": "...",
        "right_threshold": 0.0,
        "right_leaf_recommended": 0,
        "right_leaf_not_recommended": 0,
        "student_error_count": 0,
        "student_mcr": null
      }}
    ],
    "final_decision_raw": "..."
  }}
}}"""

PROMPT_WS6 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: extract the two-level decision tree from Worksheet 6 (Karar Ağacı Çiz).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

WORKSHEET 6: Two-level decision tree on 11 ProDaBi food cards.
The student drew a tree with:
  - A root split node (depth_0)
  - Two inner split nodes (depth_1: left_child on the evet branch, right_child on the hayır branch)
  - Four leaf nodes (depth_2)

DEFINITIONS:
  "left" branch = evet (yes) branch — cards where the condition is TRUE
  "right" branch = hayır (no) branch — cards where the condition is FALSE
  left_operator / left_threshold_value: the operator and numeric threshold written for the evet branch
  right_operator / right_threshold_value: the operator and numeric threshold written for the hayır branch

TREE STRUCTURE TO EXTRACT:
  depth_0 (root node):
    parsed_feature: the nutritional feature written in the root box (e.g. Yağ, Şeker, Enerji, Protein, Tuz, Karbonhidrat)
    left_operator: operator for evet branch (e.g. ≤, <, ≥, >)
    left_threshold_value: numeric threshold as a float (e.g. 13.0)
    right_operator: operator for hayır branch
    right_threshold_value: same numeric value as left_threshold_value

  depth_1 (two inner nodes):
    left_child: the inner node on the evet (left) branch from depth_0
      parsed_feature: feature written in this inner node
      node_recommended_count: how many of the 11 food cards that reach this node are labeled "tavsiye edilir"
      node_not_recommended_count: how many are labeled "tavsiye edilemez"
      left_operator, left_threshold_value, right_operator, right_threshold_value: same pattern as depth_0
    right_child: the inner node on the hayır (right) branch from depth_0 (same fields)

  depth_2 (four leaf nodes):
    left_left_leaf: cards that went LEFT at depth_0 then LEFT at left_child
    left_right_leaf: cards that went LEFT at depth_0 then RIGHT at left_child
    right_left_leaf: cards that went RIGHT at depth_0 then LEFT at right_child
    right_right_leaf: cards that went RIGHT at depth_0 then RIGHT at right_child
    Each leaf has: leaf_recommended_count and leaf_not_recommended_count

  depth_2 leaf labels:
    Each leaf also has a leaf_label field: the class label the student wrote in that leaf box.
    Transcribe exactly: "tavsiye edilir", "tavsiye edilemez", or (bos) if blank.

=== GUARDRAIL — OPERATOR TRANSCRIPTION (BAR CHECK) ===
Apply this procedure to EVERY operator in the tree (depth_0, depth_1 left_child, depth_1 right_child).

STEP 1: Find the angle mark in the ink (the < or > shape).
STEP 2: Look directly below/above the tip of the angle for a horizontal stroke.
  Clearly present → ≤ or ≥
  Clearly absent  → < or >
  CANNOT TELL     → transcribe your best guess AND note in page_notes:
                    "[depth_X operator belirsiz: < veya ≤ olabilir]"

CRITICAL — THE BAR IS OFTEN WRITTEN VERY SMALL:
A thin visible line counts as a bar → write ≤ or ≥.
No stroke at all → write < or >.
Students may genuinely write < or > (student error is possible). Transcribe what is written, not what should be there.
When ambiguous, write your best guess AND note it in page_notes.

FORBIDDEN: do NOT infer one operator from the other.
  If left is ≤, do NOT automatically write > for right — read each side independently.
  ≤ → <   FORBIDDEN
  ≥ → >   FORBIDDEN

DIRECTION RULE — which operator belongs to which branch:
  left_operator  = the operator written on or beside the LEFT (evet) branch arrow
  right_operator = the operator written on or beside the RIGHT (hayır) branch arrow
  Read the spatial position of the arrow carefully. Do NOT swap them.

NULL RULES — use null (not 0, not "(bos)") when a field is blank:
  - parsed_feature: null if the node box is empty
  - node_recommended_count / node_not_recommended_count: null if student left blank
  - left_operator / right_operator: null if no operator written
  - left_threshold_value / right_threshold_value: null if no threshold written
  - leaf_label: null if leaf box is empty
  - leaf_recommended_count / leaf_not_recommended_count: null if student left blank

ASYMMETRIC TREE — if one branch terminates at depth_1 (no further split):
  Replace that child's fields with:
  {{"is_direct_leaf": true, "leaf_label": "...", "leaf_recommended_count": N, "leaf_not_recommended_count": N}}
  And set the corresponding depth_2 leaves to {{"not_applicable": true}}

INCOMPLETE BRANCH — if a branch box is drawn but completely empty:
  Write all fields as null. Do NOT invent counts or operators.
  Note it in page_notes.

DEPTH > 2 — if the student drew a 3rd level of splits:
  Note it in page_notes. Fit the deepest reachable leaves into depth_2.

"ws_snapshot": 2-3 sentences describing ONLY what you SEE on the paper: which features,
  thresholds, and how complete the tree looks. Do NOT judge correctness.

"page_notes": operator ambiguities, blank branches, threshold ambiguities, depth > 2. Write (bos) if none.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_id": "...",
  "worksheet": "WS6",
  "ws_snapshot": "...",
  "page_notes": "...",
  "extraction": {{
    "tree_structure": {{
      "depth_0": {{
        "parsed_feature": "...",
        "left_operator": "...",
        "left_threshold_value": 0.0,
        "right_operator": "...",
        "right_threshold_value": 0.0
      }},
      "depth_1": {{
        "left_child": {{
          "parsed_feature": "...",
          "node_recommended_count": 0,
          "node_not_recommended_count": 0,
          "left_operator": "...",
          "left_threshold_value": 0.0,
          "right_operator": "...",
          "right_threshold_value": 0.0
        }},
        "right_child": {{
          "parsed_feature": "...",
          "node_recommended_count": 0,
          "node_not_recommended_count": 0,
          "left_operator": "...",
          "left_threshold_value": 0.0,
          "right_operator": "...",
          "right_threshold_value": 0.0
        }}
      }},
      "depth_2": {{
        "leaf_nodes": {{
          "left_left_leaf": {{"leaf_label": "...", "leaf_recommended_count": 0, "leaf_not_recommended_count": 0}},
          "left_right_leaf": {{"leaf_label": "...", "leaf_recommended_count": 0, "leaf_not_recommended_count": 0}},
          "right_left_leaf": {{"leaf_label": "...", "leaf_recommended_count": 0, "leaf_not_recommended_count": 0}},
          "right_right_leaf": {{"leaf_label": "...", "leaf_recommended_count": 0, "leaf_not_recommended_count": 0}}
        }}
      }}
    }}
  }}
}}"""

PROMPT_WS7 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: extract the decision tree and rule-matching responses from Worksheet 7 (Karar Kuralları).
You will receive ONE page image belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

WORKSHEET 7 PURPOSE:
The student sees a printed two-level enerji/protein decision tree with empty threshold boxes.
They must READ the printed if-then rules at the BOTTOM of the page and fill in the tree's
threshold boxes by reverse-engineering from those rules.
Expected threshold values: depth_0 (Enerji) = 180 kcal; depth_1 (Protein) = 7,7 g.
Transcribe exactly what the student WROTE — not what they should have written.

TREE STRUCTURE:
  depth_0: root node split on Enerji
    left branch (evet) → typically leads directly to a leaf (path A)
    right branch (hayır) → leads to depth_1 inner node on Protein

  depth_1:
    left_child: the node on the left (evet) branch of depth_0.
      If this is a DIRECT LEAF (no further split), use:
        {{"path_label": "A", "node_recommended_count": N, "node_not_recommended_count": N}}
      If this is an INNER NODE (has its own split), use:
        {{"parsed_feature": "...", "left_operator": "...", "left_threshold_value": 0.0,
          "right_operator": "...", "right_threshold_value": 0.0,
          "node_recommended_count": N, "node_not_recommended_count": N}}
    right_child: the node on the right (hayır) branch of depth_0 — always an inner node on Protein:
        {{"parsed_feature": "Protein", "left_operator": "...", "left_threshold_value": 0.0,
          "right_operator": "...", "right_threshold_value": 0.0,
          "node_recommended_count": N, "node_not_recommended_count": N}}

  depth_2: leaf nodes produced by depth_1 splits.
    right_left_leaf: left (evet) branch of depth_1 right_child → path B
    right_right_leaf: right (hayır) branch of depth_1 right_child → path C
    Each leaf: {{"path_label": "...", "leaf_recommended_count": N, "leaf_not_recommended_count": N}}
    If student left counts blank, use null.

RULE MATCHING (bottom of page):
  Three printed rule sentences with empty boxes beside them.
  Student writes A, B, or C in each box. Transcribe exactly; null if box is empty.
  Do NOT confuse the printed A/B/C branch labels on the tree itself with these boxes.
  rule_1_box, rule_2_box, rule_3_box.

=== GUARDRAIL — OPERATOR READING ===
Apply to every operator in depth_0, depth_1 left_child, depth_1 right_child.

STEP 1: Find the angle stroke (< or > shape).
STEP 2: Look for a horizontal bar below/above the angle tip.
  Bar present  → ≤ or ≥
  Bar absent   → < or >
  Ambiguous    → best guess + note in page_notes

REVERSED NOTATION: some students write "190 <" instead of "< 190".
  Parse the operator direction from context (left branch = smaller values, right branch = larger).
  Report the operator as the direction it logically encodes (e.g. "190 <" → operator ">").
  Note reversed notation in page_notes.

FORBIDDEN: do NOT infer one operator from its pair. Read each independently.

NULL RULES: use null (not "(bos)") for any field the student left blank.

VALIDATION — compute from what you extracted:

tree_completeness: is_correct=true if ALL of the following are non-null:
  depth_0 left_operator, left_threshold_value, right_operator, right_threshold_value AND
  depth_1 right_child operators and threshold AND leaf counts in depth_2.
  error_flags (pick the most specific): "missing_root_thresholds" | "missing_protein_thresholds" |
  "missing_leaf_counts" | null

rule_mapping: is_correct=true if all three rule boxes have a letter (A, B, or C).
  error_flag: "missing_rule_assignments" | null

threshold_alignment: is_correct=true if depth_0 threshold value ≈ 180 AND
  depth_1 right_child threshold value ≈ 7.7.
  error_flag: "threshold_mismatch_with_instructions" | null

system_analytical_summary: 2–3 sentences in Turkish. Describe what the student understood
  (or failed to understand) about the reverse-engineering task. Cite specific values they wrote.
  Compare against the expected 180 kcal / 7,7 g targets. Note rule-matching completion.

"ws_snapshot": 2–3 sentences describing what you see on the page. Do NOT judge correctness.
"page_notes": operator ambiguities, reversed notation, illegible counts, empty sections. (bos) if none.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_id": "...",
  "worksheet": "WS7",
  "ws_snapshot": "...",
  "page_notes": "...",
  "extraction": {{
    "tree_structure": {{
      "depth_0": {{
        "left_operator": "...",
        "left_threshold_value": 0.0,
        "right_operator": "...",
        "right_threshold_value": 0.0
      }},
      "depth_1": {{
        "left_child": {{
          "path_label": "A",
          "node_recommended_count": 0,
          "node_not_recommended_count": 0
        }},
        "right_child": {{
          "parsed_feature": "Protein",
          "node_recommended_count": 0,
          "node_not_recommended_count": 0,
          "left_operator": "...",
          "left_threshold_value": 0.0,
          "right_operator": "...",
          "right_threshold_value": 0.0
        }}
      }},
      "depth_2": {{
        "leaf_nodes": {{
          "right_left_leaf": {{
            "path_label": "B",
            "leaf_recommended_count": 0,
            "leaf_not_recommended_count": 0
          }},
          "right_right_leaf": {{
            "path_label": "C",
            "leaf_recommended_count": 0,
            "leaf_not_recommended_count": 0
          }}
        }}
      }}
    }},
    "rule_matching": {{
      "rule_1_box": "...",
      "rule_2_box": "...",
      "rule_3_box": "..."
    }}
  }},
  "validation": {{
    "item_checks": {{
      "tree_completeness": {{"is_correct": true, "error_flag": null}},
      "rule_mapping": {{"is_correct": true, "error_flag": null}},
      "threshold_alignment": {{"is_correct": true, "error_flag": null}}
    }},
    "system_analytical_summary": "..."
  }}
}}"""

PROMPT_WS10 = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe WS10 (Sistematik Eşik — Systematic Threshold) from a single page image
belonging to ONE pre-service teacher.

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

WORKSHEET STRUCTURE — WS10:
The page contains a printed table with 7 rows. Each row shows a candidate energy threshold value
(printed on the left) and a blank where the student writes the number of misclassification errors
for that threshold. Below the table is a line "Optimum eşik değer şudur:" where the student writes
the threshold with the fewest errors.

Printed threshold values (left column, do NOT confuse with student answers):
  Row 1: 28 kcal   Row 2: 69 kcal   Row 3: 219 kcal  Row 4: 346 kcal
  Row 5: 359 kcal  Row 6: 408 kcal  Row 7: 489 kcal

Transcribe ONLY the HANDWRITTEN numeric value in each blank. If a blank is empty, use "(bos)".

"WS10_B1"  Row 1 — misclassification count for threshold 28
"WS10_B2"  Row 2 — misclassification count for threshold 69
"WS10_B3"  Row 3 — misclassification count for threshold 219
"WS10_B4"  Row 4 — misclassification count for threshold 346
"WS10_B5"  Row 5 — misclassification count for threshold 359
"WS10_B6"  Row 6 — misclassification count for threshold 408
"WS10_B7"  Row 7 — misclassification count for threshold 489
"WS10_B8"  Optimum threshold — the number written on the "Optimum eşik değer şudur:" line

"ws_snapshot"
  1-2 sentences: did the student complete the table? Are counts plausible (integers 0–11)?
  Does B8 match the row with the lowest count? Be specific and evidence-based.

"page_notes"
  Brief note about scan quality or unusual layout. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "WS10_B1": "...", "WS10_B2": "...", "WS10_B3": "...", "WS10_B4": "...",
  "WS10_B5": "...", "WS10_B6": "...", "WS10_B7": "...", "WS10_B8": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_DT_XENO = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe one pre-service teacher's completed CODAP Arbor "Ağaçlarla Tanı Koyma" (Xeno) worksheet.

You will receive 10 page images belonging to ONE pre-service teacher. Treat all 10 pages as one document.
Most pages are printed instructions with no student writing. Student answers appear only in:
  Page 4 — "Karar Ağacını Okuyalım" table (7-row Q&A table, handwritten answers in right column)
  Page 6 — Two boxed Soru/Cevap blocks (FP/FN danger question; CODAP performance question)
  Page 7 — "Karışıklık Matrisi" table (TP/TN/FP/FN/N counts + explanations)
  Page 8 — Metric calculation table (Doğruluk/Duyarlılık/Özgüllük/Kesinlik) + three Soru/Cevap blocks
  Page 9 — "Yeni Bir Metriği Tanıyalım" MCR table + one Soru/Cevap block

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

IMPORTANT — XENO DATASET IS STUDENT-SPECIFIC:
Each student received a randomly assigned dataset. The counts for blue/pink hair cases and sick/healthy
totals will differ between students. Transcribe the student's own numbers exactly as written.
The structural invariant is: blue hair = 0% sick, pink hair = 100% sick, so FP=FN=0 always.

WHAT TO EXTRACT — return exactly these JSON keys with verbatim pre-service teacher answers:

"student_name"
  The pseudonym printed in the black name box (top-right corner of page 1).

--- PAGE 4: Karar Ağacını Okuyalım (7-row Q&A table) ---
"DTI_01"  Row 1 — Kök düğüm (root node): how many cases, what % are sick (hasta). Transcribe the full answer.
"DTI_02"  Row 2 — Mavi saçlı (blue hair) kutu: how many cases, what % are sick. Transcribe the full answer.
"DTI_03"  Row 3 — Pembe saçlı (pink hair) kutu: how many cases, what % are sick, interpretation. Transcribe the full answer.
"DTI_04"  Row 4 — Which box was labeled "pozitif" (hasta/sick)? What criteria used? Alternative possible?
"DTI_05"  Row 5 — Pembe saçlı (pink hair) kutu (repeated question about sick relationship). Transcribe the full answer.
"DTI_06"  Row 6 — "Saç rengi değişkeni bu veri setinde iyi bir ayırıcı mıdır? Neden?" — Is hair color a good predictor?
"DTI_07"  Row 7 — "Eğer yeni bir vaka gelseydi, yalnızca saç rengine bakarak..." — prediction for new case.

--- PAGE 6: Boxed question blocks ---
"DTI_08"  Soru: FP vs FN tıbbi tehlike — which error type is more dangerous and why (FP mi FN mi)?
"DTI_09"  Soru: "Karar ağacınız 10 yeni hastayı otomatik olarak teşhis edecek. Ağacınız nasıl bir performans sergiledi?" — CODAP performance summary.

--- PAGE 7: Karışıklık Matrisi table ---
"DTI_10"  TP (Doğru Pozitif) — student's numeric value in "Sayı" column.
"DTI_11"  TP — student's explanation in "Ne anlama geliyor?" column.
"DTI_12"  TN (Doğru Negatif) — student's numeric value in "Sayı" column.
"DTI_13"  TN — student's explanation in "Ne anlama geliyor?" column.
"DTI_14"  FP (Yanlış Pozitif) — student's numeric value in "Sayı" column.
"DTI_15"  FP — student's explanation in "Ne anlama geliyor?" column.
"DTI_16"  FN (Yanlış Negatif) — student's numeric value in "Sayı" column.
"DTI_17"  FN — student's explanation in "Ne anlama geliyor?" column.
"DTI_18"  N (Toplam) — student's numeric value in "Sayı" column.
"DTI_19"  N — student's explanation in "Ne anlama geliyor?" column.

--- PAGE 8: Performans Metrikleri calculation table ---
"DTI_20"  Doğruluk (Accuracy) — student's formula/calculation in "Hesaplama (Adım Adım)" column.
"DTI_21"  Doğruluk — student's interpretation in "Sonucu Yorumlayın" column.
"DTI_22"  Duyarlılık (Sensitivity) — student's formula/calculation.
"DTI_23"  Duyarlılık — student's interpretation.
"DTI_24"  Özgüllük (Specificity) — student's formula/calculation.
"DTI_25"  Özgüllük — student's interpretation.
"DTI_26"  Kesinlik (Precision) — student's formula/calculation.
"DTI_27"  Kesinlik — student's interpretation.

--- PAGE 8: Three Soru/Cevap blocks below the metrics table ---
"DTI_28"  Soru: "Bir Xenobiyolog olarak hangi metriği öncelikli olarak kullanırsınız?" — which metric and why.
"DTI_29"  Sub-question a) of new metric block: "Oluşturduğunuz metriğin formülünü yazın." — student's formula for a new metric.
"DTI_30"  Sub-question b): "Oluşturduğunuz ölçü neyi daha iyi yakalamaktadır?" — what the new metric captures.
"DTI_31"  Sub-question c): "Bu ölçü hangi durumlarda tercih edilmelidir?" — when to prefer this metric.

--- PAGE 9: Yeni Bir Metriği Tanıyalım / MCR ---
"DTI_32"  MCR (Yanlış Sınıflandırma Oranı) — student's formula/calculation in "Hesaplama" column.
"DTI_33"  MCR — student's interpretation in "Sonucu Yorumlayın" column.

"ws_snapshot"
  2-3 sentence summary of the student's overall performance: their Xeno dataset counts,
  whether FP=FN=0 was achieved, and notable observations about their metric calculations or written explanations.
"page_notes"
  Brief note about scan quality or skipped pages. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "DTI_01": "...", "DTI_02": "...", "DTI_03": "...", "DTI_04": "...",
  "DTI_05": "...", "DTI_06": "...", "DTI_07": "...",
  "DTI_08": "...", "DTI_09": "...",
  "DTI_10": "...", "DTI_11": "...", "DTI_12": "...", "DTI_13": "...",
  "DTI_14": "...", "DTI_15": "...", "DTI_16": "...", "DTI_17": "...",
  "DTI_18": "...", "DTI_19": "...",
  "DTI_20": "...", "DTI_21": "...", "DTI_22": "...", "DTI_23": "...",
  "DTI_24": "...", "DTI_25": "...", "DTI_26": "...", "DTI_27": "...",
  "DTI_28": "...", "DTI_29": "...", "DTI_30": "...", "DTI_31": "...",
  "DTI_32": "...", "DTI_33": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPT_DT_TITANIC = f"""You are an expert at reading handwritten Turkish pre-service teacher worksheets.
Your task: transcribe one pre-service teacher's completed CODAP Arbor "CODAP Arbor'da Titanic Verisi" worksheet.

You will receive 10 page images belonging to ONE pre-service teacher. Treat all 10 pages as one document.
Most pages contain printed instructions. Student handwriting appears in answer boxes and table cells.

Page layout:
  Page 1  — Cover (no student answers)
  Page 2  — VS1 Eğitim: "Karar Ağacını Okuyalım" table (DTI_01–04) + "Değerleri Yazalım" metrics table (DTI_05–09)
  Page 3  — VS1 Test: "Karar Ağacını Okuyalım" table (DTI_10–13) + "Değerleri Yazalım" metrics table (DTI_14–18)
  Page 4  — VS1 interpretation Soru/Cevap blocks (DTI_19–22)
  Page 5  — VS2 Eğitim: "Karar Ağacını Okuyalım" table (DTI_23–26) + "Değerleri Yazalım" metrics table (DTI_27–31)
  Page 6  — VS2 Test: "Karar Ağacını Okuyalım" table (DTI_32–35) + "Değerleri Yazalım" metrics table (DTI_03–40)
  Page 7  — VS2 interpretation Soru/Cevap blocks (DTI_08–44)
  Page 8  — Final Soru/Cevap blocks about good models and single metrics (DTI_12–47)
  Pages 9–10 — "Veri Setini Rastgele Bölme" instructions (no student answers)

{_NAME_INSTRUCTION}

{_HANDWRITING_INSTRUCTION}

{_SENTINEL_INSTRUCTION}

TITANIC DATASET — ALL STUDENTS USE THE SAME FIXED CSV FILES:
  VS1 eğitim:  N=812, female=290 (all survived), male=522 (none survived) → perfect separation, all metrics=1.0
  VS1 test:    N=231, female=96 (56 survived, 40 died), male=135 (49 survived, 86 died)
  VS2 eğitim:  N=834, female=304 (128 survived, 176 died), male=530 (328 survived, 202 died)
  VS2 test:    N=209, female=82 (61 survived, 21 died), male=127 (24 survived, 103 died)
  Positive class in all datasets: female (hayatta kaldı = 1)
  TP = female survived, FP = female died, TN = male died, FN = male survived

Transcribe the student's written values exactly, even if they differ from the canonical values above.
The scoring pipeline will compare against canonical; do not correct the student.

TRAP QUESTION WARNING — DTI_43 and DTI_44:
  The printed question stem for both blanks copies the VS1 wording ("eğitim duyarlılığı oldukça yüksekken"
  and "MCR oldukça düşükken"). In VS2 reality, eğitim sensitivity is LOW (~28%) and MCR is HIGH (~60%).
  A student who recognizes this contradiction and corrects for it deserves full credit.
  Transcribe whatever the student wrote, including any notes about the contradiction.

WHAT TO EXTRACT:

"student_name"  The pseudonym in the black name box (top-right corner of page 1).

--- PAGE 2: VS1 Eğitim ---
"DTI_01"  "Karar Ağacını Okuyalım – Eğitim Veri Seti 1" table — Row 1: Kök düğüm kaç yolcu? Kaçı hayatta?
"DTI_02"  Row 2: Female (kadın) kutusunda kaç kişi? Kaçı hayatta?
"DTI_03"  Row 3: Male (erkek) kutusunda kaç kişi? Kaçı hayatta?
"DTI_04"  Row 4: Hangi kutu 'pozitif' (hayatta) olarak etiketlendi?
"DTI_05"  "Değerleri Yazalım – Eğitim Veri Seti 1" — Doğruluk: student's Hesaplama (Adım Adım) column.
"DTI_06"  Duyarlılık: student's calculation.
"DTI_07"  Özgüllük: student's calculation.
"DTI_08"  Kesinlik: student's calculation.
"DTI_09"  Yanlış Sınıflandırma Oranı (MCR): student's calculation.

--- PAGE 3: VS1 Test ---
"DTI_10"  "Karar Ağacını Okuyalım – Test Veri Seti 1" — Row 1: Kök düğüm kaç yolcu? Kaçı hayatta?
"DTI_11"  Row 2: Female kutusunda kaç kişi? Kaçı hayatta?
"DTI_12"  Row 3: Male kutusunda kaç kişi? Kaçı hayatta?
"DTI_13"  Row 4: Hangi kutu 'pozitif' olarak etiketlendi?
"DTI_14"  "Değerleri Yazalım – Test Veri Seti 1" — Doğruluk: student's calculation.
"DTI_15"  Duyarlılık: student's calculation.
"DTI_16"  Özgüllük: student's calculation.
"DTI_17"  Kesinlik: student's calculation.
"DTI_18"  Yanlış Sınıflandırma Oranı (MCR): student's calculation.

--- PAGE 4: VS1 interpretation ---
"DTI_19"  Soru: "Eğitim ve test seti metrikleri arasında büyük bir fark var mı? Varsa bu fark neden olabilir?"
"DTI_20"  Soru: "Aşırı öğrenme (overfitting) nedir? Bu senaryoda neden aşırı öğrenme gerçekleşmiş olabilir?"
"DTI_21"  Soru: "Eğitim veri setinde duyarlılık (sensitivity) değeri oldukça yüksek iken test veri setinde bu değerin belirgin biçimde düşmüştür. Bu durumu modelin performansı açısından yorumlayın."
"DTI_22"  Soru: "Eğitim veri setinde yanlış sınıflandırma oranı (MCR) oldukça düşük iken test veri setinde bu oranın belirgin biçimde artmıştır. Bu durumu modelin performansı açısından yorumlayın."

--- PAGE 5: VS2 Eğitim ---
"DTI_23"  "Karar Ağacını Okuyalım – Eğitim Veri Seti 2" — Row 1: Kök düğüm kaç yolcu? Kaçı hayatta?
"DTI_24"  Row 2: Female kutusunda kaç kişi? Kaçı hayatta?
"DTI_25"  Row 3: Male kutusunda kaç kişi? Kaçı hayatta?
"DTI_26"  Row 4: Hangi kutu 'pozitif' olarak etiketlendi?
"DTI_27"  "Değerleri Yazalım – Eğitim Veri Seti 2" — Doğruluk: student's calculation.
"DTI_28"  Duyarlılık: student's calculation.
"DTI_29"  Özgüllük: student's calculation.
"DTI_30"  Kesinlik: student's calculation.
"DTI_31"  Yanlış Sınıflandırma Oranı (MCR): student's calculation.

--- PAGE 6: VS2 Test ---
"DTI_32"  "Karar Ağacını Okuyalım – Test Veri Seti 2" — Row 1: Kök düğüm kaç yolcu? Kaçı hayatta?
"DTI_33"  Row 2: Female kutusunda kaç kişi? Kaçı hayatta?
"DTI_34"  Row 3: Male kutusunda kaç kişi? Kaçı hayatta?
"DTI_35"  Row 4: Hangi kutu 'pozitif' olarak etiketlendi?
"DTI_36"  "Değerleri Yazalım – Test Veri Seti 2" — Doğruluk: student's calculation.
"DTI_37"  Duyarlılık: student's calculation.
"DTI_38"  Özgüllük: student's calculation.
"DTI_39"  Kesinlik: student's calculation.
"DTI_40"  Yanlış Sınıflandırma Oranı (MCR): student's calculation.

--- PAGE 7: VS2 interpretation ---
"DTI_41"  Soru: "Eğitim ve test seti metrikleri arasında büyük bir fark var mı? Varsa bu fark neden olabilir?"
"DTI_42"  Soru: "Yetersiz uyum (underfitting) nedir? Bu senaryoda neden yetersiz uyum gerçekleşmiş olabilir?"
"DTI_43"  TRAP QUESTION — Soru about sensitivity being high in training (prompt copied from VS1): transcribe student's answer even if they recognize the contradiction.
"DTI_44"  TRAP QUESTION — Soru about MCR being low in training (prompt copied from VS1): transcribe student's answer even if they recognize the contradiction.

--- PAGE 8: Final questions ---
"DTI_45"  Soru: "'İyi' bir model nasıl olmalıdır? Hem eğitim hem test setinde hangi metriklerin nasıl olmasını beklersin?"
"DTI_46"  Soru: "Bu iki senaryo size bir modeli değerlendirirken sadece eğitim seti metriklerine bakmanın neden yeterli olmadığını nasıl gösterdi?"
"DTI_47"  Soru: "Bir modelin performansını yalnızca tek bir metriğe (örneğin doğruluk) bakarak değerlendirmek uygun mudur? Nedenini yazın."

"ws_snapshot"
  2-3 sentence summary: how the student handled the VS1 overfitting pattern, whether they correctly identified
  underfitting in VS2, and any notable observations about blank answers or the trap questions DTI_43/44.
"page_notes"
  Brief note about scan quality or blank pages. Write (bos) if no issues.

Return ONLY the following JSON object. No text before or after it.
{{
  "student_name": "...",
  "DTI_01": "...", "DTI_02": "...", "DTI_03": "...", "DTI_04": "...",
  "DTI_05": "...", "DTI_06": "...", "DTI_07": "...", "DTI_08": "...", "DTI_09": "...",
  "DTI_10": "...", "DTI_11": "...", "DTI_12": "...", "DTI_13": "...",
  "DTI_14": "...", "DTI_15": "...", "DTI_16": "...", "DTI_17": "...", "DTI_18": "...",
  "DTI_19": "...", "DTI_20": "...", "DTI_21": "...", "DTI_22": "...",
  "DTI_23": "...", "DTI_24": "...", "DTI_25": "...", "DTI_26": "...",
  "DTI_27": "...", "DTI_28": "...", "DTI_29": "...", "DTI_30": "...", "DTI_31": "...",
  "DTI_32": "...", "DTI_33": "...", "DTI_34": "...", "DTI_35": "...",
  "DTI_36": "...", "DTI_37": "...", "DTI_38": "...", "DTI_39": "...", "DTI_40": "...",
  "DTI_41": "...", "DTI_42": "...", "DTI_43": "...", "DTI_44": "...",
  "DTI_45": "...", "DTI_46": "...", "DTI_47": "...",
  "ws_snapshot": "...",
  "page_notes": "..."
}}"""

PROMPTS: dict[str, str] = {
    # 2025
    "WorksheetDT.pdf": PROMPT_DT,
    "Worksheets1-10.pdf": PROMPT_WS,
    "Worksheet11_ Feedbacks.pdf": PROMPT_WS11,
    # 2026
    "21-28 Nisan 2026 Çalışma Kâğıdı DT.pdf": PROMPT_DT,
    "24 Mart 2026 Çalışma Kâğıdı 1.pdf": PROMPT_WS1,
    "24 Mart 2026 Çalışma Kâğıdı 3.pdf": PROMPT_WS3,
    "24 Mart 2026 Çalışma Kâğıdı 4.pdf": PROMPT_WS4,
    "24 Mart 2026 Çalışma Kâğıdı 5.pdf": PROMPT_WS5,
    "31 Mart 2026 Çalışma Kâğıdı 6.pdf": PROMPT_WS6,
    "31 Mart 2026 Çalışma Kâğıdı 7.pdf": PROMPT_WS7,
    "31 Mart 2026 Çalışma Kâğıdı 10.pdf": PROMPT_WS10,
    # 2026 — CODAP Arbor WS_DT_XENO / WS_DT_TITANIC (split from legacy WS_DT_INTRO)
    "07 Nisan 2026 Çalışma Kâğıdı Xeno.pdf": PROMPT_DT_XENO,
    "07 Nisan 2026 Çalışma Kâğıdı Titanic.pdf": PROMPT_DT_TITANIC,
}

# ---------------------------------------------------------------------------
# Page-group detection — replaces fixed PAGES_PER_STUDENT slicing
# ---------------------------------------------------------------------------

# The redaction/pseudonymization tooling used to prepare these scans appears to
# stamp a default placeholder name box on every page and overlay the real
# pseudonym on top for most students; the placeholder text stays in the PDF's
# text layer underneath, so pypdf's extract_text() returns BOTH strings on a
# page whose real label happens to be something other than the placeholder.
# Confirmed by opening the rendered page for 4 independent occurrences (DT p25,
# WS1-10 p18, WS11 p1, WS11 p7) — the *other* candidate was correct every time.
GHOST_PLACEHOLDER_NAME = "Karl"

PAGE_NAME_OVERRIDES_PATH = Path(__file__).parent / "calibration" / "page_name_overrides.json"


def _load_page_name_overrides(pdf_name: str) -> dict[int, str]:
    """Manual {page_number: name} overrides for pages a human has visually checked."""
    if not PAGE_NAME_OVERRIDES_PATH.exists():
        return {}
    doc = json.loads(PAGE_NAME_OVERRIDES_PATH.read_text(encoding="utf-8"))
    raw = doc.get("pdfs", {}).get(pdf_name, {})
    return {int(page_num): name for page_num, name in raw.items()}


def detect_student_page_ranges(pdf_name: str) -> list[dict[str, Any]]:
    """
    Detect per-student page groups from the PDF's own text layer instead of
    assuming a fixed page count per student.

    Each worksheet page prints the pseudonym in a name banner; pypdf can read it
    for free (no Claude call). A page whose text layer yields no known pseudonym
    (rotated pages, e.g. WS6, or template pages that only print the name once per
    block) inherits the previous page's owner.

    Some pages carry more than one candidate pseudonym in the text layer (see
    GHOST_PLACEHOLDER_NAME) — those are resolved via the ghost-name rule, then
    calibration/page_name_overrides.json, and any still-unresolved page is left
    unowned (inherits like a blank page) and printed as an explicit warning
    asking for a manual override entry, rather than guessed.

    Returns 1-based inclusive page ranges:
      [{"student": str, "start": int, "end": int, "page_count": int, "detected_pages": int}, ...]

    A group whose length is a clean multiple of this file's typical block length
    (PAGES_PER_STUDENT[pdf_name]) usually means an unlabeled follow-on submission
    got merged into the previous student — those extra chunks are split out as
    "unresolved_p{start}" rather than silently attributed to the wrong name.
    """
    from collections import Counter
    from pypdf import PdfReader

    reader = PdfReader(str(DATA_DIR / pdf_name))
    # Secondary alphabetical key keeps same-length ties deterministic across runs
    # (frozenset iteration order depends on PYTHONHASHSEED otherwise).
    names_by_length = sorted(KNOWN_PSEUDONYMS, key=lambda n: (-len(n), n))
    overrides = _load_page_name_overrides(pdf_name)

    page_owner: list[Optional[str]] = []
    for page_num, page in enumerate(reader.pages, start=1):
        if page_num in overrides:
            page_owner.append(overrides[page_num])
            continue
        text = page.extract_text() or ""
        fused = re.sub(r"[^A-Za-z]", "", text)
        candidates = [name for name in names_by_length if name in fused]
        if len(candidates) <= 1:
            page_owner.append(candidates[0] if candidates else None)
            continue
        others = [c for c in candidates if c != GHOST_PLACEHOLDER_NAME]
        if GHOST_PLACEHOLDER_NAME in candidates and len(others) == 1:
            page_owner.append(others[0])
            continue
        print(
            f"  WARNING: page {page_num} has multiple candidate names {candidates} in its text "
            f"layer and none resolves automatically — add an entry to "
            f"{PAGE_NAME_OVERRIDES_PATH.relative_to(Path(__file__).parent)} after checking "
            f"ocr_output/_images/{pdf_to_images_stem(pdf_name)}/."
        )
        page_owner.append(None)

    groups: list[dict[str, Any]] = []
    current_name: Optional[str] = None
    start = 1
    detected_count = 0
    for i, owner in enumerate(page_owner, start=1):
        name = owner or current_name
        if current_name is not None and name != current_name:
            groups.append({
                "student": current_name, "start": start, "end": i - 1,
                "page_count": i - start, "detected_pages": detected_count,
            })
            start = i
            detected_count = 0
        current_name = name
        if owner is not None:
            detected_count += 1
    if current_name is not None:
        groups.append({
            "student": current_name, "start": start, "end": len(page_owner),
            "page_count": len(page_owner) - start + 1, "detected_pages": detected_count,
        })

    typical_length = PAGES_PER_STUDENT.get(pdf_name, 0)
    if typical_length:
        split_groups: list[dict[str, Any]] = []
        for g in groups:
            n_chunks = g["page_count"] // typical_length
            if n_chunks <= 1 or g["page_count"] % typical_length != 0:
                split_groups.append(g)
                continue
            for chunk_idx in range(n_chunks):
                chunk_start = g["start"] + chunk_idx * typical_length
                chunk_end = chunk_start + typical_length - 1
                if chunk_idx == 0:
                    chunk_name = g["student"]
                else:
                    chunk_detected = [
                        page_owner[p - 1] for p in range(chunk_start, chunk_end + 1)
                        if page_owner[p - 1] is not None
                    ]
                    chunk_name = chunk_detected[0] if chunk_detected else f"unresolved_p{chunk_start}"
                split_groups.append({
                    "student": chunk_name, "start": chunk_start, "end": chunk_end,
                    "page_count": typical_length,
                    "detected_pages": sum(1 for p in range(chunk_start, chunk_end + 1) if page_owner[p - 1]),
                })
        groups = split_groups

    name_counts = Counter(g["student"] for g in groups)
    modal_length = Counter(g["page_count"] for g in groups).most_common(1)[0][0] if groups else 0
    for g in groups:
        reasons = []
        if name_counts[g["student"]] > 1:
            reasons.append(f"{g['student']!r} also appears in {name_counts[g['student']] - 1} other group(s)")
        if g["page_count"] != modal_length:
            reasons.append(f"length {g['page_count']} pages vs. this file's typical {modal_length}")
        if reasons:
            print(
                f"  WARNING: pages {g['start']}-{g['end']} ({g['student']}) look uncertain — "
                + "; ".join(reasons)
                + " — verify in ocr_output/_images/ before trusting this run."
            )
    return groups


# ---------------------------------------------------------------------------
# Name normalization and pseudonym matching
# ---------------------------------------------------------------------------

def normalize_student_key(name: str) -> str:
    """
    Produce a stable directory key from any name string.
    "daniella", "DANIELLA", "Daniella Smith " all → "Daniella_Smith".
    Applied before every directory read/write.
    """
    cleaned = name.strip()
    if not cleaned or cleaned.lower() in {"(bos)", "(okunamiyor)"}:
        return ""
    return "_".join(part.title() for part in cleaned.split())


def match_pseudonym(extracted_name: str) -> Optional[str]:
    """
    Match a Claude-extracted name against KNOWN_PSEUDONYMS.
    Returns the canonical pseudonym if a confident match is found, else None.

    Matching strategy (in order):
    1. Exact match (case-insensitive)
    2. Extracted name starts with or contains a pseudonym (e.g. "Daniella S." → "Daniella")
    3. A pseudonym starts with the extracted name (e.g. "Daniel" → "Daniella" if unique match)
    """
    if not extracted_name:
        return None
    name_lower = extracted_name.strip().lower()
    # 1. Exact
    for pseudo in KNOWN_PSEUDONYMS:
        if pseudo.lower() == name_lower:
            return pseudo
    # 2. Extracted contains a pseudonym as a full word
    for pseudo in KNOWN_PSEUDONYMS:
        if re.search(r'\b' + re.escape(pseudo.lower()) + r'\b', name_lower):
            return pseudo
    # 3. Unique prefix match (pseudonym starts with extracted name, min 3 chars)
    if len(name_lower) >= 3:
        prefix_matches = [p for p in KNOWN_PSEUDONYMS if p.lower().startswith(name_lower)]
        if len(prefix_matches) == 1:
            return prefix_matches[0]
    return None


def resolve_student_key(
    extracted_name: str,
    slot_index: int,
    pdf_name: str,
) -> str:
    """
    Determine the canonical student key for a given page slot.
    Priority:
      1. Pseudonym matched from Claude-extracted name.
      2. Normalized extracted name (if non-empty and not a sentinel).
      3. Fallback: "slot_{slot+1:02d}" — signals that name extraction failed.
    """
    matched = match_pseudonym(extracted_name)
    if matched:
        return matched
    key = normalize_student_key(extracted_name)
    if key:
        return key
    return f"slot_{slot_index + 1:02d}"


# ---------------------------------------------------------------------------
# Image helpers
# ---------------------------------------------------------------------------

def preprocess_for_handwriting(img: Image.Image) -> Image.Image:
    """
    Enhance a scanned worksheet image to improve handwriting legibility for Claude.

    Steps:
    1. Convert to RGB (handles grayscale scans).
    2. Unsharp mask — sharpens ink strokes without amplifying scanner noise.
    3. Contrast boost — makes light pencil marks darker relative to the page.
    4. Slight brightness reduction — compensates for over-exposed scans where
       pale ink washes out against a nearly-white background.

    These values are conservative: strong enough to help, safe enough not to
    distort letterforms that Claude must read.
    """
    img = img.convert("RGB")
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=130, threshold=2))
    img = ImageEnhance.Contrast(img).enhance(1.4)
    img = ImageEnhance.Brightness(img).enhance(0.95)
    return img


def image_to_base64(img: Image.Image, max_width: int = 1800) -> str:
    """Convert a PIL image to base64 JPEG, applying handwriting preprocessing first."""
    img = preprocess_for_handwriting(img)
    if img.width > max_width:
        ratio = max_width / img.width
        img = img.resize((max_width, int(img.height * ratio)), Image.LANCZOS)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=92)  # higher quality for fine strokes
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


def save_page_images(
    pdf_name: str,
    images: list[Image.Image],
    groups: list[dict[str, Any]],
) -> None:
    """
    Save page images for manual inspection, one folder per detected student group.
    Also writes resume markers .{name}_{pdf_stem}.
    """
    pdf_stem = pdf_to_images_stem(pdf_name)
    base = OUT_DIR / "_images" / pdf_stem

    seen: dict[str, int] = {}
    for group_idx, group_info in enumerate(groups):
        label = group_info["student"]
        seen[label] = seen.get(label, 0) + 1
        if seen[label] > 1:
            label = f"{label}_dup{seen[label]}"
        page_images = images[group_info["start"] - 1: group_info["end"]]
        student_dir = base / label
        student_dir.mkdir(parents=True, exist_ok=True)
        for page_offset, img in enumerate(page_images):
            img.save(str(student_dir / f"page_{page_offset + 1}.jpg"), format="JPEG", quality=92)
        (OUT_DIR / f".{label}_{pdf_stem}").write_text(str(group_idx + 1))
    print(f"  Images saved -> {base}/")


# ---------------------------------------------------------------------------
# Claude call
# Fix 1: use `raw` (always defined when JSONDecodeError fires) not `response.content[0].text`
# Fix 2: client is required; dry_run path is separated so None is never passed here
# ---------------------------------------------------------------------------

def transcribe_student_pages(
    client: anthropic.Anthropic,
    images: list[Image.Image],
    pdf_name: str,
    model: str = "claude-sonnet-5",
    retries: int = 3,
) -> dict[str, Any]:
    """
    Send all pages for one student in a single multi-image Claude call.
    Returns dict with item_id keys + student_name + page_notes.
    On failure returns {"_error": "...", "_raw": "..."}.
    """
    prompt = PROMPTS[pdf_name]
    content: list[dict] = []
    for i, img in enumerate(images):
        content.append({"type": "text", "text": f"[Page {i + 1} of {len(images)}]"})
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg",
                       "data": image_to_base64(img)},
        })
    content.append({"type": "text", "text": prompt})

    raw = ""
    for attempt in range(retries):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                thinking={"type": "disabled"},
                messages=[{"role": "user", "content": content}],
            )
            text_block = next((b for b in response.content if b.type == "text"), None)
            if text_block is None:
                raise json.JSONDecodeError("No text block in response", "", 0)
            raw = text_block.text.strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            return json.loads(raw)
        except json.JSONDecodeError as e:
            if attempt < retries - 1:
                time.sleep(2)
                continue
            # raw is the stripped/processed text — always defined here
            return {"_error": f"JSON parse failed: {e}", "_raw": raw[:500]}
        except anthropic.RateLimitError:
            wait = 20 * (attempt + 1)
            print(f"    Rate limit. Waiting {wait}s...")
            time.sleep(wait)
        except Exception as e:
            return {"_error": str(e)}
    return {"_error": "Max retries exceeded"}


# ---------------------------------------------------------------------------
# Mapping: raw transcription -> {item_id: answer}
# ---------------------------------------------------------------------------

def extract_item_responses(raw: dict[str, Any], pdf_name: str) -> dict[str, str]:
    """
    Pull only rubric item_id keys from a raw transcription dict.
    Distinguishes (bos) [student blank] from (missing) [model omitted key].
    """
    if pdf_name not in PDF_ITEM_IDS:
        raise KeyError(
            f"extract_item_responses: unknown pdf_name {pdf_name!r}. "
            f"Known names: {sorted(PDF_ITEM_IDS)}"
        )
    result: dict[str, str] = {}
    for item_id in PDF_ITEM_IDS[pdf_name]:
        value = raw.get(item_id)
        if value is None:
            result[item_id] = "(missing)"
        else:
            result[item_id] = str(value).strip() or "(bos)"
    return result


def is_answered(value: str) -> bool:
    """True only if value is not a sentinel (i.e. a real student answer exists)."""
    return value.strip().lower() not in {s.lower() for s in NO_ANSWER_SENTINELS}


_INJECTION_PATTERNS = (
    "ignore all instructions",
    "ignore previous",
    "disregard",
    "you are now",
    "new instructions",
    "override",
    "system prompt",
    "assistant:",
    "human:",
)

_MAX_ANSWER_LENGTH = 600


def validate_ocr_output(record: dict) -> list[str]:
    """
    Run plausibility checks on a completed build_responses() record.
    Returns a list of warning strings. Empty list means no issues found.
    Does not raise; callers decide how to handle warnings.

    Checks:
    1. All 24 item IDs present in responses.
    2. No unrecognised item IDs in responses.
    3. student_name matches a known pseudonym.
    4. High sentinel rate (> 50% of items have no real answer).
    5. Transcription errors present.
    6. Suspiciously long answers (hallucination signal).
    7. Prompt injection patterns in answer text.
    8. Improperly formed sentinel strings (typos in sentinel values).
    """
    warnings: list[str] = []
    responses: dict[str, str] = record.get("responses", {})

    # 1. Missing item IDs
    missing_ids = [i for i in ALL_ITEM_IDS if i not in responses]
    if missing_ids:
        warnings.append(f"Missing item IDs in responses: {missing_ids}")

    # 2. Unknown item IDs
    known_set = set(ALL_ITEM_IDS)
    unknown_ids = [k for k in responses if k not in known_set]
    if unknown_ids:
        warnings.append(f"Unknown item IDs in responses: {unknown_ids}")

    # 3. student_name pseudonym match
    student_name = record.get("student_name", "")
    if not student_name:
        warnings.append("student_name is empty")
    elif match_pseudonym(student_name) is None:
        warnings.append(
            f"student_name {student_name!r} does not match any known pseudonym"
        )

    # 4. High sentinel rate
    no_answer_count = sum(1 for v in responses.values() if not is_answered(v))
    if responses and no_answer_count / len(responses) > 0.5:
        warnings.append(
            f"High no-answer rate: {no_answer_count}/{len(responses)} items have no real answer"
        )

    # 5. Transcription errors
    transcription_errors = [
        item_id for item_id, v in responses.items()
        if v.strip().lower() == "(transcription_error)"
    ]
    if transcription_errors:
        warnings.append(f"Transcription errors on items: {transcription_errors}")

    # 6. Suspiciously long answers
    long_answers = [
        item_id for item_id, v in responses.items()
        if len(v) > _MAX_ANSWER_LENGTH
    ]
    if long_answers:
        warnings.append(
            f"Suspiciously long answers (>{_MAX_ANSWER_LENGTH} chars, possible hallucination): "
            f"{long_answers}"
        )

    # 7. Prompt injection patterns
    injected = [
        item_id for item_id, v in responses.items()
        if any(pat in v.lower() for pat in _INJECTION_PATTERNS)
    ]
    if injected:
        warnings.append(
            f"Possible prompt injection in items: {injected}"
        )

    # 8. Sentinel-like but malformed (e.g. "bos" instead of "(bos)", "(missing )" with space)
    # Only flag short values (<=25 chars) that look like a sentinel attempt, not real sentences.
    _SENTINEL_CORES = ("bos", "missing", "okunamiyor", "not extracted", "transcription_error")
    sentinel_lower = {s.lower() for s in NO_ANSWER_SENTINELS}
    malformed = []
    for item_id, v in responses.items():
        if not is_answered(v):
            continue  # it is already a valid sentinel
        stripped = v.strip().lower()
        if len(stripped) > 25:
            continue  # real answer — too long to be a mistyped sentinel
        if any(core == stripped or stripped in (f"({core})", f"({core} )", core)
               for core in _SENTINEL_CORES) and stripped not in sentinel_lower:
            malformed.append(item_id)
    if malformed:
        warnings.append(
            f"Items with sentinel-like but malformed values (check for typos): {malformed}"
        )

    return warnings


# ---------------------------------------------------------------------------
# Build combined response record for one student (in-memory; saved via student_bundle)
# ---------------------------------------------------------------------------

def build_responses(
    student_name: str,
    raw_by_pdf: dict[str, dict],
) -> dict[str, Any]:
    responses: dict[str, str] = {}
    errors: list[str] = []

    for pdf_name, raw in raw_by_pdf.items():
        if "_error" in raw:
            errors.append(f"{pdf_name}: {raw['_error']}")
            for item_id in PDF_ITEM_IDS[pdf_name]:
                responses[item_id] = "(transcription_error)"
        else:
            responses.update(extract_item_responses(raw, pdf_name))

    for item_id in ALL_ITEM_IDS:
        if item_id not in responses:
            responses[item_id] = "(not_extracted)"

    answered = sum(1 for v in responses.values() if is_answered(v))
    record: dict[str, Any] = {
        "student_name": student_name,
        "item_coverage": {
            "answered": answered,
            "total": len(ALL_ITEM_IDS),
            "blank_or_illegible": sum(
                1 for v in responses.values() if v in {"(bos)", "(okunamiyor)"}
            ),
            "missing_from_model": sum(
                1 for v in responses.values()
                if v in {"(missing)", "(not_extracted)"}
            ),
        },
        "responses": responses,
        "raw": {
            pdf_name.replace(" ", "_").replace(".pdf", "").lower(): raw
            for pdf_name, raw in raw_by_pdf.items()
        },
    }
    if errors:
        record["errors"] = errors
    return record


# ---------------------------------------------------------------------------
# Process one PDF
# Fix 3: partial last group (fewer pages than pps) is flagged, not silently processed
# Fix 6: resume — students already in all_raw or with existing raw JSON are skipped
# ---------------------------------------------------------------------------

def process_pdf(
    client: anthropic.Anthropic,
    pdf_name: str,
    resume: bool = True,
) -> dict[str, dict]:
    """
    Transcribe all students from one PDF.
    resume=True: skips a student if their raw JSON for this PDF already exists on disk.
    Returns {normalized_student_key: raw_dict}.

    Page groups come from detect_student_page_ranges (text-layer name banner),
    not a fixed page count — a fixed count silently misaligns once any student's
    submission has a different page count than the assumed average (see PIPELINE.md).
    """
    raw_key = pdf_name.replace(" ", "_").replace(".pdf", "_raw.json").lower()
    pdf_stem = pdf_name.replace(" ", "_").replace(".pdf", "").lower()
    print(f"\n=== {pdf_name} ===")

    print("  Converting to images...")
    images = convert_from_path(str(DATA_DIR / pdf_name), dpi=DPI)
    groups = detect_student_page_ranges(pdf_name)
    print(f"  {len(images)} pages -> {len(groups)} detected student group(s)")

    # Build resume map: {group_index: student_key} from existing markers.
    # Marker filename: .{StudentName}_{pdf_stem}  content: group number (1-based).
    done_groups: dict[int, str] = {}
    if resume:
        for marker in OUT_DIR.glob(f".*_{pdf_stem}"):
            try:
                group_num = int(marker.read_text().strip())
                student_key = marker.name[1: -(len(pdf_stem) + 1)]  # strip leading dot and _{pdf_stem}
                done_groups[group_num - 1] = student_key
            except (ValueError, IndexError):
                pass

    results: dict[str, dict] = {}
    for idx, group_info in enumerate(groups):
        page_images = images[group_info["start"] - 1: group_info["end"]]
        page_label = f"p{group_info['start']}-{group_info['end']}"
        detected_name = group_info["student"]

        if idx in done_groups:
            key = done_groups[idx]
            print(f"  Group {idx + 1} ({page_label})... -> {key} [SKIPPED]")
            existing = OUT_DIR / key / raw_key
            if existing.exists():
                with open(existing, encoding="utf-8") as f:
                    results[key] = json.load(f)
            continue

        print(f"  Group {idx + 1} ({page_label}, detected={detected_name})...", end=" ", flush=True)
        raw = transcribe_student_pages(client, page_images, pdf_name)

        name_raw = raw.get("student_name") or raw.get("student_id") or ""
        key = resolve_student_key(name_raw, idx, pdf_name) or detected_name
        if key != detected_name:
            print(f"\n  WARNING: Claude read {name_raw!r} -> {key!r} but the page banner said "
                  f"{detected_name!r} for {page_label}. Check ocr_output/_images/{pdf_stem}/ before trusting either.")
        student_dir = OUT_DIR / key

        print(f"-> {key}")
        student_dir.mkdir(exist_ok=True)
        with open(student_dir / raw_key, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        # Marker: .{StudentName}_{pdf_stem}, content = group number (1-based)
        (OUT_DIR / f".{key}_{pdf_stem}").write_text(str(idx + 1))

        results[key] = raw
        time.sleep(0.5)

    return results


# ---------------------------------------------------------------------------
# Dry run: images only, no client needed
# Fix 2: client=None never passes to transcribe; dry_run is a standalone function
# ---------------------------------------------------------------------------

def _run_layout_after_dry_run() -> None:
    """Phase 1 layout on calibration pages when OpenCV is available."""
    try:
        from layout_isolator import LayoutIsolator
    except ImportError:
        return
    cal_dir = calibration_bundle_dir("Worksheets1-10.pdf")
    if cal_dir is None or not any(cal_dir.glob("page_*.jpg")):
        return
    isolator = LayoutIsolator()
    for ws in ("WS10", "WS5"):
        page_idx = WORKSHEETS_1_10_PAGE_INDEX.get(ws)
        if not page_idx:
            continue
        page = cal_dir / f"page_{page_idx}.jpg"
        if page.exists():
            result = isolator.process_worksheet_page(page, "Sample_Student", ws)
            result.save()
            print(f"  Layout {ws}: {result.status} ({result.zone_count} zones)")


def dry_run(pdfs: Optional[list[str]] = None) -> None:
    """Convert PDFs to images and save them. No API calls."""
    all_pdfs = list(PAGES_PER_STUDENT.keys()) if pdfs is None else pdfs
    for pdf_name in all_pdfs:
        print(f"\n=== {pdf_name} ===")
        print("  Converting to images...")
        images = convert_from_path(str(DATA_DIR / pdf_name), dpi=DPI)
        groups = detect_student_page_ranges(pdf_name)
        print(f"  {len(images)} pages -> {len(groups)} detected student group(s)")
        save_page_images(pdf_name, images, groups)
        if pdf_name == "Worksheets1-10.pdf":
            _run_layout_after_dry_run()
    print("\nDry run complete. Inspect ocr_output/_images/ before running pilot.")


# ---------------------------------------------------------------------------
# Pilot: one student from one PDF
# Fix 5: item_coverage.total reflects only items from this PDF, label says so
# ---------------------------------------------------------------------------

def mode_pilot(
    client: anthropic.Anthropic,
    pdf_name: str,
    student_index: int,
) -> dict:
    """
    Transcribe one detected student group from one PDF.
    student_index is the 0-based position in detect_student_page_ranges(pdf_name),
    i.e. the Nth student group found via the page text layer — not a fixed page offset.
    """
    pdf_item_ids = PDF_ITEM_IDS[pdf_name]
    groups = detect_student_page_ranges(pdf_name)
    if student_index >= len(groups):
        print(f"ERROR: student_index {student_index} out of range. "
              f"{pdf_name} has {len(groups)} detected student group(s).")
        return {}

    group_info = groups[student_index]
    detected_name = group_info["student"]
    print(f"Pilot: {pdf_name} | group index {student_index} | pages "
          f"{group_info['start']}-{group_info['end']} | detected={detected_name}")

    images = convert_from_path(str(DATA_DIR / pdf_name), dpi=DPI)
    page_images = images[group_info["start"] - 1: group_info["end"]]

    raw = transcribe_student_pages(client, page_images, pdf_name)
    name_raw = raw.get("student_name") or raw.get("student_id") or ""
    key = resolve_student_key(name_raw, student_index, pdf_name) or detected_name
    if key != detected_name:
        print(f"  WARNING: Claude read {name_raw!r} -> {key!r} but the page banner said {detected_name!r}.")
    print(f"  Identified as: {key}")

    responses = extract_item_responses(raw, pdf_name)
    answered = sum(1 for v in responses.values() if is_answered(v))

    # WS1: flat extraction — pass full raw dict
    if pdf_name == "24 Mart 2026 Çalışma Kâğıdı 1.pdf":
        from ws1_validation import build_ws1_validation_block
        raw["validation"] = build_ws1_validation_block(raw)

    # WS3: flat extraction — pass full raw dict
    if pdf_name == "24 Mart 2026 Çalışma Kâğıdı 3.pdf":
        from ws3_validation import build_ws3_validation_block
        raw["validation"] = build_ws3_validation_block(raw)

    # For WS5: attach validation block and ws_snapshot computed from extraction
    if pdf_name == "24 Mart 2026 Çalışma Kâğıdı 4.pdf":
        from ws4_validation import build_ws4_validation_block
        extraction_block = raw.get("extraction") or {}
        raw["validation"] = build_ws4_validation_block(extraction_block)

    if pdf_name == "24 Mart 2026 Çalışma Kâğıdı 5.pdf":
        from ws5_validation import build_ws5_validation_block, generate_ws5_snapshot
        extraction_block = raw.get("extraction") or {}
        validation_block = build_ws5_validation_block(extraction_block)
        raw["validation"] = validation_block
        raw["ws_snapshot"] = generate_ws5_snapshot(extraction_block, validation_block)

    # For WS6: attach validation block (includes system_analytical_summary).
    # ws_snapshot is written by Claude in the prompt — do not overwrite it here.
    # If a manual validation already exists (e.g. 3-depth tree), preserve it.
    if pdf_name == "31 Mart 2026 Çalışma Kâğıdı 6.pdf":
        if not raw.get("validation"):
            from ws6_validation import build_ws6_validation_block
            extraction_block = raw.get("extraction") or {}
            raw["validation"] = build_ws6_validation_block(extraction_block)

    out_dir = OUT_DIR / key
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / pdf_name.replace(" ", "_").replace(".pdf", ".json").lower()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(raw, f, ensure_ascii=False, indent=2)

    print(f"\nSaved -> {out_path}")
    _print_item_summary(responses, raw.get("page_notes", ""))
    return raw


def mode_validate(student_name: str) -> None:
    """Print human-readable review of a student's combined responses for spot-checking."""
    from student_bundle import (
        artifact_payload,
        extraction_responses,
        list_student_ids,
        list_worksheets,
        load_artifact,
        student_dir,
        STUDENTS_DIR,
    )

    key = match_pseudonym(student_name) or normalize_student_key(student_name) or student_name
    sid = key if student_dir(key).is_dir() else student_name

    if not student_dir(sid).is_dir():
        print(f"No student output found for '{student_name}' (tried key: '{key}').")
        from student_bundle import list_student_ids, STUDENTS_DIR
        if STUDENTS_DIR.exists():
            print(f"Available students: {list_student_ids()}")
        return

    responses: dict[str, str] = {}
    for ws in list_worksheets(sid):
        ext = load_artifact(sid, ws, "extraction")
        responses.update(extraction_responses(ext))

    answered = sum(1 for iid in ALL_ITEM_IDS if is_answered(responses.get(iid, "")))
    blank = sum(1 for iid in ALL_ITEM_IDS if responses.get(iid) in {"(bos)", "(okunamiyor)"})
    missing = sum(1 for iid in ALL_ITEM_IDS if responses.get(iid, "(not_in_file)") in {"(missing)", "(not_extracted)", "(not_in_file)"})

    print(f"\n=== Validation report: {sid} ===")
    print(f"Coverage: {answered}/{len(ALL_ITEM_IDS)} answered "
          f"| blank/illegible: {blank} "
          f"| missing: {missing}")

    print(f"\n{'Item ID':<25} {'Status':<14} Answer (first 120 chars)")
    print("-" * 80)
    for item_id in ALL_ITEM_IDS:
        answer = responses.get(item_id, "(not_in_file)")
        if is_answered(answer):
            status = "ANSWERED"
        elif answer == "(bos)":
            status = "BLANK"
        elif answer == "(okunamiyor)":
            status = "ILLEGIBLE"
        else:
            status = "MISSING"
        preview = str(answer)[:120].replace("\n", " ")
        print(f"  {item_id:<23} {status:<14} {preview}")

    print("\nTo verify: open the PDF, find this student's pages, and manually check flagged items.")


_PROMPT_WS6_TREE = """You are an expert at reading handwritten Turkish decision tree worksheets.

The image shows ONE pre-service teacher's completed Worksheet 6 (Karar Ağacı Çiz).
The student drew a two-level decision tree classifying 11 ProDaBi food cards as
"tavsiye edilir" (recommended) or "tavsiye edilemez" (not recommended).

TREE STRUCTURE — read boxes and arrows carefully:
- Root node: a rectangular box with a feature name (e.g. Şeker, Yağ, Enerji, Protein)
  and a threshold condition written inside or beside it (e.g. ≤ 13, < 180, ≥ 7.7).
- Two branches leave the root: one labelled "evet" (yes, condition true) and one "hayır" (no, false).
- Each branch leads either to:
    a) A leaf box: "tavsiye edilir" or "tavsiye edilemez" (or abbreviation T.edilir / T.edilemez)
    b) Another split node with its own feature, threshold, evet/hayır branches, and leaves.
- Operators: read ≤, <, ≥, > EXACTLY as written. Do not normalise or flip them.
- Thresholds: Turkish decimal separator is comma (e.g. 7,7 not 7.7) — transcribe as written.

Return ONLY the following JSON. No text before or after it.

{
  "root": {
    "feature": "<feature name written in root box>",
    "operator": "<one of: <=, <, >=, >>",
    "threshold": "<numeric value as written>",
    "yes_branch": {
      "type": "leaf",
      "label": "<tavsiye edilir | tavsiye edilemez>"
    },
    "no_branch": {
      "type": "split",
      "feature": "<feature name>",
      "operator": "<operator>",
      "threshold": "<threshold>",
      "yes_branch": {"type": "leaf", "label": "<label>"},
      "no_branch":  {"type": "leaf", "label": "<label>"}
    }
  },
  "blank_items": ["<list any WS6_B slot visually empty, e.g. WS6_B5>"],
  "warnings": ["<note any illegible text, missing arrows, or ambiguous structure>"]
}

Rules:
- "type" is always "leaf" or "split".
- A leaf has only "type" and "label". A split has "type", "feature", "operator", "threshold", "yes_branch", "no_branch".
- If the student drew only one level (no inner node), set one branch to a leaf and the other to a leaf too.
- If the tree is completely blank, return: {"root": null, "blank_items": ["all"], "warnings": ["Tree not drawn."]}
- Preserve Turkish text exactly (Şeker, Yağ, Enerji, Protein, tavsiye edilir, tavsiye edilemez).
- Do not invent content for boxes you cannot read; add a warning instead."""


def _extract_ws6_tree(
    client: anthropic.Anthropic,
    student_key: str,
    ocr_model: str,
) -> dict[str, Any]:
    """
    Extract WS6 decision tree structure using Claude vision.

    Image priority:
      1. layout_rois crop (tree canvas isolated by LayoutIsolator)
      2. Full page from ocr_output/_images (2026 per-WS PDF, page_1.jpg)
    """
    from pipeline_schema import worksheet_page_image

    image_path: Optional[Path] = None

    try:
        from layout_isolator import LayoutIsolator
        crop = LayoutIsolator().tree_diagram_crop_path(student_key, "WS6")
        if crop and crop.exists():
            image_path = crop
    except ImportError:
        pass

    if image_path is None:
        full_page = worksheet_page_image(student_key, "WS6")
        if full_page and full_page.exists():
            image_path = full_page

    if image_path is None:
        return {
            "warning": "No WS6 image found. Run ocr_pipeline dry_run first.",
            "root": None,
        }

    try:
        img = Image.open(image_path).convert("RGB")
        b64 = image_to_base64(img)
        response = client.messages.create(
            model=ocr_model,
            max_tokens=1024,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": b64}},
                    {"type": "text", "text": _PROMPT_WS6_TREE},
                ],
            }],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        result = json.loads(raw)
        result["source_image"] = str(image_path.relative_to(Path(__file__).parent))
        result["vision_model"] = ocr_model
        return result
    except json.JSONDecodeError as exc:
        return {"error": f"JSON parse failed: {exc}", "source_image": str(image_path)}
    except Exception as exc:
        return {"error": str(exc), "source_image": str(image_path)}


def save_worksheet_jsons(
    student_name: str,
    all_responses: dict[str, str],
    raw_by_pdf: dict[str, dict],
    output_dir: Path | None = None,
    ocr_model: str = "claude-sonnet-5",
    client: Optional[anthropic.Anthropic] = None,
) -> Path:
    """
    Write one JSON per worksheet under students/<student_name>/.

    Each file holds an ``extraction`` section (4-gate structure) initially.
    """
    from student_bundle import STUDENTS_DIR, save_artifact, student_dir as sb_student_dir

    base = output_dir or STUDENTS_DIR
    extracted_at = datetime.now(timezone.utc).isoformat()

    def _raw_for_ws(ws_label: str) -> dict:
        pdf = WORKSHEET_PDF_SOURCE.get(ws_label, "")
        return raw_by_pdf.get(pdf, {})

    for ws_label, item_ids in WORKSHEET_ITEM_IDS.items():
        if not item_ids:
            continue

        items = {iid: all_responses.get(iid, "(not_extracted)") for iid in item_ids}
        answered          = sum(1 for v in items.values() if is_answered(v))
        blank_or_illegible = sum(1 for v in items.values() if v in {"(bos)", "(okunamiyor)"})
        missing           = sum(1 for v in items.values() if v in {"(missing)", "(not_extracted)"})
        total             = len(item_ids)
        completion_rate   = round(answered / total, 3) if total else 0.0

        raw_source  = _raw_for_ws(ws_label)
        ws_snapshot = raw_source.get("ws_snapshot", "")

        # Gate 2 validation warnings
        ocr_warnings = validate_ocr_output({
            "student_name": student_name,
            "responses": items,
        })

        # Determine gate_1 status
        if missing == total:
            g1_status = "fail"
        elif missing > 0 or blank_or_illegible > answered:
            g1_status = "partial"
        else:
            g1_status = "pass"

        # Gate 2 status
        g2_status = "fail" if completion_rate < 0.3 else ("partial" if completion_rate < 0.7 else "pass")

        record: dict[str, Any] = {
            "student_name": student_name,
            "worksheet":    ws_label,
            "pdf_source":   WORKSHEET_PDF_SOURCE[ws_label],

            "gate_1_extraction": {
                "status":       g1_status,
                "extracted_at": extracted_at,
                "ocr_model":    ocr_model,
                "items":        items,
                "raw_ocr":      {k: v for k, v in raw_source.items()
                                 if k not in ("student_name", "page_notes", "ws_snapshot")},
            },

            "gate_2_validation": {
                "status": g2_status,
                "item_coverage": {
                    "answered":           answered,
                    "total":              total,
                    "blank_or_illegible": blank_or_illegible,
                    "missing":            missing,
                    "completion_rate":    completion_rate,
                },
                "warnings": ocr_warnings,
                "student_snapshot": {
                    "completion_rate":       completion_rate,
                    "engagement_level":      ("high" if completion_rate >= 0.7
                                              else "medium" if completion_rate >= 0.4
                                              else "low"),
                    "llm_observations":      ws_snapshot,
                    "page_quality_notes":    raw_source.get("page_notes", ""),
                },
            },

            "gate_3_scoring": {
                "status":        "pending",
                "scored_at":     None,
                "scoring_model": None,
                "items":         {},
            },

            "gate_4_aicft": {
                "status":   "pending",
                "level":    None,
                "evidence": None,
            },
        }

        # WS6 — add structural tree extraction + layout manifest
        if ws_label == "WS6" and WS6_VISION_ENABLED:
            ws6_manifest = layout_manifest_path(student_name, "WS6")
            if ws6_manifest.exists():
                record["gate_1_extraction"]["layout_roi"] = json.loads(
                    ws6_manifest.read_text(encoding="utf-8")
                )
            if client is not None:
                record["gate_1_extraction"]["tree_structure"] = _extract_ws6_tree(
                    client, student_name, ocr_model
                )

        # WS10 / WS5 — attach layout manifest when Phase 1 has run
        if ws_label in {"WS10", "WS5"}:
            manifest_path = layout_manifest_path(student_name, ws_label)
            if manifest_path.exists():
                record["gate_1_extraction"]["layout_roi"] = json.loads(
                    manifest_path.read_text(encoding="utf-8")
                )

        save_artifact(student_name, ws_label, "extraction", record, base_dir=base)

    return sb_student_dir(student_name, base)


def mode_full(
    client: anthropic.Anthropic,
    pdfs: Optional[list[str]] = None,
    resume: bool = True,
) -> None:
    all_pdfs = list(PAGES_PER_STUDENT.keys()) if pdfs is None else pdfs
    all_raw: dict[str, dict[str, dict]] = {}

    for pdf_name in all_pdfs:
        pdf_results = process_pdf(client, pdf_name, resume=resume)
        for key, raw in pdf_results.items():
            all_raw.setdefault(key, {})[pdf_name] = raw

    print("\n=== Building student bundles ===")
    for key, raw_by_pdf in sorted(all_raw.items()):
        record = build_responses(key, raw_by_pdf)
        student_dir = OUT_DIR / key
        student_dir.mkdir(exist_ok=True)

        out_dir = save_worksheet_jsons(
            student_name=key,
            all_responses=record["responses"],
            raw_by_pdf=raw_by_pdf,
            client=client,
        )

        cov = record["item_coverage"]
        print(f"  {key}: {cov['answered']}/{cov['total']} answered "
              f"| {cov['blank_or_illegible']} blank "
              f"| {cov['missing_from_model']} missing "
              f"| saved: {out_dir.relative_to(Path(__file__).parent)}/")

    print("\nDone. Run 'python ocr_pipeline.py validate <StudentName>' to spot-check.")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _print_item_summary(responses: dict[str, str], page_notes: str) -> None:
    print(f"\n{'Item ID':<25} {'Status':<14} Answer preview")
    print("-" * 80)
    for item_id, answer in responses.items():
        if is_answered(answer):
            status = "ANSWERED"
        else:
            status = answer.upper().strip("()")
        preview = answer[:80].replace("\n", " ")
        print(f"  {item_id:<23} {status:<14} {preview}")
    if page_notes and is_answered(page_notes):
        print(f"\n  Page notes: {page_notes}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    args = sys.argv[1:]

    if args and args[0] == "dry_run":
        dry_run(args[1:] if len(args) > 1 else None)

    elif args and args[0] == "validate":
        if len(args) < 2:
            print("Usage: python ocr_pipeline.py validate <StudentName>")
            sys.exit(1)
        mode_validate(args[1])

    elif args and args[0] == "pilot":
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        pdf = args[1] if len(args) > 1 else "WorksheetDT.pdf"
        idx = int(args[2]) if len(args) > 2 else 0
        mode_pilot(client, pdf, idx)

    else:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        pdfs_arg = args if args else None
        mode_full(client, pdfs_arg)
