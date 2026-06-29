# WS11 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 11** (demographics + cognitive check).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS11_rubric.json` |
| Answer key | `worksheets/WS11/answer_key.json` |
| Mapping | `mappings/WS11_AICFT_mapping.json` |
| Framework edge case | `mappings/AICFT_assessment_framework.json` → `edge_cases.WS11_Q11` |
| Validity | `worksheets/WS11/validity_notes.json` |
| Responses | `students/<student_id>/WS11/extraction.json` |

**Pipeline group:** A.

---

## Construct

Mixed worksheet: **printed survey Q1–Q7**, **cognitive scored items**, and **descriptive-only** Likert/self-assessment. Only the cognitive subset produces competency evidence and behaviour-engine input.

### Scored vs descriptive-only

| Block | Item IDs | Scored? |
|-------|----------|---------|
| Survey Q1–Q5 | `WS11_B1`–`B5` | **No** — Likert/checkbox (+ optional Açıklama); no correct answer |
| Demographics Q6–Q7 | `WS11_B6`–`B7` | **No** — age / gender; no correct answer |
| Cognitive | `WS11_B8a`, `B8b`, `B9` | Yes |
| Q10 | `WS11_Q10_1` … `Q10_8` | Yes (0.125 each) |
| Q11 | `WS11_Q11_2` … `Q11_4` | Yes (0.33 / 0.33 / 0.34) |
| Q12 | `WS11_Q12_1` … `Q12_5` | Yes (0.2 each) |
| Likert / self-assessment | `WS11_L10_*`, `L11_*`, `L12_*` | **No** — never infer LO from L10–L12 |

---

## Cognitive items

### B8a — classification

Not-recommended label for the scenario food (*tavsiye edilmez*, *önerilmez*, etc.).

### B8b — rule (`need: 2`, `partial_on: 1`)

| Component | Requirement |
|-----------|-------------|
| `condition` | şeker > 10 (or equivalent threshold language) |
| `conclusion` | not recommended |

One component only → partial.

### B9 — definition (`need: 2`, `partial_on: 1`)

| Component | Requirement |
|-----------|-------------|
| `learns_from_data` | Data-driven learning |
| `tree_or_classification` | Tree structure or classification role |

Shape-only metaphor (*ağaca benzer*) without data learning → partial or zero.

### Q10 — true/false (`evaluation: true_false`)

Deterministic per `correct_answer` in rubric (`Doğru` / `Yanlış`). Do not debate keyed answers.

### Q12 — multiselect (`multiselect_subitem`)

Credit per option: student's mark must match `correct: true/false` in rubric.

| Option | Correct? | Statement (summary) |
|--------|----------|---------------------|
| 1 | ✓ | Trees can overfit |
| 2 | ✗ | Always best model |
| 3 | ✗ | Threshold irrelevant |
| 4 | ✗ | MCR must always be 0 |
| 5 | ✓ | More data usually helps |

---

## Q11 — step ordering (edge case)

> **Framework:** `edge_cases.WS11_Q11`

Step 1 (*Bir özellik seçiyorum*) is **pre-printed**. Only steps **2–4** are scored.

| Position | Step text | `correct_answer` |
|----------|-----------|------------------|
| 1 | *(given)* Bir özellik seçiyorum | — |
| 2 | Verileri seçilen özelliğe göre boyuta göre düzenliyorum | 2 |
| 3 | Birçok kartın doğru sınıflandırıldığı iyi bir eşik buldum | 3 |
| 4 | Bir karar verdim | 4 |

`evaluation: ordering_step` — deterministic; **no partial** per sub-item.

### Q11 competency (critical)

Tests **procedural workflow**, not vocabulary recall.

| Sub-items correct | Primary LO | Strength |
|-------------------|------------|----------|
| ≥2 of 3 | LO3.1.2 | moderate |
| 1 of 3 | LO3.1.2 | weak |
| 0 | — | none |
| All 3 | LO3.1.2 moderate + optional LO3.2.2 | weak supporting only |

**Do not** assign LO3.1.1 for Q11. **Do not** assign LO3.2.2 **strong** — ceiling is weak supporting.

---

## Competency quick reference

| Block | Primary LO | Level |
|-------|------------|-------|
| B8a–B8b | LO3.2.2 | Deepen — applied rule |
| B9 | LO3.1.2 | Acquire — definition |
| Q10 | LO3.1.2 | Conceptual T/F |
| Q12 | LO3.1.2 | Conceptual multiselect |
| Q11 | LO3.1.2 | Procedural ordering |

---

## Validity constraints

- Demographic items (`B6`–`B7`, `L12`) → **never** enter behaviour or LO inference (`leakage_risks` in validity notes).
- Survey Q1–Q5 (`B1`–`B5`): transcribe selected option (+ Açıklama if any); **no scoring, no competency**.
- Reference question text: `data/ws11_feedback_reference.json`.

---

## Review flags

- Missing Q10/Q11/Q12 sub-key → `score: null`, `review: true`, `evidence_present: false`.
- Illegible Likert → ignore (not scored).
- Missing demographic blank → store `(bos)`; do not flag for scoring review.
