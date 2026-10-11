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
    if (model.runs.length && listed.length) {
      const ordered = listed.slice().sort((a, b) => a.t - b.t);
      check(model.runs[0].code === (ordered[0].b || ""), student + " " + ss.id + " sequence starts at the first frame");
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
check(amy.indexOf("loading=\"lazy\"") !== -1, "preview images are lazy loaded");
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

console.log(failed ? failed + " failed" : "recording findings checks passed");
process.exit(failed ? 1 : 0);
