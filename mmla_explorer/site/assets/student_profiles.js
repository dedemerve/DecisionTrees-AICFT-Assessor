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

  function coverageChart(model) {
    const n = model.people.length;
    const fullWs = model.people.filter((p) => p.missing.length === 0).length;
    const bothFrames = model.people.filter((p) => p.frameSessions.length === CLASS_DAYS.length).length;
    const oneFrame = model.people.filter((p) => p.frameSessions.length === 1).length;
    const bothLogs = model.people.filter((p) => p.logSessions.length === CLASS_DAYS.length).length;
    const oneLog = model.people.filter((p) => p.logSessions.length === 1).length;
    const notebooks = model.people.filter((p) => p.pythonKind === "notebook").length;
    const reports = model.people.filter((p) => p.pythonKind === "report").length;
    const rows = [
      ["Worksheets", [
        { n: fullWs, label: "all " + model.expectedWorksheets + " files", color: "var(--blue)" },
        { n: n - fullWs, label: "a partial set", color: "var(--muted)" },
      ]],
      ["Frames", [
        { n: bothFrames, label: "both sessions", color: "var(--blue)" },
        { n: oneFrame, label: "one session", color: "var(--muted)" },
      ]],
      ["Platform logs", [
        { n: bothLogs, label: "both sessions", color: "var(--blue)" },
        { n: oneLog, label: "one session", color: "var(--muted)" },
      ]],
      ["Final submission", [
        { n: notebooks, label: notebooks === 1 ? "notebook" : "notebooks", color: "var(--blue)" },
        { n: reports, label: reports === 1 ? "written report" : "written reports", color: "var(--muted)" },
      ]],
    ];
    const body = rows.map(([label, parts]) => {
      const segs = parts.filter((part) => part.n > 0).map((part) => {
        const width = n ? (100 * part.n / n) : 0;
        return `<span style="width:${width.toFixed(2)}%;background:${part.color}" title="${h(num(part.n) + " " + part.label)}"></span>`;
      }).join("");
      const caption = parts.filter((part) => part.n > 0).map((part) => num(part.n) + " " + part.label).join(" · ");
      return `<div class="cov-row"><div class="cov-name">${h(label)}</div><div class="cov-track" role="img" aria-label="${h(label + ": " + caption)}">${segs}</div><div class="cov-cap">${h(caption)}</div></div>`;
    }).join("");
    return `<div class="cov-chart">${body}</div><p class="small">The caption beside each bar states the count. A stored file is not a score.</p>`;
  }

  function worksheetBars(model) {
    const n = model.people.length;
    const counts = model.codes.map((code) => ({
      code: code,
      n: model.people.filter((p) => p.extracted.includes(code)).length,
    }));
    const widest = Math.max(n, 1);
    const rows = counts.map((row) => {
      const width = (100 * row.n / widest).toFixed(2);
      return `<div class="cov-row"><div class="cov-name">${h(row.code)}</div><div class="cov-track" role="img" aria-label="${h(row.code + ": " + row.n + " / " + n)}"><span style="width:${width}%;background:var(--blue)"></span></div><div class="cov-cap">${num(row.n)} / ${num(n)}</div></div>`;
    }).join("");
    const groups = new Map();
    model.people.filter((p) => p.missing.length).forEach((p) => {
      const key = p.missing.join(", ");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(p.id);
    });
    const notes = [];
    groups.forEach((names, key) => {
      notes.push(nameList(names) + (names.length === 1 ? " has" : " have") + " no extraction for " + key);
    });
    const note = notes.length ? notes.join(". ") + "." : "";
    return `<div class="cov-chart">${rows}</div><p class="small">Each bar counts extraction files, out of ${num(n)}. A file is not a correct answer. ${h(note)}</p>`;
  }

  function page(core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return `<div class="page wide profile-page"><p class="empty">No data loaded.</p></div>`;
    const model = analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE);
    const n = model.people.length;
    const head = model.people.map((p) => `<tr>
      <td data-label="Participant"><a href="#/explore/student/${encodeURIComponent(p.id)}">${h(p.id)}</a></td>
      <td data-label="Worksheets">${num(p.extracted.length)}/${num(p.expected)}</td>
      <td data-label="Frames">${h(sessionPhrase(p.frameSessions))}</td>
      <td data-label="Platform logs">${h(sessionPhrase(p.logSessions))}</td>
      <td data-label="Final submission">${h(submissionPhrase(p))}</td>
    </tr>`).join("");
    const cards = model.people.map((p) => `<a class="student-card" href="#/explore/student/${encodeURIComponent(p.id)}">
      <b class="student-card-name">${h(p.id)}</b>
      <dl class="student-card-meta">
        <div><dt>Worksheets</dt><dd>${num(p.extracted.length)}/${num(p.expected)}</dd></div>
        <div><dt>Frames</dt><dd>${h(sessionPhrase(p.frameSessions))}</dd></div>
        <div><dt>Platform logs</dt><dd>${h(sessionPhrase(p.logSessions))}</dd></div>
        <div><dt>Python</dt><dd>${h(submissionPhrase(p))}</dd></div>
      </dl>
      <span class="student-card-cta">Open profile</span>
    </a>`).join("");
    return `<div class="page wide profile-page">
      <p class="kicker">Findings</p>
      <p class="crumbs"><a href="#/">Overview</a><span>/</span><a href="#/findings">Findings</a><span>/</span>Student profiles</p>
      <h1>Student profiles</h1>
      <p class="profile-intro">Explore the completeness of the archived evidence and the patterns observed across ${num(n)} pseudonymised participants. Each profile brings together worksheet responses, extracted screen frames, CODAP platform logs, and the final Python submission.</p>
      <p>Observed records describe the available evidence, not a participant's ability, understanding, or intent.</p>
      <h2>Cohort overview</h2>
      ${coverageChart(model)}
      <h3>Worksheet files</h3>
      ${worksheetBars(model)}
      <h2>What is stored for each participant</h2>
      <div class="table-wrap"><table class="find-table profile-store">
        <thead><tr><th>Participant</th><th>Worksheets</th><th>Frames</th><th>Platform logs</th><th>Final submission</th></tr></thead>
        <tbody>${head}</tbody>
      </table></div>
      <p class="small">Worksheet cells count extraction files, not correct answers. Frame and log cells count the two CODAP class sessions. A 7 April log is stored separately and is not one of those sessions. A missing record does not prove that an activity did not occur.</p>
      <h2>Open a profile</h2>
      <div class="student-roster">${cards}</div>
    </div>`;
  }

  function summary(id, core, frames, evidence) {
    const model = modelFor(core, frames, evidence);
    const row = model && person(model, id);
    if (!row) return "";
    const facts = "Worksheets " + num(row.extracted.length) + "/" + num(row.expected)
      + " · Frames " + sessionPhrase(row.frameSessions)
      + " · Logs " + sessionPhrase(row.logSessions)
      + " · " + submissionPhrase(row);
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
    return `<p class="profile-facts">${h(facts)}</p><p class="small">Counts describe stored records, not learning.</p>${note}`;
  }

  function framesNote() {
    const data = root.CORE;
    const thumbs = data && data.thumbs_per_session;
    return `<p class="small">Original screen recordings are not published. The archive shows up to ${num(PREVIEW_CAP)} CODAP-screen examples for a session. ${thumbs ? num(thumbs) + " preview images are stored for each session." : ""} The complete extracted-frame set is on <a href="${h(HF_FRAMES)}">Hugging Face</a>. Listed frames are not minutes of attention. Percentages use labelled frames as the denominator. “Idle / thinking” means no visible interaction was coded. It does not show that thinking was observed.</p>`;
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
    return `<p class="small">Class-session logs: ${h(names)}. Recorded threshold changes: ${num(row.threshold)}. Model submissions: ${num(row.emits)}. Predictor changes: ${num(row.predictors)}. A larger count is not evidence of difficulty or of a planned strategy.${h(extra)}</p>`;
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
