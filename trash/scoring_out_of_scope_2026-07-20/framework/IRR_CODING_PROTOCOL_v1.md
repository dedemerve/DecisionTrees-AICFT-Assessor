# IRR Coding Protocol v1
## CODAP Arbor Construct Behaviors (B0–B13)

Version: 1.0 | Date: 2026-07-20 | Status: Ready for rater training

---

## Purpose

This protocol defines how two independent human raters assign behavior
decisions to student episodes in CODAP Arbor sessions. It governs the
inter-rater reliability (IRR) study required before any publication claims
about scorer reliability.

---

## Unit of analysis: Episode

**Do NOT code at the frame level.** The unit of analysis is an **episode**:
a contiguous sequence of student actions forming a recognizable behavioral
segment (typically 30–120 seconds).

Episodes are pre-segmented in `calibration/irr_sample_manifest.json`.
Each episode is accompanied by:
- A short video clip (or ordered frame sequence)
- The audio transcript for that segment (may be "none" for silent sessions)
- Session context: emit_count_so_far, previous_split_value, previous_dependent_variable

---

## Coding levels

For each behavior B0–B13, assign ONE of:

| Level | Meaning |
|---|---|
| **Deepen** | Clear, unambiguous evidence meeting the rubric Deepen criteria |
| **Acquire** | Partial evidence — behavior is attempted or partially present |
| **not_observed** | No evidence of this behavior in the episode |
| **not_measurable** | Evidence is structurally unavailable (e.g., B8/B13 with transcript="none") |

**not_measurable ≠ not_observed.** Use not_measurable only when the evidence
channel required by the rubric is absent (no transcript for B8/B13; no tree
output for B6/B7). Do not infer absence from missing channel.

---

## Emit ≠ B8 (critical distinction)

A decision tree appearing on screen (emit event) does NOT automatically
qualify as B8 (Performance interpretation).

B8 requires:
1. A valid confusion matrix (≥3 non-zero cells) AND an accuracy/MCR value
2. An interpretive statement in the transcript linking a specific metric
   value to meaning

Seeing a tree with a confusion matrix and hearing nothing = **not_measurable**
(transcript absent), not Deepen.

---

## Scaffolding rule

If the transcript contains teacher/researcher speech (marked "Hocam:", "Merve:",
"Oğuz Hoca:", or identifiable by tone), that speech does NOT count as learner
evidence for any behavior. Treat it as context only.

---

## B13 special rule

B13 (Cost-sensitive metric trade-off) requires ALL THREE:
1. Reference to ≥1 specific metric (MCR, sensitivity, TP, FN)
2. Acknowledgment that two metrics point in different directions
3. A priority or choice justified by application context

If transcript="none" for the entire episode → B13 = **not_measurable**.

---

## Process behaviors (B15–B17) — DO NOT CODE

B15 (VOTAT), B16 (error recovery), and B17 (planning) are process-layer
behaviors coded algorithmically from event logs or session-level patterns.
They are NOT part of this IRR instrument.

---

## Rater procedure

1. Read the rubric criteria for the assigned behaviors.
2. View the episode clip (or ordered frame sequence) in full.
3. Read the transcript for the episode (if available).
4. Note the session context fields.
5. Assign a level for each behavior independently.
6. Record evidence (verbatim quote or visual description) for every Deepen
   and Acquire decision.
7. Do NOT discuss with the other rater until both have coded.

---

## Disagreement and adjudication

After independent coding, disagreements are resolved as follows:
1. Each rater explains their evidence (verbatim).
2. Discussion until consensus, or escalation to lead researcher.
3. Adjudicated decision recorded in `irr_results.json`.

Acceptable disagreement: ±1 level (Deepen vs Acquire) with shared evidence.
Unacceptable: Deepen vs not_observed without reconciliation.

---

## Target metrics

| Metric | Minimum threshold |
|---|---|
| Cohen's κ per behavior | ≥ 0.70 |
| Percentage agreement | ≥ 80% |
| Behaviors requiring revision | Any behavior with κ < 0.60 |

---

## Sample size

- Minimum: 80 episodes (from `irr_students` split only)
- Oversample: B8, B11, B2, B13 (low prevalence behaviors)
- Student source: `irr_students` from `splits_2025.json`

---

## Output

Completed sheets → `calibration/irr_coding_sheet.csv`
Computed metrics → `calibration/irr_results.json` (via `compute_irr.py`)
