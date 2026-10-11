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
  function mean(values) {
    if (!values.length) return null;
    return sum(values) / values.length;
  }
  function pill(label, text, kind) {
    return `<li><span>${h(label)}</span> <b class="src-pill src-${kind}">${h(text)}</b></li>`;
  }
  function kindOf(n, total) {
    if (!n) return "none";
    if (n === total) return "full";
    return "part";
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
        return {
          id: meta.session,
          name: meta.name,
          listed: rec.manifest ? rec.manifest.frames : listed.length,
          coded: coded.length,
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
      previewCap: PREVIEW_CAP,
      thumbsPerSession: core.thumbs_per_session,
      hfFrames: HF_FRAMES,
    };
  }

  function worksheetSentence(model) {
    const full = model.people.filter((p) => p.missing.length === 0);
    const partial = model.people.filter((p) => p.missing.length > 0);
    const groups = new Map();
    partial.forEach((p) => {
      const key = p.missing.join(", ");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(p.id);
    });
    const bits = [`${num(full.length)} of ${num(model.people.length)} participants have an extracted response for all ${num(model.expectedWorksheets)} worksheets.`];
    groups.forEach((names, key) => {
      bits.push(`${nameList(names)} ${names.length === 1 ? "has" : "have"} no extraction for ${key}.`);
    });
    return bits.join(" ");
  }

  function scorePattern(core) {
    if (!root.WorksheetFindings || !core) return null;
    const all = root.WorksheetFindings.analyze(
      core,
      root.SCORE_EXTRA || { notes: {}, status: {} },
      root.WORKSHEET_DOCS || { worksheets: {}, overrides: [] }
    );
    const rows = Object.keys(all).map((code) => {
      const item = all[code];
      if (!item || !item.sameMax || !item.people) return null;
      const cohort = item.people.filter((p) => p.inCohort);
      if (!cohort.length || item.mean == null) return null;
      return { code: code, mean: item.mean, max: item.sameMax, n: cohort.length, share: item.mean / item.sameMax };
    }).filter(Boolean);
    if (rows.length < 2) return null;
    rows.sort((a, b) => b.share - a.share || a.code.localeCompare(b.code));
    return { high: rows[0], low: rows[rows.length - 1], nSheets: rows.length };
  }

  function sessionPhrase(person, key) {
    const rows = person[key];
    if (!rows.length) return "Not stored";
    if (rows.length === CLASS_DAYS.length) return "Both sessions";
    return rows.map((row) => row.name).join(", ");
  }

  function patterns(model, core) {
    const n = model.people.length;
    const bothFrames = model.people.filter((p) => p.frameSessions.length === CLASS_DAYS.length);
    const oneFrame = model.people.filter((p) => p.frameSessions.length === 1);
    const bothLogs = model.people.filter((p) => p.logSessions.length === CLASS_DAYS.length);
    const notebooks = model.people.filter((p) => p.pythonKind === "notebook");
    const reports = model.people.filter((p) => p.pythonKind === "report");
    const logRows = model.people.flatMap((p) => p.logSessions);
    const withRate = logRows.filter((row) => row.votat);
    const rateMissing = [];
    model.people.forEach((p) => p.logSessions.forEach((row) => {
      if (row.votat) return;
      rateMissing.push(`${p.id}, ${row.name}${row.emits < 2 ? " (fewer than two model submissions)" : ""}`);
    }));
    const thresholds = model.people.map((p) => p.threshold);
    const scores = scorePattern(core);
    const cards = [];

    cards.push({
      title: "Worksheet extraction",
      text: worksheetSentence(model),
      detail: `The denominator is the ${num(model.expectedWorksheets)} worksheets stored for this archive. “Extracted” means an extraction file with responses. It is not a score, and it is not a count of correct answers. WS11 is extracted for the participants who have that file, and the worksheet findings page does not use it as scored evidence.`,
      href: "#/findings/worksheets",
      link: "Worksheet findings",
    });

    if (scores) {
      const line = (row) => `${row.code}, mean ${num(row.mean, 1)} of ${num(row.max)} (${num(row.n)} participants)`;
      cards.push({
        title: "Stored worksheet totals",
        text: `Among ${num(scores.nSheets)} worksheets with a published cohort total and one shared maximum, the highest mean is ${line(scores.high)}. The lowest mean is ${line(scores.low)}.`,
        detail: "Each mean is the mean of the stored pipeline totals for participants included in that worksheet’s findings cohort. Dividing by the worksheet maximum only compares a worksheet with itself. Worksheets do not share one scale, and a total is not a reviewed grade.",
        href: "#/findings/worksheets",
        link: "Worksheet findings",
      });
    }

    cards.push({
      title: "Frame evidence",
      text: `${num(model.people.filter((p) => p.frameSessions.length).length)} of ${num(n)} participants have extracted frames for at least one CODAP session. ${num(bothFrames.length)} have both sessions.${oneFrame.length ? " " + nameList(oneFrame.map((p) => p.id)) + (oneFrame.length === 1 ? " has " : " have ") + "one session." : ""}`,
      detail: "A session counts when the archive stores a frame manifest or listed frames for that CODAP session. The count is not minutes of recording. Original videos are not published. Collected Data shows up to " + num(PREVIEW_CAP) + " CODAP-screen examples from a session.",
      href: "#/findings/recordings",
      link: "Screen recording findings",
      also: { href: HF_FRAMES, label: "Complete frame dataset" },
    });

    cards.push({
      title: "Class-session logs",
      text: `${num(model.people.filter((p) => p.logSessions.length).length)} of ${num(n)} participants have a platform log for at least one of the two CODAP class sessions. ${num(bothLogs.length)} have both. Recorded threshold changes on those sessions range from ${num(Math.min.apply(null, thresholds))} to ${num(Math.max.apply(null, thresholds))}.`,
      detail: "The two class sessions are CODAP session 1 and CODAP session 2. A threshold change is the log action change_split_values. A larger count is not evidence of difficulty, haste, or a planned strategy. A 7 April 2026 log is stored as well and is not included in these counts.",
      href: "#/findings/logs",
      link: "Platform log findings",
    });

    if (withRate.length || rateMissing.length) {
      const rates = withRate.map((row) => row.votat.rate);
      const range = rates.length ? ` Where it is stored, it ranges from ${num(Math.min.apply(null, rates) * 100, 0)}% to ${num(Math.max.apply(null, rates) * 100, 0)}%.` : "";
      cards.push({
        title: "One thing at a time",
        text: `A stored rate is available for ${num(withRate.length)} class-session logs.${range}${rateMissing.length ? " No rate is stored for " + rateMissing.join("; ") + "." : ""}`,
        detail: "Between two consecutive model submissions, an interval counts as one thing at a time when the log records only predictor changes or only threshold changes, not both and not neither. The rate is that count divided by the number of intervals. It is stored with the session. This page does not recompute it, and it does not treat the rate as a planned strategy.",
        href: "#/findings/logs",
        link: "Platform log findings",
      });
    }

    cards.push({
      title: "Final Python submission",
      text: `${num(notebooks.length)} of ${num(n)} final files are notebooks.${reports.length ? " " + nameList(reports.map((p) => p.id)) + (reports.length === 1 ? " submitted a written report." : " submitted written reports.") : ""}`,
      detail: "A notebook and a written report are different submission types. Notebook cell counts do not apply to a written report. Pipeline rubric points are not a reviewed grade.",
      href: "#/findings/notebooks",
      link: "Python notebook findings",
    });

    return cards;
  }

  function matrix(model) {
    const head = ["Participant", "Worksheets", "Frames", "Platform logs", "Python submission"];
    const body = model.people.map((p) => {
      const wsKind = kindOf(p.extracted.length, p.expected);
      const frameKind = kindOf(p.frameSessions.length, CLASS_DAYS.length);
      const logKind = kindOf(p.logSessions.length, CLASS_DAYS.length);
      const pyText = p.pythonKind === "report" ? "Written report" : p.pythonKind === "notebook" ? "Notebook" : "Not stored";
      const pyKind = p.pythonKind === "report" ? "report" : p.pythonKind === "notebook" ? "full" : "none";
      const cells = [
        `<a href="#/explore/student/${h(p.id)}">${h(p.id)}</a>`,
        `<a href="#/explore/student/${h(p.id)}/worksheets"><b class="src-pill src-${wsKind}">${num(p.extracted.length)} of ${num(p.expected)}</b></a>`,
        `<a href="#/explore/student/${h(p.id)}/recordings"><b class="src-pill src-${frameKind}">${h(sessionPhrase(p, "frameSessions"))}</b></a>`,
        `<a href="#/explore/student/${h(p.id)}/logs"><b class="src-pill src-${logKind}">${h(sessionPhrase(p, "logSessions"))}</b></a>`,
        `<a href="#/explore/student/${h(p.id)}/notebook"><b class="src-pill src-${pyKind}">${h(pyText)}</b></a>`,
      ];
      return `<tr>${cells.map((cell, i) => `<td data-label="${h(head[i])}">${cell}</td>`).join("")}</tr>`;
    }).join("");
    return `<div class="table-wrap"><table class="find-table profile-matrix"><thead><tr>${head.map((label) => `<th>${h(label)}</th>`).join("")}</tr></thead><tbody>${body}</tbody></table></div>
      <ul class="profile-legend">
        <li><b class="src-pill src-full">Full</b> Every expected record in that column is stored.</li>
        <li><b class="src-pill src-part">Partial</b> Some of the expected records are stored.</li>
        <li><b class="src-pill src-report">Written report</b> A final submission that is not a notebook. Notebook-only measures do not apply.</li>
        <li><b class="src-pill src-none">Not stored</b> No record of that source.</li>
      </ul>
      <p class="small">Worksheet cells count extraction files, not correct answers. Frame cells count the two CODAP sessions. Log cells count those same two sessions. A 7 April log is stored for the cohort and is not one of those sessions.</p>`;
  }

  function cards(model) {
    return model.people.map((p) => {
      const py = p.pythonKind === "report" ? "Written report" : p.pythonKind === "notebook" ? "Notebook" : "Not stored";
      const pyKind = p.pythonKind === "report" ? "report" : kindOf(p.pythonKind === "notebook" ? 1 : 0, 1);
      return `<a class="student-card" href="#/explore/student/${h(p.id)}">
        <div class="student-card-name">${h(p.id)}</div>
        <p class="student-card-sources">${num(p.categories)} of 4 source categories</p>
        <ul class="src-pills">
          ${pill("Worksheets", `${num(p.extracted.length)} of ${num(p.expected)}`, kindOf(p.extracted.length, p.expected))}
          ${pill("Frames", sessionPhrase(p, "frameSessions"), kindOf(p.frameSessions.length, CLASS_DAYS.length))}
          ${pill("Platform logs", sessionPhrase(p, "logSessions"), kindOf(p.logSessions.length, CLASS_DAYS.length))}
          ${pill("Python", py, pyKind)}
        </ul>
        <div class="student-card-cta">Open profile</div>
      </a>`;
    }).join("");
  }

  function summaryCards(model) {
    const n = model.people.length;
    const fullWs = model.people.filter((p) => p.missing.length === 0).length;
    const anyFrames = model.people.filter((p) => p.frameSessions.length).length;
    const bothFrames = model.people.filter((p) => p.frameSessions.length === CLASS_DAYS.length).length;
    const anyLogs = model.people.filter((p) => p.logSessions.length).length;
    const notebooks = model.people.filter((p) => p.pythonKind === "notebook").length;
    const reports = model.people.filter((p) => p.pythonKind === "report").length;
    const items = [
      [num(n), "Participants", "Pseudonyms in this archive."],
      [`${num(fullWs)} of ${num(n)}`, "Full worksheet extraction", `An extraction file for all ${num(model.expectedWorksheets)} worksheets. ${num(n - fullWs)} have a partial set.`],
      [`${num(anyFrames)} of ${num(n)}`, "Frame evidence", `At least one CODAP session with extracted frames. ${num(bothFrames)} have both sessions.`],
      [`${num(anyLogs)} of ${num(n)}`, "Class-session log", "A platform log for at least one of the two CODAP class sessions."],
      [`${num(notebooks + reports)} of ${num(n)}`, "Final submission", `${num(notebooks)} notebook${notebooks === 1 ? "" : "s"} and ${num(reports)} written report${reports === 1 ? "" : "s"}.`],
    ];
    return `<div class="stat-row find-headline profile-stats">${items.map(([value, label, note]) => `<div class="stat-card"><div class="v">${value}</div><div class="l">${h(label)}</div><p class="small">${h(note)}</p></div>`).join("")}</div>`;
  }

  function page(core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return `<p class="empty">Participant data did not load.</p>`;
    const model = analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE || { rows: [] });
    const patternCards = patterns(model, data).map((card) => `<article class="profile-pattern">
        <h3>${h(card.title)}</h3>
        <p>${h(card.text)}</p>
        <details><summary>How this was counted</summary><p>${h(card.detail)}</p></details>
        <p class="small"><a href="${h(card.href)}">${h(card.link)}</a>${card.also ? ` · <a href="${h(card.also.href)}" target="_blank" rel="noopener">${h(card.also.label)}</a>` : ""}</p>
      </article>`).join("");
    return `<div class="page wide find-page profile-page">
      <p class="kicker">Findings</p>
      <nav class="crumbs" aria-label="Breadcrumb"><a href="#/findings">Findings</a><span aria-hidden="true">/</span><span aria-current="page">Student profiles</span></nav>
      <h1>Student profiles</h1>
      <div class="profile-banner">
        <p>Profiles for ${num(model.people.length)} pseudonymised participants. Each profile brings together worksheet extractions, screen-recording frames, CODAP platform logs, and the final Python submission. The grid shows which of those sources are stored. A stored file is not evidence of learning, and a missing file is not evidence that an activity did not happen.</p>
      </div>
      ${summaryCards(model)}
      <h2>Patterns across participants</h2>
      <div class="profile-patterns">${patternCards}</div>
      <h2>What is stored for each participant</h2>
      ${matrix(model)}
      <h2>Open a profile</h2>
      <div class="student-roster">${cards(model)}</div>
    </div>`;
  }

  function fold(title, text, detail) {
    return `<details class="find-fold profile-fold">
      <summary>${h(title)}</summary>
      <div class="find-fold-body"><p>${h(text)}</p>${detail ? `<p class="small">${h(detail)}</p>` : ""}</div>
    </details>`;
  }

  function summary(id, core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return "";
    const model = analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE || { rows: [] });
    const person = model.people.find((p) => p.id === id);
    if (!person) return "";
    const wsDetail = person.missing.length
      ? `No extraction file: ${person.missing.join(", ")}.`
      : `An extraction file is stored for all ${num(person.expected)} worksheets.`;
    const scoreGap = person.scoreWithoutExtraction.length
      ? ` A scoring file without an extraction is stored for ${person.scoreWithoutExtraction.join(", ")}. That file is not counted as an extracted response.`
      : "";
    const logLines = person.logSessions.map((row) => {
      const rate = row.votat
        ? `${num(row.votat.rate * 100, 0)}% of ${num(row.votat.intervals)} intervals between model submissions`
        : (row.emits < 2 ? "one-thing-at-a-time rate is not defined (fewer than two model submissions)" : "one-thing-at-a-time rate is not stored");
      return `${row.name}: ${num(row.events)} actions, ${num(row.emits)} model submissions, ${num(row.threshold)} threshold changes, ${num(row.predictors)} predictor placements. ${rate}.`;
    });
    const frameLines = person.frameSessions.map((row) => {
      const bits = [`${row.name}: ${num(row.listed)} listed frames, ${num(row.coded)} with a behaviour label`];
      if (row.duplicateOf.length) bits.push("the source file matches another session");
      return bits.join("; ") + ".";
    });
    const labelBits = Object.keys(person.frameCounts).map((code) => `${BEHAV[code] || code} ${num(person.frameCounts[code])}`);
    let pythonText = "No final submission is stored.";
    if (person.pythonKind === "report") {
      pythonText = "Written report. Notebook cell counts, run order, and error outputs are not applicable. The Notebook tab reads the submitted report.";
    } else if (person.pythonKind === "notebook") {
      const bits = ["Final homework notebook, separate from the teacher notebook and the weekly Colab sessions."];
      if (person.depthRecords) bits.push(`Depth-search table stored for ${num(person.depthTables)} of ${num(person.depthRecords)} targets.`);
      if (person.drawings != null) bits.push(`Tree drawing stored for ${num(person.drawings)} target${person.drawings === 1 ? "" : "s"}.`);
      if (person.reflectionOf) bits.push(`Written reflection text stored for ${num(person.reflectionFound)} of ${num(person.reflectionOf)} prompts.`);
      if (person.synthetic) bits.push("The inspection records a substitute data table.");
      pythonText = bits.join(" ");
    }
    const limits = [];
    if (person.missing.length) limits.push(`Worksheet extraction is not stored for ${person.missing.join(", ")}.`);
    if (person.frameSessions.length < CLASS_DAYS.length) {
      const absent = CLASS_DAYS.filter((meta) => !person.frameSessions.some((row) => row.id === meta.session)).map((meta) => meta.name);
      limits.push(`No extracted frames for ${absent.join(" and ")}.`);
    }
    if (person.logSessions.length < CLASS_DAYS.length) {
      const absent = CLASS_DAYS.filter((meta) => !person.logSessions.some((row) => row.session === meta.session)).map((meta) => meta.name);
      limits.push(`No class-session log for ${absent.join(" and ")}.`);
    }
    person.frameSessions.forEach((row) => {
      if (row.duplicateOf.length) limits.push(`${row.name} uses the same source file as another session, so the two sessions cannot be compared as different days.`);
    });
    if (person.pythonKind === "report") limits.push("Notebook structure cannot be measured for a written report.");
    if (person.synthetic) limits.push("The notebook inspection records that the original lizard table was not the file used.");
    limits.push("Worksheet responses, frames, and log events are not joined to one another.");

    const top = person.topCode
      ? `Most frequent coded label: ${person.topLabel}, ${num(person.topN)} of ${num(person.codedFrames)} coded frames.`
      : "No behaviour label is stored on the listed frames.";
    const buildN = person.frameCounts.BUILD_TREE || 0;
    const evalN = person.frameCounts.EVALUATE_MODEL || 0;
    const tuneN = person.frameCounts.TUNE_THRESHOLD || 0;

    return `<section class="profile-summary" aria-label="Participant evidence summary">
      <h2>Participant evidence summary</h2>
      <p class="profile-intro">Counts below are taken from the stored files. They describe records, not a participant type.</p>
      ${fold("Worksheet records", `${num(person.extracted.length)} of ${num(person.expected)} worksheets have an extracted response. Item results stay in the Worksheets tab. This summary does not add them into one score.`, wsDetail + scoreGap)}
      ${fold("Platform log actions", person.logSessions.length ? `${num(person.threshold)} recorded threshold changes and ${num(person.emits)} model submissions across ${num(person.logSessions.length)} of 2 class sessions. ${num(person.predictors)} predictor placements are stored on those sessions.` : "No log is stored for the two CODAP class sessions.", logLines.join(" ") + (person.extraLogEvents != null ? ` A log from 7 April 2026 is also stored (${num(person.extraLogEvents)} actions) and is not included in the class-session counts.` : ""))}
      ${fold("Coded frames", person.codedFrames ? `${top} Build tree ${num(buildN)}. Tune threshold ${num(tuneN)}. Evaluate model ${num(evalN)}. A label names the coded frame. It is not a measure of understanding.` : "No coded frames are stored.", frameLines.join(" "))}
      ${fold("Final Python submission", pythonText, person.pythonKind === "notebook" ? "Stored inspection status is not a mark that the step was done correctly. Pipeline rubric points on the Notebook tab are not a reviewed grade." : "")}
      ${fold("Evidence limitations", limits.join(" "), "")}
    </section>`;
  }

  function framesNote() {
    const thumbs = root.CORE && root.CORE.thumbs_per_session;
    const stored = thumbs == null ? "Preview images are stored per session." : `${num(thumbs)} preview images are stored per session.`;
    return `<div class="profile-banner">
      <p>Original screen-recording videos are not published and are not intended for public release. Collected Data shows up to ${num(PREVIEW_CAP)} CODAP-screen examples from a session. ${stored} The complete extracted frame dataset is published on <a href="${HF_FRAMES}" target="_blank" rel="noopener">Hugging Face</a>.</p>
    </div>`;
  }

  function logPreface(id, core, frames, evidence) {
    const data = core || root.CORE;
    if (!data) return "";
    const model = analyze(data, frames || root.FRAMES || [], evidence || root.NOTEBOOK_EVIDENCE || { rows: [] });
    const person = model.people.find((p) => p.id === id);
    if (!person) return "";
    const extra = person.extraLogEvents == null ? "" : ` A separate log from 7 April 2026 stores ${num(person.extraLogEvents)} actions. It is not one of the two class sessions below.`;
    return `<p>Class-session logs on file: ${num(person.logSessions.length)} of 2. Recorded actions ${num(person.logEvents)}. Threshold changes ${num(person.threshold)}. Model submissions ${num(person.emits)}. A threshold change is the action <code>change_split_values</code>. A larger count is not evidence of difficulty or of a planned strategy.${extra}</p>`;
  }

  root.StudentProfiles = {
    analyze: analyze,
    page: page,
    summary: summary,
    framesNote: framesNote,
    logPreface: logPreface,
    HF_FRAMES: HF_FRAMES,
  };
})(typeof window !== "undefined" ? window : globalThis);
