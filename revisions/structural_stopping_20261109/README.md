# Accepted stopping policy — 20261109-stopping-v1

The user explicitly requested that human `|` cases previously treated as blank be accepted as correct stopping actions and visibly distinguished on the website. This is an adjudicated applicability update, not new blind machine accuracy.

Three root participant records arise from two stopping decisions/artifacts:

- Zara / WS6 printed4: published extracted `(bos)` had a red/incorrect displayed verdict. User reference marks it `|`. The root and its unused descendants (printed5–8) now display `| · Valid stop` in three displayed units, preserving prior source scores.
- Marcus & Marco / shared WS12 page6, printed4: published blank status. User reference marks it `|`. The accepted left stop makes printed6,7,10,11 unused as well. Five fields on one shared sheet produce ten participant display records.

Thus thirteen displayed participant records change; only three root participant records (two physical cases) initiate the exceptions. The descendants are not additional independent correct stopping decisions. All affected human codes were verified as `|` in Code book12092026-3.xlsx, with source SHA256 and Excel cells in policy.json. No Excel or original extraction/scoring file was edited.

Existing WS12 structural-na statuses also display the distinct `|` label. `|` is accepted as a correct action, but is not silently converted into an ordinary correct answered-item score. Substantive four-class scoring denominators remain separate. Other null/unknown cases are not presumed blank or automatically corrected. Explicit source flags elsewhere in WS6 are not promoted under this narrowly scoped review.

## Rebuild

```sh
python3 scripts/build_stopping_review.py --human '/Users/mrved/Downloads/Code book 12092026-3.xlsx'
node mmla_explorer/test_structural_stopping.js
node mmla_explorer/test_ws12_review.js
python3 -m unittest scripts.test_score_ws12 mmla_explorer.test_stage_credit_colors -v
```

The script writes this new revision and public stopping-review artifacts only. Base WS12 v2 outputs and all raw student JSON remain unchanged. The site loads the base review and then the explicit researcher-reviewed applicability overlay. The merged WS12 download matches the revised displayed statuses. The published notes disclose the human-informed origin.

Known legacy global validation blocker, unrelated to this update: missing schema/student_extraction.schema.json. Dedicated scoring, provenance and display tests pass; global pipeline validation is not claimed successful.
