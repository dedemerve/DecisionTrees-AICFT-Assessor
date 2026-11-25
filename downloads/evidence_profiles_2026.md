# Student profiles (draft 1: Amy, Bruno)

Source: https://dedemerve.github.io/DecisionTrees-AICFT-Assessor/ , read on 2026-11-08 with every "Technical details" block opened.

## Method note

Each profile reports what the stored records show. Worksheet values come from up to three displays on the site, and each is labelled:

- **Page** = the worksheet findings page, "Student results" block (#/findings/worksheets/WSn). This is the answer-key check ("Verdict uses the answer-key check from the extraction file").
- **Profile** = the item line on the student profile, Worksheets tab (#/explore/student/Name).
- **Stage file** = the "STAGE SCORE FILE · Total" inside the profile's Technical details for that worksheet. These totals use the same maxima as the worksheet page's "Average score" (for example /27 on WS13).

Cohort figures are copied from the worksheet page header ("Average score") and its "Class analysis" block ("Average correct rate"). They are given as displayed and are not compared with the participant's value.

The limitations page states: "For six participants, a later stage file for worksheet 14 does not repeat the published reading. This site follows the OCR file." The six participants are not named (F13).

Frame labels and confidence ratings are model output. There is no second coder and no agreement statistic (#/docs/limitations, "No second coder"). Episode lists (EXPLORE, EVALUATE, MISCONCEPTION, TUNE) are not used. The Titanic activity log is excluded from every log value. WS11 is not used.

Sentence and row identifiers in square brackets (for example [A12]) link each number to the ledger map.

---

### Amy

**Evidence available.**

- Worksheets: partial. The profile's Evidence notes read "No worksheet extraction for WS1, WS3, WS4, WS5." Those four cards read "no answers on file", and Amy is not listed in their Student results blocks. [A1]
- Screen-recording frames: partial. CODAP session 1 is present. CODAP session 2 reads "No screen recording from this session.", and the Evidence notes read "No extracted frames for CODAP session 2." [A2]
- Platform logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [A3]
- Final Python submission: present, a notebook. [A4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage file | Flag | Cohort as displayed on the page |
|---|---|---|---|---|---|---|---|---|
| A5 | Concepts | WS1 | Rubric score | not listed | no answers on file | none | gap | 13 of 15 participants included |
| A6 | Concepts | WS3 | Rubric score | not listed | no answers on file | none | gap | 13 of 15 participants included |
| A7 | Concepts | WS4 | Rubric score | not listed | no answers on file | none | gap | 13 of 15 participants included |
| A8 | Thresholds | WS5 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| A9 | Thresholds | WS10 | Rule-checked item | 4 / 8 correct (50%) | 4 of 8 items correct | 4 of 8 | none | Average score 93% (7.46 / 8); average correct rate 89% |
| A10 | Rules | WS7 | Rule-checked item | 2 / 4 correct (50%) | 2 of 7 items correct | 2 of 7 | F1 | Average score 40% (2.8 / 7); average correct rate 40% |
| A11 | Documentation | WS6 | Rule-checked item | 8 / 8 scored correct (100%) | 31 answers | 4 of 4 | F4 | Average score 76% (3.04 / 4); average correct rate 63% |
| A12 | Documentation | WS12 | Consistency check | 6 / 6 correct (100%) | 6 of 6 items correct | 7 of 7 | stage file differs | Average score 71% (5 / 7); average correct rate 72% |
| A13 | CODAP | WS13 | Rubric score | 12 / 15 correct (80%) | 12 of 31 items correct | 9.5 of 27 | F1 | Average score 41% (11.2 / 27); average correct rate 32% |
| A14 | CODAP | WS14 | Rubric items plus rule checks | 33 / 33 correct (100%) | 37 of 37 items correct | 18.5 of 33 | F1, F5 | Average score 47% (15.6 / 33); average correct rate 95% |
| A15 | CODAP | WS15 | Rubric items plus rule checks | 33 / 38 correct (86.8%) | 48 of 67 items correct | 24 of 47 | F1 | Average score 47% (22.3 / 47); average correct rate 69% |

WS6 is placed with documentation because the brief's grouping does not list it. [A16]

Item-level results the site shows for Amy:

- WS10 (rule-checked items): the best threshold was written as 408 and marked "✓ Correct". Items 4 to 7 were marked "✗ Not correct", each with the check flag "count_mismatch". [A17]
- WS7 (rule-checked items): items 5, 6 and 7 were blank and marked "✗ Not correct". [A18]
- WS6 (rule-checked items): the validation values list 2 error flags, both count mismatches (depth 1 left child; depth 2 left-right leaf). [A19]
- WS13 (rubric score): all items in parts E, F and G were blank and marked "✗ Not correct". The Technical details list 18 items with the flag "review". [A20]
- WS14 (rubric items plus rule checks): all 4 further checks (counts add up, total n, FP and FN zero) were marked "✓ Correct". [A21]
- WS15 (rubric items plus rule checks): the 5 rule checks for Sample 2 test (accuracy, sensitivity, specificity, precision, MCR) were "✗ Not correct". Questions 1 to 4, 20 to 22, 43 and 44 were blank. The validation values flag the Sample 1 test root node as ROOT_COUNT_ERROR (student value "96=56+40", canonical 231). The same answer, Question 10, is marked "✓ Correct" in the item table. Both displays are reported. [A22]

Profile header, as displayed: "CODAP worksheets: mean score 47.4% of the maximum, across 3 of WS13, WS14 and WS15". The participants page states the method: "the mean of each participant's stored score divided by that worksheet's maximum, for WS13, WS14, and WS15." This value is not used to rank (F6). [A23]

**CODAP screen recordings.**

CODAP session 1 (frame labels). [A24]

| Item | Value |
|---|---|
| Length of the source recording | 1 h 23 min |
| Frames listed | 370 |
| Frames with a behaviour label | 370 |
| Speech status | ok (segments by role: classmate 983, teacher 659, student 310) |
| Coding model | claude-sonnet-5 |

| ID | Label | Frames | Share |
|---|---|---|---|
| A25 | Explore data | 140 | 37.8% |
| A26 | Build tree | 1 | 0.3% |
| A27 | Tune threshold | 9 | 2.4% |
| A28 | Evaluate model | 67 | 18.1% |
| A29 | Compare models | 136 | 36.8% |
| A30 | Interpret results | 1 | 0.3% |
| A31 | Idle / thinking | 3 | 0.8% |
| A32 | Off task | 13 | 3.5% |

The findings page prints: "The two largest shares are close. Explore data is 140 of 370 labelled frames (37.8%), and Compare models is 136 of 370 (36.8%)." [A33]
It also prints: "In the first part, Explore data is 88 of 95 labelled frames (92.6%). In the last part, it is 0 of 129 (0%)." These are counts of labelled frames in each third of the session clock, not minutes. [A34]
The primary label changed 57 times between segments of listed frames. [A35]
The model's self-rated coding confidence was 204 high and 166 medium. This is not an agreement statistic. [A36]
196 frames have a second behaviour label, which the shares exclude. [A37]

CODAP session 2: "No screen recording from this session." [A38]

**CODAP platform logs.** Titanic log excluded.

CODAP session 1 (log counts). [A39]

| ID | Measure | Value as displayed |
|---|---|---|
| A40 | Model attempts | 11 |
| A41 | First attempt | 46 min after starting |
| A42 | Accuracy of last attempt | 76.2% (n = 42, Food_Dataset_Turkish_55 (1)) |
| A43 | Target | Column 1 (recommendation label, unnamed copy) |
| A44 | Predictors tried | Doymuş Yağ (g) (saturated fat), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat) |
| A45 | Threshold edit events (split editor used) | 11 |
| A46 | One kind of edit (VOTAT) | 100% of 10 steps between submissions |
| A47 | Predictor placements | 19 |
| A48 | Total actions | 402 |
| A49 | Session span | 82 min (UTC 08:09:49 to 09:31:30) |
| A50 | Accuracy spread (SD) | 0.086 |
| A51 | Submissions that scored no rows | no such note is displayed for this session |

The last-attempt accuracy is not comparable across students or sessions. The VOTAT share describes the order of logged actions between submissions. It does not show a planned experiment. Split editor events do not show that a threshold value changed. [A52]

CODAP session 2: "No class-session log is stored." [A53]

**Final Python submission.** Notebook trace. Files were not rerun.

| ID | Assignment requirement | Evidence status | Details |
|---|---|---|---|
| A54 | Load the dataset | Found | |
| A55 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| A56 | Separate training and test data | Found | Test fraction 0.3 is recorded. |
| A57 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| A58 | Explore tree depth | Found | Depth-search table stored for 1 of 3. |
| A59 | Evaluate performance | Found | A test error is stored for 1 target. Training and test curves are stored for 1 |
| A60 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| A61 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

- Targets: Tur, Cinsiyet, YasamAlani. The depth range "1 to 5" is listed for Tur; the other two show "–". [A62]
- Research questions written out: 0 of 3. [A63]
- Cells: 22 (16 code, 6 text). Code cells run: 16 of 16. Empty code cells: 0. [A64]
- Errors in the outputs: None. Revisiting earlier code: Never. [A65]

Stored rubric points (pipeline points, rubric 1.0-draft, not a reviewed grade; scored by pipeline_hybrid). [A66]

| Section | Points | Possible |
|---|---|---|
| S1 | 10 | 10 |
| S2 | 0 | 5 |
| S3 | 4 | 5 |
| S4 | 8 | 30 |
| S5 | 8 | 21 |
| S6 | 19 | 20 |
| S7 | 7 | 9 |

A total is not displayed on the site. [A67]

**Across sources (descriptive juxtaposition only).**

The WS13 answer-key check on the worksheet page was 12 / 15 correct (80%), and the stage file total was 9.5 of 27. [A68] In CODAP session 1, Explore data was 140 of 370 labelled frames (37.8%). [A69] The session 1 log recorded 11 split editor events, and the final notebook stored a depth-search table for 1 of 3 targets. [A70]

**Missing data and caveats.**

- No extracted answers for WS1, WS3, WS4, WS5 (Evidence notes). Missing evidence, not zero.
- No frames and no log for CODAP session 2. Missing evidence, not absent behaviour.
- F1: WS7, WS13, WS14, WS15 show different numerators and denominators on the page and the profile. A third value appears in the stage file.
- F4: WS6 profile shows "31 answers" (a count of fields). Only the page value (8 / 8 scored correct) and the stage file (4 of 4) are scores.
- F5: WS14 cohort average score 47% (rubric) vs average correct rate 95% (answer check).
- F6: header mean 47.4% is reported as displayed and not used to rank. The participants page states its method (see site discrepancies below).
- WS12: page 6 / 6 vs stage file 7 of 7.
- WS15: Question 10 is marked correct in the item table and flagged ROOT_COUNT_ERROR in the validation values.
- F11: cohort action totals are not used. The per-session "Total actions" (402) is the student log tab value, which the page states excludes the Titanic log.
- F13: applies to WS14 for six unnamed participants. It is not known whether Amy is one of them.
- Frame labels and confidence are model output with no second coder.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| A1 | WS1, WS3, WS4, WS5 | #/explore/student/Amy, Evidence notes; #/findings/worksheets/WS1–WS5, Student results | worksheet coverage |
| A2 | session 2 | #/explore/student/Amy/recordings, CODAP 2; Evidence notes | frame coverage |
| A3 | session 2 | #/explore/student/Amy/logs, CODAP session 2 | log coverage |
| A4 | – | #/explore/student/Amy/notebook | notebook trace |
| A5–A8 | 13 of 15 | #/findings/worksheets/WS1, WS3, WS4, WS5, header | worksheet coverage |
| A9 | 4 / 8 (50%); 4 of 8; 4 of 8; 93% (7.46 / 8); 89% | WS10 page Student results, header, Class analysis; profile WS10 card and Technical details | rule-checked item |
| A10 | 2 / 4 (50%); 2 of 7; 2 of 7; 40% (2.8 / 7); 40% | WS7 page; profile WS7 | rule-checked item |
| A11 | 8 / 8 (100%); 31; 4 of 4; 76% (3.04 / 4); 63% | WS6 page; profile WS6 | rule-checked item |
| A12 | 6 / 6 (100%); 6 of 6; 7 of 7; 71% (5 / 7); 72% | WS12 page; profile WS12 | consistency check |
| A13 | 12 / 15 (80%); 12 of 31; 9.5 of 27; 41% (11.2 / 27); 32% | WS13 page; profile WS13 | rubric score |
| A14 | 33 / 33 (100%); 37 of 37; 18.5 of 33; 47% (15.6 / 33); 95% | WS14 page; profile WS14 | rubric items plus rule checks |
| A15 | 33 / 38 (86.8%); 48 of 67; 24 of 47; 47% (22.3 / 47); 69% | WS15 page; profile WS15 | rubric items plus rule checks |
| A16 | – | brief section 7 | none |
| A17 | 408; items 4 to 7 | profile WS10 item table and Check flags | rule-checked item |
| A18 | items 5, 6, 7 | profile WS7 item table | rule-checked item |
| A19 | 2 error flags; depth 1; depth 2 | profile WS6 Technical details, Other validation values | rule-checked item |
| A20 | 18 | profile WS13 item table and Check flags | rubric score |
| A21 | 4 | profile WS14 Further checks | rule check |
| A22 | 5 checks; Q1–4, 20–22, 43, 44; 96=56+40; 231; Q10 | profile WS15 Further checks, Check flags, Other validation values | rubric items plus rule checks |
| A23 | 47.4%; 3 | profile header; #/findings/participants, comparison table note | stored-score mean |
| A24 | 1 h 23 min; 370; 370; 983, 659, 310 | #/explore/student/Amy/recordings, CODAP 1 and Technical details | frame label |
| A25–A32 | 140, 37.8%; 1, 0.3%; 9, 2.4%; 67, 18.1%; 136, 36.8%; 1, 0.3%; 3, 0.8%; 13, 3.5% | recordings tab label table; #/findings/recordings?s=Amy, Observed behaviour | frame label |
| A33 | 140 of 370 (37.8%); 136 of 370 (36.8%) | #/findings/recordings?s=Amy, What stands out? | frame label |
| A34 | 88 of 95 (92.6%); 0 of 129 (0%) | same, What stands out? and Across the session clock | frame label |
| A35 | 57 | same, What stands out? | frame label |
| A36 | 204; 166 | same, Limitations | model self-rating |
| A37 | 196 | same, Limitations | frame label |
| A38 | session 2 | recordings tab, CODAP 2 | frame coverage |
| A39–A51 | 11; 46 min; 76.2%, n = 42; 11; 100% of 10; 19; 402; 82 min, 08:09:49, 09:31:30; 0.086 | #/explore/student/Amy/logs, CODAP session 1 and Technical event details | log count |
| A53 | session 2 | logs tab, CODAP session 2 | log coverage |
| A54–A61 | 0.3; 3; 1 of 3; 1; 1; 3; 4 of 4 | #/explore/student/Amy/notebook, requirement table | notebook trace |
| A62 | 3 targets; 1 to 5 | notebook, Trees built | notebook trace |
| A63 | 0 of 3 | notebook, Technical details | notebook trace |
| A64 | 22, 16, 6; 16 of 16; 0 | notebook, Technical details | notebook trace |
| A65 | None; Never | notebook | notebook trace |
| A66 | 10/10, 0/5, 4/5, 8/30, 8/21, 19/20, 7/9; 1.0-draft | notebook, Stored rubric points | stored rubric points |
| A67 | – | notebook | stored rubric points |
| A68 | 12 / 15 (80%); 9.5 of 27 | WS13 page; profile WS13 Technical details | rubric score |
| A69 | 140 of 370 (37.8%) | #/findings/recordings?s=Amy | frame label |
| A70 | 11; 1 of 3 | logs tab; notebook tab | log count; notebook trace |

Checklist: all ten items answered yes.

---

### Bruno

**Evidence available.**

- Worksheets: present for all eleven scored worksheets. The profile shows no Evidence notes block. [B1]
- Screen-recording frames: present for CODAP session 1 and CODAP session 2. [B2]
- Platform logs: present for CODAP session 1 and CODAP session 2. [B3]
- Final Python submission: present, a notebook. [B4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage file | Flag | Cohort as displayed on the page |
|---|---|---|---|---|---|---|---|---|
| B5 | Concepts | WS1 | Rubric score | 8 / 11 correct (72.7%) | 7 of 11 items correct | 6 of 11 | F3 | Average score 45% (4.92 / 11); average correct rate 81% |
| B6 | Concepts | WS3 | Rubric score | 7 / 8 correct (87.5%) | 5 of 8 items correct | 6 of 8 | F3 | Average score 88% (7.04 / 8); average correct rate 94% |
| B7 | Concepts | WS4 | Rubric score | 3 / 5 correct (60%) | 3 of 5 items correct | 3.5 of 5 | stage file differs | Average score 55% (2.77 / 5); average correct rate 54% |
| B8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 items correct | 4 of 4 | F2 | Average score 84% (3.35 / 4); average correct rate 58% |
| B9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 items correct | 8 of 8 | none | Average score 93% (7.46 / 8); average correct rate 89% |
| B10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 items correct | 4 of 7 | F1 | Average score 40% (2.8 / 7); average correct rate 40% |
| B11 | Documentation | WS6 | Rule-checked item | 3 / 5 scored correct (60%) | 24 answers | 3 of 4 | F4 | Average score 76% (3.04 / 4); average correct rate 63% |
| B12 | Documentation | WS12 | Consistency check | 3 / 4 correct (75%) | 3 of 6 items correct | 3.5 of 7 | F3 type | Average score 71% (5 / 7); average correct rate 72% |
| B13 | CODAP | WS13 | Rubric score | 16 / 24 correct (66.7%) | 16 of 31 items correct | 15.5 of 27 | F1 | Average score 41% (11.2 / 27); average correct rate 32% |
| B14 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 items correct | 13.5 of 33 | F1, F5 | Average score 47% (15.6 / 33); average correct rate 95% |
| B15 | CODAP | WS15 | Rubric items plus rule checks | 40 / 47 correct (85.1%) | 55 of 67 items correct | 29.5 of 47 | F1 | Average score 47% (22.3 / 47); average correct rate 69% |

WS6 is placed with documentation because the brief's grouping does not list it. [B16]

Item-level results the site shows for Bruno:

- WS1 (rubric score): items 4, 6, 8 and 10 were "✗ Not correct", with check flags such as "wrote_term_instead_of_count" (item 8). [B17]
- WS3 (rubric score): questions 2 and 6 show "No verdict". [B18]
- WS5 (rule-checked items): three trials were recorded (Doymuş Yağ, Protein, Tuz). The final choice was Protein with threshold 2,55. The validation value "final decision logical" reads true. [B19]
- WS7 (rule-checked items): items 5, 6 and 7 were blank and marked "✗ Not correct". [B20]
- WS6 (rule-checked items): the validation values list 5 tree-logic error flags (non-complementary operators at depth 0 and depth 1; count mismatches at depth 1 and depth 2). [B21]
- WS12 (consistency check): checks R1, R2, R5 "✓ Correct"; R4 "No verdict"; R6 and R7 "✗ Not correct". [B22]
- WS14 (rubric items plus rule checks): Questions 5 and 19 were blank. All 4 further checks were "✓ Correct". [B23]
- WS15 (rubric items plus rule checks): the 5 rule checks for Sample 2 test were "✗ Not correct". Questions 43 and 44 carry the flag TRAP_NOT_RECOGNIZED. The page states: "The model-written page summary also names Amy. It is not a verified attribution." [B24]

Profile header, as displayed: "CODAP worksheets: mean score 53.7% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 13 · Model submissions 10". This value is not used to rank (F6). [B25]

**CODAP screen recordings.**

| ID | Item | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| B26 | Length of the source recording | 1 h 23 min | 1 h 15 min |
| B27 | Frames listed | 238 | 246 |
| B28 | Frames with a behaviour label | 238 | 246 |
| B29 | Speech status | ok (classmate 1,090, teacher 451, student 288) | no_speech |
| B30 | Coding model | – | claude-sonnet-5 |
| B31 | Model self-rated confidence | 91 high, 147 medium | 46 high, 198 medium, 2 low |
| B32 | Frames with a second label (excluded from shares) | 151 | 165 |
| B33 | Label changes between segments | 33 | 107 |

| ID | Label | Session 1 frames | Session 1 share | Session 2 frames | Session 2 share |
|---|---|---|---|---|---|
| B34 | Explore data | 85 | 35.7% | 53 | 21.5% |
| B35 | Build tree | 3 | 1.3% | 20 | 8.1% |
| B36 | Tune threshold | 5 | 2.1% | 157 | 63.8% |
| B37 | Evaluate model | 125 | 52.5% | 11 | 4.5% |
| B38 | Compare models | 1 | 0.4% | not listed | not listed |
| B39 | Idle / thinking | 1 | 0.4% | 3 | 1.2% |
| B40 | Off task | 18 | 7.6% | 2 | 0.8% |

For session 1 the findings page prints: "Evaluate model is the most frequent primary label: 125 of 238 labelled frames (52.5%)." [B41]
It also prints: "In the first part, Evaluate model is 0 of 61 labelled frames (0%). In the last part, it is 73 of 86 (84.9%)." These are labelled-frame counts per third of the session clock, not minutes. [B42]
For session 2 it prints: "Tune threshold is the most frequent primary label: 157 of 246 labelled frames (63.8%)." No session-clock sentence is printed for session 2. [B43]
The participants comparison table shows the pooled leading label as "Tune threshold · 33.5%" (pooled across both sessions, F8). [B44]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| B45 | Model attempts | 8 | 2 |
| B46 | First attempt | 38 min after starting | 42 min after starting |
| B47 | Accuracy of last attempt | 81.8% (n = 44, Food_Dataset_Turkish_55) | 54.5% (n = 11, Food_Dataset_Turkish_55) |
| B48 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy) |
| B49 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Tag, Tuz (g) (salt), Yağ (g) (fat) |
| B50 | Threshold edit events (split editor used) | 8 | 5 |
| B51 | One kind of edit (VOTAT) | 14% of 7 steps between submissions | 0% of 1 steps between submissions |
| B52 | Predictor placements | 22 | 24 |
| B53 | Total actions | 541 | 264 |
| B54 | Session span | 82 min (UTC 08:09:13 to 09:31:34) | 62 min (UTC 08:09:18 to 09:11:38) |
| B55 | Accuracy spread (SD) | 0.056 | 0.103 |
| B56 | Submissions that scored no rows | "3 submissions scored no rows and are not plotted." | no such note is displayed |

In session 2 the first attempt scored n = 44 rows and the last attempt scored n = 11 rows. Last-attempt accuracy is not comparable across students or sessions. [B57]
VOTAT shares describe the order of logged actions between submissions, not a planned experiment. Split editor events do not show that a threshold value changed. [B58]

**Final Python submission.** Notebook trace. Files were not rerun.

| ID | Assignment requirement | Evidence status | Details |
|---|---|---|---|
| B59 | Load the dataset | Found | |
| B60 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| B61 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| B62 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| B63 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| B64 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| B65 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| B66 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

- Targets: YasamAlani (depths tried 1 to 5), Tur (1 to 10), Cinsiyet (1 to 10). [B67]
- Research questions written out: 3 of 3. [B68]
- Cells: 38 (25 code, 13 text). Code cells run: 0 of 25. Empty code cells: 1. Highest run counter: –. [B69]
- Errors in the outputs: None. Revisiting earlier code: Never. [B70]

Stored rubric points (pipeline points, rubric 1.0-draft, not a reviewed grade; scored by pipeline_hybrid). [B71]

| Section | Points | Possible |
|---|---|---|
| S1 | 7 | 10 |
| S2 | 5 | 5 |
| S3 | 5 | 5 |
| S4 | 15 | 30 |
| S5 | 12 | 21 |
| S6 | 15 | 20 |
| S7 | 6 | 9 |

A total is not displayed on the site. [B72]

**Across sources (descriptive juxtaposition only).**

In CODAP session 1, Evaluate model was 125 of 238 labelled frames (52.5%). In CODAP session 2, Tune threshold was 157 of 246 (63.8%). [B73] The logs recorded 8 split editor events in session 1 and 5 in session 2. [B74] The final notebook file recorded 0 of 25 code cells run, and a depth-search table was stored for 3 of 3 targets. [B75]

**Missing data and caveats.**

- No source gaps are listed for Bruno.
- F1: WS7, WS13, WS14, WS15 differ between page and profile. A third value appears in the stage file.
- F2: WS5 profile 3 of 3 vs page 13 / 13. These are different procedures.
- F3: WS1 (page 8 / 11, profile 7 of 11, stage 6 of 11) and WS3 (page 7 / 8, profile 5 of 8, stage 6 of 8). WS12 differs in the same way (page 3 / 4, profile 3 of 6, stage 3.5 of 7). WS4 differs only in the stage file (3.5 of 5).
- F4: WS6 profile shows "24 answers". Only the page value (3 / 5 scored correct) and the stage file (3 of 4) are scores.
- F5: WS14 cohort average score 47% vs average correct rate 95%.
- F6: header mean 53.7% reported as displayed, not used to rank.
- F8: per-session labels reported first; pooled "Tune threshold · 33.5%" is reported only as pooled.
- F11: cohort action totals not used. Per-session totals (541, 264) are from the student log tab, which excludes the Titanic log.
- F13: may apply to WS14; the six participants are not named.
- Session 1 frames: "Coding model" and "Prompt" are shown as "–" in Technical details.
- WS15: the page states the model-written summary also names Amy and is not a verified attribution.
- Notebook: code cells run 0 of 25, while saved outputs, tree drawings and depth-search tables are stored. Both are reported as displayed.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| B1–B4 | – | #/explore/student/Bruno, all four tabs | coverage |
| B5 | 8 / 11 (72.7%); 7 of 11; 6 of 11; 45% (4.92 / 11); 81% | WS1 page Student results, header, Class analysis; profile WS1 card and Technical details | rubric score |
| B6 | 7 / 8 (87.5%); 5 of 8; 6 of 8; 88% (7.04 / 8); 94% | WS3 page; profile WS3 | rubric score |
| B7 | 3 / 5 (60%); 3 of 5; 3.5 of 5; 55% (2.77 / 5); 54% | WS4 page; profile WS4 | rubric score |
| B8 | 13 / 13 (100%); 3 of 3; 4 of 4; 84% (3.35 / 4); 58% | WS5 page; profile WS5 | rule-checked item |
| B9 | 8 / 8 (100%); 8 of 8; 8 of 8; 93% (7.46 / 8); 89% | WS10 page; profile WS10 | rule-checked item |
| B10 | 4 / 4 (100%); 4 of 7; 4 of 7; 40% (2.8 / 7); 40% | WS7 page; profile WS7 | rule-checked item |
| B11 | 3 / 5 (60%); 24; 3 of 4; 76% (3.04 / 4); 63% | WS6 page; profile WS6 | rule-checked item |
| B12 | 3 / 4 (75%); 3 of 6; 3.5 of 7; 71% (5 / 7); 72% | WS12 page; profile WS12 | consistency check |
| B13 | 16 / 24 (66.7%); 16 of 31; 15.5 of 27; 41% (11.2 / 27); 32% | WS13 page; profile WS13 | rubric score |
| B14 | 31 / 31 (100%); 35 of 37; 13.5 of 33; 47% (15.6 / 33); 95% | WS14 page; profile WS14 | rubric items plus rule checks |
| B15 | 40 / 47 (85.1%); 55 of 67; 29.5 of 47; 47% (22.3 / 47); 69% | WS15 page; profile WS15 | rubric items plus rule checks |
| B16 | – | brief section 7 | none |
| B17 | items 4, 6, 8, 10 | profile WS1 item table, Check flags | rubric score |
| B18 | questions 2, 6 | profile WS3 item table | rubric score |
| B19 | 3 trials; 2,55 | profile WS5 item table, Other validation values | rule-checked item |
| B20 | items 5, 6, 7 | profile WS7 item table | rule-checked item |
| B21 | 5 flags; depth 0, 1, 2 | profile WS6 Other validation values | rule-checked item |
| B22 | R1, R2, R4, R5, R6, R7 | profile WS12 Further checks | consistency check |
| B23 | Q5, Q19; 4 checks | profile WS14 item table, Further checks | rubric items plus rule checks |
| B24 | 5 checks; Q43, Q44 | profile WS15 Further checks, Check flags, note | rubric items plus rule checks |
| B25 | 53.7%; 3; 13; 10 | profile header | stored-score mean; log count |
| B26–B30 | 1 h 23 min, 1 h 15 min; 238, 246; 1,090, 451, 288 | #/explore/student/Bruno/recordings, CODAP 1 and 2, Technical details | frame label |
| B31–B33 | 91, 147; 46, 198, 2; 151; 165; 33; 107 | #/findings/recordings?s=Bruno and &ss=codap_28apr, What stands out? and Limitations | model self-rating; frame label |
| B34–B40 | label frames and shares | recordings tab label tables; findings recordings Observed behaviour | frame label |
| B41 | 125 of 238 (52.5%) | #/findings/recordings?s=Bruno, What stands out? | frame label |
| B42 | 0 of 61 (0%); 73 of 86 (84.9%) | same, What stands out? and Across the session clock | frame label |
| B43 | 157 of 246 (63.8%) | #/findings/recordings?s=Bruno&ss=codap_28apr, What stands out? | frame label |
| B44 | 33.5% | #/findings/participants, Participant comparison | frame label (pooled) |
| B45–B56 | all values in the log table | #/explore/student/Bruno/logs, CODAP session 1 and 2, Technical event details | log count |
| B57 | n = 44; n = 11 | logs tab, CODAP session 2 Attempts table | log count |
| B59–B66 | 0.2; 3; 3 of 3; 3; 3; 3; 4 of 4 | #/explore/student/Bruno/notebook, requirement table | notebook trace |
| B67 | 1 to 5; 1 to 10; 1 to 10 | notebook, Trees built | notebook trace |
| B68 | 3 of 3 | notebook, Technical details | notebook trace |
| B69 | 38, 25, 13; 0 of 25; 1; – | notebook, Technical details | notebook trace |
| B70 | None; Never | notebook | notebook trace |
| B71 | 7/10, 5/5, 5/5, 15/30, 12/21, 15/20, 6/9; 1.0-draft | notebook, Stored rubric points | stored rubric points |
| B72 | – | notebook | stored rubric points |
| B73 | 125 of 238 (52.5%); 157 of 246 (63.8%) | #/findings/recordings?s=Bruno | frame label |
| B74 | 8; 5 | logs tab; #/findings/participants, threshold edit table | log count |
| B75 | 0 of 25; 3 of 3 | notebook tab | notebook trace |

Checklist: all ten items answered yes.

---

## Site vs brief: differences found (site wins)

1. **F6 is not as described.** The participants page states the method ("the mean of each participant's stored score divided by that worksheet's maximum, for WS13, WS14, and WS15"). The three inputs are the stage file totals in each profile's Technical details (Amy 9.5/27, 18.5/33, 24/47; Bruno 15.5/27, 13.5/33, 29.5/47), not the "items correct" lines. The profiles above report the stated method and do not recompute.
2. **A third display exists for every scored worksheet.** The stage file total in Technical details often differs from both the page and the profile (for example Amy WS12 7 of 7; Bruno WS4 3.5 of 5).
3. **F1 example for Amy WS14:** the brief does not list it. Page 33 / 33, profile 37 of 37, stage file 18.5 of 33.
4. **WS6 has no group** in the brief's section 7 list. It is placed under documentation here.
5. **Bruno CODAP session 1 frames:** Coding model and Prompt show "–".
6. **Bruno notebook:** 0 of 25 code cells run, with stored drawings and tables.

---

Conventions for the profiles below (same as Amy and Bruno). Worksheet columns: **Page** = worksheet findings page, Student results (answer-key check). **Profile** = student profile, Worksheets tab item line. **Stage** = STAGE SCORE FILE total in the profile's Technical details. **Cohort** = worksheet page "Average score" (with mean / maximum) ; "Average correct rate" (Class analysis). Frame shares use labelled frames as the denominator. Log values exclude the Titanic log. Last-attempt accuracy is not comparable across students or sessions. VOTAT shares describe the order of logged actions, not a planned experiment. Split editor events (change_split_values) do not show that a threshold value changed. Notebook files were not rerun. Stored rubric points are pipeline points, rubric 1.0-draft, scored by pipeline_hybrid, not a reviewed grade; no total is displayed for any participant.

---

### Helena

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. [HE1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [HE2]
- Logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [HE3]
- Final Python submission: present, a notebook. [HE4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| HE5 | Concepts | WS1 | Rubric score | 11 / 11 correct (100%) | 10 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| HE6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| HE7 | Concepts | WS4 | Rubric score | 2 / 5 correct (40%) | 2 of 5 | 2 of 5 | none | 55% (2.77 / 5); 54% |
| HE8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| HE9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| HE10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| HE11 | Documentation | WS6 | Rule-checked item | 4 / 5 scored correct (80%) | 24 answers | 3.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| HE12 | Documentation | WS12 | Consistency check | 6 / 6 correct (100%) | 6 of 6 | 7 of 7 | stage differs | 71% (5 / 7); 72% |
| HE13 | CODAP | WS13 | Rubric score | 11 / 17 correct (64.7%) | 11 of 31 | 9.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| HE14 | CODAP | WS14 | Rubric items plus rule checks | 33 / 33 correct (100%) | 37 of 37 | 22 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| HE15 | CODAP | WS15 | Rubric items plus rule checks | 40 / 47 correct (85.1%) | 55 of 67 | 28 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Helena:
- WS4 (rubric score): check flags "threshold_not_placed" (Blank 1), "missing_equal_fat_explanation" (Blank 4) and "energy_threshold_out_of_range" (Blank 5). [HE16]
- WS12 (consistency check): all 6 further checks "✓ Correct". WS14: all 4 further checks "✓ Correct". [HE17]
- WS13 (rubric score): 23 items carry the flag "review". [HE18]
- WS15 (rubric items plus rule checks): the 5 rule checks for Sample 1 test were "✗ Not correct". Questions 43 and 44 carry TRAP_NOT_RECOGNIZED. [HE19]

Profile header: "CODAP worksheets: mean score 53.8% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 20 · Model submissions 22". Not used to rank (F6). [HE20]

**CODAP screen recordings.**

CODAP session 1: length 1 h 28 min; frames listed 302; frames labelled 302; speech "ok" (classmate 1,232, teacher 388, student 203); coding model "–". [HE21]

| ID | Label | Frames | Share |
|---|---|---|---|
| HE22 | Explore data | 133 | 44% |
| HE23 | Build tree | 5 | 1.7% |
| HE24 | Tune threshold | 17 | 5.6% |
| HE25 | Evaluate model | 10 | 3.3% |
| HE26 | Compare models | 77 | 25.5% |
| HE27 | Idle / thinking | 3 | 1% |
| HE28 | Off task | 57 | 18.9% |

The findings page prints: "No primary label reaches half of the labelled frames. The largest share is Explore data, 133 of 302 (44%). Compare models is next, 77 of 302 (25.5%)." [HE29] It also prints: "In the first part, Compare models is 0 of 137 labelled frames (0%). In the last part, it is 54 of 76 (71.1%)." These are labelled frames per third of the clock, not minutes. [HE30] The label changed 51 times between segments. Model self-rated confidence: 196 high, 105 medium, 1 low. 121 frames have a second label. [HE31]

CODAP session 2: "No screen recording frames are on record for Helena, CODAP session 2". [HE32]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 |
|---|---|---|
| HE33 | Model attempts | 22 |
| HE34 | First attempt | 46 min after starting |
| HE35 | Accuracy of last attempt | 71.4% (n = 42, Food_Dataset_Turkish_55 (5)) |
| HE36 | Target | Column 1 (recommendation label, unnamed copy) |
| HE37 | Predictors tried | Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| HE38 | Threshold edit events (split editor used) | 20 |
| HE39 | One kind of edit (VOTAT) | 76% of 21 steps between submissions |
| HE40 | Predictor placements | 13 |
| HE41 | Total actions | 516 |
| HE42 | Session span | 84 min (UTC 08:10:58 to 09:34:58) |
| HE43 | Accuracy spread (SD) | 0.09 |
| HE44 | Submissions that scored no rows | no such note is displayed |

CODAP session 2: "No class-session log is stored." [HE45]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| HE46 | Load the dataset | Found | |
| HE47 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| HE48 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| HE49 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| HE50 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| HE51 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| HE52 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| HE53 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths tried 1 to 10 for each). Research questions written out: 0 of 3. Cells: 47 (33 code, 14 text). Code cells run: 0 of 33. Empty code cells: 1. Highest run counter: –. Errors in the outputs: None. Revisiting earlier code: Never. [HE54]

Stored rubric points: S1 8/10, S2 0/5, S3 5/5, S4 12/30, S5 10/21, S6 18/20, S7 5/9. [HE55]

**Across sources.** The WS13 answer-key check on the page was 11 / 17 correct (64.7%), and the stage file total was 9.5 of 27. [HE56] In CODAP session 1, Explore data was 133 of 302 labelled frames (44%). [HE57] The session 1 log recorded 20 split editor events, and the final notebook recorded 0 of 33 code cells run. [HE58]

**Missing data and caveats.** No frames and no log for CODAP session 2 (missing evidence). F1 (WS7, WS13, WS14, WS15). F2 (WS5). F3 (WS1 page 11 / 11 vs profile 10 of 11 vs stage 5 of 11; WS3). F4 (WS6 "24 answers"). F5. F6. WS12 stage file 7 of 7 vs page 6 / 6. F11 (only per-session totals used). F13 (unnamed six). Session 1 coding model shown as "–". Notebook: 0 of 33 code cells run while outputs are stored.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| HE1–HE4 | – | #/explore/student/Helena, Evidence notes and four tabs | coverage |
| HE5–HE15 | all Page, Profile, Stage, Cohort cells | #/findings/worksheets/WSn (Student results, header, Class analysis); profile Worksheets tab (card line, Technical details) | per row |
| HE16 | Blanks 1, 4, 5 | profile WS4 Check flags | rubric score |
| HE17 | 6; 4 | profile WS12 and WS14 Further checks | consistency check; rule check |
| HE18 | 23 | profile WS13 Check flags | rubric score |
| HE19 | 5; Q43, Q44 | profile WS15 Further checks, Check flags | rubric items plus rule checks |
| HE20 | 53.8%; 3; 20; 22 | profile header | stored-score mean; log count |
| HE21–HE28 | 1 h 28 min; 302; 302; 1,232, 388, 203; label frames and shares | #/explore/student/Helena/recordings, CODAP 1 | frame label |
| HE29–HE31 | 133 of 302 (44%); 77 of 302 (25.5%); 0 of 137 (0%); 54 of 76 (71.1%); 51; 196, 105, 1; 121 | #/findings/recordings?s=Helena, What stands out?, Limitations | frame label; model self-rating |
| HE32 | session 2 | #/findings/recordings?s=Helena&ss=codap_28apr | coverage |
| HE33–HE45 | all values in the log table | #/explore/student/Helena/logs, CODAP session 1 | log count |
| HE46–HE55 | all requirement, cell and point values | #/explore/student/Helena/notebook | notebook trace; stored rubric points |
| HE56 | 11 / 17 (64.7%); 9.5 of 27 | WS13 page; profile WS13 Technical details | rubric score |
| HE57 | 133 of 302 (44%) | #/findings/recordings?s=Helena | frame label |
| HE58 | 20; 0 of 33 | logs tab; notebook tab | log count; notebook trace |

Checklist: all ten items answered yes.

---

### Iris

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. [IR1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [IR2]
- Logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [IR3]
- Final Python submission: present, a notebook. [IR4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| IR5 | Concepts | WS1 | Rubric score | 9 / 11 correct (81.8%) | 8 of 11 | 4.5 of 11 | F3 | 45% (4.92 / 11); 81% |
| IR6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| IR7 | Concepts | WS4 | Rubric score | 3 / 5 correct (60%) | 3 of 5 | 2.5 of 5 | stage differs | 55% (2.77 / 5); 54% |
| IR8 | Thresholds | WS5 | Rule-checked item | 10 / 13 correct (76.9%) | 0 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| IR9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| IR10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| IR11 | Documentation | WS6 | Rule-checked item | 8 / 8 scored correct (100%) | 31 answers | 4 of 4 | F4 | 76% (3.04 / 4); 63% |
| IR12 | Documentation | WS12 | Consistency check | 4 / 6 correct (66.7%) | 4 of 6 | 4.5 of 7 | stage differs | 71% (5 / 7); 72% |
| IR13 | CODAP | WS13 | Rubric score | 10 / 21 correct (47.6%) | 10 of 31 | 11 of 27 | F1 | 41% (11.2 / 27); 32% |
| IR14 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 | 13.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| IR15 | CODAP | WS15 | Rubric items plus rule checks | 34 / 44 correct (77.3%) | 46 of 67 | 21.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Iris:
- WS5 (rule-checked items): trials 1, 2 and 3 each carry the flag "non_complementary_operators". [IR16]
- WS12 (consistency check): further checks R4 and R5 were not marked correct (4 of 6 "✓ Correct"). [IR17]
- WS14: Questions 32 and 33 were blank; all 4 further checks "✓ Correct". [IR18]
- WS15: 12 of 20 rule checks "✓ Correct" (Sample 1 test, five checks, and Sample 2 test accuracy, sensitivity and specificity were not). Questions 45, 46 and 47 were blank. [IR19]

Profile header: "CODAP worksheets: mean score 42.5% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 77 · Model submissions 13". Not used to rank (F6). [IR20]

**CODAP screen recordings.**

CODAP session 1: length 1 h 23 min; frames listed 164; frames labelled 164; speech "no_speech"; coding model claude-sonnet-5. [IR21]

| ID | Label | Frames | Share |
|---|---|---|---|
| IR22 | Explore data | 80 | 48.8% |
| IR23 | Build tree | 12 | 7.3% |
| IR24 | Tune threshold | 4 | 2.4% |
| IR25 | Evaluate model | 9 | 5.5% |
| IR26 | Compare models | 53 | 32.3% |
| IR27 | Off task | 6 | 3.7% |

The findings page prints: "No primary label reaches half of the labelled frames. The largest share is Explore data, 80 of 164 (48.8%). Compare models is next, 53 of 164 (32.3%)." [IR28] And: "In the first part, Explore data is 46 of 52 labelled frames (88.5%). In the last part, it is 1 of 64 (1.6%)." [IR29] 26 label changes. Model self-rated confidence: 78 high, 85 medium, 1 low. 90 frames have a second label. [IR30]

CODAP session 2: "No screen recording frames are on record for Iris, CODAP session 2". [IR31]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 |
|---|---|---|
| IR32 | Model attempts | 13 |
| IR33 | First attempt | 50 min after starting |
| IR34 | Accuracy of last attempt | 59.1% (n = 44, Food_Dataset_Turkish_55 (1)) |
| IR35 | Target | Column 1 (recommendation label, unnamed copy) |
| IR36 | Predictors tried | Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| IR37 | Threshold edit events (split editor used) | 77 |
| IR38 | One kind of edit (VOTAT) | 83% of 12 steps between submissions |
| IR39 | Predictor placements | 17 |
| IR40 | Total actions | 292 |
| IR41 | Session span | 82 min (UTC 08:09:33 to 09:31:37) |
| IR42 | Accuracy spread (SD) | 0.088 |
| IR43 | Submissions that scored no rows | no such note is displayed |

CODAP session 2: "No class-session log is stored." [IR44]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| IR45 | Load the dataset | Found | |
| IR46 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| IR47 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| IR48 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| IR49 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| IR50 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| IR51 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| IR52 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Tur, Cinsiyet (features "get_dummies applied to all columns except" the target; depths 1 to 10 for each). Research questions written out: 0 of 3. Cells: 14 (7 code, 7 text). Code cells run: 0 of 7. Empty code cells: 0. Highest run counter: –. Errors: None. Revisiting earlier code: Never. [IR53]

Stored rubric points: S1 7/10, S2 0/5, S3 3/5, S4 24/30, S5 12/21, S6 17/20, S7 5/9. [IR54]

**Across sources.** The WS5 rule check on the page was 10 / 13 correct (76.9%), while the profile line reads 0 of 3. [IR55] In CODAP session 1, Explore data was 80 of 164 labelled frames (48.8%). [IR56] The session 1 log recorded 77 split editor events and a VOTAT share of 83% of 12 steps. [IR57]

**Missing data and caveats.** No frames and no log for CODAP session 2. F1, F2 (WS5 0 of 3 vs 10 / 13; different procedures), F3 (WS1, WS3), F4, F5, F6, F11, F13. WS4 and WS12 stage files differ from the page. Notebook: 0 of 7 code cells run while outputs are stored.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| IR1–IR4 | – | #/explore/student/Iris, Evidence notes and tabs | coverage |
| IR5–IR15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| IR16 | trials 1, 2, 3 | profile WS5 Check flags | rule-checked item |
| IR17 | R4, R5; 4 of 6 | profile WS12 Further checks | consistency check |
| IR18 | Q32, Q33; 4 | profile WS14 | rubric items plus rule checks |
| IR19 | 12 of 20; Q45–47 | profile WS15 Further checks, Check flags | rubric items plus rule checks |
| IR20 | 42.5%; 3; 77; 13 | profile header | stored-score mean; log count |
| IR21–IR27 | 1 h 23 min; 164; 164; label frames and shares | recordings tab, CODAP 1 | frame label |
| IR28–IR30 | 80 of 164 (48.8%); 53 of 164 (32.3%); 46 of 52 (88.5%); 1 of 64 (1.6%); 26; 78, 85, 1; 90 | #/findings/recordings?s=Iris | frame label; model self-rating |
| IR31 | session 2 | findings recordings, session 2 | coverage |
| IR32–IR44 | all log values | logs tab, CODAP session 1 | log count |
| IR45–IR54 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| IR55 | 10 / 13 (76.9%); 0 of 3 | WS5 page; profile WS5 | rule-checked item |
| IR56 | 80 of 164 (48.8%) | findings recordings | frame label |
| IR57 | 77; 83% of 12 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Irma

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. The profile shows no Evidence notes block. [IM1]
- Frames: partial. CODAP session 1 lists 335 frames with no behaviour label ("335 frames are listed. None has a behaviour label."). CODAP session 2 lists 343 frames, 342 labelled. [IM2]
- Logs: present for CODAP session 1 and CODAP session 2. [IM3]
- Final Python submission: present, a notebook. [IM4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| IM5 | Concepts | WS1 | Rubric score | 10 / 11 correct (90.9%) | 9 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| IM6 | Concepts | WS3 | Rubric score | 5 / 8 correct (62.5%) | 5 of 8 | 5 of 8 | none | 88% (7.04 / 8); 94% |
| IM7 | Concepts | WS4 | Rubric score | 2 / 5 correct (40%) | 2 of 5 | 2.5 of 5 | stage differs | 55% (2.77 / 5); 54% |
| IM8 | Thresholds | WS5 | Rule-checked item | 8 / 13 correct (61.5%) | 0 of 3 | 2.5 of 4 | F2 | 84% (3.35 / 4); 58% |
| IM9 | Thresholds | WS10 | Rule-checked item | 7 / 8 correct (87.5%) | 7 of 8 | 7 of 8 | none | 93% (7.46 / 8); 89% |
| IM10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| IM11 | Documentation | WS6 | Rule-checked item | 4 / 4 scored correct (100%) | 36 answers | 3.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| IM12 | Documentation | WS12 | Consistency check | 3 / 4 correct (75%) | 3 of 6 | 3.5 of 7 | F3 type | 71% (5 / 7); 72% |
| IM13 | CODAP | WS13 | Rubric score | 10 / 25 correct (40%) | 10 of 31 | 13 of 27 | F1 | 41% (11.2 / 27); 32% |
| IM14 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 | 12.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| IM15 | CODAP | WS15 | Rubric items plus rule checks | 35 / 43 correct (81.4%) | 49 of 67 | 24 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Irma:
- WS5: trial flags include "non_complementary_operators", "leaf_count_mismatch" and "arithmetic_inconsistent". [IM16]
- WS10: Blank 8 carries the flag "optimal_threshold_mismatch". [IM17]
- WS6: 2 error flags (depth 1 right child incomplete; depth 2 left-right leaf count mismatch). [IM18]
- WS14: Questions 5 and 19 were blank; all 4 further checks "✓ Correct". [IM19]
- WS15: 14 of 20 rule checks "✓ Correct" (Sample 1 test sensitivity and the five Sample 2 test checks were not). Questions 1 to 4 were blank. [IM20]

Profile header: "CODAP worksheets: mean score 45.7% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 27 · Model submissions 33". Not used to rank (F6). [IM21]

**CODAP screen recordings.**

CODAP session 1: length 1 h 23 min; frames listed 335; frames with a behaviour label "No"; speech "no_speech". The findings page states: "They do not have behaviour labels, so they are not included in behaviour shares. Labels from another session are not copied onto them." No label values are reported for this session (F10). [IM22]

CODAP session 2: length 1 h 14 min; frames listed 343; frames labelled 342; speech "no_speech"; coding model claude-sonnet-5. [IM23]

| ID | Label | Frames | Share |
|---|---|---|---|
| IM24 | Explore data | 73 | 21.3% |
| IM25 | Build tree | 46 | 13.5% |
| IM26 | Tune threshold | 199 | 58.2% |
| IM27 | Evaluate model | 8 | 2.3% |
| IM28 | Compare models | 8 | 2.3% |
| IM29 | Idle / thinking | 3 | 0.9% |
| IM30 | Off task | 5 | 1.5% |

The findings page prints: "Tune threshold is the most frequent primary label: 199 of 342 labelled frames (58.2%). Explore data is the next largest share, 73 of 342 (21.3%)." No session-clock sentence is printed. [IM31] 127 label changes. 1 listed frame has no primary label. Model self-rated confidence: 73 high, 266 medium, 3 low. 192 frames have a second label. [IM32] The comparison table shows "Tune threshold · 58.2%" (pooled; only session 2 is labelled). [IM33]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| IM34 | Model attempts | 18 | 15 |
| IM35 | First attempt | 47 min after starting | 9 min after starting |
| IM36 | Accuracy of last attempt | 51% (n = 49, Food_Dataset_Turkish_55) | 65.9% (n = 44, Food_Dataset_Turkish_55Tavsiye) |
| IM37 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy), Oneri (recommendation label), Tag |
| IM38 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| IM39 | Threshold edit events (split editor used) | 17 | 10 |
| IM40 | One kind of edit (VOTAT) | 82% of 17 steps between submissions | 29% of 14 steps between submissions |
| IM41 | Predictor placements | 11 | 26 |
| IM42 | Total actions | 450 | 502 |
| IM43 | Session span | 83 min (UTC 08:09:31 to 09:32:54) | 74 min (UTC 08:09:10 to 09:22:46) |
| IM44 | Accuracy spread (SD) | 0.082 | 0.16 |
| IM45 | Submissions that scored no rows | "1 submission scored no rows and is not plotted." | no such note is displayed |

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| IM46 | Load the dataset | Found | |
| IM47 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| IM48 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| IM49 | Fit a decision tree | Found | 1 target with a stored tree record. |
| IM50 | Explore tree depth | Found | Depth-search table stored for 1 of 1. |
| IM51 | Evaluate performance | Found | A test error is stored for 1 target. Training and test curves are stored for 1 |
| IM52 | Visualise the tree | Found | A tree drawing is stored for 1 target. |
| IM53 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Target variables listed: Cinsiyet, Tur, YasamAlani; trees built: YasamAlani (depths 1 to 5). Stored model count: 4. Research questions written out: 0 of 3. Cells: 35 (16 code, 19 text). Code cells run: 16 of 16. Empty code cells: 0. Highest run counter: 40. Errors: None. Revisiting earlier code: 1 time. [IM54]

Stored rubric points: S1 9/10, S2 0/5, S3 5/5, S4 8/30, S5 6/21, S6 18/20, S7 5/9. [IM55]

**Across sources.** The WS13 answer-key check on the page was 10 / 25 correct (40%), and the stage file total was 13 of 27. [IM56] In CODAP session 2, Tune threshold was 199 of 342 labelled frames (58.2%). [IM57] The logs recorded 17 split editor events in session 1 and 10 in session 2. [IM58]

**Missing data and caveats.** CODAP session 1 frames are unlabelled (missing label evidence, not absent activity). F10: the session 1 and session 2 episode lists are identical; episodes are not used. F1, F2, F3 (WS1; WS12), F4, F5, F6, F8 (pooled label equals the one labelled session), F11, F13. Session 2 target field lists three variables, as displayed.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| IM1–IM4 | 335; 343; 342 | profile tabs; #/docs/limitations, Manifest notes | coverage |
| IM5–IM15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| IM16–IM20 | flags; Blank 8; 2 flags; Q5, Q19, 4; 14 of 20, Q1–4 | profile WS5, WS10, WS6, WS14, WS15 Technical details | rule-checked item; rubric items plus rule checks |
| IM21 | 45.7%; 3; 27; 33 | profile header | stored-score mean; log count |
| IM22 | 1 h 23 min; 335 | recordings tab CODAP 1; #/findings/recordings?s=Irma | coverage |
| IM23–IM30 | 1 h 14 min; 343; 342; label frames and shares | recordings tab CODAP 2 | frame label |
| IM31–IM32 | 199 of 342 (58.2%); 73 of 342 (21.3%); 127; 1; 73, 266, 3; 192 | #/findings/recordings?s=Irma&ss=codap_28apr | frame label; model self-rating |
| IM33 | 58.2% | #/findings/participants, comparison table | frame label (pooled) |
| IM34–IM45 | all log values | logs tab, sessions 1 and 2 | log count |
| IM46–IM55 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| IM56 | 10 / 25 (40%); 13 of 27 | WS13 page; profile WS13 | rubric score |
| IM57 | 199 of 342 (58.2%) | findings recordings | frame label |
| IM58 | 17; 10 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Isabel

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. No Evidence notes block. [IS1]
- Frames: present for CODAP session 1 and CODAP session 2. [IS2]
- Logs: present for CODAP session 1 and CODAP session 2. [IS3]
- Final Python submission: present, a notebook. [IS4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| IS5 | Concepts | WS1 | Rubric score | 9 / 11 correct (81.8%) | 8 of 11 | 4 of 11 | F3 | 45% (4.92 / 11); 81% |
| IS6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| IS7 | Concepts | WS4 | Rubric score | 5 / 5 correct (100%) | 5 of 5 | 3.5 of 5 | stage differs | 55% (2.77 / 5); 54% |
| IS8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| IS9 | Thresholds | WS10 | Rule-checked item | 3 / 7 correct (42.9%) | 3 of 8 | 7 of 8 | F3 type | 93% (7.46 / 8); 89% |
| IS10 | Rules | WS7 | Rule-checked item | 2 / 4 correct (50%) | 2 of 7 | 2 of 7 | F1 | 40% (2.8 / 7); 40% |
| IS11 | Documentation | WS6 | Rule-checked item | 4 / 5 scored correct (80%) | 31 answers | 3.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| IS12 | Documentation | WS12 | Consistency check | 2 / 3 correct (66.7%) | 2 of 6 | 2.5 of 7 | F3 type | 71% (5 / 7); 72% |
| IS13 | CODAP | WS13 | Rubric score | 13 / 25 correct (52%) | 13 of 31 | 15 of 27 | F1 | 41% (11.2 / 27); 32% |
| IS14 | CODAP | WS14 | Rubric items plus rule checks | 33 / 33 correct (100%) | 37 of 37 | 18 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| IS15 | CODAP | WS15 | Rubric items plus rule checks | 40 / 47 correct (85.1%) | 55 of 67 | 30 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Isabel:
- WS10 (rule-checked items): flags "missing_count" (Blank 4), "count_mismatch" (Blanks 5, 6, 7) and "missing_optimal_threshold" (Blank 8). The stage file reads 7 of 8 while the page reads 3 / 7 and the profile 3 of 8. All three are reported. [IS16]
- WS6: 2 error flags (depth 1 left child incomplete; depth 0 threshold_mismatch, left=191.5, right=194.5). [IS17]
- WS14: all 4 further checks "✓ Correct". [IS18]
- WS15: the 5 rule checks for Sample 1 test were "✗ Not correct". Questions 43 and 44 carry TRAP_NOT_RECOGNIZED. [IS19]

Profile header: "CODAP worksheets: mean score 58.0% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 34 · Model submissions 19". Not used to rank (F6). [IS20]

**CODAP screen recordings.**

| ID | Item | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| IS21 | Length of the source recording | 1 h 27 min | 1 h 16 min |
| IS22 | Frames listed / labelled | 259 / 259 | 195 / 195 |
| IS23 | Speech status | no_speech | no_speech |
| IS24 | Coding model | – | claude-sonnet-5 |
| IS25 | Model self-rated confidence | 164 high, 93 medium, 2 low | 53 high, 142 medium |
| IS26 | Second labels (excluded) | 132 | 131 |
| IS27 | Label changes | 68 | 61 |

| ID | Label | S1 frames | S1 share | S2 frames | S2 share |
|---|---|---|---|---|---|
| IS28 | Explore data | 79 | 30.5% | 41 | 21% |
| IS29 | Build tree | 6 | 2.3% | 10 | 5.1% |
| IS30 | Tune threshold | 15 | 5.8% | 136 | 69.7% |
| IS31 | Evaluate model | 35 | 13.5% | 1 | 0.5% |
| IS32 | Compare models | 79 | 30.5% | 4 | 2.1% |
| IS33 | Idle / thinking | 1 | 0.4% | 2 | 1% |
| IS34 | Off task | 44 | 17% | 1 | 0.5% |

Session 1, as printed: "The two largest shares are close. Compare models is 79 of 259 labelled frames (30.5%), and Explore data is 79 of 259 (30.5%)." And: "In the first part, Compare models is 0 of 84 labelled frames (0%). In the last part, it is 71 of 113 (62.8%)." [IS35]
Session 2, as printed: "Tune threshold is the most frequent primary label: 136 of 195 labelled frames (69.7%). Explore data is the next largest share, 41 of 195 (21%)." No session-clock sentence is printed. [IS36]
Pooled leading label in the comparison table: "Tune threshold · 33.3%" (pooled, F8). [IS37]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| IS38 | Model attempts | 12 | 7 |
| IS39 | First attempt | 46 min after starting | 28 min after starting |
| IS40 | Accuracy of last attempt | 75% (n = 40, Food_Dataset_Turkish_55) | 0% (n = 8, Food_Dataset_Turkish_55 (1)) small sample * |
| IS41 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy) |
| IS42 | Predictors tried | Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat) |
| IS43 | Threshold edit events (split editor used) | 22 | 12 |
| IS44 | One kind of edit (VOTAT) | 55% of 11 steps between submissions | 33% of 6 steps between submissions |
| IS45 | Predictor placements | 9 | 13 |
| IS46 | Total actions | 481 | 405 |
| IS47 | Session span | 84 min (UTC 08:09:44 to 09:33:16) | 72 min (UTC 08:09:11 to 09:21:06) |
| IS48 | Accuracy spread (SD) | 0.065 | 0.266 |
| IS49 | Submissions that scored no rows | no such note is displayed | no such note is displayed |

The site marks the session 2 value with the words "small sample". The * is added per the brief because n < 10. [IS50]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| IS51 | Load the dataset | Found | |
| IS52 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| IS53 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| IS54 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| IS55 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| IS56 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| IS57 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| IS58 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). Research questions written out: 0 of 3. Cells: 41 (32 code, 9 text). Code cells run: 32 of 32. Empty code cells: 0. Highest run counter: 99. Errors: None. Revisiting earlier code: Never. [IS59]

Stored rubric points: S1 7/10, S2 0/5, S3 4/5, S4 15/30, S5 10/21, S6 15/20, S7 5/9. [IS60]

**Across sources.** The WS13 answer-key check on the page was 13 / 25 correct (52%), and the stage file total was 15 of 27. [IS61] In CODAP session 2, Tune threshold was 136 of 195 labelled frames (69.7%). [IS62] The session 2 log recorded 12 split editor events. [IS63]

**Missing data and caveats.** No source gaps listed. Session 2 last-attempt accuracy has n = 8 (small sample, *). F1, F2, F3 (WS1, WS3; WS10 and WS12 display differences), F4, F5, F6, F8, F11, F13. Session 1 coding model shown as "–".

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| IS1–IS4 | – | profile tabs | coverage |
| IS5–IS15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| IS16–IS19 | Blanks 4–8; 3 / 7, 3 of 8, 7 of 8; 191.5, 194.5; 4; 5, Q43, Q44 | profile WS10, WS6, WS14, WS15 Technical details | rule-checked item; rubric items plus rule checks |
| IS20 | 58.0%; 3; 34; 19 | profile header | stored-score mean; log count |
| IS21–IS34 | all session values | recordings tab; #/findings/recordings?s=Isabel (both sessions), Limitations | frame label; model self-rating |
| IS35–IS36 | 79 of 259 (30.5%) x2; 0 of 84 (0%); 71 of 113 (62.8%); 136 of 195 (69.7%); 41 of 195 (21%) | findings recordings, What stands out? | frame label |
| IS37 | 33.3% | #/findings/participants | frame label (pooled) |
| IS38–IS50 | all log values; n = 8 | logs tab, sessions 1 and 2 | log count |
| IS51–IS60 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| IS61 | 13 / 25 (52%); 15 of 27 | WS13 page; profile WS13 | rubric score |
| IS62 | 136 of 195 (69.7%) | findings recordings | frame label |
| IS63 | 12 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Marco

**Evidence available.**
- Worksheets: partial. Evidence notes read "No worksheet extraction for WS1, WS3, WS4, WS5." Marco is not listed on those worksheet pages. [MO1]
- Frames: present for CODAP session 1 and CODAP session 2. [MO2]
- Logs: present for CODAP session 1 and CODAP session 2. [MO3]
- Final submission: present, a written report. Evidence notes read "Written report. Notebook cell counts are not applicable." [MO4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| MO5 | Concepts | WS1, WS3, WS4 | Rubric score | not listed | no answers on file | none | gap | 13 of 15 participants included |
| MO6 | Thresholds | WS5 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| MO7 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| MO8 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| MO9 | Documentation | WS6 | Rule-checked item | 1 / 2 scored correct (50%) | 17 answers | 1.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| MO10 | Documentation | WS12 | Consistency check | 4 / 5 correct (80%) | 4 of 6 | 4.5 of 7 | F3 type | 71% (5 / 7); 72% |
| MO11 | CODAP | WS13 | Rubric score | 6 / 19 correct (31.6%) | 6 of 31 | 8 of 27 | F1 | 41% (11.2 / 27); 32% |
| MO12 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 | 14.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| MO13 | CODAP | WS15 | Rubric items plus rule checks | 7 / 12 correct (58.3%) | 7 of 67 | 0.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Marco:
- WS6: 1 error flag (depth 0 non_complementary_operators). [MO14]
- WS13: 28 items carry the flag "review". [MO15]
- WS14: Questions 5 and 19 were blank; all 4 further checks "✓ Correct". The page states: "The model-written page summary also names Melinda. It is not a verified attribution." [MO16]
- WS15: 0 of 20 rule checks "✓ Correct". 35 questions carry the flag BLANK. [MO17]

Profile header: "CODAP worksheets: mean score 24.9% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 9 · Model submissions 25 · Written report". Not used to rank (F6). [MO18]

**CODAP screen recordings.**

| ID | Item | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| MO19 | Length of the source recording | 1 h 13 min | 1 h 19 min |
| MO20 | Frames listed / labelled | 142 / 142 | 172 / 172 |
| MO21 | Speech status | no_speech | no_speech |
| MO22 | Coding model | claude-sonnet-5 | – |
| MO23 | Model self-rated confidence | 36 high, 106 medium | 64 high, 107 medium, 1 low |
| MO24 | Second labels (excluded) | 70 | 54 |
| MO25 | Label changes | 26 | 63 |

| ID | Label | S1 frames | S1 share | S2 frames | S2 share |
|---|---|---|---|---|---|
| MO26 | Explore data | 72 | 50.7% | 62 | 36% |
| MO27 | Build tree | 3 | 2.1% | 6 | 3.5% |
| MO28 | Tune threshold | 3 | 2.1% | 11 | 6.4% |
| MO29 | Evaluate model | 30 | 21.1% | 2 | 1.2% |
| MO30 | Compare models | 33 | 23.2% | 43 | 25% |
| MO31 | Idle / thinking | not listed | not listed | 2 | 1.2% |
| MO32 | Off task | 1 | 0.7% | 46 | 26.7% |

Session 1, as printed: "Explore data is the most frequent primary label: 72 of 142 labelled frames (50.7%)." And: "In the first part, Explore data is 55 of 56 labelled frames (98.2%). In the last part, it is 1 of 50 (2%)." [MO33]
Session 2, as printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 62 of 172 (36%). Off task is next, 46 of 172 (26.7%)." And: "In the first part, Explore data is 56 of 104 labelled frames (53.8%). In the last part, it is 4 of 43 (9.3%)." [MO34]
Pooled leading label in the comparison table: "Explore data · 42.7%" (pooled, F8). [MO35]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| MO36 | Model attempts | 14 | 11 |
| MO37 | First attempt | 44 min after starting | 17 min after starting |
| MO38 | Accuracy of last attempt | 65.9% (n = 44, Food_Dataset_Turkish_55 (1)) | 30% (n = 10, Food_Dataset_Turkish_55Tavsiye) |
| MO39 | Target | Column 1 (recommendation label, unnamed copy) | Oneri (recommendation label) |
| MO40 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | same seven as session 1 |
| MO41 | Threshold edit events (split editor used) | 6 | 3 |
| MO42 | One kind of edit (VOTAT) | 77% of 13 steps between submissions | 90% of 10 steps between submissions |
| MO43 | Predictor placements | 15 | 13 |
| MO44 | Total actions | 535 | 293 |
| MO45 | Session span | 84 min (UTC 08:12:04 to 09:36:21) | 76 min (UTC 08:08:59 to 09:24:49) |
| MO46 | Accuracy spread (SD) | 0.057 | 0.129 |
| MO47 | Submissions that scored no rows | "1 submission scored no rows and is not plotted." | no such note is displayed |

**Final submission.** Written report trace. The page states: "Written report. Notebook cell counts, run order, and error outputs are not applicable. The rows below come from the submitted report."

| ID | Requirement | Status | Details |
|---|---|---|---|
| MO48 | Load the dataset | Found | |
| MO49 | Inspect the table | Not found | |
| MO50 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| MO51 | Fit a decision tree | Found | 1 target with a stored tree record. |
| MO52 | Explore tree depth | Not found | No depth-search table is stored. |
| MO53 | Evaluate performance | Found | A test error is stored for 1 target. Training and test curves are stored for 1 |
| MO54 | Visualise the tree | Found | A tree drawing is stored for 1 target. |
| MO55 | Written reflection | Found | Written text stored for 2 of 4 prompts. |

Trees built: Tur (depths tried "1 to 10"; tree drawn "✓ yes"). The "Explore tree depth" row reads "Not found" and the Trees built row lists a depth range; both are reported as displayed. Research questions written out: 0 of 1. Stored model count: 1. A model-written note in Turkish states the file was submitted as a PDF report. [MO56]

Stored rubric points: S1 1/10, S2 0/5, S3 0/5, S4 5/30, S5 4/21, S6 6/20, S7 0/9. [MO57]

**Across sources.** The WS15 answer-key check on the page was 7 / 12 correct (58.3%), and the stage file total was 0.5 of 47. [MO58] In CODAP session 1, Explore data was 72 of 142 labelled frames (50.7%). [MO59] The logs recorded 6 split editor events in session 1 and 3 in session 2. [MO60]

**Missing data and caveats.** No extracted answers for WS1, WS3, WS4, WS5 (missing evidence, not zero). Written report: cell counts are not applicable and are not treated as zero. F1, F4, F5, F6, F8, F11, F13. Session 2 coding model shown as "–". WS14 model summary names another participant (unverified attribution).

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| MO1–MO4 | WS1, WS3, WS4, WS5 | profile Evidence notes and tabs | coverage |
| MO5–MO13 | all Page, Profile, Stage, Cohort cells; 13 of 15 | worksheet pages; profile Worksheets tab | per row |
| MO14–MO17 | 1 flag; 28; Q5, Q19, 4; 0 of 20, 35 | profile WS6, WS13, WS14, WS15 Technical details | per worksheet type |
| MO18 | 24.9%; 3; 9; 25 | profile header | stored-score mean; log count |
| MO19–MO32 | all session values | recordings tab; #/findings/recordings?s=Marco (both sessions) | frame label; model self-rating |
| MO33–MO34 | 72 of 142 (50.7%); 55 of 56 (98.2%); 1 of 50 (2%); 62 of 172 (36%); 46 of 172 (26.7%); 56 of 104 (53.8%); 4 of 43 (9.3%) | findings recordings, What stands out? | frame label |
| MO35 | 42.7% | #/findings/participants | frame label (pooled) |
| MO36–MO47 | all log values | logs tab, sessions 1 and 2 | log count |
| MO48–MO57 | 0.2; 1; 2 of 4; 1 to 10; 0 of 1; 1; points | #/explore/student/Marco/notebook | written report trace; stored rubric points |
| MO58 | 7 / 12 (58.3%); 0.5 of 47 | WS15 page; profile WS15 | rubric items plus rule checks |
| MO59 | 72 of 142 (50.7%) | findings recordings | frame label |
| MO60 | 6; 3 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Marcus

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. [MU1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [MU2]
- Logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [MU3]
- Final Python submission: present, a notebook. [MU4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| MU5 | Concepts | WS1 | Rubric score | 7 / 11 correct (63.6%) | 6 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| MU6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| MU7 | Concepts | WS4 | Rubric score | 4 / 5 correct (80%) | 4 of 5 | 3 of 5 | stage differs | 55% (2.77 / 5); 54% |
| MU8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| MU9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| MU10 | Rules | WS7 | Rule-checked item | 1 / 4 correct (25%) | 1 of 7 | 1 of 7 | F1 | 40% (2.8 / 7); 40% |
| MU11 | Documentation | WS6 | Rule-checked item | 3 / 4 scored correct (75%) | 31 answers | 3 of 4 | F4 | 76% (3.04 / 4); 63% |
| MU12 | Documentation | WS12 | Consistency check | 4 / 5 correct (80%) | 4 of 6 | 4.5 of 7 | F3 type | 71% (5 / 7); 72% |
| MU13 | CODAP | WS13 | Rubric score | 3 / 15 correct (20%) | 3 of 31 | 6.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| MU14 | CODAP | WS14 | Rubric items plus rule checks | 27 / 27 correct (100%) | 31 of 37 | 13.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| MU15 | CODAP | WS15 | Rubric items plus rule checks | 26 / 40 correct (65%) | 32 of 67 | 17 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Marcus:
- WS1: 5 check flags (Blanks 4, 5, 7, 8, 10). [MU16]
- WS6: 3 error flags (non-complementary operators at depth 0 and depth 1 right child; depth 1 left child incomplete). [MU17]
- WS14: Questions 5, 19, 30, 31, 32 and 33 were blank; all 4 further checks "✓ Correct". [MU18]
- WS15: 6 of 20 rule checks "✓ Correct". Questions 41 to 47 were blank. [MU19]

Profile header: "CODAP worksheets: mean score 33.7% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 4 · Model submissions 10". Not used to rank (F6). [MU20]

**CODAP screen recordings.**

CODAP session 1: length 1 h 26 min; frames listed 256; frames labelled 256; speech "ok" (teacher 562, classmate 1,402, student 106); coding model "–". [MU21]

| ID | Label | Frames | Share |
|---|---|---|---|
| MU22 | Explore data | 120 | 46.9% |
| MU23 | Build tree | 20 | 7.8% |
| MU24 | Tune threshold | 11 | 4.3% |
| MU25 | Evaluate model | 18 | 7% |
| MU26 | Compare models | 79 | 30.9% |
| MU27 | Off task | 8 | 3.1% |

As printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 120 of 256 (46.9%). Compare models is next, 79 of 256 (30.9%)." And: "In the first part, Explore data is 84 of 89 labelled frames (94.4%). In the last part, it is 6 of 86 (7%)." [MU28] 38 label changes. Model self-rated confidence: 106 high, 150 medium. 130 frames have a second label. [MU29]

CODAP session 2: "No screen recording frames are on record for Marcus, CODAP session 2". [MU30]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 |
|---|---|---|
| MU31 | Model attempts | 10 |
| MU32 | First attempt | 46 min after starting |
| MU33 | Accuracy of last attempt | 54.3% (n = 46, Food_Dataset_Turkish_55) |
| MU34 | Target | Column 1 (recommendation label, unnamed copy) |
| MU35 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| MU36 | Threshold edit events (split editor used) | 4 |
| MU37 | One kind of edit (VOTAT) | 67% of 9 steps between submissions |
| MU38 | Predictor placements | 9 |
| MU39 | Total actions | 278 |
| MU40 | Session span | 85 min (UTC 08:10:00 to 09:34:58) |
| MU41 | Accuracy spread (SD) | 0.082 |
| MU42 | Submissions that scored no rows | "1 submission scored no rows and is not plotted." |

CODAP session 2: "No class-session log is stored." [MU43]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| MU44 | Load the dataset | Found | |
| MU45 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| MU46 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| MU47 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| MU48 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| MU49 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| MU50 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| MU51 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani (1 to 5), Tur (1 to 10), Cinsiyet (1 to 10). Research questions written out: 3 of 3. Cells: 38 (25 code, 13 text). Code cells run: 0 of 25. Empty code cells: 1. Highest run counter: –. Errors: None. Revisiting earlier code: Never. [MU52]

Stored rubric points: S1 6/10, S2 5/5, S3 5/5, S4 14/30, S5 12/21, S6 15/20, S7 6/9. [MU53]

**Across sources.** The WS13 answer-key check on the page was 3 / 15 correct (20%), and the stage file total was 6.5 of 27. [MU54] In CODAP session 1, Explore data was 120 of 256 labelled frames (46.9%). [MU55] The session 1 log recorded 4 split editor events, and the notebook recorded 0 of 25 code cells run. [MU56]

**Missing data and caveats.** No frames and no log for CODAP session 2. F1, F2, F3 (WS1, WS3; WS12), F4, F5, F6, F11, F13. Session 1 coding model shown as "–". Notebook: 0 of 25 code cells run while outputs are stored.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| MU1–MU4 | – | profile Evidence notes and tabs | coverage |
| MU5–MU15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| MU16–MU19 | 5 flags; 3 flags; Q5, 19, 30–33, 4; 6 of 20, Q41–47 | profile WS1, WS6, WS14, WS15 Technical details | per worksheet type |
| MU20 | 33.7%; 3; 4; 10 | profile header | stored-score mean; log count |
| MU21–MU29 | 1 h 26 min; 256; 256; 562, 1,402, 106; labels; 120 of 256 (46.9%); 79 of 256 (30.9%); 84 of 89 (94.4%); 6 of 86 (7%); 38; 106, 150; 130 | recordings tab; #/findings/recordings?s=Marcus | frame label; model self-rating |
| MU30 | session 2 | findings recordings | coverage |
| MU31–MU43 | all log values | logs tab | log count |
| MU44–MU53 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| MU54 | 3 / 15 (20%); 6.5 of 27 | WS13 page; profile WS13 | rubric score |
| MU55 | 120 of 256 (46.9%) | findings recordings | frame label |
| MU56 | 4; 0 of 25 | logs tab; notebook tab | log count; notebook trace |

Checklist: all ten items answered yes.

---

### Melinda

**Evidence available.**
- Worksheets: partial. Evidence notes read "No worksheet extraction for WS6, WS10, WS12." A note adds: "A scoring file without an extraction is stored for WS6. It is not counted as an extracted response." [ME1]
- Frames: partial. Evidence notes read "No extracted frames for CODAP session 1." CODAP session 2 is present. [ME2]
- Logs: partial. CODAP session 1 reads "No class-session log is stored." CODAP session 2 is present. [ME3]
- Final Python submission: present, a notebook. [ME4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| ME5 | Concepts | WS1 | Rubric score | 10 / 11 correct (90.9%) | 9 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| ME6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| ME7 | Concepts | WS4 | Rubric score | 4 / 5 correct (80%) | 4 of 5 | 4 of 5 | none | 55% (2.77 / 5); 54% |
| ME8 | Thresholds | WS5 | Rule-checked item | 10 / 13 correct (76.9%) | 0 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| ME9 | Thresholds | WS10 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| ME10 | Rules | WS7 | Rule-checked item | 0 / 0 (–) | 0 of 7 | 0 of 7 | F1, F7 | 40% (2.8 / 7); 40% |
| ME11 | Documentation | WS6 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| ME12 | Documentation | WS12 | Consistency check | not listed | no answers on file | none | gap | 13 of 15 participants included |
| ME13 | CODAP | WS13 | Rubric score | 10 / 25 correct (40%) | 10 of 31 | 14.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| ME14 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 | 16.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| ME15 | CODAP | WS15 | Rubric items plus rule checks | 38 / 46 correct (82.6%) | 52 of 67 | 29 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Melinda:
- WS7 (rule-checked item): page shows 0 / 0 correct (–). Profile reads 0 of 7 and stage file reads 0 of 7. This is not a score of 0: the page shows no items were scored. F7 applies. [ME16]
- WS14: all 4 further checks "✓ Correct". [ME17]
- WS15: 14 of 20 rule checks "✓ Correct". [ME18]

Profile header: "CODAP worksheets: mean score 55.1% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 29 · Model submissions 27". Not used to rank (F6). [ME19]

**CODAP screen recordings.**

CODAP session 1: "No screen recording frames are on record for Melinda, CODAP session 1". [ME20]

CODAP session 2: length 1 h 13 min; frames listed 195; frames labelled 195; speech "no_speech"; coding model "–". [ME21]

| ID | Label | Frames | Share |
|---|---|---|---|
| ME22 | Explore data | 45 | 23.1% |
| ME23 | Build tree | 11 | 5.6% |
| ME24 | Tune threshold | 106 | 54.4% |
| ME25 | Evaluate model | 2 | 1% |
| ME26 | Compare models | 24 | 12.3% |
| ME27 | Idle / thinking | 1 | 0.5% |
| ME28 | Off task | 6 | 3.1% |

As printed: "Tune threshold is the most frequent primary label: 106 of 195 labelled frames (54.4%). Explore data is the next largest share, 45 of 195 (23.1%)." And: "In the first part, Explore data is 24 of 52 labelled frames (46.2%). In the last part, it is 9 of 81 (11.1%)." [ME29] 90 label changes. Model self-rated confidence: 41 high, 154 medium. 121 frames have a second label. [ME30] The comparison table shows "Tune threshold · 54.4%" (pooled; only session 2 is labelled). [ME31]

**CODAP platform logs.** Titanic log excluded.

CODAP session 1: "No class-session log is stored." [ME32]

| ID | Measure | CODAP session 2 |
|---|---|---|
| ME33 | Model attempts | 27 |
| ME34 | First attempt | 13 min after starting |
| ME35 | Accuracy of last attempt | 90% (n = 10, Food_Dataset_Turkish_55Tavsiye (1)) * |
| ME36 | Target | Oneri (recommendation label) |
| ME37 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| ME38 | Threshold edit events (split editor used) | 29 |
| ME39 | One kind of edit (VOTAT) | 62% of 26 steps between submissions |
| ME40 | Predictor placements | 14 |
| ME41 | Total actions | 460 |
| ME42 | Session span | 73 min (UTC 08:09:36 to 09:22:47) |
| ME43 | Accuracy spread (SD) | 0.093 |
| ME44 | Submissions that scored no rows | no such note is displayed |

n = 10, so this is a small sample (site marker: "(1)" suffix). The * is added per the brief because n < 10. [ME45]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| ME46 | Load the dataset | Found | |
| ME47 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| ME48 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| ME49 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| ME50 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| ME51 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| ME52 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| ME53 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). Research questions written out: 0 of 3. Cells: 17 (9 code, 8 text). Code cells run: 9 of 9. Empty code cells: 1. Highest run counter: 21. Errors: "Yes, in 1 cell" (output stored). Revisiting earlier code: 1 time. [ME54]

Stored rubric points: S1 9/10, S2 0/5, S3 5/5, S4 17/30, S5 13/21, S6 17/20, S7 6/9. [ME55]

**Across sources.** The WS13 answer-key check on the page was 10 / 25 correct (40%), and the stage file total was 14.5 of 27. [ME56] In CODAP session 2, Tune threshold was 106 of 195 labelled frames (54.4%). [ME57] The session 2 log recorded 29 split editor events. [ME58]

**Missing data and caveats.** No frames and no log for CODAP session 1 (missing evidence). No extracted answers for WS6, WS10, WS12 (missing evidence). WS7 page 0 / 0 is "no items scored" (F7). F1, F2, F3 (WS1, WS3), F4 (WS6 gap), F5, F6, F8, F11, F13. Session 2 accuracy has n = 10, small sample (*).

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| ME1–ME4 | WS6, WS10, WS12; session 1 | profile Evidence notes and tabs | coverage |
| ME5–ME15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| ME16–ME18 | 0 / 0 (–); 4; 14 of 20 | profile WS7, WS14, WS15 Technical details | rule-checked item; rubric items plus rule checks |
| ME19 | 55.1%; 3; 29; 27 | profile header | stored-score mean; log count |
| ME20 | session 1 | recordings tab | coverage |
| ME21–ME28 | 1 h 13 min; 195; 195; label frames and shares | recordings tab CODAP 2 | frame label |
| ME29–ME30 | 106 of 195 (54.4%); 45 of 195 (23.1%); 24 of 52 (46.2%); 9 of 81 (11.1%); 90; 41, 154; 121 | #/findings/recordings?s=Melinda | frame label; model self-rating |
| ME31 | 54.4% | #/findings/participants | frame label (pooled) |
| ME32 | session 1 | logs tab | coverage |
| ME33–ME45 | all log values; n = 10 | logs tab CODAP session 2 | log count |
| ME46–ME55 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| ME56 | 10 / 25 (40%); 14.5 of 27 | WS13 page; profile WS13 | rubric score |
| ME57 | 106 of 195 (54.4%) | findings recordings | frame label |
| ME58 | 29 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Nadia

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. No Evidence notes block. [NA1]
- Frames: present for CODAP session 1 and CODAP session 2. [NA2]
- Logs: present for CODAP session 1 and CODAP session 2. [NA3]
- Final Python submission: present, a notebook. [NA4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| NA5 | Concepts | WS1 | Rubric score | 8 / 10 correct (80%) | 7 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| NA6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 88% (7.04 / 8); 94% |
| NA7 | Concepts | WS4 | Rubric score | 1 / 4 correct (25%) | 1 of 5 | 2 of 5 | F3 type | 55% (2.77 / 5); 54% |
| NA8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| NA9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| NA10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| NA11 | Documentation | WS6 | Rule-checked item | 3 / 5 scored correct (60%) | 31 answers | 3.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| NA12 | Documentation | WS12 | Consistency check | 4 / 6 correct (66.7%) | 4 of 6 | 4.5 of 7 | stage differs | 71% (5 / 7); 72% |
| NA13 | CODAP | WS13 | Rubric score | 9 / 22 correct (40.9%) | 9 of 31 | 12 of 27 | F1 | 41% (11.2 / 27); 32% |
| NA14 | CODAP | WS14 | Rubric items plus rule checks | 33 / 33 correct (100%) | 37 of 37 | 14.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| NA15 | CODAP | WS15 | Rubric items plus rule checks | 34 / 45 correct (75.6%) | 45 of 67 | 26.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Nadia:
- WS14: all 4 further checks "✓ Correct". A model-written note in the page summary names Marcus; this is not a verified attribution. [NA16]
- WS15: 11 of 20 rule checks "✓ Correct". [NA17]

Profile header: "CODAP worksheets: mean score 48.3% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 285 · Model submissions 30". Not used to rank (F6, F12). [NA18]

**CODAP screen recordings.**

| ID | Item | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| NA19 | Length of the source recording | 1 h 24 min | 1 h 16 min |
| NA20 | Frames listed / labelled | 178 / 178 | 215 / 215 |
| NA21 | Speech status | no_speech | no_speech |
| NA22 | Coding model | – | claude-sonnet-5 |
| NA23 | Model self-rated confidence | 93 high, 85 medium | 39 high, 175 medium, 1 low |
| NA24 | Second labels (excluded) | 79 | 163 |
| NA25 | Label changes | 25 | 70 |

| ID | Label | S1 frames | S1 share | S2 frames | S2 share |
|---|---|---|---|---|---|
| NA26 | Explore data | 105 | 59% | 27 | 12.6% |
| NA27 | Build tree | 8 | 4.5% | 38 | 17.7% |
| NA28 | Tune threshold | 12 | 6.7% | 131 | 60.9% |
| NA29 | Evaluate model | 10 | 5.6% | 2 | 0.9% |
| NA30 | Compare models | 43 | 24.2% | 14 | 6.5% |
| NA31 | Off task | not listed | not listed | 3 | 1.4% |

Session 1, as printed: "Explore data is the most frequent primary label: 105 of 178 labelled frames (59%). Compare models is the next largest share, 43 of 178 (24.2%)." And: "In the first part, Explore data is 76 of 76 labelled frames (100%). In the last part, it is 0 of 47 (0%)." [NA32]
Session 2, as printed: "Tune threshold is the most frequent primary label: 131 of 215 labelled frames (60.9%). Build tree is the next largest share, 38 of 215 (17.7%)." No session-clock sentence is printed. [NA33]
Pooled leading label in the comparison table: "Tune threshold · 36.4%" (pooled, F8). [NA34]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| NA35 | Model attempts | 18 | 12 |
| NA36 | First attempt | 48 min after starting | 14 min after starting |
| NA37 | Accuracy of last attempt | 77.8% (n = 45, Food_Dataset_Turkish_55) | 92.3% (n = 13, Food_Dataset_Turkish_56) |
| NA38 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy) |
| NA39 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| NA40 | Threshold edit events (split editor used) | 12 | 273 |
| NA41 | One kind of edit (VOTAT) | 88% of 17 steps between submissions | 9% of 11 steps between submissions |
| NA42 | Predictor placements | 20 | 24 |
| NA43 | Total actions | 367 | 617 |
| NA44 | Session span | 76 min (UTC 08:10:43 to 09:26:51) | 75 min (UTC 08:09:53 to 09:24:29) |
| NA45 | Accuracy spread (SD) | 0.064 | 0.066 |
| NA46 | Submissions that scored no rows | no such note is displayed | no such note is displayed |

Session 2 split editor events: 273 (F12). [NA47]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| NA48 | Load the dataset | Found | |
| NA49 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| NA50 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| NA51 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| NA52 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| NA53 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| NA54 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| NA55 | Written reflection | Not found | Written text stored for 0 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). Research questions written out: 3 of 3. Cells: 39 (19 code, 20 text). Code cells run: 0 of 19. Empty code cells: 0. Highest run counter: –. Errors: None. Revisiting earlier code: Never. [NA56]

Stored rubric points: S1 8/10, S2 5/5, S3 5/5, S4 15/30, S5 13/21, S6 0/20, S7 0/9. [NA57]

**Across sources.** The WS13 answer-key check on the page was 9 / 22 correct (40.9%), and the stage file total was 12 of 27. [NA58] In CODAP session 1, Explore data was 105 of 178 labelled frames (59%). In CODAP session 2, Tune threshold was 131 of 215 labelled frames (60.9%). [NA59] The session 2 log recorded 273 split editor events (F12) and a VOTAT share of 9% of 11 steps. [NA60]

**Missing data and caveats.** F12 (session 2: 273 split editor events, displayed as given). No reflection text stored. F1, F2, F3 (WS1, WS4; WS12 stage differs), F4, F5, F6, F8, F11, F13. Session 1 coding model shown as "–". WS14 model summary names another participant (unverified attribution).

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| NA1–NA4 | – | profile tabs | coverage |
| NA5–NA15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| NA16–NA17 | 4; 11 of 20 | profile WS14, WS15 Technical details | rubric items plus rule checks |
| NA18 | 48.3%; 3; 285; 30 | profile header | stored-score mean; log count |
| NA19–NA31 | all session values | recordings tab; #/findings/recordings?s=Nadia (both sessions) | frame label; model self-rating |
| NA32–NA33 | 105 of 178 (59%); 43 of 178 (24.2%); 76 of 76 (100%); 0 of 47 (0%); 131 of 215 (60.9%); 38 of 215 (17.7%) | findings recordings, What stands out? | frame label |
| NA34 | 36.4% | #/findings/participants | frame label (pooled) |
| NA35–NA47 | all log values; 273 | logs tab, sessions 1 and 2 | log count |
| NA48–NA57 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| NA58 | 9 / 22 (40.9%); 12 of 27 | WS13 page; profile WS13 | rubric score |
| NA59 | 105 of 178 (59%); 131 of 215 (60.9%) | findings recordings | frame label |
| NA60 | 273; 9% of 11 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Serena

**Evidence available.**
- Worksheets: partial. Evidence notes read "No worksheet extraction for WS6, WS10, WS12." A note adds: "A scoring file without an extraction is stored for WS6. It is not counted as an extracted response." [SE1]
- Frames: partial. Evidence notes read "No extracted frames for CODAP session 1." CODAP session 2 is present. [SE2]
- Logs: partial. CODAP session 1 reads "No class-session log is stored." CODAP session 2 is present. [SE3]
- Final Python submission: present, a notebook. [SE4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| SE5 | Concepts | WS1 | Rubric score | 10 / 11 correct (90.9%) | 9 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| SE6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| SE7 | Concepts | WS4 | Rubric score | 3 / 3 correct (100%) | 3 of 5 | 2 of 5 | F3 type | 55% (2.77 / 5); 54% |
| SE8 | Thresholds | WS5 | Rule-checked item | 7 / 13 correct (53.8%) | 0 of 3 | 1 of 4 | F2 | 84% (3.35 / 4); 58% |
| SE9 | Thresholds | WS10 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| SE10 | Rules | WS7 | Rule-checked item | 0 / 0 (–) | 0 of 7 | 0 of 7 | F1, F7 | 40% (2.8 / 7); 40% |
| SE11 | Documentation | WS6 | Rule-checked item | not listed | no answers on file | none | gap | 13 of 15 participants included |
| SE12 | Documentation | WS12 | Consistency check | not listed | no answers on file | none | gap | 13 of 15 participants included |
| SE13 | CODAP | WS13 | Rubric score | 11 / 23 correct (47.8%) | 11 of 31 | 12.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| SE14 | CODAP | WS14 | Rubric items plus rule checks | 31 / 31 correct (100%) | 35 of 37 | 10 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| SE15 | CODAP | WS15 | Rubric items plus rule checks | 45 / 47 correct (95.7%) | 65 of 67 | 29 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Serena:
- WS7 (rule-checked item): page shows 0 / 0 correct (–). F7 applies. [SE16]
- WS14: all 4 further checks "✓ Correct". A model-written note in the page summary names Nadia; this is not a verified attribution. [SE17]
- WS15: all 20 rule checks "✓ Correct". [SE18]

Profile header: "CODAP worksheets: mean score 46.1% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 27 · Model submissions 32". Not used to rank (F6). [SE19]

**CODAP screen recordings.**

CODAP session 1: "No screen recording frames are on record for Serena, CODAP session 1". [SE20]

CODAP session 2: length 1 h 14 min; frames listed 456; frames labelled 456; speech "no_speech"; coding model claude-sonnet-5. [SE21]

| ID | Label | Frames | Share |
|---|---|---|---|
| SE22 | Explore data | 219 | 48% |
| SE23 | Build tree | 44 | 9.6% |
| SE24 | Tune threshold | 81 | 17.8% |
| SE25 | Evaluate model | 10 | 2.2% |
| SE26 | Compare models | 85 | 18.6% |
| SE27 | Idle / thinking | 4 | 0.9% |
| SE28 | Off task | 13 | 2.9% |

As printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 219 of 456 (48%). Compare models is next, 85 of 456 (18.6%)." [SE29] 192 label changes. Model self-rated confidence: 108 high, 347 medium, 1 low. 184 frames have a second label. [SE30] The comparison table shows "Explore data · 48.0%" (pooled; only session 2 is labelled). [SE31]

**CODAP platform logs.** Titanic log excluded.

CODAP session 1: "No class-session log is stored." [SE32]

| ID | Measure | CODAP session 2 |
|---|---|---|
| SE33 | Model attempts | 32 |
| SE34 | First attempt | 8 min after starting |
| SE35 | Accuracy of last attempt | 47.7% (n = 44, Food_Dataset_Turkish_55Tavsiye (1)) |
| SE36 | Target | Enerji (kcal) (energy), Oneri (recommendation label), Tag |
| SE37 | Predictors tried | Doymuş Yağ (g) (saturated fat), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| SE38 | Threshold edit events (split editor used) | 27 |
| SE39 | One kind of edit (VOTAT) | 65% of 31 steps between submissions |
| SE40 | Predictor placements | 34 |
| SE41 | Total actions | 1,274 |
| SE42 | Session span | 63 min (UTC 08:09:39 to 09:12:45) |
| SE43 | Accuracy spread (SD) | 0.098 |
| SE44 | Submissions that scored no rows | "1 submission scored no rows and is not plotted." |

The target field lists three variables, as displayed. [SE45]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| SE46 | Load the dataset | Found | |
| SE47 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| SE48 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| SE49 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| SE50 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| SE51 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| SE52 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| SE53 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). Research questions written out: 0 of 3. Cells: 17 (9 code, 8 text). Code cells run: 9 of 9. Empty code cells: 0. Highest run counter: 21. Errors: "Yes, in 1 cell" (output stored). Revisiting earlier code: 1 time. [SE54]

Stored rubric points: S1 8/10, S2 0/5, S3 5/5, S4 21/30, S5 11/21, S6 17/20, S7 6/9. [SE55]

**Across sources.** The WS13 answer-key check on the page was 11 / 23 correct (47.8%), and the stage file total was 12.5 of 27. [SE56] In CODAP session 2, Explore data was 219 of 456 labelled frames (48%). [SE57] The session 2 log recorded 32 model attempts and 1,274 total actions. [SE58]

**Missing data and caveats.** No frames and no log for CODAP session 1 (missing evidence). No extracted answers for WS6, WS10, WS12. WS7 page 0 / 0 is "no items scored" (F7). F1, F2, F3 (WS1, WS3; WS4), F4 (WS6 gap), F5, F6, F7, F8, F11, F13. WS14 model summary names another participant (unverified attribution).

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| SE1–SE4 | WS6, WS10, WS12; session 1 | profile Evidence notes and tabs | coverage |
| SE5–SE15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| SE16–SE18 | 0 / 0 (–); 4; 20 of 20 | profile WS7, WS14, WS15 Technical details | rule-checked items; rubric items |
| SE19 | 46.1%; 3; 27; 32 | profile header | stored-score mean; log count |
| SE20 | session 1 | recordings tab | coverage |
| SE21–SE28 | 1 h 14 min; 456; 456; label frames and shares | recordings tab CODAP 2 | frame label |
| SE29–SE30 | 219 of 456 (48%); 85 of 456 (18.6%); 192; 108, 347, 1; 184 | #/findings/recordings?s=Serena | frame label; model self-rating |
| SE31 | 48.0% | #/findings/participants | frame label (pooled) |
| SE32 | session 1 | logs tab | coverage |
| SE33–SE45 | all log values; Enerji/Oneri/Tag | logs tab CODAP session 2 | log count |
| SE46–SE55 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| SE56 | 11 / 23 (47.8%); 12.5 of 27 | WS13 page; profile WS13 | rubric score |
| SE57 | 219 of 456 (48%) | findings recordings | frame label |
| SE58 | 32; 1,274 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Shana

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. No Evidence notes block. [SH1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [SH2]
- Logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [SH3]
- Final Python submission: present, a notebook. [SH4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| SH5 | Concepts | WS1 | Rubric score | 9 / 10 correct (90%) | 8 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| SH6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 5 of 8 | 6.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| SH7 | Concepts | WS4 | Rubric score | 1 / 3 correct (33.3%) | 1 of 5 | 1.5 of 5 | F3 type | 55% (2.77 / 5); 54% |
| SH8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 3 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| SH9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| SH10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| SH11 | Documentation | WS6 | Rule-checked item | 5 / 6 scored correct (83.3%) | 31 answers | 3 of 4 | F4 | 76% (3.04 / 4); 63% |
| SH12 | Documentation | WS12 | Consistency check | 6 / 6 correct (100%) | 6 of 6 | 7 of 7 | stage differs | 71% (5 / 7); 72% |
| SH13 | CODAP | WS13 | Rubric score | 10 / 15 correct (66.7%) | 10 of 31 | 8.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| SH14 | CODAP | WS14 | Rubric items plus rule checks | 32 / 32 correct (100%) | 36 of 37 | 17.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| SH15 | CODAP | WS15 | Rubric items plus rule checks | 34 / 41 correct (82.9%) | 49 of 67 | 24.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Shana:
- WS3 (rubric score): page 8 / 8 (100%), profile 5 of 8, stage 6.5 of 8. All three are reported (F3). [SH16]
- WS6: 5 error flags (depth 1 left child: incorrect leaf percentage; depth 2 left child: incorrect leaf percentage; depth 2 right child: incorrect leaf percentage and mismatched operators; depth 0 threshold mismatch). [SH17]
- WS12: all 6 further checks "✓ Correct". WS14: all 4 further checks "✓ Correct". [SH18]
- WS14: a model-written note in the page summary names Sheila; this is not a verified attribution. [SH19]
- WS15: 15 of 20 rule checks "✓ Correct". [SH20]

Profile header: "CODAP worksheets: mean score 45.5% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 5 · Model submissions 13". Not used to rank (F6). [SH21]

**CODAP screen recordings.**

CODAP session 1: length 1 h 23 min; frames listed 270; frames labelled 270; speech "ok" (teacher 394, classmate 963, student 285); coding model "–". [SH22]

| ID | Label | Frames | Share |
|---|---|---|---|
| SH23 | Explore data | 118 | 43.7% |
| SH24 | Build tree | 17 | 6.3% |
| SH25 | Tune threshold | 10 | 3.7% |
| SH26 | Evaluate model | 26 | 9.6% |
| SH27 | Compare models | 86 | 31.9% |
| SH28 | Idle / thinking | 4 | 1.5% |
| SH29 | Off task | 9 | 3.3% |

As printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 118 of 270 (43.7%). Compare models is next, 86 of 270 (31.9%)." And: "In the first part, Explore data is 87 of 96 labelled frames (90.6%). In the last part, it is 3 of 90 (3.3%)." [SH30] 47 label changes. Model self-rated confidence: 150 high, 119 medium, 1 low. 133 frames have a second label. [SH31]

CODAP session 2: "No screen recording frames are on record for Shana, CODAP session 2". [SH32]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 |
|---|---|---|
| SH33 | Model attempts | 13 |
| SH34 | First attempt | 46 min after starting |
| SH35 | Accuracy of last attempt | 72.5% (n = 40, Food_Dataset_Turkish_55 (3)) |
| SH36 | Target | Column 1 (recommendation label, unnamed copy) |
| SH37 | Predictors tried | Karbonhidrat (g) (carbohydrate), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| SH38 | Threshold edit events (split editor used) | 5 |
| SH39 | One kind of edit (VOTAT) | 67% of 12 steps between submissions |
| SH40 | Predictor placements | 13 |
| SH41 | Total actions | 364 |
| SH42 | Session span | 86 min (UTC 08:09:32 to 09:35:39) |
| SH43 | Accuracy spread (SD) | 0.063 |
| SH44 | Submissions that scored no rows | "2 submissions scored no rows and are not plotted." |

CODAP session 2: "No class-session log is stored." [SH45]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| SH46 | Load the dataset | Found | |
| SH47 | Inspect the table | Found | Class counts are stored (note: "Class counts are stored") |
| SH48 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| SH49 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| SH50 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| SH51 | Evaluate performance | Found | A test error is stored for 1 target. Training and test curves are stored for 1 |
| SH52 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| SH53 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani (1 to 5), Tur (1 to 10), Cinsiyet (1 to 10). Research questions written out: 0 of 3. Cells: 29 (19 code, 10 text). Code cells run: 5 of 19. Empty code cells: 0. Highest run counter: 27. Pictures stored: 5. Errors: None. Revisiting earlier code: Never. [SH54]

Stored rubric points: S1 2/10, S2 0/5, S3 5/5, S4 12/30, S5 10/21, S6 17/20, S7 4/9. [SH55]

**Across sources.** The WS13 answer-key check on the page was 10 / 15 correct (66.7%), and the stage file total was 8.5 of 27. [SH56] In CODAP session 1, Explore data was 118 of 270 labelled frames (43.7%). [SH57] The session 1 log recorded 5 split editor events and 2 no-row submissions. [SH58]

**Missing data and caveats.** No frames and no log for CODAP session 2. F1, F2, F3 (WS1 page 9 / 10 vs profile 8 of 11; WS3 page 8 / 8 vs profile 5 of 8; WS4; WS7), F4, F5, F6, F11, F13. Session 1 coding model shown as "–". WS12 stage file 7 of 7 vs page 6 / 6. WS14 model summary names another participant (unverified attribution). Notebook: 5 of 19 code cells run; a test error is stored for 1 target only.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| SH1–SH4 | – | profile tabs | coverage |
| SH5–SH15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| SH16–SH20 | 8 / 8, 5 of 8, 6.5 of 8; 5 flags; 6; 4; 15 of 20 | profile WS3, WS6, WS12, WS14, WS15 | rubric score; rule-checked item; rubric items |
| SH21 | 45.5%; 3; 5; 13 | profile header | stored-score mean; log count |
| SH22–SH31 | 1 h 23 min; 270; 270; 394, 963, 285; labels; 118 of 270 (43.7%); 86 of 270 (31.9%); 87 of 96 (90.6%); 3 of 90 (3.3%); 47; 150, 119, 1; 133 | recordings tab; #/findings/recordings?s=Shana | frame label; model self-rating |
| SH32 | session 2 | findings recordings | coverage |
| SH33–SH45 | all log values; 2 | logs tab, session 1 | log count |
| SH46–SH55 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| SH56 | 10 / 15 (66.7%); 8.5 of 27 | WS13 page; profile WS13 | rubric score |
| SH57 | 118 of 270 (43.7%) | findings recordings | frame label |
| SH58 | 5; 2 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Sheila

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. No Evidence notes block. [SL1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [SL2]
- Logs: partial. CODAP session 1 is present. CODAP session 2 reads "No class-session log is stored." [SL3]
- Final Python submission: present, a notebook. [SL4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| SL5 | Concepts | WS1 | Rubric score | 9 / 11 correct (81.8%) | 8 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| SL6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 7 of 8 | 7.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| SL7 | Concepts | WS4 | Rubric score | 2 / 5 correct (40%) | 2 of 5 | 3 of 5 | stage differs | 55% (2.77 / 5); 54% |
| SL8 | Thresholds | WS5 | Rule-checked item | 4 / 13 correct (30.8%) | 0 of 3 | 1 of 4 | F2 | 84% (3.35 / 4); 58% |
| SL9 | Thresholds | WS10 | Rule-checked item | 7 / 7 correct (100%) | 7 of 8 | 7 of 8 | F3 type | 93% (7.46 / 8); 89% |
| SL10 | Rules | WS7 | Rule-checked item | 4 / 4 correct (100%) | 4 of 7 | 4 of 7 | F1 | 40% (2.8 / 7); 40% |
| SL11 | Documentation | WS6 | Rule-checked item | 2 / 4 scored correct (50%) | 32 answers | 2.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| SL12 | Documentation | WS12 | Consistency check | 6 / 6 correct (100%) | 6 of 6 | 7 of 7 | stage differs | 71% (5 / 7); 72% |
| SL13 | CODAP | WS13 | Rubric score | 8 / 15 correct (53.3%) | 8 of 31 | 8.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| SL14 | CODAP | WS14 | Rubric items plus rule checks | 29 / 31 correct (93.5%) | 32 of 37 | 14 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| SL15 | CODAP | WS15 | Rubric items plus rule checks | 39 / 45 correct (86.7%) | 55 of 67 | 27 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Sheila:
- WS10 (rule-checked item): page 7 / 7 (100%), profile 7 of 8. Both are reported (F3 type). [SL16]
- WS14: Questions 14 and 16 carry the flag INVARIANT_FP_FN_NONZERO. The rule check "fp fn zero" is listed as "✗ Not correct" (3 of 4 further checks "✓ Correct"). A model-written note in the page summary names Serena; this is not a verified attribution. [SL17]
- WS15: 16 of 20 rule checks "✓ Correct". [SL18]

Profile header: "CODAP worksheets: mean score 43.8% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 42 · Model submissions 9". Not used to rank (F6). [SL19]

**CODAP screen recordings.**

CODAP session 1: length 1 h 26 min; frames listed 285 (labelled: 285); speech "no_speech"; coding model "–". The extraction summary reports 298 kept frames while the listed frames and behaviour coding use 285 (F9). [SL20]

| ID | Label | Frames | Share |
|---|---|---|---|
| SL21 | Explore data | 120 | 42.1% |
| SL22 | Build tree | 16 | 5.6% |
| SL23 | Tune threshold | 30 | 10.5% |
| SL24 | Evaluate model | 33 | 11.6% |
| SL25 | Compare models | 45 | 15.8% |
| SL26 | Off task | 41 | 14.4% |

As printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 120 of 285 (42.1%). Compare models is next, 45 of 285 (15.8%)." And: "In the first part, Explore data is 90 of 118 labelled frames (76.3%). In the last part, it is 8 of 104 (7.7%)." [SL27] 93 label changes. Model self-rated confidence: 119 high, 164 medium, 2 low. 130 frames have a second label. [SL28]

CODAP session 2: "No screen recording frames are on record for Sheila, CODAP session 2". [SL29]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 |
|---|---|---|
| SL30 | Model attempts | 9 |
| SL31 | First attempt | 46 min after starting |
| SL32 | Accuracy of last attempt | 77.5% (n = 40, Food_Dataset_Turkish_55 (2)) |
| SL33 | Target | Column 1 (recommendation label, unnamed copy) |
| SL34 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Yağ (g) (fat), Şeker (g) (sugar) |
| SL35 | Threshold edit events (split editor used) | 42 |
| SL36 | One kind of edit (VOTAT) | 50% of 8 steps between submissions |
| SL37 | Predictor placements | 11 |
| SL38 | Total actions | 398 |
| SL39 | Session span | 81 min (UTC 08:10:11 to 09:31:35) |
| SL40 | Accuracy spread (SD) | 0.125 |
| SL41 | Submissions that scored no rows | "1 submission scored no rows and is not plotted." |

CODAP session 2: "No class-session log is stored." [SL42]

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| SL43 | Load the dataset | Found | |
| SL44 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| SL45 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| SL46 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| SL47 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| SL48 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| SL49 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| SL50 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). Research questions written out: 0 of 3. Cells: 49 (32 code, 17 text). Code cells run: 32 of 32. Empty code cells: 0. Highest run counter: 32. Errors: None. Revisiting earlier code: Never. [SL51]

Stored rubric points: S1 8/10, S2 0/5, S3 5/5, S4 16/30, S5 12/21, S6 16/20, S7 4/9. [SL52]

**Across sources.** The WS13 answer-key check on the page was 8 / 15 correct (53.3%), and the stage file total was 8.5 of 27. [SL53] In CODAP session 1, Explore data was 120 of 285 labelled frames (42.1%). [SL54] The session 1 log recorded 42 split editor events. [SL55]

**Missing data and caveats.** No frames and no log for CODAP session 2. F9 (extraction summary 298 vs listed 285; behaviour coding uses 285). F1, F2, F3 (WS1, WS3; WS10 page 7 / 7 vs profile 7 of 8), F4, F5, F6, F11, F13. Session 1 coding model shown as "–". WS4 stage 3 of 5 vs page 2 / 5. WS12 and WS14 also carry stage differences. WS14 model summary names another participant (unverified attribution).

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| SL1–SL4 | – | profile tabs | coverage |
| SL5–SL15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| SL16–SL18 | 7 / 7, 7 of 8; Q14, Q16; 3 of 4; 16 of 20 | profile WS10, WS14, WS15 Technical details | rule-checked item; rubric items plus rule checks |
| SL19 | 43.8%; 3; 42; 9 | profile header | stored-score mean; log count |
| SL20–SL28 | 1 h 26 min; 285; 285; 298; labels; 120 of 285 (42.1%); 45 of 285 (15.8%); 90 of 118 (76.3%); 8 of 104 (7.7%); 93; 119, 164, 2; 130 | recordings tab; findings recordings; #/docs/limitations | frame label; model self-rating |
| SL29 | session 2 | findings recordings | coverage |
| SL30–SL42 | all log values; 1 | logs tab, session 1 | log count |
| SL43–SL52 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| SL53 | 8 / 15 (53.3%); 8.5 of 27 | WS13 page; profile WS13 | rubric score |
| SL54 | 120 of 285 (42.1%) | findings recordings | frame label |
| SL55 | 42 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Ulysses

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. Evidence notes read "The notebook inspection records a substitute data table." [UL1]
- Frames: present for CODAP session 1 and CODAP session 2. [UL2]
- Logs: present for CODAP session 1 and CODAP session 2. [UL3]
- Final Python submission: present, a notebook. The site notes the substitute data table. [UL4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| UL5 | Concepts | WS1 | Rubric score | 6 / 10 correct (60%) | 5 of 11 | 5 of 11 | F3 | 45% (4.92 / 11); 81% |
| UL6 | Concepts | WS3 | Rubric score | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 88% (7.04 / 8); 94% |
| UL7 | Concepts | WS4 | Rubric score | 3 / 5 correct (60%) | 3 of 5 | 4 of 5 | stage differs | 55% (2.77 / 5); 54% |
| UL8 | Thresholds | WS5 | Rule-checked item | 8 / 13 correct (61.5%) | 2 of 3 | 3 of 4 | F2 | 84% (3.35 / 4); 58% |
| UL9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| UL10 | Rules | WS7 | Rule-checked item | 2 / 4 correct (50%) | 2 of 7 | 2 of 7 | F1 | 40% (2.8 / 7); 40% |
| UL11 | Documentation | WS6 | Rule-checked item | 3 / 4 scored correct (75%) | 27 answers | 3 of 4 | F4 | 76% (3.04 / 4); 63% |
| UL12 | Documentation | WS12 | Consistency check | 2 / 3 correct (66.7%) | 2 of 6 | 2.5 of 7 | F3 type | 71% (5 / 7); 72% |
| UL13 | CODAP | WS13 | Rubric score | 8 / 19 correct (42.1%) | 8 of 31 | 11.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| UL14 | CODAP | WS14 | Rubric items plus rule checks | 32 / 32 correct (100%) | 36 of 37 | 17.5 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| UL15 | CODAP | WS15 | Rubric items plus rule checks | 18 / 20 correct (90%) | 23 of 67 | 6.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Ulysses:
- WS14: all 4 further checks "✓ Correct". A model-written note in the page summary names Shana; this is not a verified attribution. [UL16]
- WS15: 5 of 20 rule checks "✓ Correct". [UL17]

Profile header: "CODAP worksheets: mean score 36.5% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 36 · Model submissions 17". Not used to rank (F6). [UL18]

**CODAP screen recordings.**

| ID | Item | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| UL19 | Length of the source recording | 1 h 23 min | 1 h 17 min |
| UL20 | Frames listed / labelled | 223 / 223 | 529 / 529 |
| UL21 | Speech status | no_speech | no_speech (note: the page also lists per-role speech counts: student 1, classmate 12, teacher 3) |
| UL22 | Coding model | – | – |
| UL23 | Model self-rated confidence | 134 high, 89 medium | 424 high, 104 medium, 1 low |
| UL24 | Second labels (excluded) | 75 | 78 |
| UL25 | Label changes | 41 | 111 |

| ID | Label | S1 frames | S1 share | S2 frames | S2 share |
|---|---|---|---|---|---|
| UL26 | Explore data | 110 | 49.3% | 34 | 6.4% |
| UL27 | Build tree | 5 | 2.2% | 10 | 1.9% |
| UL28 | Tune threshold | 15 | 6.7% | 56 | 10.6% |
| UL29 | Evaluate model | 6 | 2.7% | not listed | not listed |
| UL30 | Compare models | 47 | 21.1% | 25 | 4.7% |
| UL31 | Idle / thinking | not listed | not listed | 3 | 0.6% |
| UL32 | Off task | 40 | 17.9% | 401 | 75.8% |

Session 1, as printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 110 of 223 (49.3%). Compare models is next, 47 of 223 (21.1%)." And: "In the first part, Compare models is 0 of 109 labelled frames (0%). In the last part, it is 40 of 48 (83.3%)." The extraction summary reports 245 kept frames while the listed frames and behaviour coding use 223 (F9). [UL33]
Session 2, as printed: "Off task is the most frequent primary label: 401 of 529 labelled frames (75.8%). Tune threshold is the next largest share, 56 of 529 (10.6%)." And: "In the first part, Off task is 34 of 69 labelled frames (49.3%). In the last part, it is 196 of 265 (74%)." [UL34]
Pooled leading label in the comparison table: "Off task · 58.6%" (pooled, F8). [UL35]
F10 verified: all episode timestamps in CODAP session 1 are listed as 0:00. [UL36]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| UL37 | Model attempts | 12 | 5 |
| UL38 | First attempt | 46 min after starting | 22 min after starting |
| UL39 | Accuracy of last attempt | 50% (n = 44, Food_Dataset_Turkish_55) | 58.3% (n = 12, Food_Dataset_Turkish_55Tavsiye (1)) |
| UL40 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy), Oneri (recommendation label) |
| UL41 | Predictors tried | Doymuş Yağ (g) (saturated fat), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Şeker (g) (sugar) |
| UL42 | Threshold edit events (split editor used) | 35 | 1 |
| UL43 | One kind of edit (VOTAT) | 64% of 11 steps between submissions | 50% of 4 steps between submissions |
| UL44 | Predictor placements | 8 | 7 |
| UL45 | Total actions | 333 | 133 |
| UL46 | Session span | 82 min (UTC 08:10:21 to 09:32:29) | 66 min (UTC 08:08:57 to 09:14:30) |
| UL47 | Accuracy spread (SD) | 0.088 | 0.071 |
| UL48 | Submissions that scored no rows | no such note is displayed | no such note is displayed |

**Final Python submission.** Notebook trace. The site states: "The inspection records a substitute data table. Rates below are taken from that table."

| ID | Requirement | Status | Details |
|---|---|---|---|
| UL49 | Load the dataset | Found | Site records a note: class counts for the substitute data are stored. |
| UL50 | Inspect the table | Found | Class counts are stored (note: substitute data, not the assigned dataset). |
| UL51 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| UL52 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| UL53 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| UL54 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| UL55 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| UL56 | Written reflection | Not found | Written text stored for 0 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (depths 1 to 10 for each). An output cell on the site prints: "Orijinal 'lizard_data.csv' bulunamadı. Rapordaki dağılımlara uygun yapay veri üretiliyor..." ("Original 'lizard_data.csv' not found. Generating synthetic data matching the report distributions...") This message is transcribed as displayed; it is not a finding about understanding. Research questions written out: 0 of 3. Cells: 1 (1 code, 0 text). Code cells run: 1 of 1. Highest run counter: 1. Pictures stored: 1. Errors: None. Revisiting earlier code: Never. [UL57]

Stored rubric points: S1 0/10, S2 0/5, S3 2/5, S4 9/30, S5 15/21, S6 0/20, S7 0/9. [UL58]

**Across sources.** The WS13 answer-key check on the page was 8 / 19 correct (42.1%), and the stage file total was 11.5 of 27. [UL59] In CODAP session 2, Off task was 401 of 529 labelled frames (75.8%). [UL60] The session 1 log recorded 35 split editor events; session 2 recorded 1. [UL61]

**Missing data and caveats.** F9 (session 1 extraction summary 245 vs listed 223). F10 (session 1 episode timestamps all 0:00). The notebook records a substitute data table; requirements read from the site's own inspection of that table. No reflection stored. F1, F2, F3 (WS1, WS12), F4, F5, F6, F8, F11, F13. WS4 stage 4 of 5 vs page 3 / 5. Session 2 target field lists two variables as displayed.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| UL1–UL4 | "substitute data table" | profile Evidence notes and tabs; #/docs/limitations | coverage |
| UL5–UL15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| UL16–UL17 | 4; 5 of 20 | profile WS14, WS15 Technical details | rubric items plus rule checks |
| UL18 | 36.5%; 3; 36; 17 | profile header | stored-score mean; log count |
| UL19–UL32 | all session values | recordings tab; #/findings/recordings?s=Ulysses (both sessions) | frame label; model self-rating |
| UL33–UL36 | 110 of 223 (49.3%); 47 of 223 (21.1%); 0 of 109 (0%); 40 of 48 (83.3%); 245; 223; 401 of 529 (75.8%); 56 of 529 (10.6%); 34 of 69 (49.3%); 196 of 265 (74%); 0:00 | findings recordings; Limitations | frame label |
| UL35 | 58.6% | #/findings/participants | frame label (pooled) |
| UL37–UL48 | all log values | logs tab, sessions 1 and 2 | log count |
| UL49–UL58 | all requirement, cell and point values; substitute-data output text | notebook tab | notebook trace; stored rubric points |
| UL59 | 8 / 19 (42.1%); 11.5 of 27 | WS13 page; profile WS13 | rubric score |
| UL60 | 401 of 529 (75.8%) | findings recordings | frame label |
| UL61 | 35; 1 | logs tab | log count |

Checklist: all ten items answered yes.

---

### Zara

**Evidence available.**
- Worksheets: present for all eleven scored worksheets. No Evidence notes block. [ZA1]
- Frames: partial. CODAP session 1 is present. Evidence notes read "No extracted frames for CODAP session 2." [ZA2]
- Logs: present for CODAP session 1 and CODAP session 2. [ZA3]
- Final Python submission: present, a notebook. [ZA4]

**Worksheets.**

| ID | Group | WS | Evidence type | Page | Profile | Stage | Flag | Cohort |
|---|---|---|---|---|---|---|---|---|
| ZA5 | Concepts | WS1 | Rubric score | 10 / 11 correct (90.9%) | 9 of 11 | 4.5 of 11 | F3 | 45% (4.92 / 11); 81% |
| ZA6 | Concepts | WS3 | Rubric score | 6 / 8 correct (75%) | 5 of 8 | 5.5 of 8 | F3 | 88% (7.04 / 8); 94% |
| ZA7 | Concepts | WS4 | Rubric score | 2 / 5 correct (40%) | 2 of 5 | 2.5 of 5 | stage differs | 55% (2.77 / 5); 54% |
| ZA8 | Thresholds | WS5 | Rule-checked item | 13 / 13 correct (100%) | 0 of 3 | 4 of 4 | F2 | 84% (3.35 / 4); 58% |
| ZA9 | Thresholds | WS10 | Rule-checked item | 8 / 8 correct (100%) | 8 of 8 | 8 of 8 | none | 93% (7.46 / 8); 89% |
| ZA10 | Rules | WS7 | Rule-checked item | 3 / 4 correct (75%) | 3 of 7 | 3 of 7 | F1 | 40% (2.8 / 7); 40% |
| ZA11 | Documentation | WS6 | Rule-checked item | 2 / 6 scored correct (33.3%) | 31 answers | 1.5 of 4 | F4 | 76% (3.04 / 4); 63% |
| ZA12 | Documentation | WS12 | Consistency check | 6 / 6 correct (100%) | 6 of 6 | 7 of 7 | stage differs | 71% (5 / 7); 72% |
| ZA13 | CODAP | WS13 | Rubric score | 12 / 22 correct (54.5%) | 12 of 31 | 12.5 of 27 | F1 | 41% (11.2 / 27); 32% |
| ZA14 | CODAP | WS14 | Rubric items plus rule checks | 32 / 32 correct (100%) | 36 of 37 | 18 of 33 | F1, F5 | 47% (15.6 / 33); 95% |
| ZA15 | CODAP | WS15 | Rubric items plus rule checks | 25 / 26 correct (96.2%) | 35 of 67 | 17.5 of 47 | F1 | 47% (22.3 / 47); 69% |

Item-level results shown for Zara:
- WS6: 4 error flags (depth 0: non_complementary_operators; depth 1 left child: incorrect leaf percentage; depth 1 right child: incorrect leaf percentage and mismatched operators). [ZA16]
- WS14: all 4 further checks "✓ Correct". [ZA17]
- WS15: 10 of 20 rule checks "✓ Correct". [ZA18]

Profile header: "CODAP worksheets: mean score 46.0% of the maximum, across 3 of WS13, WS14 and WS15 · Threshold edit events 30 · Model submissions 30". Not used to rank (F6). [ZA19]

**CODAP screen recordings.**

CODAP session 1: length 1 h 27 min; frames listed 211; frames labelled 211; speech "no_speech"; coding model "–". The extraction summary reports 233 kept frames while the listed frames and behaviour coding use 211 (F9). [ZA20]

| ID | Label | Frames | Share |
|---|---|---|---|
| ZA21 | Explore data | 94 | 44.5% |
| ZA22 | Build tree | 15 | 7.1% |
| ZA23 | Tune threshold | 10 | 4.7% |
| ZA24 | Evaluate model | 11 | 5.2% |
| ZA25 | Compare models | 54 | 25.6% |
| ZA26 | Off task | 27 | 12.8% |

As printed: "No primary label reaches half of the labelled frames. The largest share is Explore data, 94 of 211 (44.5%). Compare models is next, 54 of 211 (25.6%)." And: "In the first part, Explore data is 60 of 68 labelled frames (88.2%). In the last part, it is 9 of 73 (12.3%)." [ZA27] 50 label changes. Model self-rated confidence: 107 high, 104 medium. 97 frames have a second label. [ZA28]

CODAP session 2: "No screen recording frames are on record for Zara, CODAP session 2". [ZA29]

**CODAP platform logs.** Titanic log excluded.

| ID | Measure | CODAP session 1 | CODAP session 2 |
|---|---|---|---|
| ZA30 | Model attempts | 18 | 12 |
| ZA31 | First attempt | 45 min after starting | 19 min after starting |
| ZA32 | Accuracy of last attempt | 76.2% (n = 42, Food_Dataset_Turkish_55) | 38.5% (n = 13, Food_Dataset_Turkish_56) |
| ZA33 | Target | Column 1 (recommendation label, unnamed copy) | Column 1 (recommendation label, unnamed copy) |
| ZA34 | Predictors tried | Doymuş Yağ (g) (saturated fat), Enerji (kcal) (energy), Karbonhidrat (g) (carbohydrate), Protein (g), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) | Doymuş Yağ (g) (saturated fat), Tuz (g) (salt), Yağ (g) (fat), Şeker (g) (sugar) |
| ZA35 | Threshold edit events (split editor used) | 19 | 11 |
| ZA36 | One kind of edit (VOTAT) | 82% of 17 steps between submissions | 55% of 11 steps between submissions |
| ZA37 | Predictor placements | 18 | 14 |
| ZA38 | Total actions | 345 | 311 |
| ZA39 | Session span | 83 min (UTC 08:10:42 to 09:34:03) | 74 min (UTC 08:08:41 to 09:22:30) |
| ZA40 | Accuracy spread (SD) | 0.094 | 0.258 |
| ZA41 | Submissions that scored no rows | no such note is displayed | no such note is displayed |

**Final Python submission.** Notebook trace.

| ID | Requirement | Status | Details |
|---|---|---|---|
| ZA42 | Load the dataset | Found | |
| ZA43 | Inspect the table | Found | Class counts are stored. A numeric summary is stored |
| ZA44 | Separate training and test data | Found | Test fraction 0.2 is recorded. |
| ZA45 | Fit a decision tree | Found | 3 targets with a stored tree record. |
| ZA46 | Explore tree depth | Found | Depth-search table stored for 3 of 3. |
| ZA47 | Evaluate performance | Found | A test error is stored for 3 targets. Training and test curves are stored for 3 |
| ZA48 | Visualise the tree | Found | A tree drawing is stored for 3 targets. |
| ZA49 | Written reflection | Found | Written text stored for 4 of 4 prompts. |

Targets: YasamAlani, Cinsiyet, Tur (all depths 1 to 5). Research questions written out: 3 of 3. Cells: 66 (26 code, 40 text). Code cells run: 26 of 26. Empty code cells: 0. Highest run counter: 127. Errors: None. Revisiting earlier code: Never. [ZA50]

Stored rubric points: S1 10/10, S2 5/5, S3 5/5, S4 15/30, S5 15/21, S6 18/20, S7 6/9. [ZA51]

**Across sources.** The WS13 answer-key check on the page was 12 / 22 correct (54.5%), and the stage file total was 12.5 of 27. [ZA52] In CODAP session 1, Explore data was 94 of 211 labelled frames (44.5%). [ZA53] The two CODAP session logs recorded 18 and 12 model attempts, with VOTAT shares of 82% and 55% respectively. [ZA54]

**Missing data and caveats.** No frames for CODAP session 2. F9 (session 1 extraction summary 233 vs listed 211). F1, F2, F3 (WS1; WS3), F4, F5, F6, F11, F13. Session 1 coding model shown as "–". WS4 and WS12 stage files differ from their pages. WS15 page 25 / 26 (96.2%) vs profile 35 of 67.

**Ledger map.**

| ID | Number used | Page + section | Evidence type |
|---|---|---|---|
| ZA1–ZA4 | – | profile tabs | coverage |
| ZA5–ZA15 | all Page, Profile, Stage, Cohort cells | worksheet pages; profile Worksheets tab | per row |
| ZA16–ZA18 | 4 flags; 4; 10 of 20 | profile WS6, WS14, WS15 Technical details | rule-checked item; rubric items plus rule checks |
| ZA19 | 46.0%; 3; 30; 30 | profile header | stored-score mean; log count |
| ZA20–ZA28 | 1 h 27 min; 211; 211; 233; labels; 94 of 211 (44.5%); 54 of 211 (25.6%); 60 of 68 (88.2%); 9 of 73 (12.3%); 50; 107, 104; 97 | recordings tab; findings recordings; Limitations | frame label; model self-rating |
| ZA29 | session 2 | findings recordings | coverage |
| ZA30–ZA41 | all log values | logs tab, sessions 1 and 2 | log count |
| ZA42–ZA51 | all requirement, cell and point values | notebook tab | notebook trace; stored rubric points |
| ZA52 | 12 / 22 (54.5%); 12.5 of 27 | WS13 page; profile WS13 | rubric score |
| ZA53 | 94 of 211 (44.5%) | findings recordings | frame label |
| ZA54 | 18; 12; 82% of 17; 55% of 11 | logs tab | log count |

Checklist: all ten items answered yes.

---

## Cohort coverage table

The table uses evidence from #/findings/participants, the per-student worksheet findings pages, the per-student recordings findings pages, the logs and notebook tabs. All values are reported as displayed.

| Participant | WS1 | WS3 | WS4 | WS5 | WS6 | WS7 | WS10 | WS12 | WS13 | WS14 | WS15 | Frames S1 | Frames S2 | Log S1 | Log S2 | Notebook |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Amy | present | present | present | — | present | present | present | present | present | present | present | present | — | present | — | present |
| Bruno | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Helena | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Iris | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Irma | present | present | present | present | present | present | present | present | present | present | present | unlabelled | present | present | present | present |
| Isabel | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present |
| Marco | — | — | — | — | present | present | present | present | present | present | present | present | present | present | present | written report |
| Marcus | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Melinda | present | present | present | present | — | present | — | — | present | present | present | — | present | — | present | present |
| Nadia | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present |
| Serena | present | present | present | present | — | present | — | — | present | present | present | — | present | — | present | present |
| Shana | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Sheila | present | present | present | present | present | present | present | present | present | present | present | present | — | present | — | present |
| Ulysses | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present | present (substitute data) |
| Zara | present | present | present | present | present | present | present | present | present | present | present | present | — | present | present | present |

**Notes:**
- Amy: not listed on WS5. Irma S1: 335 frames listed, none labelled. Marco: not listed on WS1, WS3, WS4, WS5; submitted a written report.
- Melinda and Serena: not listed on WS6, WS10, WS12. Ulysses: notebook contains a substitute data table.
- "—" = not on file or not extracted. It is missing evidence, not zero.

---

## Flags per participant

The table lists which of the thirteen known discrepancies (F1 to F13) touch each participant. Flags are reported, not scored.

| Participant | Flags that apply |
|---|---|
| Amy | F1, F2, F3, F4, F6, F8, F11, F13 |
| Bruno | F1, F2, F3, F4, F6, F8, F11, F13 |
| Helena | F1, F2, F3, F4, F5, F6, F11, F13 |
| Iris | F1, F2, F3, F4, F5, F6, F11, F13 |
| Irma | F1, F2, F3, F4, F5, F6, F8, F10, F11, F13 |
| Isabel | F1, F2, F3, F4, F5, F6, F8, F11, F13 |
| Marco | F1, F4, F5, F6, F8, F11, F13 |
| Marcus | F1, F2, F3, F4, F5, F6, F11, F13 |
| Melinda | F1, F2, F3, F4, F5, F6, F7, F8, F11, F13 |
| Nadia | F1, F2, F3, F4, F5, F6, F8, F11, F12, F13 |
| Serena | F1, F2, F3, F4, F5, F6, F7, F8, F11, F13 |
| Shana | F1, F2, F3, F4, F5, F6, F11, F13 |
| Sheila | F1, F2, F3, F4, F5, F6, F9, F11, F13 |
| Ulysses | F1, F2, F3, F4, F5, F6, F8, F9, F10, F11, F13 |
| Zara | F1, F2, F3, F4, F5, F6, F9, F11, F13 |

**F-flag notes (per the brief and site):**
- F1: WS7, WS13, WS14, WS15 page differs from profile across the cohort.
- F2: WS5 profile count differs from page answer count across all 13 included participants; the two instruments measure differently.
- F3: WS1 and early worksheet page and profile values often differ; WS3 Shana page 8/8 vs profile 5 of 8; WS4, WS7, WS10, WS12 stage file differences noted per participant.
- F4: WS6 "N answers" is a count, not a score, for all participants.
- F5: WS14 average correct rate of 95% vs average score of 47% (cohort-level; affects all 15 participants).
- F6: header mean is described as the mean of WS13–WS15 stage scores; affects all 15 participants.
- F7: Melinda WS7 0/0 and Serena WS7 0/0 are "no items scored", not a zero score.
- F8: pooled leading frame label differs from per-session labels for participants with only one labelled session (Amy, Bruno, Helena, Iris, Marco, Marcus, Melinda, Serena, Shana, Sheila), or is pooled across two differing sessions (Irma, Isabel, Nadia, Ulysses, Zara).
- F9: Sheila (298 vs 285), Ulysses (245 vs 223), Zara (233 vs 211).
- F10: Irma S1 and S2 episode lists identical; Ulysses S1 episode timestamps all 0:00.
- F11: per-participant action totals are session sums; cohort-level totals would pool sessions with different coverage.
- F12: Nadia S2 split editor events 273 (as displayed).
- F13: six participants unnamed on WS14 (once only). Noted in the method.

---

## Section 10 checklist

1. Logs record actions, not understanding. **Yes.** No claim in any profile attributes understanding, intent, or learning to log values.
2. Last accuracy carries its n rows. **Yes.** All log accuracy values include the n count as displayed. The * mark is applied where n < 10 (Isabel S2, Melinda S2).
3. VOTAT is given as a share with its steps. **Yes.** All VOTAT values are given as "X% of Y steps between submissions."
4. change_split_values rows are "split editor events." **Yes.** The phrase "threshold edit events (split editor used)" is used throughout. No profile states that a threshold value changed.
5. Frame counts are not time. **Yes.** Shares use frames as the denominator. No time conversion appears.
6. analysis_confidence is the model's self-rating. **Yes.** Confidence is labelled "model self-rated confidence" in every profile.
7. There is no log-to-video synchronisation. **Yes.** No profile links log events to frame timestamps.
8. Titanic is excluded. **Yes.** Every log section carries the note "Titanic log excluded."
9. WS11 is not scored evidence. **Yes.** WS11 does not appear in any profile.
10. Missing data is missing evidence, never zero. **Yes.** All gaps use "—", "not on file", "no answers on file", or "No class-session log is stored." None writes or implies zero.
