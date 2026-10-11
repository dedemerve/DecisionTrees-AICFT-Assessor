/* Final-homework findings, organised by the four dimensions on page 8 of the
   assignment. Evidence status comes from window.NOTEBOOK_EVIDENCE. Rubric
   totals stay in window.CORE and are not recalculated. Evidence found is
   not a mark that the task was completed correctly. */
(function (root) {
  "use strict";

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v, d = 0) => (v == null || Number.isNaN(Number(v))) ? "–" :
    Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const sum = (arr) => arr.reduce((a, b) => a + b, 0);
  const na = '<span class="na">–</span>';

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
  function checks(r) {
    return (r.inspection && r.inspection.checks) || null;
  }

  function analyze(core, evidence) {
    const pack = evidence || { rows: [], cell_count_disagreements: [] };
    const byName = {};
    (pack.rows || []).forEach((r) => { byName[r.student] = r; });
    const rows = (core.students || []).map((s) => {
      const n = (core.notebooks || {})[s] || {};
      const scoring = n.scoring || null;
      const ev = byName[s] || null;
      return {
        s,
        kind: ev ? ev.kind : (n.file ? "notebook" : "report"),
        file: ev ? ev.file : null,
        inspection: ev ? ev.inspection : null,
        awarded: scoring ? sectionTotal(scoring.sections, "awarded") : null,
        possible: scoring ? sectionTotal(scoring.sections, "possible") : null,
        scoredBy: scoring ? scoring.scored_by || null : null,
        rubricVersion: scoring ? scoring.rubric_version || null : null,
      };
    });
    const scored = rows.filter((r) => r.awarded != null && r.possible != null);
    const possibles = [...new Set(scored.map((r) => r.possible))];
    return {
      rows,
      notebooks: rows.filter((r) => r.kind === "notebook"),
      reports: rows.filter((r) => r.kind === "report"),
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
  function has(rows, pred) {
    return rows.filter(pred);
  }
  function ofTotal(n, total) {
    return `${num(n)} of ${num(total)}`;
  }

  function cards(model) {
    const total = model.rows.length;
    const tables = has(model.rows, (r) => checks(r) && checks(r).depth_tables > 0);
    const comments = has(model.rows, (r) => checks(r) && checks(r).depth_comments > 0);
    const codap = has(model.rows, (r) => checks(r) && checks(r).codap_notes > 0);
    const three = has(model.rows, (r) => checks(r) && checks(r).reflection.all_three);
    const partial = model.rows.filter((r) => {
      const c = checks(r);
      return c && c.depth_records > c.depth_tables && c.depth_tables > 0;
    });
    const partialNote = partial.length
      ? ` ${nameList(partial.map((r) => r.s))} stores a table for ${partial.map((r) => ofTotal(checks(r).depth_tables, checks(r).depth_records)).join("; ")}.`
      : "";
    return `<div class="stat-row cols-4 find-headline">
      ${card(ofTotal(tables.length, total), "Depth-search table stored", `At least one table of training and test error.${partialNote}`)}
      ${card(ofTotal(comments.length, total), "Written comment on depth", "Text stored about how error changes with depth. Not a judgement of that text.")}
      ${card(ofTotal(codap.length, total), "CODAP comparison stored", "A written comparison of the Python tree with a CODAP tree.")}
      ${card(ofTotal(three.length, total), "Three settings named", "Data cards, CODAP, and Python recorded together in the reflection.")}
    </div>`;
  }

  function tally(rows, pick) {
    const out = { found: [], not_found: [], undetermined: [] };
    rows.forEach((r) => {
      const v = pick(r);
      if (out[v]) out[v].push(r.s);
      else out.undetermined.push(r.s);
    });
    return out;
  }
  function evidenceTable(items, total) {
    const body = items.map((item) => {
      const g = tally(item.rows, item.pick);
      return `<tr><th>${h(item.label)}</th><td class="num">${num(g.found.length)} of ${num(total)}</td><td class="num">${num(g.not_found.length)}</td><td class="num">${num(g.undetermined.length)}</td></tr>`;
    }).join("");
    const missing = items.map((item) => {
      const g = tally(item.rows, item.pick);
      const bits = [];
      if (g.not_found.length) bits.push(`Not in file: ${nameList(g.not_found)}`);
      if (g.undetermined.length) bits.push(`Not determined: ${nameList(g.undetermined)}`);
      return bits.length ? `<li>${h(item.label)}. ${h(bits.join(". "))}.</li>` : "";
    }).join("");
    const extra = missing
      ? `<details class="find-fold find-subfold"><summary>Where evidence is missing</summary><div class="find-fold-body"><ul class="find-notes">${missing}</ul></div></details>`
      : "";
    return `<table class="find-mini find-tasks"><thead><tr><th>Evidence</th><th class="num">Found</th><th class="num">Not in file</th><th class="num">Not determined</th></tr></thead><tbody>${body}</tbody></table>${extra}`;
  }

  function section(kicker, title, text, tableHtml) {
    return `<section class="find-dim"><p class="find-kicker">${h(kicker)}</p><h2>${h(title)}</h2><p>${text}</p>${tableHtml}</section>`;
  }

  function exploreSection(model) {
    const rows = model.rows;
    const pick = (key) => (r) => (checks(r) || {})[key];
    return section(
      "Steps 1–2",
      "Data exploration",
      "Loading the lizard table, storing a summary, writing a note, and recording how category columns were turned into numbers.",
      evidenceTable([
        { label: "Lizard table loaded", rows, pick: pick("loaded") },
        { label: "Class counts stored", rows, pick: pick("value_counts") },
        { label: "Numeric summary stored", rows, pick: pick("describe") },
        { label: "Written note on the table", rows, pick: pick("table_notes") },
        { label: "Category encoding recorded", rows, pick: pick("encoding") },
      ], rows.length)
    );
  }
  function modelSection(model) {
    const rows = model.rows;
    const c = (r) => checks(r) || {};
    return section(
      "Steps 3–4",
      "Model construction and evaluation",
      "A train/test split, a comparison of tree depths, and stored training and test error. A printed rate is not compared across participants, because the target and the split can differ.",
      evidenceTable([
        { label: "Test fraction recorded", rows, pick: (r) => c(r).test_size != null ? "found" : "undetermined" },
        { label: "Reproducibility value recorded", rows, pick: (r) => c(r).random_state != null ? "found" : "undetermined" },
        { label: "Stratified split recorded", rows, pick: (r) => c(r).stratify },
        { label: "Written note on stratification", rows, pick: (r) => c(r).stratify_note },
        { label: "Written note on the reproducibility value", rows, pick: (r) => c(r).random_note },
        { label: "Depth-search table stored", rows, pick: (r) => c(r).depth_records ? (c(r).depth_tables > 0 ? "found" : "not_found") : "undetermined" },
        { label: "Training and test curves stored", rows, pick: (r) => c(r).depth_records ? (c(r).both_curves > 0 ? "found" : "not_found") : "undetermined" },
        { label: "Written comment on depth and error", rows, pick: (r) => c(r).depth_records ? (c(r).depth_comments > 0 ? "found" : "not_found") : "undetermined" },
        { label: "Final test error stored", rows, pick: (r) => c(r).depth_records ? (c(r).test_mcr_n > 0 ? "found" : "not_found") : "undetermined" },
      ], rows.length)
    );
  }
  function visualSection(model) {
    const rows = model.rows;
    const c = (r) => checks(r) || {};
    return section(
      "Step 5",
      "Visualisation and interpretation",
      "A saved tree drawing is separate from a written reading of that tree. A drawing does not show that the tree was interpreted.",
      evidenceTable([
        { label: "Tree drawing recorded", rows, pick: (r) => c(r).depth_records ? (c(r).drawings > 0 ? "found" : "not_found") : "undetermined" },
        { label: "Root feature discussed in writing", rows, pick: (r) => c(r).root_written > 0 ? "found" : "not_found" },
        { label: "Written note on the number of decisions", rows, pick: (r) => c(r).decision_notes > 0 ? "found" : "not_found" },
        { label: "CODAP comparison stored", rows, pick: (r) => c(r).codap_notes > 0 ? "found" : "not_found" },
      ], rows.length)
    );
  }
  function reflectionSection(model) {
    const rows = model.rows;
    const ref = (r) => (checks(r) && checks(r).reflection) || {};
    return section(
      "Step 6",
      "Written responses and reflection",
      "Four question groups: the three settings, the lizard data, model performance, and the limits of a decision tree. Stored text is not a mark of how deep the answer is.",
      evidenceTable([
        { label: "Three settings", rows, pick: (r) => ref(r).settings },
        { label: "Understanding the data", rows, pick: (r) => ref(r).data },
        { label: "Model performance", rows, pick: (r) => ref(r).performance },
        { label: "Limits of decision trees", rows, pick: (r) => ref(r).limits },
        { label: "All three settings named in that answer", rows, pick: (r) => ref(r).all_three ? "found" : (ref(r).settings === "found" ? "not_found" : "undetermined") },
      ], rows.length)
    );
  }

  function cohort(model) {
    const total = model.rows.length;
    const items = [];
    const drawn = has(model.rows, (r) => checks(r) && checks(r).drawings > 0);
    if (drawn.length === total) items.push(`A tree drawing is recorded for all ${num(total)} files. The drawing is evidence that a plot was stored, not that the tree was interpreted.`);
    const noTable = model.rows.filter((r) => checks(r) && checks(r).depth_records && !checks(r).depth_tables);
    const partial = model.rows.filter((r) => checks(r) && checks(r).depth_tables > 0 && checks(r).depth_tables < checks(r).depth_records);
    if (noTable.length || partial.length) {
      const bits = [];
      if (noTable.length) bits.push(`No table is stored for ${nameList(noTable.map((r) => r.s))}`);
      if (partial.length) bits.push(`${nameList(partial.map((r) => r.s))} stores a table for ${partial.map((r) => ofTotal(checks(r).depth_tables, checks(r).depth_records)).join("; ")}`);
      items.push(`A depth-search table is stored for ${ofTotal(total - noTable.length, total)} files. ${bits.join(". ")}.`);
    }
    const noComment = model.rows.filter((r) => checks(r) && checks(r).depth_records && !checks(r).depth_comments);
    if (noComment.length) items.push(`A written comment on depth and error is stored for ${ofTotal(total - noComment.length, total)} files. It is not stored for ${nameList(noComment.map((r) => r.s))}.`);
    const q1 = has(model.rows, (r) => checks(r) && checks(r).reflection.settings === "found");
    const three = has(model.rows, (r) => checks(r) && checks(r).reflection.all_three);
    const q1missing = model.rows.filter((r) => checks(r) && checks(r).reflection.settings !== "found").map((r) => r.s);
    items.push(`Text for the three-settings question is stored for ${ofTotal(q1.length, total)} files${q1missing.length ? `, and not stored for ${nameList(q1missing)}` : ""}. The inspection recorded all three names in ${num(three.length)} of the ${num(q1.length)} stored answers.`);
    const sized = model.rows.filter((r) => checks(r) && checks(r).test_size != null);
    const preferred = sized.filter((r) => checks(r).test_size === 0.2);
    const other = sized.filter((r) => checks(r).test_size !== 0.2);
    if (preferred.length && other.length) {
      items.push(`${ofTotal(preferred.length, sized.length)} files with a recorded test fraction use 0.2, the fraction in the assignment. ${other.map((r) => `${r.s} records ${checks(r).test_size}`).join("; ")}.`);
    }
    const curves = has(model.rows, (r) => checks(r) && checks(r).both_curves > 0);
    if (curves.length) items.push(`Training and test curves are both stored for ${ofTotal(curves.length, total)} files, for at least one target. The rates themselves are not lined up across participants, because the target and the split can differ.`);
    if (!items.length) return "";
    return `<section class="find-dim"><h2>What the submissions show</h2><ul class="find-notes">${items.map((t) => `<li>${t}</li>`).join("")}</ul></section>`;
  }

  function ratio(n, d) {
    if (d == null) return na;
    if (!d) return na;
    if (!n) return "Not stored";
    return `${num(n)} of ${num(d)}`;
  }
  function reflectionCount(r) {
    const ref = checks(r) && checks(r).reflection;
    if (!ref) return na;
    const n = ["settings", "data", "performance", "limits"].filter((k) => ref[k] === "found").length;
    return `${num(n)} of 4`;
  }
  function rubricText(r) {
    if (r.awarded == null) return na;
    if (r.possible == null) return num(r.awarded, 1);
    return `${num(r.awarded, 1)} of ${num(r.possible, 1)}`;
  }
  function statusWord(v) {
    if (v === "found") return "Found";
    if (v === "not_found") return "Not in file";
    return "Not determined";
  }

  function detail(r) {
    const c = checks(r);
    const bits = [];
    if (r.kind === "report") bits.push("<p>Written report. Notebook cell counts are not available.</p>");
    if (r.inspection && r.inspection.synthetic) bits.push("<p>The inspection records a substitute table rather than the original lizard file. Rates below come from that table.</p>");
    if (c && c.models && c.models.length) {
      const rows = c.models.map((m) => `<tr><td>${h(m.target)}</td><td class="num">${m.chosen_depth == null ? na : num(m.chosen_depth)}</td><td class="num">${m.test_mcr == null ? na : num(m.test_mcr, 4)}</td><td>${m.table ? "Stored" : "Not stored"}</td><td>${m.drawing ? "Stored" : "Not stored"}</td></tr>`).join("");
      bits.push(`<table class="find-mini"><thead><tr><th>Target</th><th class="num">Chosen depth</th><th class="num">Test error</th><th>Depth table</th><th>Drawing</th></tr></thead><tbody>${rows}</tbody></table><p class="small">Test error is the stored misclassification rate for that target. It is not compared with another participant.</p>`);
    }
    if (c) {
      const lines = [
        ["Class counts", c.value_counts],
        ["Numeric summary", c.describe],
        ["Written note on the table", c.table_notes],
        ["Category encoding", c.encoding],
        ["Stratified split", c.stratify],
        ["Comment on depth", c.depth_comments > 0 ? "found" : "not_found"],
        ["Root feature discussed", c.root_written > 0 ? "found" : "not_found"],
        ["CODAP comparison", c.codap_notes > 0 ? "found" : "not_found"],
        ["Three settings", c.reflection.settings],
        ["Data question", c.reflection.data],
        ["Performance question", c.reflection.performance],
        ["Limits question", c.reflection.limits],
      ];
      bits.push(`<div class="find-check">${lines.map(([label, v]) => `<span>${h(label)}</span><span>${h(statusWord(v))}</span>`).join("")}</div>`);
    }
    if (r.file) {
      const cells = r.file.code_cells === 1 ? "code cell" : "code cells";
      const text = r.file.markdown_cells === 1 ? "text cell" : "text cells";
      bits.push(`<p class="small">${num(r.file.code_cells)} ${cells}, ${num(r.file.markdown_cells)} ${text}, ${num(r.file.cells_with_image)} with a stored image.</p>`);
    }
    return bits.join("");
  }

  function table(model) {
    const head = ["Participant", "Depth table", "Train and test curves", "Tree drawing", "Reflection text", "Stored rubric points", "Details"];
    const body = model.rows.map((r) => {
      const c = checks(r);
      const kind = r.kind === "report" ? ` <span class="find-kind">Written report</span>` : "";
      const cells = [
        `${h(r.s)}${kind}`,
        c ? ratio(c.depth_tables, c.depth_records) : na,
        c ? ratio(c.both_curves, c.depth_records) : na,
        c ? (c.drawings > 0 ? "Recorded" : "Not stored") : na,
        reflectionCount(r),
        rubricText(r),
        `<button type="button" class="find-toggle" data-nb="${h(r.s)}" aria-expanded="false">Details</button>`,
      ];
      const main = `<tr>${cells.map((cell, i) => `<td${i > 0 && i < 6 ? ' class="num"' : ""} data-label="${h(head[i])}">${cell}</td>`).join("")}</tr>`;
      return main + `<tr id="nb-${h(r.s)}" class="find-extra" hidden><td colspan="7" data-label="Details">${detail(r)}</td></tr>`;
    }).join("");
    return `<h2>Participant results</h2>
      <div class="table-wrap"><table class="find-table find-people">
        <thead><tr>${head.map((t, i) => `<th${i > 0 && i < 6 ? ' class="num"' : ""}>${h(t)}</th>`).join("")}</tr></thead>
        <tbody>${body}</tbody>
      </table></div>
      <p class="small">Not stored means the inspection did not find that evidence. A dash means the measure was not available. 0 of 4 means no answer text was stored. None of these is a score.</p>`;
  }

  function method(model) {
    const versions = [...new Set(model.scored.map((r) => r.rubricVersion).filter(Boolean))];
    const scorers = [...new Set(model.scored.map((r) => r.scoredBy).filter(Boolean))];
    const disagree = model.disagreements || [];
    const reportNames = nameList(model.reports.map((r) => r.s));
    return `<details class="find-fold" id="method">
      <summary>Methodology and data quality</summary>
      <div class="find-fold-body"><ul class="find-notes">
        <li>The page follows the four dimensions on the assignment rubric: data exploration, model construction, visualisation, and written responses. Those headings organise the evidence. This page does not assign the rubric’s levels, and it does not calculate a new score.</li>
        <li>Evidence is read from the stored inspection of each final homework file, plus cell counts and image outputs read from the current notebook. Notebooks are not executed.</li>
        <li>Found means the inspection stored that evidence. Not in file means it recorded an absence. Not determined means it did not record a yes or no. None of the three shows that a participant never did the step.</li>
        <li>A test error is shown only beside its own target, and only when the stored rate falls between 0 and 1. Rates are not compared across participants.</li>
        <li>Stored rubric points are the unchanged pipeline totals${scorers.length === 1 ? `, recorded as ${h(scorers[0])}` : ""}${versions.length === 1 ? `, rubric ${h(versions[0])}` : ""}. They are not a reviewed grade. The range on these files is ${num(model.minAwarded, 1)} to ${num(model.maxAwarded, 1)}${model.samePossible != null ? ` of ${num(model.samePossible, 1)}` : ""}. The median is ${num(model.medianAwarded, 1)}.</li>
        <li>The inspection also stores a model count and a target order. They are not used as findings here. A count does not describe the model, and the order does not show why a target was chosen.</li>
        ${disagree.length ? `<li>Cell counts in the older inspection record differ from the current file for ${num(disagree.length)} of ${num(model.notebooks.length)} notebooks. This page uses the current file for cell and image counts.</li>` : ""}
        <li>${reportNames ? `${h(reportNames)} submitted a written report. Fields the inspection stored from that report are shown. Notebook cell counts stay blank.` : "Every file in this table is a notebook."}</li>
      </ul></div>
    </details>`;
  }

  function page(core, evidence) {
    const model = analyze(core || root.CORE, evidence || root.NOTEBOOK_EVIDENCE);
    const reportNames = nameList(model.reports.map((r) => r.s));
    const lead = `Findings from the final homework, arranged by the assignment’s four rubric dimensions. ${num(model.notebooks.length)} of ${num(model.rows.length)} files are notebooks${reportNames ? `; ${h(reportNames)} submitted a written report` : ""}. Evidence found is not a mark that the step was done correctly. The teacher notebook and the weekly Colab notebooks are not included.`;
    return `<p class="lead">${lead}</p>
      ${cards(model)}
      ${exploreSection(model)}
      ${modelSection(model)}
      ${visualSection(model)}
      ${reflectionSection(model)}
      ${cohort(model)}
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
