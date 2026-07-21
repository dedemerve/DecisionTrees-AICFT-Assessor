# Self-adjudication protocol (single researcher)

**Status:** Binding for 2025 expert-coded training subset  
**Date:** 2026-07-20  
**Replaces:** Dual-adjudicator protocol (not applicable — one researcher)

## Claim lock

Allowed claim after Pass 1 + Pass 2 + written resolve log:

> Expert-coded, self-adjudicated 2025 process training subset; pilot-model-ready for active V-codes. Not dual-rated; not all-20-codes training-ready.

Forbidden claims:

- dual-rated / dual-adjudicated gold
- all 20 codes training-ready
- proficiency / B0–B13 scoring validity

## Decision states

For every V-code on every calibration episode, choose exactly one:

- `observed`
- `not_observed`
- `not_measurable`

## V7 mandatory pre-check (strict)

Before any `V7A` / `V7B` / `V7C` = `observed`, confirm all three:

1. Behavioral **opportunity** was visible on screen
2. Recording covers the **full relevant window**
3. Off-screen activity cannot reasonably explain the absence

If any fails → prefer `not_measurable` (or case-by-case note in `evidence_notes`).  
Fill `v7_precheck` object on that code when deciding `observed`.

## Pass 1

1. Open `pass1_coding_form.json`.
2. For each `calibration_id`, open narrative steps for `step_indices` (and screenshots/video as needed).
3. Code all 20 codes. Do **not** open `pipeline_hints_SEALED.json`.
4. For every `observed`, write short `evidence_notes`.
5. When finished, record:

```text
pass1_locked_at: YYYY-MM-DD
pass1_coder: <your name>
```

## Pass 2 (≥7 day washout)

1. Do not re-open Pass 1 answers while coding.
2. Fill `pass2_coding_form.json` for the same 30 episodes (order may be shuffled).
3. Same V7 rules.
4. Record:

```text
pass2_locked_at: YYYY-MM-DD
```

## Resolve (self-adjudication)

Compare Pass 1 vs Pass 2 cell-by-cell.

| Case | Action |
|------|--------|
| Agree | Final = that decision; `gold_tier` → `expert_adjudicated` |
| Disagree | Re-open evidence; pick final; write rationale (required) |
| Pipeline hints | Optional diagnostic only; never auto-overwrite your final |

Create `resolve_log.json`:

```json
{
  "claim_lock": "Expert-coded, self-adjudicated 2025 process training subset; pilot-model-ready for active V-codes. Not dual-rated; not all-20-codes training-ready.",
  "pass1_locked_at": null,
  "pass2_locked_at": null,
  "washout_days": null,
  "disagreements": [
    {
      "calibration_id": "cal_01",
      "v_code": "V7A_no_metric_inspection",
      "pass1": "observed",
      "pass2": "not_measurable",
      "final": "not_measurable",
      "rationale": "Opportunity unclear in frame window; fail pre-check #2."
    }
  ],
  "agreement_summary": {
    "cells_total": 600,
    "agree": null,
    "disagree": null
  }
}
```

Acceptance for claim:

- 30/30 episodes coded in Pass 1 and Pass 2
- Every disagreement has a written rationale
- Finals written into process tables as `gold_tier: expert_adjudicated` (scripted after resolve)

## After resolve (next work)

1. Back-fill **all** cohort `V7A=observed` cells with the same pre-check (case-by-case).
2. Pilot train on **active codes only**, using frozen `split_assignment.json`.
3. Exclude zero-fire codes from loss; do not claim all-20 readiness.

## Checklist

- [ ] Pass 1 locked
- [ ] ≥7 days elapsed
- [ ] Pass 2 locked
- [ ] `resolve_log.json` complete
- [ ] Claim language unchanged (no dual-rater wording)
