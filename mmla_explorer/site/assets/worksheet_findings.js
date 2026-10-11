/* Worksheet findings.
   Counts are derived from window.CORE (built from extraction and scoring files).
   Item notes and blocked flags come from window.SCORE_EXTRA.
   A scoring file that is missing, blocked, or all zeros with confidence 0 is not a score.
   WS11, WS12 and WS13 boolean checks in the site data are copied from item scores
   (see read_stage_as_ocr in build_site_data.py) and are not shown as a second method.
   Participants with a published score but no usable extraction are listed and left
   out of credit summaries, so a missing extraction is not counted as incorrect. */
(function (root) {
  "use strict";

  const GROUPS = [
    { label: "Conceptual foundations", codes: ["WS1"] },
    { label: "Manual classification", codes: ["WS3", "WS4", "WS5"] },
    { label: "Building decision trees", codes: ["WS6", "WS7", "WS10", "WS12"] },
    { label: "CODAP Arbor sessions", codes: ["WS13", "WS14", "WS15"] },
    { label: "Feedback survey", codes: ["WS11"] },
  ];
  const INFO = {
    WS1: { title: "Parts of a nutrition table", topic: "Name the parts of a nutrition table: object, feature, value and label." },
    WS3: { title: "Apply a given rule", topic: "Apply a given rule (fat ≤ 8.0 g) to food cards and write each comparison." },
    WS4: { title: "Search for a fat threshold", topic: "Search for the fat threshold that misclassifies the fewest of the 11 food cards." },
    WS5: { title: "Try another feature", topic: "Choose another feature, try threshold values and record the resulting counts." },
    WS6: { title: "Document a two-level tree", topic: "Document a two-level decision tree built from the 11 food cards." },
    WS7: { title: "Paths as if-then rules", topic: "Read the paths A, B and C of a tree and write them as if-then rules." },
    WS10: { title: "Energy thresholds", topic: "Test thresholds between neighbouring energy values and find the one with the fewest errors." },
    WS11: { title: "Feedback survey", topic: "Feedback on the lesson series (survey items and open questions)." },
    WS12: { title: "Decision tree documentation (training and test)", topic: "Document a two-level decision tree by recording the root variable, thresholds, node counts and misclassified items. The rubric says there is no single correct tree." },
    WS13: { title: "Decision trees for classification", topic: "Choosing variables, reading a tree, TP/FP, sensitivity, misclassification rate and overfitting." },
    WS14: { title: "Diagnosis game with trees (Xeno)", topic: "Diagnose an alien disease with a tree in CODAP Arbor. Each student receives a randomly generated case set." },
    WS15: { title: "Titanic data in CODAP Arbor", topic: "Build a tree on a Titanic training sample, then check it on a test sample." },
  };
  const ALIAS = { WS10: { WS10_B8: "optimal_threshold" } };
  const SCORE_DERIVED = new Set(["WS11", "WS12", "WS13"]);

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v) => {
    if (v == null || Number.isNaN(Number(v))) return "–";
    const n = Number(v);
    return n.toLocaleString("en-GB", { maximumFractionDigits: 2 });
  };
  const clip = (v, n) => {
    const s = String(v == null ? "" : v).replace(/\s+/g, " ").trim();
    if (!s) return "";
    return s.length <= n ? s : s.slice(0, n - 1) + "…";
  };
  const mean = (xs) => xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
  const median = (xs) => {
    if (!xs.length) return null;
    const a = xs.slice().sort((x, y) => x - y);
    const i = Math.floor(a.length / 2);
    return a.length % 2 ? a[i] : (a[i - 1] + a[i]) / 2;
  };
  const share = (part, whole) => {
    if (!whole) return "–";
    const v = 100 * part / whole;
    return (Math.abs(v - Math.round(v)) < 0.05 ? String(Math.round(v)) : v.toFixed(1)) + "%";
  };
  const pctText = (part, whole) => {
    if (!whole) return "–";
    const v = 100 * part / whole;
    const shown = Math.abs(v - Math.round(v)) < 0.05 ? String(Math.round(v)) : v.toFixed(1);
    return part + " of " + whole + " (" + shown + "%)";
  };

  function valueKind(v) {
    if (v == null || v === "" || v === "(not_extracted)") return "missing";
    if (v === "(bos)") return "blank";
    return "text";
  }
  function sheetOf(core, code) {
    return (core.worksheets || []).find((w) => w.code === code) || null;
  }
  function infoOf(w) {
    const extra = INFO[w.code] || {};
    const printed = w.printed_title ? String(w.printed_title).replace(/^Worksheet \d+:\s*/, "") : "";
    return { title: extra.title || printed || w.code, topic: extra.topic || "" };
  }
  function rubricItems(w) {
    return (w.rubric_data && w.rubric_data.items) || {};
  }
  function itemMax(w, item) {
    if (item && typeof item.max_score === "number") return item.max_score;
    const rub = rubricItems(w)[item.item];
    if (!rub) return null;
    if (typeof rub.max_score === "number") return rub.max_score;
    const rules = rub.scoring_rules || {};
    const nums = Object.keys(rules).map(Number).filter((n) => !Number.isNaN(n));
    return nums.length ? Math.max.apply(null, nums) : null;
  }
  function creditOf(score, max) {
    if (score == null || typeof score !== "number") return "unscored";
    if (max == null || typeof max !== "number") return "scored";
    if (score <= 0) return "none";
    if (score + 1e-9 >= max) return "full";
    return "partial";
  }
  function creditLabel(kind) {
    return { full: "Full credit", partial: "Partial credit", none: "No credit", scored: "Scored", unscored: "Not scored" }[kind] || kind;
  }
  function responsesFor(ocr, code, itemId) {
    if (!ocr) return [];
    const alt = (ALIAS[code] || {})[itemId];
    return ocr.responses.filter((r) => {
      if (r.item === itemId || r.path === itemId || String(r.path).indexOf(itemId + ".") === 0) return true;
      if (alt && (r.item === alt || r.path === alt || String(r.path).indexOf(alt + ".") === 0)) return true;
      return false;
    });
  }
  function extractionState(ocr) {
    if (!ocr || !ocr.responses) return "absent";
    if (!ocr.responses.length) return "failed";
    const kinds = ocr.responses.map((r) => valueKind(r.value));
    if (kinds.every((k) => k === "missing")) return "failed";
    return "present";
  }
  function sameResponses(a, b) {
    if (!a || !b || a.responses.length !== b.responses.length) return false;
    const mb = new Map(b.responses.map((r) => [r.path, String(r.value)]));
    return a.responses.every((r) => mb.get(r.path) === String(r.value));
  }
  function methodOf(w) {
    const policy = w.rubric_data && w.rubric_data.scoring_policy;
    if (w.code === "WS11") return { id: "unused", label: "Not used as scored evidence" };
    if (policy && policy.basis === "internal_consistency") return { id: "consistency", label: "Consistency check" };
    if (w.code === "WS5" || w.code === "WS6" || w.code === "WS7" || w.code === "WS10") return { id: "rule", label: "Rule-based check" };
    if (w.code === "WS14" || w.code === "WS15") return { id: "mixed", label: "Rubric scoring and rule-based checks" };
    return { id: "rubric", label: "Rubric scoring" };
  }
  function criterionText(item) {
    if (!item) return "";
    if (item.expected_answer) return String(item.expected_answer);
    if (item.student_specific) return "The rubric marks this item as student-specific. It is not compared with one fixed answer.";
    const rules = item.scoring_rules || {};
    const full = rules["1.0"] || rules["1"] || rules[1] || rules["2.0"] || rules["2"];
    if (typeof full === "string") return full;
    if (full && full.condition) return String(full.condition);
    return item.target_logic || item.note || item.prompt || "";
  }
  function ruleTextForScore(item, score) {
    if (!item || score == null || !item.scoring_rules) return "";
    const key = Object.keys(item.scoring_rules).find((k) => Number(k) === Number(score));
    if (!key) return "";
    const rule = item.scoring_rules[key];
    if (typeof rule === "string") return rule;
    return (rule && rule.condition) || "";
  }
  function itemTitle(w, id) {
    const item = rubricItems(w)[id];
    if (!item) return id;
    if (item.label) return item.label;
    if (item.printed_question != null) return "Item " + item.printed_question;
    return id;
  }
  function sortKey(w, id) {
    const item = rubricItems(w)[id];
    if (item && item.printed_question != null && !Number.isNaN(Number(item.printed_question))) return Number(item.printed_question);
    const m = /(\d+)/.exec(id);
    return m ? Number(m[1]) : 10000;
  }

  function scoreState(rec) {
    if (rec.scoring) return "published";
    const stage = rec.stage && rec.stage.scoring;
    if (stage && stage.all_zero_with_zero_confidence) return "excluded_zero";
    if (stage) return "unpublished";
    return "none";
  }

  function collectRules(core, code, students) {
    if (SCORE_DERIVED.has(code)) {
      return { derived: true, rows: [] };
    }
    const buckets = new Map();
    function add(id, family, correct, label, detail) {
      if (!buckets.has(id)) buckets.set(id, { id, family, label: label || id, pass: 0, fail: 0, open: 0, n: 0, detail: "" });
      const row = buckets.get(id);
      row.n += 1;
      if (correct === true) row.pass += 1;
      else if (correct === false) row.fail += 1;
      else row.open += 1;
      if (detail && !row.detail) row.detail = detail;
      if (label && row.label === id) row.label = label;
    }
    students.forEach((s) => {
      const ocr = core.ws[s][code] && core.ws[s][code].ocr;
      if (!ocr) return;
      (ocr.checks || []).forEach((c) => {
        const detail = c.detail || {};
        const bits = [];
        if (detail.student_value != null && detail.canonical != null) bits.push("One recorded value is " + detail.student_value + " against reference " + detail.canonical + ".");
        if (c.note) bits.push(String(c.note));
        if (c.flag) bits.push("Flag: " + c.flag);
        const id = String(c.check);
        const structural = id.indexOf("xeno_consistency") === 0 || id.indexOf("titanic_numeric") === 0 || id.indexOf("trials") === 0;
        const ruleItem = id.indexOf("item_checks") === 0 && (code === "WS5" || code === "WS6" || code === "WS7" || code === "WS10");
        add(c.check, structural || ruleItem || id.indexOf("item_checks") !== 0 ? "rule" : "boolean", c.correct, detail.check || c.check, bits.join(" "));
      });
      (ocr.other_validation || []).forEach((row) => {
        const path = row.path || "";
        const value = row.value;
        const boolPath = path.indexOf(".is_") !== -1 || path.indexOf("is_") === 0 || path === "final_decision_logical";
        const trap = path.indexOf("student_recognized_contradiction") !== -1 && (value === true || value === false || value === "True" || value === "False");
        if (boolPath && (typeof value === "boolean" || value == null)) add(path, "rule", value, path, "");
        else if (trap) add(path, "rule", value === true || value === "True", path, "Whether the stored check says the contradiction was recognised.");
      });
    });
    return { derived: false, rows: Array.from(buckets.values()) };
  }

  function analyzeWorksheet(core, extra, docs, code) {
    const w = sheetOf(core, code);
    const students = core.students || [];
    const info = w ? infoOf(w) : { title: code, topic: "" };
    const method = w ? methodOf(w) : { id: "unknown", label: "Not recorded" };
    const notes = (extra && extra.notes) || {};
    const status = (extra && extra.status) || {};
    const overrides = ((docs && docs.overrides) || []).filter((o) => o.worksheet === code);
    const overrideKey = new Set(overrides.map((o) => o.student + "|" + o.item));
    const duplicateOf = code === "WS11" && students.length && students.every((s) => sameResponses(core.ws[s].WS11 && core.ws[s].WS11.ocr, core.ws[s].WS14 && core.ws[s].WS14.ocr))
      ? "WS14" : "";

    const people = students.map((s) => {
      const rec = (core.ws[s] && core.ws[s][code]) || { ocr: null, scoring: null, stage: null };
      const ocr = rec.ocr;
      const state = extractionState(ocr);
      let nText = 0, nBlank = 0, nMissing = 0;
      if (ocr) ocr.responses.forEach((r) => {
        const k = valueKind(r.value);
        if (k === "text") nText += 1;
        else if (k === "blank") nBlank += 1;
        else nMissing += 1;
      });
      const scoring = scoreState(rec);
      const blocked = status[s] && status[s][code];
      const published = scoring === "published" && rec.scoring;
      const inCohort = !duplicateOf && published && state === "present";
      const items = published ? rec.scoring.items || [] : [];
      const tallies = { full: 0, partial: 0, none: 0, scored: 0 };
      let review = 0;
      items.forEach((it) => {
        const kind = creditOf(typeof it.score === "number" ? it.score : null, itemMax(w, it));
        if (tallies[kind] != null) tallies[kind] += 1;
        if (it.review) review += 1;
      });
      return {
        id: s,
        state: state,
        nText: nText,
        nBlank: nBlank,
        nMissing: nMissing,
        nFields: ocr ? ocr.responses.length : 0,
        scoring: scoring,
        blocked: blocked && blocked.blocked ? blocked.blocked_reason || "blocked" : "",
        blockedNote: blocked && !blocked.blocked ? blocked.blocked_reason || "" : "",
        inCohort: inCohort,
        total: published ? rec.scoring.total_score : null,
        max: published ? rec.scoring.max_score : null,
        source: published ? rec.scoring.source : (rec.stage && rec.stage.scoring && rec.stage.scoring.source) || (ocr && ocr.source) || "",
        ocrSource: ocr ? ocr.source : "",
        full: published ? tallies.full : null,
        partial: published ? tallies.partial : null,
        none: published ? tallies.none : null,
        scoredOnly: published ? tallies.scored : null,
        review: published ? review : 0,
        stageNote: rec.stage && rec.stage.scoring && rec.stage.scoring.note || "",
        stageExtract: rec.stage && rec.stage.extraction ? rec.stage.extraction.status : "",
      };
    });

    const cohort = people.filter((p) => p.inCohort);
    const scoreIds = [];
    students.forEach((s) => {
      const sc = core.ws[s][code] && core.ws[s][code].scoring;
      if (!sc) return;
      (sc.items || []).forEach((it) => { if (scoreIds.indexOf(it.item) === -1) scoreIds.push(it.item); });
    });
    scoreIds.sort((a, b) => sortKey(w || { rubric_data: null }, a) - sortKey(w || { rubric_data: null }, b) || a.localeCompare(b));
    const aligned = !duplicateOf && scoreIds.length > 0 && scoreIds.every((id) => students.some((s) => responsesFor(core.ws[s][code] && core.ws[s][code].ocr, code, id).length));

    const itemRows = duplicateOf ? [] : scoreIds.map((id) => {
      const rub = rubricItems(w)[id];
      let full = 0, partial = 0, none = 0, scored = 0, review = 0, numeric = [];
      const texts = [];
      let blankScore = 0;
      cohort.forEach((p) => {
        const sc = core.ws[p.id][code].scoring;
        const it = (sc.items || []).find((x) => x.item === id);
        if (!it || typeof it.score !== "number") return;
        const max = itemMax(w, it);
        const kind = creditOf(it.score, max);
        if (kind === "full") full += 1;
        else if (kind === "partial") partial += 1;
        else if (kind === "none") none += 1;
        else scored += 1;
        if (it.review) review += 1;
        numeric.push(it.score);
        if (aligned) {
          const vals = responsesFor(core.ws[p.id][code].ocr, code, id);
          const kinds = vals.map((r) => valueKind(r.value));
          if (kinds.length && kinds.every((k) => k !== "text")) blankScore += 1;
          vals.forEach((r) => { if (valueKind(r.value) === "text") texts.push(String(r.value)); });
        }
      });
      const denom = full + partial + none + scored;
      let frequent = null;
      if (aligned && texts.length) {
        const counts = new Map();
        texts.forEach((t) => {
          const clean = t.replace(/\s+/g, " ").trim();
          if (clean && clean.length <= 48) counts.set(clean, (counts.get(clean) || 0) + 1);
        });
        let best = "", n = 0;
        counts.forEach((c, t) => { if (c > n) { best = t; n = c; } });
        if (best && n >= 2) frequent = { text: best, n: n, denom: texts.length };
      }
      return {
        id: id,
        title: itemTitle(w, id),
        criterion: clip(criterionText(rub), 180),
        max: cohort.length ? itemMax(w, { item: id, max_score: null }) : itemMax(w, { item: id }),
        full: full, partial: partial, none: none, scored: scored, review: review,
        denom: denom,
        mean: mean(numeric),
        blankScore: blankScore,
        frequent: frequent,
      };
    });

    const fields = [];
    const seen = new Set();
    if (!duplicateOf) students.forEach((s) => {
      const ocr = core.ws[s][code] && core.ws[s][code].ocr;
      if (!ocr) return;
      ocr.responses.forEach((r) => { if (!seen.has(r.path)) { seen.add(r.path); fields.push(r.path); } });
    });
    const fieldRows = fields.map((path) => {
      let text = 0, blank = 0, missing = 0, absent = 0;
      students.forEach((s) => {
        const ocr = core.ws[s][code] && core.ws[s][code].ocr;
        if (!ocr) { absent += 1; return; }
        const hits = ocr.responses.filter((r) => r.path === path);
        if (!hits.length) { missing += 1; return; }
        const k = valueKind(hits[0].value);
        if (k === "text") text += 1;
        else if (k === "blank") blank += 1;
        else missing += 1;
      });
      return { path: path, text: text, blank: blank, missing: missing, absent: absent };
    });

    const rules = duplicateOf ? { derived: true, rows: [] } : collectRules(core, code, students);
    const totals = cohort.map((p) => p.total).filter((v) => typeof v === "number");
    const maxes = Array.from(new Set(cohort.map((p) => p.max).filter((v) => typeof v === "number")));
    let sumMismatch = [];
    cohort.forEach((p) => {
      const sc = core.ws[p.id][code].scoring;
      const sum = (sc.items || []).reduce((a, it) => a + (typeof it.score === "number" ? it.score : 0), 0);
      if (typeof sc.total_score === "number" && Math.abs(sum - sc.total_score) > 1e-6) sumMismatch.push(p.id);
    });
    const reviewItems = cohort.reduce((a, p) => a + p.review, 0);
    const scoredItems = cohort.reduce((a, p) => a + (p.full || 0) + (p.partial || 0) + (p.none || 0) + (p.scoredOnly || 0), 0);
    const cohortOverrides = overrides.filter((o) => cohort.some((p) => p.id === o.student));

    const limits = [];
    const noFile = people.filter((p) => p.state === "absent").map((p) => p.id);
    const failed = people.filter((p) => p.state === "failed").map((p) => p.id);
    const excluded = people.filter((p) => p.scoring === "excluded_zero").map((p) => p.id);
    const unpublished = people.filter((p) => p.scoring === "unpublished").map((p) => p.id);
    const noScore = people.filter((p) => p.scoring === "none").map((p) => p.id);
    const leftOut = people.filter((p) => p.scoring === "published" && !p.inCohort).map((p) => p.id);
    if (duplicateOf) {
      limits.push("For all " + students.length + " participants, every extracted path and value in the WS11 site record matches that participant’s WS14 extraction. Those values are not counted as WS11 survey answers.");
      if (excluded.length) limits.push(excluded.length + " WS11 scoring files set every item to 0 with confidence 0. Those files are not published as scores" + (noScore.length ? ". No scoring file: " + noScore.join(", ") + "." : "."));
      else if (noScore.length) limits.push("No scoring file for " + noScore.join(", ") + ".");
      limits.push("The WS11 rubric names survey and closed items, including item identifiers that do not match the repeated WS14 fields. No published WS11 score is on file.");
    } else {
      if (noFile.length) limits.push("No extraction file for " + noFile.join(", ") + ".");
      if (failed.length) limits.push("Extraction file has no readable value for " + failed.join(", ") + ".");
      if (excluded.length) limits.push(excluded.join(", ") + ": the scoring file sets every item to 0 with confidence 0, so those numbers are not used as scores.");
      people.filter((p) => p.blocked).forEach((p) => {
        limits.push(p.id + " scoring file is blocked (" + p.blocked + "). It is not included in the summaries.");
      });
      if (leftOut.length) limits.push(leftOut.join(", ") + " have a published score and no usable extraction. Those scores are listed with the participants and left out of the credit summaries, so the zeros are not counted as incorrect answers.");
      if (unpublished.length) limits.push("A scoring file exists but is not in the published score table for " + unpublished.join(", ") + ".");
      if (noScore.length) limits.push("No scoring file for " + noScore.join(", ") + ".");
      if (!aligned && scoreIds.length && fields.length) limits.push("Scoring item identifiers and extracted field identifiers differ, so a score is not placed on an individual blank.");
      if (reviewItems) limits.push(reviewItems + " of " + scoredItems + " item scores in the summary have review set to true. The flag asks for a person to look. The file does not record a later decision.");
      if (sumMismatch.length) limits.push("The stored total differs from the sum of item scores for " + sumMismatch.join(", ") + ". The table shows the stored total.");
    }
    const sharedBlocked = people.map((p) => p.blockedNote).filter(Boolean);
    if (!duplicateOf && sharedBlocked.length === students.length && sharedBlocked.every((x) => x === sharedBlocked[0])) {
      const reason = String(sharedBlocked[0]).replace(/\.$/, "");
      limits.push("Every scoring file records blocked as false and blocked_reason as “" + reason + "”. The published scores are still listed.");
    }

    const hasCredit = itemRows.some((r) => r.full || r.partial || r.none);
    return {
      code: code,
      title: info.title,
      topic: info.topic,
      method: method,
      pipeline: w && w.pipeline || "",
      rubricPath: w && w.rubric || "",
      rubricNote: w && w.rubric_data && (w.rubric_data.note || (w.rubric_data.scoring_policy && (w.rubric_data.scoring_policy.principle || w.rubric_data.scoring_policy.basis)) || "") || "",
      policy: w && w.rubric_data && w.rubric_data.scoring_policy || null,
      rubricCount: Object.keys(rubricItems(w || {})).length,
      people: people,
      cohort: cohort,
      duplicateOf: duplicateOf,
      aligned: aligned,
      items: itemRows,
      fields: fieldRows,
      rules: rules,
      totals: totals,
      sameMax: maxes.length === 1 ? maxes[0] : null,
      mean: mean(totals),
      median: median(totals),
      min: totals.length ? Math.min.apply(null, totals) : null,
      maxTotal: totals.length ? Math.max.apply(null, totals) : null,
      totalsMatch: sumMismatch.length === 0,
      reviewItems: reviewItems,
      scoredItems: scoredItems,
      overrides: overrides,
      cohortOverrides: cohortOverrides,
      limits: limits,
      hasCredit: hasCredit,
      notes: notes,
      nStudents: students.length,
    };
  }

  function analyze(core, extra, docs) {
    const codes = (core.worksheets || []).map((w) => w.code);
    const out = {};
    codes.forEach((code) => { out[code] = analyzeWorksheet(core, extra, docs, code); });
    return out;
  }

  function data() {
    const core = root.CORE;
    const extra = root.SCORE_EXTRA || { notes: {}, status: {} };
    const docs = root.WORKSHEET_DOCS || { worksheets: {}, overrides: [] };
    return { core: core, extra: extra, docs: docs, all: core ? analyze(core, extra, docs) : {} };
  }

  function table(head, rows) {
    const th = head.map((c) => `<th${c.num ? ' class="num"' : ""}>${h(c.t)}</th>`).join("");
    const body = rows.map((r) => `<tr${r.attrs || ""}>${r.cells.map((c, i) => `<td data-label="${h(head[i].t)}"${head[i].num ? ' class="num"' : ""}>${c}</td>`).join("")}</tr>`).join("");
    return `<div class="table-wrap"><table class="find-table"><thead><tr>${th}</tr></thead><tbody>${body || `<tr><td colspan="${head.length}">No rows.</td></tr>`}</tbody></table></div>`;
  }
  function cards(items) {
    return `<div class="stat-row cols-4">${items.filter(Boolean).map((x) => `<div class="stat-card"><div class="v">${x.v}</div><div class="l">${h(x.l)}</div>${x.d ? `<p class="small">${x.d}</p>` : ""}</div>`).join("")}</div>`;
  }
  function crumbs(parts) {
    const last = parts.length - 1;
    return `<nav class="crumbs" aria-label="Breadcrumb">${parts.map((p, i) => i === last ? `<span aria-current="page">${h(p[0])}</span>` : `<a href="${h(p[1])}">${h(p[0])}</a><span aria-hidden="true">/</span>`).join("")}</nav>`;
  }
  function statusText(p) {
    if (p.scoring === "published" && p.inCohort) return "Published score, included in the summary";
    if (p.scoring === "published") return "Published score, excluded from the summary";
    if (p.scoring === "excluded_zero") return "Scoring file excluded: every item is 0 with confidence 0";
    if (p.scoring === "unpublished") return "Scoring file not published";
    return "No scoring file";
  }
  function extractText(p) {
    if (p.state === "absent") return "No extraction file";
    if (p.state === "failed") return "Extraction file has no readable value";
    return p.nText + " filled, " + p.nBlank + " blank, " + p.nMissing + " not extracted";
  }

  function distribution(model) {
    const counts = new Map();
    model.cohort.forEach((p) => {
      if (typeof p.total !== "number") return;
      const key = String(p.total);
      counts.set(key, (counts.get(key) || 0) + 1);
    });
    const rows = Array.from(counts.entries()).sort((a, b) => Number(a[0]) - Number(b[0]));
    if (rows.length < 2) return "";
    return `<h3>Stored totals</h3><p class="small">Each total is the number stored in that participant’s scoring file. The denominator is the ${model.cohort.length} participants included in the summary.</p>`
      + table([{ t: "Stored total" }, { t: "Participants", num: 1 }, { t: "Share of the summary" }], rows.map(([k, n]) => ({
        cells: [num(Number(k)) + (model.sameMax != null ? " of " + num(model.sameMax) : ""), num(n), pctText(n, model.cohort.length)],
      })));
  }

  function personCells(model, p) {
    const published = p.scoring === "published" && typeof p.total === "number";
    const total = published
      ? num(p.total) + (typeof p.max === "number" ? " of " + num(p.max) : "") + (p.inCohort ? "" : " · not in summary")
      : "–";
    const percent = p.inCohort && published && typeof p.max === "number" && p.max > 0
      ? share(p.total, p.max) : "–";
    const showCredit = p.inCohort && model.hasCredit;
    return [
      `<a href="#/explore/student/${h(p.id)}">${h(p.id)}</a>`,
      h(extractText(p)),
      h(statusText(p)),
      showCredit ? num(p.full) : "–",
      showCredit ? num(p.partial) : "–",
      showCredit ? num(p.none) : "–",
      total,
      percent,
      `<a href="#/findings/worksheets/${h(model.code)}?student=${h(p.id)}">Items</a>`,
    ];
  }

  function itemTable(model) {
    if (!model.items.length) return `<p class="missing-line">No published item scores for this worksheet.</p>`;
    const credit = model.hasCredit;
    const head = [{ t: "Item" }, { t: "Criterion" }].concat(credit
      ? [{ t: "Full credit", num: 1 }, { t: "Partial", num: 1 }, { t: "No credit", num: 1 }]
      : [{ t: "Scored", num: 1 }]).concat([{ t: "Mean score", num: 1 }, { t: "Most frequent filled response" }]);
    return table(head, model.items.map((it) => ({
      attrs: ` data-item="${h(it.id)}" data-label="${h((it.id + " " + it.title + " " + it.criterion).toLowerCase())}"`,
      cells: [
        `<b>${h(it.title)}</b><div class="small"><code>${h(it.id)}</code>${it.max == null ? "" : " · max " + h(it.max)}</div>`,
        it.criterion ? h(it.criterion) : `<span class="na">No criterion text in the rubric</span>`,
      ].concat(credit
        ? [pctText(it.full, it.denom), pctText(it.partial, it.denom), pctText(it.none, it.denom)]
        : [num(it.denom)]).concat([
        it.mean == null ? "–" : num(it.mean),
        it.frequent ? `${h(it.frequent.text)} <span class="small">${h(pctText(it.frequent.n, it.frequent.denom))} non-empty</span>` : `<span class="na">–</span>`,
      ]),
    })));
  }

  function fieldTable(model) {
    if (!model.fields.length || model.aligned) return "";
    return `<h3>Extracted fields</h3><p class="small">These counts describe the extraction only. They are not scores. “Not extracted” includes an empty value and the marker (not_extracted). A missing file is counted on its own.</p>`
      + table([{ t: "Field" }, { t: "Filled", num: 1 }, { t: "Blank", num: 1 }, { t: "Not extracted", num: 1 }, { t: "No file", num: 1 }],
        model.fields.map((f) => ({ cells: [`<code>${h(f.path)}</code>`, num(f.text), num(f.blank), num(f.missing), num(f.absent)] })));
  }

  function ruleTable(model) {
    const rows = model.rules.rows || [];
    if (model.rules.derived) {
      return `<p>Boolean flags for this worksheet in the site data were copied from the item scores (1 or above stored as correct, 0 as not correct, and a partial score left without a verdict). They are not a separate rule-based check, so they are not listed again.</p>`;
    }
    if (!rows.length) return `<p class="missing-line">No independent rule-based or boolean check records are in the extraction files.</p>`;
    const ruleRows = rows.filter((r) => r.family === "rule");
    const boolRows = rows.filter((r) => r.family !== "rule");
    const draw = (list, intro) => list.length ? `<p>${intro}</p>` + table(
      [{ t: "Check" }, { t: "Passed", num: 1 }, { t: "Failed", num: 1 }, { t: "No verdict", num: 1 }],
      list.map((r) => ({
        cells: [
          `<b>${h(clip(r.label, 140))}</b><div class="small"><code>${h(r.id)}</code>${r.detail ? " · " + h(clip(r.detail, 160)) : ""}</div>`,
          pctText(r.pass, r.n),
          pctText(r.fail, r.n),
          r.open ? pctText(r.open, r.n) : "0 of " + r.n,
        ],
      }))
    ) : "";
    return draw(ruleRows, "Each proportion uses the participants who have that check record as the denominator. A pass is the stored boolean, not a reviewed conclusion about understanding.")
      + draw(boolRows, "Boolean item checks stored beside the extraction. These are not the rubric scores. A partial score can disagree with the boolean.");
  }

  function rubricBlock(model, core) {
    const w = sheetOf(core, model.code);
    const items = w ? Object.entries(rubricItems(w)) : [];
    if (!items.length) return `<p class="missing-line">No rubric file is in the site data for this worksheet.</p>`;
    const policy = model.policy;
    const policyBits = policy ? Object.entries(policy).filter(([, v]) => typeof v === "string").map(([k, v]) => `<li><b>${h(k)}</b> — ${h(v)}</li>`).join("") : "";
    return `<p>Rubric items on file: ${num(items.length)}.${model.rubricPath ? ` Source: <code>${h(model.rubricPath)}</code>.` : ""}</p>`
      + (model.rubricNote ? `<p>${h(clip(model.rubricNote, 500))}</p>` : "")
      + (policyBits ? `<ul class="scoring-rules">${policyBits}</ul>` : "")
      + `<details class="tech"><summary>Criteria</summary><div class="tech-body">${table(
        [{ t: "Item" }, { t: "Maximum", num: 1 }, { t: "Criterion on file" }],
        items.map(([id, item]) => ({
          cells: [`<code>${h(id)}</code> ${h(item.label || "")}`, item.max_score == null ? "–" : num(item.max_score), h(clip(criterionText(item), 220)) || `<span class="na">–</span>`],
        }))
      )}</div></details>`
      + (model.totalsMatch && model.cohort.length ? `<p class="small">For every participant in the summary, the stored total equals the sum of that file’s item scores. This page copies the stored total.</p>` : "");
  }

  function responseBody(ocr, code, itemId) {
    if (!ocr) return `<p class="missing-line">No extraction file for this participant.</p>`;
    const vals = responsesFor(ocr, code, itemId);
    if (!vals.length) return `<p class="missing-line">No extracted field is tied to this item identifier.</p>`;
    return vals.map((r) => {
      const k = valueKind(r.value);
      const label = r.path === itemId ? "" : `<span class="small"><code>${h(r.path)}</code></span> `;
      if (k === "text") return `<p class="response-text">${label}${h(r.value)}</p>`;
      if (k === "blank") return `<p class="missing-line">${label}Blank. The extraction records (bos).</p>`;
      return `<p class="missing-line">${label}Not extracted.</p>`;
    }).join("");
  }

  function scoreBody(model, core, docs, person, itemId) {
    const rec = core.ws[person][model.code];
    const sc = rec.scoring;
    const w = sheetOf(core, model.code);
    if (!sc) {
      if (person && model.people.find((p) => p.id === person).scoring === "excluded_zero") {
        return `<p class="missing-line">A scoring file exists and gives every item 0 with confidence 0. Those numbers are not shown as a score.</p>`;
      }
      return `<p class="missing-line">No published score for this item.</p>`;
    }
    const it = (sc.items || []).find((x) => x.item === itemId);
    if (!it) return `<p class="missing-line">This item is not in the published scoring file.</p>`;
    const max = itemMax(w, it);
    const kind = creditOf(typeof it.score === "number" ? it.score : null, max);
    const rub = rubricItems(w)[itemId];
    const rule = ruleTextForScore(rub, it.score);
    const note = ((model.notes[person] || {})[model.code] || {})[itemId] || "";
    const ov = (docs.overrides || []).find((o) => o.student === person && o.worksheet === model.code && o.item === itemId);
    const check = rec.ocr && (rec.ocr.checks || []).find((c) => c.check === "item_checks." + itemId || c.check === itemId);
    const bits = [`<p><span class="badge">${h(creditLabel(kind))}</span> <strong>${h(it.score)}${max == null ? "" : " of " + h(max)}</strong>`
      + (it.confidence == null ? "" : ` <span class="small">confidence ${h(it.confidence)}</span>`)
      + (it.review ? ` <span class="badge badge-flag">Flagged for review</span>` : "")
      + `</p>`];
    if (ov) bits.push(`<p class="small">Researcher override recorded. ${h(ov.rationale || "No rationale text in the file.")}</p>`);
    else if (it.review) bits.push(`<p class="small">The review flag means the pipeline asked for a person to check this item. A later decision is not in the file.</p>`);
    else bits.push(`<p class="small">Published pipeline score. A researcher decision is not recorded for this item.</p>`);
    if (rule) bits.push(`<p class="small">Rubric text for this score: ${h(rule)}</p>`);
    if (note) bits.push(`<p class="small">Note stored on the score: ${h(note)}</p>`);
    if (check && !SCORE_DERIVED.has(model.code)) {
      const verdict = check.correct === true ? "passed" : check.correct === false ? "failed" : "no verdict";
      bits.push(`<p class="small">Separate extraction check: ${h(verdict)}${check.flag ? ". Flag: " + h(check.flag) : ""}. This boolean is not the score above.</p>`);
    }
    if (sc.source) bits.push(`<div class="src">${h(sc.source)}</div>`);
    return bits.join("");
  }

  function personPanel(model, core, docs, person, selected) {
    const p = model.people.find((x) => x.id === person);
    if (!p) return "";
    const rec = core.ws[person][model.code];
    let scores = "";
    if (model.items.length) {
      scores = model.items.map((it) => `<details class="find-item"><summary><code>${h(it.id)}</code> ${h(it.title)}</summary><div class="tech-body">${model.aligned ? responseBody(rec.ocr, model.code, it.id) : ""}${scoreBody(model, core, docs, person, it.id)}</div></details>`).join("");
    } else if (!model.duplicateOf) {
      scores = `<p class="missing-line">No published item scores.</p>`;
    }
    let fields = "";
    if (!model.aligned && rec.ocr) {
      fields = `<h4>Extracted responses</h4>` + rec.ocr.responses.map((r) => {
        const k = valueKind(r.value);
        const body = k === "text" ? h(r.value) : k === "blank" ? "Blank. The extraction records (bos)." : "Not extracted.";
        return `<details class="find-item"><summary><code>${h(r.path)}</code></summary><div class="tech-body"><p class="${k === "text" ? "response-text" : "missing-line"}">${body}</p></div></details>`;
      }).join("");
    }
    const publishedTotal = p.scoring === "published" && typeof p.total === "number";
    const total = publishedTotal
      ? `<p>Stored total ${h(p.total)}${typeof p.max === "number" ? " of " + h(p.max) : ""}${p.inCohort && typeof p.max === "number" && p.max > 0 ? " (" + h(share(p.total, p.max)) + ")" : ""}${p.inCohort ? "." : ". Not included in the credit summary."}</p>`
      : "";
    const held = p.scoring === "published" && !p.inCohort
      ? `<p class="small">These item scores are in the scoring file. They are left out of the credit counts because there is no usable extraction.</p>` : "";
    return `<article class="find-person" data-person="${h(person)}"${person === selected ? "" : " hidden"}><h3>${h(person)}</h3><p class="small">${h(extractText(p))}. ${h(statusText(p))}.</p>${held}${total}${model.aligned ? "" : (model.items.length && rec.ocr ? `<p class="small">Scores and extracted fields use different identifiers, so they are listed separately.</p>` : "")}${scores}${fields}<p class="small"><a href="#/explore/student/${h(person)}">Student profile</a></p></article>`;
  }

  function index() {
    const pack = data();
    if (!pack.core) return `<div class="page"><h1>Worksheet findings</h1><p>Data files are missing.</p></div>`;
    const listed = new Set(GROUPS.flatMap((g) => g.codes));
    const groups = GROUPS.map((g) => ({ label: g.label, codes: g.codes.filter((c) => pack.all[c]) }));
    const rest = Object.keys(pack.all).filter((c) => !listed.has(c));
    if (rest.length) groups.push({ label: "Other recorded worksheets", codes: rest });
    const body = groups.map((g) => {
      const cardsHtml = g.codes.map((code) => {
        const m = pack.all[code];
        const withFile = m.people.filter((p) => p.state !== "absent").length;
        const limit = m.limits[0] || "";
        const blob = `${code} ${m.title} ${m.topic} ${g.label} ${m.method.label}`.toLowerCase();
        return `<a class="find-ws" href="#/findings/worksheets/${h(code)}" data-code="${h(code)}" data-group="${h(g.label)}" data-title="${h(blob)}">
          <span class="k">${h(code)}</span>
          <h3>${h(m.title)}</h3>
          <p>${h(m.topic)}</p>
          <dl class="find-facts">
            <dt>Assessment</dt><dd>${h(m.method.label)}</dd>
            <dt>Extraction files</dt><dd>${h(withFile)} of ${h(m.nStudents)}</dd>
            <dt>In the score summary</dt><dd>${m.duplicateOf ? "Not summarised" : h(m.cohort.length) + " of " + h(m.nStudents)}</dd>
            <dt>Item results</dt><dd>${m.duplicateOf ? "Not used as WS11 answers" : m.items.length ? (m.aligned ? "Joined to extracted fields" : "Scores and fields listed separately") : "No published item scores"}</dd>
          </dl>
          ${limit ? `<p class="small">${h(limit)}</p>` : ""}
        </a>`;
      }).join("");
      return `<section class="ws-group" data-group-block="${h(g.label)}"><h2>${h(g.label)}</h2><div class="find-ws-grid">${cardsHtml}</div></section>`;
    }).join("");
    const chips = ["All"].concat(GROUPS.map((g) => g.label)).map((label, i) =>
      `<button type="button" class="chip${i === 0 ? " on" : ""}" data-group="${i === 0 ? "" : h(label)}" aria-pressed="${i === 0 ? "true" : "false"}">${h(label)}</button>`).join("");
    return `<div class="page wide find-page">${crumbs([["Findings", "#/findings"], ["Worksheet findings"]])}
      <p class="kicker">Findings</p>
      <h1>Worksheet findings</h1>
      <p class="lead">Results read from the extracted responses and the published scoring files. A stored score is a pipeline result. It is not a reviewed conclusion about learning.</p>
      <div class="ws-search-bar">
        <label class="sr-only" for="findSearch">Search worksheets</label>
        <input type="search" id="findSearch" placeholder="Search by code, title, or method" autocomplete="off">
        <span class="ws-count" id="findCount">${Object.keys(pack.all).length} worksheets</span>
      </div>
      <div class="ws-filters" role="group" aria-label="Filter by worksheet purpose">${chips}</div>
      <div id="findGroups">${body}</div>
      <p class="empty" id="findEmpty" hidden>No worksheets match.</p>
      <h2>Collected materials</h2>
      <p>Blank worksheets, answer keys, and scanned submissions stay with the collected data. <a href="#/explore/worksheets">Open the worksheet files</a>.</p>
    </div>`;
  }

  function page(code, q) {
    const pack = data();
    q = q || {};
    if (!pack.core) return `<div class="page"><h1>Worksheet findings</h1><p>Data files are missing.</p></div>`;
    const model = pack.all[code];
    if (!model) {
      return `<div class="page">${crumbs([["Findings", "#/findings"], ["Worksheet findings", "#/findings/worksheets"], ["Not found"]])}
        <h1>Worksheet not found</h1><p>No worksheet “${h(code)}” is in this archive.</p><p><a href="#/findings/worksheets">Back to worksheet findings</a></p></div>`;
    }
    if (model.duplicateOf) return duplicatePage(model);
    const withFile = model.people.filter((p) => p.state !== "absent").length;
    const filled = model.people.filter((p) => p.nText > 0).length;
    const head = [{ t: "Participant" }, { t: "Extraction" }, { t: "Scoring status" }, { t: "Full credit", num: 1 }, { t: "Partial", num: 1 }, { t: "No credit", num: 1 }, { t: "Stored total" }, { t: "Percent of maximum" }, { t: "Detail" }];
    const rows = model.people.map((p) => ({
      attrs: ` data-student="${h(p.id)}"`,
      cells: personCells(model, p),
    }));
    const selected = pack.core.students.indexOf(q.student) !== -1 ? q.student : "";
    const panels = pack.core.students.map((s) => personPanel(model, pack.core, pack.docs, s, selected)).join("");
    const summaryCards = [
      { v: num(withFile), l: "Participants with an extraction file", d: "Of " + model.nStudents + " pseudonyms." },
      { v: num(filled), l: "With at least one filled response", d: "A blank or a failed extraction is not counted here." },
      { v: num(model.cohort.length), l: "Included in the score summary", d: "Published score and a usable extraction." },
      model.sameMax != null && model.cohort.length ? { v: num(model.mean), l: "Mean stored total", d: "Of " + num(model.sameMax) + ". Median " + num(model.median) + ". Range " + num(model.min) + "–" + num(model.maxTotal) + "." } : null,
    ];
    const policyLine = model.code === "WS10"
      ? `<p>The processing notes describe Python rules for the energy-threshold table. The site data’s pipeline label for this worksheet is <code>${h(model.pipeline || "–")}</code>. Item scores and boolean checks are both shown, and they are not treated as the same result.</p>`
      : `<p>Assessment label used on this page: ${h(model.method.label)}. Pipeline label stored in the site data: <code>${h(model.pipeline || "–")}</code>.</p>`;
    return `<div class="page wide find-page">${crumbs([["Findings", "#/findings"], ["Worksheet findings", "#/findings/worksheets"], [code]])}
      <p class="kicker">Worksheet findings</p>
      <h1>${h(code)} · ${h(model.title)}</h1>
      <p class="lead">${h(model.topic)} The figures below count extracted responses and published scores. They describe what is in the files. They are not a measure of learning gain.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#overview">Overview</a>
        <a href="#participants">Participants</a>
        <a href="#items">Items</a>
        <a href="#summary">Summary</a>
        <a href="#assessment">Assessment</a>
        <a href="#limits">Limitations</a>
      </nav>
      ${cards(summaryCards)}
      <section class="section-block" id="overview"><h2>Overview</h2>
        ${policyLine}
        <p>A response can be extracted, scored, flagged for review, or missing. An extraction file is not itself a score. ${model.cohort.length ? `The score summary uses ${model.cohort.length} of ${model.nStudents} participants: those with a published scoring file and an extraction that contains at least one value other than a failed read.` : "No participant meets both conditions, so there is no score summary."}</p>
        <p><a href="#/explore/worksheet/${h(code)}">Blank worksheet, answer key, and scanned submissions</a></p>
      </section>
      <section class="section-block" id="participants"><h2>Participant results</h2>
        <p>Full credit, partial credit, and no credit count published item scores for participants in the summary. A participant without a published score shows a dash, not a zero. Percent is shown only when the scoring file stores both a total and a maximum.</p>
        <div class="ws-search-bar">
          <label class="sr-only" for="findPsearch">Filter participants</label>
          <input type="search" id="findPsearch" placeholder="Filter by pseudonym" autocomplete="off">
        </div>
        ${table(head, rows)}
        <p class="empty" id="findPempty" hidden>No participants match.</p>
      </section>
      <section class="section-block" id="items"><h2>Item results</h2>
        <p>${model.aligned ? "Each item is joined to the extracted field that uses the same identifier." : "Item scores and extracted fields do not share identifiers. The score table and the field table are separate."} Proportions use only participants in the score summary who have a numeric score for that item. ${model.items[0] ? "The denominator is shown in each cell." : ""}</p>
        ${model.items.some((it) => it.blankScore) ? `<p class="small">${model.items.reduce((a, it) => a + it.blankScore, 0)} scored items in the summary have no filled extraction on the joined field. A blank is counted in the extraction columns and, when the score is 0, also as no credit. It is not labelled incorrect on its own.</p>` : ""}
        <div class="ws-search-bar">
          <label class="sr-only" for="findIsearch">Filter items</label>
          <input type="search" id="findIsearch" placeholder="Filter items" autocomplete="off">
        </div>
        ${itemTable(model)}
        ${fieldTable(model)}
        <h3>One participant</h3>
        <p class="small">Open a participant to read each stored score and, where the identifiers match, the extracted response.</p>
        <label>Participant <select id="findStudent"><option value="">Choose a participant</option>${pack.core.students.map((s) => `<option value="${h(s)}"${s === selected ? " selected" : ""}>${h(s)}</option>`).join("")}</select></label>
        <p id="findPersonEmpty"${selected ? " hidden" : ""}>Choose a participant to read item-level responses.</p>
        <div id="findPeople">${panels}</div>
      </section>
      <section class="section-block" id="summary"><h2>Aggregate findings</h2>
        ${model.cohort.length ? `<p>Included participants: ${h(model.cohort.map((p) => p.id).join(", "))}.</p>
          <p>Mean stored total ${h(num(model.mean))}, median ${h(num(model.median))}, range ${h(num(model.min))}–${h(num(model.maxTotal))}${model.sameMax != null ? ", each out of " + h(num(model.sameMax)) + ". The mean is " + h(share(model.mean, model.sameMax)) + " of that maximum." : ". A single percentage is not shown because the files do not share one maximum."}</p>
          ${distribution(model)}
          <h3>By item</h3>
          <p class="small">The item table above is the aggregate. Full, partial, and no credit are disjoint. Their denominator is the number of included participants with a numeric score on that item, not the full cohort of ${h(model.nStudents)}.</p>`
          : `<p class="missing-line">No aggregate score is available. A published score and a usable extraction are both required.</p>`}
        ${model.cohortOverrides.length ? `<h3>Researcher overrides</h3><p>${model.cohortOverrides.length} item score${model.cohortOverrides.length === 1 ? "" : "s"} in the summary record a researcher override.</p>${table([{ t: "Participant" }, { t: "Item" }, { t: "Stored score" }, { t: "Rationale in the file" }], model.cohortOverrides.map((o) => ({ cells: [h(o.student), `<code>${h(o.item)}</code>`, num(o.score), h(o.rationale || "–")] })))}` : ""}
      </section>
      <section class="section-block" id="assessment"><h2>Assessment and validation</h2>
        <h3>${model.method.id === "rule" ? "Rule-based scores" : model.method.id === "consistency" ? "Consistency scores" : "Rubric scores"}</h3>
        ${rubricBlock(model, pack.core)}
        ${model.method.id === "consistency" ? `<p>The rubric scores internal consistency. A high score means the recorded tree agrees with itself. It does not mean the tree matches one correct answer.</p>` : ""}
        <h3>Rule-based and boolean checks</h3>
        ${ruleTable(model)}
        <p class="small">A check that passes does not, by itself, establish that the participant understood the concept.</p>
      </section>
      <section class="section-block" id="limits"><h2>Limitations and coverage</h2>
        ${model.limits.length ? `<ul>${model.limits.map((x) => `<li>${h(x)}</li>`).join("")}</ul>` : `<p>No further coverage gap is recorded for this worksheet.</p>`}
        <details class="tech"><summary>Source paths</summary><div class="tech-body">
          ${model.rubricPath ? `<div class="src">${h(model.rubricPath)}</div>` : ""}
          ${model.people.filter((p) => p.ocrSource).slice(0, 1).map((p) => `<div class="src">${h(p.ocrSource)}</div>`).join("")}
          ${model.people.filter((p) => p.source).slice(0, 1).map((p) => `<div class="src">${h(p.source)}</div>`).join("")}
        </div></details>
      </section>
      <p><a href="#/findings/worksheets">All worksheet findings</a></p>
    </div>`;
  }

  function duplicatePage(model) {
    return `<div class="page wide find-page">${crumbs([["Findings", "#/findings"], ["Worksheet findings", "#/findings/worksheets"], [model.code]])}
      <p class="kicker">Worksheet findings</p>
      <h1>${h(model.code)} · ${h(model.title)}</h1>
      <p class="lead">${h(model.topic)}</p>
      <div class="warn">WS11 is not used as scored evidence. The extraction record repeats WS14 for every participant, and the scoring files are not published.</div>
      <section class="section-block" id="overview"><h2>Overview</h2>
        <p>The worksheet rubric describes a feedback survey and a short set of closed items. The extraction files stored under WS11 do not provide a separate response set.</p>
        <p><a href="#/findings/worksheets/${h(model.duplicateOf)}">WS14 findings</a> · <a href="#/explore/worksheet/WS11">WS11 files in collected data</a></p>
      </section>
      <section class="section-block" id="assessment"><h2>Assessment</h2>
        <p>Rubric source: <code>${h(model.rubricPath || "–")}</code>. ${model.rubricCount ? h(model.rubricCount) + " rubric entries are on file." : "No rubric entries are on file."}</p>
        <p>The method is documented. Corresponding published scores are not. Zero-confidence files are not shown as results, and the repeated WS14 text is not scored again here.</p>
      </section>
      <section class="section-block" id="limits"><h2>Limitations and coverage</h2>
        <ul>${model.limits.map((x) => `<li>${h(x)}</li>`).join("")}</ul>
      </section>
      <p><a href="#/findings/worksheets">All worksheet findings</a></p>
    </div>`;
  }

  function bind() {
    const search = document.getElementById("findSearch");
    if (search) {
      let group = "";
      const apply = () => {
        const q = search.value.trim().toLowerCase();
        const cards = document.querySelectorAll(".find-ws");
        let visible = 0;
        cards.forEach((card) => {
          const ok = (!q || card.dataset.title.indexOf(q) !== -1 || card.dataset.code.toLowerCase().indexOf(q) !== -1) && (!group || card.dataset.group === group);
          card.hidden = !ok;
          if (ok) visible += 1;
        });
        document.querySelectorAll(".ws-group").forEach((g) => {
          g.hidden = !Array.from(g.querySelectorAll(".find-ws")).some((c) => !c.hidden);
        });
        const count = document.getElementById("findCount");
        if (count) count.textContent = (q || group) ? visible + " of " + cards.length + " worksheets" : cards.length + " worksheets";
        const empty = document.getElementById("findEmpty");
        if (empty) empty.hidden = visible !== 0;
      };
      search.addEventListener("input", apply);
      document.querySelectorAll(".ws-filters .chip").forEach((btn) => {
        btn.addEventListener("click", () => {
          group = btn.dataset.group || "";
          document.querySelectorAll(".ws-filters .chip").forEach((b) => {
            const on = b === btn;
            b.classList.toggle("on", on);
            b.setAttribute("aria-pressed", on ? "true" : "false");
          });
          apply();
        });
      });
    }
    const psearch = document.getElementById("findPsearch");
    if (psearch) {
      psearch.addEventListener("input", () => {
        const q = psearch.value.trim().toLowerCase();
        const rows = document.querySelectorAll("#participants tbody tr");
        let shown = 0;
        rows.forEach((row) => {
          const ok = !q || (row.dataset.student || "").toLowerCase().indexOf(q) !== -1;
          row.hidden = !ok;
          if (ok) shown += 1;
        });
        const empty = document.getElementById("findPempty");
        if (empty) empty.hidden = shown !== 0;
      });
    }
    const isearch = document.getElementById("findIsearch");
    if (isearch) {
      isearch.addEventListener("input", () => {
        const q = isearch.value.trim().toLowerCase();
        document.querySelectorAll("#items tbody tr").forEach((row) => {
          row.hidden = !!(q && (row.dataset.label || "").indexOf(q) === -1 && (row.dataset.item || "").toLowerCase().indexOf(q) === -1);
        });
      });
    }
    const sel = document.getElementById("findStudent");
    if (sel) {
      const show = () => {
        document.querySelectorAll(".find-person").forEach((el) => { el.hidden = el.dataset.person !== sel.value; });
        const empty = document.getElementById("findPersonEmpty");
        if (empty) empty.hidden = !!sel.value;
      };
      sel.addEventListener("change", () => {
        show();
        const raw = location.hash.replace(/^#\/?/, "");
        const parts = raw.split("?");
        const params = new URLSearchParams(parts[1] || "");
        if (sel.value) params.set("student", sel.value);
        else params.delete("student");
        const next = "#/" + parts[0] + (params.toString() ? "?" + params.toString() : "");
        if (history.replaceState) history.replaceState(null, "", next);
      });
      show();
    }
  }

  root.WorksheetFindings = { analyze: analyze, index: index, page: page, bind: bind };
})(typeof window !== "undefined" ? window : globalThis);
