/* Decision Tree Learning Archive. All content is generated from data/core.js and
   data/frames.js, which build_site_data.py creates from the project files. */
(function () {
  "use strict";

  const C = window.CORE;
  const F = window.FRAMES || [];
  const app = document.getElementById("app");
  const tip = document.getElementById("tip");
  if (!C) { app.innerHTML = '<p class="empty">Data files are missing. Run build_site_data.py first.</p>'; return; }

  // ------------------------------------------------------------------ helpers
  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v, d = 0) => (v == null || Number.isNaN(v)) ? "–" :
    Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const pct = (a, b, d = 0) => b ? num(100 * a / b, d) + "%" : "–";
  const bytes = (b) => b == null ? "–" : b >= 1e9 ? num(b / 1e9, 2) + " GB" : b >= 1e6 ? num(b / 1e6, 1) + " MB" : num(b / 1e3, 0) + " kB";
  const dur = (s) => {
    if (s == null) return "–";
    const m = Math.round(s / 60);
    return m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`;
  };
  const clock = (s) => {
    if (s == null) return "–";
    s = Math.round(s);
    const hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
    return (hh ? hh + ":" + String(mm).padStart(2, "0") : mm) + ":" + String(ss).padStart(2, "0");
  };
  const src = (p) => p ? `<div class="src">${h(p)}</div>` : "";
  const yesno = (b) => b === true ? '<span class="yes">✓ yes</span>' : b === false ? '<span class="no">✗ no</span>' : '<span class="na">–</span>';
  const result = (b) => b === true ? '<span class="yes">✓ Correct</span>' : b === false ? '<span class="no">✗ Not correct</span>' : '<span class="na">No verdict</span>';
  const mark = (b) => b === true ? '<span class="yes" title="correct">✓</span>' : b === false ? '<span class="no" title="not correct">✗</span>' : '<span class="na">–</span>';
  const sum = (arr) => arr.reduce((a, b) => a + (b || 0), 0);
  const tipAttr = (html) => ` data-tip="${h(html)}"`;
  const tech = (title, body) => body ? `<details class="tech"><summary>${h(title)}</summary><div class="tech-body">${body}</div></details>` : "";

  // ------------------------------------------------------------------ reference
  const STUDENTS = C.students;
  const SESS = C.sessions_meta;
  // Short session names used throughout. The date is shown once, in the session detail.
  const SESS_NAME = { codap_21apr: "CODAP session 1", codap_28apr: "CODAP session 2" };
  const SESS_DATE = { codap_21apr: "21 April 2026", codap_28apr: "28 April 2026" };

  // Titles come from the answer-key PDFs; dates from the file names of the scanned student PDFs.
  const WS_INFO = {
    WS1: { date: "24 March 2026", topic: "Name the parts of a nutrition table: object, feature, value and label." },
    WS3: { date: "24 March 2026", topic: "Apply a given rule (fat ≤ 8.0 g) to food cards and write each comparison." },
    WS4: { date: "24 March 2026", topic: "Search for the fat threshold that misclassifies the fewest of the 11 food cards." },
    WS5: { date: "24 March 2026", topic: "Choose another feature, try threshold values and record the resulting counts." },
    WS6: { date: "31 March 2026", topic: "Document a two-level decision tree built from the 11 food cards." },
    WS7: { date: "31 March 2026", topic: "Read the paths A, B and C of a tree and write them as if-then rules." },
    WS10: { date: "31 March 2026", topic: "Test thresholds between neighbouring energy values and find the one with the fewest errors." },
    WS11: { date: null, topic: "Feedback on the lesson series (survey items and open questions)." },
    WS13: { date: "21–28 April 2026", title: "Decision trees for classification activity", topic: "Choosing variables, reading a tree, TP/FP, sensitivity, misclassification rate and overfitting." },
    WS14: { date: "7 April 2026", title: "Diagnosis game with trees (Xeno)", topic: "Diagnose an alien disease with a tree in CODAP Arbor. Each student receives a randomly generated case set." },
    WS15: { date: "7 April 2026", title: "Titanic data in CODAP Arbor", topic: "Build a tree on a Titanic training sample, then check it on a test sample." },
  };
  const wsTitle = (w) => (WS_INFO[w.code] && WS_INFO[w.code].title) || (w.printed_title ? w.printed_title.replace(/^Worksheet \d+:\s*/, "") : w.code);
  const HOW_CHECKED = {
    deterministic: "Python rules compare each value with the 11 food cards. The language model only reads the handwriting.",
    llm_rubric: "Each answer is compared with the researcher's rubric and answer key. Python adds up the item scores.",
  };
  const howChecked = (w) => w.code === "WS14" ? "Numbers are checked against rules that always hold for this data (FP = 0, FN = 0, TP + TN = N). Open answers use the rubric."
    : w.code === "WS15" ? "Numbers are compared with the true Titanic values, allowing ±2% for reading off the screen. Open answers use the rubric."
      : HOW_CHECKED[w.pipeline];

  // Readable labels for worksheet fields.
  const TOKEN = {
    threshold_error_table: "", error_count_parsed: "", value_parsed: "", optimal_threshold: "Best threshold",
    titanic_vs1_egitim: "Sample 1 · training", titanic_vs1_test: "Sample 1 · test", titanic_vs1_interpretation: "Sample 1 · interpretation",
    titanic_vs2_egitim: "Sample 2 · training", titanic_vs2_test: "Sample 2 · test", titanic_vs2_interpretation: "Sample 2 · interpretation",
    genel_sorular: "General questions", trials: "Trial", trial_id: "trial number",
    tree_structure: "", depth_0: "Root", depth_1: "Level 1", depth_2: "Level 2", depth_3: "Level 3", leaf_nodes: "",
    left_child: "left branch", right_child: "right branch", left_left_child: "left-left branch",
    parsed_feature: "feature", left_operator: "left operator", right_operator: "right operator",
    left_threshold: "left threshold", right_threshold: "right threshold",
    left_threshold_value: "left threshold", right_threshold_value: "right threshold",
    left_leaf_recommended: "left leaf · recommended", left_leaf_not_recommended: "left leaf · not recommended",
    right_leaf_recommended: "right leaf · recommended", right_leaf_not_recommended: "right leaf · not recommended",
    leaf_recommended_count: "recommended", leaf_not_recommended_count: "not recommended",
    node_recommended_count: "recommended", node_not_recommended_count: "not recommended",
    student_error_count: "errors counted", student_mcr: "misclassification rate", final_decision_raw: "Final choice",
    rule_matching: "Rule matching", rule_1_box: "rule 1", rule_2_box: "rule 2", rule_3_box: "rule 3",
    path_label: "path", leaf_label: "leaf label", leaf_text: "leaf text", is_direct_leaf: "direct leaf", not_applicable: "not applicable",
    threshold_value_raw: "threshold as written", threshold_value_parsed: "threshold as a number",
    placement_description: "where the line was drawn", detection_method: "how foods were marked",
    circled_cards: "circled cards", written_foods: "written foods", foods_parsed: "foods read",
    response_raw: "answer", agrees_with_pia: "agrees with Pia",
    left_left_leaf: "left-left leaf", left_right_leaf: "left-right leaf", right_left_leaf: "right-left leaf", right_right_leaf: "right-right leaf",
    left_left_left_leaf: "left-left-left leaf", left_left_right_leaf: "left-left-right leaf",
  };
  const itemLabel = (id) => {
    let m;
    if ((m = /^WS\d+_B(\d+)([a-z]?)$/.exec(id))) return `Blank ${m[1]}${m[2]}`;
    if ((m = /^WS7_P1_box(\d)$/.exec(id))) return `Part 1 · box ${m[1]}`;
    if ((m = /^WS\d+_(\d+)$/.exec(id))) return `Item ${m[1]}`;
    if ((m = /^DTI_(\d+)$/.exec(id))) return `Question ${Number(m[1])}`;
    return null;
  };
  function rubricItem(code, id) {
    const w = C.worksheets.find((x) => x.code === code);
    const items = w && w.rubric_data && w.rubric_data.items;
    return items && items[id];
  }
  function rubricItemLabel(code, id, max) {
    const it = rubricItem(code, id);
    if (!it) return null;
    const exp = String(it.expected_answer || "").replace(/\s+/g, " ").trim();
    const n = it.printed_question;
    if (exp && exp.length <= max) return (n != null ? n + ". " : "") + exp;
    if (n != null) return "Question " + n;
    return null;
  }
  function questionLabel(code, raw) {
    const id = String(raw).replace(/^item_checks\./, "");
    return rubricItemLabel(code, id, 80) || itemLabel(id) || checkLabel(raw);
  }
  const fieldLabel = (path) => {
    const parts = path.match(/[^.\[\]]+|\[[^\]]+\]/g) || [path];
    const out = [];
    parts.forEach((p) => {
      if (p.startsWith("[")) { out.push(p.slice(1, -1)); return; }
      const il = itemLabel(p);
      if (il) { out.push(il); return; }
      if (p in TOKEN) { if (TOKEN[p]) out.push(TOKEN[p]); return; }
      out.push(p.replace(/_/g, " "));
    });
    return out.join(" · ").replace(/Trial · (\d+)/, "Trial $1") || path;
  };
  const checkLabel = (c) => {
    const k = c.replace(/^item_checks\./, "");
    const il = itemLabel(k);
    if (il) return il;
    if (/^trials\[(\d+)\]$/.test(k)) return "Trial " + k.match(/\d+/)[0];
    return k.replace(/^xeno_consistency_checks\./, "").replace(/^titanic_numeric_checks\./, "").replace(/_/g, " ");
  };
  // Response items that carry a different id from their check.
  const ITEM_ALIAS = { WS10: { optimal_threshold: "WS10_B8" } };

  const BEHAV = [
    ["EXPLORE_DATA", "Explore data", "Looking at data tables or graphs", "--b1"],
    ["SELECT_TARGET", "Select target", "Choosing the target (dependent) variable", "--b2"],
    ["BUILD_TREE", "Build tree", "Building the decision tree", "--b3"],
    ["TUNE_THRESHOLD", "Tune threshold", "Adjusting a split threshold", "--b4"],
    ["EVALUATE_MODEL", "Evaluate model", "Checking model performance", "--b5"],
    ["COMPARE_MODELS", "Compare models", "Comparing different models", "--b6"],
    ["INTERPRET_RESULTS", "Interpret results", "Interpreting model output or results", "--b7"],
    ["IDLE_THINKING", "Idle / thinking", "Working or thinking without visible interaction", "--b-idle"],
    ["OFF_TASK", "Off task", "Activity unrelated to the task", "--b-off"],
  ];
  const BEH = Object.fromEntries(BEHAV.map((b, i) => [b[0], { i, label: b[1], desc: b[2], color: `var(${b[3]})` }]));
  const behLabel = (k) => k ? (BEH[k] ? BEH[k].label : k.replace(/_/g, " ").toLowerCase()) : "Not coded";
  const behColor = (k) => k && BEH[k] ? BEH[k].color : "var(--rule-strong)";
  const SCREEN = { TREE: "Tree", GRAPH: "Graph", TABLE: "Table", MIXED: "Mixed", MENU: "Menu", CODAP: "CODAP window" };
  const PHASE = { SETUP: "Setup", BUILDING: "Building", TUNING: "Tuning", EVALUATING: "Evaluating", IDLE: "Idle" };
  const cap = (v, map) => v ? (map[v] || v.charAt(0) + v.slice(1).toLowerCase()) : "–";

  // On-screen observations recorded by the frame coder (yes/no flags).
  const EVIDENCE = {
    tree_has_nodes: "Tree has nodes", dependent_variable_set: "Target variable set", split_values_visible: "Split values visible",
    accuracy_visible: "Accuracy visible", confusion_matrix_visible: "Confusion matrix visible",
    systematic_variable_selection: "Variables tried systematically", threshold_reasoning: "Threshold being reasoned about",
    accuracy_interpretation: "Accuracy being interpreted", overfitting_awareness: "Overfitting addressed",
    train_test_distinction: "Training vs test distinguished", confusion_matrix_reading: "Confusion matrix being read",
    iterative_refinement: "Model being refined", technical_difficulty: "Technical difficulty",
    misconception_detected: "Possible misconception", aha_moment_candidate: "Possible insight moment", is_transition_frame: "Screen in transition",
  };

  // Meanings checked against scripts/dynamic_video_analytics.py.
  const TRIGGERS = {
    motion_threshold_exceeded: "The screen changed noticeably while speech was available.",
    motion_only_fallback: "The screen changed noticeably in a recording without usable speech.",
    speech_anchor_midpoint: "Someone was speaking. The frame shows the screen at that moment.",
    codap_static_gap_fill: "Nothing had been captured for a while on the CODAP screen, so a frame was taken anyway.",
    silent_screen_gap_fill: "Nothing had been captured for a while in a silent recording, so a frame was taken anyway.",
  };

  const LOG_DAYS = {
    "2026-04-21": { name: "CODAP session 1", date: "21 April 2026", ss: "codap_21apr" },
    "2026-04-28": { name: "CODAP session 2", date: "28 April 2026", ss: "codap_28apr" },
  };
  const ACTION = {
    emit_tree_data: "Submitted model results", drop_attribute: "Added a predictor to the tree",
    change_split_values: "Changed a split threshold", change_tree_type: "Changed the tree type",
    change_dataset: "Switched between training and test data", data_context_change: "Changed or selected data",
    set_dependent_variable: "Chose the target variable", set_focus_node: "Selected a node in the tree",
    refresh_tree: "Refreshed the tree", swap_focus_split: "Swapped a split", session_start: "Opened the session",
    codap_component_change: "Moved or resized a CODAP window", codap_document_change: "Changed the CODAP document",
    dragstart: "Started dragging a variable", dragend: "Finished dragging a variable",
    dragenter: "Dragged a variable over the tree", dragleave: "Dragged a variable away",
  };
  const MODEL_ACTIONS = ["emit_tree_data", "drop_attribute", "change_split_values", "change_tree_type", "change_dataset", "data_context_change"];
  const NB_USES = {
    "lizard_data.csv": "Loads the lizard data", DecisionTreeClassifier: "Builds a decision tree",
    train_test_split: "Splits training and test data", max_depth: "Tries different tree depths",
    get_dummies: "Converts categories to numbers", plot_tree: "Draws the tree",
  };

  // ------------------------------------------------------------------ derived
  const allSessions = [];
  STUDENTS.forEach((s) => SESS.forEach((ss) => allSessions.push(Object.assign({ student: s }, C.sessions[s][ss.id]))));
  const lengthOf = (r) => r.video_measured_seconds || (r.recording && r.recording.duration_seconds) || null;
  const lengthSrc = (r) => r.video_measured_seconds ? "measured from the video file" : r.recording ? "from the audio manifest" : "";
  const uniqueVideo = {};
  allSessions.forEach((r) => { if (r.video_sha256 && !uniqueVideo[r.video_sha256]) uniqueVideo[r.video_sha256] = r; });
  const uniqueVideoList = Object.values(uniqueVideo);
  const uniqueVideoSeconds = sum(uniqueVideoList.map(lengthOf));
  const videoFilesListed = allSessions.filter((r) => r.video_bytes).length;
  const logDays = C.logs.per_student;
  const logEvents = sum(Object.values(logDays).flatMap((d) => Object.values(d).map((x) => x.events)));
  const notebooksPresent = STUDENTS.filter((s) => C.notebooks[s] && C.notebooks[s].file).length;
  const schemaFields = sum(C.worksheets.map((w) => w.fields_in_schema));
  const responseRows = sum(STUDENTS.map((s) => sum(Object.values(C.ws[s]).map((r) => r.ocr ? r.ocr.responses.length : 0))));
  const wsWithAnswers = C.worksheets.filter((w) => STUDENTS.some((s) => C.ws[s][w.code].ocr)).length;
  const sessionIssues = (r) => {
    const out = [];
    if (r.same_video_file_as) out.push(`This video is the same file as the ${r.same_video_file_as.map((x) => SESS_NAME[x]).join(" and ")} video. Only one of them can be the real recording of this day.`);
    if (r.video_bytes && r.video_on_disk === false) out.push("The original video file is no longer in the data folder. The frames taken from it are still available.");
    if (r.frame_coverage != null && r.frame_coverage < 0.8) out.push(`Frames cover only the first ${num(r.frame_coverage * 100)}% of the recording.`);
    return out;
  };

  document.getElementById("navFooter").innerHTML = "Built " + h(C.built_at.slice(0, 4));

  // ------------------------------------------------------------------ tooltip, theme, menu
  document.addEventListener("mouseover", (e) => {
    const el = e.target.closest("[data-tip]");
    if (!el) { tip.style.display = "none"; return; }
    tip.innerHTML = el.getAttribute("data-tip");
    tip.style.display = "block";
  });
  document.addEventListener("mousemove", (e) => {
    if (tip.style.display !== "block") return;
    const w = tip.offsetWidth, hg = tip.offsetHeight;
    let x = e.clientX + 14, y = e.clientY + 14;
    if (x + w > window.innerWidth - 8) x = e.clientX - w - 14;
    if (y + hg > window.innerHeight - 8) y = e.clientY - hg - 14;
    tip.style.left = x + "px"; tip.style.top = y + "px";
  });
  document.addEventListener("scroll", () => { tip.style.display = "none"; }, true);

  const themeBtn = document.getElementById("themeBtn");
  const applyTheme = (t) => { if (t) document.documentElement.setAttribute("data-theme", t); else document.documentElement.removeAttribute("data-theme"); };
  try { applyTheme(localStorage.getItem("dta-theme")); } catch (e) { /* storage unavailable */ }
  themeBtn.addEventListener("click", () => {
    const cur = document.documentElement.getAttribute("data-theme") || (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    applyTheme(next);
    try { localStorage.setItem("dta-theme", next); } catch (e) { /* ignore */ }
  });
  const navDrawer = document.getElementById("navDrawer");
  const navOverlay = document.getElementById("navOverlay");
  const menuBtn = document.getElementById("menuBtn");
  const hdrSearch = document.getElementById("hdrSearch");
  const hdrList = document.getElementById("hdrStudents");
  if (hdrList) hdrList.innerHTML = STUDENTS.map((s) => `<option value="${h(s)}">`).join("");
  function goStudent(raw, exact) {
    const v = (raw || "").trim().toLowerCase();
    if (!v) return;
    const s = STUDENTS.find((x) => exact ? x.toLowerCase() === v : x.toLowerCase().startsWith(v));
    if (s) location.hash = `#/explore/student/${s}`;
  }
  if (hdrSearch) {
    document.getElementById("hdrSearchForm").addEventListener("submit", (e) => { e.preventDefault(); goStudent(hdrSearch.value, false); });
    hdrSearch.addEventListener("change", () => goStudent(hdrSearch.value, true));
  }
  function navItems() {
    return Array.from(navDrawer.querySelectorAll("a, summary")).filter((el) => {
      const group = el.closest("details");
      return !group || group.open || el.tagName === "SUMMARY";
    });
  }
  function openNav() {
    navDrawer.classList.add("open");
    navDrawer.inert = false;
    navDrawer.setAttribute("aria-hidden", "false");
    navOverlay.hidden = false;
    navOverlay.classList.add("open");
    menuBtn.setAttribute("aria-expanded", "true");
    document.body.classList.add("nav-open");
    const first = navDrawer.querySelector("a");
    if (first) first.focus();
  }
  function closeNav(restore) {
    const was = navDrawer.classList.contains("open");
    navDrawer.classList.remove("open");
    navDrawer.inert = true;
    navDrawer.setAttribute("aria-hidden", "true");
    navOverlay.classList.remove("open");
    navOverlay.hidden = true;
    menuBtn.setAttribute("aria-expanded", "false");
    document.body.classList.remove("nav-open");
    if (restore && was) menuBtn.focus();
  }
  menuBtn.addEventListener("click", () => { navDrawer.classList.contains("open") ? closeNav(true) : openNav(); });
  navOverlay.addEventListener("click", () => closeNav(true));
  document.addEventListener("keydown", (e) => {
    if (!navDrawer.classList.contains("open")) return;
    if (e.key === "Escape") { e.preventDefault(); closeNav(true); return; }
    if (e.key !== "Tab") return;
    const items = navItems();
    if (!items.length) return;
    const first = items[0], last = items[items.length - 1];
    if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
    else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
  });

  // Lightbox for frame images.
  const lb = document.createElement("div");
  lb.className = "lightbox"; lb.setAttribute("role", "dialog"); lb.setAttribute("aria-label", "Enlarged frame");
  lb.innerHTML = '<figure><img alt=""><figcaption></figcaption></figure><button type="button" class="btn">Close</button>';
  document.body.appendChild(lb);
  const closeLb = () => lb.classList.remove("open");
  lb.addEventListener("click", closeLb);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeLb(); });
  document.addEventListener("click", (e) => {
    const im = e.target.closest("[data-zoom]");
    if (!im) return;
    e.preventDefault(); e.stopPropagation();
    lb.querySelector("img").src = im.getAttribute("data-zoom");
    lb.querySelector("img").alt = im.getAttribute("data-cap") || "";
    lb.querySelector("figcaption").textContent = im.getAttribute("data-cap") || "";
    lb.classList.add("open");
  });

  // ------------------------------------------------------------------ components
  function table(head, rows, opts = {}) {
    const ths = head.map((c) => `<th class="${c.num ? "num" : ""}">${h(c.t)}</th>`).join("");
    const trs = rows.map((r) => `<tr${r.href ? ` class="click" data-href="${h(r.href)}"` : ""}${r.attrs || ""}>${r.cells.map((c, i) =>
      `<td class="${[head[i] && head[i].num ? "num" : "", head[i] && head[i].cls || ""].join(" ")}">${c}</td>`).join("")}</tr>`).join("");
    return `<div class="table-wrap"${opts.max ? ` style="max-height:${opts.max}px;overflow:auto"` : ""}><table><thead><tr>${ths}</tr></thead><tbody>${trs || `<tr><td colspan="${head.length}" class="na">No rows.</td></tr>`}</tbody></table></div>`;
  }
  const kv = (pairs) => `<dl class="kv">${pairs.filter(Boolean).map(([k, v]) => `<dt>${h(k)}</dt><dd>${v}</dd>`).join("")}</dl>`;
  const legend = (keys) => `<div class="legend">${keys.map((k) => `<span><i style="background:${behColor(k)}"></i>${h(behLabel(k))}</span>`).join("")}</div>`;
  function hbars(counts, label = (k) => k, tipFn) {
    const ent = Object.entries(counts).sort((a, b) => b[1] - a[1]);
    const max = Math.max(1, ...ent.map((e) => e[1]));
    return ent.map(([k, v]) => `<div class="hbar"${tipFn ? tipAttr(tipFn(k, v)) : ""}><span>${h(label(k))}</span><span class="track"><span class="fill" style="width:${100 * v / max}%"></span></span><span class="n">${num(v)}</span></div>`).join("");
  }
  function behKeys(counts) {
    const keys = BEHAV.map((b) => b[0]).filter((k) => counts[k]);
    Object.keys(counts).forEach((k) => { if (!BEH[k]) keys.push(k); });
    return keys;
  }
  function behaviorStack(counts) {
    const total = sum(Object.values(counts));
    if (!total) return "";
    return `<div class="stack" role="img" aria-label="Share of frames by behaviour">${behKeys(counts).map((k) =>
      `<div style="flex:${counts[k]};background:${behColor(k)}"${tipAttr(`<b>${h(behLabel(k))}</b><br>${num(counts[k])} frames · ${pct(counts[k], total, 1)}`)}></div>`).join("")}</div>`;
  }
  function behaviorTable(counts) {
    const total = sum(Object.values(counts));
    return table([{ t: "Observed behaviour" }, { t: "Meaning" }, { t: "Frames", num: 1 }, { t: "Share", num: 1 }],
      behKeys(counts).map((k) => ({ cells: [`<span class="sw" style="background:${behColor(k)}"></span>${h(behLabel(k))}`, h(BEH[k] ? BEH[k].desc : "Not in the nine-code list"), num(counts[k]), pct(counts[k], total, 1)] })));
  }
  const addCounts = (a, b) => { Object.entries(b || {}).forEach(([k, v]) => { a[k] = (a[k] || 0) + v; }); return a; };
  const evidenceText = (f) => f.ev && f.ev.length ? f.ev.map((k) => EVIDENCE[k] || k).join(" · ") : f.b ? "No flags set" : (TRIGGERS[f.tr] || "");
  const methodLink = (anchor, text = "How this was processed") => `<a class="more" href="#/methods${anchor ? "/" + anchor : ""}">${h(text)} →</a>`;

  // ------------------------------------------------------------------ 01 Overview
  const codedFrameCount = F.filter((f) => f.b).length;
  function pageOverview() {
    return `<div class="page wide home">
      <div class="hero">
        <div class="hero-copy">
          <p class="kicker">Pre-service teacher education · 2026</p>
          <h1><span class="hero-line">Documenting How Pre-Service Teachers</span> <span class="hero-line">Learn Decision Trees</span></h1>
          <p class="hero-lead">A research archive of worksheets, screen recordings, platform logs, and notebooks from a decision-tree unit with ${STUDENTS.length} pre-service teachers, shown only by pseudonym.</p>
          <div class="hero-actions">
            <a class="btn-primary" href="#/explore/worksheets">Explore learning activities</a>
            <a class="btn-secondary" href="#/docs">Browse research datasets</a>
          </div>
        </div>
        <figure class="hero-visual">
          <p class="hero-diagram-label">Worksheet 3 · given rule</p>
          <svg viewBox="0 0 560 220" role="img" aria-label="Schematic of the worksheet rule: if fat is at most 8 grams, the card is recommended; otherwise it is not.">
            <path d="M280 56 V104 H145 V148 M280 104 H415 V148" fill="none" stroke="#2458A6" stroke-width="1.5"/>
            <rect x="176" y="4" width="208" height="52" fill="#172B4D"/>
            <text x="280" y="36" text-anchor="middle" fill="#FFFFFF" font-size="18" font-weight="600">Fat ≤ 8.0 g</text>
            <text x="212" y="96" text-anchor="middle" fill="#2458A6" font-size="12" font-weight="600">yes</text>
            <text x="348" y="96" text-anchor="middle" fill="#586579" font-size="12" font-weight="600">no</text>
            <rect x="40" y="148" width="210" height="64" fill="#EDF3FB" stroke="#2458A6" stroke-width="1"/>
            <text x="145" y="176" text-anchor="middle" fill="#172B4D" font-size="15" font-weight="600">Recommended</text>
            <text x="145" y="196" text-anchor="middle" fill="#586579" font-size="12">fat is at most 8.0 g</text>
            <rect x="310" y="148" width="210" height="64" fill="#F6F8FB" stroke="#D8DEE8" stroke-width="1"/>
            <text x="415" y="176" text-anchor="middle" fill="#172B4D" font-size="15" font-weight="600">Not recommended</text>
            <text x="415" y="196" text-anchor="middle" fill="#586579" font-size="12">fat is above 8.0 g</text>
          </svg>
          <figcaption>The rule students apply to the 11 food cards in worksheet 3. This is a teaching example, not a finding from the recordings.</figcaption>
        </figure>
      </div>
      <div class="metric-row">
        <a class="metric" href="#/explore/students"><div class="v">${STUDENTS.length}</div><div class="l">Participants</div><div class="s">Pseudonyms only</div></a>
        <a class="metric" href="#/explore/worksheets"><div class="v">${C.worksheets.length}</div><div class="l">Worksheets</div><div class="s">${num(schemaFields)} response fields</div></a>
        <a class="metric" href="#/explore/frames"><div class="v">${num(F.length)}</div><div class="l">Frames listed</div><div class="s">${num(codedFrameCount)} coded for behaviour</div></a>
        <a class="metric" href="#/explore/logs"><div class="v">${num(logEvents)}</div><div class="l">Log events</div><div class="s">CODAP Arbor, 3 class days</div></a>
      </div>
      <div class="portal">
        <section class="portal-card">
          <h2>Learning activities</h2>
          <p>Paper worksheets from naming table parts through building and reading trees, plus the CODAP Arbor tasks. Each entry links to student responses and the blank PDF.</p>
          <div class="portal-links"><a href="#/explore/worksheets">Open the worksheet catalogue</a><a href="#/explore/students">Browse by student</a></div>
        </section>
        <div class="portal-side">
          <section class="portal-card">
            <h2>Research data</h2>
            <p>Screen-recording frames are published separately from the CODAP interaction logs. ${num(uniqueVideoList.length)} recordings and ${notebooksPresent} final notebooks sit alongside them.</p>
            <div class="portal-links"><a href="#/docs">Datasets and downloads</a><a href="#/explore/frames">Frame explorer</a></div>
          </section>
          <section class="portal-card">
            <h2>Methods</h2>
            <p>How answers were read, frames were selected, and codes were checked.</p>
            <div class="portal-links"><a href="#/methods">How the system works</a><a href="#/docs/limitations">Data notes</a></div>
          </section>
        </div>
      </div>
      <p class="small">Screen previews are cropped and softened so that on-screen text cannot be read. Listed frames are the rows in each session manifest; a frame is coded only when it has a behaviour label.</p>
    </div>`;
  }

  // ------------------------------------------------------------------ 02 Methods
  function pageMethods() {
    let rawEx = null;
    STUDENTS.some((s) => Object.entries(C.ws[s]).some(([code, r]) => {
      if (r.ocr && r.ocr.raw_diff && r.ocr.raw_diff.length) { rawEx = { s, code, d: r.ocr.raw_diff[0] }; return true; }
      return false;
    }));
    let checkEx = null;
    STUDENTS.some((s) => {
      const r = C.ws[s].WS10 && C.ws[s].WS10.ocr;
      const chk = r && r.checks.find((c) => c.check === "item_checks.WS10_B8");
      const resp = r && r.responses.find((x) => x.item === "optimal_threshold");
      if (chk && resp) { checkEx = { s, v: resp.value, chk }; return true; }
      return false;
    });
    const trigTotals = {};
    F.forEach((f) => { trigTotals[f.tr] = (trigTotals[f.tr] || 0) + 1; });
    const params = {};
    allSessions.forEach((r) => { if (r.manifest) Object.entries(r.manifest.parameters).forEach(([k, v]) => { if (v == null) return; params[k] = params[k] || {}; params[k][String(v)] = (params[k][String(v)] || 0) + 1; }); });
    const pv = (k) => Object.entries(params[k] || {}).map(([v, n]) => `${h(v)} <span class="small">(${n} sessions)</span>`).join(", ") || "–";
    const tables = { ep: 0, codes: 0 };
    STUDENTS.forEach((s) => Object.values(C.episodes[s] || {}).forEach((e) => { tables.ep += (e.episodes || []).length; tables.codes += e.code_rows || 0; }));
    const linkedFrames = F.filter((f) => f.gx).length;

    return `<div class="page">
      <p class="kicker">How the data were processed</p>
      <h1>From student work to analysable data</h1>
      <p class="lead">This page explains each step once. The pages under Explore link back here.</p>
      <nav class="jump"><a href="#/methods/idea">Core idea</a><a href="#/methods/worksheets">Worksheets</a><a href="#/methods/recordings">Screen recordings</a><a href="#/methods/logs">Platform logs</a><a href="#/methods/notebooks">Notebooks</a><a href="#/methods/review">Researcher review</a></nav>

      <h2 id="m-idea">The core idea: look up the rule, then answer</h2>
      <p>A language model that can read images can read handwriting or describe a screen. Left alone, it might also invent things. So the system never asks it an open question. For each answer it first <b>looks up</b> the matching rule written by the researcher. It then <b>places</b> that rule next to the student's work. Only then does the model <b>respond</b>, and only in a fixed format. This is called <b>retrieval-augmented generation</b>.</p>
      <div class="flow" aria-label="Processing steps">
        <div class="step"><div class="n">1</div><div class="h">Student work</div><div class="d">A scanned worksheet or a screen frame.</div></div>
        <div class="step"><div class="n">2</div><div class="h">Look up</div><div class="d">The rubric, answer key or codebook entry for this exact item.</div></div>
        <div class="step"><div class="n">3</div><div class="h">Combine</div><div class="d">Work, rule and output format go into one request.</div></div>
        <div class="step"><div class="n">4</div><div class="h">Answer</div><div class="d">Structured fields only. No new categories, no totals.</div></div>
        <div class="step"><div class="n">5</div><div class="h">Check</div><div class="d">Python tests values against reference data and adds up.</div></div>
        <div class="step"><div class="n">6</div><div class="h">Review</div><div class="d">The researcher reads the outputs and corrects them.</div></div>
      </div>
      <p class="small">The look-up is direct: each item has an ID, and the entry with that ID is loaded from the rubric files. It is not a fuzzy search through many documents.</p>

      <h2 id="m-worksheets">Worksheets</h2>
      <p>Students filled in ${C.worksheets.length} paper worksheets. Answers came as words, numbers, operators like ≤, tree drawings, sums and survey ticks. So there are two ways of checking.</p>
      ${table([{ t: "How answers were checked" }, { t: "Worksheets" }, { t: "Why" }], [
        { cells: ["<b>Rubric, with the language model</b>", "WS1, WS3, WS4, WS10, WS11, WS13, WS14, WS15", "Answers need interpretation, or several answers can be right. The model compares each answer with the rubric and answer key."] },
        { cells: ["<b>Python rules</b>", "WS5, WS6, WS7", "The right values can be computed from the 11 food cards. The model only reads the handwriting."] },
      ])}
      <ol class="stages">
        <li><div><h3>Scan and find the answer areas</h3><p>Each worksheet was scanned. The system knows where every answer box is. Tables in WS5, WS6 and WS10 were split into cells. In WS10 the column tells which blank a number belongs to.</p></div></li>
        <li><div><h3>Read text and handwriting</h3><p>Each answer area went to the model with its ID, the expected type of answer and any limits, for example that an operator must be ≤, &lt;, ≥ or &gt;. The raw reading was saved unchanged.</p></div></li>
        <li><div><h3>Clean up and check by hand</h3><p>Mechanical fixes were applied, such as writing <code>&lt;=</code> as ≤ or a decimal comma as a point. The researcher then reviewed every student's answers.${rawEx ? ` Example: in ${h(rawEx.s)}'s ${h(rawEx.code)}, the raw reading <code>${h(rawEx.d.raw)}</code> became <code>${h(rawEx.d.normalized)}</code>.` : ""}</p></div></li>
        <li><div><h3>Check and score</h3><p>For WS5 to WS7, Python checks operators, threshold ranges, card counts, opposite operator pairs and the misclassification rate. WS7 is checked against the tree the same student drew in WS6.</p>
          <p>For the other worksheets the model sees one rubric item at a time. It returns a score, the rubric criterion it used, a short reason and a verbatim quote from the student. Python adds up the scores.</p>
          <p>WS14 (Xeno) gives each student a different random case set, so numbers are checked against rules that always hold: FP = 0, FN = 0, TP + TN = N, accuracy = 100%. WS15 (Titanic) uses the same data for everyone, so numbers are compared with the true values, allowing ±2%.${checkEx ? ` Example: ${h(checkEx.s)} wrote <code>${h(checkEx.v)}</code> as the best threshold in WS10. Result: ${result(checkEx.chk.correct)}.` : ""}</p></div></li>
      </ol>

      <h2 id="m-recordings">Screen recordings</h2>
      <p>Students recorded their screens with a simple browser recorder built for this study during the two CODAP Arbor sessions. A session lasts more than an hour, so the system picks the moments that matter and describes them with a fixed list of behaviours.</p>
      <ol class="stages">
        <li><div><h3>Sound: who is speaking?</h3><p>The audio was transcribed with Whisper. Voices were grouped and labelled teacher, student or classmate using typical teacher phrases. Recordings without usable speech were marked as such, and no talk-based judgement was made for them.</p></div></li>
        <li><div><h3>Pick frames when something happens</h3><p>Instead of one image every few seconds, a frame is taken when the screen changes enough or when someone speaks. If nothing has been captured for a while, a frame is forced, so quiet stretches are still represented. Near-identical frames are removed.</p>
          ${tech("Settings recorded in the files", kv([
            ["Share of screen that must change", pv("motion_threshold_fraction")],
            ["Same, in silent recordings", pv("silent_motion_threshold")],
            ["Forced frame after a gap of (seconds)", pv("codap_gap_fill_seconds")],
            ["Forced frame after a speech gap of (seconds)", pv("speech_gap_bypass_seconds")],
          ]) + `<h4>Why frames were taken</h4>` + hbars(trigTotals, (k) => (TRIGGERS[k] || k).replace(/\.$/, ""), (k, v) => `<code>${h(k)}</code><br>${num(v)} frames`))}</div></li>
        <li><div><h3>Describe each frame with the codebook</h3><p>Each CODAP frame was sent to the model with the researcher's codebook. The codebook comes from earlier second-by-second human coding of recordings (Koklu et al., 2026). The model may only choose from nine behaviours. It also records what is visible, such as whether the tree has nodes or the accuracy is shown. Anything it cannot see is left empty.</p>
          ${table([{ t: "Behaviour" }, { t: "Meaning" }], BEHAV.map((b) => ({ cells: [`<span class="sw" style="background:var(${b[3]})"></span>${h(b[1])}`, h(b[2])] })))}
          <p>Each frame also gets a screen type (tree, graph, table, mixed or menu) and a phase (setup, building, tuning, evaluating or idle). When a frame fits two behaviours, building a tree comes first.</p></div></li>
        <li><div><h3>Link video and platform log</h3><p>Some actions are hard to see on screen, so the plan is to match log events to frames in time. In the 2026 files this matching is not recorded for individual frames. Instead, ${num(linkedFrames)} frames are linked to the researcher's written observation steps by order in time. These links are automatic, not checked by a person. <a href="#/docs/limitations">See data quality →</a></p></div></li>
      </ol>
      <p>The results form three tables per student and session: one summary row per session, ${num(tables.ep)} episodes (longer stretches of related activity), and ${num(tables.codes)} episode-by-code rows.</p>

      <h2 id="m-logs">Platform logs</h2>
      <p>CODAP Arbor writes a time-stamped line for every action. No language model is involved. Plain rules turn the lines into measures.</p>
      <dl class="terms">
        <dt>Model attempts</dt><dd>How often the student submitted a tree's results. Each attempt records accuracy and the counts of right and wrong decisions.</dd>
        <dt>Time to first attempt</dt><dd>Minutes from the student's first action to the first submitted model.</dd>
        <dt>Accuracy spread</dt><dd>How much accuracy varied between attempts (standard deviation).</dd>
        <dt>Changed one thing at a time</dt><dd>Share of steps between two attempts where only the predictor or only the threshold changed. Researchers call this VOTAT. A high share suggests controlled testing.</dd>
        <dt>Recovering from errors</dt><dd>Deleting a tree and rebuilding it with another predictor. ${C.logs.delete_events_present ? "" : "The 2026 logs contain no delete actions, so this is not measured."}</dd>
      </dl>

      <h2 id="m-notebooks">Python notebooks</h2>
      <p>For the final project students analysed lizard data in Google Colab. They wrote at least three research questions, built a tree for each, tried several depths, compared training and test errors and chose a final tree. The notebook files are read directly: which cells exist, which ran, whether the student went back to earlier code, and whether errors appeared. A second step records which analysis steps are present. Choosing one's own questions is linked to competency LO3.3.3. Trying settings such as tree depth is linked to LO3.3.2.</p>

      <h2 id="m-review">The researcher's role</h2>
      <p>The automation organises and pre-processes. It does not judge. Raw readings stay untouched. The researcher checked the outputs, corrected reading errors and decided what counts. Measures produced only by rules are kept apart from evidence a person has confirmed.</p>
    </div>`;
  }

  // ------------------------------------------------------------------ 03 Explore
  function exploreShell(active, body) {
    return `<p class="kicker">The data</p>${body}`;
  }
  function availableSummary(s) {
    const ws = C.worksheets.filter((w) => C.ws[s][w.code].ocr).length;
    const rec = SESS.filter((ss) => C.sessions[s][ss.id].manifest).length;
    const lg = Object.keys(logDays[s] || {}).length;
    const nb = C.notebooks[s] && C.notebooks[s].file ? "notebook" : C.notebooks[s] && C.notebooks[s].extraction ? "report instead of notebook" : "no notebook";
    return `${ws} of ${C.worksheets.length} worksheets · ${rec} of ${SESS.length} screen recordings · ${lg} log session${lg === 1 ? "" : "s"} · ${nb}`;
  }

  function pageStudents() {
    return `<div class="page wide">${exploreShell("students", `
      <h1>Students</h1>
      <p class="lead">Fifteen participants, each shown by a pseudonym. Open a student to see their worksheets, recordings, logs and notebook.</p>
      ${table([{ t: "Student" }, { t: "Available data" }, { t: "" }], STUDENTS.map((s) => ({ href: `#/explore/student/${s}`, cells: [`<b>${h(s)}</b>`, h(availableSummary(s)), `<a href="#/explore/student/${h(s)}">Explore →</a>`] })))}`)}</div>`;
  }

  // ---- student: worksheets
  function wsBlock(s, w) {
    const r = C.ws[s][w.code], o = r.ocr, st = r.stage || {};
    const info = WS_INFO[w.code] || {};
    const fixed = w.fixed_responses || {};
    let status = "no answers on file", body = `<p class="small">${h(info.topic || "")} ${h(howChecked(w))} ${methodLink("worksheets", "More")}</p>`;
    if (!o) {
      body += `<p class="empty">No extracted answers exist for this worksheet and student.</p>`;
    } else {
      const chkBy = Object.fromEntries(o.checks.map((c) => [c.check, c]));
      const alias = ITEM_ALIAS[w.code] || {};
      const used = new Set();
      const hasExpected = o.responses.some((x) => fixed[alias[x.item] || x.item] !== undefined);
      const rows = o.responses.map((x) => {
        const id = alias[x.item] || x.item;
        const c = chkBy["item_checks." + id] || chkBy[id];
        if (c) used.add(c.check);
        const v = x.value === null || x.value === "(bos)" ? '<span class="na">blank</span>' : `<span class="orig">${h(x.value)}</span>`;
        const pathLabel = fieldLabel(x.path);
        const blank = itemLabel(id);
        const rub = rubricItemLabel(w.code, id, 64);
        const label = rub && blank && (pathLabel === blank || pathLabel.startsWith(blank + " · ")) ? pathLabel.replace(blank, rub) : pathLabel;
        const cells = [h(label), v];
        if (hasExpected) cells.push(fixed[id] !== undefined ? `<span class="mono">${h(fixed[id])}</span>` : "");
        cells.push(c ? `<span${c.flag ? tipAttr(h(c.flag)) : ""}>${result(c.correct)}</span>` : "");
        return { cells };
      });
      const passed = o.checks.filter((c) => c.correct === true).length;
      status = o.checks.length ? `${passed} of ${o.checks.length} items correct` : `${o.responses.length} answers`;
      const head = [{ t: "Question" }, { t: "Student answer" }].concat(hasExpected ? [{ t: "Expected" }] : []).concat([{ t: "Result" }]);
      body += table(head, rows, { max: 560 });
      const rest = o.checks.filter((c) => !used.has(c.check));
      if (rest.length) body += `<h4>Further checks</h4>` + table([{ t: "Check" }, { t: "Result" }], rest.map((c) => ({ cells: [h(questionLabel(w.code, c.check)), `<span${tipAttr(h([c.flag, c.note, Object.entries(c.detail || {}).map(([k, v]) => `${k}: ${v}`).join(", ")].filter(Boolean).join(" · ")))}>${result(c.correct)}</span>`] })));
      body += `<p class="small">Answers are shown in the original Turkish. <a href="#/docs/glossary">Common Turkish words →</a></p>`;
      const notes = [["Page summary written by the model", o.snapshot], ["Reading notes", o.page_notes], ["Check summary", o.system_summary]].filter((n) => n[1] && n[1] !== "(bos)");
      let t = "";
      if (o.raw_diff.length) t += `<h4>Raw reading vs. cleaned value</h4>` + table([{ t: "Field" }, { t: "Raw" }, { t: "Cleaned" }], o.raw_diff.map((d) => ({ cells: [h(fieldLabel(d.path)), `<code>${h(d.raw)}</code>`, `<code>${h(d.normalized)}</code>`] })));
      if (notes.length) t += `<h4>Model-written notes (Turkish, not translated)</h4>` + notes.map((n) => `<p><b class="small">${h(n[0])}</b><br><span class="orig">${h(n[1])}</span></p>`).join("");
      if (o.checks.some((c) => c.flag)) t += `<h4>Check flags</h4>` + table([{ t: "Check" }, { t: "Flag" }], o.checks.filter((c) => c.flag).map((c) => ({ cells: [h(checkLabel(c.check)), `<code>${h(c.flag)}</code>`] })));
      if (o.other_validation.length) t += `<h4>Other validation values</h4>` + table([{ t: "Field" }, { t: "Value" }], o.other_validation.map((v) => ({ cells: [h(fieldLabel(v.path)), h(v.value)] })));
      if (st.scoring) t += `<h4>Stage score file</h4>` + kv([["Total", `${num(st.scoring.total, 2)} of ${num(st.scoring.max, 2)}`], st.scoring.all_zero_with_zero_confidence && ["Note", "All items 0 with confidence 0. This file does not match the answers above."]]) + src(st.scoring.source);
      t += `<h4>Source</h4>` + src(o.source) + (o.raw_source ? src(o.raw_source) : "");
      body += tech("Technical details", t);
    }
    return `<details class="ws" id="ws-${h(w.code)}"><summary><span class="code">${h(w.code)}</span><span class="t">${h(wsTitle(w))}</span><span class="st">${h(status)}</span></summary><div class="body">${body}</div></details>`;
  }

  // ---- student: recordings
  function strip(s, ssid, rec) {
    const fr = F.filter((f) => f.s === s && f.ss === ssid);
    if (!fr.length) return "";
    const total = Math.max(lengthOf(rec) || 0, fr[fr.length - 1].t) || 1;
    const coded = fr.some((f) => f.b);
    const ticks = fr.map((f) => {
      const t = `<b>${clock(f.t)}</b> · ${h(coded ? behLabel(f.b) : "Not coded")}<br>${h(evidenceText(f))}`;
      return `<a class="tick" href="#/explore/frames?s=${h(s)}&ss=${h(ssid)}&f=${h(f.id)}" style="left:${Math.min(99.6, 100 * f.t / total)}%;background:${coded ? behColor(f.b) : "var(--ink-2)"}"${tipAttr(t)} aria-label="Frame at ${clock(f.t)}"></a>`;
    }).join("");
    return `<div class="strip" role="img" aria-label="Frames over the session">${ticks}</div><div class="axis"><span>0:00</span><span>${clock(total / 2)}</span><span>${clock(total)}</span></div>`;
  }
  // 21 April only. The extraction summary, the pilot manifest, and the coded list
  // were checked as separate records: the pilot images are not a subset of the
  // directory counted by the summary. Other sessions are left unchanged.
  const SEPARATE_FRAME_COUNTS = new Set(["Sheila|codap_21apr", "Ulysses|codap_21apr", "Zara|codap_21apr"]);
  function frameCountNote(s, ssid, m, cd) {
    if (!SEPARATE_FRAME_COUNTS.has(s + "|" + ssid)) return "";
    const kept = m.summary && m.summary.total_frames_extracted;
    const listed = m.frames;
    const coded = cd && cd.frames_coded;
    if (typeof kept !== "number" || typeof listed !== "number" || kept === listed || coded !== listed) return "";
    return `<p class="small">The extraction summary reports ${num(kept)} kept frames. The pilot manifest and the coded frame list contain ${num(listed)}. These are separate extraction records.</p>`;
  }
  function sessionBlock(s, ss) {
    const r = C.sessions[s][ss.id];
    let out = `<section class="session"><h3>${h(SESS_NAME[ss.id])} <span class="small">${h(SESS_DATE[ss.id])}</span></h3>`;
    if (!r.manifest) return out + `<p class="empty">No screen recording from this session.</p></section>`;
    const cd = r.coding;
    sessionIssues(r).forEach((m) => { out += `<div class="warn">${h(m)} <a href="#/docs/limitations">Why this matters →</a></div>`; });
    out += kv([["Length", dur(lengthOf(r))], ["Frames listed", num(r.manifest.frames)], ["Coded for behaviour", cd ? num(cd.frames_coded) : "No"]]);
    out += strip(s, ss.id, r);
    if (cd) {
      out += legend(behKeys(cd.behaviors)) + behaviorStack(cd.behaviors) + behaviorTable(cd.behaviors);
    } else out += `<p class="small">Each tick is a selected frame. Hover to see why it was taken.</p>`;
    const thumbs = F.filter((f) => f.s === s && f.ss === ss.id && f.th);
    if (thumbs.length) {
      out += `<h4>Sample frames</h4><div class="thumbs">${thumbs.map((f) => `<figure><button class="thumb" type="button" data-zoom="thumbs/${h(f.th)}" data-cap="${h(`${s} · ${SESS_NAME[ss.id]} · ${clock(f.t)} · ${behLabel(f.b)}`)}"><img loading="lazy" src="thumbs/${h(f.th)}" alt="Screen at ${clock(f.t)}"></button><figcaption><span class="mono">${clock(f.t)}</span> · ${h(f.b ? behLabel(f.b) : "Not coded")}</figcaption></figure>`).join("")}</div>`;
    }
    out += `<p><a class="btn" href="#/explore/frames?s=${h(s)}&ss=${h(ss.id)}">See all ${num(r.manifest.frames)} frames</a> ${methodLink("recordings")}</p>`;
    // technical
    const m = r.manifest, sp = r.speech, ep = (C.episodes[s] || {})[ss.id];
    const SUM = { candidate_frames_considered: "Candidate frames considered", visual_duplicates_filtered: "Removed as near-duplicates", temporal_duplicates_filtered: "Removed as too close in time", non_task_screens_filtered: "Removed as unrelated screens", pruned_frames_removed: "Removed in a later clean-up", total_frames_extracted: "Frames kept" };
    let t = `<h4>How frames were selected</h4>` + kv(Object.entries(m.summary || {}).filter(([k]) => SUM[k]).map(([k, v]) => [SUM[k], num(v)])) +
      frameCountNote(s, ss.id, m, cd) +
      `<h4>Why each frame was taken</h4>` + hbars(m.triggers, (k) => (TRIGGERS[k] || k).replace(/\.$/, ""));
    if (cd) {
      t += `<div class="three compact"><div><h4>Screen</h4>${hbars(cd.screen_context, (k) => cap(k, SCREEN))}</div><div><h4>Phase</h4>${hbars(cd.deepen_phase, (k) => cap(k, PHASE))}</div><div><h4>Coder confidence</h4>${hbars(cd.confidence, (k) => cap(k, {}))}</div></div>`;
      t += kv([["Coding model", `<code>${h(cd.model || "–")}</code>`], ["Prompt", `<code>${h(cd.prompt_file || "–")}</code> ${h(cd.prompt_version || "")}`]]);
    }
    if (sp) t += `<h4>Speech</h4>` + kv([["Status", h(sp.status)], sp.role_counts && ["Speech segments by role", Object.entries(sp.role_counts).map(([k, v]) => `${h(k)} ${num(v)}`).join(", ")]]);
    if (ep && ep.episodes) t += `<h4>Episodes</h4>` + table([{ t: "Episode" }, { t: "Category" }, { t: "From" }, { t: "To" }, { t: "Assistance" }], ep.episodes.map((e) => ({ cells: [h(e.id), h(e.category), clock(e.start_ms / 1000), clock(e.end_ms / 1000), h(e.assistance)] })));
    t += `<h4>Files</h4>` + kv([["Video", r.video_bytes ? `${bytes(r.video_bytes)}, ${lengthSrc(r)}` : "–"]]) + src(r.video_path) + src(m.source) + (cd ? src(cd.source) : "") + (sp ? src(sp.source) : "") + (ep ? src(ep.episodes_source) : "");
    out += tech("Technical details", t);
    return out + `</section>`;
  }

  // ---- student: logs
  function minutesBetween(a, b) {
    const t = (x) => { const [hh, mm, ss] = x.split(":").map(Number); return hh * 3600 + mm * 60 + ss; };
    return (t(b) - t(a)) / 60;
  }
  function accuracyChart(emits, start) {
    const pts = emits.map((e, i) => ({ i, a: e.accuracy })).filter((p) => typeof p.a === "number");
    if (!pts.length) return "";
    const W = 640, H = 170, L = 38, R = 10, T = 10, B = 26;
    const x = (i) => L + (emits.length === 1 ? (W - L - R) / 2 : (i * (W - L - R)) / (emits.length - 1));
    const y = (a) => T + (1 - a) * (H - T - B);
    const grid = [0, 0.25, 0.5, 0.75, 1].map((g) => `<line x1="${L}" x2="${W - R}" y1="${y(g)}" y2="${y(g)}" stroke="var(--rule)"/><text x="${L - 6}" y="${y(g) + 4}" text-anchor="end" font-size="10" fill="var(--muted)">${g * 100}%</text>`).join("");
    const line = pts.map((p, k) => `${k ? "L" : "M"}${x(p.i).toFixed(1)},${y(p.a).toFixed(1)}`).join("");
    const dots = pts.map((p) => {
      const e = emits[p.i];
      return `<circle cx="${x(p.i)}" cy="${y(p.a)}" r="4.5" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"${tipAttr(`<b>Attempt ${p.i + 1}</b>, ${num(minutesBetween(start, e.t), 0)} min after starting<br>Accuracy ${num(e.accuracy * 100, 1)}%<br>Tree depth ${h(e.depth)}`)}><title>Attempt ${p.i + 1}: ${num(e.accuracy * 100, 1)}%</title></circle>`;
    }).join("");
    return `<svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;display:block;background:var(--surface);border:1px solid var(--rule)" role="img" aria-label="Accuracy of each model attempt">${grid}<path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2"/>${dots}<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" font-size="10.5" fill="var(--muted)">attempt 1 to ${emits.length} →</text></svg>`;
  }
  function logBlock(s) {
    const days = logDays[s] || {};
    if (!Object.keys(days).length) return `<p class="empty">No platform log for this student.</p>`;
    return Object.entries(LOG_DAYS).map(([d, meta]) => {
      const v = days[d];
      let out = `<section class="session"><h3>${h(meta.name)} <span class="small">${h(meta.date)}</span></h3>`;
      if (!v) return out + `<p class="empty">No actions recorded in this session.</p></section>`;
      const start = v.first_event.slice(11);
      const vt = meta.ss && C.sessions[s][meta.ss].votat;
      out += kv([
        ["Model attempts", num(v.emit_count)],
        ["First attempt", v.minutes_to_first_emit == null ? "–" : `${num(v.minutes_to_first_emit, 0)} min after starting`],
        ["Accuracy of last attempt", v.last_emit_accuracy == null ? "–" : num(v.last_emit_accuracy * 100, 1) + "%"],
        ["Predictors tried", v.unique_attributes_dropped.length ? v.unique_attributes_dropped.map(h).join(", ") : "–"],
        ["Threshold changes", num(v.modelling_actions.change_split_values)],
        vt && ["Changed one thing at a time", `${num(vt.votat_rate * 100, 0)}% of ${vt.intervals} steps between attempts`],
      ]);
      if (v.emits.length) out += `<h4>Accuracy of each attempt</h4>` + accuracyChart(v.emits, start);
      out += `<h4>What the student did</h4>` + table([{ t: "Action" }, { t: "Times", num: 1 }], MODEL_ACTIONS.filter((a) => v.modelling_actions[a]).map((a) => ({ cells: [h(ACTION[a]), num(v.modelling_actions[a])] })));
      let t = `<h4>All recorded actions</h4>` + table([{ t: "Action" }, { t: "Event code" }, { t: "Count", num: 1 }], Object.entries(v.actions).sort((a, b) => b[1] - a[1]).map(([k, n]) => ({ cells: [h(ACTION[k] || k), `<code>${h(k)}</code>`, num(n)] })));
      t += kv([["Total actions", num(v.events)], ["Session span", `${num(v.span_minutes, 0)} min (UTC ${h(start)} to ${h(v.last_event.slice(11))})`], ["Accuracy spread (SD)", v.accuracy_sd == null ? "–" : num(v.accuracy_sd, 3)], ["Predictor placements", num(v.predictor_drops)]]);
      if (v.emits.length) t += `<h4>Attempts</h4>` + table([{ t: "#", num: 1 }, { t: "Minutes in", num: 1 }, { t: "Target" }, { t: "Depth", num: 1 }, { t: "Accuracy", num: 1 }, { t: "TP", num: 1 }, { t: "TN", num: 1 }, { t: "FP", num: 1 }, { t: "FN", num: 1 }],
        v.emits.map((e, i) => ({ cells: [i + 1, num(minutesBetween(start, e.t), 1), h(e.target), h(e.depth), e.accuracy == null ? "–" : num(e.accuracy * 100, 1) + "%", h(e.TP), h(e.TN), h(e.FP), h(e.FN)] })));
      if (vt && vt.interval_rows.length) t += `<h4>Steps between attempts (VOTAT)</h4>` + table([{ t: "Step", num: 1 }, { t: "Predictor changes", num: 1 }, { t: "Threshold changes", num: 1 }, { t: "One thing at a time" }], vt.interval_rows.map((x, i) => ({ cells: [i + 1, num(x.predictor_changes), num(x.threshold_changes), yesno(x.is_votat)] }))) + src(vt.source);
      t += src(C.logs.source);
      return out + tech("Technical event details", t) + `</section>`;
    }).join("") + `<p>${methodLink("logs", "What these measures mean")}</p>`;
  }

  // ---- student: notebook
  function notebookBlock(s) {
    const n = C.notebooks[s] || {};
    if (!n.file && !n.extraction) return `<p class="empty">No final project file for this student.</p>`;
    const f = n.file, e = n.extraction;
    let out = "";
    if (e && e.data_source_note && !f) out += `<div class="warn">No notebook was submitted. The details below were taken from a submitted report.</div>`;
    out += kv([
      e && ["Target variables", e.targets.map((t) => `<code>${h(t)}</code>`).join(" ")],
      e && ["Research questions written out", `${e.questions_written} of ${e.targets.length}`],
      e && ["Decision tree models", num(e.models)],
      f && ["Errors in the outputs", f.cells_with_error_output ? `Yes, in ${f.cells_with_error_output} cell${f.cells_with_error_output > 1 ? "s" : ""}` : "None"],
      f && ["Revisiting earlier code", f.order_reversals ? `${f.order_reversals} time${f.order_reversals > 1 ? "s" : ""}` : "Never"],
    ]);
    if (f) out += `<h4>Analysis steps found</h4><ul class="checks">${Object.entries(f.uses).map(([k, v]) => `<li class="${v ? "on" : "off"}">${v ? "✓" : "✗"} ${h(NB_USES[k] || k)}</li>`).join("")}</ul>`;
    if (e && e.experiments.length) out += `<h4>Trees built</h4>` + table([{ t: "Target" }, { t: "Features used" }, { t: "Depths tried" }, { t: "Tree drawn" }], e.experiments.map((x) => ({ cells: [`<code>${h(x.target)}</code>`, `<span class="small">${h((x.features || []).join(", "))}</span>`, x.depth_min == null ? "–" : `${x.depth_min} to ${x.depth_max}`, yesno(x.checks.tree_visualized)] })));
    if (n.scoring) out += `<h4>Rubric points</h4>` + table([{ t: "Section" }, { t: "Points", num: 1 }, { t: "Possible", num: 1 }], Object.entries(n.scoring.sections).map(([k, v]) => ({ cells: [h(k), num(v.awarded, 1), num(v.possible, 1)] })));
    let t = "";
    if (f) {
      const ec = f.execution_counts, max = Math.max(1, ...ec.filter((x) => x != null)), W = Math.max(240, ec.length * 22), H = 120;
      t += kv([["Cells", `${num(f.cells)} (${num(f.code_cells)} code, ${num(f.markdown_cells)} text)`], ["Code cells run", `${num(f.executed_code_cells)} of ${num(f.code_cells)}`], ["Empty code cells", num(f.empty_code_cells)], ["Highest run counter", num(f.max_execution_count)], ["Cells with a picture output", num(f.cells_with_image_output)]]);
      t += `<h4>Run counter per code cell</h4><p class="small">A steadily rising line means cells ran in order. A drop means the student went back to earlier code.</p><svg viewBox="0 0 ${W} ${H}" width="100%" style="max-width:${W}px;display:block;background:var(--surface);border:1px solid var(--rule)" role="img" aria-label="Run counter per code cell">${ec.map((v, i) => {
        const x = 8 + i * 22;
        if (v == null) return `<rect x="${x}" y="${H - 22}" width="14" height="2" fill="var(--rule-strong)"${tipAttr(`Code cell ${i + 1}: never run`)}/>`;
        const bh = Math.max(2, (v / max) * (H - 30));
        return `<rect x="${x}" y="${H - 20 - bh}" width="14" height="${bh}" rx="2" fill="var(--green)"${tipAttr(`Code cell ${i + 1}: run counter ${v}`)}/>`;
      }).join("")}<line x1="0" x2="${W}" y1="${H - 20}" y2="${H - 20}" stroke="var(--rule-strong)"/></svg>` + src(f.source);
    }
    if (e) t += (e.data_source_note ? `<p class="orig">${h(e.data_source_note)}</p>` : "") + src(e.source);
    if (n.scoring) t += kv([["Scored by", `<code>${h(n.scoring.scored_by)}</code>`], ["Rubric version", `<code>${h(n.scoring.rubric_version)}</code>`]]) + src(n.scoring.source);
    return out + tech("Technical details", t) + `<p>${methodLink("notebooks")}</p>`;
  }

  function pageStudent(s, tab) {
    if (!STUDENTS.includes(s)) return `<div class="page">${exploreShell("students", `<h1>Not found</h1><p>No student with the pseudonym “${h(s)}”.</p>`)}</div>`;
    tab = tab || "worksheets";
    const tabs = [["worksheets", "Worksheets"], ["recordings", "Screen recordings"], ["logs", "Platform logs"], ["notebook", "Notebook"]];
    const i = STUDENTS.indexOf(s);
    let body = "";
    if (tab === "worksheets") body = C.worksheets.map((w) => wsBlock(s, w)).join("");
    if (tab === "recordings") body = SESS.map((ss) => sessionBlock(s, ss)).join("");
    if (tab === "logs") body = logBlock(s);
    if (tab === "notebook") body = notebookBlock(s);
    const prev = i > 0 ? `<a href="#/explore/student/${h(STUDENTS[i - 1])}/${tab}">← ${h(STUDENTS[i - 1])}</a>` : "";
    const next = i < STUDENTS.length - 1 ? `<a href="#/explore/student/${h(STUDENTS[i + 1])}/${tab}">${h(STUDENTS[i + 1])} →</a>` : "";
    return `<div class="page">${exploreShell("students", `
      <h1>${h(s)}</h1>
      <p class="small">Pseudonym · ${h(availableSummary(s))}</p>
      <nav class="tabs sub">${tabs.map(([k, l]) => `<a href="#/explore/student/${h(s)}/${k}" class="${k === tab ? "active" : ""}">${l}</a>`).join("")}</nav>
      ${body}
      <p class="small pn">${prev}${prev && next ? " · " : ""}${next}</p>`)}</div>`;
  }

  // ---- cohort views
  const WS_GROUPS = [
    { label: "Conceptual foundations", codes: ["WS1"] },
    { label: "Manual classification", codes: ["WS3", "WS4", "WS5"] },
    { label: "Building decision trees", codes: ["WS6", "WS7", "WS10"] },
    { label: "CODAP Arbor sessions", codes: ["WS13", "WS14", "WS15"] },
    { label: "Feedback survey", codes: ["WS11"] },
  ];
  function pageWorksheets() {
    const wsMap = Object.fromEntries(C.worksheets.map((w) => [w.code, w]));
    const allCards = C.worksheets.map((w) => {
      const info = WS_INFO[w.code] || {};
      const have = STUDENTS.filter((s) => C.ws[s][w.code].ocr).length;
      const dl = (C.downloads && C.downloads.worksheets || []).find((d) => d.code === w.code);
      const links = [`<a href="#/explore/worksheet/${h(w.code)}">Student responses</a>`];
      if (dl) links.push(`<a href="${h(dl.file)}" download>Download PDF</a>`);
      const group = (WS_GROUPS.find((g) => g.codes.includes(w.code)) || {}).label || "";
      return `<article class="ws-card" data-code="${h(w.code)}" data-group="${h(group)}" data-title="${h(wsTitle(w)).toLowerCase()} ${h((info.topic || "")).toLowerCase()} ${h(group).toLowerCase()}">
        <div class="ws-card-code">${h(w.code)}</div>
        <h3 class="ws-card-title">${h(wsTitle(w))}</h3>
        ${info.date ? `<div class="ws-card-date">${h(info.date)}</div>` : ""}
        <p class="ws-card-desc">${h(info.topic || "")}</p>
        <div class="ws-card-actions">${links.join("")}<span class="small">${have} of ${STUDENTS.length} with answers</span></div>
      </article>`;
    });
    const chips = `<div class="ws-filters" role="group" aria-label="Filter by worksheet purpose">${["All"].concat(WS_GROUPS.map((g) => g.label)).map((label, i) =>
      `<button type="button" class="chip${i === 0 ? " on" : ""}" data-group="${i === 0 ? "" : h(label)}" aria-pressed="${i === 0 ? "true" : "false"}">${h(label)}</button>`).join("")}</div>`;
    const groups = WS_GROUPS.map((g) => {
      const cards = g.codes.map((code) => {
        const idx = C.worksheets.findIndex((w) => w.code === code);
        return idx >= 0 ? allCards[idx] : "";
      }).join("");
      return `<section class="ws-group" data-codes="${h(g.codes.join(","))}"><h2 class="ws-group-label">${h(g.label)}</h2><div class="ws-group-cards">${cards}</div></section>`;
    }).join("");
    return `<div class="page wide">${exploreShell("worksheets", `
      <h1>Worksheets</h1>
      <p class="lead">${C.worksheets.length} paper worksheets from the unit. Search by title or topic, or filter by purpose. Each card links to student responses and the blank PDF.</p>
      <div class="ws-search-bar">
        <input type="search" id="wsSearch" placeholder="Search worksheets…" aria-label="Search worksheets">
        <span class="ws-count" id="wsCount">${C.worksheets.length} worksheets</span>
      </div>
      ${chips}
      <div id="wsGroups">${groups}</div>
      <p class="empty" id="wsEmpty" hidden>No worksheets match. Clear the search or choose All.</p>
      <p>${methodLink("worksheets")}</p>`)}</div>`;
  }

  function pageWorksheet(code) {
    const w = C.worksheets.find((x) => x.code === code);
    if (!w) return pageWorksheets();
    const info = WS_INFO[code] || {};
    const have = STUDENTS.filter((s) => C.ws[s][code].ocr);
    const cols = [];
    have.forEach((s) => C.ws[s][code].ocr.checks.forEach((c) => { if (!cols.includes(c.check)) cols.push(c.check); }));

    // Answer key + scoring criteria section
    let answerKey = "";
    if (w.rubric_data && w.rubric_data.items) {
      const items = Object.entries(w.rubric_data.items);
      const akLink = w.answer_key_url
        ? `<p><a href="${h(w.answer_key_url)}" download>Download answer key PDF</a></p>`
        : "";
      answerKey = `<h2 id="answer-key">Answer key and scoring criteria</h2>
        ${akLink}
        <p class="small">Expected answers and scoring rules from the researcher's rubric, in worksheet order. The expected text is shown as written in the rubric.</p>
        ${table([{ t: "Item" }, { t: "Expected answer" }, { t: "Scoring rules" }],
          items.map(([id, item]) => {
            const q = rubricItemLabel(code, id, 72) || (item.printed_question != null ? `Question ${item.printed_question}` : id.replace(/^[A-Z0-9]+_/, ""));
            const expected = item.expected_answer || "";
            const rules = Object.entries(item.scoring_rules || {}).map(([score, rule]) => {
              const cond = typeof rule === "string" ? rule : (rule.condition || "");
              return `<li><b>${h(score)}</b> — ${h(cond)}</li>`;
            }).join("");
            return { cells: [`<b>${h(q)}</b>`, h(expected), `<ul class="scoring-rules">${rules}</ul>`] };
          }))}`;
    } else if (w.answer_key_url) {
      answerKey = `<h2 id="answer-key">Answer key</h2><p><a href="${h(w.answer_key_url)}" download>Download answer key PDF</a></p>`;
    }

    // Student results matrix
    let matrix = "";
    if (cols.length) {
      const alias = ITEM_ALIAS[code] || {};
      const body = have.map((s) => {
        const o = C.ws[s][code].ocr;
        const by = Object.fromEntries(o.checks.map((c) => [c.check, c]));
        const correct = o.checks.filter((c) => c.correct === true).length;
        const total = o.checks.length;
        return `<tr class="click" data-href="#/explore/student/${h(s)}/worksheets"><td><a href="#/explore/student/${h(s)}/worksheets">${h(s)}</a></td>${cols.map((c) => {
          const k = by[c];
          if (!k) return `<td class="cell na">·</td>`;
          const item = c.replace(/^item_checks\./, "");
          const label = rubricItemLabel(code, item, 28) || checkLabel(c);
          const vals = o.responses.filter((x) => (alias[x.item] || x.item) === item || x.item === c).map((x) => x.value).slice(0, 3);
          return `<td class="cell"${tipAttr(`<b>${h(s)} · ${h(label)}</b><br>${k.correct === true ? "Correct" : k.correct === false ? "Not correct" : "No verdict"}${vals.length ? "<br>Answer: " + vals.map(h).join(" · ") : ""}`)}>${mark(k.correct)}</td>`;
        }).join("")}<td class="num">${correct}/${total}</td></tr>`;
      }).join("");
      matrix = `<h2 id="responses">Student responses</h2><p>Each column is one check. The score is items marked correct out of checks recorded for that student. A dot means that check was not recorded. Hover a cell for the answer. Click a row to open that student.</p><div class="table-wrap"><table><tr><th>Student</th>${cols.map((c) => `<th class="vert" title="${h(questionLabel(code, c))}">${h(rubricItemLabel(code, c.replace(/^item_checks\./, ""), 28) || checkLabel(c))}</th>`).join("")}<th class="num">Items correct</th></tr>${body}</table></div>`;
    }

    // Processing workflow section
    const isDeterministic = w.pipeline === "deterministic";
    const workflow = `<h2 id="processing">How responses were processed</h2>
      ${isDeterministic
        ? `<p>This worksheet uses a <b>deterministic pipeline</b>. The language model reads and extracts the handwritten values. Python then checks each value against a fixed rule derived from the 11 food cards. There is no judgement call: a value either matches or it does not.</p>`
        : `<p>This worksheet uses a <b>rubric-based pipeline</b>. The language model reads the handwriting and compares each answer against the researcher's rubric. Python aggregates the per-item scores. Partial credit (0.5) is possible where the rubric defines it.</p>`}
      <p>${methodLink("worksheets", "Full description of the worksheet processing pipeline")}</p>`;

    return `<div class="page wide">${exploreShell("worksheets", `
      <p class="small"><a href="#/explore/worksheets">← All worksheets</a></p>
      <h1>${h(code)} · ${h(wsTitle(w))}</h1>
      <p class="lead">${h(info.topic || "")}</p>
      <nav class="jump" aria-label="On this page">
        <a href="#about">About</a>
        ${answerKey ? `<a href="#answer-key">Answer key</a>` : ""}
        ${matrix ? `<a href="#responses">Student responses</a>` : ""}
        <a href="#processing">Processing</a>
      </nav>
      <h2 id="about">About this worksheet</h2>
      ${kv([["Used in class", h(info.date || "No scanned student file")], ["How answers were checked", `${h(howChecked(w))}`], ["Students with extracted answers", `${have.length} of ${STUDENTS.length}`]])}
      <p>${methodLink("worksheets", "How worksheet processing works")}</p>
      ${!have.length ? `<div class="warn">No student answers were extracted for this worksheet. <a href="#/docs/limitations">See data quality →</a></div>` : ""}
      ${answerKey}
      ${matrix}
      ${workflow}
      ${tech("Technical details", kv([["Internal key", `<code>${h(w.key)}</code>`], ["Response fields defined", num(w.fields_in_schema)]]) + src(w.schema) + src(w.rubric) + src(w.answer_key))}`)}</div>`;
  }
  function pageRecordings() {
    const rows = [];
    STUDENTS.forEach((s) => SESS.forEach((ss) => {
      const r = C.sessions[s][ss.id];
      if (!r.manifest) return;
      rows.push({ href: `#/explore/student/${s}/recordings`, cells: [`<a href="#/explore/student/${h(s)}/recordings">${h(s)}</a>`, h(SESS_NAME[ss.id]), dur(lengthOf(r)), num(r.manifest.frames), r.coding ? `<div class="mix">${behaviorStack(r.coding.behaviors)}</div>` : '<span class="na">not coded</span>'] });
    }));
    const tot = {};
    allSessions.forEach((r) => { if (r.coding) addCounts(tot, r.coding.behaviors); });
    return `<div class="page wide">${exploreShell("recordings", `
      <h1>Screen recordings</h1>
      <p class="lead">One row per student and session. The frame count is the manifest list for that session. ${num(codedFrameCount)} of ${num(F.length)} listed frames have a behaviour code. Where an extraction summary reports a different total, the session page says so.</p>
      ${legend(BEHAV.map((b) => b[0]))}
      ${table([{ t: "Student" }, { t: "Session" }, { t: "Length" }, { t: "Frames", num: 1 }, { t: "Behaviour mix" }], rows)}
      <h2>All coded frames together</h2>
      <p>${num(sum(Object.values(tot)))} frames from the two CODAP sessions.</p>
      ${behaviorStack(tot)}${behaviorTable(tot)}
      <p>${methodLink("recordings")}</p>`)}</div>`;
  }

  // ---- frames
  const fState = { s: "", ss: "", b: "", prev: false, page: 0, sel: null };
  const filteredFrames = () => F.filter((f) => (!fState.s || f.s === fState.s) && (!fState.ss || f.ss === fState.ss) &&
    (!fState.b || (fState.b === "__none" ? !f.b : f.b === fState.b)) && (!fState.prev || f.th));
  function pageFrames(q) {
    Object.assign(fState, { s: q.s || "", ss: q.ss || "", b: q.b || "", prev: q.p === "1", page: 0, sel: q.f || null });
    const opt = (vals, cur, label = (x) => x) => `<option value="">All</option>` + vals.map((v) => `<option value="${h(v)}"${v === cur ? " selected" : ""}>${h(label(v))}</option>`).join("");
    return `<div class="page wide">${exploreShell("frames", `
      <h1>Frame explorer</h1>
      <p class="lead">${num(F.length)} frames listed in the session manifests. ${num(codedFrameCount)} of them are coded for behaviour. Click a row to see what was observed and why the frame was taken.</p>
      <div class="filters">
        <label>Student<select id="fS">${opt(STUDENTS, fState.s)}</select></label>
        <label>Session<select id="fSS">${opt(SESS.map((x) => x.id), fState.ss, (x) => SESS_NAME[x])}</select></label>
        <label>Observed behaviour<select id="fB">${opt(BEHAV.map((b) => b[0]).filter((k) => F.some((f) => f.b === k)), fState.b, behLabel)}${F.some((f) => !f.b) ? `<option value="__none"${fState.b === "__none" ? " selected" : ""}>Not coded</option>` : ""}</select></label>
        <label class="chk"><input type="checkbox" id="fP"${fState.prev ? " checked" : ""}> Only frames with a preview</label>
        <button class="btn" id="fCsv" type="button">Download these rows (CSV)</button>
      </div>
      <div class="split"><div id="fOut"></div><aside id="fDetail" class="detail" aria-live="polite"></aside></div>`)}</div>`;
  }
  function frameDetail(f) {
    const el = document.getElementById("fDetail");
    if (!el) return;
    if (!f) { el.innerHTML = `<p class="empty">Select a frame to see its details.</p>`; return; }
    const rec = C.sessions[f.s][f.ss];
    const g = f.gx;
    const issues = sessionIssues(rec);
    el.innerHTML = `<h3>${h(f.s)} · ${h(SESS_NAME[f.ss])} · ${clock(f.t)}</h3>
      ${f.th ? `<button class="thumb big" type="button" data-zoom="thumbs/${h(f.th)}" data-cap="${h(`${f.s} · ${SESS_NAME[f.ss]} · ${clock(f.t)}`)}"><img src="thumbs/${h(f.th)}" alt="Screen at ${clock(f.t)}"></button><p class="small">Cropped and softened for privacy. Click to enlarge.</p>` : `<p class="small">No preview image for this frame. Previews exist for ${C.thumbs_per_session} evenly spaced frames per session.</p>`}
      ${kv([
        ["Observed behaviour", f.b ? `<span class="sw" style="background:${behColor(f.b)}"></span>${h(behLabel(f.b))}` : "Not coded"],
        f.b2 && ["Also observed", h(behLabel(f.b2))],
        f.sc && ["Screen", h(cap(f.sc, SCREEN))],
        f.ph && ["Phase", h(cap(f.ph, PHASE))],
        f.b && ["Visible on screen", f.ev ? f.ev.map((k) => h(EVIDENCE[k] || k)).join("<br>") : "No observation flags set"],
        f.cf && ["Coder confidence", h(cap(f.cf, {}))],
        ["Why this frame was selected", h(TRIGGERS[f.tr] || f.tr)],
        f.sp && f.sp !== "unknown" && ["Speaker at that moment", h(f.sp)],
        ["Related log event", "Not linked frame by frame in the 2026 files"],
        ["Validation", g ? `Automated coding. Matched by order in time to the researcher's observation step ${h(g.step)} (${h(g.category)}). This match was not checked by a person.` : "Automated coding"],
      ])}
      ${issues.length ? `<div class="warn">${h(issues[0])}</div>` : ""}
      ${tech("Technical details", kv([["Frame ID", `<code>${h(f.id)}</code>`], ["Time in recording (s)", num(f.t, 1)], ["Selection code", `<code>${h(f.tr)}</code>`], f.px != null && ["Screen change (%)", num(f.px, 2)], f.b && ["Behaviour code", `<code>${h(f.b)}</code>`], f.ab && ["Added by", `<code>${h(f.ab)}</code>`]]) + (g && g.note ? `<h4>Observation step text (Turkish)</h4><p class="orig">${h(g.note)}</p>` + src(g.source) : "") + src(rec.manifest && rec.manifest.source) + src(rec.coding && rec.coding.source))}`;
  }
  function renderFrameTable() {
    const out = document.getElementById("fOut");
    if (!out) return;
    const rows = filteredFrames();
    const per = 25, pages = Math.max(1, Math.ceil(rows.length / per));
    if (fState.sel) { const idx = rows.findIndex((f) => f.id === fState.sel); if (idx >= 0) fState.page = Math.floor(idx / per); }
    fState.page = Math.min(fState.page, pages - 1);
    const slice = rows.slice(fState.page * per, fState.page * per + per);
    const showStudent = !fState.s, showSession = !fState.ss;
    const head = [].concat(showStudent ? [{ t: "Student" }] : []).concat(showSession ? [{ t: "Session" }] : []).concat([{ t: "Time" }, { t: "Preview" }, { t: "Observed behaviour" }, { t: "Evidence" }]);
    out.innerHTML = `<p class="small">${num(rows.length)} frames${fState.s ? ` for ${h(fState.s)}` : ""}${fState.ss ? ` in ${h(SESS_NAME[fState.ss])}` : ""}</p>
      ${table(head, slice.map((f) => ({
        attrs: ` data-fid="${h(f.s + "|" + f.ss + "|" + f.id)}"${fState.sel === f.id ? ' aria-selected="true"' : ""}`,
        cells: [].concat(showStudent ? [h(f.s)] : []).concat(showSession ? [h(SESS_NAME[f.ss])] : []).concat([
          `<span class="mono">${clock(f.t)}</span>`,
          f.th ? `<img class="mini" loading="lazy" src="thumbs/${h(f.th)}" alt="">` : '<span class="na">–</span>',
          f.b ? `<span class="sw" style="background:${behColor(f.b)}"></span>${h(behLabel(f.b))}` : '<span class="na">Not coded</span>',
          `<span class="small">${h(f.ev && f.ev.length > 3 ? f.ev.slice(0, 3).map((k) => EVIDENCE[k] || k).join(" · ") + ` · +${f.ev.length - 3} more` : evidenceText(f))}</span>`]),
      })))}
      <div class="pager"><button class="btn" id="fPrev" ${fState.page ? "" : "disabled"}>← Previous</button><span>Page ${fState.page + 1} of ${pages}</span><button class="btn" id="fNext" ${fState.page < pages - 1 ? "" : "disabled"}>Next →</button></div>`;
    out.querySelectorAll("tr[data-fid]").forEach((tr) => {
      tr.classList.add("click");
      tr.addEventListener("click", () => {
        const [s, ss, id] = tr.getAttribute("data-fid").split("|");
        fState.sel = id;
        out.querySelectorAll("tr[aria-selected]").forEach((x) => x.removeAttribute("aria-selected"));
        tr.setAttribute("aria-selected", "true");
        frameDetail(F.find((f) => f.s === s && f.ss === ss && f.id === id));
        if (window.innerWidth <= 1280) document.getElementById("fDetail").scrollIntoView({ behavior: "smooth", block: "start" });
      });
    });
    const p = document.getElementById("fPrev"), n = document.getElementById("fNext");
    if (p) p.onclick = () => { fState.page--; fState.sel = null; renderFrameTable(); };
    if (n) n.onclick = () => { fState.page++; fState.sel = null; renderFrameTable(); };
    const selF = fState.sel && rows.find((f) => f.id === fState.sel);
    frameDetail(selF || null);
  }
  function bindWsSearch() {
    const inp = document.getElementById("wsSearch");
    const countEl = document.getElementById("wsCount");
    if (!inp) return;
    let group = "";
    function filterWs() {
      const q = inp.value.trim().toLowerCase();
      const cards = document.querySelectorAll(".ws-card");
      let visible = 0;
      cards.forEach((card) => {
        const textOk = !q || card.dataset.title.includes(q) || card.dataset.code.toLowerCase().includes(q);
        const groupOk = !group || card.dataset.group === group;
        const match = textOk && groupOk;
        card.classList.toggle("ws-hidden", !match);
        if (match) visible++;
      });
      document.querySelectorAll(".ws-group").forEach((g) => {
        const hasVisible = Array.from(g.querySelectorAll(".ws-card")).some((c) => !c.classList.contains("ws-hidden"));
        g.classList.toggle("ws-hidden", !hasVisible);
      });
      const filtering = q || group;
      if (countEl) countEl.textContent = filtering ? `${visible} of ${cards.length} worksheets` : `${cards.length} worksheets`;
      const empty = document.getElementById("wsEmpty");
      if (empty) empty.hidden = visible !== 0;
    }
    inp.addEventListener("input", filterWs);
    document.querySelectorAll(".ws-filters .chip").forEach((btn) => {
      btn.addEventListener("click", () => {
        group = btn.dataset.group || "";
        document.querySelectorAll(".ws-filters .chip").forEach((b) => {
          const on = b === btn;
          b.classList.toggle("on", on);
          b.setAttribute("aria-pressed", on ? "true" : "false");
        });
        filterWs();
      });
    });
  }
  function bindFrames() {
    const upd = () => {
      fState.s = document.getElementById("fS").value; fState.ss = document.getElementById("fSS").value;
      fState.b = document.getElementById("fB").value; fState.prev = document.getElementById("fP").checked; fState.page = 0; fState.sel = null;
      const qs = [["s", fState.s], ["ss", fState.ss], ["b", fState.b], ["p", fState.prev ? "1" : ""]].filter((x) => x[1]).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
      history.replaceState(null, "", "#/explore/frames" + (qs ? "?" + qs : ""));
      renderFrameTable();
    };
    ["fS", "fSS", "fB", "fP"].forEach((id) => { document.getElementById(id).onchange = upd; });
    document.getElementById("fCsv").onclick = () => {
      const head = ["student", "session", "time_s", "primary_behavior", "secondary_behavior", "screen_context", "deepen_phase", "evidence_flags", "confidence", "trigger", "frame_id"];
      const esc = (v) => { v = v == null ? "" : String(v); return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v; };
      const csv = [head.join(",")].concat(filteredFrames().map((f) => [f.s, f.ss, f.t, f.b, f.b2, f.sc, f.ph, (f.ev || []).join(";"), f.cf, f.tr, f.id].map(esc).join(","))).join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
      a.download = "frames_filtered.csv"; document.body.appendChild(a); a.click(); a.remove();
    };
    renderFrameTable();
  }

  function pageLogs() {
    const rows = [];
    STUDENTS.forEach((s) => Object.entries(LOG_DAYS).forEach(([d, meta]) => {
      const v = logDays[s] && logDays[s][d];
      if (!v) {
        rows.push({ cells: [h(s), h(meta.name), '<span class="na">no data</span>', '<span class="na">·</span>', '<span class="na">·</span>', '<span class="na">·</span>'] });
        return;
      }
      const vt = meta.ss && C.sessions[s][meta.ss].votat;
      rows.push({ href: `#/explore/student/${s}/logs`, cells: [`<a href="#/explore/student/${h(s)}/logs">${h(s)}</a>`, h(meta.name), num(v.emit_count), v.last_emit_accuracy == null ? "–" : num(v.last_emit_accuracy * 100, 1) + "%", num(v.unique_attributes_dropped.length), vt ? num(vt.votat_rate * 100, 0) + "%" : "–"] });
    }));
    const L = C.logs;
    return `<div class="page wide">${exploreShell("logs", `
      <h1>Platform logs</h1>
      <p class="lead">CODAP Arbor recorded every action. One row per student and session.</p>
      <dl class="terms compact-terms"><dt>Model attempts</dt><dd>Times the student submitted a tree's results.</dd><dt>Predictors tried</dt><dd>Different variables placed into the tree.</dd><dt>One thing at a time</dt><dd>Share of steps where only one setting changed between attempts.</dd></dl>
      ${table([{ t: "Student" }, { t: "Session" }, { t: "Model attempts", num: 1 }, { t: "Last accuracy", num: 1 }, { t: "Predictors tried", num: 1 }, { t: "One thing at a time", num: 1 }], rows)}
      <p>${methodLink("logs", "What these measures mean")}</p>
      ${tech("Technical details", kv([["Source", `<code>${h(L.source)}</code>`], ["Rows in the file", num(L.rows_total)], ["Rows mapped to a pseudonym", num(sum(L.rows_remapped_to_pseudonym.map((x) => x.rows)))], ["Instructor rows removed", num(sum(Object.values(L.rows_excluded_unmatched_by_day)))]]) + "<p>The 28 April file already contains the 7 and 21 April rows, so it is used as the single source and split by date.</p>" + table([{ t: "Action" }, { t: "Event code" }, { t: "Count", num: 1 }], Object.entries(L.action_types).sort((a, b) => b[1] - a[1]).map(([k, n]) => ({ cells: [h(ACTION[k] || k), `<code>${h(k)}</code>`, num(n)] }))))}`)}</div>`;
  }
  function pageNotebooks() {
    const rows = STUDENTS.map((s) => {
      const n = C.notebooks[s] || {}, f = n.file, e = n.extraction;
      const tot = n.scoring ? sum(Object.values(n.scoring.sections).map((x) => x.awarded)) : null;
      const pos = n.scoring ? sum(Object.values(n.scoring.sections).map((x) => x.possible)) : null;
      return { href: `#/explore/student/${s}/notebook`, cells: [`<a href="#/explore/student/${h(s)}/notebook">${h(s)}</a>`, e ? e.targets.map((t) => `<code>${h(t)}</code>`).join(" ") : "–", e ? num(e.models) : "–", f ? (f.cells_with_error_output ? "Yes" : "None") : "–", f ? num(f.order_reversals) : "–", tot == null ? "–" : `${num(tot, 1)} / ${num(pos, 1)}`] };
    });
    return `<div class="page wide">${exploreShell("notebooks", `
      <h1>Python notebooks</h1>
      <p class="lead">The final project: decision trees on lizard data in Google Colab.</p>
      ${table([{ t: "Student" }, { t: "Target variables" }, { t: "Models", num: 1 }, { t: "Errors in outputs" }, { t: "Revisiting earlier code", num: 1 }, { t: "Rubric points", num: 1 }], rows)}
      <p class="small">“Revisiting earlier code” counts places where the student went back and re-ran earlier cells. It describes how the notebook was produced, not what the student intended.</p>
      <p>${methodLink("notebooks")}</p>`)}</div>`;
  }

  // ------------------------------------------------------------------ 04 Documentation
  const docShell = (active, body) => {
    const back = active ? `<p class="back"><a href="#/docs">← Data and downloads</a></p>` : "";
    return `${back}<p class="kicker">Reference</p>${body}`;
  };

  function pageDownloads() {
    const DICT = {
      "frames.csv": [`One selected screen frame (${num(F.length)} rows)`, [["student", "Pseudonym"], ["session", "codap_21apr or codap_28apr"], ["frame_id", "Frame name within the session"], ["time_s", "Seconds from the start of the recording"], ["trigger", "Why the frame was selected"], ["pixel_change_pct", "Share of the screen that changed"], ["speaker_role", "Who was speaking at that moment, if known"], ["primary_behavior", "Observed behaviour (one of nine codes)"], ["secondary_behavior", "A second behaviour, if any"], ["screen_context", "Tree, graph, table, mixed or menu"], ["deepen_phase", "Setup, building, tuning, evaluating or idle"], ["confidence", "The coder's own confidence"]]],
      "worksheet_responses.csv": [`One extracted worksheet value (${num(responseRows)} rows)`, [["student", "Pseudonym"], ["worksheet", "WS1 to WS15"], ["item", "Question or blank ID"], ["field_path", "Exact position of the value in the extraction file"], ["extracted_value", "What the student wrote, as read and cleaned"], ["item_check_correct", "Result of the check: True, False or empty"], ["item_check_flag", "Short code describing an error, if any"], ["source_file", "Extraction file the value came from"]]],
      "log_sessions.csv": ["One student in one CODAP session", [["student", "Pseudonym"], ["date", "Session date"], ["events", "All recorded actions"], ["span_minutes", "Minutes from first to last action"], ["emit_count", "Model attempts"], ["minutes_to_first_emit", "Minutes to the first attempt"], ["last_emit_accuracy", "Accuracy of the last attempt (0 to 1)"], ["accuracy_sd", "Standard deviation of accuracy across attempts"], ["predictor_drops", "Predictor placements"], ["unique_attributes", "Different predictors tried"], ["emit_tree_data … data_context_change", "Counts of the six modelling actions"]]],
      "episodes.csv": ["One episode of a session (from the video pipeline's Parquet tables)", [["student", "Pseudonym"], ["session", "Session ID"], ["episode_id", "Episode within the session"], ["category", "Episode category"], ["start_ms / end_ms / duration_ms", "Timing in milliseconds"], ["steps", "Observation steps in the episode"], ["assistance", "Independent or assisted"]]],
    };
    return `<div class="page">${docShell("", `
      <h1>Data and downloads</h1>
      <p class="lead">Files from the 2026 decision tree unit, and where to read how they were made. Screen-recording frames and CODAP logs are separate collections.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#guide">Where to go</a>
        <a href="#datasets">Datasets</a>
        <a href="#worksheets">Worksheets</a>
        <a href="#food">Food cards</a>
        <a href="#tables">Analysis tables</a>
      </nav>

      <h2 id="guide">Where to go</h2>
      <ul class="guide">
        <li><a href="#/">Overview</a><span>What the archive contains, and the counts behind it.</span></li>
        <li><a href="#/methods">How the system works</a><span>How answers were read, frames were selected, and codes were checked.</span></li>
        <li><a href="#/explore/worksheets">Worksheets</a><span>Purpose, student responses, and the blank PDFs.</span></li>
        <li><a href="#/explore/recordings">Screen recordings</a><span>One row per student and session, with behaviour over time.</span></li>
        <li><a href="#/explore/frames">Frame explorer</a><span>Manifest-listed frames and their behaviour codes.</span></li>
        <li><a href="#/explore/logs">Platform logs</a><span>CODAP Arbor actions. These logs are not a Hugging Face dataset.</span></li>
        <li><a href="#/explore/notebooks">Python notebooks</a><span>Final projects on the lizard data.</span></li>
        <li><a href="#/docs/limitations">Data notes</a><span>Where a file is missing, duplicated, or differs from the written method.</span></li>
        <li><a href="#/docs/glossary">Glossary</a><span>Terms used on this site, including Turkish words in student answers.</span></li>
        <li><a href="#/docs/technical">Technical documentation</a><span>Folder paths, rebuild commands, and the coverage table.</span></li>
      </ul>

      <h2 id="datasets">Research datasets</h2>
      <p>The frame dataset is published on Hugging Face under a CC BY 4.0 licence. The interaction logs stay in this archive.</p>
      <div class="dataset-grid">
        <div class="dataset-card">
          <div class="ds-type">Screen-recording frames</div>
          <div class="ds-title">DecisionTrees-AICFT-Frames</div>
          <div class="ds-desc">${num(F.length)} frames listed from two CODAP Arbor sessions, of which ${num(codedFrameCount)} are coded for behaviour. Each coded frame includes a behaviour code, screen context, confidence, and observation flags.</div>
          <div class="ds-meta">${num(F.length)} listed · ${STUDENTS.length} participants · 2 sessions · CC BY 4.0</div>
          <div class="ds-links">
            <a href="https://huggingface.co/datasets/dedemerve/DecisionTrees-AICFT-Frames" target="_blank" rel="noopener">View on Hugging Face</a>
            <a href="#/explore/frames">Browse frames</a>
            <a href="data/frames.csv" download>frames.csv</a>
          </div>
        </div>
        <div class="dataset-card">
          <div class="ds-type">Platform interaction logs</div>
          <div class="ds-title">CODAP Arbor interaction logs</div>
          <div class="ds-desc">Time-stamped platform actions, including model submissions with accuracy, depth, and confusion-matrix counts. Not published as a Hugging Face dataset.</div>
          <div class="ds-meta">${num(logEvents)} events · ${STUDENTS.length} participants · 3 log days</div>
          <div class="ds-links">
            <a href="#/explore/logs">Browse log data</a>
            <a href="data/log_sessions.csv" download>log_sessions.csv</a>
          </div>
        </div>
      </div>

      ${materials()}
      <h2 id="tables">Analysis tables</h2>
      <p>The tables behind this site. Column definitions stay closed until you open them.</p>
      ${Object.entries(DICT).map(([f, [desc, cols]]) => `<section class="dl"><h3><a href="data/${f}" download>${f}</a></h3><p>${h(desc)}</p>${tech("Data dictionary", table([{ t: "Column" }, { t: "Meaning" }], cols.map(([c, m]) => ({ cells: [`<code>${h(c)}</code>`, h(m)] }))))}</section>`).join("")}
      <h2 id="access">Access</h2>
      <p>All tables use pseudonyms only. They still contain student work, so sharing beyond the research team should follow the project's data protection rules (<code>DATA_PROTECTION.md</code> in the repository). The original Parquet tables stay in the repository and are described in the <a href="#/docs/technical">technical documentation</a>.</p>`)}</div>`;
  }
  function materials() {
    const D = C.downloads || {};
    const cards = D.cards;
    const LABEL = { recommended: "Recommended", not_recommended: "Not recommended" };
    let out = `<h2 id="worksheets">Worksheet PDFs</h2><p>Blank editions, as handed to the students. Descriptions and extracted responses are in the <a href="#/explore/worksheets">worksheet catalogue</a>.</p>` +
      table([{ t: "Worksheet" }, { t: "Topic" }, { t: "File", num: 1 }], D.worksheets.map((d) => {
        const w = C.worksheets.find((x) => x.code === d.code);
        return { cells: [`<a href="${h(d.file)}" download><b>${h(d.code)} · ${h(wsTitle(w))}</b></a>`, `<span class="small">${h((WS_INFO[d.code] || {}).topic || "")}</span>`, `<a href="${h(d.file)}" download>PDF, ${bytes(d.bytes)}</a>`] };
      }));
    if (cards) {
      const nutr = [["energy_kcal", "Energy (kcal)"], ["fat_g", "Fat (g)"], ["saturated_fat_g", "Saturated fat (g)"], ["carbohydrates_g", "Carbohydrates (g)"], ["sugar_g", "Sugar (g)"], ["protein_g", "Protein (g)"], ["salt_g", "Salt (g)"]];
      out += `<h2 id="food">Food data cards</h2><p>The ${cards.rows.length} food cards used in worksheets 4 to 7. The Python checks for WS5, WS6 and WS7 compute the correct answers from this table. <a href="${h(cards.file)}" download>Download CSV</a></p>` +
        table([{ t: "Food" }, { t: "Turkish name" }, { t: "Label" }].concat(nutr.map(([, l]) => ({ t: l, num: 1 }))),
          cards.rows.map((r) => ({ cells: [h(r.name_en), `<span class="orig">${h(r.name_tr)}</span>`, h(LABEL[r.label] || r.label)].concat(nutr.map(([k]) => h(r[k]))) })));
    }
    out += `<h2 id="class-data">Class datasets</h2><p>The class datasets (food data, Xeno, Titanic and the lizard data) are not stored as separate files in the project folder. The food data exists only inside the students' saved CODAP documents, and those copies differ because students filtered or edited cases. They are therefore not offered here as a single download.</p>`;
    return out;
  }

  function limitationItems() {
    const dupes = {};
    allSessions.filter((r) => r.same_video_file_as).forEach((r) => { (dupes[r.student] = dupes[r.student] || []).push(SESS_NAME[r.session]); });
    const gone = allSessions.filter((r) => r.video_bytes && r.video_on_disk === false);
    const low = allSessions.filter((r) => r.frame_coverage != null && r.frame_coverage < 0.8);
    const noOcr = C.worksheets.filter((w) => STUDENTS.every((s) => !C.ws[s][w.code].ocr)).map((w) => w.code);
    const thr = {};
    allSessions.forEach((r) => { const v = r.manifest && r.manifest.parameters.motion_threshold_fraction; if (v != null) thr[v] = (thr[v] || 0) + 1; });
    const zero = [];
    STUDENTS.forEach((s) => C.worksheets.forEach((w) => { const r = C.ws[s][w.code]; if (r.ocr && r.stage && r.stage.scoring && r.stage.scoring.all_zero_with_zero_confidence) zero.push(`${s} ${w.code}`); }));
    const epNoVideo = [];
    STUDENTS.forEach((s) => SESS.forEach((ss) => { if ((C.episodes[s] || {})[ss.id] && !C.sessions[s][ss.id].manifest) epNoVideo.push(`${s} (${SESS_NAME[ss.id]})`); }));
    const badLen = allSessions.filter((r) => r.video_measured_seconds && r.recording && Math.abs(r.video_measured_seconds - r.recording.duration_seconds) > 60);
    const missingWs = C.build.missing.filter((m) => /^OCR file/.test(m.what));
    const missingBy = {};
    missingWs.forEach((m) => { const mm = /^OCR file (\S+) for (\S+)$/.exec(m.what); if (mm) (missingBy[mm[2]] = missingBy[mm[2]] || []).push(mm[1]); });
    const tl = C.training_log_meta;
    const L = C.logs;
    const I = (title, what, why, detail) => ({ title, what, why, detail });
    return [
      ["Missing or duplicated data", [
        Object.keys(dupes).length && I("Some recordings are the same file", `${Object.entries(dupes).map(([s, l]) => `${h(s)} (${l.map(h).join(", ")})`).join("; ")}: the video files for these sessions are identical.`, "Only one of each group can be the real recording of its day. Behaviour results for these sessions may describe a different day, so comparisons across sessions are unreliable for these students.", "Identical SHA-256 fingerprints in <code>data_sources_2026/MANIFEST.json</code>."),
        gone.length && I("Some original videos are no longer in the data folder", `${gone.length} of ${videoFilesListed} listed videos: ${gone.map((r) => `${h(r.student)} (${h(SESS_NAME[r.session])})`).join(", ")}.`, "The frames and their coding remain, but they cannot be re-extracted or checked against the original video.", `Listed in <code>MANIFEST.json</code> of ${h(C.inventory.generated_at.slice(0, 10))}. Some processing folders hold re-encoded copies (<code>*.video.webm</code>) of different size.`),
        low.length && I("Frames cover only part of some videos", `${low.map((r) => `${h(r.student)} (${h(SESS_NAME[r.session])}, ${num(r.frame_coverage * 100)}%)`).join(", ")}.`, "Activity in the later part of these sessions is not represented in the frames.", table([{ t: "Student" }, { t: "Session" }, { t: "Last frame" }, { t: "Length in manifest" }, { t: "Real length" }], low.map((r) => ({ cells: [h(r.student), h(SESS_NAME[r.session]), clock(r.manifest.last_s), r.manifest.profile_duration_seconds ? clock(r.manifest.profile_duration_seconds) : "–", clock(lengthOf(r))] }))) + "<p>The extractor recorded the videos as shorter than they are. WebM files often carry no length in their header.</p>"),
        noOcr.length && I(`No extracted answers for ${noOcr.join(" and ")}`, "No student answers were extracted for these worksheets.", "These worksheets add no evidence to the analysis.", "Stage files in <code>students/</code> record a failed extraction. No scanned student file for WS11 is in <code>All Documents/</code>. A file named “31 Mart 2026 Çalışma Kâğıdı 12.pdf” exists but was not processed."),
        Object.keys(missingBy).length && I("Some worksheets are missing for some students", Object.entries(missingBy).map(([s, l]) => `${h(s)}: ${l.map(h).join(", ")}`).join("; ") + ".", "These students have fewer worksheet data points than others.", missingWs.map((m) => `<code>${h(m.path)}</code>`).join("<br>")),
        C.notebooks.Marco && !C.notebooks.Marco.file && C.notebooks.Marco.extraction && I("One final project is a report, not a notebook", "Marco submitted a PDF report. The notebook details were taken from it.", "Notebook structure (cells, run order, errors) cannot be measured for this student.", ""),
      ]],
      ["Method and data differences", [
        I("Motion threshold differs from the written method", `The method text gives 0.005. The CODAP extraction files record ${Object.entries(thr).map(([v, n]) => `${h(v)} (${n} sessions)`).join(", ")}.`, "A higher threshold selects fewer frames. The method description should state the value actually used.", "0.005 is the code default in <code>scripts/dynamic_video_analytics.py</code>."),
        I("Video and log are not linked frame by frame", "The 2026 frame-coding files record the alignment as unavailable or do not record it.", "The site cannot show which log action belongs to which frame. Logs are shown separately.", `Training-bundle metadata (${tl.files} files) also says no event log was available, which is out of date: the log CSV files exist.`),
        I("No written visual evidence per frame", "The method text names <code>visual_evidence</code> and <code>confidence_status</code>. The files contain yes/no observation flags and <code>analysis_confidence</code> instead.", "The evidence shown on this site is the coder's flags, not a written description.", ""),
        I("Fewer response fields than stated", `The method text mentions 270 response fields. The worksheet schemas define ${num(schemaFields)}.`, "Reported totals should match the schemas.", C.worksheets.map((w) => `${h(w.code)} ${w.fields_in_schema}`).join(", ")),
        zero.length && I("Stage scores that do not match the answers", `For ${zero.length} student-worksheet pairs the stage score file gives every item 0 points with confidence 0, while the answers exist.`, "Totals taken from these files would understate these students. The site shows the answers and their checks instead.", zero.map(h).join(", ")),
        badLen.length && I("A recording length in the audio list is wrong", badLen.map((r) => `${h(r.student)} (${h(SESS_NAME[r.session])}): listed as ${num(r.recording.duration_seconds, 1)} s, the video is ${dur(r.video_measured_seconds)}`).join("; ") + ".", "The site uses the length measured from the video.", ""),
        I("Episode tables use their own categories", "The episode tables use categories such as EXPLORE and MISCONCEPTION, not the nine frame behaviours.", "Episode results and frame results cannot be compared one to one.", epNoVideo.length ? `They also exist for sessions without a recording: ${epNoVideo.map(h).join(", ")}.` : ""),
        !L.delete_events_present && I("Recovery from errors cannot be measured", "The method describes deleting a tree and rebuilding it. The 2026 logs contain no delete actions.", "This behaviour is absent from the log-based measures.", ""),
        I("Evidence length rule", "The method text says the evidence quote has at least 10 characters. In the code this minimum applies to the model's reason, not the quote.", "The method description should be corrected.", "<code>worksheet_assessor.py</code>, field <code>llm_rationale</code>."),
      ]],
      ["Privacy and validation", [
        I("Pseudonyms only", `Log entries typed under a real name were mapped to the pseudonym with the project's official mapping (${num(sum(L.rows_remapped_to_pseudonym.map((x) => x.rows)))} rows). Instructor entries were removed (${num(sum(Object.values(L.rows_excluded_unmatched_by_day)))} rows).`, "No real name appears on the site. The build stops if one does.", "Mapping: <code>scripts/anonymize_student_data.py</code>."),
        I("Screen images are cropped and softened", "The browser tab in the recordings shows students' real names. Previews drop the browser bar and taskbar and are softened until no text can be read.", "Previews show the layout of the screen, not its content.", "Speech transcripts are not shown."),
        I("Automated results vs. researcher checks", "The files used here do not record the researcher's decision for each frame or answer. Everything is labelled as automated. Frames matched to the researcher's written observations are marked, with a note that the match itself is automatic.", "Treat behaviour codes and checks as machine output that was reviewed in bulk, not as item-by-item human ratings.", ""),
        I("How this site was checked", "A separate test script re-reads the original files and compares samples of every table with the site: worksheet values, checks, frames, codes, log counts, notebook structure and the duplicate claims.", "Values on the site match their source files.", "<code>mmla_explorer/test_site_data.py</code>"),
      ]],
    ].map(([g, items]) => [g, items.filter(Boolean)]);
  }
  function pageLimitations() {
    return `<div class="page">${docShell("limitations", `
      <h1>Data notes</h1>
      <p class="lead">Where the data are incomplete, duplicated, or differ from the written method, and what that means for the results. Each point is computed from the files. File-level details are in the <a href="#/docs/technical">technical documentation</a>.</p>
      <nav class="jump" aria-label="On this page">${limitationItems().map(([g], i) => `<a href="#note-${i}">${h(g)}</a>`).join("")}</nav>
      ${limitationItems().map(([g, items], i) => `<h2 id="note-${i}">${h(g)}</h2>${items.map((it) => `<section class="lim"><h3>${it.title}</h3><p>${it.what}</p><p class="why"><b>Why it matters.</b> ${it.why}</p>${it.detail ? tech("Details", `<div>${it.detail}</div>`) : ""}</section>`).join("")}`).join("")}`)}</div>`;
  }
  function pageGlossary() {
    const treeFundamentals = [
      ["Decision tree", "A predictive model that makes decisions by following a sequence of branching rules. Starting at the root, each rule tests whether a value meets a threshold, routing a case left or right until it reaches a leaf that gives the prediction. In this project students built trees to classify food items as recommended or not recommended."],
      ["Classification", "A task in which each case is assigned to one of a fixed set of categories, called classes. In this project the two classes are “recommended” and “not recommended”. A decision tree that performs classification is called a classification tree."],
      ["Model", "A representation of a pattern in data used to make predictions about new cases. In this archive “model” usually refers to a decision tree that a student has built and submitted for evaluation."],
      ["Node, root node, leaf", "A node is any decision point in a tree. The root node is the first and topmost decision point. A leaf is a terminal node with no further splits; it gives the final prediction. In this project leaf labels show whether food is recommended or not recommended."],
      ["Split", "A single decision rule that divides cases into two groups based on whether a feature value meets a threshold. Choosing a feature and a threshold defines one split."],
      ["Feature, predictor", "A measurable characteristic used as input to a model. In this project features are the nutritional values on the food cards, such as fat or energy. The terms feature, predictor, and variable are often used interchangeably, though their precise meanings can vary by context."],
      ["Target", "The variable the model is built to predict. In this project the target is whether a food item is recommended or not recommended. Also called the dependent variable or outcome."],
      ["Threshold", "A numerical cut-off used in a decision rule. In the rule “fat ≤ 8 g”, the threshold is 8: items at or below 8 g go to the left branch; items above go to the right."],
    ];
    const evaluation = [
      ["Accuracy", "The proportion of predictions that are correct over the evaluated cases. If a tree classifies 90 of 100 items correctly, its accuracy is 90%. Accuracy is calculated over a defined set of cases, usually the test data."],
      ["Misclassification rate", "The proportion of predictions that are incorrect; the complement of accuracy (1 − accuracy). A misclassification rate of 10% means 1 in 10 predictions is wrong."],
      ["TP, TN, FP, FN", "Four counts that describe how a model’s predictions compare with actual outcomes. A true positive (TP) is a case the model correctly predicts as the positive class. A true negative (TN) is a case correctly predicted as the negative class. A false positive (FP) is a case incorrectly predicted as positive. A false negative (FN) is a case incorrectly predicted as negative."],
      ["Confusion matrix", "A table that arranges the four prediction outcomes—TP, TN, FP, and FN—showing at a glance where a model is correct and where it errs. Rows represent actual classes; columns represent predicted classes."],
      ["Sensitivity", "The proportion of actual positive cases that the model correctly identifies: TP ÷ (TP + FN). High sensitivity means few genuine positives are missed. Sensitivity is different from accuracy, which covers all predictions regardless of class."],
      ["Overfitting", "A model that has learned the specific details of its training data so closely that it does not generalise well to new data. An overfitted tree may score high accuracy on training data but perform worse on the test set."],
      ["Training and test data", "The training data are used to build the model. The test data are kept separate and used only to measure performance on unseen cases; they play no part in building the model. In this project students compared training and test accuracy to detect overfitting."],
    ];
    const researchData = [
      ["Screen recording", "A video file that captures everything displayed on a participant’s screen during an activity, along with audio. Students recorded their screens during each CODAP Arbor session in this project."],
      ["Session", "One period of work by a student on a given date. In this archive each student has records from up to two CODAP Arbor sessions."],
      ["Frame", "A single still image extracted from a screen recording at a moment of interest, such as when the screen changes or when speech occurs. Frames are not taken at fixed intervals. A frame represents one moment; it is not the full recording."],
      ["Episode", "A labelled stretch of a screen recording during which a student is engaged in a related sequence of activity, such as building or evaluating a tree. Each episode has a start time, an end time, and a category."],
      ["Behavioural code", "A category from the codebook assigned to a frame to describe what a student appears to be doing at that moment. Nine codes are used in this project, for example building a tree or evaluating a model."],
      ["Platform log", "A time-stamped record of actions taken in CODAP Arbor during a session, such as adding a predictor, changing a threshold, or submitting results. Log data allow behaviour to be measured without watching the recordings."],
      ["CODAP Arbor", "A browser-based learning tool in which students explore data and build decision trees by dragging variables into a tree interface. During this project it recorded a time-stamped entry for each platform action, including every tree submission."],
    ];
    const computational = [
      ["Language model", "A computational system that can read, describe, and interpret written or visual content. In this project a language model read handwritten worksheet responses and described screen frames, always working within researcher-defined instructions and output formats."],
      ["Retrieval-augmented generation (RAG)", "A method in which relevant reference material—such as a rubric entry or codebook rule—is retrieved and supplied to a language model alongside the task. This provides specific guidance rather than relying on the model’s general training alone. Retrieval does not guarantee a correct answer; the researcher reviewed all outputs."],
      ["Rubric", "A set of predefined criteria used to evaluate student responses, specifying what counts as a full, partial, or missing answer. In this project rubrics were used alongside the language model to score worksheet responses that require interpretation."],
      ["Codebook", "A document that defines the behaviour categories that can be assigned to a screen-recording frame, together with the criteria for choosing one category over another. The codebook was developed from human-coded recordings before being used to guide the language model."],
    ];
    const privacyTerms = [
      ["Pseudonym", "An alternative identifier assigned to a participant in place of their real name. In this archive all students are referred to by pseudonyms. Pseudonymisation reduces identifiability but does not constitute complete anonymisation, as contextual details in the data could potentially still identify an individual."],
    ];
    const techTerms = [
      ["OCR / HTR", "Optical character recognition (OCR) reads printed text from images; handwriting text recognition (HTR) reads handwritten text. Both were used to extract student answers from scanned worksheets."],
      ["Diarization", "Separating an audio recording into segments by speaker. Used here to distinguish teacher and student speech in screen recordings."],
      ["VOTAT", "“Vary one thing at a time”: changing only the predictor or only the threshold between two model submissions. A high VOTAT rate suggests systematic exploration."],
      ["Emit", "Submit a tree’s results in CODAP Arbor. Each submission records the tree’s accuracy, depth, target, and TP / TN / FP / FN counts."],
      ["Log–video alignment", "Matching platform log events to screen-recording frames by timestamp. In the 2026 data this alignment is not recorded at the individual-frame level."],
      ["SHA-256", "A hash function that produces a fixed-length fingerprint for a file. Two files with the same SHA-256 value have identical contents."],
      ["Parquet", "A column-oriented file format used for the analysis tables in this archive. Readable with Python (pandas, polars) or R."],
      ["AI-CFT", "UNESCO’s AI Competency Framework for Teachers. Codes such as LO3.2.1 label the competencies mapped in this project."],
    ];
    const tr = [["Enerji", "Energy"], ["Yağ", "Fat"], ["Doymuş yağ", "Saturated fat"], ["Karbonhidrat", "Carbohydrate"], ["Şeker", "Sugar"], ["Tuz", "Salt"], ["Tavsiye edilebilir", "Recommended"], ["Tavsiye edilemez / edilmez", "Not recommended"], ["Nesne", "Object"], ["Özellik", "Feature"], ["Değişken", "Variable"], ["Etiket", "Label"], ["Değer", "Value"], ["Eşik değer", "Threshold value"], ["Hasta / sağlıklı", "Sick / healthy"], ["Hayatta / öldü", "Survived / died"], ["Eğitim / test", "Training / test"], ["(bos)", "Blank"]];
    const mkTable = (rows) => table([{ t: "Term" }, { t: "Meaning" }], rows.map(([a, b]) => ({ cells: [`<b>${h(a)}</b>`, h(b)] })));
    return `<div class="page">${docShell("glossary", `
      <h1>Glossary</h1>
      <p class="lead">Terms used on this site, grouped by topic.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#g-tree">Decision trees</a>
        <a href="#g-eval">Evaluation</a>
        <a href="#g-data">Research data</a>
        <a href="#g-methods">Methods</a>
        <a href="#g-privacy">Privacy</a>
        <a href="#g-tr">Turkish words</a>
      </nav>
      <h2 id="g-tree">Decision tree fundamentals</h2>
      ${mkTable(treeFundamentals)}
      <h2 id="g-eval">Model evaluation</h2>
      ${mkTable(evaluation)}
      <h2 id="g-data">Research data and behavioural analysis</h2>
      ${mkTable(researchData)}
      <h2 id="g-methods">Computational methods</h2>
      ${mkTable(computational)}
      <h2 id="g-privacy">Privacy</h2>
      ${mkTable(privacyTerms)}
      <h2 id="g-tr">Turkish words in student answers</h2>
      ${table([{ t: "Turkish" }, { t: "English" }], tr.map(([a, b]) => ({ cells: [`<span class="orig">${h(a)}</span>`, h(b)] })))}
      ${tech("Technical terms", mkTable(techTerms))}`)}</div>`;
  }
  function pageTechnical() {
    const inv = Object.assign({}, C.inventory);
    // The Python-session screen recordings are not part of this archive.
    inv.folders = inv.folders.filter((f) => !/Colab Python Screen Recordings/.test(f.folder));
    inv.file_count = sum(inv.folders.map((f) => f.files));
    inv.total_bytes = sum(inv.folders.map((f) => f.bytes));
    return `<div class="page wide">${docShell("technical", `
      <h1>Technical documentation</h1>
      <p class="lead">For researchers who want to trace values back to the project files.</p>
      <h2>Rebuilding the site</h2>
      <p><code>python3 mmla_explorer/build_site_data.py</code> reads the project files and writes the site data. <code>python3 mmla_explorer/test_site_data.py</code> re-reads the sources and compares them with the site. Last build: ${h(C.built_at.replace("T", " "))}.</p>
      <h2>Raw data folders</h2>
      <p>From <code>${h(inv.source)}</code> (${h(inv.generated_at.slice(0, 10))}): ${num(inv.file_count)} files, ${bytes(inv.total_bytes)}. The Python-session screen recordings are left out.</p>
      ${table([{ t: "Folder" }, { t: "Files", num: 1 }, { t: "Size", num: 1 }, { t: "Types" }], inv.folders.map((f) => ({ cells: [`<code>${h(f.folder)}</code>`, num(f.files), bytes(f.bytes), h(Object.entries(f.ext).map(([e, n]) => `${e} ${n}`).join(", "))] })))}
      <h2>Analysis tables per session</h2>
      ${table([{ t: "Level" }, { t: "File" }, { t: "Contents" }], [
        { cells: ["Session", "<code>*_session_ml_features.parquet</code>", "One row per session with yes/no process features."] },
        { cells: ["Episode", "<code>*_episodes.parquet</code>", "Stretches of related activity with start, end, category and assistance."] },
        { cells: ["Episode × code", "<code>*_episode_process_codes.parquet</code>", "Each episode and process code: observed or not, with evidence counts."] },
      ])}
      <p class="small">Location: <code>training_datasets/2026/&lt;student&gt;/&lt;session&gt;/exports/tabular/</code>.</p>
      <h2>Coverage by student</h2>
      ${table([{ t: "Student" }].concat(C.worksheets.map((w) => ({ t: w.code }))).concat(SESS.map((s) => ({ t: SESS_NAME[s.id] }))).concat([{ t: "Notebook" }]),
        STUDENTS.map((s) => ({ cells: [h(s)].concat(C.worksheets.map((w) => C.ws[s][w.code].ocr ? mark(true) : '<span class="na">·</span>')).concat(SESS.map((ss) => C.sessions[s][ss.id].manifest ? mark(true) : '<span class="na">·</span>')).concat([C.notebooks[s] && C.notebooks[s].file ? mark(true) : '<span class="na">·</span>']) })))}`)}</div>`;
  }

  // ------------------------------------------------------------------ router
  function parse() {
    const raw = location.hash.replace(/^#\/?/, "");
    const [path, query] = raw.split("?");
    const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
    const q = {};
    (query || "").split("&").filter(Boolean).forEach((kvp) => { const [k, v] = kvp.split("="); q[k] = decodeURIComponent(v || ""); });
    return { parts, q, query };
  }
  // Links from the first version of the site.
  const LEGACY = { how: "methods", students: "explore/students", worksheets: "explore/worksheets", recordings: "explore/recordings", frames: "explore/frames", logs: "explore/logs", notebooks: "explore/notebooks", data: "docs", notes: "docs/limitations", glossary: "docs/glossary", student: "explore/student", worksheet: "explore/worksheet" };
  function route() {
    const { parts, q, query } = parse();
    if (LEGACY[parts[0]]) {
      const rest = parts.slice(1).join("/");
      location.replace("#/" + LEGACY[parts[0]] + (rest ? "/" + rest : "") + (query ? "?" + query : ""));
      return;
    }
    const top = parts[0] || "";
    let html, after = null;
    if (top === "") html = pageOverview();
    else if (top === "methods") { html = pageMethods(); after = () => { const a = parts[1] && document.getElementById("m-" + parts[1]); if (a) a.scrollIntoView(); }; }
    else if (top === "explore") {
      const sub = parts[1] || "students";
      if (sub === "student") html = pageStudent(parts[2], parts[3]);
      else if (sub === "worksheets") { html = pageWorksheets(); after = bindWsSearch; }
      else if (sub === "worksheet") html = pageWorksheet(parts[2]);
      else if (sub === "recordings") html = pageRecordings();
      else if (sub === "frames") { html = pageFrames(q); after = bindFrames; }
      else if (sub === "logs") html = pageLogs();
      else if (sub === "notebooks") html = pageNotebooks();
      else html = pageStudents();
    } else if (top === "docs") {
      const sub = parts[1] || "";
      html = sub === "limitations" ? pageLimitations() : sub === "glossary" ? pageGlossary() : sub === "technical" ? pageTechnical() : pageDownloads();
    } else html = `<div class="page"><h1>Page not found</h1><p><a href="#/">Go to the overview</a></p></div>`;
    app.innerHTML = html;
    tip.style.display = "none";
    const navKey = top === "explore" ? ({ student: "students", worksheet: "worksheets" }[parts[1]] || parts[1] || "students")
      : top === "docs" ? (parts[1] || "docs") : top;
    document.querySelectorAll(".nav-link, .top-link").forEach((a) => {
      const on = a.dataset.r === navKey || (a.classList.contains("top-link") && a.dataset.r === "docs" && top === "docs");
      a.classList.toggle("active", on);
    });
    document.querySelectorAll(".nav-group").forEach((g) => { if (g.querySelector(".nav-link.active")) g.open = true; });
    closeNav();
    window.scrollTo(0, 0);
    if (after) after();
    const finder = document.getElementById("finder");
    if (finder) {
      const find = (exact) => { const v = finder.value.trim().toLowerCase(); return v && STUDENTS.find((x) => exact ? x.toLowerCase() === v : x.toLowerCase().startsWith(v)); };
      finder.addEventListener("change", () => { const s = find(true); if (s) location.hash = `#/explore/student/${s}`; });
      finder.addEventListener("keydown", (e) => { if (e.key === "Enter") { const s = find(false); if (s) location.hash = `#/explore/student/${s}`; } });
    }
    const h1 = app.querySelector("h1");
    document.title = (top && h1 ? h1.textContent + " · " : "") + "Decision Tree Learning Archive";
  }
  app.addEventListener("click", (e) => {
    if (e.target.closest("a, button, summary, input, select, [data-fid]")) return;
    const tr = e.target.closest("tr[data-href]");
    if (tr) location.hash = tr.getAttribute("data-href");
  });
  window.addEventListener("hashchange", route);
  route();
})();
