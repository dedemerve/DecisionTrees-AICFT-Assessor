# WS5 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 5** (threshold grid experiment).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS5_rubric.json` |
| Answer key | `worksheets/WS5/answer_key.json` |
| Mapping | `mappings/WS5_AICFT_mapping.json` |
| Validity | `worksheets/WS5/validity_notes.json` |
| Responses | `students/<student_id>/WS5/extraction.json` |
| Validation | `students/<student_id>/WS5/validation.json` — **required** |

**Pipeline group:** B.

---

## Construct

**Dataset size N = 10.** Students complete a table: for each candidate threshold row — threshold expression, correct count, error count, MCR. Final item **B25** selects the best threshold with data-based justification.

Rows map to extraction fields `WS5_B1`–`WS5_B24` (six rows × four cells; row 6 optional in rubric).

---

## Row scoring (`WS5_row1` … `WS5_row5`)

| Check | Rule |
|-------|------|
| `row_consistency` | TP+FP+FN+TN logic: **correct + errors = 10**; **MCR = errors / 10** |
| Partial 0.5 | Threshold **variable** correct (e.g. şeker) but **operator** wrong or missing |
| Authority | Python `validation.json` → `deterministic_checks` per row — **use those scores** |

Do not re-count confusion matrix cells unless validation is missing or `blocked: true`.

### Optional row 6 (`WS5_row6`)

Present only if student filled it. Same consistency rules; not required for full worksheet credit.

---

## B25 — final choice + justification

| Component | Requirement |
|-----------|-------------|
| `threshold_stated` | Specific numeric threshold from the grid |
| `data_justification` | References MCR or error count from **their table** (not intuition alone) |

`need: 2`, `partial_on: 1` → threshold without data justification = partial.

---

## Validation gating

| `validation.json` state | Action |
|-------------------------|--------|
| `blocked: true` | Set worksheet `blocked: true`; empty or null item scores |
| `parse_success: false` | Score only items with extraction present; `review: true` on others |
| Row check failed | Use deterministic result; LLM adds competency rationale only |

---

## Competency inference

| Item | Primary LO | Rationale focus |
|------|------------|-----------------|
| `WS5_row1`–`row5` | LO3.2.3 | Iterative parameter exploration |
| `WS5_B25` | LO3.2.2 / LO3.2.3 | Selection + justification of optimal threshold |

Supporting LO3.1.1 only when student explicitly names MCR formula in B25 justification.

Strength ceilings per mapping. Partial row credit → **weak** or **moderate** only.

---

## Review flags

- Internal inconsistency (MCR ≠ errors/10) when validation absent → `review: true`.
- B25 threshold not appearing in any grid row → partial or zero + review.
