# WS5 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 5** (threshold grid on food cards).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS5_rubric.json` |
| Food cards | `data/prodabi_food_cards.csv` (11 ProDaBi classroom cards) |
| Answer key | `worksheets/WS5/answer_key.json` |
| Mapping | `mappings/WS5_AICFT_mapping.json` |
| Responses | `students/<student_id>/WS5/extraction.json` |
| Validation | `students/<student_id>/WS5/validation.json` — **required** |

**Pipeline group:** B.

---

## Construct

Pre-service teachers build decision trees from **11 fixed food data cards** (green clip = tavsiye edilebilir, red = tavsiye edilemez). For each threshold trial they record:

1. Threshold expression: **variable + operator + value** (e.g. `şeker ≤ 10`, `yağ ≤ 8`, `enerji > 180`)
2. Correct classification count
3. Error (misclassification) count
4. MCR = errors / 11

Final item **B25** selects the best threshold with data-based justification.

**No fixed threshold answers.** `example_answer` in the rubric and answer key are Sample_Student fixtures only. Any acceptable feature + operator + value is valid if counts match the dataset.

---

## Operator rules (critical)

| True / evet side | Required false / hayır side |
|------------------|----------------------------|
| `≤` | `>` |
| `<` | `≥` |
| `≥` | `<` |
| `>` | `≤` |

The unwritten branch always uses the **complement** so all 11 cards are classified.

| Example written | False branch implied |
|-----------------|---------------------|
| `şeker ≤ 10` | `> 10` |
| `şeker < 10` | `≥ 10` |
| `yağ ≤ 8` | `> 8` |

**Invalid pairing** (e.g. `<` with implicit `>` instead of `≥`) yields wrong counts — not full credit.

Python authority: `food_cards_data.complementary_operator()` + `ws5_validation.py`.

---

## Acceptable features

enerji, yağ, doymuş yağ, karbonhidrat, şeker, protein, tuz (and English aliases). Parsed via `food_cards_data.resolve_feature()`.

---

## Row scoring (`WS5_row1` … `WS5_row5`, optional `WS5_row6`)

Each row item aggregates four cells (threshold, doğru, hata, MCR).

| Credit | Rule |
|--------|------|
| **Full (1.0)** | Parseable threshold; doğru + hata = **11**; MCR ≈ hata/11; counts match `prodabi_food_cards.csv` for that threshold with complementary false branch |
| **Partial (0.5)** | Parseable threshold; arithmetic internally consistent but **counts do not match** the dataset |
| **Zero** | Unparseable threshold, incomplete row, or arithmetic inconsistent |
| **Not attempted** | All four cells blank |

Inclusive (`≤`, `≥`) and strict (`<`, `>`) operators are both valid when the complement rule is applied correctly.

Authority: `validation.json` → `deterministic_checks.WS5_rowN`.

Do not re-count cards unless validation is missing.

### Optional row 6 (`WS5_row6`)

Same rules if filled; not required for full worksheet credit.

---

## B25 — final choice (minimum misclassification)

**Method:** For each grid trial, assume per-row counts and MCR are **arithmetically valid** (row partial or full). The pre-service teacher should **prefer the threshold with the lowest error count** among those trials.

| Credit | Rule |
|--------|------|
| **Full** | B25 names a threshold from the grid with the **minimum error count** |
| **Partial (0.5)** | Threshold is in the grid but **not** among minimum-error trials |
| **Zero** | Blank, or threshold not found in any grid row |
| **Tie** | Two+ trials share minimum errors → **any** tied choice is full credit |
| **Tie flag** | Pre-service teacher names only one tied option → `review: true`, `tie_note` lists alternatives (no score penalty) |

Python authority: `validate_ws5_b25()` → `deterministic_checks.WS5_B25`.

Optional semantic check (LLM): brief justification with error/MCR numbers; not required for full credit if deterministic check passes.

---

## Review flags

- Row partial with `review_reason: counts_inconsistent_with_food_cards` → counts wrong but notation/arithmetic OK.
- B25 `tie_at_minimum` with `other_tied_thresholds` → note for reviewer; score unchanged if chosen row is tied for minimum.
- B25 threshold not in grid → zero + review.

---

## Insufficient evidence (zero hallucination)

If the extracted response is blank, illegible (`(bos)`, `(okunamiyor)`, `(missing)`), or clearly unrelated to the item:

- Do **not** invent or guess a score from plausibility.
- Assign score **0**, set `"review": true`, and write the rationale as **yetersiz kanıt — [specific reason]**.
- This matches the portfolio layer: when evidence is missing, mark insufficient — do not infer competence.

**Note:** This does not override B25 “assume per-row counts valid” when row data is present and arithmetically consistent.
