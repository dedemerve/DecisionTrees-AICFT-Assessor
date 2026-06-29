# WS4 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 4** (searching for the best threshold value).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS4_rubric.json` |
| Answer key | `worksheets/WS4/answer_key.json` |
| Mapping | `mappings/WS4_AICFT_mapping.json` |
| Validity | `worksheets/WS4/validity_notes.json` |
| Responses | `students/<student_id>/WS4/extraction.json` |

**Pipeline group:** A.

---

## Construct

Students improve a fat threshold on sorted food cards, identify misclassified items, reflect on fewer errors, evaluate Pia's claim about equal fat values, and state an energy threshold they learned.

Handwriting and OCR are imperfect — score on rubric intent, not literal transcription perfection.

---

## Items

| Item | Worksheet task | Scoring |
|------|----------------|---------|
| `WS4_B1` | Draw new threshold line **between avocado and french fries** | **Interpretive.** Visual line or text naming avokado + patates kızartması as the boundary. |
| `WS4_B2` | Mark/write **four** misclassified foods on images | **Deterministic** `unordered_token_set`. All four required: jelibon, kraker, yulaf, avokado. Order irrelevant. **Three foods = zero.** |
| `WS4_B3` | State that **misclassification decreased** after the new threshold | **Interpretive.** Gist suffices (*daha az yanlış sınıflandırma*). |
| `WS4_B4` | Evaluate Pia — apple & raspberry jam have **same fat** | **Interpretive.** Full: agrees Pia is haklı **and** cites equal fat values. **Reject** meta answers like *bazı öğrenciler aynı yanlışı yaptı* without same-fat reasoning. |
| `WS4_B5` | Energy threshold learned from cards | **Deterministic** `numeric_range` **160–2223** inclusive. Any value in range is correct. |

### B1 guidance

Primary evidence is a **line drawn between avocado and french fries** (yeni eşik). Accept written references to that pair as threshold boundary when OCR captures text instead of the drawing.

### B2 guidance

Accept marks on images **or** written lists. All four token groups must match. Do not award credit for only three foods even if handwriting is unclear on the fourth — flag `review: true` instead.

### B4 guidance

Full credit requires **both** agreement with Pia **and** same-fat-value reasoning (elma / ahududu reçeli). Partial (`partial_on: 1`): one of the two components only.

---

## Competency inference

| Item | Primary LO | Notes |
|------|------------|-------|
| B1, B5 | LO3.2.2 | Threshold placement / parameter selection (Deepen) |
| B2 | LO3.2.2 | Identifying misclassified cases |
| B3 | LO3.2.2 | Reflecting on model performance improvement |
| B4 | LO3.2.2 | Evaluating peer claim about equal feature values |

Strength ceilings per `mappings/WS4_AICFT_mapping.json`.

---

## Review flags

- B1 visual line not visible in OCR → `review: true`; do not invent placement.
- B2 only three of four foods legible → `review: true` before scoring zero.
- B5 numeric OCR uncertain → `review: true`; use Python `numeric_range` when a number is extracted.
