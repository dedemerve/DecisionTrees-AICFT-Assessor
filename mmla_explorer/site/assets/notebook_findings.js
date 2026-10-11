/* Final-homework findings.
   Notebook structure is read from window.NOTEBOOK_EVIDENCE, built by
   scripts/extract_notebook_evidence.py from the notebook files and the
   stored inspection records. Rubric totals stay in window.CORE and are
   not recalculated. A written report has no notebook cell counts. */
(function (root) {
  "use strict";

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v, d = 0) => (v == null || Number.isNaN(Number(v))) ? "–" :
    Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const sum = (arr) => arr.reduce((a, b) => a + b, 0);
  const na = '<span class="na">–</span>';
  const STATUS = { found: "Found", not_found: "Not in file", undetermined: "Not determined" };

  function nameList(names) {
    const a = names.slice().sort((x, y) => x.localeCompare(y));
    if (a.length < 2) return a.join("");
    if (a.length === 2) return a[0] + " and " + a[1];
    return a.slice(0, -1).join(", ") + ", and " + a[a.length - 1];
  }
  function median(values) {
    const a = values.slice().sort((x, y) => x - y);
    if (!a.length) return null;
    const i = Math.floor(a.length / 2);
    return a.length % 2 ? a[i] : (a[i - 1] + a[i]) / 2;
  }
  function sectionTotal(sections, key) {
    const values = Object.values(sections || {}).map((x) => x[key]);
    if (!values.length || values.some((v) => v == null || Number.isNaN(Number(v)))) return null;
    return sum(values.map(Number));
  }
  function tally(rows, keyFn) {
    const map = new Map();
    rows.forEach((r) => {
      const k = keyFn(r);
      if (k == null || k === "") return;
      if (!map.has(k)) map.set(k, []);
      map.get(k).push(r);
    });
    return [...map.entries()].sort((a, b) => b[1].length - a[1].length || String(a[0]).localeCompare(String(b[0])));
  }

  function analyze(core, evidence) {
    const pack = evidence || { rows: [], tasks: [], cell_count_disagreements: [] };
    const byName = {};
    (pack.rows || []).forEach((r) => { byName[r.student] = r; });
    const rows = (core.students || []).map((s) => {
      const n = (core.notebooks || {})[s] || {};
      const scoring = n.scoring || null;
      const ev = byName[s] || null;
      const ins = ev ? ev.inspection : null;
      return {
        s,
        kind: ev ? ev.kind : (n.file ? "notebook" : "report"),
        file: ev ? ev.file : null,
        inspection: ins,
        awarded: scoring ? sectionTotal(scoring.sections, "awarded") : null,
        possible: scoring ? sectionTotal(scoring.sections, "possible") : null,
        scoredBy: scoring ? scoring.scored_by || null : null,
        rubricVersion: scoring ? scoring.rubric_version || null : null,
      };
    });
    const notebooks = rows.filter((r) => r.kind === "notebook");
    const reports = rows.filter((r) => r.kind === "report");
    const scored = rows.filter((r) => r.awarded != null && r.possible != null);
    const possibles = [...new Set(scored.map((r) => r.possible))];
    return {
      rows,
      notebooks,
      reports,
      tasks: pack.tasks || [],
      disagreements: pack.cell_count_disagreements || [],
      scored,
      samePossible: possibles.length === 1 ? possibles[0] : null,
      medianAwarded: median(scored.map((r) => r.awarded)),
      minAwarded: scored.length ? Math.min(...scored.map((r) => r.awarded)) : null,
      maxAwarded: scored.length ? Math.max(...scored.map((r) => r.awarded)) : null,
    };
  }

  function card(value, label, note) {
    return `<div class="stat-card"><div class="v">${value}</div><div class="l">${h(label)}</div>${note ? `<p class="small">${note}</p>` : ""}</div>`;
  }
  function bar(n, total) {
    const w = total ? Math.max(0, Math.min(100, Math.round(100 * n / total))) : 0;
    return `<span class="find-bar" aria-hidden="true"><span style="width:${w}%"></span></span>`;
  }
  function panel(title, body, note) {
    return `<section class="find-panel"><h3>${h(title)}</h3>${body}${note ? `<p class="small">${note}</p>` : ""}</section>`;
  }

  function cards(model) {
    const cohort = model.rows.length;
    const nNote = model.notebooks.length;
    const reportNames = nameList(model.reports.map((r) => r.s));
    const groups = tally(model.notebooks.filter((r) => r.inspection && r.inspection.stored_model_count != null), (r) => r.inspection.stored_model_count);
    const mode = groups.length && (groups.length === 1 || groups[0][1].length > groups[1][1].length) ? groups[0][0] : null;
    const modeNote = groups.map(([k, names]) => names.length === 1 ? `One records ${num(k)}` : `${num(names.length)} of ${num(groups.reduce((a, g) => a + g[1].length, 0))} record ${num(k)}`).join(". ") + ".";
    const errs = model.notebooks.filter((r) => r.file && r.file.cells_with_error > 0);
    const upload = errs.length && errs.every((r) => r.file.upload_interrupt && (r.file.error_types || []).join() === "KeyboardInterrupt");
    const errNote = upload ? "Each one is a KeyboardInterrupt on a file upload." : "A stored output whose type is error.";
    const rubricValue = model.medianAwarded == null ? "–" : (model.samePossible != null ? `${num(model.medianAwarded, 1)} of ${num(model.samePossible, 1)}` : num(model.medianAwarded, 1));
    return `<div class="stat-row cols-4 find-headline">
      ${card(`${num(nNote)} of ${num(cohort)}`, "Inspectable notebooks", reportNames ? `${h(reportNames)} submitted a written report.` : "")}
      ${card(mode == null ? "–" : num(mode), "Most common model count", modeNote)}
      ${card(`${num(errs.length)} of ${num(nNote)}`, "Stored error outputs", errNote)}
      ${card(rubricValue, "Median stored rubric points", `Pipeline total for ${num(model.scored.length)} files, not a reviewed grade.`)}
    </div>`;
  }

  function targetPanel(model) {
    const withTargets = model.rows.filter((r) => r.inspection && r.inspection.targets && r.inspection.targets.length);
    const groups = tally(withTargets, (r) => r.inspection.targets[0]);
    const total = withTargets.length;
    const body = `<table class="find-mini"><tbody>${groups.map(([name, rows]) => `<tr><th>${h(name)}</th><td class="num">${num(rows.length)} of ${num(total)}</td><td>${bar(rows.length, total)}</td></tr>`).join("")}</tbody></table>`;
    return panel("First stored target", body, "Order stored in the inspection. Not a record of how the target was chosen.");
  }
  function modelPanel(model) {
    const groups = tally(model.rows.filter((r) => r.inspection && r.inspection.stored_model_count != null), (r) => r.inspection.stored_model_count);
    const total = model.rows.filter((r) => r.inspection && r.inspection.stored_model_count != null).length;
    const body = `<table class="find-mini"><tbody>${groups.map(([k, rows]) => `<tr><th>${num(k)}</th><td class="num">${num(rows.length)} of ${num(total)}</td><td>${bar(rows.length, total)}</td></tr>`).join("")}</tbody></table>`;
    return panel("Stored model count", body, "The number stored on the inspection record.");
  }
  function taskPanel(model) {
    const total = model.rows.length;
    const body = `<table class="find-mini find-tasks"><thead><tr><th>Assignment evidence</th><th class="num">Found</th><th class="num">Not in file</th><th class="num">Not determined</th></tr></thead><tbody>${
      model.tasks.map((task) => {
        const counts = { found: 0, not_found: 0, undetermined: 0 };
        model.rows.forEach((r) => {
          const v = r.inspection && r.inspection.tasks ? r.inspection.tasks[task.id] : "undetermined";
          counts[v] = (counts[v] || 0) + 1;
        });
        return `<tr><th>${h(task.label)}</th><td class="num">${num(counts.found)} of ${num(total)} ${bar(counts.found, total)}</td><td class="num">${num(counts.not_found)}</td><td class="num">${num(counts.undetermined)}</td></tr>`;
      }).join("")
    }</tbody></table>`;
    return `<section class="find-panel find-panel-wide">${body}<p class="small">Found means the inspection stored that evidence. Not in file means it was not stored. That is not a judgement that the step never happened.</p></section>`;
  }

  function patterns(model) {
    const items = [];
    const sized = model.rows.filter((r) => r.inspection && r.inspection.test_size != null);
    const sizeGroups = tally(sized, (r) => r.inspection.test_size);
    if (sizeGroups.length > 1) {
      const [mode, modeRows] = sizeGroups[0];
      const rest = sizeGroups.slice(1).map(([k, rows]) => `${nameList(rows.map((r) => r.s))} records ${k}`);
      items.push(`${num(modeRows.length)} of ${num(sized.length)} files record a test fraction of ${mode}. ${rest.join(". ")}.`);
    }
    const odd = model.rows.filter((r) => r.inspection && r.inspection.stored_model_count != null && r.inspection.stored_model_count !== r.inspection.depth_search_records);
    odd.forEach((r) => {
      items.push(`${r.s}'s stored model count is ${num(r.inspection.stored_model_count)}. The inspection lists ${num(r.inspection.depth_search_records)} depth-search record${r.inspection.depth_search_records === 1 ? "" : "s"} and ${num(r.inspection.preliminary_models)} preliminary model${r.inspection.preliminary_models === 1 ? "" : "s"}.`);
    });
    const synthetic = model.rows.filter((r) => r.inspection && r.inspection.synthetic === true);
    if (synthetic.length) items.push(`${nameList(synthetic.map((r) => r.s))}: the inspection records a substitute table rather than the original lizard file.`);
    const back = model.notebooks.filter((r) => r.file && r.file.order_reversals > 0);
    if (back.length) {
      const once = back.every((r) => r.file.order_reversals === 1);
      items.push(`The run counter goes backwards in ${num(back.length)} of ${num(model.notebooks.length)} notebooks: ${nameList(back.map((r) => r.s))}${once ? ", once each" : ""}.`);
    }
    if (!items.length) return "";
    return `<section class="find-panel find-panel-wide"><h3>Patterns worth noting</h3><ul class="find-notes">${items.map((t) => `<li>${t}</li>`).join("")}</ul></section>`;
  }

  function depthCell(r) {
    if (!r.inspection) return na;
    const n = r.inspection.depth_search_records;
    const t = r.inspection.depth_tables;
    if (n == null) return na;
    if (!n) return na;
    if (!t) return "Not stored";
    return `${num(t)} of ${num(n)}`;
  }
  function rubricText(r) {
    if (r.awarded == null) return na;
    if (r.possible == null) return num(r.awarded, 1);
    return `${num(r.awarded, 1)} of ${num(r.possible, 1)}`;
  }
  function statusText(v) {
    return STATUS[v] || "Not determined";
  }

  function detail(r, tasks) {
    const bits = [];
    if (r.kind === "report") bits.push("<p>Read from the written report. Notebook cell counts and run counters are not available.</p>");
    if (r.file) {
      const f = r.file;
      const codeNoun = f.code_cells === 1 ? "code cell" : "code cells";
      const textNoun = f.markdown_cells === 1 ? "text cell" : "text cells";
      const outNoun = f.cells_with_output === 1 ? "code cell has" : "code cells have";
      let counter = "Every code cell has a run counter.";
      if (f.code_without_execution_count) {
        const gapNoun = f.code_without_execution_count === 1 ? "code cell has" : "code cells have";
        counter = `${num(f.code_without_execution_count)} ${gapNoun} no run counter.`;
        if (f.cells_with_output) counter += " A missing counter is not treated as an unrun cell, because a stored output can remain after a kernel restart.";
      }
      bits.push(`<p>${num(f.code_cells)} ${codeNoun} and ${num(f.markdown_cells)} ${textNoun}. ${num(f.cells_with_output)} ${outNoun} a stored output. ${counter}</p>`);
      if (f.cells_with_error) bits.push(`<p>Stored error: ${h((f.error_types || []).join(", ") || "error")}.${f.upload_interrupt ? " The cell calls a file upload." : ""}</p>`);
      const missing = Object.entries(f.code_present || {}).filter(([, v]) => !v).map(([k]) => k);
      bits.push(`<p>${missing.length ? "Not found in the code text: " + missing.map(h).join(", ") + "." : "The checked code names are present in the code text."}</p>`);
    }
    if (r.inspection && r.inspection.depths && r.inspection.depths.length) {
      const chosen = r.inspection.depths.filter((d) => d.chosen != null).map((d) => `${h(d.target)} ${num(d.chosen)}`);
      if (chosen.length) bits.push(`<p>Recorded depth choice: ${chosen.join(", ")}.</p>`);
    }
    if (tasks.length && r.inspection && r.inspection.tasks) {
      bits.push(`<div class="find-check">${tasks.map((t) => `<span>${h(t.label)}</span><span class="st st-${h(r.inspection.tasks[t.id] || "undetermined")}">${h(statusText(r.inspection.tasks[t.id]))}</span>`).join("")}</div>`);
    }
    return bits.join("");
  }

  function table(model) {
    const head = ["Participant", "Target variables", "Models", "Depth table", "Stored rubric points", "Details"];
    const body = model.rows.map((r) => {
      const targets = r.inspection && r.inspection.targets && r.inspection.targets.length
        ? `<span class="find-targets">${r.inspection.targets.map(h).join(", ")}</span>` : na;
      const models = r.inspection && r.inspection.stored_model_count != null ? num(r.inspection.stored_model_count) : na;
      const kind = r.kind === "report" ? ` <span class="find-kind">Written report</span>` : "";
      const cells = [
        `${h(r.s)}${kind}`,
        targets,
        models,
        depthCell(r),
        rubricText(r),
        `<button type="button" class="find-toggle" data-nb="${h(r.s)}" aria-expanded="false">Details</button>`,
      ];
      const main = `<tr>${cells.map((c, i) => `<td${i >= 2 && i < 5 ? ' class="num"' : ""} data-label="${h(head[i])}">${c}</td>`).join("")}</tr>`;
      const extra = `<tr id="nb-${h(r.s)}" class="find-extra" hidden><td colspan="6" data-label="Details">${detail(r, model.tasks)}</td></tr>`;
      return main + extra;
    }).join("");
    return `<h2>Participant results</h2>
      <div class="table-wrap"><table class="find-table find-people">
        <thead><tr>${head.map((t, i) => `<th${i >= 2 && i < 5 ? ' class="num"' : ""}>${h(t)}</th>`).join("")}</tr></thead>
        <tbody>${body}</tbody>
      </table></div>
      <p class="small">A dash means the measure was not available. Not stored is not a zero.</p>`;
  }

  function method(model) {
    const versions = [...new Set(model.scored.map((r) => r.rubricVersion).filter(Boolean))];
    const scorers = [...new Set(model.scored.map((r) => r.scoredBy).filter(Boolean))];
    const reportNames = nameList(model.reports.map((r) => r.s));
    const disagree = model.disagreements || [];
    return `<details class="find-fold" id="method">
      <summary>Methodology and data quality</summary>
      <div class="find-fold-body">
        <ul class="find-notes">
          <li>The 15 final homework files were inspected. Weekly Colab notebooks and the teacher instruction notebook are not included.</li>
          <li>Cell counts, run counters, and stored error names are read from the current notebook file. The notebook is not executed.</li>
          <li>A model count is the number stored on the inspection record. It is not the number of times a classifier name appears in the code.</li>
          <li>Depth-search records and preliminary models are separate lists. This page does not add them together.</li>
          <li>An error output is a stored output of type error. A KeyboardInterrupt on a file upload is an upload interrupt, not a judgement of the model.</li>
          <li>Assignment evidence is marked found, not in the file, or not determined. A missing step is not evidence that the participant never did it.</li>
          <li>A run counter that goes backwards shows that an earlier cell was executed again. It does not show why.</li>
          ${disagree.length ? `<li>For ${num(disagree.length)} of ${num(model.notebooks.length)} notebooks, cell counts in the older inspection record differ from the current file (${h(nameList(disagree))}). This page uses the current file and does not change that record.</li>` : ""}
          <li>Stored rubric points are the unchanged pipeline totals${scorers.length === 1 ? `, recorded as ${h(scorers[0])}` : ""}${versions.length === 1 ? `, rubric ${h(versions[0])}` : ""}. They are not a reviewed grade, and a higher total is not a learning gain.</li>
          <li>${reportNames ? `${h(reportNames)} submitted a written report. Target, model, and rubric fields that the inspection stored are shown. Notebook cell counts and run counters are left blank.` : "Every file in this table is a notebook."}</li>
        </ul>
      </div>
    </details>`;
  }

  function page(core, evidence) {
    const model = analyze(core || root.CORE, evidence || root.NOTEBOOK_EVIDENCE);
    const reportNames = nameList(model.reports.map((r) => r.s));
    const lead = `Final homework files only. ${num(model.notebooks.length)} of ${num(model.rows.length)} are notebooks${reportNames ? `; ${h(reportNames)} submitted a written report` : ""}. The teacher instruction notebook and the weekly Colab notebooks are separate, and these files are not a record of the guided sessions.`;
    return `<p class="lead">${lead}</p>
      ${cards(model)}
      <h2>Overall patterns</h2>
      <div class="find-board">${targetPanel(model)}${modelPanel(model)}</div>
      ${taskPanel(model)}
      ${patterns(model)}
      ${table(model)}
      ${method(model)}`;
  }

  function bind() {
    document.querySelectorAll(".find-toggle").forEach((btn) => {
      btn.addEventListener("click", () => {
        const row = document.getElementById("nb-" + btn.getAttribute("data-nb"));
        if (!row) return;
        const open = row.hasAttribute("hidden");
        if (open) row.removeAttribute("hidden");
        else row.setAttribute("hidden", "");
        btn.setAttribute("aria-expanded", open ? "true" : "false");
        btn.textContent = open ? "Hide" : "Details";
      });
    });
  }

  root.NotebookFindings = { analyze, page, bind };
})(typeof window !== "undefined" ? window : globalThis);
