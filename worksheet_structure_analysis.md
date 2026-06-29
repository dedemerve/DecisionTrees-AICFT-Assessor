# Worksheet Structure Analysis

## Overview

9 PDF found in answer_key_worksheets folder.
Two distinct worksheet families identified:

1. ProDaBi worksheets (WS 1, 3, 4, 5, 6, 7, 10, 11) — unplugged phase, paper-based
2. Worksheet DT — plugged phase, CODAP Arbor activity, most analytically rich

---

## Family 1: ProDaBi Worksheets (Unplugged Phase)

### Worksheet 1 — Important Terms
Type: Fill-in-the-blank
Concepts tested: object, feature/variable, label
Key blanks: nesne (object), özellik (feature), etiket (label)
Assessment difficulty: Recall only. Binary correct/wrong.

Expected answers:
- "Tek tek gıdalar" → nesne (object)
- Sol sütundaki bilgiler → özellik / değişken / karakteristik (feature)
- Kaç özellik? → 8 (the food data cards have 8 nutritional features)
- "Fındıklı gofret ... tavsiye edilemez" → etiket (label)

### Worksheet 3 — Applying Thresholds in a Decision Rule
Type: Apply a given threshold to classify 3 foods
Concepts tested: threshold application, decision rule interpretation
The worksheet itself shows the worked example (Leo's rule: fat ≤ 8.0g = recommended)

Expected answers (applying fat ≤ 8.0g rule):
- Patlamış mısır (popcorn): tavsiye edilebilir, because fat ≤ 8.0g
- Elma (apple): tavsiye edilebilir, because fat ≤ 8.0g
- Patates kızartması (french fries): tavsiye edilemez, because fat > 8.0g
Second task: pre-service teacher picks any reasonable energy threshold with correct ≤ / > notation.

### Worksheet 4 — Searching for the Best Threshold Value
Type: Identify misclassified items, improve threshold placement, evaluate peer claim, state energy threshold
Concepts tested: threshold optimisation, equal feature values, misclassification reduction

Five response blanks (B1–B5):
- **B1:** Draw new threshold line between **avocado** and **french fries** (yeni eşik değeri)
- **B2:** Mark or write all **four** misclassified foods: jelibon, kraker, yulaf, avokado (order irrelevant; three foods not accepted)
- **B3:** State that **misclassification decreased** after the improved threshold
- **B4:** Pia is **haklı** because **apple and raspberry jam have the same fat value** (reject meta answers about classmates only)
- **B5:** Any learned **energy threshold from 160 to 2223** inclusive is correct

### Worksheet 5 — Trying Out Threshold Values
Type: Record outcomes of multiple threshold attempts using **11 ProDaBi food data cards** (`data/prodabi_food_cards.csv`)
Concepts tested: feature selection, threshold operators (≤/≥ vs strict </>), counting correct/misclassified cards, MCR

Structure: Grid per trial — variable + operator + value, correct count, error count, MCR.
- **N = 11** cards (salatalık … sütlü çikolata; green/red clips = label)
- **Full credit:** inclusive `≤`/`≥` and counts match reference confusion matrix; MCR = errors/11
- **Partial (0.5):** valid feature but strict `<`/`>` only — equality value left unclassified
- **Zero:** counts disagree with cards or MCR arithmetic wrong
- **B25:** best threshold with **lowest misclassification (error) count** among grid trials; flag when tied minima and only one named

### Worksheet 6 — Two-Level Decision Tree (Food Cards)
Type: Draw and label a **çift seviyeli** binary decision tree on **11 ProDaBi food cards** (`data/prodabi_food_cards.csv` — same as WS5)
Concepts tested: two features, threshold operators (≤/≥ vs strict), branch labels, leaf classes, tree validity

Structure: 13 OCR fields (B1–B13) → 8 rubric items. Python walks tree over food cards for MCR.
- **Full credit thresholds:** inclusive `≤`/`≥` on B2/B7 (strict `<`/`>` → partial 0.5, never full — same as WS5)
- **MCR=0 with two levels:** valid — not penalized
- **tree_structure:** requires inner split (2 levels), 2 features, paired operators, labeled leaves

### Worksheet 7 — Formulate Decision Rules
Type: Match paths (A, B, C) to written decision rules, then write own rules
Concepts tested: reading a tree as if-then rules, translating path logic to language

Correct matching (from the worksheet):
- Path A: "energy < 180 kcal → recommended"
- Path B: "energy ≥ 180 AND protein < 7.7 → not recommended"  
- Path C: "energy ≥ 180 AND protein ≥ 7.7 → recommended"
Pre-service teacher's own rules: evaluated on logical consistency with their WS6 tree.

### Worksheet 10 — Systematically Determine Threshold Value
Type: Compute misclassification count for each candidate threshold from a sorted list
Concepts tested: systematic threshold search, minimising misclassification

The worksheet gives candidate thresholds and a table to fill.
Correct answer: the threshold with the minimum misclassification count.
The energy values listed: 28, 69, 219, 346, 359, 408, 489
Pre-service teacher must find midpoints between adjacent values and count errors.
Optimal threshold: stated as a specific value (depends on the data cards used).

### Worksheet 11 — Evaluation
Type: Mixed — printed survey Q1–Q5 (satisfaction, recommendation, difficulty, self-assessment, topic enjoyment) + demographics Q6–Q7 (age, gender) + Likert attitude items + conceptual items + open-ended cognitive tasks
Most important items for AI-CFT assessment:

Q8: Use tree to classify strawberries → Acquire level (reading a tree)
Q10: What can DT do? (multiple select)
Correct: predict a feature's category, make decisions for new objects, model part of reality, determine recommendation status, understand how good decisions are
Wrong: create a meal plan, tell someone what to eat, predict what features an object has

Q11: Order the steps (1-4)
Correct order:
1 = Select a feature
2 = Arrange data by that feature
3 = Find a good threshold with few misclassifications
4 = Make a decision

Q12: Why is DT considered AI?
Correct: a computer can build DTs, it enables automatic decision-making
Wrong: computer thinks correctly, computer is as smart as a human, DT never makes mistakes

---

## Family 2: Worksheet DT (Plugged Phase — CODAP Arbor)

This is the primary assessment instrument for the CODAP Arbor phase.
It has 7 sections (A-G) and maps directly to the AI-CFT levels.

### Section A — Exploratory Feature Selection
Q1: Which variable(s) do you think predict recommendability? (prior belief, no analysis)
Type: Open-ended, no wrong answer. Evaluates initial hypothesis.

Q2: Which variables actually influence recommendability based on data exploration?
Type: Open-ended + graph evidence required.
Correct approach: pre-service teacher must reference a graph/visualisation, not just intuition.
Minimum acceptable: names at least one variable with a data-based reason.
Strong answer: names 2+ variables with graph-based justification.

Q3: Did you find a feature showing meaningful difference between recommended/not?
Type: Yes/No + explanation.
Correct: consistent with Q2, references the actual data.

Q4: Which variable would you use first in a prediction model? Why?
Type: Open-ended justification.
Correct: any variable is acceptable IF the justification references data 
(e.g. "energy because the graph showed the clearest separation").
Wrong: justification based only on general knowledge ("fat because fatty foods are unhealthy").

### Section B — Building and Comparing Single-Level Trees
Q1-Q3: Build three trees with different variables, record EMIT results each time.
Assessment: did the pre-service teacher actually emit (log evidence), record accuracy values, and try three different variables.

Q4: Which variable gave the best result? What criteria did you use?
Correct criteria: accuracy, misclassification rate, or TP/TN/FP/FN balance.
Wrong criteria: "it looked better" with no metric reference.

### Section C — Threshold Optimisation
Q1: Recall the best tree, try different threshold values, find the best.
Assessment: did threshold_change_count increase after this section (log evidence).

Q2: How does changing the threshold affect performance?
Correct: changing threshold moves the decision boundary, affecting how many items are correctly classified; too low or too high a threshold misclassifies more items.
Partial: "it changes accuracy" with no explanation of direction or mechanism.
Wrong: "it doesn't matter" or no answer.

Q3: Which threshold best separates recommended from not-recommended? How did you find it?
Correct: specific numeric threshold + method described (tried multiple values, compared accuracy, or used systematic midpoint approach).
Partial: specific threshold with no method explanation.
Wrong: threshold not matching their CODAP log data.

### Section D — Two-Level Tree
Q1: Add a second variable to create a depth-2 tree. Emit after.
Assessment: max_tree_depth_reached ≥ 2 in log, emit_count increased.

Q2: Did the second variable improve classification? How?
Correct: compares accuracy before and after second split, with specific numbers.
Partial: says "yes it improved" with no numbers.
Wrong: says it improved when their log shows accuracy dropped.

Q3: Which variable combination gave the best result?
Must be consistent with their CODAP log data.

Q4: How did you decide you reached the best tree?
Correct: references a stopping criterion (accuracy plateau, overfitting concern, comparison between trees).
Partial: "it had the highest accuracy" — acceptable if they actually compared.
Wrong: "I just stopped" or no criterion.

### Section E — Model Evaluation
Fill-in:
- Sensitivity (Duyarlılık): TP / (TP + FN)
- MCR (Hata Oranı): (FP + FN) / total
These must match their final EMIT log data exactly.

Q1: Which metric matters more for your model's purpose — sensitivity, MCR, or other?
Correct: any metric is acceptable IF justified with reference to the classification goal
(e.g. "sensitivity because missing a recommended food is worse than false alarms").

Q2: Did your model produce more false positives or false negatives?
Must match their TP/FP/TN/FN values from the final emit snapshot.

Q3: How does software decide when a DT is good enough?
Correct: references optimisation criterion (minimise error, maximise accuracy, use a threshold).
Partial: "when accuracy is high enough" — vague but not wrong.

Q4: Can a DT achieve perfect classification?
Correct: No — DT cannot always achieve zero misclassification because data may overlap or be noisy.
Wrong: Yes (any justification).

### Section F — Train/Test Evaluation
Q1: Apply best tree to test dataset. Emit and record.
Assessment: train_test_applied from log (True = attempted, False = did not switch datasets).
Note: for Food Dataset students this cannot be confirmed from log alone — screen recording required.

Q2: Compare test vs training performance. Explain differences.
Correct: test accuracy is usually lower; explains overfitting concept (model fitted training data too closely).
Partial: notes a difference without explaining why.
Wrong: claims identical performance without checking, or cannot explain the difference.

### Section G — Reflection
Q1: What did your DT model "learn"?
Correct: model learned patterns/rules from training data that distinguish recommended from not-recommended foods.
Partial: "it learned the data" — acceptable if they can specify what kind of pattern.

Q2: What did YOU learn while building DTs?
Open-ended, no wrong answer. Evaluates metacognitive awareness.
Rich answers: mention specific concepts (threshold, feature importance, overfitting, train/test).
Thin answers: "I learned how to use the program."

---

## AI-CFT Mapping Summary

| Worksheet | Section | AI-CFT Level Signal |
|---|---|---|
| WS1 | All | Acquire — basic concept recognition (LO3.1.2) |
| WS3, WS4 | All | Acquire — applying threshold rules (LO3.1.3, LO3.1.4) |
| WS7 | Path matching | Acquire — reading decision rules (LO3.1.2) |
| WS11 Q8, Q10-12 | All | Acquire — Basic AI techniques and applications (LO3.1) |
| WS DT A | Q2, Q4 | Acquire→Deepen — data-driven vs intuition-driven reasoning |
| WS DT B | Q4 | Deepen — comparing models with metrics (LO3.2.1) |
| WS DT C | Q2, Q3 | Deepen — threshold optimisation with method (LO3.2.1) |
| WS DT D | Q2, Q4 | Deepen/Create — stopping criterion, improvement justification |
| WS DT E | Fill-in | Acquire — metric computation |
| WS DT E | Q1, Q3, Q4 | Deepen — metric interpretation, limitations (LO3.2.2, LO3.3.1) |
| WS DT F | Q2 | Deepen/Create — train/test interpretation, overfitting (LO3.2.3, LO3.3.1) |
| WS DT G | Q1, Q2 | Create — reflection on model learning and own learning |

---

## What Is Still Needed

The PDFs in this folder are the question templates, not filled student responses.
To build the worksheet assessment agent (Phase 1) the following are needed:

1. The reference answer key — specific correct answers for each item above.
   For some items (WS DT B-F) the correct answer depends on which variable/threshold
   the pre-service teacher chose, so the key must be rule-based, not value-based.

2. Prior-year pre-service teacher responses — 3-5 examples per worksheet item showing:
   - a full-credit response
   - a partial-credit response  
   - a zero-credit response

3. For WS DT specifically: whether students submitted handwritten or typed responses,
   and in what format (photos, scans, Google Forms).
