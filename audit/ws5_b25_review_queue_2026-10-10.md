# WS5 Item B25 — Manual Review Queue
**Date:** 2026-10-10 (updated with provisional researcher decisions)  
**Scope:** 13 students whose WS5_B25 received score=0  
**Status:** Provisional researcher decisions entered. Error counts for Sheila and Serena computed from rec/not_rec (no source PDF needed). Three rows remain Researcher-must-decide. No scoring.json files modified.

---

## Rubric Reference

**WS5_B25** (`max_score = 1.0`, check: `b25_minimum_errors`)

> The student must record the threshold from their own trial table that produced the fewest misclassifications (student-calculated errors, not the system's).

| Score | Condition |
|---|---|
| 1.0 | Threshold from the minimum-error trial, written with variable name |
| 0.5 | Minimum-error threshold written without variable name, OR a non-minimum grid threshold (with or without variable) |
| 0.0 | Threshold not in the grid at all, or blank |

---

## Root Cause of Scorer Failure

**All 13 students scored 0.0 due to a scorer limitation, not all due to student error.**

The `_match_b25_to_row()` function attempts to match the student's B25 text against grid trials in three ways: (1) parsed threshold signature match, (2) substring of trial threshold in prose, (3) feature+value pair match.

All three fail here because `parse_threshold_expression()` returns `None` for full Turkish question sentences. The OCR captured the printed form prompt ("Protein değişkeni için hangi eşik değerini seçiyorsunuz? Not alın:") together with the student's handwritten response ("2,55") as a single string. The parser expects a clean threshold expression, not a full printed question.

This was confirmed by direct invocation of `validate_ws5_b25()` with the correct `remap_to_rubric_cells()` mapping for all 13 students:

- **12 students** have 3 arithmetic_ok trials (grid data is valid; only Sheila has 1, Serena has 0)
- All 12 return `reason=threshold_not_in_grid` — not because the threshold is absent from the grid, but because the matcher cannot extract it from the prose sentence
- The scorer does **not** raise a review flag for this case; it silently returns zero

**Consequence:** Students who correctly identified the minimum-error threshold in their prose response received 0.0 with no review flag. The current scoring.json files for these students contain incorrect credit values for WS5_B25.

---

## Review Table

Two students (Amy, Marco) had no WS5 OCR data and were skipped. They are not in this queue.

| # | Student | final_decision_raw (verbatim) | Grid trials (arithmetic_ok) | Minimum errors | Extracted threshold | In grid? | Minimum-error trial? | Provisional rubric tier | Researcher decision | Researcher rationale |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Bruno | "Protein değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: 2,55" | T1: Doymuş Yağ ≤ 0.05 (4) / **T2: Protein ≤ 2.55 (3)** / T3: Tuz ≤ 0.15 (4) | 3 (T2, unique) | Protein, 2.55 (2,55=2.55) | **Yes — T2** | **Yes — unique minimum** | **1.0** | **1.0** | Correct variable + minimum-error threshold. Scorer failure only (prompt prefix unparseable). |
| 2 | Helena | "Enerji değişkeni için 192 değerini seçiyorum. Çünkü diğerlerine göre yanlış sınıflandırma sayısı daha az çıktı." | **T1: Enerji ≤ 192.0 (2)** / **T2: Yağ ≤ 13.5 (2)** / T3: Tuz ≤ 0.6 (4) | 2 (T1+T2 tied) | Enerji, 192 (192=192.0) | **Yes — T1** | **Yes — minimum (tied)** | **1.0** | **1.0** | Named variable + minimum-error threshold (tied). Student explicitly cited lower error count as rationale. |
| 3 | Iris | "Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Not alın:" | T1: Protein < 2.0 (3) / **T2: Şeker < 30.0 (2)** / T3: Tuz < 0.2 (4) | 2 (T2, unique) | Nothing after colon | — | — | **0.0** (blank) | **0.0** | Nothing written after the colon. Blank response. |
| 4 | Irma | "Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: \[cevap alanı boş bırakılmış\]" | T1: karbonhidrat <= 35.5 (2) / **T2: şeker <= 30.0 (1)** / T3: protein ≤ 3.0 (3) | 1 (T2, unique) | OCR-confirmed blank | — | — | **0.0** (blank, OCR-confirmed) | **0.0** | OCR explicitly notes blank answer field. |
| 5 | Isabel | "Yağ değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: 13,5 eşik değeri belirledim." | **T1: Enerji ≤ 191.5 (2)** / T2: Doymuş yağ ≤ 8.3 (3) / **T3: Yağ ≤ 13.5 (2)** | 2 (T1+T3 tied) | Yağ, 13.5 (13,5=13.5) | **Yes — T3** | **Yes — minimum (tied)** | **1.0** | **1.0** | Named variable + minimum-error threshold (tied). Scorer failure only. |
| 6 | Marcus | "yağ değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: 13,8" | **T1: yağ <= 13.5 (2)** / T2: şeker <= 10.0 (3) / T3: protein <= 2.0 (3) | 2 (T1, unique) | yağ, 13.8 | **No — 13.8 ≠ 13.5 (closest grid entry)** | — | **0.0** (threshold not in grid) | **0.0** | 13.8 is not a grid threshold. Student named variable but recorded the wrong number. |
| 7 | Nadia | "Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Not alın:" | **T1: Şeker <= 29.0 (2)** / T2: Protein <= 2.0 (3) / T3: Tuz <= 0.6 (4) | 2 (T1, unique) | Nothing after colon | — | — | **0.0** (blank) | **0.0** | Nothing written after the colon. Blank response. |
| 8 | Shana | "karbonhidrat değişkeni için hangi eşik değerini seçiyorsunuz? Not alın:" | **T1: enerji ≤ 200.0 (2)** / **T2: karbonhidrat ≤ 25.0 (2)** / T3: protein ≤ 3.0 (3) | 2 (T1+T2 tied) | Nothing after colon | — | — | **0.0** (blank) | **0.0** | Nothing written after the colon. Blank response. |
| 9 | Sheila | "enerji değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: eski bilgilerime göre daha değer sonucu verdiğini düşünüyorum" | **T1: enerji < 161.0 (2)** / **T2: karbonhidrat < 16.0 (2)** / **T3: şeker < 12.0 (2)** | 2 (all 3 tied; errors computed from rec/not_rec: left_not_rec + right_rec) | enerji — no numeric value written | Partial (variable matches T1, which is tied minimum) | T1 is a minimum-error trial (tied) | **Ambiguous**: variable correctly names a minimum-error trial; no number written. Rubric 0.5 covers "only number, no variable" — the inverse (only variable, no number) is not explicit. Could be 0.0 or 0.5. | **Researcher must decide** | Variable name written but no numeric threshold. Errors computed: all 3 trials tie at 2. Enerji is a valid minimum-error trial. Rubric does not explicitly cover variable-only responses. |
| 10 | Ulysses | "protein değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: 2" | **T1: karbonhidrat ≤ 20.0 (2)** / **T2: şeker ≤ 2.0 (2)** / T3: protein ≤ 2.0 (5) | 2 (T1+T2 tied) | protein, 2 (= protein ≤ 2.0) | **Yes — T3** | **No — T3 has 5 errors (worst trial)** | **0.5** (threshold in grid but not minimum-error trial) | **0.5** | Threshold value is in the grid (protein ≤ 2.0) but it is the worst trial (5 errors). Student identified the wrong trial. Rubric 0.5: "tablodaki başka (daha yüksek hatalı) bir eşiği seçmişse." |
| 11 | Zara | "Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: Hata Sayısı 2 daha kullanışlı." | **T1: Enerji < 200.0 (2)** / T2: Protein < 2.0 (3) / **T3: Şeker < 2.0 (2)** | 2 (T1+T3 tied) | "Hata Sayısı 2" — "2" is ambiguous (could be threshold < 2.0 or error count 2) | Ambiguous | If "2" = threshold: T3 matches (minimum, tied). If "2" = error count: no threshold stated | **Ambiguous**: 0.0 (no threshold stated) or 0.5–1.0 (if "2" references Şeker trial). Source PDF recommended. | **Researcher must decide** | "Hata Sayısı 2" = "Error Count 2". If read as the threshold value, Şeker < 2.0 matches T3 (minimum tied). If read as describing the error count only, no threshold is stated. |
| 12 | Melinda | "Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Not alın: Eşik değeri 29 gr" | T1: protein < 2.0 (3) / **T2: şeker < 29.0 (2)** / T3: tuz < 0.15 (4) | 2 (T2, unique) | Şeker, 29 gr (29=29.0) | **Yes — T2** | **Yes — unique minimum** | **1.0** | **1.0** | Named threshold with unit (29 gr = 29.0). Unique minimum-error trial. Scorer failure only. |
| 13 | Serena | "Enerji ve Şeker değişkeni için hangi eşik değerini seçiyorsunuz? Çünkü 2 hata var ikisinde de" | **T1: Enerji < 200.0 (2)** / **T2: Şeker < 2.0 (2)** / T3: Protein < 2.0 (3) | 2 (T1+T2 tied; errors computed from rec/not_rec: T1=0+2=2, T2=1+1=2, T3=1+2=3) | Enerji + Şeker named; "2 hata ikisinde de" = "2 errors in both"; no numeric threshold values | Both T1 and T2 are in grid; both are minimum-error (tied) | Yes — both Enerji and Şeker are minimum-error trials | **Ambiguous**: both minimum-error variables named, error count stated correctly ("2 hata var ikisinde de"), but no threshold numbers (200.0 / 2.0). Rubric 1.0 requires variable + threshold number. Rubric 0.5 covers number-only or non-minimum-error threshold. Variable + error count but no threshold number is not explicitly covered. Could be 0.0, 0.5, or 0.5–1.0. | **Researcher must decide** | Variables correct, error count correct, threshold numbers omitted. Errors computed without source PDF: T1=2, T2=2, T3=3. T1 and T2 tied for minimum. |

---

## Summary by Researcher Decision

| Decision | Students | Count |
|---|---|---|
| **1.0 — full credit** | Bruno, Helena, Isabel, Melinda | 4 |
| **0.5 — partial credit** | Ulysses | 1 |
| **0.0 — confirmed zero** | Iris, Irma, Marcus, Nadia, Shana | 5 |
| **Researcher must decide** | Sheila, Zara | 2 |
| **Researcher must decide** | Serena | 1 |

**Net score change if all 1.0 and 0.5 decisions are applied:** Bruno +1.0, Helena +1.0, Isabel +1.0, Melinda +1.0, Ulysses +0.5. No scoring.json files modified yet.

---

## Scorer Limitation — Recommended Fix

The `_match_b25_to_row()` function should attempt an additional extraction pass: strip the printed prompt prefix ("…için hangi eşik değerini seçiyorsunuz? Not alın:") from the B25 text before parsing. This prefix is a known printed template that appears on all students' worksheets. Removing it would leave only the student's handwritten response, which is parseable.

**Do not implement this fix now** — it would change scoring outputs for potentially scored students. Document for researcher review.

---

## Notes for Reviewer

1. Do not alter `extraction.json` files. `final_decision_raw` is read-only.
2. To apply a decision, edit only the `WS5_B25` entry in `students/{student}/WS5/scoring.json` — update `score`, `credit`, and `rationale`.
3. If Bruno, Helena, Isabel, and Melinda receive 1.0, each WS5 total increases by 1.0.
4. If Ulysses receives 0.5, their WS5 total increases by 0.5.
5. Sheila: source PDF check may clarify whether the student wrote only the variable or also a threshold value that OCR missed.
6. Zara: "Hata Sayısı 2 daha kullanışlı" — if the researcher interprets "2" as the Şeker threshold value (Şeker < 2.0), this is a minimum-error tied trial; partial or full credit could apply.
7. Serena: Error counts computed from rec/not_rec without source PDF: T1 Enerji=2, T2 Şeker=2, T3 Protein=3. Both T1 and T2 are minimum-error (tied). Serena named both variables and stated "2 hata var ikisinde de" (2 errors in both) — factually correct. No threshold numbers written. Rubric decision required.
