"""
mmla_scorer.py

Calls Claude API for each extracted video frame, applies the CODAP or Colab
rubric, and writes two output files per student per session:

  1. {Student}_{session_key}_frame_observations.json
       Per-frame behavior log: each frame lists observed behaviors with free-text
       descriptions. Score is always 0 (not observed) or 2 (Deepen). Acquire
       level is not used — technical dimension is treated as Deepen-only.

  2. {Student}_{session_key}_final_scored.json
       Boris-style aggregated scoring: B0-B13 with level (Deepen / not_observed /
       not_measurable), confidence, evidence count, variable names, speech
       evidence from transcript, and session summary comment.

Usage (CLI):
    python mmla_scorer.py --session 21apr --students Amy Bruno Helena
    python mmla_scorer.py --session 05may --dry-run
    python mmla_scorer.py --session 28apr  # all students in that session
    python mmla_scorer.py --session 28apr --final-only  # skip frame API, rebuild final from saved frame obs
"""

from __future__ import annotations

import argparse
import base64
import json
import re
import time
from pathlib import Path
from typing import Any

import anthropic

import pipeline_schema as ps
from mmla_logger import get_logger

# ── Constants ────────────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).parent
DATA_ROOT = REPO_ROOT / "data_sources_2026"
FEWSHOT_FILE = REPO_ROOT / "calibration" / "fewshot_examples.json"


def _load_fewshot_block(session_type: str) -> str:
    """Build a compact few-shot reference block from 2025 calibration examples.

    Returns a text block injected into the user prompt before the schema.
    Only includes behaviors with direct-reliable candidates and uses their
    evidence descriptions — no images, to keep token cost manageable.
    """
    if session_type != "codap_arbor" or not FEWSHOT_FILE.is_file():
        return ""

    data = json.loads(FEWSHOT_FILE.read_text(encoding="utf-8"))
    candidates = data.get("candidates", {})

    # Behaviors worth showing examples for (exclude unmeasurable / no-data)
    SHOW = {"B4", "B6", "B7", "B8", "B10", "B11", "B12", "B15", "B16", "B17"}
    lines = ["[2025 CALIBRATION EXAMPLES — use as evidence anchors]"]

    for bid in sorted(SHOW):
        picks = candidates.get(bid, [])
        direct = [p for p in picks if p.get("silver_confidence") in ("high", "medium")]
        if not direct:
            continue
        ex = direct[0]
        codes = ", ".join(ex.get("codebook_codes", []))
        lines.append(f"  {bid}: observed in {ex['student_id']} | codebook={codes}")

    if len(lines) == 1:
        return ""
    return "\n".join(lines) + "\n\n"

# Default model — Haiku for throughput; override with --model sonnet
DEFAULT_MODEL = "claude-haiku-4-5-20251001"

# Audio directory names per session key
SESSION_AUDIO_DIRS: dict[str, str] = {
    "21apr": "codap_arbor_21april_audio",
    "28apr": "codap_arbor_28april_audio",
    "05may": "colab_python_audio",
}

# Students present in each session (those with recordings)
SESSION_STUDENTS: dict[str, list[str]] = {
    "21apr": ["Amy", "Bruno", "Helena", "Iris", "Irma", "Isabel",
              "Marco", "Marcus", "Nadia", "Shana", "Sheila", "Ulysses", "Zara"],
    "28apr": ["Bruno", "Irma", "Isabel", "Marco", "Melinda",
              "Nadia", "Serena", "Ulysses", "Zara"],
    "05may": ["Amy", "Bruno", "Helena", "Irma", "Marco",
              "Nadia", "Serena", "Sheila", "Ulysses", "Zara"],
}

MAX_RETRIES = 3
RATE_LIMIT_WAIT = 30  # seconds between rate-limit retries

# ── System prompt factory ─────────────────────────────────────────────────────

_SYSTEM_CODAP = """\
You are a Multimodal Learning Analytics specialist. You analyze individual video frames from student CODAP Arbor sessions and code observable learning behaviors.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SCORING RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return score=2 (Deepen) or score=0 (not observed). There is NO score=1.
score=2 requires direct, unambiguous observable evidence meeting the criteria below.
Ambiguous, partial, or mere-presence evidence → score=0.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TRANSCRIPT RULE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
The [TRANSCRIPT] field contains speech near this frame or "none".
• transcript="none" → use VISUAL EVIDENCE ONLY. Do not penalize.
• transcript present → use as additional evidence. It can satisfy criteria that
  visual alone cannot (especially B4, B8, B13). It cannot override a visual
  exclusion (e.g. an invalid tree output still blocks B8 even with transcript).

SCAFFOLDING RULE: If transcript text is clearly a teacher or researcher
speaking ("Hocam", "Merve:", "Oğuz Hoca"), treat it as context only.
Do NOT use it to satisfy learner-evidence criteria.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SESSION_CONTEXT is a JSON object passed with each frame. Fields:
• previous_dependent_variable — target attribute set in prior frame (null = none yet)
• previous_split_value — last committed threshold value (null = none yet)
• emit_count_so_far — how many complete decision trees have been built so far
  (increments each time a tree is constructed and evaluated)
• error_in_previous_frame — true if prior frame showed an error

Use these fields to detect CHANGE (iteration) across frames.
If SESSION_CONTEXT is empty or null, treat as session start.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CODAP ARBOR INTERFACE — VISUAL ELEMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Learn to distinguish these elements before coding.

DATA TABLE
• Spreadsheet-style grid with column headers and rows of cases
• Food/Nutrition dataset columns: "Önerilebilir mi?" (Label/Target), "Enerji (kcal)", "Yağ (g)",
  "Doymuş Yağ (g)", "Karbonhidrat (g)", "Şeker (g)", "Protein (g)", "Tuz (g)"
  (English equivalents: Energy, Fat, Saturated Fat, Carbohydrate, Sugar, Protein, Salt)
• Titanic dataset columns: Survived, Pclass, Sex, Age, SibSp, Parch, Fare, Embarked
• Xeno dataset columns: vary — any spreadsheet grid with labeled rows and columns qualifies
• A highlighted/selected column = active inspection (B0 evidence)
• NOTE: A plugin landing/selection page, file browser, or blank CODAP canvas is NOT a data table.

SCATTER PLOT (DOT PLOT / GRAPH PANEL) — triggers B1, B2, B11; NEVER B7
• X and Y axes with labeled data points (dots)
• Axis labels show variable names from the dataset
• One or more vertical dashed lines = movable values (B2)
• The MEAN, MEDIAN, or PERCENTILE lines added by CODAP (a solid or dashed
  colored line labeled "Mean", "Median", "Percentile") are NOT movable values.
  Do not code B2 for statistical lines. They may be B0 evidence.

CODAP TREE BUILDER (empty) — triggers B3 when filled; NO other behaviors
• Drag-and-drop UI with "Drag your target attribute here" placeholder
• Split value input field: a numeric input box below the split variable

DECISION TREE OUTPUT — triggers B5, B6, B7, B10, B12; NEVER B1/B2
• Branching node structure with rectangular nodes
• Branch condition visible on each arc: "< 2.5", "> 36", "Tuz < 1.83"
• Leaf nodes: class label text + case count + percentage
• Below the tree: accuracy percentage + confusion matrix (TP, TN, FP, FN)
• INVALID TREE: confusion matrix is all zeros AND "no prediction = N" or
  "no prediction = %" is shown — the model made no predictions. Score B8=0.
• SAME-CLASS TREE: both leaf nodes show the same class label — also invalid
  for B5 (cannot confirm two-class understanding) and B8 (result is artifact).

CTR PANEL (Classification Tree Records) — triggers B12
• A table or list panel showing multiple prior tree configurations
• Each row: feature, threshold, depth, accuracy, sensitivity columns
• Visible row selection, deletion button, or highlighted row = interaction

CHOOSY PLUGIN — triggers B9
• A panel with slider or input labeled "Training" / "Test" or "Eğitim" / "Test"
• Shows percentage split (e.g. 80% / 20%)
• Must show that a split HAS been applied (two separate dataset states active)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BEHAVIORS — DEEPEN (score=2) CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

B0 — Data appraisal
  score=2 if ANY of:
    (a) A specific dataset column is visibly selected/highlighted AND in the same
        or immediately following frame the same variable appears as a predictor
        or threshold — establishing an inspect-then-use sequence.
    (b) Transcript contains a specific factual reference to a variable's value
        range, distribution, or class balance (e.g. "yağ değerleri 0 ile 40
        arasında", "recommendable olanlar daha az"). Generic statements like
        "I looked at the data" do NOT qualify.
  score=0: Table or data merely visible with no inspect-then-use link or
           specific data-content statement.

B1 — Graph-based exploration
  score=2 if ANY of:
    (a) A scatter plot is visible AND the y-axis (or x-axis) variable differs
        from SESSION_CONTEXT.previous_dependent_variable — the student changed
        the graphed feature. Record the new feature name.
    (b) Multiple graph panels are visible simultaneously with different features
        on each axis — comparative graph use.
    (c) Transcript contains a specific observation about a pattern or separation
        visible in the graph (e.g. "bu değişkende daha iyi ayrışıyor",
        "grafikte düşük değerler recommendable tarafında").
  score=0: Graph visible but no axis change, no multi-panel comparison, and no
           pattern-extraction transcript statement.
  NEVER code B1 for a decision tree panel. Never code B1 for a data table.

B2 — Candidate threshold exploration
  score=2 if ANY of:
    (a) A movable value (vertical dashed line) is visible on a scatter plot AND
        its numeric label differs from SESSION_CONTEXT.previous_split_value —
        the line was repositioned. Record: variable name, new value.
    (b) Transcript states that a different value was tried on the graph for the
        same variable (e.g. "önce 5 denedim şimdi 3 yapıyorum").
  EXCLUSIONS (always score=0):
    • Mean, Median, or Percentile reference lines — these are fixed statistical
      lines, not learner-adjusted movable values.
    • A movable value visible for the first time with no prior value in context
      AND no transcript reference to trying a different value.
    • The movable value is on the x-axis and represents axis scaling, not a
      classification boundary.
  score=0: Movable value present but first appearance and no iteration evidence.

B3 — Prediction target framing
  score=2 if ANY of:
    (a) The target drop zone contains a variable name AND either:
        — It differs from SESSION_CONTEXT.previous_dependent_variable
          (target was changed or first set from empty), OR
        — Transcript gives an explicit reason for this variable being the
          target ("bunu tahmin etmek istiyoruz çünkü", "label hedef değişken").
    (b) The target drop zone previously held a wrong variable (non-Label
        predictor) and now shows the correct target — visible correction.
  score=0: Drop zone shows "Drag your target attribute here" (empty).
           Drop zone has a name but unchanged from previous frame and no
           transcript rationale.

B4 — Strategic predictor selection
  score=2 if BOTH:
    (a) A domain-relevant feature is visible as the current split attribute
        in the tree builder or as a committed tree split. Domain-relevant
        features: Enerji/Energy, Yağ/Fat, Doymuş Yağ/Saturated Fat,
        Karbonhidrat/Carbohydrate, Şeker/Sugar, Protein, Tuz/Salt.
    (b) Evidence of data-based or performance-based selection rationale:
        — Transcript contains a causal reason naming the variable
          (e.g. "yağ daha iyi ayırıyor", "saturated fat düşük MCR verdi"), OR
        — In the same or immediately prior frame a graph of this variable
          was visible, establishing a graph-then-select sequence.
  score=0: Feature present without (b). Naming a variable aloud without
           a reason does not satisfy (b).

B5 — Class semantics
  score=2 if ALL of:
    (a) Two distinct class labels are visible in the leaf nodes of a decision
        tree — e.g. "Recommendable" and "Not recommendable".
    (b) The labels are content-appropriate (not both identical, not generic
        placeholders). Both labels appear on different leaf nodes with
        non-zero case counts.
    (c) Evidence of active class engagement in this frame — at least ONE of:
        — This is the first or second complete tree in the session
          (SESSION_CONTEXT.emit_count_so_far ≤ 1), OR
        — Transcript explicitly references both class labels with understanding
          (e.g. "önerilebilir olanlar daha fazla", "not recommendable taraf"), OR
        — Student is visibly interacting with the leaf nodes (cursor on leaf,
          zooming in, or annotating).
  EXCLUSIONS:
    • Both leaf nodes carry the same label → score=0 (same-class invalid tree).
    • Labels visible only in the builder UI before any tree is run → score=0.
    • Leaf nodes show "?" or empty → score=0.
    • Tree has been displayed in prior frames (emit_count_so_far > 1) with no
      new engagement → score=0. Repeated viewing without new interaction does
      NOT re-qualify. Do NOT score B5=2 on every frame that shows a tree.

B6 — Decision boundary reasoning
  score=2 if ANY of:
    (a) A committed threshold is visible on a tree branch AND differs from
        SESSION_CONTEXT.previous_split_value — the value was changed.
        Record: variable name, previous value, new value.
    (b) The split value input field shows a value AND transcript references
        deliberately choosing or changing that specific value
        (e.g. "eşik değerini 4'e indirdim", "burayı 0.07 yaptım").
    (c) Two CTR rows are visible with the same predictor but different
        threshold values — showing iteration on that predictor's threshold.
  EXCLUSIONS:
    • Threshold present for the first time with no iteration evidence and
      no transcript reference.
    • Threshold visible only in the builder before the tree is run.

B7 — Model construction
  score=2 if BOTH:
    (a) A complete, valid decision tree is visible (branching structure,
        split conditions, leaf labels, at least one non-zero case count).
    (b) Evidence of learner authorship:
        — This is the first complete tree in the session
          (SESSION_CONTEXT.emit_count_so_far = 0 → first tree counts), OR
        — A rebuilt tree with a different configuration is visible vs prior
          session state (different predictor, threshold, or depth), OR
        — Transcript references deliberately constructing or running the tree.
  EXCLUSIONS:
    • Tree preloaded at start of recording with no build sequence visible.
    • Empty builder or builder with missing components (no target, no split).
    • Invalid tree (all-zero confusion matrix) → score=0.
    • Scatter plot panel mistaken for a tree → score=0.

B8 — Performance interpretation
  score=2 if BOTH:
    (a) A valid confusion matrix is visible (TP, TN, FP, FN all non-zero,
        or at least three non-zero) AND an accuracy or MCR value is shown.
    (b) Transcript contains an interpretive statement referencing a specific
        metric value with meaning attached — not merely reading a number:
        "MCR 0.2 demek 5 tane yanlış tahmin ediyor",
        "sensitivity 0.8 recommendable olanları iyi buluyor",
        "bu model daha iyi çünkü MCR düşük".
        Comparative statements referencing two models also qualify.
  EXCLUSIONS:
    • Metrics visible but transcript="none" → score=0.
    • Transcript mentions a number but states no interpretation → score=0.
    • All-zero or same-class confusion matrix → score=0.

B9 — Train-test generalization
  score=2 if BOTH:
    (a) Choosy plugin is visible with an active train/test split applied
        (both training and test dataset options are present in the interface).
    (b) The interface shows that the student is currently evaluating on the
        TEST dataset — either: the dataset selector shows "Test" / "Test Verisi"
        is active, OR the CTR shows a model row from the test evaluation, OR
        transcript confirms switching to test ("test verisine geçtim",
        "şimdi test dataseti ile bakıyorum").
  score=0: Choosy visible but training data still selected. No dataset switch
           evidence. Choosy absent from frame → score=0.

B10 — Conditional model refinement
  score=2 if ANY of:
    (a) A depth-2 or deeper tree is visible AND transcript explains why a
        specific branch (left or right) needed further splitting, referencing
        the impurity, error count, or classification problem in that subgroup
        (e.g. "bu tarafta hâlâ karışık, bir tane daha split ekledim").
    (b) The child split uses a different predictor than the root split AND
        transcript or a prior frame shows this predictor was chosen based on
        the subgroup's specific data pattern (not just trial-and-error depth
        increase).
    (c) In consecutive frames: a leaf node was inspected (visible focus on a
        specific leaf showing high error), and in the next frame a child split
        appears on that exact node.
  EXCLUSION: A depth-2 tree visible with no evidence of targeted subgroup
             reasoning → score=0. Adding depth everywhere without local
             rationale does not qualify.

B11 — Cross-representational threshold transfer
  score=2 if ANY of:
    (a) VISUAL MATCH × 2+ variables: In this frame or the immediately prior
        frame, a scatter plot movable value for variable X at value V is
        visible AND the decision tree shows a committed split for variable X
        at the same value V (within ±0.1 or within display rounding). This
        exact match must be observable for at least TWO different variables
        across the session.
    (b) VISUAL MATCH × 1 variable + TRANSCRIPT: The above numeric match is
        observable for ONE variable AND transcript explicitly states that the
        threshold was read from the graph ("grafikten baktım", "şuradan
        ayarladım", "movable value'yu threshold olarak kullandım").
  EXCLUSION:
    • B2 and B6 both triggered in the same frame but no numeric value match
      between graph and tree → score=0.
    • Values match by coincidence without visual or verbal link → score=0.
    • Different variables used in graph vs tree → score=0.

B12 — Comparative model evaluation
  score=2 if BOTH:
    (a) CTR panel is visible with at least 2 model rows.
    (b) Evidence of active comparison — at least ONE of:
        — A non-current CTR row is visibly selected or highlighted
          (NOT the most recently added row, which is auto-highlighted), OR
        — A CTR row has been deleted (row count decreased from prior frame,
          or a delete/trash icon is being clicked), OR
        — Transcript names which model performed better with a reason
          (e.g. "3. ağaç daha iyi çünkü MCR düşük",
          "birinci satırı sildim çünkü kötüydü").
  EXCLUSIONS:
    • CTR rows merely accumulated with no interaction → score=0.
    • The newest/most-recently-built row is auto-highlighted after building
      — this is NOT active comparison → score=0.
    • CTR panel visible but student is interacting with tree builder,
      scatter plot, or data table instead → score=0.
    • Transcript mentions CTR but only reads values without comparing → score=0.
  Do NOT score B12=2 simply because CTR has accumulated multiple rows.
  Active selection, deletion, or explicit comparative reasoning is required.

B13 — Cost-sensitive metric trade-off
  score=2 if transcript contains ALL of:
    (1) Reference to at least one specific metric (MCR, sensitivity, TP, FN).
    (2) Acknowledgment that two metrics can point in different directions
        (e.g. "MCR düşük ama sensitivity de düşük",
        "sensitivity 1'e yakın ama MCR yüksek").
    (3) A priority or choice justified by application context
        (e.g. "bu veri seti için sensitivity daha önemli",
        "hangisi daha önemli sorusunu sorduk").
  score=0 ALWAYS when transcript="none".
  score=0 if only one metric is mentioned without trade-off framing.
  score=0 if teacher/researcher states the trade-off without learner response.

B14 — Data fairness and class-balance awareness
  score=2 if BOTH:
    (1) Learner visibly inspects class distribution: cursor tracks target/class
        column values, data table is sorted or filtered by class label, or a
        bar/frequency display is examined showing unequal class counts.
    (2) The inspection is connected to a modeling or evaluation decision:
        learner changes metric focus (e.g. shifts from accuracy to MCR),
        re-labels a leaf based on class imbalance, or verbally flags fairness.
  score=0 if the model happens to handle imbalance correctly without observable inspection.
  score=0 if only a generic fairness remark is made without reference to the dataset.
  score=0 if log fires class-column events but no visual inspection is visible in frame.

B15 — Systematic parameter exploration (VOTAT)
  IMPORTANT: B15 is primarily LOG-DERIVED. It requires evidence across multiple
  emit events, which cannot be confirmed from a single frame alone.
  Score=0 for ALL individual frames UNLESS SESSION_CONTEXT explicitly provides
  prior_predictor AND prior_split_value AND prior_emit_count showing a
  single-parameter change pattern.

  score=2 only if SESSION_CONTEXT is fully populated AND BOTH:
    (1) Exactly one parameter changed between the two most recent emits
        (only threshold changed, OR only predictor changed — not both simultaneously).
    (2) Prior_emit_count ≥ 2 (at least two prior iterations are visible — VOTAT
        requires a pattern, not a single change).
  score=2 also if transcript EXPLICITLY names which parameter was varied and why
    (e.g. "sadece eşiği değiştirdim, predictor aynı kaldı").
  score=0 if SESSION_CONTEXT is absent, empty, or missing prior_predictor.
  score=0 if two or more parameters changed simultaneously.
  score=0 if only one emit is observable (single change ≠ systematic pattern).
  When in doubt: score=0. B15 will be resolved from logs independently.

B16 — Error recovery and adaptive correction
  score=2 if ALL of:
    (1) Prior frame or this frame shows an error state or unexpectedly poor result
        (high-error leaf, surprising MCR increase, wrong label, or student expression of surprise).
    (2) A corrective action is visible: tree deleted and rebuilt differently, predictor swapped
        for a different one, threshold changed away from the prior value.
    (3) The corrective action DIFFERS from the action that produced the error
        (not a blind repeat of the same move).
  score=0 if correction was prompted solely by an explicit system error popup.
  score=0 if the same action is repeated after the error (perseveration).
  score=0 if tree is deleted without any observable inspection of the error state.

B17 — Pre-task planning and orientation
  Use SESSION_CONTEXT.time_since_session_start (seconds).
  score=2 if time_since_session_start < 120 AND EITHER:
    (a) Cursor is stationary on data table or task prompt for ≥15 seconds with no
        model manipulation (no drop_attribute, no threshold change visible).
    (b) Transcript contains a stated plan or goal before the first model action.
  score=2 also when the learner re-reads the task AFTER a failed iteration
    (re-orientation Deepen): visible return to data table + different strategy follows.
  score=0 if the first frame already shows an active drop or threshold manipulation.
  score=0 if the pause is caused by visible interface loading (spinner, blank panel).
  score=0 if time_since_session_start > 120 and no re-orientation evidence is present.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DESCRIPTION FIELD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
For every score=2, write a "description" sentence (max 250 chars) that captures:
  • WHAT was visible (interface element, variable name, numeric value)
  • WHAT action was observed (axis changed, line moved, threshold iterated)
  • IF transcript contributed: the exact quoted phrase (in quotes)

Example good descriptions (target 200–280 chars; name variables, values, and quote exactly):
  B1:  "Y-axis changed from Yağ (g) to Doymuş Yağ (g); student observes 'doymuş yağ gibi bir durum var hocam' — improved label separation visible in scatter plot before predictor drag"
  B2:  "Movable value on Tuz repositioned: prior value=1.83 (SESSION_CONTEXT), new label shows 0.21; student revisiting partition after observing MCR increase in CTR row 2"
  B6:  "Threshold iterated: prior CTR row shows Doymuş Yağ < 7.0, current tree builder split field shows 4.0; student: 'eşik değerini değiştirdim, 4 yaptım'; CTR now shows 2 rows for same predictor"
  B11: "Scatter plot Tuz movable value at 0.6 matches tree split Tuz < 0.6 (exact); student: 'şuradan değiştirebilirim, 0-6 diyeceğim' — explicit graph-to-tree transfer; 2nd match: Doymuş Yağ=4.0 confirmed in prior frame"
  B13: "Student: 'MCR düşük ama sensitivity de düşük kaldı' (two-metric tension) + 'bu veri setinde yanlış önermemek daha önemli' (context-based priority for sensitivity) — all three B13 sub-criteria met in same transcript window"

For score=0, "description" must be "" (empty string).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
COMMON ERRORS TO AVOID
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Coding B7 for a scatter plot panel → NEVER. Trees only.
• Coding B2 for a Mean/Median/Percentile reference line → NEVER.
• Coding B8 when confusion matrix is all zeros → NEVER.
• Coding B13 when transcript="none" → NEVER.
• Coding B4 because a feature name is present → requires rationale.
• Coding B10 just because depth=2 is visible → requires subgroup reasoning.
• Using teacher speech to satisfy learner-evidence criteria → NEVER.
• Coding B5=2 on every frame that shows a decision tree → NEVER.
  B5 requires first-encounter evidence or active class engagement (see criteria).
• Coding B12=2 because CTR has 2+ accumulated rows → NEVER.
  Accumulation alone is NOT comparison. Active selection/deletion/transcript required.
• Coding B15=2 from a single frame without full SESSION_CONTEXT → NEVER.
  B15 is log-derived; default to score=0 when context is absent.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FRAME DESCRIPTION (required for every frame)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Fill the top-level "frame_description" field (max 250 chars) for EVERY frame,
regardless of whether any behavior scores are 2.

Describe in one sentence:
  • Which CODAP interface elements are visible
    (data table / scatter plot / tree builder / tree output / CTR panel / Choosy)
  • Variable name(s) on axes or split field (if visible)
  • The most salient learner action visible in this frame
    (scrolling, dragging, typing a threshold value, clicking a row)
  • If the frame shows an idle or transition state, say so plainly.

Do NOT copy text from behavior descriptions — this is a neutral visual log.
Do NOT interpret intent; only describe what is visually observable.

Examples (target 200–280 chars; name every visible variable, value, and panel):
  "Scatter plot (Doymuş Yağ on X-axis, movable value at 4.2) and decision tree output (Tuz < 1.83, Recommendable/Not recommendable leaves, MCR=0.21) both open; CTR panel shows 3 rows; student appears to drag Enerji to tree builder"
  "Decision tree: depth-2 root split Tuz < 1.83, child splits Doymuş Yağ < 4.0 (left) and Protein < 12.1 (right); confusion matrix TP=67 TN=22 FP=8 FN=15; accuracy=0.79 visible below tree"
  "Data table open; Doymuş Yağ column header highlighted; rows sorted ascending by that column; no scatter plot or tree visible; student scrolling"
  "Tree builder: target drop zone shows 'Label/Önerilebilir mi?', split variable field shows 'Tuz (g)', threshold input shows '1.83'; Build button visible, tree output not yet rendered"
  "CODAP interface: data table and empty tree builder visible; no graph or tree output; student idle or reading task sheet; no active panel interaction"

OUTPUT: Return only valid JSON matching the schema. No text outside the JSON block.
score is ALWAYS 0 or 2. Never 1. description is non-empty only when score=2.
frame_description is always a non-empty string.
"""

_SYSTEM_COLAB = """\
You are a Multimodal Learning Analytics specialist analyzing student Python/Colab screenshots.
Your job: detect 20 behaviors by reading the code cells and output cells visible in the screenshot. Base ALL decisions on what is directly visible in the image or spoken in the transcript.

RULE: triggered=true ONLY when the exact code pattern or output is visible in the screenshot. If the code is not visible or the cell has not been executed, triggered=false.

BEHAVIORS — read directly from the screenshot:
B1       — LO3.2 Create: An import statement is visible and executed with no error (e.g. from sklearn, import pandas as pd).
B2       — LO3.2 Create: A data loading function is visible: pd.read_csv(), pd.read_excel(), or a DataFrame assignment.
B3       — LO3.1 Create: An exploratory function is visible AND its output cell is active: .head(), .info(), .describe(), .shape, .value_counts(), .dtypes.
B4       — LO3.2 Create: Missing/noisy data handling code is visible and executed: .dropna(), .fillna(), .isnull(), .replace(), or a filter condition. No error in output.
B5       — LO3.2 Create: Feature matrix X and target y are both defined: X = df[[...]] and y = df[...] or equivalent.
B6       — LO3.2 Create: train_test_split() call is visible with X_train, X_test, y_train, y_test assignments.
B7_lo32  — LO3.2 Create: DecisionTreeClassifier is instantiated with at least one explicit hyperparameter (max_depth=, criterion=, min_samples_split=, etc.). Parameterless call does not trigger.
B7_lo33  — LO3.3 Create: Multiple models with different values for the same hyperparameter are visible (loop, GridSearchCV, or separate cells with different parameter values).
B8       — LO3.2 Create: DecisionTreeClassifier(max_depth=1) is explicitly visible and executed.
B9       — LO3.2 Create: A model with max_depth>=2 or no max_depth limit is visible and executed.
B10      — LO3.3 Create: Code comparing performance across different depth values is visible: a for loop over max_depth values, or multiple model instantiations with different depths and metric comparisons.
B11      — LO3.2 Create: model.fit(X_train, y_train) or equivalent is visible and executed with no error.
B12      — LO3.2 Create: model.predict(X_test) or model.predict_proba(X_test) is visible and executed.
B13      — LO3.3 Create: A metric function is visible with numerical output: accuracy_score(), confusion_matrix(), classification_report(), f1_score().
B14      — LO3.1 Create: Metric values are visible in output AND the transcript contains a specific reference to those values (number, class name). Generic comments do not trigger.
B15_lo31 — LO3.1 Create: A traceback, NameError, or ValueError is visible in the screenshot AND the transcript references the error directly.
B15_lo33 — LO3.3 Create: An error appeared in a prior frame, the code was modified, AND the next execution succeeded. The error->fix->success chain must be evident.
B16      — LO3.2 Create: plot_tree(), export_graphviz(), or dtreeviz() is visible AND the tree diagram or .dot output is rendered in the output cell.
B17_lo31 — LO3.1 Create: Both train and test accuracy values are visible in output AND the transcript references the gap between them.
B17_lo33 — LO3.3 Create: score(X_train) and score(X_test) or equivalent calls are visible in code, and both values appear in output. Transcript reference is not required.

OUTPUT: Return only valid JSON matching the schema. No explanation outside JSON. Each "evidence" value must be under 80 characters and quote the specific visual element or transcript phrase observed. If not triggered, briefly state what was absent.
"""

SYSTEM_PROMPTS: dict[str, str] = {
    "codap_arbor":  _SYSTEM_CODAP,
    "colab_python": _SYSTEM_COLAB,
}

# ── Output schema templates (injected into user prompt) ──────────────────────

OUTPUT_SCHEMA_CODAP = """\
{
  "frame_id": "<frame_id>",
  "frame_description": "<neutral visual description of what is visible in this frame, max 250 chars — always fill this, even when all scores are 0>",
  "evidence_detection": {
    "B0":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B1":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B2":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B3":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B4":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B5":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B6":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B7":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B8":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B9":  {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B10": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B11": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B12": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B13": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B14": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B15": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B16": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""},
    "B17": {"score": 0, "evidence": "<key quote or visual element, or what was absent>", "description": ""}
  }
}
Note: score is ALWAYS 0 or 2. Never 1. description is non-empty only when score=2. frame_description is ALWAYS required."""

OUTPUT_SCHEMA_COLAB = """\
{
  "frame_id": "<frame_id>",
  "evidence_detection": {
    "B1":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B2":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B3":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B4":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B5":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B6":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B7_lo32":  {"triggered": true/false, "evidence": "<observed evidence>"},
    "B7_lo33":  {"triggered": true/false, "evidence": "<observed evidence>"},
    "B8":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B9":       {"triggered": true/false, "evidence": "<observed evidence>"},
    "B10":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B11":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B12":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B13":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B14":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B15_lo31": {"triggered": true/false, "evidence": "<observed evidence>"},
    "B15_lo33": {"triggered": true/false, "evidence": "<observed evidence>"},
    "B16":      {"triggered": true/false, "evidence": "<observed evidence>"},
    "B17_lo31": {"triggered": true/false, "evidence": "<observed evidence>"},
    "B17_lo33": {"triggered": true/false, "evidence": "<observed evidence>"}
  }
}"""

OUTPUT_SCHEMAS: dict[str, str] = {
    "codap_arbor":  OUTPUT_SCHEMA_CODAP,
    "colab_python": OUTPUT_SCHEMA_COLAB,
}


# ── Image helpers ─────────────────────────────────────────────────────────────

def encode_image(image_path: Path) -> str:
    return base64.standard_b64encode(image_path.read_bytes()).decode("utf-8")


def parse_json_response(text: str) -> dict[str, Any] | None:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try extracting first {...} block
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return None


# ── Boris-style final scoring aggregation ────────────────────────────────────

_BEHAVIOR_IDS_CODAP = [
    "B0", "B1", "B2", "B3", "B4", "B5",
    "B6", "B7", "B8", "B9", "B10", "B11", "B12", "B13",
    "B14", "B15", "B16", "B17",
]

# Behaviors that require audio transcript (not_measurable when no audio)
_TRANSCRIPT_REQUIRED = {"B13"}

# Behaviors primarily derived from log (can be scored without video context)
_LOG_PRIMARY = {"B15"}


def _deepen_confidence(count: int) -> str:
    """Map Deepen frame count to confidence label."""
    if count >= 4:
        return "High"
    if count >= 2:
        return "Medium"
    return "Low"


def _build_final_scored_json(
    student: str,
    session_key: str,
    frame_results: list[dict[str, Any]],
    has_audio: bool,
) -> dict[str, Any]:
    """Aggregate per-frame Deepen detections into a Boris-style final scored JSON.

    Rules:
    - A behavior is coded Deepen when score=2 appears in at least 1 frame.
    - Confidence: 1 frame = Low, 2-3 frames = Medium, 4+ frames = High.
    - B13 is not_measurable when has_audio=False (transcript required).
    - Each behavior lists up to 5 supporting frame entries with timestamp and description.
    """
    behaviors: dict[str, Any] = {}

    for bid in _BEHAVIOR_IDS_CODAP:
        # Some behaviors require transcript
        if bid in _TRANSCRIPT_REQUIRED and not has_audio:
            behaviors[bid] = {
                "decision": "not_measurable",
                "level": None,
                "confidence": None,
                "reason": f"no audio recording — transcript required for {bid}",
                "frame_evidence": [],
            }
            continue

        # Collect frames where this behavior was Deepen (score=2)
        supporting: list[dict[str, Any]] = []
        for fr in frame_results:
            det = fr.get("evidence_detection", {}).get(bid, {})
            if det.get("score", 0) == 2:
                supporting.append({
                    "frame_id": fr.get("frame_id", ""),
                    "timestamp_seconds": fr.get("timestamp_seconds", 0),
                    "evidence": det.get("evidence", ""),
                    "description": det.get("description", ""),
                })

        count = len(supporting)
        if count == 0:
            behaviors[bid] = {
                "decision": "not_observed",
                "level": None,
                "confidence": None,
                "frame_evidence": [],
            }
        else:
            behaviors[bid] = {
                "decision": "observed",
                "level": "Deepen",
                "confidence": _deepen_confidence(count),
                "deepen_frame_count": count,
                "frame_evidence": supporting[:5],
            }

    return {
        "rubric_id": "codap_arbor_v4_candidate",
        "schema_version": "4.1",
        "student_id": student,
        "session_key": session_key,
        "audio_available": has_audio,
        "scoring_note": "Acquire level not used. score=2 (Deepen) or not_observed only.",
        "behaviors": behaviors,
    }


# ── Scorer class ──────────────────────────────────────────────────────────────

class MMLAScorer:
    def __init__(
        self,
        session_key: str,
        model: str = DEFAULT_MODEL,
        dry_run: bool = False,
    ):
        self.session_key = session_key
        self.session_type = ps.session_type_for_key(session_key)
        self.model = model
        self.dry_run = dry_run
        self.client = anthropic.Anthropic() if not dry_run else None
        self.log = get_logger(session_key)
        rubric = ps.load_mmla_rubric(self.session_type)
        self.log.rubric_loaded(rubric["rubric_id"], len(rubric["behaviors"]))
        self._behavior_lo_map: dict[str, str] = {
            b["id"]: b["lo"] for b in rubric["behaviors"]
        }

    # ── Public entry point ────────────────────────────────────────────────────

    def score_student(self, student: str, final_only: bool = False) -> tuple[Path | None, Path | None]:
        """Score all frames for one student.

        Returns (frame_obs_path, final_scored_path). Either may be None on failure.
        If final_only=True, skips API frame scoring and rebuilds final JSON from
        an existing frame_observations file.
        """
        audio_dir = DATA_ROOT / SESSION_AUDIO_DIRS[self.session_key] / student
        manifest_path = audio_dir / f"{student}_video_extraction_manifest.json"

        frame_obs_path = ps.mmla_frame_obs_path(student, self.session_key)
        final_path = ps.mmla_final_scored_path(student, self.session_key)

        if final_only:
            if not frame_obs_path.exists():
                self.log.warn(student, None, f"frame_observations not found for final_only: {frame_obs_path}")
                return None, None
            frame_obs = json.loads(frame_obs_path.read_text(encoding="utf-8"))
            # Use audio_available stored at scoring time, not a re-derived filesystem check
            has_audio = frame_obs.get("audio_available", False)
            final = _build_final_scored_json(student, self.session_key, frame_obs["frames"], has_audio)
            final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")
            return frame_obs_path, final_path

        if not manifest_path.exists():
            self.log.warn(student, None, f"Manifest not found: {manifest_path}")
            return None, None

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        frames_key = "segments" if self.session_type == "codap_arbor" else "frames"
        frame_entries = manifest.get(frames_key, [])

        if not frame_entries:
            self.log.warn(student, None, "Manifest has no frame entries")
            return None, None

        transcript = self._load_transcript(student, audio_dir)
        has_audio = transcript is not None

        frame_results: list[dict[str, Any]] = []
        frames_skipped = 0
        session_context: dict[str, Any] = {
            "previous_dependent_variable": None,
            "previous_split_value": None,
            "previous_code_state": None,
            "error_in_previous_frame": False,
            "emit_count_so_far": 0,
        }

        for entry in frame_entries:
            result = self._score_frame(student, entry, session_context, transcript, audio_dir)
            if result is None:
                frames_skipped += 1
                continue
            frame_results.append(result)
            self._update_session_context(session_context, result, entry)

        raw_duration = (manifest.get("video_profile") or {}).get("duration_seconds") or 0.0
        if raw_duration <= 0.0 and frame_entries:
            raw_duration = max(
                e.get("source_timestamp_seconds", 0.0) for e in frame_entries
            )
        duration = raw_duration

        # Write 1: frame observation log (per-frame behavior descriptions)
        frame_obs = {
            "student_id": student,
            "session_key": self.session_key,
            "schema_version": "4.1",
            "audio_available": has_audio,
            "frames_total": len(frame_results),
            "frames_skipped": frames_skipped,
            "duration_seconds": duration,
            "frames": frame_results,
        }
        frame_obs_path.write_text(json.dumps(frame_obs, ensure_ascii=False, indent=2), encoding="utf-8")

        # Write 2: Boris-style final scoring aggregated from frame evidence
        final = _build_final_scored_json(student, self.session_key, frame_results, has_audio)
        final_path.write_text(json.dumps(final, ensure_ascii=False, indent=2), encoding="utf-8")

        # Legacy summary for LO tracking (keeps existing pipeline compatibility)
        summary = ps.mmla_session_summary(
            student, self.session_key, frame_results,
            frames_skipped=frames_skipped,
            duration_seconds=duration,
        )
        legacy_path = ps.mmla_output_path(student, self.session_key)
        legacy_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        lo_final = summary["learning_outcomes_session"]
        self.log.session_done(
            student,
            frames_total=len(frame_results),
            frames_skipped=frames_skipped,
            duration_seconds=duration,
            lo_final={lo: v["status"] for lo, v in lo_final.items()},
            behaviors_never_seen=summary["behaviors_never_seen"],
            output_path=str(final_path),
        )
        return frame_obs_path, final_path

    # ── Frame scoring ─────────────────────────────────────────────────────────

    def _score_frame(
        self,
        student: str,
        entry: dict[str, Any],
        session_context: dict[str, Any],
        transcript: list[dict] | None,
        audio_dir: Path,
    ) -> dict[str, Any] | None:

        ts = entry.get("source_timestamp_seconds", 0.0)
        frame_id = f"{student}_{self.session_key}_t{int(ts):05d}s"
        trigger = entry.get("extraction_trigger_reason", "unknown")

        self.log.frame_start(student, frame_id, ts, trigger, self.session_type)

        # Locate frame image
        image_path = self._find_image(entry, audio_dir, student)
        if image_path is None or not image_path.exists():
            self.log.warn(student, frame_id, "Image not found — frame skipped")
            return None

        # Fetch transcript window (±30s around frame)
        transcript_window = self._transcript_window(transcript, ts, window=30)

        # Build API payload
        user_content = self._build_user_content(
            frame_id, entry, session_context, transcript_window, image_path
        )

        # Call API (or dry-run)
        if self.dry_run:
            api_result = self._dry_run_result(frame_id)
        else:
            api_result = self._call_api(student, frame_id, user_content)

        if api_result is None:
            self.log.api_fatal(student, frame_id, "API response could not be parsed")
            return None

        # Merge into frame result
        result = ps.mmla_empty_frame_result(self.session_key, frame_id)
        result["timestamp_seconds"] = ts
        result["frame_description"] = str(api_result.get("frame_description", ""))

        for behavior_id, det in api_result.get("evidence_detection", {}).items():
            if behavior_id in result["evidence_detection"]:
                # CODAP uses score (0/2); Colab uses triggered (bool)
                if self.session_type == "codap_arbor":
                    score = int(det.get("score", 0))
                    if score not in (0, 2):
                        score = 0
                    result["evidence_detection"][behavior_id] = {
                        "score": score,
                        "triggered": score == 2,
                        "evidence": str(det.get("evidence", "")),
                        "description": str(det.get("description", "")),
                    }
                else:
                    result["evidence_detection"][behavior_id] = {
                        "triggered": bool(det.get("triggered", False)),
                        "evidence": str(det.get("evidence", "")),
                        "description": "",
                    }

        ps.mmla_fill_lo_summary(result, self.session_key)

        # Build clean behaviors_observed summary (only Deepen hits, with description)
        if self.session_type == "codap_arbor":
            result["behaviors_observed"] = [
                {
                    "behavior_id": bid,
                    "description": result["evidence_detection"][bid].get("description", ""),
                }
                for bid in _BEHAVIOR_IDS_CODAP
                if result["evidence_detection"].get(bid, {}).get("score", 0) == 2
            ]
        else:
            result["behaviors_observed"] = [
                {
                    "behavior_id": bid,
                    "description": result["evidence_detection"][bid].get("evidence", ""),
                }
                for bid, v in result["evidence_detection"].items()
                if v.get("triggered", False)
            ]

        # Log individual behaviors
        for b, v in result["evidence_detection"].items():
            lo = self._behavior_lo(b)
            if v["triggered"]:
                self.log.behavior_triggered(student, frame_id, b, lo, v["evidence"])
            else:
                self.log.behavior_not_triggered(student, frame_id, b, lo, v["evidence"])

        triggered = [b for b, v in result["evidence_detection"].items() if v["triggered"]]
        lo_summary = {lo: v["status"] for lo, v in result["learning_outcomes"].items()}
        for lo, status in lo_summary.items():
            self.log.lo_result(student, frame_id, lo, status,
                               result["learning_outcomes"][lo]["triggering_behaviors"])
        self.log.frame_done(student, frame_id, triggered, lo_summary)

        return result

    # ── API call ──────────────────────────────────────────────────────────────

    def _call_api(
        self,
        student: str,
        frame_id: str,
        user_content: list[dict],
    ) -> dict[str, Any] | None:

        system_prompt = SYSTEM_PROMPTS[self.session_type]
        _BASE_MAX_TOKENS = 4000
        _MAX_TOKENS_CAP = 16000

        max_tokens = _BASE_MAX_TOKENS
        attempt = 0

        while attempt < MAX_RETRIES:
            attempt += 1
            try:
                t0 = time.time()
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                )
                latency_ms = int((time.time() - t0) * 1000)
                text_block = next((b for b in response.content if b.type == "text"), None)
                if text_block is None:
                    raise ValueError("No text block in API response")

                self.log.api_response(student, frame_id,
                                      response.usage.output_tokens, latency_ms)

                # Response was truncated — double max_tokens and retry without
                # counting this as a failure attempt
                if response.stop_reason == "max_tokens":
                    new_limit = min(max_tokens * 2, _MAX_TOKENS_CAP)
                    self.log.warn(
                        student, frame_id,
                        f"Response truncated at max_tokens={max_tokens}; retrying with {new_limit}",
                    )
                    if new_limit == max_tokens:
                        # Already at cap — try parsing whatever we got
                        parsed = parse_json_response(text_block.text)
                        if parsed is not None:
                            return parsed
                        raise ValueError("Response truncated at max_tokens cap; JSON incomplete")
                    max_tokens = new_limit
                    attempt -= 1  # truncation retry does not consume an error attempt
                    continue

                parsed = parse_json_response(text_block.text)
                if parsed is not None:
                    return parsed

                raise ValueError(f"JSON parse failed: {text_block.text[:200]}")

            except anthropic.RateLimitError:
                self.log.api_error(student, frame_id, "RateLimitError", attempt)
                if attempt < MAX_RETRIES:
                    time.sleep(RATE_LIMIT_WAIT * attempt)

            except (anthropic.APIError, ValueError) as e:
                self.log.api_error(student, frame_id, str(e), attempt)
                if attempt < MAX_RETRIES:
                    time.sleep(2 * attempt)

        return None

    # ── Prompt builder ────────────────────────────────────────────────────────

    def _build_user_content(
        self,
        frame_id: str,
        entry: dict[str, Any],
        session_context: dict[str, Any],
        transcript_window: str,
        image_path: Path,
    ) -> list[dict]:

        schema = OUTPUT_SCHEMAS[self.session_type]

        # Build session context block — only include non-null fields
        ctx_filtered = {k: v for k, v in session_context.items() if v is not None and v != 0}
        context_block = json.dumps(ctx_filtered, ensure_ascii=False) if ctx_filtered else "none"

        # screen_state and log_context are not pre-extracted — omit empty blocks
        screen = entry.get("screen_state") or {}
        logs = entry.get("log_context") or {}
        structured_block = ""
        if screen:
            structured_block += f"[SCREEN_STATE]\n{json.dumps(screen, ensure_ascii=False, indent=2)}\n\n"
        if logs:
            structured_block += f"[LOG_CONTEXT]\n{json.dumps(logs, ensure_ascii=False, indent=2)}\n\n"

        fewshot_block = _load_fewshot_block(self.session_type)
        text_intro = (
            f"Frame ID: {frame_id}\n"
            f"Timestamp: {int(entry.get('source_timestamp_seconds', 0))}s\n\n"
            f"[SESSION_CONTEXT]\n{context_block}\n\n"
            + structured_block +
            f"[TRANSCRIPT (±30s around this frame)]\n{transcript_window if transcript_window else 'none — no audio recording for this student; use visual evidence only'}\n\n"
            + fewshot_block
            + f"Apply the rubric to the screenshot above and fill in this JSON schema:\n{schema}"
        )

        return [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": encode_image(image_path),
                },
            },
            {"type": "text", "text": text_intro},
        ]

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _load_transcript(
        self, student: str, audio_dir: Path
    ) -> list[dict] | None:
        path = audio_dir / f"{student}_hybrid_diarization.json"
        if not path.exists():
            return None
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("status") == "no_speech":
            return None
        return doc.get("segments", [])

    def _transcript_window(
        self,
        segments: list[dict] | None,
        ts: float,
        window: float = 30.0,
    ) -> str:
        if not segments:
            return ""
        lo, hi = ts - window, ts + window
        hits = [
            s.get("text", "").strip()
            for s in segments
            if lo <= s.get("start", 0) <= hi and s.get("text", "").strip()
        ]
        return " ".join(hits)

    def _find_image(
        self, entry: dict[str, Any], audio_dir: Path, student: str
    ) -> Path | None:
        frames_dir = audio_dir / f"{student}_frames"

        # Primary: frame_id field (e.g. "frame_0001" → "frame_0001.jpg")
        fid = entry.get("frame_id")
        if fid:
            candidate = frames_dir / f"{fid}.jpg"
            if candidate.exists():
                return candidate

        # Secondary: explicit path key
        for key in ("image_path", "frame_path", "path"):
            p = entry.get(key)
            if p:
                candidate = Path(p) if Path(p).is_absolute() else REPO_ROOT / p
                if candidate.exists():
                    return candidate

        # Tertiary: gap-fill naming (gap_{Student}_{seconds:05d}s.jpg)
        ts = int(entry.get("source_timestamp_seconds", 0))
        gap_candidate = frames_dir / f"gap_{student}_{ts:05d}s.jpg"
        if gap_candidate.exists():
            return gap_candidate

        return None

    def _update_session_context(
        self,
        ctx: dict[str, Any],
        result: dict[str, Any],
        entry: dict[str, Any],
    ) -> None:
        screen = entry.get("screen_state", {})
        if self.session_type == "codap_arbor":
            dv = screen.get("dependent_variable")
            if dv:
                ctx["previous_dependent_variable"] = dv
            sv = screen.get("split_value")
            if sv is not None:
                ctx["previous_split_value"] = sv
            det = result.get("evidence_detection", {})
            if det.get("B7", {}).get("score", 0) == 2:
                ctx["emit_count_so_far"] = ctx.get("emit_count_so_far", 0) + 1
        else:
            code = screen.get("code_cell_content", "")
            if code:
                ctx["previous_code_state"] = code[:500]
            det = result.get("evidence_detection", {})
            ctx["error_in_previous_frame"] = det.get("B15_lo31", {}).get("triggered", False)

    def _behavior_lo(self, behavior_id: str) -> str:
        return self._behavior_lo_map.get(behavior_id, "?")

    def _dry_run_result(self, frame_id: str) -> dict[str, Any]:
        """Return a deterministic fake result for dry-run testing."""
        behavior_ids = ps.mmla_behavior_ids(self.session_key)
        return {
            "frame_id": frame_id,
            "frame_description": "[dry-run]",
            "evidence_detection": {
                b: {"score": 0, "evidence": "[dry-run]", "description": ""}
                for b in behavior_ids
            },
        }

    def close(self):
        self.log.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="MMLA Rubric Scorer")
    parser.add_argument("--session", required=True,
                        choices=list(ps.MMLA_SESSION_TYPES),
                        help="Session key: 21apr / 28apr / 05may")
    parser.add_argument("--students", nargs="*",
                        help="Student names (default: all in session)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip API calls, write empty scored JSONs")
    parser.add_argument("--final-only", action="store_true",
                        help="Skip frame API calls; rebuild final_scored.json from existing frame_observations.json")
    args = parser.parse_args()

    students = args.students or SESSION_STUDENTS.get(args.session, [])
    if not students:
        print(f"No students defined for session {args.session}")
        return

    print(f"Session    : {ps.MMLA_SESSION_LABELS[args.session]}")
    print(f"Students   : {students}")
    print(f"Model      : {args.model}")
    print(f"Dry-run    : {args.dry_run}")
    print(f"Final-only : {args.final_only}")
    print()

    t_start = time.time()
    success, failed = [], []

    with MMLAScorer(args.session, model=args.model, dry_run=args.dry_run) as scorer:
        for student in students:
            print(f"  Scoring {student}...", end=" ", flush=True)
            frame_path, final_path = scorer.score_student(student, final_only=args.final_only)
            if final_path:
                print(f"OK → {final_path.name}")
                success.append(student)
            else:
                print("FAILED")
                failed.append(student)

    elapsed = time.time() - t_start
    print(f"\nDone in {elapsed:.0f}s — {len(success)} OK, {len(failed)} failed")
    if failed:
        print(f"Failed: {failed}")


if __name__ == "__main__":
    main()
