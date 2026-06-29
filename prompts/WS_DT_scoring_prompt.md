# WS_DT scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet DT** (CODAP / Arbor plugged inquiry).

## Core policy — interpretive inquiry (read first)

From `rubrics/WS_DT_rubric.json` → `scoring_policy`:

| Policy | Rule |
|--------|------|
| `default_mode` | **interpretive** — no single canonical answer |
| `component_scoring` | Award on rubric **components** + student-grounded reasoning |
| `emit_scoring` | EMIT blocks: internal numeric consistency only |
| `example_answers` | Quality illustrations — **never** the only acceptable response |

Students choose variables, thresholds, trees, and conclusions from **their own CODAP work**. Accept any valid food feature (şeker, yağ, enerji, protein, …) and student-specific EMIT numbers.

---

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS_DT_rubric.json` |
| Answer key | `worksheets/WS_DT/answer_key.json` |
| Mapping | `mappings/WS_DT_AICFT_mapping.json` |
| Framework | `edge_cases.DT_Section_A`, `edge_cases.DT_Section_G` |
| Validity | `worksheets/WS_DT/validity_notes.json` |
| Responses | `students/<student_id>/WS_DT/extraction.json` |

**Pipeline group:** A.

**Dataset assumption (rubric):** training N=16 (10 recommended, 6 not); test N=8.

---

## Deterministic exceptions only

Python checks — do not override with semantic judgment:

- `DT_B_Q1`–`Q3`, `DT_C_Q1`, `DT_D_Q1`, `DT_F_Q1` (EMIT action capture)
- `DT_E_sensitivity_formula`, `DT_E_MCR_formula`, `DT_E_sensitivity`, `DT_E_MCR`

All other items: **component-based interpretive scoring**.

**Section routing:** match `item_id` to section headings and question text — not page position alone. Section C printed Q2 → `DT_C_Q2`; Section C EMIT → `DT_C_Q1`.

---

## Section A — prior beliefs vs first exploration

> **Framework:** `edge_cases.DT_Section_A`  
> Section A is **before** full tool mastery. **Do not treat Q1–Q4 identically.**

### `DT_A_Q1` — prior belief (`evaluation: prior_belief`)

| | |
|-|-|
| **Full credit** | ≥1 specific food feature named (prediction link optional) |
| **Partial** | Vague, no feature name |
| **Zero** | Blank / off-topic |
| **LO** | LO3.1.1, `evidence_type: prior_belief`, strength **weak** |
| **Portfolio** | `portfolio_weight: baseline` — **excluded from LO peak aggregation** |

Do **not** award LO3.2.x unless student explicitly cites CODAP graphs (unexpected at this stage).

### `DT_A_Q2` — data exploration (`data_exploration`)

| | |
|-|-|
| **Full credit** | Named feature **+** observed pattern from graphs/data |
| **Partial (0.5)** | Feature OR data evidence, not both |
| **Primary LO** | LO3.2.2 moderate |
| **Review** | `true` if answer mirrors Q1 intuition without data reference |

### `DT_A_Q3` — meaningful difference (`feature_observation`)

Full: feature + direction (e.g. lower sugar in recommended group). Partial: one component.

Primary LO3.2.2 moderate.

### `DT_A_Q4` — first split (`feature_selection_with_justification`)

Full: feature + **data-based** justification (separation, MCR, graph). Partial: feature with intuition only (*şeker kötü*).

Primary LO3.2.2 **strong** (ceiling) when both components at full credit. Supporting LO3.2.1 weak.

**Distinction:** Q4 = one variable choice; Section B = compare three trees.

### Section A checklist

```
□ Q1 = prior belief only — not Deepen
□ Q2–Q4 require data evidence for full credit
□ Q4 intuition-only → partial score AND LO3.2.2 ≤ moderate
□ Strength never exceeds mapping ceiling
□ Q1 uses evidence_type prior_belief
```

---

## Sections B–G — summary

| Section | Focus | Primary LOs |
|---------|-------|-------------|
| **B** | EMIT trees, 3 variables, compare | LO3.1.3, LO3.2.1 |
| **C–D** | Threshold optimization, 2-level tree | LO3.2.3 |
| **E** | Metrics + evaluation | LO3.1.1 (formulas), LO3.2.3 (Q1–Q3) |
| **F** | Test data, overfitting | LO3.2.3; LO3.3.1 weak Create on Q2 |
| **G** | Reflection | `portfolio_weight: diagnostic` — LO peaks excluded |

### Additional rules

- **EMIT action items:** record variable, threshold, TP/FP/TN/FN; partial if metrics noted without full EMIT.
- **DT_E_Q1:** metric name **and** purpose justification for full credit.
- **DT_E_Q4:** must cite data overlap / inseparability (`conceptual_limitation`).
- **DT_F_Q2:** strongest Create signal — train vs test performance gap explicit.
- **DT_G_Q1/Q2:** reflective; lower confidence; diagnostic weight only.
- Blank on sheet → `(bos)`; do not borrow from other sections.

---

## Competency strength discipline

Mapping `strength` is a **ceiling**. Interpretive full credit does not automatically imply **strong** — check `mappings/WS_DT_AICFT_mapping.json` per item.

`portfolio_weight: baseline` (Q1) and `diagnostic` (Section G) → exclude from peak LO aggregation per `pipeline_schema.contributes_to_portfolio_peaks()`.

---

## Insufficient evidence (zero hallucination)

If the extracted response is blank, illegible (`(bos)`, `(okunamiyor)`, `(missing)`), or clearly unrelated to the item:

- Do **not** invent or guess a score from plausibility.
- Assign score **0**, set `"review": true`, and write the rationale as **yetersiz kanıt — [specific reason]**.
- This matches the portfolio layer: when evidence is missing, mark insufficient — do not infer competence.
