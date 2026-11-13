#!/usr/bin/env node
/* Runs every test_*.js in this directory as a child process and
   reports a summary. Exit code 0 only if all tests pass. */
"use strict";

const { spawnSync } = require("child_process");
const { readdirSync } = require("fs");
const path = require("path");

const dir = __dirname;
const files = readdirSync(dir)
  .filter((f) => f.startsWith("test_") && f.endsWith(".js") && f !== "run_tests.js")
  .sort();

let passed = 0;
let failed = 0;

for (const file of files) {
  const result = spawnSync("node", [path.join(dir, file)], { encoding: "utf8" });
  const ok = result.status === 0;
  const lastLine = (result.stdout || "").trim().split("\n").pop() || "";
  console.log(`${ok ? "PASS" : "FAIL"} ${file}: ${lastLine}`);
  if (ok) passed++;
  else failed++;
}

console.log(`\n${passed} passed, ${failed} failed`);
process.exit(failed > 0 ? 1 : 0);
