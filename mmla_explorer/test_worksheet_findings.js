/* Checks worksheet findings against the site data.
   Run from the repository root:
     node mmla_explorer/test_worksheet_findings.js
*/
"use strict";

const fs = require("fs");
const path = require("path");
const vm = require("vm");

const root = path.resolve(__dirname, "..");
const site = path.join(root, "mmla_explorer", "site");
const context = { console: console };
context.window = context;
context.globalThis = context;
vm.createContext(context);

function load(rel) {
  vm.runInContext(fs.readFileSync(path.join(site, rel), "utf8"), context, { filename: rel });
}

load("data/core.js");
load("assets/worksheet_findings.js");
if (fs.existsSync(path.join(site, "data/score_extra.js"))) load("data/score_extra.js");
if (fs.existsSync(path.join(site, "data/worksheet_docs.js"))) load("data/worksheet_docs.js");

const core = context.CORE;
const extra = context.SCORE_EXTRA || { notes: {}, status: {} };
const docs = context.WORKSHEET_DOCS || { worksheets: {}, overrides: [] };
const WF = context.WorksheetFindings;
const all = WF.analyze(core, extra, docs);
const codes = ["WS1", "WS3", "WS4", "WS5", "WS6", "WS7", "WS10", "WS11", "WS12", "WS13", "WS14", "WS15"];
let failed = 0;
function check(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL", msg);
  }
}

check(codes.every((c) => all[c]), "every listed worksheet is analysed");

const indexHtml = WF.index();
codes.forEach((code) => {
  check(indexHtml.indexOf('href="#/findings/worksheets/' + code + '"') !== -1, code + " catalogue link");
  check(indexHtml.indexOf('href="#/explore/worksheet/' + code + '"') === -1, code + " catalogue does not open collected data");
});
check(indexHtml.indexOf('href="#/explore/worksheets"') !== -1, "collected worksheets link stays on the landing page");

codes.forEach((code) => {
  const model = all[code];
  const html = WF.page(code, {});
  check(html.indexOf("<h1>" + code) !== -1, code + " page heading");
  check(html.indexOf("#/findings/worksheets") !== -1, code + " returns to findings");
  if (code !== "WS11") {
    check(html.indexOf('href="#/explore/worksheet/' + code + '"') !== -1, code + " links to collected files without replacing the page");
    check(html.indexOf('id="participants"') !== -1, code + " participant section");
    check(html.indexOf('id="items"') !== -1, code + " item section");
  } else {
    check(model.cohort.length === 0, "WS11 has no score summary");
    check(model.duplicateOf === "WS14", "WS11 duplicates WS14");
    check(html.indexOf("not used as scored evidence") !== -1, "WS11 states it is not scored evidence");
    check(html.indexOf("No credit") === -1, "WS11 does not present credit counts");
  }
  model.items.forEach((it) => {
    check(it.full + it.partial + it.none + it.scored === it.denom, code + " " + it.id + " credit parts sum to the denominator");
  });
  const creditSum = model.items.reduce((a, it) => a + it.none, 0);
  const peopleNone = model.cohort.reduce((a, p) => a + (p.none || 0), 0);
  check(creditSum === peopleNone, code + " no-credit total matches participants in the summary");
  model.cohort.forEach((p) => {
    const sc = core.ws[p.id][code].scoring;
    check(sc && sc.total_score === p.total && sc.max_score === p.max, code + " " + p.id + " total copied from the scoring file");
    const kinds = { full: 0, partial: 0, none: 0, scored: 0 };
    (sc.items || []).forEach((it) => {
      const max = typeof it.max_score === "number" ? it.max_score : ((core.worksheets.find((w) => w.code === code).rubric_data.items || {})[it.item] || {}).max_score;
      let kind = "scored";
      if (typeof max === "number") kind = it.score <= 0 ? "none" : it.score + 1e-9 >= max ? "full" : "partial";
      kinds[kind] += 1;
    });
    check(kinds.full === p.full && kinds.partial === p.partial && kinds.none === p.none, code + " " + p.id + " credit counts");
  });
  core.students.forEach((s) => {
    const rec = core.ws[s][code];
    if (!rec.ocr) check(!model.cohort.some((p) => p.id === s), code + " " + s + " without extraction is outside the summary");
  });
});

check(all.WS1.cohort.length === 13, "WS1 summary is 13");
check(!all.WS1.cohort.some((p) => p.id === "Amy" || p.id === "Marco"), "Amy and Marco are outside the WS1 summary");
check(all.WS6.cohort.length === 13 && !all.WS6.cohort.some((p) => p.id === "Melinda" || p.id === "Serena"), "WS6 leaves out scores with no extraction");
const melinda = all.WS6.people.find((p) => p.id === "Melinda");
check(melinda.scoring === "published" && melinda.inCohort === false && melinda.none === 4, "Melinda WS6 score is stored and not treated as a summary incorrect count");
check(all.WS6.items.reduce((a, it) => a + it.none, 0) === all.WS6.cohort.reduce((a, p) => a + p.none, 0), "WS6 no-credit excludes Melinda");
check(all.WS12.cohort.length === 13, "WS12 summary is 13");
check(all.WS14.rules.rows.some((r) => r.id.indexOf("xeno_consistency") === 0), "WS14 has consistency checks");
check(all.WS14.rules.rows.some((r) => r.family === "boolean"), "WS14 boolean checks stay separate");
check(all.WS15.rules.rows.some((r) => r.id.indexOf("titanic_numeric") === 0), "WS15 has numeric checks");
check(all.WS12.rules.derived === true && all.WS12.rules.rows.length === 0, "WS12 derived booleans are not a second method");
check(all.WS5.rules.rows.some((r) => r.id.indexOf("trials") === 0), "WS5 trial checks are present");
const amyNote = extra.notes && extra.notes.Amy && extra.notes.Amy.WS12 && extra.notes.Amy.WS12.WS12_R1;
if (amyNote) {
  const html = WF.page("WS12", { student: "Amy" });
  check(html.indexOf("Note stored on the score") !== -1 && html.indexOf("Enerji") !== -1, "WS12 score note is shown for Amy");
} else {
  check(false, "WS12 score notes were not loaded");
}
check(all.WS5.cohortOverrides.length === 5 || (docs.overrides || []).filter((o) => o.worksheet === "WS5").length === 5, "WS5 overrides");

const studentHtml = WF.page("WS1", { student: "Bruno" });
check(studentHtml.indexOf('data-person="Bruno"') !== -1 && studentHtml.indexOf('data-person="Amy" hidden') !== -1, "participant detail opens Bruno and hides others");

console.log(failed ? failed + " failed" : "worksheet findings checks passed");
process.exit(failed ? 1 : 0);
