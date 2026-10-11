/* Student profile overview and participant evidence summaries.
   Counts are derived from window.CORE, window.FRAMES, and window.NOTEBOOK_EVIDENCE.
   A stored file is not evidence of learning. A missing file is not evidence that
   the activity did not happen. This script does not score, classify, or execute notebooks. */
(function (root) {
  "use strict";

  const HF_FRAMES = "https://huggingface.co/datasets/dedemerve/DecisionTrees-AICFT-Frames";
  /* Matches the Collected Data session preview in app.js (PREVIEW_CAP). */
  const PREVIEW_CAP = 12;
  const CLASS_DAYS = [
    { day: "2026-04-21", session: "codap_21apr", name: "CODAP session 1" },
    { day: "2026-04-28", session: "codap_28apr", name: "CODAP session 2" },
  ];
  const EXTRA_LOG_DAY = "2026-04-07";
  const BEHAV = {
    EXPLORE_DATA: "Explore data",
    SELECT_TARGET: "Select target",
    BUILD_TREE: "Build tree",
    TUNE_THRESHOLD: "Tune threshold",
    EVALUATE_MODEL: "Evaluate model",
    COMPARE_MODELS: "Compare models",
    INTERPRET_RESULTS: "Interpret results",
    IDLE_THINKING: "Idle / thinking",
    OFF_TASK: "Off task",
  };

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v, d = 0) => (v == null || Number.isNaN(Number(v))) ? "–" :
    Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const sum = (arr) => arr.reduce((a, b) => a + b, 0);

  function nameList(names) {
    const a = names.slice().sort((x, y) => x.localeCompare(y));
    if (a.length < 2) return a.join("");
    if (a.length === 2) return a[0] + " and " + a[1];
    return a.slice(0, -1).join(", ") + ", and " + a[a.length - 1];
  }
  function analyze(core, frames, evidence) {
    const students = core.students || [];
    const sheets = core.worksheets || [];
    const codes = sheets.map((w) => w.code);
    const byEvidence = {};
    ((evidence && evidence.rows) || []).forEach((row) => { byEvidence[row.student] = row; });
    const frameList = frames || [];

    const people = students.map((id) => {
      const ws = (core.ws && core.ws[id]) || {};
      const extracted = codes.filter((code) => ws[code] && ws[code].ocr);
      const missing = codes.filter((code) => !extracted.includes(code));
      const scoreWithoutExtraction = codes.filter((code) => {
        const rec = ws[code];
        return rec && rec.scoring && !rec.ocr;
      });
      const sessions = core.sessions && core.sessions[id] ? core.sessions[id] : {};
      const frameSessions = CLASS_DAYS.map((meta) => {
        const rec = sessions[meta.session] || {};
        const listed = frameList.filter((f) => f.s === id && f.ss === meta.session);
        if (!rec.manifest && !listed.length) return null;
        const coded = listed.filter((f) => f.b);
        const behaviors = {};
        coded.forEach((f) => { behaviors[f.b] = (behaviors[f.b] || 0) + 1; });
        return {
          id: meta.session,
          name: meta.name,
          short: meta.session === "codap_21apr" ? "Session 1" : "Session 2",
          listed: rec.manifest ? rec.manifest.frames : listed.length,
          coded: coded.length,
          behaviors: behaviors,
          duplicateOf: rec.same_video_file_as || [],
          coverage: typeof rec.frame_coverage === "number" ? rec.frame_coverage : null,
        };
      }).filter(Boolean);
      const counts = {};
      frameList.filter((f) => f.s === id && f.b).forEach((f) => { counts[f.b] = (counts[f.b] || 0) + 1; });
      const codedFrames = sum(Object.values(counts));
      let topCode = null;
      Object.keys(counts).forEach((code) => {
        if (!topCode || counts[code] > counts[topCode]) topCode = code;
      });

      const logs = (core.logs && core.logs.per_student && core.logs.per_student[id]) || {};
      const logSessions = CLASS_DAYS.map((meta) => {
        const row = logs[meta.day];
        if (!row) return null;
        const actions = row.modelling_actions || {};
        const votat = sessions[meta.session] && sessions[meta.session].votat;
        return {
          name: meta.name,
          short: meta.session === "codap_21apr" ? "Session 1" : "Session 2",
          session: meta.session,
          events: row.events || 0,
          emits: row.emit_count || 0,
          threshold: actions.change_split_values || 0,
          predictors: actions.drop_attribute || 0,
          lastAccuracy: typeof row.last_emit_accuracy === "number" ? row.last_emit_accuracy : null,
          votat: votat && typeof votat.votat_rate === "number" ? {
            rate: votat.votat_rate,
            intervals: votat.intervals,
          } : null,
        };
      }).filter(Boolean);
      const extra = logs[EXTRA_LOG_DAY];

      const ev = byEvidence[id] || null;
      const nb = (core.notebooks && core.notebooks[id]) || {};
      const checks = ev && ev.inspection && ev.inspection.checks;
      let pythonKind = "none";
      if (ev && ev.kind) pythonKind = ev.kind;
      else if (nb.file) pythonKind = "notebook";
      else if (nb.extraction) pythonKind = "report";
      const reflection = checks && checks.reflection;
      const reflectionKeys = reflection ? ["settings", "data", "performance", "limits"] : [];
      const reflectionFound = reflectionKeys.filter((key) => reflection[key] === "found").length;

      const categories = [
        extracted.length > 0,
        frameSessions.length > 0,
        logSessions.length > 0,
        pythonKind === "notebook" || pythonKind === "report",
      ].filter(Boolean).length;

      return {
        id: id,
        extracted: extracted,
        missing: missing,
        expected: codes.length,
        scoreWithoutExtraction: scoreWithoutExtraction,
        frameSessions: frameSessions,
        frameCounts: counts,
        codedFrames: codedFrames,
        topCode: topCode,
        topLabel: topCode ? (BEHAV[topCode] || topCode) : "",
        topN: topCode ? counts[topCode] : 0,
        logSessions: logSessions,
        threshold: sum(logSessions.map((row) => row.threshold)),
        emits: sum(logSessions.map((row) => row.emits)),
        predictors: sum(logSessions.map((row) => row.predictors)),
        logEvents: sum(logSessions.map((row) => row.events)),
        extraLogEvents: extra ? extra.events || 0 : null,
        pythonKind: pythonKind,
        checks: checks || null,
        synthetic: !!(ev && ev.inspection && ev.inspection.synthetic),
        depthTables: checks && typeof checks.depth_tables === "number" ? checks.depth_tables : null,
        depthRecords: checks && typeof checks.depth_records === "number" ? checks.depth_records : null,
        drawings: checks && typeof checks.drawings === "number" ? checks.drawings : null,
        reflectionFound: reflection ? reflectionFound : null,
        reflectionOf: reflection ? reflectionKeys.length : null,
        categories: categories,
      };
    });

    return {
      people: people,
      expectedWorksheets: codes.length,
      codes: codes,
      previewCap: PREVIEW_CAP,
      thumbsPerSession: core.thumbs_per_session,
      hfFrames: HF_FRAMES,
    };
  }

  const BEHAV_COLOR = {
    EXPLORE_DATA: "var(--b1)",
    SELECT_TARGET: "var(--b2)",
    BUILD_TREE: "var(--b3)",
    TUNE_THRESHOLD: "var(--b4)",
    EVALUATE_MODEL: "var(--b5)",
    COMPARE_MODELS: "var(--b6)",
    INTERPRET_RESULTS: "var(--b7)",
    IDLE_THINKING: "var(--b-idle)",
    OFF_TASK: "var(--b-off)",
  };

  function person(model, id) {
    return model.people.find((row) => row.id === id) || null;
  }
  function modelFor(core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return null;
    return analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE);
  }
  function sessionPhrase(rows) {
    if (!rows.length) return "Not stored";
    if (rows.length === CLASS_DAYS.length) return "Both sessions";
    return rows.map((row) => row.short || row.name).join(", ");
  }
  function submissionPhrase(row) {
    if (row.pythonKind === "report") return "Written report";
    if (row.pythonKind === "notebook") return "Notebook";
    return "Not stored";
  }
  function plural(n, word) {
    return num(n) + " " + word + (n === 1 ? "" : "s");
  }
  function nice(v) {
    if (v == null || Number.isNaN(Number(v))) return "–";
    const n = Number(v);
    return Math.abs(n - Math.round(n)) < 1e-9 ? String(Math.round(n)) : n.toFixed(1);
  }
  function pct(part) {
    if (part == null || Number.isNaN(Number(part))) return "–";
    return nice(100 * part) + "%";
  }
  function sheetModels() {
    if (!root.WorksheetFindings || !root.CORE) return null;
    return root.WorksheetFindings.analyze(root.CORE, root.SCORE_EXTRA || {}, root.WORKSHEET_DOCS || {});
  }
  const CODAP_SHEETS = ["WS13", "WS14", "WS15"];

  function scoredSheets(sheets) {
    return Object.keys(sheets).map((code) => sheets[code]).filter((sheet) => {
      return sheet.cohort.length && sheet.sameMax && sheet.mean != null && !sheet.duplicateOf;
    }).map((sheet) => ({
      code: sheet.code,
      title: sheet.title,
      method: sheet.method.id,
      mean: sheet.mean,
      max: sheet.sameMax,
      n: sheet.cohort.length,
      share: sheet.mean / sheet.sameMax,
      ids: sheet.cohort.map((p) => p.id).slice().sort().join("|"),
      sheet: sheet,
    })).sort((a, b) => b.share - a.share);
  }
  function sameCohortContrast(rows) {
    const rules = rows.filter((row) => row.method === "rule");
    const groups = new Map();
    rules.forEach((row) => {
      if (!groups.has(row.ids)) groups.set(row.ids, []);
      groups.get(row.ids).push(row);
    });
    let best = [];
    groups.forEach((list) => { if (list.length > best.length) best = list; });
    if (best.length < 2) return null;
    const ordered = best.slice().sort((a, b) => b.share - a.share);
    return { high: ordered[0], low: ordered[ordered.length - 1], n: ordered[0].n };
  }
  function outsidePhrase(sheet) {
    return sheet.people.filter((p) => !p.inCohort).map((p) => {
      if (p.scoring === "published" && p.state !== "present") return p.id + " has a published score and no usable extraction";
      if (p.scoring === "none") return p.id + " has no scoring file";
      if (p.state === "absent") return p.id + " has no extraction file";
      return p.id + " is not included";
    });
  }
  function codapShare(sheets, id) {
    if (!sheets) return { n: 0, mean: null };
    const parts = [];
    CODAP_SHEETS.forEach((code) => {
      const sheet = sheets[code];
      if (!sheet) return;
      const row = sheet.people.find((p) => p.id === id);
      if (row && row.inCohort && typeof row.total === "number" && row.max > 0) parts.push(row.total / row.max);
    });
    return { n: parts.length, mean: parts.length ? sum(parts) / parts.length : null };
  }
  function depthPhrase(row) {
    const tables = row.checks && row.checks.depth_tables;
    if (row.pythonKind === "report") return tables > 0 ? "Written report, table stored" : "Written report, table not stored";
    if (row.pythonKind !== "notebook") return "Not stored";
    return tables > 0 ? "Notebook, table stored" : "Notebook, table not stored";
  }
  function framePhrase(row) {
    if (!row.codedFrames) return "Not stored";
    return row.topLabel + " · " + pct(row.topN / row.codedFrames);
  }
  function hbars(rows) {
    return `<div class="cov-chart">${rows.map((row) => {
      const width = Math.max(0, Math.min(100, row.share));
      return `<div class="cov-row"><div class="cov-name">${h(row.name)}</div><div class="cov-track" role="img" aria-label="${h(row.name + " " + row.caption)}"><span style="width:${width.toFixed(2)}%;background:${row.color || "var(--blue)"}"></span></div><div class="cov-cap">${h(row.caption)}</div></div>`;
    }).join("")}</div>`;
  }

  function researchPage(model) {
    const sheets = sheetModels();
    const rows = sheets ? scoredSheets(sheets) : [];
    const contrast = sameCohortContrast(rows);
    const scoreChart = rows.length ? hbars(rows.map((row) => ({
      name: row.code,
      share: 100 * row.share,
      caption: nice(row.mean) + " / " + nice(row.max) + " · n=" + row.n,
      color: "var(--blue)",
    }))) : "";
    let contrastText = "";
    if (contrast) {
      const lowOut = outsidePhrase(contrast.low.sheet);
      const highOut = outsidePhrase(contrast.high.sheet);
      const who = nameList(contrast.low.sheet.people.filter((p) => !p.inCohort).map((p) => p.id));
      const zeros = contrast.low.sheet.items.filter((item) => item.denom === contrast.low.n && item.full === 0);
      contrastText = `<p>Among rule-based worksheets scored for the same ${num(contrast.n)} participants, ${h(contrast.high.code)} (${h(contrast.high.title)}) has the highest mean stored score, ${nice(contrast.high.mean)} of ${nice(contrast.high.max)}. ${h(contrast.low.code)} (${h(contrast.low.title)}) has the lowest, ${nice(contrast.low.mean)} of ${nice(contrast.low.max)}. ${who ? h(who) + " " + (who.includes(" and ") || who.includes(",") ? "are" : "is") + " outside both summaries." : ""}</p>`
        + (lowOut.length || highOut.length ? `<p class="small">${h(contrast.low.code)}: ${h(lowOut.join("; ") || "everyone with a record is included")}. ${h(contrast.high.code)}: ${h(highOut.join("; ") || "everyone with a record is included")}. A missing extraction is left out of the mean. It is not scored as zero.</p>` : "")
        + (zeros.length ? `<p class="small">On ${h(contrast.low.code)}, ${num(zeros.length)} of ${num(contrast.low.sheet.items.length)} items have no stored full credit in that summary. A stored zero is no credit on a scored item. It is not a missing response.</p>` : "");
    }

    const checked = model.people.filter((p) => p.checks);
    const withTable = checked.filter((p) => p.checks.depth_tables > 0);
    const withoutTable = checked.filter((p) => !(p.checks.depth_tables > 0));
    const withCodap = checked.filter((p) => p.checks.codap_notes > 0);
    const assignmentText = checked.length
      ? `<p>A depth-search table is stored for ${num(withTable.length)} of ${num(checked.length)} final submissions. ${withoutTable.length ? h(nameList(withoutTable.map((p) => p.id))) + (withoutTable.length === 1 && withoutTable[0].pythonKind === "report" ? " submitted a written report, and that report does not store a depth-search table." : " " + (withoutTable.length === 1 ? "has" : "have") + " no depth-search table in the submitted file.") : ""} A written comparison with a CODAP tree is stored for ${num(withCodap.length)} of ${num(checked.length)}. Stored text is not a mark of how complete the comparison is.</p>`
      : "";

    const counts = {};
    let labelled = 0;
    model.people.forEach((p) => {
      Object.keys(p.frameCounts).forEach((code) => {
        counts[code] = (counts[code] || 0) + p.frameCounts[code];
        labelled += p.frameCounts[code];
      });
    });
    const frameRows = Object.keys(BEHAV).filter((code) => counts[code]).concat(Object.keys(counts).filter((code) => !BEHAV[code])).map((code) => ({
      name: BEHAV[code] || code,
      n: counts[code],
      share: labelled ? 100 * counts[code] / labelled : 0,
      caption: num(counts[code]) + " · " + pct(labelled ? counts[code] / labelled : null),
      color: BEHAV_COLOR[code] || "var(--ink-2)",
    })).sort((a, b) => b.share - a.share);
    const frameLead = frameRows[0];
    const frameText = labelled && frameLead
      ? `<p>${h(frameLead.name)} is the most frequent primary label, ${num(frameLead.n)} of ${num(labelled)} labelled frames (${pct(frameLead.n / labelled)}). Shares use labelled frames as the denominator. Extracted frames are a sample, not a continuous record of a session.</p>`
      : "";

    const both = model.people.filter((p) => p.logSessions.length === 2);
    const lower = both.filter((p) => p.logSessions[1].threshold < p.logSessions[0].threshold);
    const higher = both.filter((p) => p.logSessions[1].threshold > p.logSessions[0].threshold);
    const shiftRows = both.map((p) => `<tr>
      <td data-label="Participant">${h(p.id)}</td>
      <td class="num" data-label="Session 1">${num(p.logSessions[0].threshold)}</td>
      <td class="num" data-label="Session 2">${num(p.logSessions[1].threshold)}</td>
    </tr>`).join("");
    const shiftText = both.length
      ? `<p>Among ${num(both.length)} participants with a log for both class sessions, ${num(lower.length)} record fewer threshold changes in session 2 than in session 1. ${higher.length ? h(higher.map((p) => p.id + " records " + num(p.logSessions[0].threshold) + " in session 1 and " + num(p.logSessions[1].threshold) + " in session 2").join("; ")) + "." : ""} A larger count is not evidence of difficulty or of a planned strategy.</p>`
        + `<div class="table-wrap"><table class="find-table"><thead><tr><th>Participant</th><th class="num">Session 1</th><th class="num">Session 2</th></tr></thead><tbody>${shiftRows}</tbody></table></div>`
      : "";

    const head = model.people.map((p) => {
      const share = codapShare(sheets, p.id);
      const codap = share.mean == null ? "Not stored" : pct(share.mean) + " · " + num(share.n) + (share.n === 1 ? " worksheet" : " worksheets");
      return `<tr>
        <td data-label="Participant"><a href="#/explore/student/${encodeURIComponent(p.id)}">${h(p.id)}</a></td>
        <td data-label="CODAP worksheets">${h(codap)}</td>
        <td data-label="Model submissions">${p.logSessions.length ? num(p.emits) : "Not stored"}</td>
        <td data-label="Threshold changes">${p.logSessions.length ? num(p.threshold) : "Not stored"}</td>
        <td data-label="Leading frame label">${h(framePhrase(p))}</td>
        <td data-label="Depth-search table">${h(depthPhrase(p))}</td>
      </tr>`;
    }).join("");
    const cards = model.people.map((p) => {
      const share = codapShare(sheets, p.id);
      const codap = share.mean == null ? "Not stored" : pct(share.mean) + " of each maximum";
      return `<a class="student-card" href="#/explore/student/${encodeURIComponent(p.id)}">
        <b class="student-card-name">${h(p.id)}</b>
        <dl class="student-card-meta">
          <div><dt>CODAP worksheets</dt><dd>${h(codap)}</dd></div>
          <div><dt>Threshold changes</dt><dd>${p.logSessions.length ? num(p.threshold) : "Not stored"}</dd></div>
        </dl>
        <span class="student-card-cta">Open profile</span>
      </a>`;
    }).join("");

    return `<div class="page wide profile-page">
      <p class="kicker">Findings</p>
      <p class="crumbs"><a href="#/">Overview</a><span>/</span><a href="#/findings">Findings</a><span>/</span>Student profiles</p>
      <h1>Student profiles</h1>
      <p class="profile-intro">Worksheet responses, extracted screen frames, CODAP platform logs, and final Python assignments for ${num(model.people.length)} pseudonymised participants.</p>
      <p>These findings describe the available records. They are not measures of ability or intention.</p>
      <h2>Cohort findings</h2>
      <section class="insight">
        <h3>Stored worksheet scores, each scaled by its own maximum</h3>
        ${contrastText}
        ${scoreChart}
        <p class="small">Each bar is the mean stored score divided by that worksheet’s maximum. The count is the participants included in that summary. It is not the same set on every worksheet. WS12 records agreement within the written tree. It is not a mark for one correct tree. WS11 is omitted because its extraction repeats WS14 and no published WS11 score is used.</p>
      </section>
      <section class="insight">
        <h3>Evidence stored in the final assignment</h3>
        ${assignmentText}
      </section>
      <section class="insight">
        <h3>Primary labels on extracted frames</h3>
        ${frameText}
        ${frameRows.length ? hbars(frameRows) : ""}
        <p class="small">“Idle / thinking” means no visible interaction was coded. It does not show that thinking was observed.</p>
      </section>
      <section class="insight">
        <h3>Threshold changes in the two class sessions</h3>
        ${shiftText}
        <p class="small">A threshold change is the stored action change_split_values. Model submissions are stored emit counts. The 7 April log is not one of these sessions.</p>
      </section>
      <h2>What the four sources can be compared on</h2>
      <div class="theme-grid">
        <section class="insight">
          <h3>Worksheet performance</h3>
          <p>Comparable scores are published item totals for participants with a usable extraction. Raw totals are not compared across worksheets, because the maxima differ.</p>
        </section>
        <section class="insight">
          <h3>Modelling in the class logs</h3>
          <p>The log records model submissions, threshold changes, and predictors placed in the tree. It does not record why those actions were taken.</p>
        </section>
        <section class="insight">
          <h3>Frame labels</h3>
          <p>Each coded frame has one primary behaviour label from the existing scheme. The set of frames is not the whole recording.</p>
        </section>
        <section class="insight">
          <h3>Final assignment</h3>
          <p>Checks describe evidence present in the submitted file. A written report is not scored as a notebook with empty cells. Pipeline rubric points are not a reviewed grade.</p>
        </section>
      </div>
      <section class="insight">
        <h3>Cross-source limits</h3>
        <p>The same pseudonym identifies a participant across the four sources. There is no verified join from a worksheet item to a frame or to a log event, so this page does not report an association between worksheet scores and threshold changes, or between frames and logged actions.</p>
      </section>
      <h2>Participant comparison</h2>
      <div class="table-wrap"><table class="find-table profile-store">
        <thead><tr><th>Participant</th><th>CODAP worksheets</th><th>Model submissions</th><th>Threshold changes</th><th>Leading frame label</th><th>Depth-search table</th></tr></thead>
        <tbody>${head}</tbody>
      </table></div>
      <p class="small">CODAP worksheets are the mean of each participant’s stored score divided by that worksheet’s maximum, for WS13, WS14, and WS15. Those three include all ${num(model.people.length)} participants. Threshold changes and model submissions cover the class sessions that have a log. A missing log is not shown as zero.</p>
      <h2>Open a profile</h2>
      <div class="student-roster">${cards}</div>
      <details class="profile-notes">
        <summary>How these figures were counted</summary>
        <ul>
          <li>Worksheet means copy the published scoring files. Participants without a usable extraction are left out of a worksheet’s mean.</li>
          <li>A stored zero on a scored item is no credit. A missing file is not entered as zero.</li>
          <li>Frame percentages use labelled frames. One primary label is counted per labelled frame.</li>
          <li>Notebook checks describe evidence in the submitted file. They do not re-run the notebook.</li>
        </ul>
      </details>
    </div>`;
  }

  function page(core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return `<div class="page wide profile-page"><p class="empty">No data loaded.</p></div>`;
    const model = analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE);
    return researchPage(model);
  }

  function summary(id, core, frames, evidence) {
    const model = modelFor(core, frames, evidence);
    const row = model && person(model, id);
    if (!row) return "";
    const sheets = sheetModels();
    const share = codapShare(sheets, row.id);
    const bits = [];
    if (share.mean != null) bits.push("CODAP worksheets " + pct(share.mean) + " of each maximum (" + num(share.n) + ")");
    if (row.logSessions.length) bits.push("Threshold changes " + num(row.threshold) + " · Model submissions " + num(row.emits));
    else bits.push("No class-session log stored");
    bits.push(submissionPhrase(row));
    const notes = [];
    if (row.missing.length) notes.push("No worksheet extraction for " + row.missing.join(", ") + ".");
    if (row.scoreWithoutExtraction.length) {
      notes.push("A scoring file without an extraction is stored for " + row.scoreWithoutExtraction.join(", ") + ". It is not counted as an extracted response.");
    }
    const absent = CLASS_DAYS.filter((meta) => !row.frameSessions.some((session) => session.id === meta.session));
    if (absent.length && absent.length < CLASS_DAYS.length) {
      notes.push("No extracted frames for " + absent.map((meta) => meta.name).join(" and ") + ".");
    }
    row.frameSessions.forEach((session) => {
      if (session.duplicateOf.length) notes.push(session.name + " uses the same source file as the other session.");
    });
    if (row.pythonKind === "report") notes.push("Written report. Notebook cell counts are not applicable.");
    if (row.synthetic) notes.push("The notebook inspection records a substitute data table.");
    const note = notes.length
      ? `<details class="profile-notes"><summary>Evidence notes</summary><ul>${notes.map((item) => `<li>${h(item)}</li>`).join("")}</ul></details>`
      : "";
    return `<p class="profile-facts">${h(bits.join(" · "))}</p><p class="small">Counts describe stored records, not learning.</p>${note}`;
  }


  function framesNote() {
    const data = root.CORE;
    const thumbs = data && data.thumbs_per_session;
    return `<p class="small">Original screen recordings are not published. The archive shows up to ${num(PREVIEW_CAP)} CODAP-screen examples for a session. ${thumbs ? num(thumbs) + " preview images are stored for each session." : ""} The complete extracted-frame set is on <a href="${h(HF_FRAMES)}">Hugging Face</a>. Extracted frames are a sample, not a continuous record of the session, and they are not minutes of attention. Percentages use labelled frames as the denominator. “Idle / thinking” means no visible interaction was coded. It does not show that thinking was observed.</p>`;
  }

  function sessionChart(id, sessionId, core, frames, evidence) {
    const model = modelFor(core, frames, evidence);
    const row = model && person(model, id);
    if (!row) return "";
    const session = row.frameSessions.find((item) => item.id === sessionId);
    if (!session) return `<p class="empty">No extracted frames are stored for this session.</p>`;
    if (!session.coded) return `<p class="small">${num(session.listed)} frames are listed. None has a behaviour label.</p>`;
    const keys = Object.keys(BEHAV).filter((code) => session.behaviors[code]);
    Object.keys(session.behaviors).forEach((code) => { if (!keys.includes(code)) keys.push(code); });
    const parts = keys.map((code) => ({
      code: code,
      label: BEHAV[code] || code,
      n: session.behaviors[code],
      color: BEHAV_COLOR[code] || "var(--ink-2)",
    }));
    const bar = parts.map((part) => {
      const width = (100 * part.n / session.coded).toFixed(2);
      return `<span style="width:${width}%;background:${part.color}" title="${h(part.label + " " + part.n)}"></span>`;
    }).join("");
    const body = parts.map((part) => `<tr>
      <td data-label="Label"><i class="beh-swatch" style="background:${part.color}"></i>${h(part.label)}</td>
      <td class="num" data-label="Frames">${num(part.n)}</td>
      <td class="num" data-label="Share">${num(100 * part.n / session.coded, 1)}%</td>
    </tr>`).join("");
    return `<p class="small">${num(session.listed)} listed frames. ${num(session.coded)} have a behaviour label. The bar and the timeline below follow those labels.</p>
      <div class="cov-track cov-stack" role="img" aria-label="Behaviour labels for ${h(session.name)}">${bar}</div>
      <div class="table-wrap"><table class="find-table">
        <thead><tr><th>Label</th><th class="num">Frames</th><th class="num">Share</th></tr></thead>
        <tbody>${body}</tbody>
      </table></div>`;
  }

  function logPreface(id, core, frames, evidence) {
    const model = modelFor(core, frames, evidence);
    const row = model && person(model, id);
    if (!row) return "";
    const stored = row.logSessions;
    if (!stored.length) return `<p class="small">No class-session log is stored. A larger action count is not evidence of difficulty or of a planned strategy.</p>`;
    const names = stored.map((item) => item.name).join(" and ");
    const extra = row.extraLogEvents != null
      ? ` A log from 7 April is also stored (${num(row.extraLogEvents)} events). It is not one of the two class sessions, and it is not included in the counts below.`
      : "";
    const split = stored.length === 2
      ? ` ${stored[0].short} records ${num(stored[0].threshold)} threshold changes and ${num(stored[0].emits)} model submissions. ${stored[1].short} records ${num(stored[1].threshold)} threshold changes and ${num(stored[1].emits)} model submissions.`
      : "";
    return `<p class="small">Class-session logs: ${h(names)}. Recorded threshold changes: ${num(row.threshold)}. Model submissions: ${num(row.emits)}. Predictor changes: ${num(row.predictors)}. A larger count is not evidence of difficulty or of a planned strategy.${h(split)}${h(extra)}</p>`;
  }

  function checkStatus(value) {
    if (value === "found" || value === true) return "Found";
    if (value === "not_found" || value === false) return "Not found";
    return "Cannot determine";
  }

  function notebookTable(id, core, frames, evidence) {
    const model = modelFor(core, frames, evidence);
    const row = model && person(model, id);
    if (!row) return "";
    if (row.pythonKind === "none") return `<p class="empty">No final submission is stored.</p>`;
    const lead = row.pythonKind === "report"
      ? `<p><b>Written report.</b> Notebook cell counts, run order, and error outputs are not applicable. The rows below come from the submitted report.</p>`
      : `<p>These rows describe evidence stored in the final homework file. They are not a reviewed grade.</p>`;
    const synthetic = row.synthetic ? `<p class="small">The inspection records a substitute data table. Rates below are taken from that table.</p>` : "";
    const checks = row.checks;
    if (!checks) return lead + synthetic + `<p class="small">No inspection record is stored.</p>`;
    const inspect = (checks.value_counts === "found" || checks.describe === "found")
      ? "Found"
      : (checks.value_counts === "not_found" && checks.describe === "not_found" ? "Not found" : "Cannot determine");
    const inspectBits = [];
    if (checks.value_counts === "found") inspectBits.push("Class counts are stored");
    if (checks.describe === "found") inspectBits.push("A numeric summary is stored");
    const split = typeof checks.test_size === "number" ? "Found" : "Cannot determine";
    const splitDetail = typeof checks.test_size === "number"
      ? "Test fraction " + checks.test_size + " is recorded."
      : "No test fraction is stored.";
    const fit = checks.depth_records > 0 ? "Found" : (checks.depth_records === 0 ? "Not found" : "Cannot determine");
    const fitDetail = checks.depth_records > 0 ? plural(checks.depth_records, "target") + " with a stored tree record." : "";
    const depth = checks.depth_tables > 0 ? "Found" : (checks.depth_records > 0 ? "Not found" : "Cannot determine");
    const depthDetail = checks.depth_tables > 0
      ? "Depth-search table stored for " + num(checks.depth_tables) + " of " + num(checks.depth_records) + "."
      : (checks.depth_records > 0 ? "No depth-search table is stored." : "");
    const evaluated = (checks.test_mcr_n > 0 || checks.both_curves > 0)
      ? "Found"
      : (checks.depth_records > 0 ? "Not found" : "Cannot determine");
    const evalBits = [];
    if (checks.test_mcr_n > 0) evalBits.push("A test error is stored for " + plural(checks.test_mcr_n, "target"));
    if (checks.both_curves > 0) evalBits.push("Training and test curves are stored for " + num(checks.both_curves));
    const drawn = checks.drawings > 0 ? "Found" : (checks.depth_records > 0 ? "Not found" : "Cannot determine");
    const drawDetail = checks.drawings > 0 ? "A tree drawing is stored for " + plural(checks.drawings, "target") + "." : "";
    const ref = checks.reflection || {};
    const refKeys = ["settings", "data", "performance", "limits"];
    const known = refKeys.every((key) => ref[key] === "found" || ref[key] === "not_found");
    const refFound = refKeys.filter((key) => ref[key] === "found").length;
    const refStatus = !known ? "Cannot determine" : (refFound ? "Found" : "Not found");
    const refDetail = known ? "Written text stored for " + num(refFound) + " of 4 prompts." : "";
    const lines = [
      ["Load the dataset", checkStatus(checks.loaded), ""],
      ["Inspect the table", inspect, inspectBits.join(". ")],
      ["Separate training and test data", split, splitDetail],
      ["Fit a decision tree", fit, fitDetail],
      ["Explore tree depth", depth, depthDetail],
      ["Evaluate performance", evaluated, evalBits.join(". ")],
      ["Visualise the tree", drawn, drawDetail],
      ["Written reflection", refStatus, refDetail],
    ];
    const body = lines.map((line) => `<tr><td data-label="Assignment requirement">${h(line[0])}</td><td data-label="Evidence status">${h(line[1])}</td><td data-label="Details">${h(line[2])}</td></tr>`).join("");
    return `${lead}${synthetic}<div class="table-wrap"><table class="find-table profile-req">
      <thead><tr><th>Assignment requirement</th><th>Evidence status</th><th>Details</th></tr></thead>
      <tbody>${body}</tbody>
    </table></div><p class="small">Notebook checks describe evidence present in the submitted file.</p>`;
  }

  root.StudentProfiles = {
    analyze: analyze,
    page: page,
    summary: summary,
    framesNote: framesNote,
    sessionChart: sessionChart,
    notebookTable: notebookTable,
    logPreface: logPreface,
    HF_FRAMES: HF_FRAMES,
  };
})(typeof window !== "undefined" ? window : globalThis);
