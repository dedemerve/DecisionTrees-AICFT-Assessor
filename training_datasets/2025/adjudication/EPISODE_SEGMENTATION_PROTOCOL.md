# Episode segmentation protocol (2025) — as-is pipeline

**Status:** Documented acceptance of current pipeline boundaries  
**Date:** 2026-07-20  
**Decision:** Dual re-segmentation deferred (researcher choice). Modeling uses existing episode IDs.

## Unit of analysis

An **episode** is the pipeline-defined behavioral segment stored in:

- `*_process_codes.json` → `episodes[]`
- linked from narrative steps via `episode_id` / `step_indices`

## Boundary rule (as implemented)

1. Episodes are derived from expert observation steps grouped by meaningful behavioral continuity and dominant category / anchor-event transitions in the build pipeline.
2. Each episode has:
   - `episode_id` (e.g., `ep_0003`)
   - `step_indices` (inclusive set of narrative steps)
   - optional `start_ms` / `end_ms` from silver/gold visual anchors when available
   - `dominant_category` and `anchor_event` when inferred
3. **Do not re-cut episodes** during self-adjudication. Code the episode as bounded by existing `step_indices`.
4. If a step feels mis-assigned, note it in `episode_notes`; do not invent a new `episode_id` in the calibration forms.

## Minimum content

- An episode must contain ≥1 observation step.
- Timestamp span may be zero when only a single anchored step exists (allowed; still one coding unit).

## What this protocol does *not* claim

- It does **not** claim dual-analyst boundary IRR.
- It does **not** authorize changing splits or episode grains after seeing model results.

## Calibration implication

Self-adjudication judges **V-code decisions inside fixed episodes**, not the placement of episode cuts. Segmentation reliability for papers should be described as: *pipeline-defined episodes documented here; dual boundary study not performed.*

## Change control

If episode boundaries are later revised, bump codebook/dataset versions and regenerate tabular exports; do not silently edit calibration IDs.
