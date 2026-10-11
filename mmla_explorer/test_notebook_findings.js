/* Checks final-homework findings against the assignment evidence.
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
check(model.medianAwarded === 58 && model.samePossible === 100, "rubric median stays 58 of 100");
check(model.minAwarded === 16 && model.maxAwarded === 74, "rubric range stays 16 to 74");

const irma = model.rows.find((r) => r.s === "Irma");
check(irma.inspection.stored_model_count === 4, "Irma stored count is unchanged");
check(irma.inspection.checks.encoding === "not_found", "Irma has no recorded category encoding");
check(irma.file.code_cells === 16, "Irma cell count matches the file");

const marco = model.rows.find((r) => r.s === "Marco");
check(marco.inspection.checks.value_counts === "not_found", "Marco class counts are not in the report");
check(marco.inspection.checks.stratify === "undetermined", "Marco stratification is not determined");
check(marco.inspection.checks.depth_tables === 0, "Marco has no depth-search table");
check(marco.inspection.checks.reflection.settings === "not_found", "Marco has no three-settings text");
check(marco.inspection.checks.reflection.data === "found", "Marco data reflection is stored");

const ulysses = model.rows.find((r) => r.s === "Ulysses");
check(ulysses.inspection.synthetic === true, "Ulysses substitute table stays flagged");
check(ulysses.inspection.checks.depth_comments === 0, "Ulysses has no stored depth comment");

check(html.includes("Data exploration"), "exploration section");
check(html.includes("Model construction and evaluation"), "model section");
check(html.includes("Visualisation and interpretation"), "visual section");
check(html.includes("Written responses and reflection"), "reflection section");
check(html.includes("What the submissions show"), "cohort section");
check(!html.includes("First stored target"), "target-order panel is gone");
check(!html.includes("Stored model count"), "model-count panel is gone");
check(!html.includes(">successful<") && !html.includes("unsuccessful") && !html.includes("mastered"), "no mastery label");
check(html.includes("not a mark that the step was done correctly"), "presence is not correctness");
check(html.includes("does not assign the rubric"), "no new rubric score");
check(html.includes("Written report"), "Marco label");
check(!html.includes("The inspection read the report because"), "no paragraph under Marco");
check(html.includes("not a reviewed grade"), "pipeline rubric stays labelled");
check(!html.includes("<details class=\"find-fold\" id=\"method\" open"), "methodology starts closed");
check(!html.includes("#/explore/student/"), "rows do not open a profile");
check(!html.includes("scoring_output_"), "scoring paths stay off the page");
check((html.match(/class="find-toggle"/g) || []).length === 15, "each participant can expand");
check(html.includes("They are not compared with another participant") || html.includes("not compared with another participant"), "MCR values are not ranked");

if (failed) {
  console.error(failed + " failed");
  process.exit(1);
}
console.log("notebook findings ok");
