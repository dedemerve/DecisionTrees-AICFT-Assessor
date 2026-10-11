/* Checks screen-recording findings against the listed frames.
   Run from the repository root:
     node mmla_explorer/test_recording_findings.js
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
load("data/frames.js");
load("assets/recording_findings.js");

const core = context.CORE;
const frames = context.FRAMES;
const RF = context.RecordingFindings;
const pack = RF.analyze(core, frames);
let failed = 0;
function check(cond, msg) {
  if (!cond) {
    failed += 1;
    console.error("FAIL", msg);
  }
}

const nine = ["EXPLORE_DATA", "SELECT_TARGET", "BUILD_TREE", "TUNE_THRESHOLD", "EVALUATE_MODEL", "COMPARE_MODELS", "INTERPRET_RESULTS", "IDLE_THINKING", "OFF_TASK"];

core.students.forEach((student) => {
  core.sessions_meta.forEach((ss) => {
    const model = pack.byStudent[student][ss.id];
    const listed = frames.filter((f) => f.s === student && f.ss === ss.id);
    check(model.listed === listed.length, student + " " + ss.id + " listed frame count");
    const coded = listed.filter((f) => f.b);
    check(model.coded === coded.length, student + " " + ss.id + " coded frame count");
    const sum = Object.values(model.primary).reduce((a, n) => a + n, 0);
    check(sum === model.coded, student + " " + ss.id + " primary counts sum to coded frames");
    if (model.fileCounts) check(model.countsMatch, student + " " + ss.id + " matches the coding file");
    const runFrames = model.runs.reduce((a, r) => a + r.n, 0);
    check(runFrames === model.listed, student + " " + ss.id + " runs cover every listed frame");
    const runPrimary = {};
    model.runs.forEach((r) => { if (r.code) runPrimary[r.code] = (runPrimary[r.code] || 0) + r.n; });
    Object.keys(model.primary).forEach((k) => {
      check(runPrimary[k] === model.primary[k], student + " " + ss.id + " timeline matches primary " + k);
    });
    const fromB = {};
    const fromB2 = {};
    const fromCf = {};
    let b2Frames = 0;
    listed.forEach((f) => {
      if (f.b) fromB[f.b] = (fromB[f.b] || 0) + 1;
      if (f.b2) { b2Frames += 1; fromB2[f.b2] = (fromB2[f.b2] || 0) + 1; }
      if (f.b && f.cf) fromCf[f.cf] = (fromCf[f.cf] || 0) + 1;
    });
    Object.keys(fromB).forEach((k) => check(model.primary[k] === fromB[k], student + " " + ss.id + " primary uses b " + k));
    Object.keys(model.primary).forEach((k) => check(model.primary[k] === (fromB[k] || 0), student + " " + ss.id + " primary is not filled from b2 " + k));
    Object.keys(fromB2).forEach((k) => check(model.secondary[k] === fromB2[k], student + " " + ss.id + " secondary uses b2 " + k));
    check(model.secondaryFrameCount === b2Frames, student + " " + ss.id + " secondary frame denominator");
    Object.keys(fromCf).forEach((k) => check(model.confidence[k] === fromCf[k], student + " " + ss.id + " confidence uses cf " + k));
    if (model.runs.length && listed.length) {
      const ordered = listed.slice().sort((a, b) => a.t - b.t);
      check(model.runs[0].code === (ordered[0].b || ""), student + " " + ss.id + " sequence starts at the first frame");
    }
    if (model.coded) {
      const html = RF.page({ s: student, ss: ss.id });
      check(html.indexOf("Preview frames") === -1 && html.indexOf("preview images") === -1 && html.indexOf("<img") === -1, student + " " + ss.id + " findings omit the preview gallery");
      check(html.indexOf("#/explore/recordings?s=" + encodeURIComponent(student)) !== -1, student + " " + ss.id + " links to collected frames");
      const obs = html.indexOf("Observed behaviour");
      const order = html.indexOf("Order of coded frames");
      const extra = html.indexOf("Additional coding details");
      check(obs !== -1 && order > obs && extra > order, student + " " + ss.id + " section order");
    }
  });
});

check(pack.byStudent.Amy.codap_21apr.primary.EXPLORE_DATA === 140, "Amy session 1 explore-data count");
check(!pack.byStudent.Amy.codap_21apr.primary.SELECT_TARGET, "Select target is not counted as Amy's primary label");
check(pack.byStudent.Bruno.codap_21apr.secondary.SELECT_TARGET === 7, "Bruno session 1 stores select target as a second label");
check(pack.byStudent.Amy.codap_28apr.hasRecording === false, "Amy session 2 has no recording");
check(pack.byStudent.Irma.codap_21apr.duplicateOf.indexOf("codap_28apr") !== -1, "Irma sessions share one video file");

const amy = RF.page({ s: "Amy", ss: "codap_21apr" });
check(amy.indexOf("Explore data") !== -1 && amy.indexOf("var(--b1)") !== -1, "Amy session uses the explore-data colour");
check(amy.indexOf("140") !== -1 && amy.indexOf("370") !== -1, "Amy session shows the coded-frame denominator");
check(amy.indexOf("loading=\"lazy\"") === -1 && amy.indexOf("preview images") === -1, "Amy findings omit preview images");
check(amy.indexOf(".webm") === -1 && amy.indexOf(".mp4") === -1, "original videos are not linked");
check(amy.indexOf("#/explore/recordings?s=Amy") !== -1, "session links to collected frames");
check(amy.indexOf("not the nine frame labels") !== -1, "episodes stay a separate scheme");
check(amy.indexOf("Select target") !== -1, "Amy's second label select target is shown");

const amyMissing = RF.page({ s: "Amy", ss: "codap_28apr" });
check(amyMissing.indexOf("No screen recording frames are on record") !== -1, "Amy session 2 states that frames are missing");
check(amyMissing.indexOf("not shown as frame findings") !== -1, "Amy session 2 does not treat the episode table as frame findings");
check(amyMissing.indexOf("Observed behaviour") === -1, "Amy session 2 does not invent a behaviour summary");

const helena = RF.page({ s: "Helena", ss: "codap_21apr" });
check(helena.indexOf("STRUGGLE") !== -1 && helena.indexOf("not one of the nine primary codes") !== -1, "an unknown second label stays outside the nine codes");

const irma = RF.page({ s: "Irma", ss: "codap_28apr" });
check(irma.indexOf("same file") !== -1, "Irma's duplicate video is named");
check(irma.indexOf("no primary label") !== -1, "Irma's unlabelled frame is not folded into a behaviour");

const sheila = RF.page({ s: "Sheila", ss: "codap_21apr" });
check(sheila.indexOf("extraction summary") !== -1, "Sheila's two frame counts stay distinct");

const landing = RF.page({});
check(landing.indexOf("Choose a participant") !== -1, "landing asks for a participant");
nine.forEach((code) => {
  const label = {
    EXPLORE_DATA: "Explore data", SELECT_TARGET: "Select target", BUILD_TREE: "Build tree",
    TUNE_THRESHOLD: "Tune threshold", EVALUATE_MODEL: "Evaluate model", COMPARE_MODELS: "Compare models",
    INTERPRET_RESULTS: "Interpret results", IDLE_THINKING: "Idle / thinking", OFF_TASK: "Off task",
  }[code];
  check(landing.indexOf(label) === -1 || code === "EXPLORE_DATA", "landing does not invent a cohort summary for " + label);
});
check(core.students.every((s) => landing.indexOf(s) !== -1), "every pseudonym is listed");

const bruno = pack.byStudent.Bruno.codap_28apr;
check(bruno.primary.TUNE_THRESHOLD === 157, "Bruno session 2 primary tune threshold is 157");
check(bruno.primary.EXPLORE_DATA === 53, "Bruno session 2 primary explore data is 53");
check(bruno.secondary.EXPLORE_DATA === 157, "Bruno session 2 secondary explore data is 157");
check(bruno.secondary.TUNE_THRESHOLD === 3, "Bruno session 2 secondary tune threshold is 3");
check(bruno.secondaryFrameCount === 165, "Bruno session 2 has 165 frames with a second label");
check(bruno.confidence.HIGH === 46 && bruno.confidence.MEDIUM === 198 && bruno.confidence.LOW === 2, "Bruno session 2 confidence counts");
const brunoHtml = RF.page({ s: "Bruno", ss: "codap_28apr" });
check(brunoHtml.indexOf("165 of 246 listed frames store a second label") !== -1, "Bruno session 2 states the second-label denominator");
check(brunoHtml.indexOf("Preview frames") === -1, "Bruno session 2 has no preview gallery");
const brunoObs = brunoHtml.indexOf(">Observed behaviour<");
const brunoOrder = brunoHtml.indexOf("Order of coded frames");
const brunoExtra = brunoHtml.indexOf("Additional coding details");
check(brunoObs !== -1 && brunoOrder > brunoObs && brunoExtra > brunoOrder, "Bruno session 2 puts the timeline before additional coding");

const fixtureCore = {
  students: ["Ada"],
  sessions_meta: [{ id: "s1", date: "2026-01-01", label: "Fixture" }],
  sessions: { Ada: { s1: { manifest: { frames: 3 }, coding: { behaviors: { TUNE_THRESHOLD: 2, EXPLORE_DATA: 1 }, frames_coded: 3, source: "fixture" } } } },
  episodes: {},
};
const fixtureFrames = [
  { s: "Ada", ss: "s1", t: 1, b: "TUNE_THRESHOLD", b2: "EXPLORE_DATA", cf: "HIGH" },
  { s: "Ada", ss: "s1", t: 2, b: "TUNE_THRESHOLD", b2: "", cf: "MEDIUM" },
  { s: "Ada", ss: "s1", t: 3, b: "EXPLORE_DATA", b2: "EVALUATE_MODEL", cf: "LOW" },
];
const fixture = RF.analyze(fixtureCore, fixtureFrames).byStudent.Ada.s1;
check(fixture.primary.TUNE_THRESHOLD === 2 && fixture.primary.EXPLORE_DATA === 1, "fixture primary counts come from b");
check(fixture.secondary.EXPLORE_DATA === 1 && fixture.secondary.EVALUATE_MODEL === 1 && !fixture.secondary.TUNE_THRESHOLD, "fixture secondary counts come from b2 and are not the primary tune count");
check(fixture.secondaryFrameCount === 2, "fixture counts frames that carry any second label");
check(fixture.confidence.HIGH === 1 && fixture.confidence.MEDIUM === 1 && fixture.confidence.LOW === 1, "fixture confidence comes from cf");
check(fixture.runs.reduce((a, r) => a + r.n, 0) === 3, "fixture timeline covers listed frames");

console.log(failed ? failed + " failed" : "recording findings checks passed");
process.exit(failed ? 1 : 0);
