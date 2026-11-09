/* Versioned WS12 printed-item review. Historical source files remain unchanged. */
(function (root) {
  "use strict";
  const data = root.WS12_REVIEW;
  if (!data || !root.CORE) return;
  const labels = { correct: "Correct", incorrect: "Wrong", partial: "Partial", blank: "Blank", structural_na: "| · Valid stop", unknown: "Unverified" };
  const classes = { correct: "gc-correct", incorrect: "gc-wrong", partial: "gc-partial", blank: "ws12-blank", structural_na: "gc-stop", unknown: "gc-na" };
  const h = (v) => String(v == null ? "" : v).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const source = root.STRUCTURAL_STOPPING ? "downloads/stopping_review/ws12_scoring.json" : "downloads/ws12_review/scoring.json";
  const meta = root.CORE.worksheets.find((w) => w.code === "WS12");
  if (meta) {
    meta.rubric_data = data.rubric;
    meta.pipeline = "deterministic_reviewed_scan";
    meta.fields_in_schema = data.fields.length;
  }
  if (root.WORKSHEET_DOCS && root.WORKSHEET_DOCS.worksheets.WS12) {
    root.WORKSHEET_DOCS.worksheets.WS12.fields = data.fields;
    root.WORKSHEET_DOCS.worksheets.WS12.schema_note = data.rubric.note;
  }
  // Prevent every other site view from using superseded aggregate totals/colors.
  // No complete score is published while applicable printed items are unverified.
  data.groups.forEach((group) => group.students.forEach((student) => {
    const rec = root.CORE.ws[student].WS12;
    rec.revision = data.version;
    rec.historical_scoring_source = "students/" + student + "/WS12/scoring.json";
    rec.scoring = null;
    rec.stage = Object.assign({}, rec.stage, { scoring: {
      source: source, total: null, max: null, percent: null,
      n_items: 15, n_review: group.status_counts.unknown || 0,
      note: "Revised WS12 assessment: complete total withheld because applicable items remain unverified. Open Worksheet findings for all 15 printed-item statuses.",
      items: group.items
    }});
    rec.ocr = {
      source: "downloads/ws12_review/observations.json", modified: "2026-11-09",
      responses: group.items.map((it) => ({ path: it.item, item: it.item,
        value: it.response_state === "blank" ? "(bos)" : it.value })),
      checks: group.items.map((it) => ({ check: "item_checks." + it.item,
        correct: it.status === "correct" ? true : it.status === "incorrect" ? false : null,
        flag: it.status, note: it.note, detail: { status: it.status, page: it.page } })),
      other_validation: [], page_notes: group.note, raw_diff: []
    };
    if (root.SCORE_EXTRA) {
      if (root.SCORE_EXTRA.notes[student]) delete root.SCORE_EXTRA.notes[student].WS12;
      if (root.SCORE_EXTRA.status[student]) delete root.SCORE_EXTRA.status[student].WS12;
    }
  }));
  const statusBadge = (status) => `<span class="gc-legend ${classes[status]}">${h(labels[status])}</span>`;
  function value(it) {
    return it.value == null ? (it.status === "structural_na" ? "—" : "Blank response region") : String(it.value);
  }
  function render() {
    const groups = data.groups;
    const statusCounts = {};
    groups.forEach((g) => g.items.forEach((it) => { statusCounts[it.status] = (statusCounts[it.status] || 0) + g.students.length; }));
    const legend = Object.keys(labels).map(statusBadge).join(" ");
    const columns = Object.values(data.rubric.items);
    const grid = `<div class="table-wrap"><table class="find-table answer-grid transposed"><caption>WS12 · 15 printed items · 13 participant records from 7 shared scans</caption><thead><tr><th scope="col">Student / PDF page</th>${columns.map((it) => `<th scope="col">${h(it.label)}</th>`).join("")}</tr></thead><tbody>${groups.flatMap((g) => g.students.map((s) => `<tr><th scope="row">${h(s)}<div class="small">Page ${g.page}</div></th>${g.items.map((it) => `<td class="gc-cell ${classes[it.status]}" data-label="${h(columns[Number(it.printed_item_id)-1].label)}" title="${h(it.note)}">${statusBadge(it.status)}<div>${h(value(it))}</div></td>`).join("")}</tr>`)).join("")}</tbody></table></div>`;
    const details = groups.map((g) => `<details class="sr-accordion"><summary class="sr-summary"><span class="sr-name">${h(g.students.join(" & "))} · page ${g.page}</span><span>${g.status_counts.correct || 0} consistent · ${g.status_counts.structural_na || 0} not applicable · ${g.status_counts.unknown || 0} unverified</span></summary><div class="sr-body"><p>${h(g.note)}</p><p><a href="${h(data.source_pdf)}#page=${g.page}" target="_blank" rel="noopener">Open shared scan · page ${g.page}</a></p><div class="table-wrap"><table class="find-table"><thead><tr><th scope="col">Printed item</th><th scope="col">Observed response</th><th scope="col">Result</th><th scope="col">Reason</th></tr></thead><tbody>${g.items.map((it) => `<tr><th scope="row">${h(columns[Number(it.printed_item_id)-1].label)}</th><td data-label="Observed response">${h(value(it))}</td><td data-label="Result">${statusBadge(it.status)}</td><td data-label="Reason">${h(it.note)}</td></tr>`).join("")}</tbody></table></div><p class="small">Count checks: ${g.count_diagnostics.map((d) => h(d.node + ": " + d.status + ". " + d.note)).join(" ")}</p></div></details>`).join("");
    const stats = Object.keys(labels).map((status) => `<tr><th scope="row">${statusBadge(status)}</th><td data-label="Participant–item records">${statusCounts[status] || 0}</td></tr>`).join("");
    return `<div class="page wide find-page ws12-review"><p><a href="#/findings/worksheets">Worksheet findings</a> / WS12</p><p class="kicker">2026 · Revised ${h(data.version)}</p><h1>WS12 · Decision tree documentation</h1>
      <p class="lead">Printed-item assessment from manually reviewed scans. Decisions, class counts and unused branches are checked separately.</p>
      <p><strong>13 students · 7 shared submissions · 15 printed items.</strong> Complete worksheet totals are withheld while applicable items remain unverified. “Correct” here means local internal consistency under the revised rubric, not verified optimality or agreement with the human coder.</p>
      <section class="section-block" id="answer-grid"><h2>Answer grid</h2><p>${legend}</p><p class="small">| means an accepted correct stopping action: no extension is required. This is distinct from an answered item receiving full credit. Unused fields earn no extra graded points. Researcher-confirmed exceptions and their prior statuses are documented below. Unverified is distinct from blank and wrong. Hover for the reason or expand a shared submission below.</p>${grid}</section>
      <section class="section-block" id="participants"><h2>Student results · shared submissions</h2>${details}<p>No submitted WS12:${h(data.absent.join(", "))}.</p></section>
      <section class="section-block" id="items"><h2>Coverage by participant record</h2><p>The 195 cells below represent 13 students × 15 items. Paired students share the same scan; these are not 195 independent observations.</p><table class="find-table"><thead><tr><th scope="col">Status</th><th scope="col">Participant–item records</th></tr></thead><tbody>${stats}</tbody></table></section>
      <section class="section-block" id="method"><h2>Revised rubric and provenance</h2><ul>${data.limitations.map((s) => `<li>${h(s)}</li>`).join("")}</ul><p>Slots 10–13 are terminal decisions; 14/15 are training/test errors. Numeric counts and the predicted class remain separate. Ambiguous operators receive no inferred complement. Base consistency checks do not use human labels. Specific stopping exceptions were accepted using human applicability codes, are identified in each item note, and are not blind machine predictions. Historical composite scoring files are retained and superseded in this site view.</p><p><a href="downloads/ws12_review/rubric.json">Base rubric</a> · <a href="downloads/stopping_review/policy.json">Accepted stopping policy and provenance</a> · <a href="downloads/ws12_review/observations.json">Reviewed observations</a> · <a href="${source}">Revised results and reasons</a> · <a href="#/explore/worksheet/WS12">Collected worksheet files</a></p></section></div>`;
  }
  root.WS12Review = { render: render, data: data };
})(typeof window !== "undefined" ? window : globalThis);
