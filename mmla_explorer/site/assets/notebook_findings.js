/* Final-homework findings.
   Counts come from window.CORE.notebooks, which build_site_data.py reads from
   each participant's final file, inspection record, and scoring record.
   A notebook file supports cell-level measures. A written report does not.
   Stored rubric points are pipeline totals. They are not a reviewed grade. */
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
  function fileNote(note) {
    if (!note) return "";
    const n = String(note).replace(/\s+/g, " ").trim();
    if (n.includes("PDF rapor") && n.includes("Notebook kodu")) {
      return "Written report. The inspection read the report because the file has no notebook cells.";
    }
    if (n.includes("lizard_data.csv") && n.includes("bulunamad")) {
      return "The stored note says the original lizard_data.csv was not found, and that a substitute table was generated to match distributions in the report.";
    }
    return n.length > 180 ? n.slice(0, 177) + "…" : n;
  }

  function analyze(core) {
    const rows = (core.students || []).map((s) => {
      const n = (core.notebooks || {})[s] || {};
      const scoring = n.scoring || null;
      return {
        s,
        file: n.file || null,
        extraction: n.extraction || null,
        awarded: scoring ? sectionTotal(scoring.sections, "awarded") : null,
        possible: scoring ? sectionTotal(scoring.sections, "possible") : null,
        scoredBy: scoring ? scoring.scored_by || null : null,
        rubricVersion: scoring ? scoring.rubric_version || null : null,
      };
    });
    const notebooks = rows.filter((r) => r.file);
    const reports = rows.filter((r) => !r.file && r.extraction);
    const withTargets = rows.filter((r) => r.extraction && Array.isArray(r.extraction.targets) && r.extraction.targets.length);
    const withModels = rows.filter((r) => r.extraction && r.extraction.models != null);
    const notebookModels = notebooks.filter((r) => r.extraction && r.extraction.models != null);
    const scored = rows.filter((r) => r.awarded != null && r.possible != null);
    const possibles = [...new Set(scored.map((r) => r.possible))];
    return {
      rows,
      notebooks,
      reports,
      withTargets,
      withModels,
      notebookModels,
      scored,
      samePossible: possibles.length === 1 ? possibles[0] : null,
      medianAwarded: median(scored.map((r) => r.awarded)),
      minAwarded: scored.length ? Math.min(...scored.map((r) => r.awarded)) : null,
      maxAwarded: scored.length ? Math.max(...scored.map((r) => r.awarded)) : null,
    };
  }

  function card(value, label, note) {
    return `<div class="stat-card"><div class="v">${value}</div><div class="l">${label}</div><p class="small">${note}</p></div>`;
  }

  function modelGroups(rows) {
    const groups = new Map();
    rows.forEach((r) => {
      const k = r.extraction.models;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(r.s);
    });
    return [...groups.entries()].sort((a, b) => b[1].length - a[1].length || a[0] - b[0]);
  }

  function cards(model) {
    const nNote = model.notebooks.length;
    const cohort = model.rows.length;
    const reportNames = nameList(model.reports.map((r) => r.s));
    const reportNote = model.reports.length
      ? `${reportNames} submitted a written report, so cell-level measures are blank there.`
      : "Each of these files can be read cell by cell.";
    const errN = model.notebooks.filter((r) => r.file.cells_with_error_output > 0).length;
    const groups = modelGroups(model.notebookModels);
    const mode = groups.length && (groups.length === 1 || groups[0][1].length > groups[1][1].length) ? groups[0][0] : null;
    const modeNote = groups.map(([k, names]) => names.length === 1
      ? `One records ${num(k)}`
      : `${num(names.length)} of ${num(model.notebookModels.length)} record ${num(k)}`).join(". ") + ".";
    const scored = model.scored.length;
    const rubricValue = model.medianAwarded == null ? "–" : (model.samePossible != null ? `${num(model.medianAwarded, 1)} of ${num(model.samePossible, 1)}` : num(model.medianAwarded, 1));
    const rubricNote = scored
      ? `Median of ${num(scored)} stored totals${model.samePossible != null ? `, each out of ${num(model.samePossible, 1)}` : ""}. A pipeline total, not a reviewed grade.`
      : "No stored rubric total is available.";
    return `<div class="stat-row cols-4 find-headline">
      ${card(`${num(nNote)} of ${num(cohort)}`, "Inspectable notebooks", reportNote)}
      ${card(mode == null ? "–" : num(mode), "Most common model count", modeNote + " The count is what the inspection stored. It is not a measure of mastery.")}
      ${card(`${num(errN)} of ${num(nNote)}`, "Notebooks with an error output", "A code cell whose stored output is an error. No error output is not proof the code was correct.")}
      ${card(rubricValue, "Median stored rubric points", rubricNote)}
    </div>`;
  }

  function overall(model) {
    const paras = [];
    const cohort = model.withTargets.length;
    if (cohort) {
      const first = new Map();
      model.withTargets.forEach((r) => {
        const t = r.extraction.targets[0];
        if (!first.has(t)) first.set(t, []);
        first.get(t).push(r.s);
      });
      const ordered = [...first.entries()].sort((a, b) => b[1].length - a[1].length);
      const bits = ordered.map(([t, names]) => {
        const verb = names.length === 1 ? "lists" : "list";
        const who = names.length > 3
          ? `${num(names.length)} of ${num(cohort)} files`
          : `${nameList(names)} (${num(names.length)} of ${num(cohort)})`;
        return `${who} ${verb} ${t} first`;
      });
      paras.push(`The inspection stores target columns in the order it found them. ${bits.join(". ")}. That order is the order in the file. It does not show how the participant chose the target.`);
      const names = ["YasamAlani", "Tur", "Cinsiyet"];
      const allThree = model.withTargets.filter((r) => names.every((t) => r.extraction.targets.includes(t)));
      const missing = model.withTargets.filter((r) => !names.every((t) => r.extraction.targets.includes(t)));
      if (allThree.length) {
        const miss = missing.map((r) => `${r.s}'s file lists ${r.extraction.targets.join(", ")}`).join("; ");
        paras.push(`${num(allThree.length)} of ${num(cohort)} files list YasamAlani, Tur, and Cinsiyet, the three category columns in the lizard table.${miss ? " " + miss + "." : ""}`);
      }
    }
    if (model.notebookModels.length) {
      const groups = modelGroups(model.notebookModels);
      const bits = groups.map(([k, names]) => names.length === 1
        ? `${names[0]}'s notebook records ${num(k)}`
        : `${num(names.length)} of ${num(model.notebookModels.length)} notebooks record ${num(k)}`);
      const reportBits = model.reports.filter((r) => r.extraction && r.extraction.models != null)
        .map((r) => `${r.s}'s report records ${num(r.extraction.models)}`);
      paras.push(`${bits.join(". ")}.${reportBits.length ? " " + reportBits.join(". ") + "." : ""} A model count describes the inspection record. It does not establish mastery.`);
    }
    const errRows = model.notebooks.filter((r) => r.file.cells_with_error_output > 0);
    const clear = model.notebooks.filter((r) => r.file.cells_with_error_output === 0);
    if (model.notebooks.length) {
      const who = errRows.length ? `${nameList(errRows.map((r) => r.s))} ${errRows.length === 1 ? "has" : "have"} an error output stored` : "No notebook has an error output stored";
      const each = errRows.length && errRows.every((r) => r.file.cells_with_error_output === errRows[0].file.cells_with_error_output)
        ? ` (${num(errRows[0].file.cells_with_error_output)} cell${errRows[0].file.cells_with_error_output === 1 ? "" : "s"} each)` : "";
      paras.push(`${who}${each}. ${num(clear.length)} of ${num(model.notebooks.length)} notebooks have none. A missing error output does not show that the code was correct, and a recorded error does not, by itself, show a lack of understanding.`);
    }
    const back = model.notebooks.filter((r) => r.file.order_reversals > 0);
    if (model.notebooks.length) {
      const once = back.length && back.every((r) => r.file.order_reversals === 1);
      const who = back.length
        ? `The run counter goes backwards in ${num(back.length)} of ${num(model.notebooks.length)} notebooks: ${nameList(back.map((r) => r.s))}${once ? ", once each" : ""}.`
        : `The run counter does not go backwards in any of the ${num(model.notebooks.length)} notebooks.`;
      paras.push(`${who} That mark means an earlier code cell was run again. It does not show whether the change helped.`);
    }
    const asked = model.notebooks.filter((r) => r.extraction && r.extraction.questions_written > 0);
    if (model.notebooks.length) {
      paras.push(asked.length
        ? `A written question is stored for ${num(asked.length)} of ${num(model.notebooks.length)} notebooks: ${nameList(asked.map((r) => r.s))}. The other notebooks list target columns without that question text. Missing question text is not evidence that no question was considered.`
        : `None of the ${num(model.notebooks.length)} notebooks store a written question beside the target columns. Missing question text is not evidence that no question was considered.`);
    }
    const useKeys = ["lizard_data.csv", "DecisionTreeClassifier", "train_test_split", "max_depth", "plot_tree", "get_dummies"];
    const useLabel = {
      "lizard_data.csv": "lizard_data",
      DecisionTreeClassifier: "DecisionTreeClassifier",
      train_test_split: "train_test_split",
      max_depth: "max_depth",
      plot_tree: "plot_tree",
      get_dummies: "get_dummies",
    };
    if (model.notebooks.length && model.notebooks.every((r) => r.file.uses)) {
      const present = useKeys.filter((k) => model.notebooks.every((r) => r.file.uses[k]));
      const partial = useKeys.filter((k) => !present.includes(k));
      if (present.length) {
        const rest = partial.map((k) => {
          const hit = model.notebooks.filter((r) => r.file.uses[k]);
          const miss = model.notebooks.filter((r) => !r.file.uses[k]);
          const absent = miss.length === 1 ? `${miss[0].s}'s notebook` : `the notebooks of ${nameList(miss.map((r) => r.s))}`;
          return `${useLabel[k]} appears in ${num(hit.length)} of ${num(model.notebooks.length)}${miss.length ? ` and is absent from ${absent}` : ""}`;
        });
        const labels = present.map((k) => useLabel[k]);
        const listed = labels.length < 2 ? labels.join("") : labels.slice(0, -1).join(", ") + ", and " + labels[labels.length - 1];
        paras.push(`The code text of all ${num(model.notebooks.length)} notebooks includes ${listed}.${rest.length ? " " + rest.join(". ") + "." : ""} Finding a name in the code is not evidence that the step ran correctly.`);
      }
    }
    if (model.scored.length && model.medianAwarded != null) {
      const of = model.samePossible != null ? ` of ${num(model.samePossible, 1)}` : "";
      paras.push(`Stored rubric points are available for ${num(model.scored.length)} of ${num(model.rows.length)} files. The totals run from ${num(model.minAwarded, 1)} to ${num(model.maxAwarded, 1)}${of}. The median is ${num(model.medianAwarded, 1)}${of}. These are pipeline totals. A higher total does not establish learning gain.`);
    }
    model.rows.forEach((r) => {
      const note = r.file && r.extraction && r.extraction.data_source_note;
      const text = fileNote(note);
      if (text && r.file) paras.push(`${r.s}: ${text}`);
    });
    paras.push("These patterns describe the final homework files. They do not describe the guided Colab sessions, and they do not show what a participant understood.");
    return `<h2>Overall findings</h2>${paras.map((p) => `<p>${p}</p>`).join("")}`;
  }

  function errorText(r) {
    if (!r.file || r.file.cells_with_error_output == null) return na;
    const n = r.file.cells_with_error_output;
    if (n === 0) return "None";
    return n === 1 ? "Yes, 1 cell" : `Yes, ${num(n)} cells`;
  }
  function revisitText(r) {
    if (!r.file || r.file.order_reversals == null) return na;
    const n = r.file.order_reversals;
    if (n === 0) return "None";
    return n === 1 ? "Yes, once" : `Yes, ${num(n)} times`;
  }
  function rubricText(r) {
    if (r.awarded == null) return na;
    if (r.possible == null) return num(r.awarded, 1);
    return `${num(r.awarded, 1)} of ${num(r.possible, 1)}`;
  }

  function table(model) {
    const head = ["Participant", "Target variables", "Models", "Error output recorded", "Earlier code revisited", "Stored rubric points"];
    const body = model.rows.map((r) => {
      const targets = r.extraction && Array.isArray(r.extraction.targets) && r.extraction.targets.length
        ? `<span class="find-targets">${r.extraction.targets.map((t) => h(t)).join(", ")}</span>`
        : na;
      const models = r.extraction && r.extraction.models != null ? num(r.extraction.models) : na;
      const note = fileNote(r.extraction && r.extraction.data_source_note);
      const cells = [
        `<span class="who">${h(r.s)}</span>${note ? `<span class="find-sub">${h(note)}</span>` : ""}`,
        targets,
        models,
        errorText(r),
        revisitText(r),
        rubricText(r),
      ];
      return `<tr>${cells.map((c, i) => `<td${i >= 2 ? ' class="num"' : ""} data-label="${h(head[i])}">${c}</td>`).join("")}</tr>`;
    }).join("");
    return `<h2>Participant results</h2>
      <p>One row per participant. Target variables are the columns stored for that file, in the stored order. A dash means the measure was not available. It is not a zero.</p>
      <div class="table-wrap"><table class="find-table find-people">
        <thead><tr>${head.map((t, i) => `<th${i >= 2 ? ' class="num"' : ""}>${h(t)}</th>`).join("")}</tr></thead>
        <tbody>${body}</tbody>
      </table></div>`;
  }

  function method(model) {
    const versions = [...new Set(model.scored.map((r) => r.rubricVersion).filter(Boolean))];
    const scorers = [...new Set(model.scored.map((r) => r.scoredBy).filter(Boolean))];
    const versionText = versions.length === 1 ? ` The stored rubric version is ${h(versions[0])}.` : "";
    const scorerText = scorers.length === 1 ? ` The scoring record names the scorer as ${h(scorers[0])}.` : "";
    const reportNames = nameList(model.reports.map((r) => r.s));
    return `<details class="find-fold" id="method">
      <summary>Methodology and data quality</summary>
      <div class="find-fold-body">
        <h3>What was inspected</h3>
        <p>Each final homework notebook was read for its cells, code text, stored outputs, and run counter. The teacher instruction notebook and the weekly Colab notebooks are a separate collection. They are not in this table, and these files are not a record of the guided sessions.</p>
        <h3>Target variables and model counts</h3>
        <p>Target variables are the target columns stored on the inspection’s question list, in that stored order. The model count is the total stored by the inspection. A written question count is the number of those targets that also have question text stored. Zero means the text was not stored.</p>
        <h3>Error outputs and earlier code</h3>
        <p>An error output is a code cell whose stored output is an error. Revisiting earlier code counts places where the run counter on successive executed cells goes down. Both measures need a notebook file.</p>
        <h3>Scoring method and limitations</h3>
        <p>Stored rubric points are the sum of the section totals in the scoring record.${scorerText}${versionText} The site does not record a separate manual review of these totals, so they are not a verified grade. A higher total does not establish learning gain. This page does not calculate a new grade.</p>
        <h3>Written reports</h3>
        <p>${reportNames ? `${h(reportNames)} submitted a written report rather than a notebook. Target variables, the model count, and stored rubric points were taken from that report. Error outputs and run-counter changes cannot be read from it, so those cells stay blank.` : "Every participant in this table has a notebook file."} A dash is not a zero.</p>
      </div>
    </details>`;
  }

  function page(core) {
    const model = analyze(core || root.CORE);
    const reportNames = nameList(model.reports.map((r) => r.s));
    const lead = `This page describes the final homework files. ${num(model.notebooks.length)} of ${num(model.rows.length)} participants have an inspectable notebook.${reportNames ? ` ${h(reportNames)} submitted a written report, so notebook-only measures are left blank.` : ""} The teacher instruction notebook is the guided resource for Colab Sessions 1, 2, and 3. Weekly Colab notebooks are separate collected materials. They are not mixed into these results, and a final homework file is not a complete record of the guided sessions.`;
    return `<p class="lead">${lead}</p>
      ${cards(model)}
      ${overall(model)}
      ${table(model)}
      ${method(model)}`;
  }

  root.NotebookFindings = { analyze, page };
})(typeof window !== "undefined" ? window : globalThis);
