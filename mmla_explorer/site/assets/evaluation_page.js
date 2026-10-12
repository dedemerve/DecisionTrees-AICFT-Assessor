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

  function table(heads, rows) {
    const th = heads.map((name) => `<th>${h(name)}</th>`).join("");
    const body = rows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("");
    return `<div class="table-wrap"><table class="vq"><thead><tr>${th}</tr></thead><tbody>${body}</tbody></table></div>`;
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
    const bothSessions = (tri.matrix || []).filter((row) => row.frame_sessions === 2).length;
    const labelRows = Object.entries(frames.label_counts || {})
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => [h(label), num(count), labelled ? `${(100 * count / labelled).toFixed(1)}%` : "–"]);
    const taskRows = Object.entries(nb.task_found || {}).map(([task, count]) => [
      h(task), `${num(count)} / ${num(nb.task_denominator)}`,
    ]);
    const overrideRows = (E.overrides || []).map((row) => [
      h(row.student), h(row.final_score), row.review_flag_still_set ? "Still set" : "Not set", h(row.rationale),
    ]);
    const mismatchRows = (rules.mismatches || []).map((row) => [
      h(row.student), h(row.worksheet), h(row.item), h(row.scoring), h(row.validation),
    ]);
    const statusRows = (E.matrix || []).map((row) => [
      h(row.component), h(row.status), h(row.result),
    ]);
    const b25Gap = (rules.mismatches || []).filter((row) => row.item === "WS5_B25" && row.scoring === 0 && row.validation === 1).length;
    const seq = (logs.interval_sequence_difference_sessions || [])
      .map((row) => `${row.student}, ${row.session}`).join("; ");
    return `
      <h1>Evaluation and validation</h1>
      <p class="lead">The archive records what was extracted, scored, labelled, and logged. Those records can be checked against each other. They do not yet show that an automated score or a behaviour label is independently correct.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#/docs/evaluation/architecture">Architecture</a>
        <a href="#/docs/evaluation/scores">Scores</a>
        <a href="#/docs/evaluation/frames">Frames</a>
        <a href="#/docs/evaluation/logs">Logs</a>
        <a href="#/docs/evaluation/sources">Across sources</a>
        <a href="#/docs/evaluation/matrix">What was calculated</a>
      </nav>

      <h2 id="architecture">What kind of system this is</h2>
      <p>A language model reads worksheet pages and screen frames. Rubrics and examples are written into the prompt. Rule worksheets are then scored in Python. Nothing searches a document index and hands the retrieved passages to the model.</p>
      <p>That is why retrieval metrics such as precision at k, mean reciprocal rank, and nDCG were not calculated. There is no retrieval stage and no judged set of relevant passages. Faithfulness metrics from RAG evaluation frameworks were not applied for the same reason.</p>
      <p>The researcher compared each extracted worksheet response with the original handwriting and reports that the reading matched in every case. That check is about transcription. It is separate from whether the answer is conceptually right, whether the rubric was applied correctly, and whether a behaviour label would be given by a second coder.</p>

      <h2 id="scores">Worksheet scores</h2>
      <p>The score summary contains ${num(E.scored_items)} items. The denominator is a published extraction that is not worksheet 11, not a blocked file, and not a file whose scores all have confidence zero. ${num(E.review_flags_all_files)} review flags exist if blocked and unused files are included. Those extra flags are not score results.</p>
      <p>Five scores were changed, all on worksheet 5, item B25. Each change stores a rationale. The score that was replaced is not stored, so the size of the change cannot be measured. On each of those five rows the review flag is still set. The flag remains a request marker. The accepted change is the override and its rationale.</p>
      ${table(["Student", "Final score", "Review flag", "Rationale"], overrideRows)}
      <p>In the score summary, a review flag without an override is present on ${frac(E.review_without_override, E.scored_items)} items. The flag sits on ${frac((credit.partial || {}).review_flag, (credit.partial || {}).items)} partial-credit items, ${frac((credit.no_credit || {}).review_flag, (credit.no_credit || {}).items)} no-credit items, and ${frac((credit.full_credit || {}).review_flag, (credit.full_credit || {}).items)} full-credit items. For several rubric worksheets the pipeline sets the flag when credit is partial or zero. A flag is therefore not, by itself, a human decision waiting to be accepted.</p>
      <p>For the four rule worksheets, the stored score and the stored deterministic check agree on ${frac(rules.exact_agreement, rules.compared)} items. Mean absolute error on those ${num(rules.compared)} pairs is ${Number(rules.mae).toFixed(3)}. The reference is the validation file from the same pipeline, not a second rater. ${num(rules.mismatch_count)} items disagree.</p>
      ${table(["Student", "Worksheet", "Item", "Stored score", "Validation score"], mismatchRows)}
      <p>${num(b25Gap)} of the disagreements are worksheet 5, item B25, where the check awards full credit and the score file stores zero, with no accepted change. The five accepted B25 changes are not in this list: their final scores match the validation file. The remaining rows in the table also differ across the two files. For Isabel’s worksheet 10 item B4, the extraction stores “3”, the check calls the item blank, and the score file stores full credit. The files do not agree, and this evaluation does not choose one of them.</p>
      <p>Rubric scores were not compared with an independent human score. Mean absolute error, exact agreement, and weighted kappa against a human rater were not calculated.</p>

      <h2 id="frames">Screen-recording frames</h2>
      <p>The researcher has inspected the frame images. That inspection is complete as a visual check. It is not an inter-rater statistic. No second coder is in the archive, so Cohen’s kappa was not calculated. The model’s own confidence is not accuracy: ${num(frames.model_confidence.HIGH)} high, ${num(frames.model_confidence.MEDIUM)} medium, and ${num(frames.model_confidence.LOW)} low, out of ${num(labelled)} labelled frames.</p>
      ${table(["Behaviour label", "Frames", "Share of labelled frames"], labelRows)}
      <p>SELECT_TARGET does not appear. The coding instructions reserve that label for a frame that shows the target being placed, and they tell the model to prefer more common labels when it is unsure. The log, separately, records ${num(tri.target_setting_events)} target-setting events. The two instruments are not counting the same thing, and the zero label count is not evidence that no target was set.</p>
      <p>Eight session files record that the log was not used and that video alignment was unavailable. Twelve session files do not store those fields. No frame record stores a log window. Dropping the ${num(frames.low_confidence_frames)} low-confidence frames does not change which label is most common.</p>

      <h2 id="logs">Platform logs</h2>
      <p>In the two CODAP sessions, ${num(logs.action_class_counts.interface_rows)} rows are interface events, ${num(logs.action_class_counts.learner_decision_rows)} are decision actions such as placing an attribute, changing a threshold, or submitting a tree, and ${num(logs.action_class_counts.other_rows)} are other recorded actions. An interface event shows that the software logged it. It does not show a learning strategy.</p>
      <p>Between submissions, the published count uses <code>timestamp_ms</code>. That clock decreases along wall-clock order in all ${num(logs.sessions)} sessions, which is the reset the alignment code already documents. Reordering the same events by <code>created_at</code> leaves the category totals unchanged: ${num(logs.wall_clock_totals.only_attribute)} only-attribute intervals, ${num(logs.wall_clock_totals.only_threshold)} only-threshold intervals, and ${num(logs.wall_clock_totals.both_or_neither)} both-or-neither intervals, out of ${num(logs.wall_clock_totals.intervals)}. The order of those categories differs for ${h(seq || "no session")}.</p>
      <p>Of the ${num(logs.only_threshold_wall)} wall-clock intervals that contain a threshold change and no attribute placement, ${num(logs.only_threshold_wall_with_no_other_config_action)} also contain no other configuration action such as a target change or a tree refresh. ${num(logs.only_threshold_wall_with_changed_numeric_emit_field)} are followed by a submitted payload whose numeric fields differ. Accuracy differs in ${num((logs.numeric_emit_fields_that_changed || {}).accuracy)} of those intervals. Depth differs in ${num((logs.numeric_emit_fields_that_changed || {}).depth)}. The next submission often carries a different accuracy after a threshold change. That is a temporal association in the log. It does not show why the learner made the change.</p>

      <h2 id="sources">Across sources</h2>
      <p>Frame time is seconds from the start of the recording. Log <code>timestamp_ms</code> is not that clock. The fallback that estimates the recording start from the first log row would make the offset depend on the log. No frame was matched to a log row.</p>
      <p>${num(tri.paired_sessions)} sessions have both a frame manifest and a log. ${num(bothSessions)} of 15 participants have frame manifests for both CODAP sessions. ${num(tri.paired_with_both_threshold_signals)} labelled sessions contain both at least one TUNE_THRESHOLD frame and at least one threshold-change event. The counts are not expected to match, because a frame is a sampled image and a log row is a software event. ${num(tri.paired_sessions_without_labels)} session, Irma’s first CODAP session, has frames and a log but no behaviour labels. Its 17 threshold-change events are not read as a disagreement with a label.</p>
      <p>Final submissions: ${num(nb.notebooks)} notebooks. ${nb.reports.length ? `${nb.reports.map(h).join(", ")} submitted a written report.` : ""} A train/test split is recorded in ${frac(nb.split_recorded, nb.submissions)} files. A stored test misclassification rate is present for ${frac(nb.models_with_stored_test_mcr, nb.models)} described models. Those rates were not recomputed. A missing trace is missing evidence, not a score of zero.</p>
      ${table(["Trace in the final file", "Submissions"], taskRows)}
      <p>The inspection record marks Ulysses as using synthetic data. This evaluation did not run the notebook again, so that flag is reported as stored, not as a new measurement. A written question is recorded in ${num(nb.task_found.question)} of ${num(nb.task_denominator)} files. The other files do not contain that trace in the inspection.</p>

      <h2 id="matrix">What was calculated</h2>
      <p>Completed means the calculation ran on the files named in <code>evaluation/results/</code>. A result can be complete and still be the wrong kind of evidence for a claim about learning.</p>
      ${table(["Component", "Status", "Result"], statusRows)}
      <p class="small">Rebuild with <code>python3 evaluation/run_evaluation.py</code>. The full argument, literature mapping, and limitations are in <code>evaluation/EVALUATION_REPORT.md</code>. <a href="#/docs/limitations">Data Quality and Limitations</a></p>
    `;
  }

  root.EvaluationPage = { body };
})(window);
