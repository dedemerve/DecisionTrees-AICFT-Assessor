# WS6 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 6** (draw a 2-level decision tree).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS6_rubric.json` |
| Answer key | `worksheets/WS6/answer_key.json` |
| Mapping | `mappings/WS6_AICFT_mapping.json` |
| Validity | `worksheets/WS6/validity_notes.json` |
| Responses | `students/<student_id>/WS6/extraction.json` (fields `WS6_B1`–`WS6_B13`) |
| Validation | `students/<student_id>/WS6/validation.json` — **required** |

**Pipeline group:** B.

---

## Construct

Student **draws** a binary decision tree on food data. OCR captures **13 structured fields** plus holistic tree validity. Scoring uses **rubric aggregate items** (not individual B-fields in `scoring.json`).

---

## Scoring items (rubric keys)

| Rubric item | OCR fields | Focus |
|-------------|------------|-------|
| `WS6_root_feature` | `WS6_B1` | Valid food feature (şeker, yağ, enerji, protein) |
| `WS6_root_threshold` | `WS6_B2` | Operator + numeric value; partial if operator missing |
| `WS6_root_labels` | `WS6_B3`, `WS6_B4` | evet/hayır (or yes/no) branch labels |
| `WS6_inner_feature` | `WS6_B6` | Second feature — **must differ from root** |
| `WS6_inner_threshold` | `WS6_B7` | Operator + value on inner node |
| `WS6_inner_labels` | `WS6_B8`, `WS6_B9` | Inner branch labels |
| `WS6_leaves` | `WS6_B5`, `B10`–`B13` | Leaf class labels (*tavsiye edilir/edilmez*) consistent with paths |
| `WS6_tree_structure` | all fields | Holistic: depth ≥1, ≥2 features, labeled leaves, consistent ≤/> pairing |

### `WS6_tree_structure` components

1. At least one split (depth ≥ 1)
2. ≥2 **different** features across tree
3. All leaves have class labels
4. Branch operators consistent (≤ paired with >, or < with ≥)

`need: 4`, `partial_on: 2` for holistic item.

---

## Validation integration

- `validation.json` → `deterministic_checks` for thresholds, labels, `tree_validity` — **prefer Python scores**.
- If tree drawing not captured (`parse_success: false`), score from text description with **lower confidence** and `review: true`.
- Layout ROI / supplemental page image may improve OCR — do not infer unstated nodes.

---

## Competency inference

| Item | Primary LO | Strength |
|------|------------|----------|
| `WS6_tree_structure` | LO3.2.2 | **strong** (ceiling) when holistic full credit |
| Feature/threshold/label items | LO3.2.2 | **moderate** supporting |

Tree construction demonstrates **Deepen** — model structure from data features. Do not assign LO3.3.1 (Create) unless leaves show explicit design adaptation (rare on WS6).

---

## Cross-worksheet link

**WS7 Part 2** grades rules against **this student's WS6 tree**. Preserve consistent feature/threshold interpretation when both worksheets are scored.

---

## Review flags

- Single-feature tree → `tree_structure` partial; review if OCR may have missed inner node.
- Contradictory leaf on same path → zero on `WS6_leaves`, flag for human.
