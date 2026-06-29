# WS10 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 10** (systematic energy threshold search).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS10_rubric.json` |
| Reference dataset | `data/ws10_energy_reference.json` |
| Answer key | `worksheets/WS10/answer_key.json` |
| Responses | `students/<student_id>/WS10/extraction.json` |
| Numeric table | `extraction.json` → `numeric_table`, `htr_status` |

**Pipeline group:** A. **Scoring authority:** `ws10_validation.py` (exact integers).

---

## Construct

Fixed ProDaBi v4 worksheet: **8 foods**, **7 printed threshold rows**, **1 optimum blank**.

Printed thresholds (left column, not scored): `28, 69, 219, 346, 359, 408, 489`.

Students fill **misclassification counts** (right column) and **optimum threshold** below the table.

---

## Blank number → response (worksheet layout)

Printed **blank number** (1–8) maps to `WS10_B1`–`WS10_B8`. Score the **handwritten response** only.

| Blank # | Field | Correct response |
|---------|-------|------------------|
| 1 | `WS10_B1` | **4** |
| 2 | `WS10_B2` | **3** |
| 3 | `WS10_B3` | **2** |
| 4 | `WS10_B4` | **3** |
| 5 | `WS10_B5` | **2** |
| 6 | `WS10_B6` | **1** |
| 7 | `WS10_B7` | **2** |
| 8 | `WS10_B8` | **408** |

Blanks 1–7 sit in the table’s response column (left column thresholds 28…489 are printed, not scored).

## Single correct answer per blank

Classification rule on reference cards: **enerji < eşik → tavsiye edilir**; **≥ eşik → tavsiye edilmez**.

No partial credit — exact integer match only.

---

## Blocked worksheet

If `numeric_table` not captured or `htr_status` = error → `blocked: true`, do not score.

---

## HTR mapping

`ws10_table_extractor._derive_responses`: row HTR → B1–B7; optimum blank crop → B8.

---

## Review flags

- Unparseable number → `review: true`
- B8 ≠ 408 when table row 6 has minimum count → still score B8 independently (each blank exact)
