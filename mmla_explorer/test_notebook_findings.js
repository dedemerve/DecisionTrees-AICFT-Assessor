/* Checks final-homework findings against the site notebook records.
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
vm.runInContext(fs.readFileSync(path.join(site, "data/core.js"), "utf8"), context, { filename: "core.js" });
vm.runInContext(fs.readFileSync(path.join(site, "assets/notebook_findings.js"), "utf8"), context, { filename: "notebook_findings.js" });

const core = context.CORE;
const NF = context.NotebookFindings;
const model = NF.analyze(core);
const html = NF.page(core);
let failed = 0;
function check(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL", msg);
  }
}

check(model.rows.length === core.students.length, "one row per participant");
check(model.notebooks.length === 14, "14 inspectable notebooks");
check(model.reports.map((r) => r.s).join() === "Marco", "Marco is the written report");
check(!model.reports[0].file, "Marco has no notebook file");
check(model.reports[0].extraction.models === 1, "Marco's report stores 1 model");
check(model.reports[0].extraction.targets.join() === "Tur", "Marco's report stores Tur only");

const irma = model.notebooks.find((r) => r.s === "Irma");
check(irma.extraction.models === 4, "Irma records 4 models");
check(model.notebookModels.filter((r) => r.extraction.models === 3).length === 13, "13 notebooks record 3 models");

const errors = model.notebooks.filter((r) => r.file.cells_with_error_output > 0).map((r) => r.s).sort();
check(errors.join() === "Melinda,Serena", "error outputs are Melinda and Serena");
const revisits = model.notebooks.filter((r) => r.file.order_reversals > 0).map((r) => r.s).sort();
check(revisits.join() === "Irma,Melinda,Serena", "run-counter drops are Irma, Melinda, Serena");

check(model.scored.length === 15, "stored rubric totals for all 15");
check(model.samePossible === 100, "every stored total is out of 100");
check(model.medianAwarded === 58, "median stored rubric points is 58");
check(model.minAwarded === 16 && model.maxAwarded === 74, "rubric range is 16 to 74");

check(html.includes("Inspectable notebooks"), "summary card for notebooks");
check(html.includes("Most common model count"), "summary card for models");
check(html.includes("Notebooks with an error output"), "summary card for errors");
check(html.includes("Median stored rubric points"), "summary card for rubric points");
check(html.includes("Overall findings"), "overall findings section");
check(html.includes("Participant results"), "participant table");
check(html.includes("Methodology and data quality"), "methodology fold");
check(html.includes("Scoring method and limitations"), "scoring limitations");
check(html.includes("not a verified grade"), "rubric is not called a verified grade");
check(html.includes("does not establish learning gain"), "rubric is not called learning gain");
check(html.includes("not proof the code was correct"), "missing error is not correctness");
check(html.includes("does not, by itself, show a lack of understanding"), "an error is not a lack of understanding");
check(html.includes("does not show how the participant chose"), "target order is not reasoning");
check(html.includes("does not show whether the change helped"), "revisiting is not interpreted");
check(!html.includes('open'), "methodology starts closed");
check(!html.includes("#/explore/student/"), "participant rows do not open a profile");
check(!html.includes("scoring_output_"), "raw scoring paths stay off the page");
check(!html.includes("Final Ödevi"), "raw homework folder stays off the page");
check(html.includes("Written report"), "Marco's report is labelled");
check(html.includes("not a zero"), "a dash is not described as zero");
check(html.includes("weekly Colab") || html.includes("Weekly Colab"), "guided notebooks stay separate");
check(html.includes("YasamAlani"), "stored target names are shown");
check((html.match(/data-label="Error output recorded"/g) || []).length === 15, "error column for every participant");

const marcoRow = html.split("<tr>").find((row) => row.includes(">Marco<"));
check(marcoRow && marcoRow.includes('class="na"'), "Marco's unavailable measures are a dash");
check(marcoRow && !/>0</.test(marcoRow), "Marco's blank cells are not a zero");

if (failed) {
  console.error(failed + " failed");
  process.exit(1);
}
console.log("notebook findings ok");
