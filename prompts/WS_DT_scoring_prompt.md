# WS_DT scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring WS_DT.

## Files to load

| Artifact | Path |
|----------|------|
| Rubric | `rubrics/WS_DT_rubric.json` |
| Competency priors | `mappings/WS_DT_AICFT_mapping.json` (schema 2.0) |
| Framework edge cases | `edge_cases.DT_Section_A`, `edge_cases.DT_Section_G` |
| Responses | `students/<student>/WS_DT/extraction.json` |
| Validation | *(Group A — not required)* |

## Worksheet description

CODAP / Arbor plugged inquiry (Sections A–G). Section E includes deterministic sensitivity/MCR items. Section F includes test-set / overfitting evidence. Section G is metacognitive reflection.

**Section routing:** match `item_id` using section headings and question text — not page position alone.  
Section C printed Q2 → `DT_C_Q2`; Section C EMIT block → `DT_C_Q1`. Section D action block → `DT_D_Q1`.

---

## Section A — prior beliefs and first CODAP exploration (edge case)

> **Framework:** `edge_cases.DT_Section_A`  
> Section A is **before** full tool mastery (Section B). Do **not** treat all four items identically.

### Item-by-item scoring and competency

#### `DT_A_Q1` — prior belief (baseline)

| Field | Guidance |
|-------|----------|
| **Rubric** | `evaluation: prior_belief` — names ≥1 food feature (şeker, yağ, enerji, …). No CODAP analysis required. |
| **Full credit** | Any specific dataset feature named (prediction link optional). |
| **Partial** | Vague answer without a feature name. |
| **Zero** | Blank or off-topic. |
| **Competency** | LO3.1.1, `evidence_type: prior_belief`, strength ceiling **weak** |
| **Portfolio** | `portfolio_weight: baseline` — **does not** affect LO peak aggregation |
| **Rationale** | *"Records uninformed prior about predictive features before data exploration."* |

Do **not** award LO3.2.x for Q1 unless the student explicitly cites CODAP graphs (they should not at this stage).

---

#### `DT_A_Q2` — data exploration after CODAP

| Field | Guidance |
|-------|----------|
| **Rubric** | `data_exploration` — (1) feature named, (2) **observed** pattern from graphs/data |
| **Full credit** | Both: specific feature + data/graph evidence (not “I think” alone). |
| **Partial (0.5)** | Feature named OR data cited, not both. |
| **Zero** | Blank, or only general opinion without data reference. |
| **Primary competency** | LO3.2.2 moderate — early data interpretation |
| **Supporting** | LO3.1.2 weak — links exploration to modelling |
| **Rationale** | *"Cites feature explored in CODAP and an observed pattern separating classes."* |

**Review flag:** `true` if answer could be pre-data intuition copied from Q1 without graph reference.

---

#### `DT_A_Q3` — meaningful class difference

| Field | Guidance |
|-------|----------|
| **Rubric** | `feature_observation` — (1) feature with meaningful difference, (2) direction described |
| **Full credit** | Yes/no + feature + direction (e.g. lower sugar in recommended group). |
| **Partial** | Feature OR direction, not both. |
| **Zero** | Denies difference without evidence, or blank. |
| **Primary competency** | LO3.2.2 moderate |
| **Rationale** | *"Identifies feature showing meaningful separation between recommended and not-recommended foods from data."* |

---

#### `DT_A_Q4` — first split variable with justification

| Field | Guidance |
|-------|----------|
| **Rubric** | `feature_selection_with_justification` — (1) feature for first split, (2) **data-based** justification |
| **Full credit** | Feature + graph/separation/MCR-based reason (not nutrition folklore alone). |
| **Partial** | Feature named; justification is intuition only (“şeker kötü”). |
| **Zero** | No feature or no justification. |
| **Primary competency** | LO3.2.2 **strong** (ceiling) when both components at full credit |
| **Supporting** | LO3.2.1 weak — early evaluate→select before Section B three-tree comparison |
| **Rationale** | *"Selects first split variable with explicit data-based justification."* |

**Distinction from Section B:** Q4 is **one** variable choice; B4 is **compare three trees**.

---

### Section A — scorer checklist

```
□ Q1 scored as prior belief only — not Deepen
□ Q2–Q4 distinguished from Q1 (data evidence required for full credit)
□ Q4 intuition-only justification → partial score AND LO3.2.2 ≤ moderate
□ Competency strength never exceeds mapping ceiling
□ Q1 evidence listed with evidence_type prior_belief in output
```

---

## Sections B–G — summary notes

| Section | Focus | Primary LOs |
|---------|-------|-------------|
| **B** | EMIT trees, 3 variables, compare | LO3.1.3, LO3.2.1 |
| **C–D** | Threshold optimization, 2-level tree | LO3.2.3 |
| **E** | Metrics + evaluation | LO3.1.1 (formulas), LO3.2.3 (Q1–Q3) |
| **F** | Test data, overfitting | LO3.2.3; LO3.3.1 weak Create on Q2 |
| **G** | Reflection | `portfolio_weight: diagnostic` — LO peaks excluded |

### Other scoring rules

- **EMIT action items** (B_Q1–Q3, C_Q1, D_Q1, F_Q1): capture variable, threshold, TP/FP/TN/FN. Partial metric-only notes valid.
- **DT_E_sensitivity / DT_E_MCR:** deterministic when confusion counts present.
- **DT_E_Q1:** metric name **and** purpose justification required for full credit.
- **DT_E_Q4:** must cite data overlap / inseparability.
- **DT_F_Q2:** strongest Create signal — full credit only with explicit train vs test performance gap.
- **DT_G_Q1/Q2:** reflective; lower confidence; diagnostic portfolio weight.
- Blank on worksheet → `(bos)`; do not infer from other sections.
