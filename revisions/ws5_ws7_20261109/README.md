# WS5–WS7 corrections, 2026-11-09

Requested researcher correction: Serena WS5 final decision is **Enerji ve Şeker**.
The renderer had a stale `Protein ve Enerji` override in addition to the first-feature-only extraction display.

WS6: show operators together with each threshold at every level; check the same numeric cutpoint AND complementary inequalities. Normalize visibly constant-left notation (e.g. `28 ≥ x` → `x ≤ 28`). Recover Sheila's written `>11 / <11` pair without silently making it complementary. Unwritten inequalities remain missing; structural stopping exceptions remain unchanged.

WS7: the supplied annotated template and the three printed rules in completed/WS7.pdf establish the fixed key `<180 kcal`, `≥180 kcal`, `<7.7 g`, `≥7.7 g`, B, A, C. This is not a free threshold search based on WS6. `≤180` is not `<180`; protein 11 is not 7.7. Amy's two root blanks were incorrectly populated from the lower protein node. Additional clearly visible transcription/constant-left corrections are recorded in corrections.json. Original scanned PDFs and raw extraction files remain intact; the normalized extraction and derived scores are corrected.

`corrections.json` records original and corrected values plus visual evidence. `ws7_score_changes.json` records original HEAD and corrected totals (42/91 → 2/91, 13 present participants). The absent Melinda/Serena worksheets retain their missing-source status.

Validation: 17 Python tests passed (WS6, legacy WS7 and new fixed printed-rule cases); the focused JS WS5/6/7 rendering/data test passed; structural stopping regression passed. The existing worksheet findings test has the same 39 failures before/after (outdated layout assertions). General data fidelity checks have existing WS13 failures, outside this correction.
