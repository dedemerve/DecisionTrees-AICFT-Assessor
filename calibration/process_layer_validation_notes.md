# Process Layer Validation Notes

Date: 2026-07-20 | RF02 Remediation

---

## Distinction: Construct Layer vs Process Layer

| Layer | Behaviors | Detection method | Validation instrument |
|---|---|---|---|
| **Construct** | B0–B13 | Video frame + transcript scoring (mmla_scorer.py) | IRR protocol (human episode coding) |
| **Process** | B15, B16, B17 | Algorithmic (log events / session sequences) | Log validation (compute_b15_from_logs.py) + separate video-episode coding |

**These layers must NOT be merged in reliability reporting.**

---

## B15 — Systematic parameter exploration (VOTAT)

Detection: `scripts/compute_b15_from_logs.py`
Source: CODAP event logs (emit_tree_data events)
Measurement: VOTAT rate = proportion of inter-emit intervals with single-parameter change

Validation status:
- Log-derived computation verified for 2026 sessions (Amy, Bruno, Nadia: Deepen; others: not_observed/not_measured)
- NO human video coding conducted for B15
- Frame-level F1 = 0.000 (expected: B15 cannot be observed in a single frame)

Reporting language:
> "VOTAT rate (B15) was computed algorithmically from CODAP event logs. No frame-level or episode-level human validation has been conducted."

---

## B16 — Error recovery and adaptive correction

Detection: `scripts/build_2025_calibration_dataset.py` (detect_b16_steps)
Source: Sequence detection: DELETE_TREE_OR_CTR_ROW → DRAG_SPLIT_ATTRIBUTE with different predictor

Validation status:
- Algorithmic only; no human rater has independently validated these detections
- Frame-level F1 = 0.000 (expected: single frame cannot show delete-then-rebuild sequence)

Required for Q1: Independent video-episode coding by ≥2 raters using episode-level protocol.
Minimum: 40 episodes with B16 indicator flagged by algorithm.

---

## B17 — Pre-task planning and orientation

Detection: `scripts/build_2025_calibration_dataset.py` (detect_b17_steps, regex on observer text)
Source: Observer text regex matching planning language

Validation status:
- Regex-based; no human validation of regex precision/recall
- time_since_session_start not populated in SESSION_CONTEXT for 2025 data
- Frame-level F1 = 0.000

Required for Q1: Manual review of observer text detections by domain expert.
Minimum: Verify all 72 flagged frames (2025) against original observer notes.

---

## Scorer target list correction

The following change must be applied to `mmla_scorer.py` before any Q1 submission:

- `_LOG_PRIMARY = {"B15"}` is correctly set — B15 scored from logs, not video
- B16 and B17 remain in `_BEHAVIOR_IDS_CODAP` — they are scored by video but flagged as process
- Publications must state: "B16 and B17 are process behaviors scored by video analysis;
  their reliability has not been independently validated at the human-coding level."

---

## What must NOT appear in publications

- "B15 was video-validated" — B15 is log-derived
- "B16/B17 construct reliability κ=..." — no human IRR for these
- Merging B15/B16/B17 F1 into the same table as B0-B13 construct reliability
