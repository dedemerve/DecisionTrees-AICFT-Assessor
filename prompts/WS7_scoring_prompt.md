# WS7 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 7** (path matching + rule writing).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS7_rubric.json` |
| Sample tree | `data/ws7_sample_tree.json` |
| Answer key | `worksheets/WS7/answer_key.json` |
| Responses | `students/<student_id>/WS7/extraction.json` |
| Validation | `students/<student_id>/WS7/validation.json` — **required** |
| Cross-ref | `students/<student_id>/WS6/extraction.json` — for B1–B3 |

**Pipeline group:** B. Python authority: `ws7_validation.py`.

---

## Construct

**Part 1 — fixed sample tree (enerji / protein):** Match three **printed** if-then rules (rows 5–7) to paths **A, B, C**. Each box has **one correct letter**.

**Part 2 — pre-service teacher's WS6 tree:** Write if-then rules for each leaf path (B1–B3). Each rule has **one correct formulation** for that path given the pre-service teacher's WS6 operators and thresholds.

B4–B7 are **not scored** when the tree has three paths.

---

## Operator rules (critical)

| Sample-tree split | Evet / written | Hayır / complement |
|-------------------|----------------|-------------------|
| enerji @ 180 kcal | `< 180` (path A) | `≥ 180` (paths B, C) |
| protein @ 7,7 g | `< 7,7` (path B) | `≥ 7,7` (path C) |

Part 2 rules must use the **same operators** as the pre-service teacher's WS6 tree (`≤` vs `<`, `>` vs `≥` matter).

| Verdict | Part 1 | Part 2 |
|---------|--------|--------|
| Full | Letter matches B/A/C | Features, values, operators, label all match path |
| Partial 0.5 | — | Features + label correct, operator wrong |
| Zero | Wrong letter | Wrong feature, value, or label |

---

## Part 1 — path matching (deterministic)

| Item | Correct | Printed rule |
|------|---------|--------------|
| `WS7_P1_box1` | **B** | enerji ≥180 ve protein <7,7 → tavsiye edilemez |
| `WS7_P1_box2` | **A** | enerji <180 → tavsiye edilebilir |
| `WS7_P1_box3` | **C** | enerji ≥180 ve protein ≥7,7 → tavsiye edilebilir |

Exact letter match (case-insensitive). Blank → `not_attempted`, `review: true`.

---

## Part 2 — rule consistency with WS6 (`WS7_B1`–`B3`)

Path order (standard two-level WS6 on evet branch):

1. **B1** — root evet + inner evet (B10 leaf)
2. **B2** — root evet + inner hayır (B11 leaf)
3. **B3** — root hayır (B13 leaf)

Load WS6 when scoring. If WS6 missing → B1–B3 `review: true`.

---

## Review flags

- P1 blank or unparseable → `review: true`
- WS6 missing with B1–B3 filled → `review: true`, `blocked_dependency: WS6`
- Partial operator credit → `review: false` (deterministic 0.5)

---

## Insufficient evidence (zero hallucination)

If the extracted response is blank, illegible (`(bos)`, `(okunamiyor)`, `(missing)`), or clearly unrelated to the item:

- Do **not** invent or guess a score from plausibility.
- Assign score **0**, set `"review": true`, and write the rationale as **yetersiz kanıt — [specific reason]**.
- This matches the portfolio layer: when evidence is missing, mark insufficient — do not infer competence.
