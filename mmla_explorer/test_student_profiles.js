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
check(model.people.filter((p) => p.frameSessions.length === 2).length === 6, "6 participants with both frame sessions");
const irma = model.people.find((p) => p.id === "Irma");
const zara = model.people.find((p) => p.id === "Zara");
check(irma.frameSessions.length === 2 && irma.frameSessions.every((s) => !s.duplicateOf.length), "Irma has two recordings and neither is a duplicate file");
check(zara.frameSessions.length === 1 && zara.frameSessions[0].id === "codap_21apr", "Zara’s published frames are session 1");
check(SP.summary("Irma").indexOf("same source file") === -1, "Irma’s profile does not call the sessions the same file");
check(SP.summary("Zara").indexOf("No extracted frames for") !== -1, "Zara’s profile names the session without frames");
check(model.people.filter((p) => p.pythonKind === "notebook").length === 14, "14 notebooks");
check(marco.pythonKind === "report", "Marco is a written report");
check(nadia.threshold === 285, "Nadia class-session threshold changes");
check(amy.categories === 4, "Amy has all four source categories");
check(model.codes.length === 12, "worksheet codes follow the archive order");
check(html.includes("Cohort findings"), "cohort findings");
check(html.includes("Participant comparison"), "comparison table");
check(html.includes("These findings describe the available records"), "evidence caveat");
check(html.includes("WS10") && html.includes("WS7"), "rule-based score contrast is named from the data");
check(html.includes("7.5 of 8") && html.includes("0.4 of 7"), "WS10 and WS7 means use each worksheet maximum");
check(html.includes("no verified join"), "cross-source limit is stated");
check(html.includes("Written report, table not stored"), "Marco depth table is not shown as a notebook zero");
check(!html.includes("Patterns across participants"), "no repeated pattern cards");
check(!html.includes("#/findings/worksheets"), "no worksheet-findings cross-link");
check(!html.includes("src-pill"), "no status pills");
check(!html.includes("4 of 4"), "cards do not repeat source-category counts");
check(!html.includes("15 of 15"), "coverage is not repeated as 15 of 15");
check((html.match(/class="student-card"/g) || []).length === 15, "15 profile cards");
check(!html.includes("8/12"), "file fractions are not the comparison");
check(!html.includes("no longer in the data folder"), "overview does not say videos were lost");
check(!/rushing|guessing|indecisive|high performer|mastered|careless|trial-and-error/i.test(html + amyHtml + marcoHtml), "no invented participant types");
check(!html.includes("–%"), "a missing rate is not shown as a blank percent");
check(marcoHtml.includes("Written report"), "Marco summary uses Written report");
check(marcoHtml.includes("not applicable"), "Marco notebook measures are not applicable");
check(SP.summary("Bruno").includes("Threshold changes 13") && SP.summary("Bruno").includes("Model submissions 10"), "Bruno class-session counts");
check(!SP.summary("Bruno").includes("<summary>Worksheet records"), "profile summary has no accordion stack");
check(amyHtml.includes("WS1, WS3, WS4, WS5"), "Amy summary names missing worksheets");
check(frames.includes("not published"), "frames note says videos are not published");
check(frames.includes("up to 12"), "preview cap is 12 examples");
check(frames.includes("16 preview images"), "16 stored previews per session");
check(frames.includes(SP.HF_FRAMES), "Hugging Face frame dataset link");
check(!frames.includes("no longer in the data folder"), "frames note does not say videos were lost");
check(SP.logPreface("Helena").includes("not one of the two class sessions"), "7 April log is kept separate");
check(SP.logPreface("Helena").includes("not evidence of difficulty"), "action counts are not read as difficulty");
const brunoChart = SP.sessionChart("Bruno", "codap_21apr");
check(brunoChart.includes("behaviour label") && brunoChart.includes("Share"), "frame chart uses labelled frames");
check(!/0%/.test(SP.sessionChart("Helena", "codap_28apr")), "a missing frame session is not a zero share");
const marcoNb = SP.notebookTable("Marco");
check(marcoNb.includes("Written report") && marcoNb.includes("not applicable"), "Marco notebook table stays a written report");
check(marcoNb.includes("Evidence status"), "notebook requirements table");
check(!/0 code cells/.test(marcoNb), "Marco cell counts are not shown as zero");
const brunoNb = SP.notebookTable("Bruno");
check(brunoNb.includes("Separate training and test data") && brunoNb.includes("Test fraction 0.2"), "Bruno split is read from the inspection");
check(SP.notebookTable("Amy").includes("Test fraction 0.3"), "Amy split is read from the inspection");

if (failed) {
  console.error(failed + " failed");
  process.exit(1);
}
console.log("ok");
