# WS6 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 6** (two-level decision tree on food cards).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS6_rubric.json` |
| Food cards | `data/prodabi_food_cards.csv` (11 cards — **same set as WS5**) |
| Answer key | `worksheets/WS6/answer_key.json` |
| Mapping | `mappings/WS6_AICFT_mapping.json` |
| Responses | `students/<student_id>/WS6/extraction.json` (`WS6_B1`–`B13`) |
| Validation | `students/<student_id>/WS6/validation.json` — **required** |

**Pipeline group:** B.

---

## Construct

Student **draws** a **çift seviyeli (two-level)** binary decision tree using the **11 fixed ProDaBi food data cards** (green clip = tavsiye edilebilir). OCR captures 13 structured fields; Python validates the student's tree against the same CSV as WS5.

**No fixed tree answer.** `example_answer` in the rubric and answer key are Sample_Student fixtures only. Students may choose different features, thresholds, and values; scoring checks notation, structure, complementary operators, and required leaf labels — not match to a canonical tree.

### Field map (OCR)

| Fields | Role |
|--------|------|
| B1, B2 | Root feature + threshold |
| B3, B4 | Root evet / hayır branch labels |
| B6, B7 | Inner feature + threshold (evet subtree) — **must differ from B1** |
| B8, B9 | Inner branch labels |
| B10, B11 | Inner subtree leaves |
| B13 | Root hayır branch leaf |
| B5, B12 | Optional extra leaves depending on tree shape |

---

## Acceptable features

enerji, yağ, doymuş yağ, karbonhidrat, şeker, protein, tuz (and English aliases). Parsed via `food_cards_data.resolve_feature()`.

Threshold cells B2/B7 accept `operatör + sayı` (feature from B1/B6) or full `özellik operatör sayı`.

---

## Operator rules (critical — same as WS5)

| True / evet (B2, B7) | Required false / hayır (B4, B9) |
|----------------------|--------------------------------|
| `≤` | `>` |
| `<` | `≥` |
| `≥` | `<` |
| `>` | `≤` |

| Credit | Rule |
|--------|------|
| **Full** | Complementary pairs on both splits; all 11 cards classifiable |
| **Partial (0.5)** | Operator missing on threshold, or hayır label op does **not** complement evet op (e.g. `< 10` with `> 10` instead of `≥ 10`) |
| **Zero** | Unparseable threshold or blank required fields |

Inclusive (`≤`, `≥`) and strict (`<`, `>`) operators are both valid when paired correctly with the complement on the hayır branch.

Python: `food_cards_data.operators_are_complementary()` + `ws6_validation.py`.

---

## MCR and two-level trees

Python computes **MCR = errors / 11** by walking the student's tree over food cards (`ws6_validation.compute_tree_mcr`).

**Important:** Students may build a **two-level tree even when MCR = 0**. This is **not penalized** — `tree_structure` full credit does not require MCR > 0 or minimum MCR.

---

## Scoring items

| Rubric item | Check | Full credit |
|-------------|-------|-------------|
| `WS6_root_feature` | feature | Valid nutrient from dataset |
| `WS6_root_threshold` | `threshold_with_operator` | B2: operator + value; B4 complements when present |
| `WS6_root_labels` | branch labels | evet + hayır present; hayır op complements B2 |
| `WS6_inner_feature` | feature | Valid feature **≠** B1 |
| `WS6_inner_threshold` | `threshold_with_operator` | B7: same rules as B2 |
| `WS6_inner_labels` | branch labels | evet + hayır; B9 complements B7 |
| `WS6_leaves` | `leaf_consistency_with_tree_logic` | Required leaves for tree shape labeled (tavsiye edilir/edilemez) |
| `WS6_tree_structure` | `tree_validity` | 4/4: depth, 2 features, leaves, operators cover all 11 cards |

Partial credit: threshold/labels (0.5 on mismatch), leaves (one missing), tree_structure (2–3 of 4 components).

Authority: `validation.json` → `deterministic_checks.<item_id>`.

`WS6_tree_structure`: `need: 4`, `partial_on: 2`.

---

## Validation / vision

- **Primary:** OCR fields B1–B13 — validation does **not** require vision `tree_structure` if fields are present.
- Vision crop (`layout_roi` / `dt_vision_pipeline`) is supplementary.
- If OCR sparse, `review: true` and lower confidence.

---

## Cross-worksheet

**WS7** Part 2 rules are graded against **this pre-service teacher's WS6 tree**. **WS5** uses the same food-card reference for threshold exploration.

---

## Review flags

- Complementary operator mismatch on B2/B4 or B7/B9 → partial on threshold/labels; `tree_structure.operators` false.
- `unclassified > 0` in validation `mcr` → operator/leaf gap.
- Single-level tree only → `tree_structure.depth` false (çift seviyeli expected).
- MCR=0 with two levels → **no penalty**.

---

## Insufficient evidence (zero hallucination)

If the extracted response is blank, illegible (`(bos)`, `(okunamiyor)`, `(missing)`), or clearly unrelated to the item:

- Do **not** invent or guess a score from plausibility.
- Assign score **0**, set `"review": true`, and write the rationale as **yetersiz kanıt — [specific reason]**.
- This matches the portfolio layer: when evidence is missing, mark insufficient — do not infer competence.
