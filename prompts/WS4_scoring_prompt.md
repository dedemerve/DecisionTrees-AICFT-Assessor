# WS4 scoring context

Injected alongside `prompts/stage3_scoring.md` when scoring **Worksheet 4** (best threshold from sorted values / MCR).

## Artifacts

| Role | Path |
|------|------|
| Rubric | `rubrics/WS4_rubric.json` |
| Answer key | `worksheets/WS4/answer_key.json` |
| Mapping | `mappings/WS4_AICFT_mapping.json` |
| Validity | `worksheets/WS4/validity_notes.json` |
| Responses | `students/<student_id>/WS4/extraction.json` |

**Pipeline group:** A.

---

## Construct

Students search for the **best threshold** on a sorted value grid by minimizing **MCR (misclassification rate)**. The visual circle task is **not text-extractable** — do not score it.

---

## Items

| Item | Evaluation | Scoring authority |
|------|------------|-------------------|
| `WS4_B1` | `numeric` — valid midpoint minimizing MCR | Deterministic tolerance; multiple tied thresholds may be valid |
| `WS4_B2` | `criterion` — names MCR / error rate as selection criterion | Semantic. `need: 1` on `mcr_reference`; minimization language optional bonus |
| `WS4_B3` | `comparison` — two candidates + which is better | Semantic. `need: 2`, `partial_on: 1` |
| `WS4_B4` | `formula` — MCR = (FP+FN)/N | **Deterministic** (`check: formula`). Accepted: `(FP+FN)/total`, `(FP+FN)/N`, Turkish equivalents. Do not re-derive arithmetic. |
| `WS4_B5` | `agreement_with_reasoning` — evaluate Pia's statement | Semantic. Agrees Pia is correct **and** explains minimum errors / lowest MCR |

### B1 guidance

Accept any **midpoint threshold** that yields minimum MCR for the grid — not a single canonical number if several tie.

### B5 guidance

Full credit: confirms Pia + reasoning (*en düşük MCR = en az hata*). Partial: agreement without MCR reasoning, or correct reasoning without explicit agreement.

---

## Competency inference

| Item | Primary LO | Notes |
|------|------------|-------|
| B1, B3 | LO3.2.2 | Threshold search / comparison (Deepen) |
| B2 | LO3.2.2 | Evaluation criterion articulation |
| B4 | LO3.1.1 | Metric definition (Acquire) — formula recall |
| B5 | LO3.2.2 | Evaluating a peer's optimization claim |

Strength ceilings per `mappings/WS4_AICFT_mapping.json`. Do not exceed **strong** unless mapping allows.

---

## Review flags

- B1 numeric OCR uncertain → `review: true`; do not compute correct midpoint yourself.
- B4: if deterministic check already failed, use Python score; infer LO3.1.1 only if formula concept is present in student text despite format mismatch (rare — flag for human).
