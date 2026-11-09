# WS12 published revision — 20261109-v2

Scope: 2026 WS12 only. Thirteen students share seven physical submissions. Melinda/Serena have no submission. This is manually reviewed transcription followed by deterministic internal-consistency checks, not an independent AI benchmark and not a human–machine agreement result.

## Changes

- Physical numbering corrected: terminal decisions10–13, training/test errors14–15. Class selections, node features and numeric counts remain distinct.
- Checks accept a selected printed class option or explicit text; ambiguous marks remain unknown. Bruno/Irma root threshold0.6, displaced Enerji and separate horizontal counts are preserved from the scan. Helena/Shana left count5 is not historical6.
- Pure-node stopping makes unused descendants `structural_na`, not extra correct items. A purity/stop inference needs independently observed counts; the human `|` annotation is not an input.
- Threshold pairs compare numeric cutpoints AND complementary operators, support decimal commas and constant-left operators. Ambiguity is not automatically accepted. A pair failure concerns the pair, not proof of which isolated branch is at fault.
- Node-count conservation uses independent parent/child observations, class by class, with no circular inference.
- Training errors use the actual predicted class at active terminal nodes. Test-error recording alone does not establish correctness. No assumed8/11/14/20-card dataset.
- Leaf counts alone do not establish the predicted class. Missing counts/decisions and unresolved branch activity remain unknown. Feature/threshold checks establish only the stated local criterion, not optimality or fidelity to a chosen WS6 tree.

## Sources and preservation

`observations.json` contains seven scan-reviewed groups, page numbers and ambiguities. Its SHA256 is checked against the existing public completed WS12 PDF, which is byte-identical to the supplied PDF. `source_hashes.json` checks all existing student WS12 JSON artifacts and the PDF. None is overwritten. Human Excel/codes are not scoring inputs and are unchanged.

`previous_rubric.json`, `previous_extraction_schema.json`, `previous_scorer.py` are historical snapshots for interpretation only. Current rubric/schema/scorer live in their usual project paths. Historical `WS12_R*` maxima are resolved using the archived rubric, never the new printed-item rubric.

New results are in `scoring.json`. The site loads `data/ws12_review.js` and `assets/ws12_review.js` after the existing core/docs data, replacing WS12 only at runtime. Original `core.js` is not rebuilt or committed by this release. No other worksheet record is changed. Superseded WS12 totals are withheld across site views; current details are displayed in Worksheet findings. Do not edit generated JS by hand: regenerate it with the command below. A future full site build must retain these script tags; the versioned overlay remains authoritative for WS12.

## Reproduce

```sh
python3 scripts/score_ws12.py --publish-data
python3 -m unittest scripts.test_score_ws12 mmla_explorer.test_stage_credit_colors -v
node mmla_explorer/test_ws12_review.js
```

The scorer writes only the revision folder and the explicit WS12 public JS/download files. `--dry-run` writes nothing. It does not rerun a language model or automatically reinterpret scans.

## Verified checks

- 26 Python tests passed:19 scoring/source tests and7 color regressions.
- WS12 rubric passed `pipeline_schema.validate_rubric`.
- JS integration test passed:15 printed columns,13 participant rows,7 groups, status separation, no legacy total leakage, script order and non-WS12 records unchanged.
- Integration also passed against committed `core.js` rather than the user's uncommitted local changes.
- Headless Chromium: WS12, catalogue, WS6, collected WS12, Helena profile and participant index opened without JavaScript errors. Mobile390px had no document overflow; each stacked cell has its printed-item label. Desktop1440px reviewed visually.
- 195 participant-item statuses reconcile:76 correct by local criterion,30 structural_na,79 unknown,10 confirmed blank. These are not independent195 observations and not a performance accuracy numerator/denominator. Complete totals withheld because all groups have unresolved applicable items.

Broader legacy checks are not certified: `test_worksheet_findings.js` has39 failures, reproduced identically with the pre-change asset; `test_student_profiles.js` has5 pre-existing expectation failures (its source and ordinary loaded data are unchanged by this revision). Global `validate_pipeline_outputs.py` cannot complete because tracked repository schema/student_extraction.schema.json is absent; jsonschema was installed in a temporary environment to verify this concrete blocker. These unrelated failures were not repaired or hidden.

## Remaining evidence

A documented WS12 training/test card set, chosen/revised group tree provenance and adjudicated ambiguous operators are needed for a complete correctness reference. In particular, Isabel/Ulysses item4 is visibly nonblank, but current scan evidence does not independently establish the user's human code−1. No rule is tailored to reproduce that human verdict. No post-revision Cohen kappa/accuracy is claimed here.
