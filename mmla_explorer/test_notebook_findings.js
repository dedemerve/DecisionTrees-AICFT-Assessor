/* Checks final-homework findings against the notebook files and inspection records.
   Run from the repository root:
     node mmla_explorer/test_notebook_findings.js
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
load("data/notebook_evidence.js");
load("assets/notebook_findings.js");

const core = context.CORE;
const evidence = context.NOTEBOOK_EVIDENCE;
const NF = context.NotebookFindings;
const model = NF.analyze(core, evidence);
const html = NF.page(core, evidence);
let failed = 0;
function check(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL", msg);
  }
}

check(model.rows.length === 15, "one row per participant");
check(model.notebooks.length === 14, "14 notebooks");
check(model.reports.map((r) => r.s).join() === "Marco", "Marco is the report");
check(model.reports[0].file == null, "Marco has no notebook structure");
check(model.reports[0].inspection.stored_model_count === 1, "Marco stored model count is 1");
check(model.medianAwarded === 58 && model.samePossible === 100, "rubric median stays 58 of 100");
check(model.minAwarded === 16 && model.maxAwarded === 74, "rubric range stays 16 to 74");

const irma = model.rows.find((r) => r.s === "Irma");
check(irma.inspection.stored_model_count === 4, "Irma stored count stays 4");
check(irma.inspection.depth_search_records === 1, "Irma depth-search list stays 1");
check(irma.inspection.preliminary_models === 3, "Irma preliminary list stays 3");
check(irma.file.code_present.get_dummies === false, "get_dummies is absent from Irma's code");
check(irma.file.code_cells === 16 && irma.file.markdown_cells === 19, "Irma cell counts match the file");

const amy = model.rows.find((r) => r.s === "Amy");
check(amy.file.code_cells === 16 && amy.file.markdown_cells === 6, "Amy cell counts match the file");
check(amy.inspection.test_size === 0.3, "Amy test fraction stays 0.3");

["Melinda", "Serena"].forEach((name) => {
  const row = model.rows.find((r) => r.s === name);
  check(row.file.error_types.join() === "KeyboardInterrupt", name + " error is KeyboardInterrupt");
  check(row.file.upload_interrupt === true, name + " error is an upload interrupt");
});

const ulysses = model.rows.find((r) => r.s === "Ulysses");
check(ulysses.inspection.synthetic === true, "Ulysses substitute table flag stays");
check(ulysses.file.code_cells === 1, "Ulysses file has one code cell");

check(html.includes("Written report"), "Marco is labelled Written report");
check(!html.includes("The inspection read the report because"), "Marco has no paragraph under the name");
check(!html.includes("successful"), "no success judgement");
check(!html.includes("unsuccessful"), "no failure judgement");
check(!html.includes("mastered"), "no mastery judgement");
check(html.includes("Assignment evidence"), "task table is present");
check(html.includes("Patterns worth noting"), "patterns section is present");
check(html.includes("Not stored is not a zero"), "a missing depth table is not called a zero");
check(html.includes("not a reviewed grade"), "rubric is not a reviewed grade");
check(html.includes("Methodology and data quality"), "methodology fold exists");
check(!html.includes("<details class=\"find-fold\" id=\"method\" open"), "methodology starts closed");
check(!html.includes("#/explore/student/"), "rows do not open a profile");
check(!html.includes("scoring_output_"), "scoring paths stay off the page");
check((html.match(/class="find-toggle"/g) || []).length === 15, "each participant can expand");
check(html.includes("data-nb=\"Marco\""), "Marco has a details control");

const marco = html.split('data-nb="Marco"')[0].split("<tr>").pop();
check(marco && marco.includes("Written report"), "the label sits on Marco's row");
check(marco && !marco.includes("files.upload"), "the upload note is not on Marco's row");

if (failed) {
  console.error(failed + " failed");
  process.exit(1);
}
console.log("notebook findings ok");
