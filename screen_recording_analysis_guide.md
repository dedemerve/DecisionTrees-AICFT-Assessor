# Screen Recording Analysis Guide

## What the Log File Cannot Capture

This document defines every behavioural signal that must be coded from screen
recordings. None of these can be derived from the CODAP Arbor CSV log or from
worksheet data. Each section describes the signal, why it matters for AI-CFT
coding, and the exact observation protocol for the human or AI coder.

---

## 1. Pre-Action Hesitation (Mouse Dwell Without Click)

**What it is**
The cursor moves to a feature, threshold slider, or menu item and stays there
for a measurable period without clicking. The log records only the click, not
the dwell.

**Why it matters**
Hesitation before a correct action suggests the pre-service teacher reached the
right answer through deliberation. Hesitation followed by a wrong action suggests
uncertainty or guessing. Hesitation that resolves into no action at all (cursor
moves away) suggests the option was considered and rejected.

**Observation protocol**
For each hesitation event, record:
- timestamp
- target element (feature name, threshold slider, menu)
- estimated dwell duration in seconds (short <3s, medium 3-10s, long >10s)
- outcome: clicked, moved_away, or clicked_elsewhere
- whether the outcome changed model accuracy (from next emit)

---

## 2. Data Table Inspection Before Decisions

**What it is**
The pre-service teacher scrolls through, resizes, or examines the data table
before selecting a feature or changing a threshold. The log records the
drop_attribute or change_split_values event but not the preparatory inspection.

**Why it matters**
This distinguishes analytical reasoning (looking at data, forming a hypothesis,
then acting) from blind trial-and-error (acting without consulting the data).
It maps directly to AI-CFT LO3.1.4 (appropriateness_assessment) and LO3.2.2
(workflow_visualisation).

**Observation protocol**
For each feature selection or threshold change, record whether:
- the data table was scrolled or examined in the 30 seconds before the action
- the scatter plot or distribution graph was examined
- no data consultation occurred (action was immediate)

Label each action as: data_informed, graph_informed, or uninformed.

---

## 3. Tree Visualisation Reading Time

**What it is**
Time the pre-service teacher spends looking at the decision tree diagram after
an emit, before taking the next action. The log records the emit timestamp and
the next action timestamp but does not distinguish between reading the tree and
being idle.

**Why it matters**
A pre-service teacher who reads the tree output and then makes a targeted change
is demonstrating interpretive skill (LO3.2.2). A pre-service teacher who emits
and immediately changes something without reading the output is not processing
feedback.

**Observation protocol**
For each emit event, measure the gap (in seconds) between the emit and the next
meaningful action. Then observe whether:
- the cursor moved over the tree nodes during this gap (active reading)
- the screen was static (passive pause or distraction)
- the teacher scrolled the tree or zoomed in
- the teacher immediately switched to another panel without reading

Label each post-emit gap as: active_read, passive_pause, or immediate_action.
Note: gaps over 60 seconds may indicate external distraction rather than reading.

---

## 4. Physical Worksheet Reference

**What it is**
The pre-service teacher minimises or moves the browser window to consult a
physical worksheet, or looks away from the screen toward paper materials on
the desk. The log has no record of this.

**Why it matters**
Consulting the worksheet while working in CODAP or Python indicates the
pre-service teacher is using the unplugged activity as a reference scaffold.
This is a positive transfer signal. Conversely, never consulting it may indicate
either independence (positive) or ignoring guidance (negative). Context matters.

**Observation protocol**
For each instance of worksheet consultation, record:
- timestamp
- what was happening in CODAP/Python immediately before
- what the teacher appeared to check (threshold section, feature list, misclassification table)
- whether the next action in CODAP/Python was consistent with what the worksheet showed

Estimate total time spent consulting physical materials per session.

---

## 5. Instruction Panel Reading

**What it is**
CODAP Arbor displays task instructions in a panel. The teacher may open, read,
scroll, or close this panel at different moments. The log records only
codap_component_change events with type DG.WebView but does not capture reading
time or which part was read.

**Why it matters**
Reading instructions before acting indicates that the teacher is working from
understanding rather than imitation. Re-reading instructions mid-task after an
error indicates self-regulation. Never reading the instructions is also a
meaningful signal.

**Observation protocol**
For each instruction panel interaction, record:
- timestamp
- approximate reading duration
- whether this was first open, re-open after error, or scanning
- what the teacher did immediately after closing the panel

---

## 6. Error Recognition and Response (CODAP Context)

**What it is**
After a poor accuracy result (e.g. below 0.50 on an emit), the pre-service
teacher's immediate response. The log shows the accuracy value and the next
action but not whether the teacher recognised the result as poor or what their
reasoning was.

**Why it matters**
Error recognition and corrective action map directly to AI-CFT LO3.2.1
(proficient_independent_operation). A teacher who sees 0.277 accuracy, pauses,
inspects the tree, and then systematically changes a feature is demonstrating
error diagnosis. A teacher who immediately changes the threshold without reading
the tree is reacting without diagnosis.

**Observation protocol**
For each emit where accuracy is below 0.55 (threshold for concern), record:
- how long before the next action (reading pause duration)
- whether the teacher looked at the confusion matrix (TP/TN/FP/FN panel)
- whether they changed feature (deeper diagnosis) or threshold (surface fix)
- whether they verbalised anything (if audio is available)
- whether the corrective action actually improved accuracy (from next emit)

Label the response as: systematic_diagnosis, surface_correction, or no_response.

---

## 7. Confusion Matrix Inspection

**What it is**
The TP, TN, FP, FN values are visible in the CODAP Arbor interface after each
emit. The log records these values but does not record whether the teacher
actually read them.

**Why it matters**
Reading the confusion matrix (not just accuracy) indicates a deeper conceptual
understanding. A teacher who adjusts strategy based on the FP/FN balance is
demonstrating knowledge beyond the accuracy metric. This maps to LO3.3.1
(limitation_analysis).

**Observation protocol**
For each emit, observe whether the teacher:
- moved the cursor over the confusion matrix cells
- scrolled to the matrix panel if it was off-screen
- appeared to compare FP vs FN values before deciding what to change
- used only the accuracy percentage and ignored the matrix

---

## 8. Regression Tree Switch: Intentional or Accidental

**What it is**
The log records change_tree_type events for 4 pre-service teachers. It does not
record whether this was a deliberate exploration, an accidental click, or a
misunderstanding of the interface.

**Why it matters**
An accidental click is an interface usability issue, not a conceptual error.
A deliberate switch to regression on a classification task is a conceptual error.
Deliberate switch followed by immediate recognition of the error and correction
is actually a positive signal (error self-detection).

**Observation protocol**
For each change_tree_type event, record:
- whether the cursor hesitated before clicking (deliberate) or clicked immediately
- whether the teacher showed any reaction to the changed output (noticing the change)
- how quickly they switched back (if they did)
- whether they appeared confused by the regression output before switching back

---

## 9. Python Phase: Error Message Reading

**What it is**
In Google Colab, when a cell throws an error (traceback), the teacher must read
the error message to diagnose the problem. The screen recording shows whether
they read it, scrolled to it, or ignored it.

**Why it matters**
Reading and acting on a traceback is a fundamental debugging skill. It maps to
LO3.2.3 (transferable_problem_solving) and is a key signal for Deepen-level
behaviour. A teacher who deletes the entire cell and rewrites from scratch every
time they get an error is not transferring CODAP diagnostic skills to Python.

**Observation protocol**
For each error event in Python (visible red traceback in Colab), record:
- error reading duration (how long the cursor or scroll stayed on the traceback)
- whether the teacher scrolled to the bottom of the traceback (where the actual error line is)
- corrective strategy: targeted_fix (edited specific line), full_rewrite (deleted all code),
  copy_paste (copied from somewhere), or no_action (ran next cell without fixing)
- whether the fix resolved the error or produced a new error

---

## 10. Python Phase: Typing vs Copying

**What it is**
Whether the teacher typed code character by character or pasted it from an
external source (worksheet, another cell, a peer's screen). Paste actions may
produce a brief flash or immediate large text appearance.

**Why it matters**
Typing indicates authorship and cognitive engagement with the code. Copy-paste
is not inherently wrong but changes what the screen recording evidence supports.
If a teacher copies a full decision tree implementation and runs it without
modification, that is not the same as building it incrementally.

**Observation protocol**
For each code cell, record:
- method: typed, pasted, or mixed
- if pasted: from where (within Colab, from external source, or unclear)
- whether the teacher read the pasted code before running it

---

## 11. Python Phase: Incremental Building vs All-at-Once

**What it is**
Whether the teacher wrote code cell by cell (running each cell before writing
the next) or wrote the entire notebook at once before running.

**Why it matters**
Incremental building demonstrates understanding of what each code block does.
Writing everything at once then running is consistent with copying without
comprehension. Maps to LO3.2.1 and LO3.3.2.

**Observation protocol**
For each Python session, record the run order:
- cell written → cell run → next cell written (incremental)
- all cells written → all run at once (batch)
- mixed pattern

Also note whether the teacher checked the output of each cell before proceeding.

---

## 12. Python Phase: Variable Name Inspection

**What it is**
After defining a variable (e.g. X_train, clf, y_pred), the teacher may or may
not inspect its value (e.g. by printing it or running type() / shape). The log
does not capture this.

**Why it matters**
Inspecting intermediate variables indicates the teacher understands what each
step produces. Not inspecting them means running code blind. This distinguishes
a teacher who understands the pipeline from one who is executing a memorised
sequence.

**Observation protocol**
For each major variable definition, record:
- whether the teacher printed/inspected the variable before moving on
- whether the inspection revealed something unexpected (visible reaction or correction)

---

## 13. Peer Interaction and Screen Sharing

**What it is**
The teacher looks at a peer's screen, discusses with a peer, or receives a
hint from the instructor. None of this appears in the log.

**Why it matters**
Peer assistance changes what the individual's log data means. A teacher who
achieved 0.900 accuracy after looking at a peer's screen is not demonstrating
the same competency as one who achieved it independently.

**Observation protocol**
For each session, record:
- any visible peer screen visible in the background
- teacher turning to speak with a peer (head movement if camera is on)
- instructor visible in frame or voice audible
- timestamps of any apparent external help

Label sessions as: fully_independent, peer_assisted, instructor_assisted, or unclear.

---

## 14. Interface Navigation Difficulty

**What it is**
Time spent looking for a button, clicking the wrong panel, reopening a closed
window, or repeatedly opening and closing the same menu without taking action.
The log records some of these as codap_component_change events but does not
record failed navigation attempts.

**Why it matters**
Interface confusion creates dead time that inflates session duration and
suppresses the number of model iterations. It is a usability issue, not a
learning issue. Separating interface difficulty from conceptual difficulty is
necessary for fair AI-CFT coding.

**Observation protocol**
For each session, estimate total time lost to interface navigation in minutes.
Record specific examples:
- cannot find the Emit button
- opens data context menu repeatedly without selecting
- accidentally closes a panel and spends time reopening it
- clicks on a non-interactive element expecting a response

---

## 15. Affect and Engagement Signals

**What it is**
Visible frustration (rapid clicking, sudden stopping), engagement (leaning
forward, rapid purposeful iteration), or disengagement (long idle periods,
switching to another browser tab).

**Why it matters**
Affect signals provide context for the log data. A teacher with 30 emits but
visible disengagement in the final 10 may not have been consciously improving
the model. A teacher with high volatility (std > 0.15) who appears engaged and
deliberate is different from one who appears to be clicking randomly.

**Observation protocol**
This is coded at the session level, not per-event. For each session, record:
- overall engagement level: high, medium, low
- any visible frustration episodes (with timestamps)
- any visible moments of insight (positive reaction to an improvement)
- any disengagement periods (idle >90 seconds, tab switching)

---

## 16. Train/Test Split Understanding (CODAP Context)

**What it is**
Whether the teacher deliberately selected a different dataset for testing versus
training, understood that the two datasets should not be the same, and reacted
to the difference in accuracy between them.

**Why it matters**
The log file cannot confirm train/test understanding for Food Dataset students
because dataset names do not encode train/test membership (see process_log.md).
Screen recording is the only way to verify this for 17 of 18 active students.

**Observation protocol**
For each student, record:
- whether the teacher explicitly switched datasets before emitting
- whether they appeared to notice a difference in accuracy when switching
- whether they verbalised or gestured any reaction to the train/test gap
- whether they attempted to improve the model based on the test result

This resolves the train_test_indeterminate flag for all Food Dataset students.

---

## 17. Depth Decision: Intentional or Accidental

**What it is**
When depth increases (e.g. from 2 to 3), was this because the teacher
deliberately added a new split node, or because adding a feature automatically
extended the tree? The log records the resulting depth on emit, not the
decision to increase it.

**Why it matters**
A teacher who deliberately deepens the tree and explains why is demonstrating
LO3.3.3 (self_defined_test_criteria). A teacher who does not notice the depth
changed is not.

**Observation protocol**
For each emit where depth increases from the prior emit, record:
- whether the teacher appeared to notice the depth change
- whether the depth increase was preceded by a deliberate split action
- whether the teacher reverted the depth change after seeing the accuracy result

---

## Coder Instructions

Each event type above produces a structured observation record. The format is:

```
{
  "student_id": "canonical_id",
  "recording_id": "recording_filename",
  "timestamp": "HH:MM:SS",
  "signal_type": one of the 17 types above,
  "observation": short factual description,
  "label": the coded label for this signal type,
  "ai_cft_relevance": which LO this supports or contradicts,
  "confidence": high / medium / low
}
```

When a signal cannot be determined from the recording (camera angle, low
resolution, obscured screen), mark confidence as low and note the reason.
Do not infer; mark as insufficient_evidence.

---

## Priority Order for Coding

Not all 17 signals carry equal weight for AI-CFT level assignment.
Code in this order to maximise coverage within limited annotation time.

Priority 1 (required for any level assignment):
- Signal 2: Data table inspection before decisions
- Signal 6: Error recognition and response
- Signal 13: Peer interaction (validity check)
- Signal 16: Train/test understanding

Priority 2 (required for Deepen or Create assignment):
- Signal 3: Tree visualisation reading time
- Signal 7: Confusion matrix inspection
- Signal 9: Python error message reading
- Signal 17: Depth decision intentionality

Priority 3 (contextual, enriches interpretation):
- Signal 1: Pre-action hesitation
- Signal 4: Physical worksheet reference
- Signal 5: Instruction panel reading
- Signal 8: Regression switch type
- Signal 11: Python incremental building
- Signal 14: Interface navigation difficulty
- Signal 15: Affect and engagement

Priority 4 (optional, adds nuance):
- Signal 10: Python typing vs copying
- Signal 12: Variable name inspection
