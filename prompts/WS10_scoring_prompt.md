# WS10 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 10** (systematic energy threshold search).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS10_rubric.json` |
| Answer key | `worksheets/WS10/answer_key.json` |
| Mapping | `mappings/WS10_AICFT_mapping.json` |
| Validity | `worksheets/WS10/validity_notes.json` |
| Responses | `students/<student_id>/WS10/extraction.json` |
| Numeric table | `extraction.json` → `numeric_table`, `htr_status`, `layout_roi` |

**Pipeline group:** A (no `validation.json`; quality metadata on extraction).

---

## Construct

Fixed training set: **7 energy values** `[28, 69, 219, 346, 359, 408, 489]`. Students complete a numeric table: midpoints, misclassification counts, optimal threshold (**408** for this dataset), and two open rows.

---

## Blocked worksheet

If `numeric_table` region not captured or `htr_status` indicates incomplete table:

```json
{ "blocked": true, "blocked_reason": "Numeric table incomplete or HTR review required." }
```

→ **Do not score items.** Set `items: []` or null scores with worksheet-level `blocked: true`.

---

## Items (all `check: numeric` or `row_consistency`)

| Item | Expected (reference) | Notes |
|------|-------------------|-------|
| `WS10_B1` | 48.5 (±10) | Midpoint 28–69 |
| `WS10_B2` | 6 | Midpoint candidates from 7 values |
| `WS10_B3` | 144.0 (±30) | Midpoint 69–219 |
| `WS10_B4` | 3 | Misclassifications at a row |
| `WS10_B5` | 408 | `numeric_optimal` — min MCR threshold |
| `WS10_B6` | open | `row_consistency` — counts sum to N, MCR arithmetic |
| `WS10_B7` | open | Same as B6 (second row) |
| `WS10_B8` | 408 | Final optimal — should match B5 |

**Scoring authority:** Python deterministic (`rubric_deterministic`, `ws10_table_extractor`). **Use computed scores** — do not recalculate midpoints or MCR.

B6/B7: no fixed answer; full credit when internal arithmetic consistent with student's chosen threshold row.

---

## Partial capture

If only some cells extracted: score present items; mark missing keys `review: true`, `score: null`.

---

## Competency inference

| Item | Primary LO |
|------|------------|
| B1–B5, B8 | LO3.2.2 — threshold optimization procedure |
| B6–B7 | LO3.2.2 — interpreting confusion counts / MCR |

LO3.1.1 supporting only if student explicitly writes MCR formula in free text (unusual on WS10).

---

## Review flags

- B5 ≠ B8 when both present → review (should be consistent optimal).
- Values consistent with table but outside tolerance → trust Python tolerance flags.
