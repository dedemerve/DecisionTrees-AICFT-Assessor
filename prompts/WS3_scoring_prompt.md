# WS3 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 3** (Leo's fat rule + student energy threshold).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS3_rubric.json` |
| Answer key | `worksheets/WS3/answer_key.json` |
| Mapping | `mappings/WS3_AICFT_mapping.json` |
| Validity | `worksheets/WS3/validity_notes.json` |
| Responses | `students/<student_id>/WS3/extraction.json` |

**Pipeline group:** A.

---

## Construct

**Part 1 (B1–B6):** Apply Leo's pre-defined rule — **fat ≤ 8.0 g** → recommend; **> 8 g** → not recommended — to three foods.

**Part 2 (B7–B8):** Student defines their own **energy (enerji)** threshold with complementary operators.

---

## Part 1 — classification + reasoning

| Item | Type | Full credit requires |
|------|------|---------------------|
| `WS3_B1` | classification | Not recommended label (food 1: fat > 8g) |
| `WS3_B2` | reasoning | Fat feature cited **and** comparison to 8g threshold |
| `WS3_B3` | classification | Recommended label (food 2: fat ≤ 8g) |
| `WS3_B4` | reasoning | Fat feature cited **and** comparison to 8g |
| `WS3_B5` | classification | Not recommended (food 3: fat > 8g) |
| `WS3_B6` | reasoning | Fat feature cited **and** comparison to 8g |

**Classification items:** accept spelling variants (*tavsiye edilemez/edilmez*, *önerilmez*, *uygun değil*). Wrong direction → zero.

**Reasoning items:** `need: 2`, `partial_on: 1`. One component only → partial (0.5). Specific gram value need not match OCR exactly if threshold comparison is clear.

---

## Part 2 — student threshold (B7–B8)

| Item | Variable | Operator | Partial rule |
|------|----------|----------|--------------|
| `WS3_B7` | enerji | ≤ (küçük eşit, en fazla, <=) | 0.5 if variable correct but operator missing/wrong |
| `WS3_B8` | enerji | > (büyük, fazla, üstünde) | Same; **must be complementary to B7** (same numeric value, opposite operator) |

Wrong variable (e.g. şeker) → **zero** regardless of operator.

Numeric threshold value is **student-chosen** — any defensible number is acceptable if operators and variable are correct.

---

## Competency inference

Primary LO for scored items: **LO3.2.2** (Deepen — apply thresholds to classify). Strength ceiling **moderate**.

| Item pattern | Inference |
|--------------|-----------|
| B1/B3/B5 full | Direct application of fixed rule |
| B2/B4/B6 full | Interpretation + justification |
| B7–B8 full | Parameter selection (student-defined boundary) |

Supporting LO3.1.2 only when reasoning explicitly names variable/feature vocabulary without application.

---

## Review flags

- Blank Part 2 with filled Part 1 → score Part 1 normally; flag B7/B8 for review if OCR shows partial text.
- B7/B8 same operator on both → likely student error; score accordingly, `review: true` if ambiguous.
