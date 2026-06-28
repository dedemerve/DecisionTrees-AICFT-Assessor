# WS11 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring WS11.

## Files to load

| Artifact | Path |
|----------|------|
| Rubric | `rubrics/WS11_rubric.json` |
| Competency priors | `mappings/WS11_AICFT_mapping.json` (schema 2.0) |
| Framework edge case | `mappings/AICFT_assessment_framework.json` → `edge_cases.WS11_Q11` |
| Responses | `students/<student>/WS11/extraction.json` |
| Validation | *(not required for WS11)* |

## Worksheet description

WS11 is the final reflection worksheet.

| Block | Items | Scored? |
|-------|-------|---------|
| B8a–B8b | Classification + rule | Yes |
| B9 | Decision tree definition | Yes |
| Q10 | `WS11_Q10_1..8` — true/false sub-items | Yes (0.125 each) |
| Q11 | `WS11_Q11_2..4` — order steps 2–4 | Yes (0.33 each) |
| Q12 | `WS11_Q12_1..5` — multiselect | Yes (0.2 each) |
| L10, L11, L12 | Likert / demographics | **No** |

---

## General scoring notes

- **B8a:** exact classification (tavsiye edilmez or equivalent).
- **B8b:** requires **both** condition (şeker > 10) **and** outcome (tavsiye edilmez). One component only → partial credit.
- **B9:** semantic definition — must convey learning from data **and** tree-like structure. Shape-only (“ağaca benzer”) is insufficient.
- **Q10:** deterministic Doğru/Yanlış per `correct_answer` in rubric.
- **Q12:** credit per sub-item for correct mark/unmark.
- Missing extraction → `score: null`, `review: true`, `evidence_present: false` for that sub-item.

---

## Q11 — decision tree construction step ordering (edge case)

> **Framework:** `edge_cases.WS11_Q11`  
> Step 1 (*Bir özellik seçiyorum*) is **pre-printed** on the worksheet. Only steps **2–4** are scored.

### Canonical workflow (correct order)

| Position | Step text (rubric `statement`) |
|----------|--------------------------------|
| 1 | *(given)* Bir özellik seçiyorum |
| 2 | Verileri seçilen özelliğe göre boyuta göre düzenliyorum |
| 3 | Birçok kartın doğru sınıflandırıldığı iyi bir eşik buldum |
| 4 | Bir karar verdim |

### Scoring rules (`evaluation: ordering_step`)

- Each sub-item `WS11_Q11_2`, `_3`, `_4` is scored **independently**.
- Student writes the **position number** (2, 3, or 4) next to each step statement.
- **Full credit** when the written number equals `correct_answer` in the rubric.
- **Zero** when wrong position or blank/`(bos)`.
- No partial credit on ordering (deterministic).

### Competency inference (do not use LO3.1.1 for Q11)

Q11 tests **procedural understanding of how decision trees are built**, not vocabulary recall.

| Sub-item | Primary LO | Strength ceiling | When to assign |
|----------|------------|----------------|----------------|
| `WS11_Q11_2..4` | **LO3.1.2** | moderate | Full credit on ≥2 of 3 sub-items |
| `WS11_Q11_2..4` | **LO3.1.2** | weak | Only 1 sub-item correct |
| `WS11_Q11_2..4` | **LO3.1.2** | none | All wrong or missing |
| supporting | LO3.2.2 | weak | Full credit on all 3 — optional supporting only |

**Rationale template (item-specific):**  
*"Student [correctly/incorrectly] ordered step N (…statement…) in the decision-tree workflow, demonstrating [strong/partial/no] understanding of the feature → threshold → decision sequence."*

**Confidence:** 1.0 when all three positions deterministic; 0.85 when 1–2 wrong but OCR clear; 0.0 when missing.

### Common errors

- Treating Q11 as vocabulary (LO3.1.1) — **incorrect** per framework v2.0.
- Giving LO3.2.2 **strong** — ceiling is **weak** supporting only.
- Scoring step 1 — it is not in extraction keys.

---

## Q10 / Q12 — competency quick reference

| Block | Primary LO | Notes |
|-------|------------|-------|
| Q10_1..8 | LO3.1.2 | Conceptual T/F about what DTs do |
| Q12_1..5 | LO3.1.2 | Multiselect conceptual understanding |
| B8a–B8b | LO3.2.2 | Applied interpretation (Deepen) |
| B9 | LO3.1.2 | Definition item |
