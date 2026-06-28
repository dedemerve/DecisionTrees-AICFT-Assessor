# WS7 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 7** (path matching + rule writing).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS7_rubric.json` |
| Answer key | `worksheets/WS7/answer_key.json` |
| Mapping | `mappings/WS7_AICFT_mapping.json` |
| Validity | `worksheets/WS7/validity_notes.json` |
| Responses | `students/<student_id>/WS7/extraction.json` |
| Validation | `students/<student_id>/WS7/validation.json` — **required** |
| Cross-ref | `students/<student_id>/WS6/extraction.json` — for B1–B3 |

**Pipeline group:** B.

---

## Construct

**Part 1 — fixed sample tree:** Match three printed if-then rules to paths **A, B, C**.

**Part 2 — student's tree:** Write up to three if-then rules **consistent with the student's own WS6 tree** (not the sample tree).

> Validity note: Part 1 uses a **fixed sample tree**; Part 2 depends on WS6. B4–B7 are **not in rubric** — only P1 boxes + B1–B3 are scored.

---

## Part 1 — path matching (deterministic)

| Item | Correct path | Notes |
|------|--------------|-------|
| `WS7_P1_box1` | **B** | Rule 1 → path B |
| `WS7_P1_box2` | **A** | Rule 2 → path A |
| `WS7_P1_box3` | **C** | Rule 3 → path C |

Also extracted as `WS7_P1_box1`–`box3` in extraction schema. Exact letter match; case-insensitive.

If validation marks Part 1 not captured → `score: null`, `review: true` for all three.

---

## Part 2 — rule consistency with WS6 (`WS7_B1`–`B3`)

Each rule graded with `check: rule_consistency_with_WS6`:

| Component | Requirement |
|-----------|-------------|
| `correct_feature` | Feature(s) match WS6 root/inner splits |
| `correct_operator` | ≤ or > direction matches WS6 branch |
| `correct_label` | Conclusion matches leaf on that path |

Partial 0.5: `correct_feature_and_label_but_wrong_operator`.

Accept paraphrased if-then forms (*Eğer … ise → …*). Threshold **values** may differ from answer key if WS6 used a valid value.

Load WS6 responses when scoring B1–B3 — rules cannot be correct relative to a tree the student did not draw.

---

## Competency inference

| Item | Primary LO |
|------|------------|
| P1 boxes | LO3.2.2 — reading tree structure |
| B1–B3 | LO3.2.2 — translating structure to natural-language rules |

Supporting LO3.1.2 only when rule syntax shows vocabulary without correct tree linkage.

---

## Review flags

- WS6 missing or blocked → B1–B3 `review: true`; do not invent tree structure.
- P1 response is path description not letter → attempt normalization; else review.
