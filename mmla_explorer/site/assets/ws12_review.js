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
  // Same tree roles as WS6, plus the two error-count fields. Every printed item
  // belongs to exactly one display group; no canonical feature/threshold is used.
  const columns = [
    { id: "root_feature", label: "Blank 1 · Root Feature", printed: [1] },
    { id: "root_split", label: "Blank 2–3 · Root Split Cond.", printed: [2, 3] },
    { id: "inner_left", label: "Blank 4 · Internal Node (L)", printed: [4] },
    { id: "threshold_left", label: "Blank 6–7 · Sub-Branch (L)", printed: [6, 7] },
    { id: "terminal_left", label: "Blank 10–11 · Terminal (L)", printed: [10, 11] },
    { id: "inner_right", label: "Blank 5 · Internal Node (R)", printed: [5] },
    { id: "threshold_right", label: "Blank 8–9 · Sub-Branch (R)", printed: [8, 9] },
    { id: "terminal_right", label: "Blank 12–13 · Terminal (R)", printed: [12, 13] },
    { id: "train_errors", label: "Blank 14 · Training Errors", printed: [14] },
    { id: "test_errors", label: "Blank 15 · Test Errors", printed: [15] },
  ];
  function combinedStatus(items) {
    const statuses = items.map((it) => it ? it.status : "unknown");
    if (statuses.includes("incorrect")) return "incorrect";
    if (statuses.every((s) => s === "structural_na")) return "structural_na";
    if (statuses.some((s) => s === "unknown" || s === "structural_na")) return "unknown";
    if (statuses.every((s) => s === "correct")) return "correct";
    if (statuses.every((s) => s === "blank")) return "blank";
    return "partial";
  }
  function responseText(it) {
    if (!it || it.value == null) return !it || it.status === "unknown" ? "?" : "–";
    // Counts are visible evidence, not a fabricated class label or answer key.
    if (typeof it.value === "string" && it.value.startsWith("Counts: ") && it.count_evidence) {
      return `${it.count_evidence[0]} R / ${it.count_evidence[1]} NR`;
    }
    return String(it.value);
  }
  function displayItems(group) {
    const byId = new Map(group.items.map((it) => [Number(it.printed_item_id), it]));
    return columns.map((col) => {
      const items = col.printed.map((n) => byId.get(n));
      return { id: col.id, label: col.label, printed: col.printed, items: items,
        status: combinedStatus(items), response: items.map(responseText).join(" | "),
        note: items.map((it, i) => `Item ${col.printed[i]} (${it ? labels[it.status] : "Unverified"}): ${it ? it.note : "No item record."}`).join("\n") };
    });
  }
  function render() {
    const groupByStudent = new Map();
    data.groups.forEach((g) => g.students.forEach((s) => groupByStudent.set(s, g)));
    const students = root.CORE.students.filter((s) => groupByStudent.has(s));
    const statusCounts = {};
    const displayByStudent = new Map(students.map((s) => [s, displayItems(groupByStudent.get(s))]));
    displayByStudent.forEach((items) => items.forEach((it) => { statusCounts[it.status] = (statusCounts[it.status] || 0) + 1; }));
    const legend = ["correct", "partial", "incorrect", "blank", "structural_na", "unknown"].map(statusBadge).join(" ");
    const cellValue = (it) => it.status === "structural_na" ? statusBadge(it.status) : h(it.response);
    const grid = `<div class="table-wrap"><table class="find-table answer-grid transposed ws12-grid"><caption class="sr-only">WS12: 13 students; 10 displayed groups covering 15 printed items. Colors show each student's own recorded tree checks.</caption><thead><tr><th class="gc-student-head" scope="col">Student</th>${columns.map((col) => `<th class="gc-head" scope="col">${h(col.label)}</th>`).join("")}</tr></thead><tbody>${students.map((student) => `<tr><th class="gc-student-name" scope="row">${h(student)}</th>${displayByStudent.get(student).map((it) => `<td class="gc-cell ${classes[it.status]}" data-cell-id="${h(it.id)}" data-printed-items="${it.printed.join(",")}" data-verdict="${h(it.status)}" data-label="${h(it.label)}" aria-label="${h(it.label + ": " + labels[it.status] + ". " + it.response)}" title="${h(labels[it.status] + ". " + it.note)}">${cellValue(it)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
    const details = students.map((student) => {
      const group = groupByStudent.get(student), items = displayByStudent.get(student);
      const correct = items.filter((it) => it.status === "correct").length;
      const checked = items.filter((it) => ["correct", "incorrect", "partial", "blank"].includes(it.status)).length;
      const unknown = items.filter((it) => it.status === "unknown").length;
      const stops = items.filter((it) => it.status === "structural_na").length;
      const shared = group.students.filter((s) => s !== student);
      const summary = `${correct} / ${checked} checked correct${unknown ? " · " + unknown + " unverified" : ""}${stops ? " · " + stops + " valid stops (separate)" : ""}`;
      return `<details class="sr-accordion"><summary class="sr-summary"><span class="sr-name">${h(student)}</span><span class="ws12-result-summary">${h(summary)}</span></summary><div class="sr-body"><p class="small">${shared.length ? "Shared sheet with " + h(shared.join(", ")) + ". " : ""}<a href="${h(data.source_pdf)}#page=${group.page}" target="_blank" rel="noopener">Open scan · page ${group.page}</a>. Unverified groups are outside the checked denominator.</p><div class="table-wrap"><table class="find-table"><thead><tr><th scope="col">Blank</th><th scope="col">Written answer</th><th scope="col">Result</th></tr></thead><tbody>${items.map((it) => `<tr><th scope="row">${h(it.label)}</th><td data-label="Written answer"><span class="written-answer">${h(it.response)}</span></td><td data-label="Result">${statusBadge(it.status)}<details class="ws12-item-note"><summary>Check details</summary><p class="small">${h(it.note).replace(/\n/g, "<br>")}</p></details></td></tr>`).join("")}</tbody></table></div></div></details>`;
    }).join("");
    const stats = Object.keys(labels).map((status) => `<tr><th scope="row">${statusBadge(status)}</th><td data-label="Displayed student–group cells">${statusCounts[status] || 0}</td></tr>`).join("");
    return `<div class="page wide find-page ws12-review"><p><a href="#/findings/worksheets">Worksheet findings</a> / WS12</p><p class="kicker">2026 · Revised ${h(data.version)}</p><h1>WS12 · Decision tree documentation</h1>
      <p class="lead">Each student's recorded tree is checked for internal consistency. Features, thresholds and decisions can differ between students; there is no shared answer key.</p>
      <section class="section-block" id="answer-grid"><h3>Answer grid <span class="small grid-toggle-hint">${legend}</span></h3><p class="small">Columns follow the same tree structure as WS6. Colors combine the listed printed-item checks; hover for the reason. | marks an accepted correct stopping action, separately from graded answers. R / NR are recorded recommended / not-recommended counts, not an inferred class decision. – marks a blank field; ? marks an unverified field.</p>${grid}</section>
      <section id="participants"><details class="answer-grid-toggle"><summary><h3 class="inline-h3">Student results</h3></summary><p class="small">Click a student to expand their own answers and checks. Paired students share a scan.</p><div class="student-results">${details}</div></details></section>
      <details class="find-fold" id="items"><summary>Coverage and grouping</summary><div class="find-fold-body"><p>13 students share 7 scans. The 10 displayed groups cover all 15 printed items once. Grouping changes the displayed observation unit; the underlying printed-item judgments are preserved. A wrong component makes a group wrong; unresolved or mixed-applicability components prevent a full-correct group. Unused descendants are not extra correct answers. No submitted WS12: ${h(data.absent.join(", "))}.</p><table class="find-table"><thead><tr><th scope="col">Status</th><th scope="col">Displayed student–group cells</th></tr></thead><tbody>${stats}</tbody></table></div></details>
      <details class="find-fold" id="method"><summary>Method and sources</summary><div class="find-fold-body"><ul>${data.limitations.map((s) => `<li>${h(s)}</li>`).join("")}</ul><p>Only the current student's own fields are combined. Original printed-item judgments, reasons and provenance remain available. Base checks do not use human labels; specific stopping exceptions were accepted using human applicability codes and are not blind machine predictions. Historical composite scores are superseded in this view. Test-error values are recorded but cannot be verified without test cards.</p><p><a href="downloads/ws12_review/rubric.json">Base rubric</a> · <a href="downloads/stopping_review/policy.json">Accepted stopping policy and provenance</a> · <a href="downloads/ws12_review/observations.json">Reviewed observations</a> · <a href="${source}">Printed-item results and reasons</a> · <a href="#/explore/worksheet/WS12">Collected worksheet files</a></p></div></details></div>`;
  }
  root.WS12Review = { render: render, data: data, columns: columns, displayItems: displayItems, combinedStatus: combinedStatus };
})(typeof window !== "undefined" ? window : globalThis);
