/* Checks the student-profile summary against the site data.
   Run from the repository root:
     node mmla_explorer/test_student_profiles.js
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
load("data/score_extra.js");
load("data/worksheet_docs.js");
load("data/frames.js");
load("data/notebook_evidence.js");
load("assets/worksheet_findings.js");
load("assets/student_profiles.js");

const SP = context.StudentProfiles;
const model = SP.analyze(context.CORE, context.FRAMES, context.NOTEBOOK_EVIDENCE);
const html = SP.page(context.CORE, context.FRAMES, context.NOTEBOOK_EVIDENCE);
const amy = model.people.find((p) => p.id === "Amy");
const marco = model.people.find((p) => p.id === "Marco");
const nadia = model.people.find((p) => p.id === "Nadia");
const melinda = model.people.find((p) => p.id === "Melinda");
const marcoHtml = SP.summary("Marco");
const amyHtml = SP.summary("Amy");
const frames = SP.framesNote();
let failed = 0;
function check(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL", msg);
  }
}

check(model.people.length === 15, "15 participants");
check(model.expectedWorksheets === 12, "12 worksheets");
check(model.people.filter((p) => p.missing.length === 0).length === 11, "11 full worksheet extractions");
check(amy.missing.join() === "WS1,WS3,WS4,WS5", "Amy missing worksheets");
check(marco.missing.join() === "WS1,WS3,WS4,WS5", "Marco missing worksheets");
check(melinda.missing.join() === "WS6,WS7,WS10,WS12", "Melinda missing worksheets");
check(melinda.scoreWithoutExtraction.join() === "WS6,WS7", "Melinda score files without extraction");
check(model.people.filter((p) => p.frameSessions.length === 2).length === 7, "7 participants with both frame sessions");
check(model.people.filter((p) => p.pythonKind === "notebook").length === 14, "14 notebooks");
check(marco.pythonKind === "report", "Marco is a written report");
check(nadia.threshold === 285, "Nadia class-session threshold changes");
check(amy.categories === 4, "Amy has all four source categories");
check(html.includes("Patterns across participants"), "cohort patterns");
check(html.includes("What is stored for each participant"), "completeness matrix");
check((html.match(/class="student-card"/g) || []).length === 15, "15 profile cards");
check(html.includes("WS10") && html.includes("WS7"), "highest and lowest stored totals");
check(!html.includes("no longer in the data folder"), "overview does not say videos were lost");
check(!/rushing|guessing|indecisive|high performer|mastered/i.test(html), "no invented participant types");
check(html.includes(SP.HF_FRAMES), "Hugging Face frame dataset link");
check(html.includes("from 11% to 100%"), "stored one-thing-at-a-time range");
check(!html.includes("–%"), "rate range is not blank");
check(marcoHtml.includes("Written report"), "Marco summary uses Written report");
check(marcoHtml.includes("not applicable"), "Marco notebook measures are not applicable");
check(amyHtml.includes("Participant evidence summary"), "evidence summary heading");
check(SP.summary("Bruno").includes("across 2 of 2 class sessions"), "Bruno class-session count");
check(amyHtml.includes("WS1, WS3, WS4, WS5"), "Amy summary names missing worksheets");
check(frames.includes("not published"), "frames note says videos are not published");
check(frames.includes("up to 12"), "preview cap is 12 examples");
check(frames.includes("16 preview images"), "16 stored previews per session");
check(!frames.includes("no longer in the data folder"), "frames note does not say videos were lost");
check(SP.logPreface("Helena").includes("not one of the two class sessions"), "7 April log is kept separate");

if (failed) {
  console.error(failed + " failed");
  process.exit(1);
}
console.log("ok");
