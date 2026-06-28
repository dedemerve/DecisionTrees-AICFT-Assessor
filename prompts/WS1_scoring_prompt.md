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

Seven printed blanks (5–11) on a **nutrition label** paragraph. Students supply short Turkish terms linking the food-recommendation scenario to ML vocabulary: **object (nesne)**, **feature (özellik)**, **variable/label (değişken/etiket)**, feature count, nutrient list, example food, and recommendation-as-label.

This is **vocabulary recall in context**, not procedural modelling. Do not treat WS1 as a formula or threshold worksheet.

---

## Terminology equivalence (rubric `equivalence_sets`)

| Set | Accept either term |
|-----|-------------------|
| `object_feature` | nesne **or** özellik (+ aliases: varlık, örnek, karakteristik, …) |
| `variable_label` | değişken **or** etiket (+ aliases: label, etiket olarak, …) |

Python applies `any_of_tokens` deterministically when `check` is set. LLM competency inference should note which term the student used without penalizing valid equivalents.

---

## Items (7 scored)

| Item | Blank | Evaluation | Scoring |
|------|-------|------------|---------|
| `WS1_B1` | 5 | `any_of_tokens` → `variable_label` | Deterministic. Example: *etiket* |
| `WS1_B2` | 6 | `any_of_tokens` → `object_feature` | Deterministic. Example: *nesne* |
| `WS1_B3` | 7 | `any_of_tokens` → either set | Deterministic. Example: *özellik* |
| `WS1_B4` | 8 | `any_of_tokens` — feature count | Deterministic. Accept **7** or **yedi** only (nutrition table rows). |
| `WS1_B5` | 9 | `unordered_token_set` — nutrient names | Deterministic token groups; order-free. Need ≥5 of 7 groups for full; ≥3 partial. Groups: enerji, yağ, doymuş yağ, karbonhidrat, şeker, protein, tuz. |
| `WS1_B6` | 10 | `single_concept` — example food object | Semantic. e.g. *Fındıklı Gofret* or any food named on the sheet. |
| `WS1_B7` | 11 | `any_of_tokens` → `variable_label` | Deterministic + optional outcome phrases (*tavsiye edilir/edilmez*). Example: *etiket* |

---

## Competency inference

All items map primarily to **LO3.1.2** (Acquire — conceptual vocabulary for data-driven classification). Strength ceiling is typically **moderate**; WS1 demonstrates **naming**, not application.

| Guidance | Action |
|----------|--------|
| Full credit on terminology items | LO3.1.2 **moderate** when student uses term correctly in context |
| Partial on B5 (3–4 nutrients) | LO3.1.2 **weak** |
| B4 wrong count | Do not infer LO3.2.x — no application demonstrated |

**Do not** map WS1 to LO3.2.2 (Deepen) — no threshold or model decision is required.

---

## Validity constraints

- Fill-in recall ≠ procedural competence — keep strength at mapping ceiling.
- Feature count accepts only 7 or yedi (see `validity_notes.json`).
- No cross-worksheet dependencies.

---

## Review flags

- `review: true` if OCR garbles Turkish characters (ş/ğ/ı) and token match is uncertain.
- `review: true` if B5 lists fewer than 3 recognizable nutrient tokens.
