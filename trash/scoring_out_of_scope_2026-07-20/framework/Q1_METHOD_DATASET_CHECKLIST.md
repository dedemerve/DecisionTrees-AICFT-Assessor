# Q1 Method/Dataset Paper Checklist

Target: C4 supported (method/dataset paper)
Companion: Q1_CLAIM_LANGUAGE.md | IRR_CODING_PROTOCOL_v1.md

Status key: DONE | PENDING (human task) | PARTIAL | BLOCKED

---

## Red Flag Remediation Status

| RF | Issue | Status | Evidence |
|---|---|---|---|
| RF01 | Miras etiket bağımsız gold gibi sunulmuş | DONE | label_status=step_inherited_indicator; label_warning in v2 |
| RF02 | Construct–process kirlenmesi | DONE | B15/B16/B17 → process_flags; separate notes |
| RF03 | B13/B14/B15-B17 ihlali | DONE | b13_status field; process quarantine |
| RF04 | Emit ≠ interpretation | DONE | Rubric B8 criteria unchanged; COMMON ERRORS section |
| RF05 | IRR yok | PENDING | IRR protocol, sample, sheet ready; human coding needed |
| RF06 | Eşik altı κ/F1 | PARTIAL | Frame debug metrics documented; session-grain pending |
| RF07 | n/imbalance görmezden gelme | PARTIAL | Behavior counts in v2 summary; weighted-F1 needed |
| RF08 | Student leakage | DONE | splits_2025.json; fewshot ∩ irr_sample = ∅ |
| RF09 | Absolute path | DONE | 0 absolute paths in v2 and fewshot_v2 |
| RF10 | Model/prompt provenance | DONE | write_run_manifest.py; runs/ directory |
| RF11 | Frame grain ≠ deployment grain | DONE | session_validation_metrics.json; debug_only flag |
| RF12 | Overclaim (dataset = main results) | DONE | Q1_CLAIM_LANGUAGE.md prohibits |

---

## Gate Results After Remediation

| Gate | Status | Notes |
|---|---|---|
| G0 Claim-evidence congruence | PARTIAL | label_status field added; session-grain pending |
| G1 Construct validity | DONE | Construct/process separated |
| G2 Reliability | PENDING | IRR human coding not yet conducted |
| G3 Sampling/generalizability | PARTIAL | Student split done; 2026 external val needed |
| G4 Measurement design | DONE | Session-grain evaluator built; debug flag set |
| G5 Open science | PARTIAL | Paths fixed; ethics/IRB documentation needed |
| G6 Statistical reporting | PARTIAL | Weighted-F1 to add; multi-label note needed |
| G7 Few-shot adequacy | DONE | fewshot_examples_v2.json with 2 pos + 2 neg per behavior |

---

## Deliverables Checklist

### FAZ 0 — Claim Language
- [x] `framework/Q1_CLAIM_LANGUAGE.md`
- [ ] Add claim language note to `calibration/README.md`

### FAZ 1A — Dataset v2
- [x] `schema/calibration_dataset_v2.schema.json`
- [x] `scripts/build_2025_calibration_dataset_v2.py`
- [x] `calibration/2025_calibration_dataset_v2.json` (2753 frames, 0 absolute paths)

### FAZ 1B — Provenance
- [x] `calibration/runs/run_manifest.schema.json`
- [x] `scripts/write_run_manifest.py`
- [ ] Run manifests for past validation runs (retroactive, as notes)

### FAZ 1C — Leakage-safe splits
- [x] `calibration/splits_2025.json` (fewshot ∩ irr = ∅ verified)

### FAZ 1D — Few-shot v2
- [x] `scripts/build_fewshot_examples_v2.py`
- [x] `calibration/fewshot_examples_v2.json` (2 pos + 2 neg per B0-B12)

### FAZ 2 — IRR
- [x] `framework/IRR_CODING_PROTOCOL_v1.md`
- [x] `scripts/sample_irr_units.py` → `calibration/irr_sample_manifest.json`
- [x] `calibration/irr_coding_sheet.csv` (80 episodes, 2 rater rows each)
- [x] `scripts/compute_irr.py`
- [ ] **HUMAN TASK**: Complete irr_coding_sheet.csv with two independent raters
- [ ] **HUMAN TASK**: Run compute_irr.py; verify κ ≥ 0.70 per behavior

### FAZ 3 — Session grain
- [x] `scripts/evaluate_session_construct_agreement.py`
- [x] `calibration/session_validation_metrics.json` (scaffold; needs 2026 scoring)
- [ ] Run mmla_scorer.py on 2026 sessions → populate session_validation_metrics

### FAZ 4 — Process quarantine
- [x] `calibration/process_layer_validation_notes.md`
- [ ] Update mmla_scorer.py scorer output to flag B15/B16/B17 as process_layer=true

### FAZ 5 — Paper pack
- [x] `framework/Q1_METHOD_DATASET_CHECKLIST.md` (this file)
- [ ] Dataset card draft (HF-compatible)
- [ ] Methods section draft with correct claim language

---

## Remaining Human Tasks (cannot be automated)

1. **IRR coding**: Two independent human raters must complete `irr_coding_sheet.csv`
2. **Ethics/IRB**: Document IRB approval or exemption for student video data
3. **CVI/CVR panel**: Expert panel review of rubric for construct validity
4. **2026 scoring**: Run mmla_scorer.py on 2026 sessions to enable session-level comparison
5. **Dataset card**: Write HF-compatible dataset card linking to existing tabular exports

---

## Minimum before submission

All boxes above marked HUMAN TASK must be completed.
After IRR coding: re-run compute_irr.py and verify κ ≥ 0.70.
After 2026 scoring: re-run evaluate_session_construct_agreement.py.
Update this checklist with evidence before submitting.
