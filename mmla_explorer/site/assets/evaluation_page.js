/* Evaluation and validation page. Numbers come from window.EVALUATION,
   which evaluation/run_evaluation.py writes from the source files. */
(function (root) {
  "use strict";

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
  const num = (v) => {
    const n = Number(v);
    if (!Number.isFinite(n)) return "–";
    return n.toLocaleString("en-GB");
  };
  const frac = (a, b) => `${num(a)} of ${num(b)}`;
  const share = (count, total) => (total ? `${(100 * count / total).toFixed(1)}%` : "–");

  function table(cols, rows) {
    const th = cols.map((col) => `<th${col.num ? ' class="num"' : ""}>${h(col.t)}</th>`).join("");
    const body = rows.map((row) => `<tr>${row.map((cell, i) => `<td${cols[i].num ? ' class="num"' : ""} data-label="${h(cols[i].t)}">${cell}</td>`).join("")}</tr>`).join("");
    return `<div class="table-wrap"><table class="vq vq-stack"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  function status(kind, label, detail) {
    return `<span class="eval-status ${kind}">${h(label)}</span>${detail ? `<span class="eval-did">${h(detail)}</span>` : ""}`;
  }

  function body() {
    const E = root.EVALUATION;
    if (!E) return `<h1>Evaluation and validation</h1><p>The evaluation table has not been built.</p>`;
    const rules = E.rules;
    const frames = E.frames;
    const logs = E.logs;
    const nb = E.notebooks;
    const tri = E.triangulation;
    const credit = E.review_by_credit || {};
    const labelled = frames.labelled_frames;
    const counts = frames.label_counts || {};
    const principal = ["EXPLORE_DATA", "TUNE_THRESHOLD", "COMPARE_MODELS", "OFF_TASK"].filter((key) => counts[key]);
    const principalSum = principal.reduce((sum, key) => sum + counts[key], 0);
    const other = labelled - principalSum;
    const otherNames = Object.keys(counts).filter((key) => !principal.includes(key) && counts[key]);
    const mae = Number(rules.mae);
    const creditRows = [
      ["Full credit, stored score of 1 or higher", (credit.full_credit || {}).items, (credit.full_credit || {}).review_flag],
      ["Partial credit, above 0 and below 1", (credit.partial || {}).items, (credit.partial || {}).review_flag],
      ["No credit, stored 0", (credit.no_credit || {}).items, (credit.no_credit || {}).review_flag],
    ];
    const b25Gaps = (rules.mismatches || []).filter((row) => row.item === "WS5_B25" && row.scoring === 0 && row.validation === 1);
    const numeric = logs.numeric_emit_fields_that_changed || {};
    const seq = logs.interval_sequence_difference_sessions || [];
    const wall = logs.wall_clock_totals || {};
    const labelRows = principal.map((key) => [h(key), num(counts[key]), share(counts[key], labelled)])
      .concat([["Other stored labels", num(other), share(other, labelled)]]);
    const overview = [
      [status("done", "Completed", "Active code paths were inspected."), "No retrieval index. Rubrics and examples are written into the prompt.", "RAG metrics do not apply. Unused scripts were not treated as the current system."],
      [status("done", "Completed", "Researcher comparison with the original pages."), "The researcher reports that every extracted response matched the handwriting.", "This is transcription fidelity, not a grade. No item-level comparison file is stored."],
      [status("part", "Partially evaluated", "Stored scores compared with the pipeline validation file."), `${frac(rules.exact_agreement, rules.compared)} items agree exactly. MAE is ${mae.toFixed(3)}.`, "The reference is the same pipeline, not an independent human grade."],
      [status("human", "Requires independent validation", "No second-rater file."), "Not calculated.", "The transcription check does not validate the rubric score."],
      [status("part", "Partially evaluated", "Counts of labels on sampled frames. The researcher inspected the images."), `${num(labelled)} labelled frames. The largest label is ${h(frames.majority_label)} (${num(frames.majority_count)}).`, "No second coder, so kappa was not calculated. Model confidence is not accuracy."],
      [status("done", "Completed", "Intervals between model submissions were counted."), "A threshold change is often followed by a different numeric model state.", "The association is temporal. It is not an intention, a cause, or a learning gain."],
      [status("none", "Not established", "A match was attempted. No shared clock was available."), "0 frame-to-log matches.", "Session-level comparison remains possible where both files exist."],
      [status("part", "Partially evaluated", "Saved files were read and not rerun."), `${num(nb.notebooks)} notebooks and ${num(nb.reports.length)} written report. A stored test misclassification rate is present for ${frac(nb.models_with_stored_test_mcr, nb.models)} described models.`, "Those rates are the student’s model results, not a score for this archive."],
      [status("part", "Partially evaluated", "Sources were compared by participant and session."), `${num(tri.paired_with_both_threshold_signals)} labelled sessions with both sources contain a threshold label and a threshold-change event.`, "Co-occurrence is not a matched moment and not a causal claim."],
    ];
    const components = [
      "System architecture",
      "Worksheet transcription",
      "Rule-based scoring",
      "Rubric scoring",
      "Frame behaviour labels",
      "CODAP event sequences",
      "Frame–log alignment",
      "Final submissions",
      "Multimodal coverage",
    ];
    return `
      <h1>Evaluation and validation</h1>
      <p class="lead">These are the checks that were calculated, what they support, and what still needs an independent judgement. How the sources were collected and what the researcher verified are on <a href="#/docs/limitations">Data Quality and Limitations</a>.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#/docs/evaluation/overview">Overview</a>
        <a href="#/docs/evaluation/architecture">Architecture</a>
        <a href="#/docs/evaluation/scores">Scores</a>
        <a href="#/docs/evaluation/frames">Frames</a>
        <a href="#/docs/evaluation/logs">Logs</a>
        <a href="#/docs/evaluation/alignment">Alignment</a>
        <a href="#/docs/evaluation/submissions">Final submissions</a>
      </nav>

      <h2 id="architecture">Architecture</h2>
      <p>The model sees the worksheet page or the frame, together with a rubric or examples written into the prompt. Nothing retrieves passages from a document index. Precision at k, mean reciprocal rank, nDCG, and RAG faithfulness measures were not calculated: there is no retrieval stage and no set of judged passages.</p>

      <h2 id="overview">Overview</h2>
      ${table(
        [{ t: "Component" }, { t: "Evaluation" }, { t: "Main result" }, { t: "Remaining limitation" }],
        components.map((name, i) => [h(name), overview[i][0], h(overview[i][1]), h(overview[i][2])])
      )}

      <h2 id="scores">Worksheet scores</h2>
      <p>The score summary contains ${num(E.scored_items)} items: a published extraction that is not worksheet 11, not a blocked file, and not a file whose scores all have confidence zero. Five accepted changes are stored, all on worksheet 5, item B25. Each has a rationale. The score that was replaced is not stored, so the size of each change cannot be reconstructed. The review flag is still set on all five. A flag is a pipeline marker. The accepted change is the override and its rationale. <a href="#/explore/worksheet/WS5?view=compare&amp;mode=score&amp;item=WS5_B25">The five changes on worksheet 5</a>.</p>
      ${table(
        [{ t: "Stored credit in the score summary" }, { t: "Items", num: 1 }, { t: "Review flag", num: 1 }],
        creditRows.map((row) => [h(row[0]), num(row[1]), num(row[2])])
      )}
      <p>The three credit rows sum to ${num(E.scored_items)} items and ${num(E.review_flags)} review flags. ${frac(E.review_without_override, E.review_flags)} flags have no accepted change. The other ${num((E.overrides || []).length)} are the accepted changes, and those rows stay flagged. If blocked and unused files are included, the flag count is ${num(E.review_flags_all_files)}. Those extra flags are outside the ${num(E.scored_items)} items. On several rubric worksheets the pipeline sets the flag when credit is partial or zero, so a flag is not, by itself, a decision waiting to be accepted.</p>
      <p>For the four rule worksheets, the stored score and the deterministic check in the validation file agree on ${frac(rules.exact_agreement, rules.compared)} items. Mean absolute error on those ${num(rules.compared)} pairs is ${mae.toFixed(3)}. The reference is that validation file, not a second rater. ${num(rules.mismatch_count)} items disagree, of which ${num(b25Gaps.length)} are worksheet 5, item B25, with a stored score of 0 and a validation score of 1. None of those is an accepted change. Rubric scores were not compared with an independent human score, so exact agreement and weighted kappa against a human rater were not calculated.</p>
      <details class="vq">
        <summary>Score record</summary>
        <p>Unrounded mean absolute error is ${mae}. It is the sum of absolute gaps divided by ${num(rules.compared)} paired items. Items without a validation score are excluded, not coded as zero.</p>
        ${table(
          [{ t: "Student" }, { t: "Final score", num: 1 }, { t: "Review flag" }, { t: "Rationale" }],
          (E.overrides || []).map((row) => [h(row.student), h(row.final_score), row.review_flag_still_set ? "Still set" : "Not set", h(row.rationale)])
        )}
        <p>The accepted B25 changes match the validation file, so they are not in the disagreement table. This evaluation does not choose between files that still disagree.</p>
        ${table(
          [{ t: "Student" }, { t: "Worksheet" }, { t: "Item" }, { t: "Stored score", num: 1 }, { t: "Validation score", num: 1 }],
          (rules.mismatches || []).map((row) => [h(row.student), h(row.worksheet), h(row.item), h(row.scoring), h(row.validation)])
        )}
      </details>

      <h2 id="frames">Screen-recording frames</h2>
      <p>The counts below are shares of ${num(labelled)} sampled, labelled frames. They are not shares of recording time. The researcher inspected the images. No second coder is in the archive, so Cohen’s kappa was not calculated. The model’s own confidence is not accuracy: ${num(frames.model_confidence.HIGH)} high, ${num(frames.model_confidence.MEDIUM)} medium, and ${num(frames.model_confidence.LOW)} low.</p>
      ${table(
        [{ t: "Behaviour label" }, { t: "Frames", num: 1 }, { t: "Share of labelled frames", num: 1 }],
        labelRows
      )}
      <p>Other stored labels are ${otherNames.map(h).join(", ") || "none"}. SELECT_TARGET is not among the stored labels (${num(tri.select_target_labels)} frames). The log, separately, records ${num(tri.target_setting_events)} target-setting events. The two instruments do not count the same thing, and the zero label count is not evidence that no target was set. The full label list is on <a href="#/findings/recordings">screen recording findings</a>.</p>

      <h2 id="logs">Platform logs</h2>
      <p>Between model submissions, ${num(logs.only_threshold_wall)} intervals in wall-clock order contain a threshold change and no attribute placement. Of those, ${num(logs.only_threshold_wall_with_no_other_config_action)} also contain no other configuration action, and ${num(logs.only_threshold_wall_with_changed_numeric_emit_field)} are followed by a submission whose numeric fields differ. Accuracy differs in ${num(numeric.accuracy)} of the ${num(logs.only_threshold_wall)} intervals. Depth differs in ${num(numeric.depth)}. This is a temporal association in the log. It does not show why the learner made the change.</p>
      <details class="vq">
        <summary>Timestamp order</summary>
        <p><code>timestamp_ms</code> decreases along wall-clock order in ${frac(logs.sessions_with_timestamp_ms_reset, logs.sessions)} sessions. Category totals are the same under both clocks: ${num(wall.only_attribute)} only-attribute intervals, ${num(wall.only_threshold)} only-threshold intervals, and ${num(wall.both_or_neither)} both-or-neither intervals, out of ${num(wall.intervals)}. The order of those categories differs in ${num(logs.sessions_whose_interval_sequence_differs)} sessions${seq.length ? `: ${seq.map((row) => `${h(row.student)}, ${h(row.session)}`).join("; ")}` : ""}.</p>
      </details>

      <h2 id="alignment">Frame–log alignment</h2>
      <p>No frame was matched to a log row. Frame time is seconds from the start of the recording. Log <code>timestamp_ms</code> is not that clock, and it resets. The fallback that estimates the recording start from the first log row would make the offset depend on the log, so it was not used as a shared clock. Participant and session comparisons remain possible where both sources exist: ${num(tri.paired_sessions)} sessions have both a frame manifest and a log. ${num(tri.paired_with_both_threshold_signals)} labelled sessions contain both at least one TUNE_THRESHOLD frame and at least one threshold-change event. ${num(tri.paired_tune_label_without_threshold_event)} have the label without the event, and ${num(tri.paired_threshold_event_without_tune_label)} have the event without the label. ${num(tri.paired_sessions_without_labels)} paired session has frames and a log but no behaviour labels, so its log events are not read as a disagreement.</p>

      <h2 id="submissions">Final submissions</h2>
      <p>${num(nb.notebooks)} notebooks and ${num(nb.reports.length)} written report were inspected and not rerun. A train/test split is recorded in ${frac(nb.split_recorded, nb.submissions)} files. A stored test misclassification rate is present for ${frac(nb.models_with_stored_test_mcr, nb.models)} described models. That rate belongs to the student’s model. It is not a performance score for this archive, and it was not recomputed. Which traces each file contains is on <a href="#/docs/limitations/vq-notebooks">Data Quality and Limitations</a>.</p>
      <details class="vq">
        <summary>Stored inspection flags</summary>
        <p>${(nb.synthetic_flags || []).length ? `The inspection record marks ${nb.synthetic_flags.map(h).join(", ")} as using synthetic data. This evaluation did not run the notebook again, so the flag is reported as stored.` : "No stored synthetic-data flag was read."} A written question is recorded in ${num(nb.task_found.question)} of ${num(nb.task_denominator)} files.</p>
      </details>

      <p class="small">Rebuild with <code>python3 evaluation/run_evaluation.py</code>. In the calculation record, a finished script is not the same thing as a validated claim. Frame–log alignment is recorded there as not established. <a href="#/docs/limitations">Data Quality and Limitations</a></p>
    `;
  }

  root.EvaluationPage = { body };
})(window);
