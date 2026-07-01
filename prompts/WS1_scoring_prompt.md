# WS1 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 1** (nutrition-label terminology).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS1_rubric.json` |
| Answer key | `worksheets/WS1/answer_key.json` |
| Mapping | `mappings/WS1_AICFT_mapping.json` |
| Validity | `worksheets/WS1/validity_notes.json` |
| Responses | `students/<student_id>/WS1/extraction.json` |

**Pipeline group:** A (no `validation.json`).

---

## Construct

Eleven numbered items on the **nutrition label** worksheet (`WS1_B1`–`WS1_B11` = printed **1–11**):

| Region | Items | Content |
|--------|-------|---------|
| Diagram callouts | B1–B4 | etiket, nesne, özellik/karakteristik/değişken, değer |
| Paragraph fill-ins | B5–B11 | nesne ×2, özellik/karakteristik/değişken, count 7, nutrient list, example food, etiket olarak |

This is **vocabulary recall in context**, not procedural modelling.

---

## Terminology sets (rubric `equivalence_sets`)

| Set | Kabul edilen |
|-----|----------------|
| `object` | **nesne** |
| `feature_variable` | **özellik**, **karakteristik**, **değişken** |
| `label` | **etiket**, **etiket olarak** |
| `feature_value` | **değer**, **özelliğin değeri**, … |

Her madde yalnızca kendi `accept_sets` listesini kullanır — çapraz eşleme yok (ör. B5/B6 yalnızca `object`).

---

## Items (11 scored)

| Item | # | Region | Evaluation | Example |
|------|---|--------|------------|---------|
| `WS1_B1` | 1 | diagram | `label` | etiket |
| `WS1_B2` | 2 | diagram | `object` | nesne |
| `WS1_B3` | 3 | diagram | `feature_variable` | özellik |
| `WS1_B4` | 4 | diagram | `feature_value` | değer |
| `WS1_B5` | 5 | paragraph | `object` | nesne |
| `WS1_B6` | 6 | paragraph | `object` | nesne |
| `WS1_B7` | 7 | paragraph | `feature_variable` | özellik |
| `WS1_B8` | 8 | paragraph | count | 7 / yedi |
| `WS1_B9` | 9 | paragraph | `unordered_token_set` | 7 besin adı |
| `WS1_B10` | 10 | paragraph | `single_concept` | Fındıklı Gofret |
| `WS1_B11` | 11 | paragraph | `label` | etiket olarak |

---

## Competency inference

All items map primarily to **LO3.1.2** (Acquire). Strength ceiling typically **moderate**; B9 may be **strong** when full nutrient list given.

**Do not** map WS1 to LO3.2.2 (Deepen).

---

## Review flags

- `review: true` if OCR garbles Turkish characters.
- `review: true` if B9 lists fewer than 3 recognizable nutrient tokens.

---

## Insufficient evidence

Blank, illegible, or unrelated → score **0**, `review: true`, rationale **yetersiz kanıt — …**.
