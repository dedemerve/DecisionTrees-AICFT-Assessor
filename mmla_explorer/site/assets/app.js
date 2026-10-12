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
    WS12: { date: "31 March 2026", title: "Decision tree documentation (training & test data)", topic: "Document a two-level decision tree by recording the root variable, thresholds, node counts at each branch, and the number of misclassified items in training and test sets. Unplugged group activity." },
    WS13: { date: "21–28 April 2026", title: "Decision trees for classification activity", topic: "Choosing variables, reading a tree, TP/FP, sensitivity, misclassification rate and overfitting." },
    WS14: { date: "7 April 2026", title: "Diagnosis game with trees (Xeno)", topic: "Diagnose an alien disease with a tree in CODAP Arbor. Each student receives a randomly generated case set." },
    WS15: { date: "7 April 2026", title: "Titanic data in CODAP Arbor", topic: "Build a tree on a Titanic training sample, then check it on a test sample." },
  };
  const wsTitle = (w) => (WS_INFO[w.code] && WS_INFO[w.code].title) || (w.printed_title ? w.printed_title.replace(/^Worksheet \d+:\s*/, "") : w.code);
  const HOW_CHECKED = {
    deterministic: "Python rules compare each value with the 11 food cards. The language model only reads the handwriting.",
    llm_rubric: "Each answer is compared with the researcher's rubric and answer key. Python adds up the item scores.",
  };
  const howChecked = (w) => {
    const policy = w.rubric_data && w.rubric_data.scoring_policy;
    if (policy && policy.basis === "internal_consistency") return "Scores check whether the recorded tree is internally consistent. The rubric says there is no single correct tree.";
    return w.code === "WS14" ? "Numbers are checked against rules that always hold for this data (the four counts add up, and false positives and false negatives are zero). Open answers use the rubric."
    : w.code === "WS15" ? "Numbers are compared with the Titanic reference values, within 0.02. Open answers use the rubric."
      : w.code === "WS10" ? "Python rules check the energy-threshold table. The language model only reads the handwriting. This is not the Titanic worksheet."
        : w.code === "WS11" ? "No extracted student answers are aligned to this survey, so it is not treated as scored evidence."
          : HOW_CHECKED[w.pipeline];
  };

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
    WS12_root_feature: "Root variable", WS12_root_left_threshold: "Left threshold", WS12_root_right_threshold: "Right threshold",
    WS12_left_child_label: "Left child", WS12_left_child_rec: "Left · recommended", WS12_left_child_notrec: "Left · not recommended",
    WS12_right_child_label: "Right child", WS12_right_child_rec: "Right · recommended", WS12_right_child_notrec: "Right · not recommended",
    WS12_depth1_ll_threshold: "Left-left threshold", WS12_depth1_lr_threshold: "Left-right threshold",
    WS12_depth1_rl_threshold: "Right-left threshold", WS12_depth1_rr_threshold: "Right-right threshold",
    WS12_leaf_ll_rec: "Leaf LL · rec", WS12_leaf_ll_notrec: "Leaf LL · not rec",
    WS12_leaf_lr_rec: "Leaf LR · rec", WS12_leaf_lr_notrec: "Leaf LR · not rec",
    WS12_leaf_rl_rec: "Leaf RL · rec", WS12_leaf_rl_notrec: "Leaf RL · not rec",
    WS12_leaf_rr_rec: "Leaf RR · rec", WS12_leaf_rr_notrec: "Leaf RR · not rec",
    WS12_train_errors: "Training errors", WS12_test_errors: "Test errors",
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
    return `<div class="table-wrap"${opts.max ? ` style="max-height:${opts.max}px;overflow:auto"` : ""}><table${opts.cls ? ` class="${h(opts.cls)}"` : ""}><thead><tr>${ths}</tr></thead><tbody>${trs || `<tr><td colspan="${head.length}" class="na">No rows.</td></tr>`}</tbody></table></div>`;
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
          <h1><span class="hero-line">Documenting the Process of Learning</span> <span class="hero-line">Decision Tree Modeling</span></h1>
          <p class="hero-lead">A research archive of worksheets, screen recordings, platform logs, and notebooks from a decision-tree unit with ${STUDENTS.length} pre-service teachers, shown only by pseudonym.</p>
          <div class="hero-actions">
            <a class="btn-primary" href="https://github.com/dedemerve/DecisionTrees-AICFT-Assessor" target="_blank" rel="noopener">View the code on GitHub</a>
            <a class="btn-secondary" href="#/methods">How it was processed</a>
          </div>
        </div>
        <figure class="hero-visual">
          <svg viewBox="0 0 560 248" role="img" aria-label="A decision tree. Fat is the feature. A rule sends the food card down one branch. The leaf is the prediction: recommended or not recommended.">
            <path d="M280 78 V118 H150 V162 M280 118 H410 V162" fill="none" stroke="#2458A6" stroke-width="1.5"/>
            <rect x="168" y="8" width="224" height="70" fill="#172B4D"/>
            <text x="280" y="30" text-anchor="middle" fill="#8FB4E8" font-size="11" font-weight="600">Feature</text>
            <text x="280" y="52" text-anchor="middle" fill="#FFFFFF" font-size="18" font-weight="600">Fat</text>
            <text x="280" y="68" text-anchor="middle" fill="#D5E3F7" font-size="11">Rule: at or below the cut-off?</text>
            <text x="188" y="112" text-anchor="middle" fill="#2458A6" font-size="12" font-weight="600">yes</text>
            <text x="372" y="112" text-anchor="middle" fill="#586579" font-size="12" font-weight="600">no</text>
            <rect x="40" y="162" width="220" height="70" fill="#EDF3FB" stroke="#2458A6" stroke-width="1"/>
            <text x="150" y="186" text-anchor="middle" fill="#2458A6" font-size="11" font-weight="600">Prediction</text>
            <text x="150" y="210" text-anchor="middle" fill="#172B4D" font-size="15" font-weight="600">Recommended</text>
            <rect x="300" y="162" width="220" height="70" fill="#F6F8FB" stroke="#D8DEE8" stroke-width="1"/>
            <text x="410" y="186" text-anchor="middle" fill="#586579" font-size="11" font-weight="600">Prediction</text>
            <text x="410" y="210" text-anchor="middle" fill="#172B4D" font-size="15" font-weight="600">Not recommended</text>
          </svg>
        </figure>
      </div>
      <div class="metric-row">
        <a class="metric" href="#/findings/participants"><div class="v">${STUDENTS.length}</div><div class="l">Participants</div><div class="s">Pseudonyms only</div></a>
        <a class="metric" href="#/explore/worksheets"><div class="v">${C.worksheets.length}</div><div class="l">Worksheets</div><div class="s">${num(schemaFields)} response fields</div></a>
        <a class="metric" href="#/explore/recordings"><div class="v">${num(F.length)}</div><div class="l">Frames listed</div><div class="s">${num(codedFrameCount)} with a behaviour label</div></a>
        <a class="metric" href="#/explore/logs"><div class="v">${num(logEvents)}</div><div class="l">Log events</div><div class="s">CODAP Arbor, 3 class days</div></a>
      </div>
      <h2>How the archive is organised</h2>
      <p class="span-line">Collected data describe what was gathered; Findings present what the analyses reveal.</p>
      <ol class="explore-path">
        <li><a href="#/collected"><span class="n">1</span><h3>Collected Data</h3><p>Explore the worksheets, screen-recording frames, platform logs, and other research materials.</p></a></li>
        <li><a href="#/methods"><span class="n">2</span><h3>Processing</h3><p>Learn how the collected materials were prepared, coded, and analysed.</p></a></li>
        <li><a href="#/findings"><span class="n">3</span><h3>Findings</h3><p>Explore the results, patterns, and interpretations derived from the data.</p></a></li>
        <li><a href="#/docs/technical"><span class="n">4</span><h3>Reference</h3><p>Consult documentation, definitions, and supporting resources.</p></a></li>
      </ol>
      <p class="small span-line">This is a recommended way to explore the archive. It is not a claim that every research task follows this sequence.</p>
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
    const pvOne = (k) => {
      const entries = Object.entries(params[k] || {});
      if (entries.length !== 1) return pv(k);
      const n = Number(entries[0][0]);
      if (!Number.isFinite(n)) return h(entries[0][0]);
      const shown = Number.isInteger(n) ? num(n) : String(n);
      return h(shown);
    };
    const tables = { ep: 0, codes: 0 };
    STUDENTS.forEach((s) => Object.values(C.episodes[s] || {}).forEach((e) => { tables.ep += (e.episodes || []).length; tables.codes += e.code_rows || 0; }));
    const linkedFrames = F.filter((f) => f.gx).length;
    const noExtracted = C.worksheets.filter((w) => STUDENTS.every((s) => !C.ws[s][w.code].ocr)).map((w) => w.code);
    const reportOnly = STUDENTS.filter((s) => C.notebooks[s] && !C.notebooks[s].file && C.notebooks[s].extraction);
    const missingAnswers = noExtracted.length
      ? ` ${noExtracted.map(h).join(" and ")} ${noExtracted.length === 1 ? "has" : "have"} no extracted student answers, so ${noExtracted.length === 1 ? "it is" : "they are"} not scored evidence.`
      : "";
    const recorded = allSessions.filter((r) => r.manifest);
    const unrecorded = allSessions.filter((r) => !r.manifest);
    const slotName = (r) => `${h(r.student)} (${h(SESS_NAME[r.session])})`;
    const modeCount = (mode) => recorded.filter((r) => r.manifest.extraction_mode === mode);
    const speechOn = modeCount("full_multimodal");
    const motionOnly = modeCount("motion_only_fallback");
    const speechStatus = (status) => recorded.filter((r) => r.speech && r.speech.status === status);
    const pipeField = (r, key) => {
      const pipeline = r.speech && r.speech.pipeline;
      return pipeline && typeof pipeline === "object" ? (pipeline[key] || "") : "";
    };
    const asrOf = (r) => pipeField(r, "asr");
    const fusionSessions = speechStatus("ok").filter((r) => asrOf(r) === "existing_transcript_fusion");
    const smallAsr = recorded.filter((r) => asrOf(r) === "small");
    const lexical = recorded.filter((r) => r.speech && r.speech.method === "hybrid_matrix_duration_and_lexical");
    const postProcessed = recorded.filter((r) => r.coding && r.coding.post_processing);
    const logCsvUsed = recorded.filter((r) => r.coding && r.coding.log_csv_used);
    const votatMissing = recorded.filter((r) => !r.votat);
    const tally = (key) => {
      const out = {};
      F.forEach((row) => { if (row[key]) out[row[key]] = (out[row[key]] || 0) + 1; });
      return Object.entries(out).sort((a, b) => b[1] - a[1]);
    };
    const screenCounts = tally("sc");
    const phaseCounts = tally("ph");
    const behN = (code) => F.filter((row) => row.b === code).length;
    const actions = C.logs.action_types || {};
    const actionNames = Object.keys(actions).sort();
    const epCats = {};
    const decisions = {};
    let epFiles = 0;
    let epWithoutRecording = 0;
    let featureFlagsTrue = 0;
    STUDENTS.forEach((s) => Object.entries(C.episodes[s] || {}).forEach(([sid, e]) => {
      epFiles += 1;
      if (!(C.sessions[s][sid] && C.sessions[s][sid].manifest)) epWithoutRecording += 1;
      (e.episodes || []).forEach((ep) => { if (ep.category) epCats[ep.category] = (epCats[ep.category] || 0) + 1; });
      Object.entries(e.code_decisions || {}).forEach(([k, n]) => { decisions[k] = (decisions[k] || 0) + n; });
      featureFlagsTrue += (e.features_true || []).length;
    }));
    const resolutions = {};
    recorded.forEach((r) => {
      const res = r.manifest.native_resolution;
      const key = Array.isArray(res) ? res.join("×") : "not stored";
      resolutions[key] = (resolutions[key] || 0) + 1;
    });
    const resolutionText = Object.entries(resolutions).map(([k, n]) => `${h(k)} (${num(n)} manifests)`).join(", ");
    const dupeNames = recorded.filter((r) => r.same_video_file_as).map(slotName);
    const slotOf = (student, session) => allSessions.find((r) => r.student === student && r.session === session);
    const sessionFileNote = () => {
      const bits = [];
      const irma1 = slotOf("Irma", "codap_21apr");
      const irma2 = slotOf("Irma", "codap_28apr");
      if (irma1 && irma2 && irma1.video_sha256 && irma2.video_sha256 && irma1.video_sha256 !== irma2.video_sha256) {
        bits.push(irma1.coding
          ? "Irma’s two CODAP recordings are different files."
          : "Irma’s two CODAP recordings are different files. Session 1 frames have no behaviour labels yet, so they are not included in behaviour shares.");
      }
      const zara1 = slotOf("Zara", "codap_21apr");
      const zara2 = slotOf("Zara", "codap_28apr");
      if (zara1 && zara1.manifest && zara2 && !zara2.manifest) {
        bits.push("Zara’s stored CODAP recording is session 1. No session 2 recording or frame manifest is published, and frames taken from the session 1 video are not shown as a second session.");
      }
      return bits.length ? bits.join(" ") + " " : "";
    };
    const linkMethods = {};
    F.forEach((row) => {
      const method = row.gx && row.gx.method;
      if (method) linkMethods[method] = (linkMethods[method] || 0) + 1;
    });
    const linkMethodText = Object.entries(linkMethods).map(([k, n]) => `<code>${h(k)}</code> (${num(n)})`).join(", ") || "none stored";

    const STAGE_PANELS = [
      { id: "collect", num: 1, title: "Collect", summary: "Gather all sources",
        what: "All four source types are brought together before any processing starts. Each file is inventoried, fingerprinted (SHA-256), and assigned to a student pseudonym. Instructor entries and real-name log rows are removed before further processing.",
        sources: ["Paper worksheets scanned to PDF", "Screen recording files from CODAP Arbor sessions", "CODAP Arbor interaction log files (CSV/JSON)", "Google Colab notebook files (.ipynb) from the final project"],
        output: "Raw source material, file-by-file. Each source is counted and assigned. Nothing is modified at this stage." },
      { id: "extract", num: 2, title: "Extract", summary: "Read handwriting, label frames, parse logs",
        what: "Extraction works differently for each source. A language model reads defined areas of each worksheet scan. The same model assigns a behaviour label to each selected recording frame. Python parses log lines directly and inspects notebook files cell by cell. The raw reading is always kept alongside any cleaned value.",
        sources: ["Worksheet scan areas → language model reads handwriting in pre-defined regions", "Recording frames → language model assigns one behaviour label per frame from the codebook", "Log files → Python groups events by student, session, and action type", "Notebook .ipynb files → Python reads cells, outputs, and execution counters"],
        output: `Extracted response values for every worksheet item; one behaviour label per coded frame; per-session log measures; notebook inspection records.` },
      { id: "check", num: 3, title: "Check", summary: "Compare with rubric, rule, or codebook",
        what: "What happens after extraction depends on the question type. Open answers are scored against a researcher-written rubric. Numeric or rule-based answers are checked by Python against a fixed criterion derived from the data. The two paths are not interchangeable, and the distinction is recorded in each worksheet’s pipeline field.",
        sources: ["Researcher-written rubric PDFs (criteria for open answers, partial credit where defined)", "11 food card reference values (deterministic checks for WS4–WS7)", "Titanic reference values (WS15 numeric comparisons, within 0.02)", "Behaviour codebook (nine codes, developed from earlier human coding, applied per frame)"],
        output: "Per-item check results with pass, fail, or no-verdict flags. Rubric scores include the rationale the model used. Behaviour codes include a confidence rating and any observation flags set." },
      { id: "analyse", num: 4, title: "Analyse", summary: "Organise records, keep source links",
        what: `Checked material is organised into structured JSON files. Each result stays tied to the file and rule that produced it. Aggregates are built from item-level records. ${num(schemaFields)} response fields are defined across ${C.worksheets.length} worksheets.`,
        sources: ["Extraction JSON files (one per student per worksheet)", "Frame manifests with coded labels (one per session)", "Log measure tables (per student per day)", "Notebook inspection records (one per student)"],
        output: "JSON files in students/ folders; per-session and per-student aggregate measures; the processed CSV tables (frames.csv, log_sessions.csv, worksheet_responses.csv) that power this site." },
      { id: "review", num: 5, title: "Review", summary: "Inspect uncertain cases",
        what: "Uncertain items need a researcher. A correction is logged only when the underlying record supports the change. The archive labels everything as automated and does not record a separate decision for each answer or frame.",
        sources: ["Items flagged at low confidence or with a contradiction note", "Audit trail files documenting researcher-confirmed corrections", "Data Quality and Limitations page listing known gaps and limitations"],
        output: "Researcher-confirmed corrections with logged rationale; uncertainty flags preserved in output files; documented limitations accessible from the data notes page." },
    ];

    const stageButtons = STAGE_PANELS.map((s, i) =>
      `<button role="tab" class="process-step" data-stage="${h(s.id)}" aria-selected="${i === 0 ? "true" : "false"}" aria-controls="process-panel-${h(s.id)}" id="pstep-${h(s.id)}" tabindex="${i === 0 ? "0" : "-1"}"><span class="ps-num" aria-hidden="true">${s.num}</span><span class="ps-title">${h(s.title)}</span><span class="ps-summary">${h(s.summary)}</span></button>`
    ).join("");

    const stagePanels = STAGE_PANELS.map((s, i) =>
      `<div class="process-panel" id="process-panel-${h(s.id)}" role="tabpanel" aria-labelledby="pstep-${h(s.id)}" data-stage="${h(s.id)}"${i !== 0 ? " hidden" : ""}><p>${h(s.what)}</p><div class="process-panel-grid"><div class="process-panel-col"><h4>Sources at this stage</h4><ul>${s.sources.map((src) => `<li>${h(src)}</li>`).join("")}</ul></div><div class="process-panel-col"><div class="process-output"><b>Output</b><br>${h(s.output)}</div></div></div></div>`
    ).join("");

    return `<div class="page methods">
      ${crumbs([["Data processing and analysis", "#/methods"], ["Processing workflow"]])}
      <p class="kicker">Data processing and analysis</p>
      <h1>From Student Activity to Research Evidence</h1>
      <p class="lead">Written work, screen recordings, platform logs, and notebooks each show a different part of how the students learned decision trees.</p>
      <nav class="section-nav" aria-label="On this page">
        <a href="#/methods/idea" data-sec="idea">Processing</a>
        <a href="#/methods/worksheets" data-sec="worksheets">Worksheets</a>
        <a href="#/methods/recordings" data-sec="recordings">Recordings</a>
        <a href="#/methods/logs" data-sec="logs">Logs</a>
        <a href="#/methods/notebooks" data-sec="notebooks">Notebooks</a>
        <a href="#/methods/review" data-sec="review">Quality checks</a>
      </nav>

      <section class="method-block" id="m-idea">
        <h2>How the processing works</h2>
        <p>Select a stage to see what it does, which sources are involved, and what it produces.</p>
        <div class="process-nav" id="processNav">
          <div class="process-steps" role="tablist" aria-label="Processing stages">${stageButtons}</div>
          ${stagePanels}
        </div>
        <p class="small">A language model reads handwriting and what is visible on screen. Python reads the logs and notebooks and applies a rule wherever a value can be tested. An original reading is kept beside a cleaned value when both are stored.</p>
      </section>

      <section class="method-block" id="m-worksheets">
        <h2>Worksheets</h2>
        <p>Students completed ${C.worksheets.length} paper worksheets. The answers include words, numbers, operators such as ≤, decision-tree drawings, calculations, and survey responses.</p>
        <div class="method-flow" aria-label="Worksheet processing pipeline" role="img">
          <div class="flow-node flow-node--accent">Scanned<br>worksheet</div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node">Answer<br>extraction</div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node">Check<br><span class="flow-node-sub">rubric or rule</span></div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node flow-node--output">Scored<br>evidence</div>
        </div>
        <p>Each scan was divided into known answer areas. A language model read the handwriting in those areas. The raw reading is kept. Mechanical clean-up, such as storing <code>&lt;=</code> as ≤, is recorded separately.</p>
        <div class="compare">
          <div>
            <h3>Rubric-based scoring</h3>
            <p>The model compares the answer with criteria from the researcher’s rubric. The rubric sets the score. Python adds the item scores. Partial credit is possible where the rubric defines it.</p>
          </div>
          <div>
            <h3>Rule-based checking</h3>
            <p>After the handwriting is read, Python checks a value or relationship, such as a threshold, a count, or an error rate, against a fixed rule derived from the data.</p>
          </div>
        </div>
        <p>These records show what was written and how it compares with a rubric or rule. They do not show what a student was thinking.${missingAnswers}</p>
        ${tech("Which worksheets use which method?", table([{ t: "Worksheets" }, { t: "Reading" }, { t: "Check" }], [
          { cells: ["WS1, WS3, WS4", "Model reads handwriting", "Model scores each item against the rubric. Python sums the scores."] },
          { cells: ["WS5, WS6, WS7", "Model reads handwriting", "Python rules from the 11 food cards. WS7 is checked against the tree that student drew on WS6."] },
          { cells: ["WS10", "Model reads handwriting", "Python rules for the energy-threshold table. Not the Titanic worksheet (WS15)."] },
          { cells: ["WS13", "Model reads the answers", "Rubric scoring. Log measures are attached only when that student’s log exists."] },
          { cells: ["WS14", "Model reads the answers", "Rubric for open answers. Python checks that the four counts sum to N and that false positives and false negatives are zero."] },
          { cells: ["WS15", "Model reads the answers", "Rubric for open answers. Python compares numbers with the Titanic reference, within 0.02."] },
          { cells: ["WS11", noExtracted.includes("WS11") ? "Not extracted" : "Model reads the answers", "A checker exists for some closed survey items. This worksheet is not treated as a validated response set" + (noExtracted.includes("WS11") ? " because no student answers were extracted." : ".")] },
          { cells: ["WS12", "Read from the scanned sheet", "Consistency checks. The rubric says there is no single correct tree."] },
        ]) + `<p class="small">For a rubric item, the scorer loads the entry with that item’s ID. It does not search across documents.</p>` + (rawEx ? `<p class="small">Clean-up example: in ${h(rawEx.s)}’s ${h(rawEx.code)}, the raw reading <code>${h(rawEx.d.raw)}</code> was stored as <code>${h(rawEx.d.normalized)}</code>.</p>` : "") + (checkEx ? `<p class="small">WS10 check example: ${h(checkEx.s)} wrote <code>${h(checkEx.v)}</code> for the chosen threshold. Result: ${result(checkEx.chk.correct)}.</p>` : "") + `<p class="small">WS14 and WS15 were split from an earlier combined worksheet. They are checked separately. The survey worksheet WS11 has a checker for some closed items, but the item identifiers in that checker have drifted from the rubric, so it is not treated as a validated response set.</p>`)}
      </section>

      <section class="method-block" id="m-recordings">
        <h2>Screen recordings</h2>
        <p>Students’ CODAP Arbor screens were recorded under pseudonyms. This archive has a frame manifest for ${num(recorded.length)} of ${num(allSessions.length)} session slots. ${num(unrecorded.length)} slots have no manifest: ${unrecorded.map(slotName).join(", ")}. The inventory of source files lists these recordings as <code>.webm</code>. Every stored manifest gives the picture size as ${resolutionText}. The recorder program is not in this repository, so its codec settings, and whether each file is an uninterrupted session, are not verified here.</p>
        <div class="method-flow" aria-label="Implemented recording pipeline. Speech processing, frame selection, and behaviour coding are stored. A frame-level join to the log is not." role="img">
          <div class="flow-node flow-node--accent">Screen<br>recording</div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node">Speech and<br>frame selection</div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node">Behaviour<br>coding</div>
          <div class="flow-arr" aria-hidden="true">→</div>
          <div class="flow-node flow-node--output">Stored<br>labels</div>
        </div>
        <p>Three stages are stored: speech processing where a transcript exists, frame selection, and a behaviour label on the kept frames. A fourth stage, matching each log event to a frame, is described in the study method. The frame files do not contain that join. ${dupeNames.length ? `Some videos are the same file: ${dupeNames.join("; ")}. Only one file in each pair can be the recording of its day. ` : ""}${sessionFileNote()} Frames and counts are listed under <a href="#/explore/recordings">Screen recording frames</a>. Counts of the nine labels, with labelled frames as the denominator, are on the <a href="#/findings/recordings">screen recording findings</a> page.</p>

        <h3>Speech</h3>
        <p>${num(speechStatus("ok").length)} of the ${num(recorded.length)} recordings store a usable transcript. ${fusionSessions.length ? `${num(fusionSessions.length)} of those store speaker grouping as <code>${h(pipeField(fusionSessions[0], "diarization") || "not stored")}</code> and speech-to-text as <code>existing_transcript_fusion</code>: the words were joined to a transcript already on file. Whisper was not run on every recording.` : ""} ${lexical.length ? `${num(lexical.length)} files label speakers with <code>hybrid_matrix_duration_and_lexical</code>, a duration and word-pattern heuristic. The archive does not store a speaker-identification accuracy for that heuristic.` : ""}</p>
        <p>${num(speechStatus("no_speech").length)} recordings are marked <code>no_speech</code>. ${smallAsr.length ? `${smallAsr.map(slotName).join(", ")} ${smallAsr.length === 1 ? "is" : "are"} marked as a speech-enabled run, with speech-to-text field <code>small</code>, speech status <code>no_speech</code>, and ${smallAsr.map((r) => num((r.manifest.summary || {}).speech_anchor_count || 0)).join(", ")} speech anchor${smallAsr.length === 1 && ((smallAsr[0].manifest.summary || {}).speech_anchor_count || 0) === 1 ? "" : "s"}.` : ""} The frame-analysis files do not contain <code>argumentation_score</code>.</p>

        <h3>How a frame was kept</h3>
        <p>Motion is the share of pixels that still differ after each frame is turned to grayscale, narrowed to 960 pixels wide when the recording is wider, blurred with a 5×5 Gaussian kernel, and compared with the previous frame by Otsu’s threshold. It is not a raw pixel-difference ratio. The code default is 0.005. Every manifest stores <code>motion_threshold_fraction</code> ${pvOne("motion_threshold_fraction")} and <code>silent_motion_threshold</code> ${pvOne("silent_motion_threshold")}. The extractor uses ${pvOne("motion_threshold_fraction")} on the ${num(speechOn.length)} speech-enabled sessions and ${pvOne("silent_motion_threshold")} on the ${num(motionOnly.length)} <code>motion_only_fallback</code> sessions.</p>
        <p>If no frame has been kept for ${pvOne("codap_gap_fill_seconds")} seconds, one is saved anyway. The trigger is <code>codap_static_gap_fill</code> on a speech-enabled run and <code>silent_screen_gap_fill</code> on a motion-only run. A speech anchor more than ${pvOne("speech_gap_bypass_seconds")} seconds after the previous kept frame bypasses the duplicate filter. That bypass is not its own trigger. Every manifest also stores a cooldown of ${pvOne("cooldown_ms")} milliseconds and perceptual-hash duplicate removal at threshold ${pvOne("phash_threshold")}. The frame files do not record a check that each log action appears in a picture, or a later re-extraction when a picture was missing.${logCsvUsed.length ? "" : " No coding file records that a log CSV was used while the frames were labelled."}</p>

        <h3>Behaviour labels</h3>
        <p>${num(F.length)} frames are listed and ${num(codedFrameCount)} have a behaviour label. The nine codes below were developed from earlier human coding and then given to the model as a closed list. They name visible activity. They are not a measure of what the student understood, and a count of frames is not time spent. The coding prompt tells the model to prefer building a tree when two labels could fit. The stored counts do not follow that expectation: building a tree is on ${num(behN("BUILD_TREE"))} frames and comparing models is on ${num(behN("COMPARE_MODELS"))}. ${postProcessed.length ? `${num(postProcessed.length)} coding files record a later rule-based change to the label, including a rule that replaces EVALUATE_MODEL with COMPARE_MODELS when an iterative-refinement flag is set. The stored label is not always the model’s first output.` : ""}</p>
        <div class="code-grid">${BEHAV.map((b) => `<article class="code-card"><h3><span class="sw" style="background:var(${b[3]})"></span> ${h(b[1])}</h3><p><code>${h(b[0])}</code>. ${h(b[2])}.</p></article>`).join("")}</div>
        <p><code>SELECT_TARGET</code> is stored on ${num(behN("SELECT_TARGET"))} frames. The log contains ${num(actions.set_dependent_variable || 0)} <code>set_dependent_variable</code> events. A zero frame count does not show that students never chose a target. The prompt tells the model not to use <code>SELECT_TARGET</code> for an empty prediction box.</p>
        <p>The prompt allows the screen contexts TREE, GRAPH, TABLE, MIXED, and MENU. The stored frames use ${screenCounts.map(([k, n]) => `<code>${h(k)}</code> (${num(n)})`).join(", ")}. ${["GRAPH", "TABLE"].filter((k) => !screenCounts.some(([name]) => name === k)).length ? `${["GRAPH", "TABLE"].filter((k) => !screenCounts.some(([name]) => name === k)).map((k) => `<code>${h(k)}</code>`).join(" and ")} ${["GRAPH", "TABLE"].filter((k) => !screenCounts.some(([name]) => name === k)).length === 1 ? "does" : "do"} not appear.` : ""} <code>deepen_phase</code> is a label the model wrote beside the behaviour. It is not a validated stage of learning. Stored phases: ${phaseCounts.map(([k, n]) => `${h(k)} ${num(n)}`).join(", ")}.</p>
        <p><code>analysis_confidence</code> is the model’s own rating of that label. It is not classification accuracy. This archive does not contain a 2026 frame-by-frame human sign-off, a gold-standard accuracy, or a kappa coefficient. The codebook’s origin in earlier human coding is not a reliability result for this cohort.</p>

        <h3>Logs are separate</h3>
        <p>${num(linkedFrames)} frames link to a researcher observation step. The stored link methods are ${linkMethodText}. The heuristic places researcher steps in order across the frames. The files do not record a person checking each link. Those links are not log events. The frame files do not contain <code>synchronized_log_event</code>, a T1 or T2 evidence tier, or a nearest-frame match to a log event.</p>
        <p>The 2026 log contains ${num(actionNames.length)} action names: ${actionNames.map((name) => `<code>${h(name)}</code>`).join(", ")}. <code>change_dataset</code> is not one of them, so these logs do not record a dataset switch under that name. Between two consecutive <code>emit_tree_data</code> events, an interval counts as one-thing-at-a-time when the events between them include <code>drop_attribute</code> or <code>change_split_values</code>, but not both. The rate is the number of those intervals divided by the number of intervals, rounded to three decimals. Fewer than two emits makes the script return 0.0, and this site does not show that return value when no rate file is stored. ${votatMissing.length ? `No rate file is stored for ${votatMissing.map(slotName).join(" and ")}.` : "A rate file is stored for every session that has a manifest."} The rate describes the log. It does not prove a planned experiment.</p>
        <p>${C.logs.delete_events_present ? "Delete actions are present in the 2026 log." : "The 2026 log has no delete action, so recovery by deleting a tree and then choosing a different predictor cannot be calculated."} ${actions.refresh_tree ? `<code>refresh_tree</code> occurs ${num(actions.refresh_tree)} times. That action is not the missing deletion sequence.` : ""} The absence of a logged deletion does not show that a student never recovered outside the log.</p>

        <h3>Exported session tables</h3>
        <p>The pipeline also wrote three tables per session folder: session features, episodes, and episode process codes. ${num(epFiles)} CODAP session folders have those tables, including ${num(epWithoutRecording)} folders with no recording. The ${num(tables.ep)} episodes use ${Object.entries(epCats).sort((a, b) => b[1] - a[1]).map(([k, n]) => `${h(k)} (${num(n)})`).join(", ")}. Those categories are not the nine frame labels. Of the process-code rows, ${Object.entries(decisions).map(([k, n]) => `${num(n)} are <code>${h(k)}</code>`).join(", ") || "none are stored"}. ${featureFlagsTrue ? "" : "No session-feature flag whose name ends in <code>_present</code> is stored as true. "}These tables are not validated screen-recording results, and a row marked not observed is not evidence that the behaviour was seen.</p>
        <p>A frame is one visible moment. It is not elapsed time, and it is not a log event. ${dupeNames.length ? "Duplicate video files make session comparisons unreliable for those students. " : ""}Missing recordings are omitted rather than treated as empty sessions. Further limits are on <a href="#/docs/limitations">Data Quality and Limitations</a>.</p>
        ${tech("Technical details for majors", `<p class="small">Thresholds below are the values stored on the manifests, not the 0.005 default in <code>scripts/dynamic_video_analytics.py</code>. Motion uses <code>motion_change_fraction</code>: Otsu’s threshold on a blurred grayscale preview.</p>` + kv([
          ["Speech-enabled sessions", `${num(speechOn.length)} at 0.012`],
          ["Motion-only sessions", `${num(motionOnly.length)} at 0.008`],
          ["motion_threshold_fraction stored", pv("motion_threshold_fraction")],
          ["silent_motion_threshold stored", pv("silent_motion_threshold")],
          ["Gap fill (seconds)", pv("codap_gap_fill_seconds")],
          ["Speech-anchor duplicate bypass (seconds)", pv("speech_gap_bypass_seconds")],
          ["Cooldown (milliseconds)", pv("cooldown_ms")],
          ["Perceptual-hash threshold", pv("phash_threshold")],
        ]) + hbars(trigTotals, (k) => (TRIGGERS[k] || k).replace(/\.$/, ""), (k, v) => `<code>${h(k)}</code><br>${num(v)} frames`))}
      </section>

      <section class="method-block" id="m-logs">
        <h2>Platform logs</h2>
        <p>CODAP Arbor writes a time-stamped line each time the software records an action. ${num(logEvents)} events are in the archive. Python rules turn the lines into measures; no language model reads these files.</p>
        <div class="log-metrics">
          <div class="log-metric"><div class="lm-label">Measure</div><div class="lm-name">Model attempts</div><div class="lm-desc">Times the student submitted a tree’s results, with accuracy, depth, and confusion-matrix counts.</div></div>
          <div class="log-metric"><div class="lm-label">Measure</div><div class="lm-name">Time to first attempt</div><div class="lm-desc">Minutes from the first recorded action to the first tree submission.</div></div>
          <div class="log-metric"><div class="lm-label">Measure</div><div class="lm-name">Predictors tried</div><div class="lm-desc">Distinct variables placed into the tree across all attempts in the session.</div></div>
          <div class="log-metric"><div class="lm-label">Measure</div><div class="lm-name">VOTAT rate</div><div class="lm-desc">Share of steps between attempts where only the predictor or only the threshold changed. Describes the log; does not prove planned experimentation.</div></div>
        </div>
        <p>A measure cannot be calculated when the events it needs are missing. ${C.logs.delete_events_present ? "Delete actions are present, so rebuilding after a deletion can be counted." : "The 2026 logs contain no delete actions, so recovery by deleting a tree and rebuilding cannot be calculated."} That absence does not show what a student did outside the recorded events. Logs are not matched to individual screen frames.</p>
      </section>

      <section class="method-block" id="m-notebooks">
        <h2>Python notebooks</h2>
        <p>For the final project, students analysed lizard data in Google Colab. ${notebooksPresent} notebook files are in the archive.${reportOnly.length ? ` ${reportOnly.map(h).join(" and ")} submitted a report instead, so cell order and errors cannot be read for ${reportOnly.length === 1 ? "that file" : "those files"}.` : ""} This inspection is not the weekly Colab collection. Those files are listed under <a href="#/explore/notebooks">Python notebooks</a> and were not scored here.</p>
        <div class="nb-stages">
          <div class="nb-stage"><div class="nb-num">Inspected</div><div class="nb-name">Research questions</div><div class="nb-items">Whether research questions were written out for each target variable.</div></div>
          <div class="nb-stage"><div class="nb-num">Inspected</div><div class="nb-name">Tree models built</div><div class="nb-items">Count of decision trees, target variables, features used, and depths tried.</div></div>
          <div class="nb-stage"><div class="nb-num">Inspected</div><div class="nb-name">Train / test split</div><div class="nb-items">Whether the code contains a split between training and test data.</div></div>
          <div class="nb-stage"><div class="nb-num">Inspected</div><div class="nb-name">Cell execution</div><div class="nb-items">Which cells ran, in what order, and whether any printed an error output.</div></div>
          <div class="nb-stage"><div class="nb-num">Inspected</div><div class="nb-name">Revisiting earlier code</div><div class="nb-items">How many times the student went back and re-ran an earlier cell.</div></div>
        </div>
        <p>These notes describe what is in the file. They are not a grade. A missing step was not found; it does not show the student never considered it.</p>
        ${tech("Learning objectives and rubric", `<p class="small">In the study design, LO3.3.3 names the goal of posing one’s own questions and LO3.3.2 names changing tool settings such as tree depth. Those codes are learning goals. The notebook inspection records what is present; it does not assign them. Rubric section points are visible on each student’s notebook page.</p>`)}
      </section>

      <section class="method-block" id="m-review">
        <h2>Quality checks and limitations</h2>
        <p>Evidence quality varies across sources. The three columns below distinguish what is verified automatically, what still needs a researcher, and what is documented as incomplete or uncertain.</p>
        <div class="evidence-grid">
          <div class="evidence-col evidence-col--auto">
            <div class="evidence-col-head">Automated checks</div>
            <ul>
              <li>Rubric item scores and pass/fail flags generated per item</li>
              <li>Deterministic Python rules from food card and Titanic reference data</li>
              <li>WS14 confusion-matrix consistency (four counts sum to N; FP and FN zero)</li>
              <li>SHA-256 fingerprints for all source files</li>
              <li>Build-time test script that compares site values with source files</li>
            </ul>
          </div>
          <div class="evidence-col evidence-col--human">
            <div class="evidence-col-head">Researcher review</div>
            <ul>
              <li>Low-confidence or contradicted items reviewed individually</li>
              <li>Corrections logged only where the record supports the change</li>
              <li>WS5 B25 researcher overrides: rationale stored per student</li>
              <li>Rubric criteria written before scoring runs</li>
              <li>Behaviour codebook developed from earlier human-coded recordings</li>
            </ul>
          </div>
          <div class="evidence-col evidence-col--limit">
            <div class="evidence-col-head">Limitations and uncertainty</div>
            <ul>
              <li>WS11: no extracted student answers; not scored evidence</li>
              <li>Irma’s session 1 frames have no behaviour labels. Zara has no session 2 recording</li>
              <li>Frame coverage below 80% in some sessions</li>
              <li>Log–video alignment not recorded at the individual-frame level</li>
              <li>Episode categories are not the nine frame behaviour codes</li>
            </ul>
          </div>
        </div>
        <p>Written answers, screens, software events, and notebooks are different evidence. None is direct proof of what a student was thinking. Where a stage-score file disagrees with the extracted answers, the site shows the answers. Further limitations are in <a href="#/docs/limitations">Data Quality and Limitations</a>.</p>
        <p class="explore-next"><a href="#/explore/worksheets">Worksheets</a><a href="#/explore/recordings">Screen recording frames</a><a href="#/docs/technical">Technical documentation</a><a href="#/findings">Research findings</a></p>
      </section>
    </div>`;
  }

  let methodsOnScroll = null;
  function bindMethods() {
    if (methodsOnScroll) { window.removeEventListener("scroll", methodsOnScroll); methodsOnScroll = null; }
    const nav = document.querySelector(".section-nav");
    if (!nav) return;
    const links = [...nav.querySelectorAll("a[data-sec]")];
    const blocks = links.map((a) => document.getElementById("m-" + a.dataset.sec)).filter(Boolean);
    let shown = null;
    const setCurrent = (id) => {
      if (id === shown) return;
      shown = id;
      links.forEach((a) => {
        const on = a.dataset.sec === id;
        a.classList.toggle("active", on);
        if (on) a.setAttribute("aria-current", "true");
        else a.removeAttribute("aria-current");
      });
      const live = links.find((a) => a.dataset.sec === id);
      if (live && nav.scrollWidth > nav.clientWidth + 4) nav.scrollLeft = Math.max(0, live.offsetLeft - 8);
    };
    const pick = () => {
      const marker = 180;
      let id = "";
      for (const el of blocks) {
        if (el.getBoundingClientRect().top <= marker) id = el.id.slice(2);
      }
      if (!id) {
        const vis = blocks.find((el) => el.getBoundingClientRect().bottom > marker);
        id = vis ? vis.id.slice(2) : "";
      }
      setCurrent(id);
    };
    methodsOnScroll = pick;
    window.addEventListener("scroll", pick, { passive: true });
    pick();
    bindProcessNav();
  }

  function bindProcessNav() {
    const nav = document.getElementById("processNav");
    if (!nav) return;
    const steps = [...nav.querySelectorAll(".process-step[role='tab']")];
    const panels = [...nav.querySelectorAll(".process-panel[data-stage]")];
    function activate(id) {
      steps.forEach((btn) => {
        const on = btn.dataset.stage === id;
        btn.setAttribute("aria-selected", on ? "true" : "false");
        btn.tabIndex = on ? 0 : -1;
      });
      panels.forEach((panel) => { panel.hidden = panel.dataset.stage !== id; });
    }
    steps.forEach((btn) => {
      btn.addEventListener("click", () => { activate(btn.dataset.stage); btn.focus(); });
      btn.addEventListener("keydown", (e) => {
        const i = steps.indexOf(btn);
        if (e.key === "ArrowRight" || e.key === "ArrowDown") { e.preventDefault(); const n = steps[(i + 1) % steps.length]; activate(n.dataset.stage); n.focus(); }
        else if (e.key === "ArrowLeft" || e.key === "ArrowUp") { e.preventDefault(); const n = steps[(i - 1 + steps.length) % steps.length]; activate(n.dataset.stage); n.focus(); }
        else if (e.key === "Home") { e.preventDefault(); activate(steps[0].dataset.stage); steps[0].focus(); }
        else if (e.key === "End") { e.preventDefault(); activate(steps[steps.length - 1].dataset.stage); steps[steps.length - 1].focus(); }
      });
    });
  }

  // ------------------------------------------------------------------ 03 Explore
  function exploreShell(active, body) {
    return `<p class="kicker">Collected data</p>${body}`;
  }
  function pageStudents() {
    if (window.StudentProfiles) return window.StudentProfiles.page();
    return `<div class="page wide profile-page"><p class="kicker">Findings</p><h1>Student profiles</h1><p>The profile summary did not load.</p></div>`;
  }

  // ---- student: worksheets
  function wsBlock(s, w) {
    const r = C.ws[s][w.code], o = r.ocr, st = r.stage || {};
    const info = WS_INFO[w.code] || {};
    const fixed = w.fixed_responses || {};
    let status = "no answers on file", body = `<p class="small">${h(info.topic || "")} ${h(howChecked(w))} <a href="#/explore/worksheet/${h(w.code)}?view=student&student=${h(s)}&mode=response">Open in the worksheet explorer</a></p>`;
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
      const named = namesInText(o.snapshot, s);
      if (named.length) body += `<div class="warn">The model-written page summary also names ${named.map(h).join(", ")}. It is not a verified attribution.</div>`;
      const notes = [["Page summary written by the model", o.snapshot], ["Reading notes", o.page_notes], ["Check summary", o.system_summary]].filter((n) => n[1] && n[1] !== "(bos)");
      let t = "";
      if (o.raw_diff.length) t += `<h4>Raw reading vs. cleaned value</h4>` + table([{ t: "Field" }, { t: "Raw" }, { t: "Cleaned" }], o.raw_diff.map((d) => ({ cells: [h(fieldLabel(d.path)), `<code>${h(d.raw)}</code>`, `<code>${h(d.normalized)}</code>`] })));
      if (notes.length) t += `<h4>Model-written notes (Turkish, not translated)</h4>` + notes.map((n) => `<p><b class="small">${h(n[0])}</b><br><span class="orig">${h(n[1])}</span></p>`).join("");
      if (o.checks.some((c) => c.flag)) t += `<h4>Check flags</h4>` + table([{ t: "Check" }, { t: "Flag" }], o.checks.filter((c) => c.flag).map((c) => ({ cells: [h(checkLabel(c.check)), `<code>${h(c.flag)}</code>`] })));
      if (o.other_validation.length) t += `<h4>Other validation values</h4>` + table([{ t: "Field" }, { t: "Value" }], o.other_validation.map((v) => ({ cells: [h(fieldLabel(v.path)), h(v.value)] })));
      if (st.scoring) t += `<h4>Stage score file</h4>` + kv([["Total", `${num(st.scoring.total, 2)} of ${num(st.scoring.max, 2)}`], st.scoring.all_zero_with_zero_confidence && ["Note", "All items 0 with confidence 0. This file does not match the answers above."]]) + src(st.scoring.source);
      t += `<h4>Source</h4>` + src(o.source) + (o.raw_source ? src(o.raw_source) : "");
      body += tech("Technical details for majors", t);
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
    out += kv([["Length of the source recording", dur(lengthOf(r))], ["Frames listed", num(r.manifest.frames)], ["Frames with a behaviour label", cd ? num(cd.frames_coded) : "No"]]);
    if (window.StudentProfiles) out += window.StudentProfiles.sessionChart(s, ss.id);
    out += strip(s, ss.id, r);
    out += `<p><a class="btn" href="#/explore/recordings?s=${encodeURIComponent(s)}&ss=${encodeURIComponent(ss.id)}">View the frames from this session</a></p>`;
    // technical
    const m = r.manifest, sp = r.speech, ep = (C.episodes[s] || {})[ss.id];
    const SUM = { candidate_frames_considered: "Candidate frames considered", visual_duplicates_filtered: "Removed as near-duplicates", temporal_duplicates_filtered: "Removed as too close in time", non_task_screens_filtered: "Removed as unrelated screens", pruned_frames_removed: "Removed in a later clean-up", total_frames_extracted: "Frames kept" };
    let t = `<h4>How frames were selected</h4>` + kv(Object.entries(m.summary || {}).filter(([k]) => SUM[k]).map(([k, v]) => [SUM[k], num(v)])) +
      frameCountNote(s, ss.id, m, cd) +
      `<h4>Why each frame was taken</h4>` + hbars(m.triggers, (k) => (TRIGGERS[k] || k).replace(/\.$/, ""));
    if (cd) {
      t += kv([["Coding model", `<code>${h(cd.model || "–")}</code>`], ["Prompt", `<code>${h(cd.prompt_file || "–")}</code> ${h(cd.prompt_version || "")}`]]);
    }
    if (sp) t += `<h4>Speech</h4>` + kv([["Status", h(sp.status)], sp.role_counts && ["Speech segments by role", Object.entries(sp.role_counts).map(([k, v]) => `${h(k)} ${num(v)}`).join(", ")]]);
    if (ep && ep.episodes) t += `<h4>Episodes</h4>` + table([{ t: "Episode" }, { t: "Category" }, { t: "From" }, { t: "To" }, { t: "Assistance" }], ep.episodes.map((e) => ({ cells: [h(e.id), h(e.category), clock(e.start_ms / 1000), clock(e.end_ms / 1000), h(e.assistance)] })));
    t += `<h4>Files</h4>` + kv([["Video", r.video_bytes ? `${bytes(r.video_bytes)}, ${lengthSrc(r)}` : "–"]]) + src(r.video_path) + src(m.source) + (cd ? src(cd.source) : "") + (sp ? src(sp.source) : "") + (ep ? src(ep.episodes_source) : "");
    out += tech("Technical details for majors", t);
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
    return `<svg class="profile-chart" viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Accuracy of each model attempt">${grid}<path d="${line}" fill="none" stroke="var(--accent)" stroke-width="2"/>${dots}<text x="${(L + W - R) / 2}" y="${H - 6}" text-anchor="middle" font-size="10.5" fill="var(--muted)">attempt 1 to ${emits.length} →</text></svg>`;
  }
  function logBlock(s) {
    const days = logDays[s] || {};
    if (!Object.keys(days).length) return `<p class="empty">No platform log for this student.</p>`;
    const preface = window.StudentProfiles ? window.StudentProfiles.logPreface(s) : "";
    return preface + Object.entries(LOG_DAYS).map(([d, meta]) => {
      const v = days[d];
      let out = `<section class="session"><h3>${h(meta.name)} <span class="small">${h(meta.date)}</span></h3>`;
      if (!v) return out + `<p class="empty">No class-session log is stored.</p></section>`;
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
      if (meta.ss && !vt) out += `<p class="small">No one-thing-at-a-time rate is stored for this session.</p>`;
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
    const weekly = ((window.NOTEBOOKS || {}).students || []).find((row) => row.pseudonym === s);
    const weeklySession = { "5 May": "Colab Session 1", "12 May": "Colab Session 2", "2 June": "Colab Session 3" }[weekly && weekly.stage] || "";
    const finalNb = ((window.NOTEBOOKS || {}).final || []).find((row) => row.pseudonym === s);
    let out = window.StudentProfiles ? window.StudentProfiles.notebookTable(s) : "";
    if (finalNb) out += `<p><a href="${h(finalNb.file)}" download>Download the final notebook</a></p>`;
    else if (!f && s === "Marco") out += `<p><a href="downloads/notebooks/final/Marco.pdf" download>Download the written report</a></p>`;
    if (weekly) out += `<p class="small">The guided Colab notebook is a different file${weeklySession ? `, from ${h(weeklySession)}` : ""}. <a href="${h(weekly.file)}" download>Download it</a>.</p>`;
    if (!f && e && !window.StudentProfiles) out += `<p><b>Written report.</b> Notebook cell counts are not available.</p>`;
    out += kv([
      f && ["Errors in the outputs", f.cells_with_error_output ? `Yes, in ${f.cells_with_error_output} cell${f.cells_with_error_output > 1 ? "s" : ""}` : "None"],
      f && ["Revisiting earlier code", f.order_reversals ? `${f.order_reversals} time${f.order_reversals > 1 ? "s" : ""}` : "Never"],
    ]);
    if (e && e.experiments.length) out += `<h4>Trees built</h4>` + table([{ t: "Target" }, { t: "Features used" }, { t: "Depths tried" }, { t: "Tree drawn" }], e.experiments.map((x) => ({ cells: [`<code>${h(x.target)}</code>`, `<span class="small">${h((x.features || []).join(", "))}</span>`, x.depth_min == null ? "–" : `${x.depth_min} to ${x.depth_max}`, yesno(x.checks.tree_visualized)] })));
    if (n.scoring) out += `<h4>Stored rubric points</h4><p class="small">Pipeline points. Not a reviewed grade.</p>` + table([{ t: "Section" }, { t: "Points", num: 1 }, { t: "Possible", num: 1 }], Object.entries(n.scoring.sections).map(([k, v]) => ({ cells: [h(k), num(v.awarded, 1), num(v.possible, 1)] })));
    let t = "";
    if (e) t += kv([
      ["Target variables", e.targets.map((t) => `<code>${h(t)}</code>`).join(" ")],
      ["Research questions written out", `${e.questions_written} of ${e.targets.length}`],
      ["Stored model count", num(e.models)],
    ]);
    if (f) t += `<h4>Analysis steps found</h4><ul class="checks">${Object.entries(f.uses).map(([k, v]) => `<li class="${v ? "on" : "off"}">${v ? "✓" : "✗"} ${h(NB_USES[k] || k)}</li>`).join("")}</ul>`;
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
    return out + tech("Technical details for majors", t) + `<p>${methodLink("notebooks")}</p>`;
  }

  function pageStudent(s, tab) {
    if (!STUDENTS.includes(s)) return `<div class="page"><p class="kicker">Findings</p><h1>Not found</h1><p>No participant with the pseudonym “${h(s)}”.</p><p><a href="#/findings/participants">Student profiles</a></p></div>`;
    tab = tab || "worksheets";
    const tabs = [["worksheets", "Worksheets"], ["recordings", "Frames"], ["logs", "Platform logs"], ["notebook", "Notebook"]];
    const i = STUDENTS.indexOf(s);
    let body = "";
    if (tab === "worksheets") body = C.worksheets.map((w) => wsBlock(s, w)).join("");
    if (tab === "recordings") body = (window.StudentProfiles ? window.StudentProfiles.framesNote() : "") + SESS.map((ss) => sessionBlock(s, ss)).join("");
    if (tab === "logs") body = logBlock(s);
    if (tab === "notebook") body = notebookBlock(s);
    const prev = i > 0 ? `<a href="#/explore/student/${h(STUDENTS[i - 1])}/${tab}">← ${h(STUDENTS[i - 1])}</a>` : "";
    const next = i < STUDENTS.length - 1 ? `<a href="#/explore/student/${h(STUDENTS[i + 1])}/${tab}">${h(STUDENTS[i + 1])} →</a>` : "";
    const evidence = window.StudentProfiles ? window.StudentProfiles.summary(s) : "";
    return `<div class="page wide profile-page"><p class="kicker">Findings</p>
      ${crumbs([["Findings", "#/findings"], ["Student profiles", "#/findings/participants"], [s]])}
      <h1>${h(s)}</h1>
      ${evidence}
      <nav class="tabs profile-tabs" aria-label="Participant sources">${tabs.map(([k, l]) => `<a href="#/explore/student/${h(s)}/${k}" class="${k === tab ? "active" : ""}">${l}</a>`).join("")}</nav>
      ${body}
      <p class="small pn">${prev}${prev && next ? " · " : ""}${next}</p></div>`;
  }

  // ---- cohort views
  const DOCS = window.WORKSHEET_DOCS || { worksheets: {}, overrides: [] };
  const OVERRIDE = {};
  (DOCS.overrides || []).forEach((o) => { OVERRIDE[`${o.student}|${o.worksheet}|${o.item}`] = o; });

  function docOf(code) { return (DOCS.worksheets || {})[code] || {}; }
  function crumbs(parts) {
    const last = parts.length - 1;
    return `<nav class="crumbs" aria-label="Breadcrumb">${parts.map((p, i) => {
      if (i === last) return `<span aria-current="page">${h(p[0])}</span>`;
      return `<a href="${h(p[1])}">${h(p[0])}</a><span aria-hidden="true">/</span>`;
    }).join("")}</nav>`;
  }
  function namesInText(text, self) {
    if (!text) return [];
    return STUDENTS.filter((n) => n !== self && new RegExp(`(?:^|[^A-Za-z])${n}(?:[^A-Za-z]|$)`).test(text));
  }
  function sameResponses(a, b) {
    if (!a || !b || a.responses.length !== b.responses.length) return false;
    const mb = new Map(b.responses.map((r) => [r.path, r.value]));
    return a.responses.every((r) => mb.has(r.path) && String(mb.get(r.path)) === String(r.value));
  }
  const WS11_IS_WS14 = STUDENTS.every((s) => sameResponses(C.ws[s].WS11 && C.ws[s].WS11.ocr, C.ws[s].WS14 && C.ws[s].WS14.ocr));

  function isEmptyResponse(v) {
    return v == null || v === "" || v === "(bos)" || v === "(not_extracted)";
  }
  function responseState(v) {
    if (v == null || v === "") return { kind: "missing", text: "No value in the extraction" };
    if (v === "(bos)") return { kind: "blank", text: "Blank — the extraction records (bos)" };
    if (v === "(not_extracted)") return { kind: "missing", text: "Not extracted" };
    return { kind: "text", text: String(v) };
  }
  function answerKeyHref(w) {
    return w.answer_key_url || docOf(w.code).answer_key_url || "";
  }
  function scoreItemForGroup(code, groupId) {
    return (ITEM_ALIAS[code] || {})[groupId] || groupId;
  }
  function groupIdOf(code, response) {
    if ((code === "WS6" || code === "WS7") && response.item === "tree_structure") {
      const parts = response.path.split(".");
      return parts.length >= 2 ? `${parts[0]}.${parts[1]}` : response.item;
    }
    if (code === "WS7" && response.path.startsWith("rule_matching.")) return response.path;
    return response.item;
  }
  function itemTitle(code, id) {
    const it = rubricItem(code, id);
    if (it && it.label) return it.label;
    return rubricItemLabel(code, id, 80) || fieldLabel(id);
  }
  function fieldDisplay(code, path) {
    const fld = (docOf(code).fields || []).find((f) => f.field_id === path);
    if (fld && fld.location_hint) return fld.location_hint;
    return fieldLabel(path);
  }
  function groupLabel(code, id) {
    const it = rubricItem(code, id);
    if (it && (it.label || it.expected_answer || it.printed_question != null)) return itemTitle(code, id);
    return fieldDisplay(code, id);
  }
  function sortKey(code, id) {
    const rub = rubricItem(code, id);
    const family = id.startsWith("tree_structure") ? 0 : id.startsWith("rule_matching") ? 1 : id.startsWith("final_") ? 2 : 0;
    const printed = rub && rub.printed_question != null ? Number(rub.printed_question) : null;
    const numMatch = /(\d+)/.exec(id);
    const n = printed != null && !Number.isNaN(printed) ? printed : (numMatch ? Number(numMatch[1]) : 10000);
    return family * 100000 + n;
  }
  function explorerModel(code) {
    const seen = new Map();
    const responseGroups = [];
    STUDENTS.forEach((s) => {
      const o = C.ws[s][code] && C.ws[s][code].ocr;
      if (!o) return;
      o.responses.forEach((r) => {
        const id = groupIdOf(code, r);
        if (!seen.has(id)) {
          const g = { id, label: groupLabel(code, id), paths: [] };
          seen.set(id, g);
          responseGroups.push(g);
        }
        const g = seen.get(id);
        if (!g.paths.some((p) => p.path === r.path)) g.paths.push({ path: r.path, label: fieldDisplay(code, r.path) });
      });
    });
    responseGroups.sort((a, b) => sortKey(code, a.id) - sortKey(code, b.id) || a.id.localeCompare(b.id));
    const scoreIds = [];
    STUDENTS.forEach((s) => {
      const sc = C.ws[s][code] && C.ws[s][code].scoring;
      if (!sc) return;
      (sc.items || []).forEach((it) => { if (!scoreIds.includes(it.item)) scoreIds.push(it.item); });
    });
    const aligned = scoreIds.length > 0 && responseGroups.length > 0 && responseGroups.every((g) => scoreIds.includes(scoreItemForGroup(code, g.id)));
    return { responseGroups, scoreIds, aligned };
  }
  function wsHref(code, q) {
    const p = new URLSearchParams();
    ["view", "mode", "item", "student"].forEach((k) => { if (q[k]) p.set(k, q[k]); });
    const s = p.toString();
    return `#/explore/worksheet/${encodeURIComponent(code)}${s ? `?${s}` : ""}`;
  }
  function renderFields(student, code, group) {
    const o = C.ws[student][code].ocr;
    if (!o) return `<p class="missing-line">No extraction file for this student.</p>`;
    const rows = group.paths.map((p) => {
      const hits = o.responses.filter((r) => r.path === p.path);
      if (!hits.length) return `<dt>${h(p.label)}</dt><dd><p class="missing-line">Not in this extraction.</p></dd>`;
      return hits.map((r) => {
        const st = responseState(r.value);
        const body = st.kind === "text" ? `<p class="response-text">${h(st.text)}</p>` : `<p class="missing-line">${h(st.text)}</p>`;
        const dup = hits.length > 1 ? ` <span class="badge badge-flag">Duplicate record</span>` : "";
        return `<dt>${h(p.label)}${dup}</dt><dd>${body}</dd>`;
      }).join("");
    }).join("");
    return `<dl class="field-list">${rows}</dl>`;
  }
  function renderScore(student, code, itemId) {
    const ov = OVERRIDE[`${student}|${code}|${itemId}`];
    const rec = C.ws[student][code];
    const sc = rec.scoring;
    const stage = rec.stage && rec.stage.scoring;
    if (!sc) {
      if (stage && stage.all_zero_with_zero_confidence) {
        return `<p class="missing-line">A scoring file exists and gives every item 0 with confidence 0. Those numbers are not shown as scores.</p>${src(stage.source)}`;
      }
      if (stage) return `<p class="missing-line">A scoring file exists but is not in the published score table.</p>${stage.note ? `<p class="small">${h(stage.note)}</p>` : ""}${src(stage.source)}`;
      return `<p class="missing-line">No scoring file for this student.</p>`;
    }
    const it = (sc.items || []).find((i) => i.item === itemId);
    if (!it) return `<p class="missing-line">This item is not in the published scoring file.</p>`;
    let badge = `<span class="badge">Automated preliminary score</span>`;
    let note = `<p class="small">Produced by the scoring pipeline. A researcher decision is not recorded for this item.</p>`;
    if (it.review) {
      badge = `<span class="badge badge-flag">Automated score, flagged for review</span>`;
      note = `<p class="small">The review flag means the pipeline asked for a person to check this item. The file does not record a later human decision.</p>`;
    }
    if (ov) {
      badge = `<span class="badge">Researcher override recorded</span>`;
      note = `<p class="small">Override rationale, as stored: ${h(ov.rationale || "No rationale text in the file.")}</p>${src(ov.source)}`;
    }
    const rubricMax = rubricItem(code, itemId) && rubricItem(code, itemId).max_score;
    const maxShown = it.max_score != null ? it.max_score : rubricMax;
    const max = maxShown == null ? "" : ` of ${h(maxShown)}`;
    const conf = it.confidence == null ? "" : ` <span class="small">confidence ${h(it.confidence)}</span>`;
    return `<p>${badge} <strong>${h(it.score)}${max}</strong>${conf}</p>${note}`;
  }
  function renderTotal(student, code) {
    const sc = C.ws[student][code].scoring;
    if (!sc || sc.total_score == null) return "";
    return `<p class="small">Stored total ${h(sc.total_score)} of ${h(sc.max_score)}. Copied from the scoring file and not recalculated here.</p>${src(sc.source)}`;
  }
  function checkLine(student, code, groupId) {
    const o = C.ws[student][code].ocr;
    if (!o) return "";
    const id = scoreItemForGroup(code, groupId);
    const c = o.checks.find((x) => x.check === `item_checks.${id}` || x.check === id || x.check === `item_checks.${groupId}` || x.check === groupId);
    if (!c) return "";
    const verdict = c.correct === true ? "records this as correct" : c.correct === false ? "records this as not correct" : "records no verdict";
    const flag = c.flag ? ` Flag: ${h(c.flag)}.` : "";
    return `<p class="small">Automated check ${verdict}.${flag} This is the pipeline check, not a researcher-reviewed decision.</p>`;
  }
  function studentHead(student) {
    return `<header><h3><a href="#/explore/student/${h(student)}">${h(student)}</a></h3><a class="small" href="#/explore/student/${h(student)}/worksheets">Student profile</a></header>`;
  }

  function pageCollected() {
    const sessions = allSessions.filter((r) => r.manifest).length;
    return `<div class="page">${crumbs([["Collected data"]])}
      <p class="kicker">Collected data</p>
      <h1>Collected data</h1>
      <p class="lead">Material gathered from the ${STUDENTS.length} pre-service teachers in the decision-tree unit. Choose a category. Processing steps and research claims are in the other sections.</p>
      <div class="cat-grid">
        <a class="cat-card" href="#/explore/worksheets"><h3>Worksheets</h3><p>${C.worksheets.length} instructional worksheets. Open one for its blank file, answer key, and the scanned student submissions.</p></a>
        <a class="cat-card" href="#/explore/recordings"><h3>Screen recording frames</h3><p>${num(F.length)} frames extracted from the CODAP sessions. Previews on this site are a spaced subset. Original videos are not published.</p></a>
        <a class="cat-card" href="#/explore/logs"><h3>Platform logs</h3><p>${num(logEvents)} time-stamped CODAP Arbor actions. Logs are not matched to individual frames.</p></a>
        <a class="cat-card" href="#/explore/notebooks"><h3>Python notebooks</h3><p>The guided Colab notebook, the final homework, and the anonymised student files.</p></a>
      </div>
      <p class="small span-line">A worksheet response is not joined to a screen frame or a log event anywhere in the files this site reads.</p>
    </div>`;
  }
  function pageFindings() {
    const nOverride = (DOCS.overrides || []).length;
    return `<div class="page">${crumbs([["Findings and research insights"]])}
      <p class="kicker">Findings and research insights</p>
      <h1>Findings and research insights</h1>
      <p class="lead">This section is for results a researcher has reviewed and reported. No findings report is part of the site data, so this page does not state what students learned.</p>
      <h2>What is not published here</h2>
      <ul>
        <li>No competency levels, learning gains, or conclusions about the decision-tree unit.</li>
        <li>Counts on the overview describe the collection. They are not outcomes.</li>
        <li>Worksheet scores elsewhere on the site are pipeline outputs. A review flag means the pipeline asked for a person to look. It does not mean a person accepted the score.</li>
        <li>${nOverride ? `${nOverride} scoring items store a researcher override and a rationale. All of them are WS5 item WS5_B25. They are recorded adjustments to an automated score, not a finding about learning. <a href="#/explore/worksheet/WS5?view=compare&mode=score&item=WS5_B25">See them on worksheet 5</a>.` : "No researcher-override records were found in the scoring files."}</li>
      </ul>
      <h2>Where to read the evidence</h2>
      <ul class="ia-list">
        <li><a href="#/explore/worksheets">Collected worksheets</a><p>Responses, answer keys, and stored scores, labelled by how they were produced.</p></li>
        <li><a href="#/methods">Processing and analysis</a><p>How extraction, checks, and notebook inspection were done.</p></li>
        <li><a href="#/docs/limitations">Data Quality and Limitations</a><p>Missing files, duplicate recordings, and places where the files disagree with the written method.</p></li>
      </ul>
    </div>`;
  }

  const WS_GROUPS = [
    { label: "Conceptual foundations", codes: ["WS1"] },
    { label: "Manual classification", codes: ["WS3", "WS4", "WS5"] },
    { label: "Building decision trees", codes: ["WS6", "WS7", "WS10", "WS12"] },
    { label: "CODAP Arbor sessions", codes: ["WS13", "WS14", "WS15"] },
    { label: "Feedback survey", codes: ["WS11"] },
  ];
  function pipelineShort(w) {
    const policy = w.rubric_data && w.rubric_data.scoring_policy;
    if (policy && policy.basis === "internal_consistency") return "Consistency check";
    if (w.code === "WS11") return "Not used as scored evidence";
    if (w.pipeline === "deterministic") return "Rule-based check";
    return "Rubric scoring";
  }
  function catalogueTopic(code) {
    const info = WS_INFO[code] || {};
    if (info.topic) return info.topic;
    const note = docOf(code).schema_note || "";
    if (!note) return "";
    const cut = note.split(/\. (?=[A-Z])/)[0];
    return cut.endsWith(".") ? cut : `${cut}.`;
  }
  function extractedLabel(code) {
    const n = STUDENTS.filter((s) => C.ws[s][code].ocr).length;
    if (code === "WS11" && WS11_IS_WS14) return `${n} files, identical to WS14`;
    if (!n) return "No extraction files";
    const missing = STUDENTS.filter((s) => !C.ws[s][code].ocr);
    return missing.length ? `${n} of ${STUDENTS.length}; missing ${missing.join(", ")}` : `${n} of ${STUDENTS.length}`;
  }
  function pageWorksheets() {
    const groups = WS_GROUPS.map((g) => ({ label: g.label, codes: g.codes.filter((c) => C.worksheets.some((w) => w.code === c)) }));
    const listed = new Set(groups.flatMap((g) => g.codes));
    const rest = C.worksheets.map((w) => w.code).filter((c) => !listed.has(c));
    if (rest.length) groups.push({ label: "Other recorded worksheets", codes: rest });
    const body = groups.map((g) => {
      const cards = g.codes.map((code) => {
        const w = C.worksheets.find((x) => x.code === code);
        if (!w) return "";
        const topic = catalogueTopic(code);
        const blob = `${code} ${wsTitle(w)} ${topic} ${g.label}`.toLowerCase();
        return `<a class="ws-cat ws-card" href="#/explore/worksheet/${h(code)}" data-code="${h(code)}" data-group="${h(g.label)}" data-title="${h(blob)}"><b>${h(code)} · ${h(wsTitle(w))}</b><span>${h(topic)}</span></a>`;
      }).join("");
      return `<section class="ws-group" data-codes="${h(g.codes.join(","))}"><h2>${h(g.label)}</h2><div class="ws-catalogue">${cards}</div></section>`;
    }).join("");
    const chips = `<div class="ws-filters" role="group" aria-label="Filter by worksheet purpose">${["All"].concat(WS_GROUPS.map((g) => g.label)).map((label, i) =>
      `<button type="button" class="chip${i === 0 ? " on" : ""}" data-group="${i === 0 ? "" : h(label)}" aria-pressed="${i === 0 ? "true" : "false"}">${h(label)}</button>`).join("")}</div>`;
    return `<div class="page wide">${crumbs([["Collected data", "#/collected"], ["Worksheets"]])}
      ${exploreShell("worksheets", `
      <h1>Worksheets</h1>
      <p class="lead">${C.worksheets.length} worksheets. Search by code, title, or topic, then open a worksheet for its files and a short description.</p>
      <div class="ws-search-bar">
        <label class="sr-only" for="wsSearch">Search worksheets</label>
        <input type="search" id="wsSearch" placeholder="Search by code, title, or topic" autocomplete="off">
        <span class="ws-count" id="wsCount">${C.worksheets.length} worksheets</span>
      </div>
      ${chips}
      <div id="wsGroups">${body}</div>
      <p class="empty" id="wsEmpty" hidden>No worksheets match. Clear the search or choose All.</p>
      <p>${methodLink("worksheets")}</p>`)}</div>`;
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

  function loSection(code) {
    const mapping = docOf(code).mapping;
    if (!mapping) {
      return `<section class="section-block" id="objectives"><h2>Documented learning objectives</h2><p>No competency mapping file is in <code>mappings/</code> for ${h(code)}. Nothing on this page assigns a learning outcome.</p></section>`;
    }
    const by = {};
    Object.entries(mapping.items || {}).forEach(([id, arr]) => {
      (arr || []).forEach((x) => {
        if (!x.lo) return;
        (by[x.lo] = by[x.lo] || []).push(Object.assign({ id }, x));
      });
    });
    const rows = Object.entries(by).map(([lo, items]) => ({
      cells: [
        `<code>${h(lo)}</code>`,
        h(items.map((x) => x.expected_level).filter((v, i, a) => v && a.indexOf(v) === i).join(", ") || "–"),
        items.map((x) => `<p><code>${h(x.id)}</code> ${h(x.rationale || "")}</p>`).join(""),
      ],
    }));
    return `<section class="section-block" id="objectives"><h2>Documented learning objectives</h2>
      <p>From the competency mapping file. These lines say what an item was written to evidence. They are not scores, and they are not findings about what a student achieved.</p>
      ${mapping.framework ? `<p class="small">${h(mapping.framework)}</p>` : ""}
      ${table([{ t: "Mapped code" }, { t: "Mapped level in the file" }, { t: "Item note in the mapping" }], rows)}
      ${src(mapping.source)}</section>`;
  }
  function instructionsSection(code) {
    const doc = docOf(code);
    const questions = (doc.fields || []).filter((f) => f.question_tr);
    let q = "";
    if (questions.length) {
      q = table([{ t: "Field" }, { t: "Printed question recorded in the schema" }], questions.map((f) => ({
        cells: [`<code>${h(f.field_id)}</code>`, `<span class="orig">${h(f.question_tr)}</span>`],
      })));
    } else {
      q = `<p>The extraction schema does not store a separate transcription of the student-facing instructions. The wording handed out is the blank PDF, where that file is in the archive.</p>`;
    }
    const note = doc.schema_note ? `<h3>Extraction schema note</h3><p>${h(doc.schema_note)}</p>${src(doc.schema)}` : `<p class="missing-line">No extraction schema note is on file for this worksheet.</p>`;
    return `<section class="section-block" id="instructions"><h2>Purpose and instructions</h2>
      <p>${h((WS_INFO[code] || {}).topic || "No purpose statement is stored for this worksheet beyond its title.")}</p>
      ${note}${q}</section>`;
  }
  function pdfSection(code) {
    const doc = docOf(code);
    const file = doc.worksheet_pdf
      ? `<p><a href="${h(doc.worksheet_pdf)}" download>Download the blank worksheet PDF</a></p>`
      : `<p class="missing-line">No blank worksheet PDF is in the site downloads. The build report records it as missing when the source file was not in <code>mmla_explorer/materials/worksheets/</code>.</p>`;
    return `<section class="section-block" id="source-pdf"><h2>Original worksheet</h2>
      <p>This is the blank edition, where a file was copied into the site. Scanned student pages are not shown here.</p>
      ${file}</section>`;
  }
  function rubricSection(w) {
    const href = answerKeyHref(w);
    const policy = w.rubric_data && w.rubric_data.scoring_policy;
    const noKey = policy && policy.no_canonical_tree;
    const link = href
      ? (noKey
        ? `<p><a href="${h(href)}" download>Download the printed template PDF</a>. The rubric says scores are not compared with one correct tree.</p>`
        : `<p><a href="${h(href)}" download>Download the answer-key PDF</a></p>`)
      : (noKey
        ? `<p>The rubric records that there is no single correct tree, and no template PDF is on file.</p>`
        : `<p class="missing-line">No answer-key PDF is on file for this worksheet.</p>`);
    if (!(w.rubric_data && w.rubric_data.items)) {
      return `<section class="section-block" id="answer-key"><h2>Answer key and scoring rubric</h2>${link}<p class="missing-line">No rubric file was found for this worksheet, so scoring rules are not shown.</p></section>`;
    }
    const items = Object.entries(w.rubric_data.items);
    const consistency = items.some(([, item]) => item && (item.components || item.label) && !item.scoring_rules);
    const tableHtml = consistency
      ? table([{ t: "Item" }, { t: "What the rubric checks" }], items.map(([id, item]) => {
          const bits = []
            .concat(item.note ? [item.note] : [])
            .concat((item.components || []).map((c) => c.idea).filter(Boolean));
          return { cells: [`<b>${h(item.label || id)}</b><div class="small"><code>${h(id)}</code>${item.max_score == null ? "" : ` · max ${h(item.max_score)}`}</div>`, bits.map((b) => `<p>${h(b)}</p>`).join("") || `<span class="na">No criterion text in the file</span>`] };
        }))
      : table([{ t: "Item" }, { t: "Expected answer" }, { t: "Scoring rules" }], items.map(([id, item]) => {
          const q = rubricItemLabel(w.code, id, 72) || id;
          const rules = Object.entries(item.scoring_rules || {}).map(([score, rule]) => {
            const cond = typeof rule === "string" ? rule : (rule && rule.condition) || "";
            return `<li><b>${h(score)}</b> — ${h(cond)}</li>`;
          }).join("");
          return { cells: [`<b>${h(q)}</b><div class="small"><code>${h(id)}</code></div>`, h(item.expected_answer || ""), rules ? `<ul class="scoring-rules">${rules}</ul>` : `<span class="na">No rules in the file</span>`] };
        }));
    const intro = w.rubric_data.note ? `<p>${h(w.rubric_data.note)}</p>` : `<p class="small">Expected answers and scoring rules from the rubric file, in the file’s order. Text is shown as written, including Turkish.</p>`;
    return `<section class="section-block" id="answer-key"><h2>Answer key and scoring rubric</h2>
      ${link}
      ${intro}
      ${tableHtml}
      ${src(w.rubric)}</section>`;
  }
  function summarySection(code, model) {
    const withOcr = STUDENTS.filter((s) => C.ws[s][code].ocr);
    const without = STUDENTS.filter((s) => !C.ws[s][code].ocr);
    let values = 0, blanks = 0;
    withOcr.forEach((s) => C.ws[s][code].ocr.responses.forEach((r) => { values += 1; if (isEmptyResponse(r.value)) blanks += 1; }));
    const published = STUDENTS.filter((s) => C.ws[s][code].scoring);
    const totals = published.map((s) => C.ws[s][code].scoring).filter((sc) => typeof sc.total_score === "number");
    const maxes = [...new Set(totals.map((sc) => sc.max_score))];
    let range = "";
    if (totals.length && maxes.length === 1 && typeof maxes[0] === "number") {
      const nums = totals.map((sc) => sc.total_score);
      range = `<p>Stored automated totals for ${totals.length} student${totals.length === 1 ? "" : "s"} range from ${h(Math.min(...nums))} to ${h(Math.max(...nums))} out of ${h(maxes[0])}. Those totals are copied from the scoring files and were not recalculated. They are not a competency measure.</p>`;
    }
    const excluded = STUDENTS.filter((s) => !C.ws[s][code].scoring && C.ws[s][code].stage && C.ws[s][code].stage.scoring && C.ws[s][code].stage.scoring.all_zero_with_zero_confidence);
    const alignNote = model.scoreIds.length && !model.aligned
      ? `<p>Scoring item identifiers and extracted field identifiers are different for this worksheet, so scores are not placed on individual response fields. Both are shown, in separate views.</p>`
      : "";
    const buckets = new Map();
    withOcr.forEach((s) => {
      const sig = C.ws[s][code].ocr.responses.map((r) => `${r.path}\u0000${r.value}`).join("\n");
      if (!buckets.has(sig)) buckets.set(sig, []);
      buckets.get(sig).push(s);
    });
    const dupGroups = [...buckets.values()].filter((g) => g.length > 1);
    const dupNote = dupGroups.length ? `<p>Identical extracted values: ${dupGroups.map((g) => g.map(h).join(" and ")).join("; ")}.${(C.worksheets.find((x) => x.code === code).rubric_data || {}).scoring_policy && (C.worksheets.find((x) => x.code === code).rubric_data.scoring_policy.group_policy) ? ` The rubric says: ${h(C.worksheets.find((x) => x.code === code).rubric_data.scoring_policy.group_policy)}.` : ""}</p>` : "";
    return `<section class="section-block" id="summary"><h2>What can be counted</h2>
      <p>${withOcr.length} of ${STUDENTS.length} students have an extraction file.${without.length ? ` No extraction file: ${without.map(h).join(", ")}.` : ""} Of ${num(values)} extracted values in those files, ${num(blanks)} are blank, empty, or marked not extracted.</p>
      <p>${published.length ? `Published scoring files: ${published.length}.` : "No published scoring file."}${excluded.length ? ` ${excluded.length} scoring file${excluded.length === 1 ? " is" : "s are"} excluded because every item is 0 with confidence 0 (${excluded.map(h).join(", ")}).` : ""}</p>
      ${range}${alignNote}${dupNote}
      ${code === "WS11" && WS11_IS_WS14 ? `<div class="warn">For every student, the WS11 extraction values are identical to that student’s WS14 extraction. They are not counted above as WS11 survey answers. Read them on <a href="#/explore/worksheet/WS14">WS14</a>.</div>` : ""}
      </section>`;
  }
  function provenanceSection(w, model) {
    const code = w.code;
    const doc = docOf(code);
    const clashes = [];
    STUDENTS.forEach((s) => {
      const snap = C.ws[s][code].ocr && C.ws[s][code].ocr.snapshot;
      const others = namesInText(snap, s);
      if (others.length) clashes.push(`${s} (summary also names ${others.join(", ")})`);
    });
    const prohibit = doc.interpretation_prohibited === true
      ? `<p>The extraction schema sets <code>interpretation_prohibited</code>. The extracted text is not a competency judgement.</p>` : "";
    return `<section class="section-block" id="provenance"><h2>Data provenance</h2>
      ${prohibit}
      ${kv([
        ["How answers were checked", h(howChecked(w))],
        ["Pipeline label in the site data", `<code>${h(w.pipeline || "–")}</code>`],
        ["Response fields in the schema", w.fields_in_schema == null ? "–" : num(w.fields_in_schema)],
        ["Extracted field groups", num(model.responseGroups.length)],
        ["Published scoring items", model.scoreIds.length ? num(model.scoreIds.length) : "None"],
        ["Curriculum status in the schema", h(doc.curriculum_status || "Not recorded")],
      ])}
      ${code === "WS11" && WS11_IS_WS14 ? `<p>The extraction files under WS11 repeat WS14 for every student. Field counts above describe that repeated text, not a WS11 survey.</p>` : ""}
      ${clashes.length ? `<div class="warn">Model-written page summaries name a different pseudonym from the file for: ${clashes.map(h).join("; ")}. Those summaries are not treated as verified attributions, and they are not quoted here.</div>` : ""}
      <p>There is no verified join from a worksheet item to a screen recording or a CODAP log event. A pseudonym does link to that participant’s <a href="#/findings/participants">student profile</a>.</p>
      <p>${methodLink("worksheets", "Extraction and scoring methods")} <a href="#/docs/limitations">Data Quality and Limitations</a></p>
      ${tech("Source paths", [w.schema, w.rubric, w.answer_key || doc.answer_key, doc.schema].filter(Boolean).map(src).join(""))}</section>`;
  }
  function ws11ResponseSection() {
    const doc = docOf("WS11");
    const fields = doc.fields || [];
    const rows = fields.map((f) => ({
      cells: [
        `<code>${h(f.field_id)}</code>`,
        f.question_tr ? `<span class="orig">${h(f.question_tr)}</span>` : h(f.location_hint || "No printed question stored"),
        `<span class="missing-line">No extracted WS11 response</span>`,
      ],
    }));
    return `<section class="section-block" id="responses"><h2>Student responses</h2>
      <div class="warn">The WS11 extraction files repeat WS14. For all ${STUDENTS.length} students, every extracted path and value matches that student’s WS14 file. The WS11 rubric uses different item identifiers. Those files are not shown again here as survey answers. The WS14 responses are on <a href="#/explore/worksheet/WS14">the WS14 page</a>.</div>
      <p>Each schema field is listed so the missing WS11 responses stay visible. Published scoring files for WS11 are absent; stage score files that are all zeros with confidence 0 are not shown as scores.</p>
      ${fields.length ? table([{ t: "Schema field" }, { t: "What the schema records" }, { t: "Extraction" }], rows, { max: 520 }) : `<p class="missing-line">The extraction schema fields could not be loaded.</p>`}
      </section>`;
  }
  function responseExplorer(w, q) {
    const code = w.code;
    const model = explorerModel(code);
    const hasScores = model.scoreIds.length > 0;
    const view = q.view === "student" ? "student" : "compare";
    const mode = q.mode === "score" && hasScores ? "score" : "response";
    const items = mode === "score" && !model.aligned
      ? model.scoreIds.map((id) => ({ id, label: itemTitle(code, id), paths: [], scoreOnly: true }))
      : model.responseGroups;
    let item = q.item && items.some((g) => g.id === q.item) ? q.item : (items[0] && items[0].id);
    if (q.item && item !== q.item) item = items[0] && items[0].id;
    const student = STUDENTS.includes(q.student) ? q.student : (STUDENTS.find((s) => C.ws[s][code].ocr) || STUDENTS[0]);
    const base = { view, mode, item, student: view === "student" ? student : "" };
    const switcher = `<div class="view-switch">
      <div class="switch-set" role="group" aria-label="Response arrangement">
        <a href="${wsHref(code, Object.assign({}, base, { view: "compare", student: "" }))}" ${view === "compare" ? 'aria-current="true"' : ""}>Compare students</a>
        <a href="${wsHref(code, Object.assign({}, base, { view: "student" }))}" ${view === "student" ? 'aria-current="true"' : ""}>Inspect one student</a>
      </div>
      ${hasScores ? `<div class="switch-set" role="group" aria-label="Response or score">
        <a href="${wsHref(code, Object.assign({}, base, { mode: "response" }))}" ${mode === "response" ? 'aria-current="true"' : ""}>Responses</a>
        <a href="${wsHref(code, Object.assign({}, base, { mode: "score" }))}" ${mode === "score" ? 'aria-current="true"' : ""}>Scores</a>
      </div>` : `<span class="small">No published scores for this worksheet.</span>`}
    </div>`;
    const tools = `<div class="resp-tools">
      ${view === "student" ? `<label>Student<select id="respStudent" aria-label="Pseudonym">${STUDENTS.map((s) => `<option value="${h(s)}"${s === student ? " selected" : ""}>${h(s)}${C.ws[s][code].ocr ? "" : " — no extraction"}</option>`).join("")}</select></label>` : `<label>Filter students<input type="search" id="respFilter" placeholder="Pseudonym" autocomplete="off"></label><span class="small" id="respCount"></span>`}
    </div>`;
    let detail = "";
    if (!items.length) {
      detail = `<p class="empty">No extracted response fields are on file for this worksheet.</p>`;
    } else if (view === "compare") {
      const group = items.find((g) => g.id === item) || items[0];
      const nav = `<nav class="item-nav" aria-label="Worksheet items">${items.map((g) => `<a href="${wsHref(code, { view: "compare", mode, item: g.id })}"${g.id === group.id ? ' aria-current="true"' : ""}>${h(g.label)}</a>`).join("")}</nav>`;
      const scoreId = group.scoreOnly ? group.id : scoreItemForGroup(code, group.id);
      const blocks = STUDENTS.map((s) => `<article class="response-block" data-student="${h(s)}">${studentHead(s)}
          ${group.scoreOnly || mode === "score" ? "" : renderFields(s, code, group)}
          ${group.scoreOnly || mode === "score" ? "" : checkLine(s, code, group.id)}
          ${mode === "score" ? renderScore(s, code, scoreId) : ""}
        </article>`).join("");
      const align = mode === "score" && !model.aligned ? `<p class="small">These scoring identifiers are not the extracted field identifiers. The score is not attached to a response field.</p>` : "";
      detail = `<div class="resp-layout">${nav}<div>${align}${blocks}<p class="empty" id="respEmpty" hidden>No students match that pseudonym.</p></div></div>`;
    } else {
      const showScore = mode === "score";
      const blocks = items.map((g) => {
        const scoreId = g.scoreOnly ? g.id : scoreItemForGroup(code, g.id);
        return `<article class="response-block" id="item-${h(g.id)}"><h3>${h(g.label)}</h3>
          ${g.scoreOnly ? "" : renderFields(student, code, g)}
          ${g.scoreOnly ? "" : checkLine(student, code, g.id)}
          ${showScore ? renderScore(student, code, scoreId) : ""}
        </article>`;
      }).join("");
      const scoreTable = showScore && !model.aligned ? "" : "";
      detail = `${renderTotal(student, code)}${!model.aligned && showScore ? `<p class="small">Scores below use the scoring file’s item identifiers. They are not matched onto the extracted fields.</p>` : ""}${blocks}${scoreTable}`;
      if (showScore && !model.aligned) {
        const scoreBlocks = model.scoreIds.map((id) => `<article class="response-block"><h3>${h(itemTitle(code, id))}</h3><p class="small"><code>${h(id)}</code></p>${renderScore(student, code, id)}</article>`).join("");
        const responseBlocks = model.responseGroups.map((g) => `<article class="response-block"><h3>${h(g.label)}</h3>${renderFields(student, code, g)}</article>`).join("");
        detail = `${renderTotal(student, code)}<h3>Extracted responses</h3>${responseBlocks}<h3>Stored scores</h3><p class="small">These identifiers are not the extracted field identifiers, so the two lists are not joined.</p>${scoreBlocks}`;
      }
    }
    const knownSomewhere = q.item && (model.responseGroups.some((g) => g.id === q.item) || model.scoreIds.includes(q.item));
    const unknown = q.item && view === "compare" && !items.some((g) => g.id === q.item) && !knownSomewhere
      ? `<div class="warn">No item “${h(q.item)}” is in this worksheet. Showing the first item.</div>` : "";
    const badStudent = q.view === "student" && q.student && !STUDENTS.includes(q.student)
      ? `<div class="warn">No student with the pseudonym “${h(q.student)}”.</div>` : "";
    return `<section class="section-block" id="responses"><h2>Student responses</h2>
      <p>Compare one item across students, or read one student’s items in order. Response text is the extracted value, unchanged. Empty and missing values stay visible. Switch to scores only where a published scoring file exists.</p>
      ${!model.aligned && hasScores && mode === "response" ? `<p class="small">Scoring identifiers differ from the extracted fields on this worksheet. Use the scores view to read the stored scores beside the responses.</p>` : ""}
      ${unknown}${badStudent}${switcher}${tools}${detail}</section>`;
  }
  function bindRespFilter() {
    const sel = document.getElementById("respStudent");
    if (sel) {
      sel.addEventListener("change", () => {
        const hash = location.hash.replace(/^#\/?/, "");
        const [path, query] = hash.split("?");
        const p = new URLSearchParams(query || "");
        p.set("view", "student");
        p.set("student", sel.value);
        location.hash = `#/${path}?${p.toString()}`;
      });
    }
    const inp = document.getElementById("respFilter");
    if (!inp) return;
    const apply = () => {
      const q = inp.value.trim().toLowerCase();
      const rows = [...document.querySelectorAll("#responses [data-student]")];
      let shown = 0;
      rows.forEach((el) => {
        const ok = !q || (el.dataset.student || "").toLowerCase().includes(q);
        el.classList.toggle("ws-hidden", !ok);
        if (ok) shown += 1;
      });
      const c = document.getElementById("respCount");
      if (c) c.textContent = q ? `${shown} of ${rows.length} students` : `${rows.length} students`;
      const empty = document.getElementById("respEmpty");
      if (empty) empty.hidden = shown !== 0;
    };
    inp.addEventListener("input", apply);
  }
  function loBrief(code) {
    const mapping = docOf(code).mapping;
    if (!mapping || !mapping.items) return `<p class="small">No competency mapping file is on record for this worksheet.</p>`;
    const los = [];
    Object.values(mapping.items).forEach((arr) => (arr || []).forEach((x) => { if (x.lo && !los.includes(x.lo)) los.push(x.lo); }));
    if (!los.length) return "";
    return `<p class="small">Documented learning-objective codes: ${los.map((l) => `<code>${h(l)}</code>`).join(", ")}. These name what an item was written to evidence. They are not scores.</p>`;
  }
  function uniqueFiles(items) {
    const seen = new Set();
    return (items || []).filter((item) => {
      const key = item.sha256 || item.href;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }
  const FOOD_HEADERS = ["YİYECEK ADI", "ENERJİ (KCAL)", "YAĞ (G)", "DOYMUŞ YAĞ (G)", "KARBONHİDRAT (G)", "ŞEKER (G)", "PROTEİN (G)", "TUZ (G)", "ETİKET"];
  const FOOD_11_ROWS = [
    ["Salatalık", "12", "0.1", "0", "3.6", "1.7", "0.7", "0", "Tavsiye edilebilir"],
    ["Patates", "71", "0.1", "0", "15", "0.8", "1.7", "2", "Tavsiye edilebilir"],
    ["Elma", "52", "0.2", "0", "13.8", "11", "0.3", "0", "Tavsiye edilebilir"],
    ["Ahududu reçeli", "223", "0.2", "0", "52.2", "51.7", "0.7", "0", "Tavsiye edilemez"],
    ["Yulaf", "368", "7", "1.5", "58.7", "0.7", "13.5", "0", "Tavsiye edilebilir"],
    ["Jelibon", "343", "0.1", "0.1", "77", "46", "6.9", "0.1", "Tavsiye edilemez"],
    ["Avokado", "160", "13", "2.8", "2", "0.7", "1.5", "0.1", "Tavsiye edilebilir"],
    ["Sütlü çikolata", "530", "29.5", "17.5", "58.5", "57.5", "6.6", "0.2", "Tavsiye edilemez"],
    ["Kraker", "349", "3", "0.7", "61", "0.7", "12", "0.5", "Tavsiye edilebilir"],
    ["Patates kızartması", "289", "14", "1.3", "36", "0.3", "3.4", "0.7", "Tavsiye edilemez"],
    ["Patlamış mısır", "499", "23", "13.8", "57", "3.8", "10.7", "1.8", "Tavsiye edilemez"]
  ];
  const FOOD_EXTRA_ROWS = [
    ["Somun Ekmek", "271", "1.6", "0.5", "55", "1.2", "8", "1.7", "Tavsiye edilemez"],
    ["Vegan Salam", "345", "33", "23", "5.8", "1.6", "5.7", "1.6", "Tavsiye edilemez"]
  ];
  function foodTable(rows) {
    const head = `<tr>${FOOD_HEADERS.map((c) => `<th>${h(c)}</th>`).join("")}</tr>`;
    const body = rows.map((r) => `<tr>${r.map((c) => `<td>${h(c)}</td>`).join("")}</tr>`).join("");
    return `<div class="table-wrap"><table class="food-table"><thead>${head}</thead><tbody>${body}</tbody></table></div>`;
  }
  function foodDownload(href, title, size) {
    return `<ul class="file-list"><li class="file-item"><a href="${h(href)}" download="${h(href.split("/").pop())}">${h(title)}</a><span class="file-meta">CSV, UTF-8 · ${num(size)} bytes</span></li></ul>`;
  }
  function foodCardSection(code) {
    if (code === "WS4" || code === "WS5" || code === "WS6") {
      return `<section class="section-block" id="food-cards"><h2>Food card dataset</h2>
        <p>These are the 11 food cards for the task “search for the fat threshold that misclassifies the fewest cards.” The rows are the classroom set used to check worksheets 4 to 7. Names and nutrient values are copied from that source. The label is the Turkish class wording.</p>
        ${foodDownload("downloads/food_cards_11.csv", "11 food cards", 718)}
        ${foodTable(FOOD_11_ROWS)}
      </section>`;
    }
    if (code === "WS12") {
      return `<section class="section-block" id="food-cards"><h2>Extended food card dataset (13 cards)</h2>
        <p>Worksheet 12 uses the 11 food cards from Worksheets 4 and 5, plus Somun Ekmek and Vegan Salam. The extended dataset supports exploring two-level decision trees.</p>
        <p>Note: The original 11 cards cannot be perfectly separated by a single fat threshold. The original labels and card values have been preserved.</p>
        ${foodDownload("downloads/food_cards_13.csv", "13 food cards", 827)}
        ${foodTable(FOOD_11_ROWS.concat(FOOD_EXTRA_ROWS))}
      </section>`;
    }
    return "";
  }
  function fileList(items, empty) {
    const unique = uniqueFiles(items);
    if (!unique.length) return `<p class="missing-line">${empty}</p>`;
    return `<ul class="file-list">${unique.map((item) => {
      const groups = item.groups || [];
      const people = groups.reduce((n, g) => n + g.length, 0);
      const who = groups.length
        ? `<details class="file-who"><summary>${num(people)} pseudonym${people === 1 ? "" : "s"} in this file</summary><p>${groups.map((g) => g.map(h).join(" and ")).join(", ")}</p></details>`
        : "";
      return `<li class="file-item"><a href="${h(encodeURI(item.href))}" download="${h(item.download || "")}">${h(item.title)}</a><span class="file-meta">PDF · ${bytes(item.bytes)}</span>${who}</li>`;
    }).join("")}</ul>`;
  }
  function ws15Card(title, name, rows, role) {
    return `<article class="ws15-card">
      <h4>${h(title)}</h4>
      <code class="ws15-file">${h(name)}</code>
      <p class="ws15-role">${h(role)}</p>
      <div class="ws15-foot">
        <span class="ws15-meta">CSV · ${num(rows)} rows</span>
        <a class="btn-primary" href="downloads/ws15/${h(name)}" download="${h(name)}" aria-label="Download ${h(name)}">Download</a>
      </div>
    </article>`;
  }
  function ws15DatasetSection(code) {
    if (code !== "WS15") return "";
    return `<section class="section-block" id="ws15-data"><h2>WS15 dataset collection</h2>
      <p>These datasets were prepared specifically for Worksheet 15. Use the provided files for the activities rather than a generic Titanic dataset.</p>
      <h3>Training and test samples</h3>
      <p>Four files provide two separate training and test samples for the worksheet activities.</p>
      <div class="ws15-pair">
        <p class="ws15-pair-label">Sample 1</p>
        <div class="ws15-grid">
          ${ws15Card("Training Sample 1", "titanic_egitim_veri_seti1.csv", 812, "Use this file to build the first decision tree.")}
          ${ws15Card("Test Sample 1", "titanic_test_veri_seti1.csv", 231, "Use this file to check the first tree.")}
        </div>
      </div>
      <div class="ws15-pair">
        <p class="ws15-pair-label">Sample 2</p>
        <div class="ws15-grid">
          ${ws15Card("Training Sample 2", "titanic_egitim_veri_seti2.csv", 834, "Use this file to build the second decision tree.")}
          ${ws15Card("Test Sample 2", "titanic_test_veri_seti2.csv", 209, "Use this file to check the second tree.")}
        </div>
      </div>
      <details class="tech"><summary>Columns in these four files</summary><div class="tech-body">
        <p>The four files share the columns <code>survived</code>, <code>pclass</code>, <code>sex</code>, <code>age</code>, <code>fare</code>, <code>embarked</code>, and <code>sex_bin</code>. In these files, <code>sex_bin</code> is 1 for female passengers and 0 for male passengers.</p>
      </div></details>
      <article class="ws15-card ws15-full">
        <h3>Full Passenger Dataset</h3>
        <code class="ws15-file">titanic_veri_seti.csv</code>
        <p class="ws15-role">This file contains the full passenger records used in the final activity, where the data is randomly split into training and test groups.</p>
        <details class="tech"><summary>Columns in this file</summary><div class="tech-body">
          <p>This file does not use the same columns as the four samples. Its columns are <code>survived</code>, <code>pclass</code>, <code>name</code>, <code>sex</code>, <code>age</code>, <code>sibsp</code>, <code>parch</code>, <code>ticket</code>, <code>fare</code>, <code>cabin</code>, <code>embarked</code>, <code>boat</code>, <code>body</code>, and <code>homedest</code>.</p>
        </div></details>
        <div class="ws15-foot">
          <span class="ws15-meta">CSV · ${num(1326)} rows</span>
          <a class="btn-primary" href="downloads/ws15/titanic_veri_seti.csv" download="titanic_veri_seti.csv" aria-label="Download titanic_veri_seti.csv">Download</a>
        </div>
      </article>
    </section>`;
  }
  function pageWorksheet(code) {
    const w = C.worksheets.find((x) => x.code === code);
    if (!w) {
      return `<div class="page">${crumbs([["Collected data", "#/collected"], ["Worksheets", "#/explore/worksheets"], ["Not found"]])}
        <h1>Worksheet not found</h1><p>No worksheet with the code "${h(code)}" is in this archive.</p><p><a href="#/explore/worksheets">Back to the worksheets</a></p></div>`;
    }
    const info = WS_INFO[code] || {};
    const files = (window.WS_FILES && window.WS_FILES[code]) || { materials: [], completed: [] };
    const completed = uniqueFiles(files.completed);
    return `<div class="page wide">${crumbs([["Collected data", "#/collected"], ["Worksheets", "#/explore/worksheets"], [code]])}
      ${exploreShell("worksheets", `
      <h1>${h(code)} · ${h(wsTitle(w))}</h1>
      <section class="section-block" id="overview"><h2>Worksheet overview</h2>
        <p>${h(info.topic || "No purpose statement is stored for this worksheet.")}</p>
        ${loBrief(code)}
        <p class="small span-line">Extracted answers and item scores are not listed on this page. <a href="#/methods/worksheets">How worksheets were checked \u2192</a></p>
      </section>
      ${foodCardSection(code)}
      ${ws15DatasetSection(code)}
      <section class="section-block" id="materials"><h2>Worksheet materials</h2>
        <p class="small">Each distinct blank worksheet or answer key is listed once.</p>
        ${fileList(files.materials, "No blank worksheet or answer key could be matched to this worksheet.")}
      </section>
      <section class="section-block" id="completed"><h2>Completed student worksheets</h2>
        <p class="small span-line">${completed.length ? `${num(completed.length)} file${completed.length === 1 ? "" : "s"}. ` : ""}The original scans are shown as they were stored. Different students were not merged into a new PDF, and no dates are shown.</p>
        ${fileList(files.completed, "No completed student PDF is on record for this worksheet.")}
      </section>
      `)}</div>`;
  }

  const HF_FRAMES = "https://huggingface.co/datasets/dedemerve/DecisionTrees-AICFT-Frames";
  const HF_LOGS = "https://huggingface.co/datasets/dedemerve/DecisionTrees-AICFT-CODAP-Arbor-LogFile";
  const CODAP_SCREEN = new Set(["TREE", "GRAPH", "TABLE", "MIXED", "CODAP"]);
  const frameView = { s: "", ss: "" };
  const isCodapScreen = (f) => CODAP_SCREEN.has(f.sc);
  const PREVIEW_CAP = 12;
  const codapPreviews = (s, ss) => F.filter((f) => f.s === s && (!ss || f.ss === ss) && f.th && isCodapScreen(f));
  const sessionPreviews = (s, ss) => {
    const coded = codapPreviews(s, ss);
    if (coded.length) return coded;
    return F.filter((f) => f.s === s && (!ss || f.ss === ss) && f.th);
  };
  function previewSample(pics) {
    if (pics.length <= PREVIEW_CAP) return pics;
    const used = new Set();
    const picked = [];
    for (let i = 0; i < PREVIEW_CAP; i++) {
      let idx = Math.round((i * (pics.length - 1)) / (PREVIEW_CAP - 1));
      if (used.has(idx)) {
        for (let d = 1; d < pics.length; d++) {
          if (idx + d < pics.length && !used.has(idx + d)) { idx += d; break; }
          if (idx - d >= 0 && !used.has(idx - d)) { idx -= d; break; }
        }
      }
      used.add(idx);
      picked.push(idx);
    }
    picked.sort((a, b) => a - b);
    return picked.map((i) => pics[i]);
  }
  const sessionHasFrames = (s, ss) => !!(C.sessions[s] && C.sessions[s][ss] && C.sessions[s][ss].manifest);

  function firstSessionWithFrames(s) {
    const withPictures = SESS.find((ss) => sessionPreviews(s, ss.id).length);
    if (withPictures) return withPictures.id;
    const hit = SESS.find((ss) => sessionHasFrames(s, ss.id));
    return hit ? hit.id : (SESS[0] ? SESS[0].id : "");
  }
  function pageRecordings(q) {
    frameView.s = (q && q.s) || "";
    frameView.ss = (q && q.ss) || "";
    if (frameView.s && !frameView.ss) frameView.ss = firstSessionWithFrames(frameView.s);
    const sessionsWithFrames = allSessions.filter((r) => r.manifest).length;
    const storedPreviews = F.filter((f) => f.th).length;
    const shownPreviews = F.filter((f) => f.th && isCodapScreen(f)).length;
    const who = STUDENTS.map((s) => `<button type="button" class="person-card" data-who="${h(s)}" aria-pressed="false"><span class="person-name">${h(s)}</span></button>`).join("");
    return `<div class="page wide">${exploreShell("recordings", `
      ${crumbs([["Collected data", "#/collected"], ["Screen recording frames"]])}
      <h1>Screen recording frames</h1>
      <p class="lead">Still images from students working in CODAP Arbor. The original videos are not available for download.</p>
      <div class="stat-row">
        <div class="stat-card"><div class="v">${num(F.length)}</div><div class="l">Extracted frames</div></div>
        <div class="stat-card"><div class="v">${num(sessionsWithFrames)}</div><div class="l">Sessions with frames</div></div>
      </div>
      <p class="frame-note">Each session view shows up to 12 examples from the CODAP screen, spaced through that session. ${num(storedPreviews)} preview images are stored on this site, ${num(C.thumbs_per_session)} per session. ${num(shownPreviews)} of those are a table, graph, tree, or the CODAP window. Menus and other screens are not shown. A session whose frames have no stored screen type shows its previews without a behaviour label. The full set of frame images is in the dataset below.</p>

      <section class="section-block" id="frame-explore">
        <h2>Choose a participant</h2>
        <div class="person-grid" id="whoRow">${who}</div>
        <div id="frameOut"></div>
      </section>

      <section class="section-block" id="frame-dataset">
        <div class="dataset-card frame-dataset">
          <div class="ds-type">Complete dataset · CC BY 4.0</div>
          <div class="ds-title">All extracted frames on Hugging Face</div>
          <p class="ds-desc">The public dataset holds the frame images, <code>metadata.csv</code>, and <code>codap_log_anonymized.csv</code>. It does not include the original videos.</p>
          <div class="frame-actions">
            <a class="btn btn-primary frame-dataset-btn" href="${HF_FRAMES}" target="_blank" rel="noopener">Open the complete frame dataset</a>
            <a class="frame-method" href="#/methods/recordings">How these frames were chosen and labelled</a>
          </div>
        </div>
      </section>
      `)}</div>`;
  }
  function renderFrameBrowse() {
    const out = document.getElementById("frameOut");
    if (!out) return;
    document.querySelectorAll("#whoRow .person-card").forEach((b) => {
      const on = b.dataset.who === frameView.s;
      b.classList.toggle("on", on);
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
    if (!frameView.s) {
      out.innerHTML = `<p class="frame-prompt">Choose a participant, then a session, to see examples from the CODAP screen.</p>`;
      return;
    }
    if (!frameView.ss) frameView.ss = firstSessionWithFrames(frameView.s);
    const tabs = SESS.map((ss) => {
      const ready = sessionPreviews(frameView.s, ss.id).length > 0;
      const sub = !sessionHasFrames(frameView.s, ss.id) ? `${SESS_DATE[ss.id]} · No recording` : (ready ? SESS_DATE[ss.id] : `${SESS_DATE[ss.id]} · No previews`);
      return `<button type="button" role="tab" class="sess-tab" data-ss="${h(ss.id)}" aria-selected="${frameView.ss === ss.id ? "true" : "false"}"><span>${h(SESS_NAME[ss.id])}</span><span class="when">${h(sub)}</span></button>`;
    }).join("");
    const picsAll = sessionPreviews(frameView.s, frameView.ss);
    const pics = previewSample(picsAll);
    const other = SESS.find((ss) => ss.id !== frameView.ss && sessionPreviews(frameView.s, ss.id).length);
    const heading = `<h3 class="preview-heading">${h(frameView.s)} · ${h(SESS_NAME[frameView.ss])}</h3>`;
    const note = picsAll.length > PREVIEW_CAP ? `<p class="preview-note">12 examples from this session.</p>` : "";
    const emptyCopy = sessionHasFrames(frameView.s, frameView.ss)
      ? `No previews are available for ${h(frameView.s)}, ${h(SESS_NAME[frameView.ss])}.`
      : `No recording is stored for ${h(frameView.s)}, ${h(SESS_NAME[frameView.ss])}.`;
    const body = pics.length
      ? `${heading}${note}<div class="thumbs frame-grid">${pics.map((f) => {
          const capText = `${f.s} · ${SESS_NAME[f.ss]} · ${clock(f.t)} · ${f.b ? behLabel(f.b) : "No label"} · ${f.id}`;
          return `<figure><button type="button" class="thumb" data-zoom="thumbs/${h(f.th)}" data-cap="${h(capText)}"><img loading="lazy" src="thumbs/${h(f.th)}" alt="${h(capText)}"></button><figcaption><span class="mono">${clock(f.t)}</span><br>${h(f.b ? behLabel(f.b) : "No label")}</figcaption></figure>`;
        }).join("")}</div>`
      : `${heading}<div class="empty-session"><p>${emptyCopy}</p>${other ? `<button type="button" class="btn btn-primary" id="openOther" data-ss="${h(other.id)}">Open ${h(SESS_NAME[other.id])}</button>` : ""}</div>`;
    out.innerHTML = `<h2 class="sess-heading">Choose a session</h2><div class="sess-tabs" role="tablist">${tabs}</div>${body}`;
    out.querySelectorAll(".sess-tab").forEach((b) => {
      b.addEventListener("click", () => { frameView.ss = b.dataset.ss; syncFrameQuery(); });
    });
    const alt = document.getElementById("openOther");
    if (alt) alt.addEventListener("click", () => { frameView.ss = alt.dataset.ss; syncFrameQuery(); });
  }
  function syncFrameQuery() {
    const qs = [["s", frameView.s], ["ss", frameView.ss]].filter((x) => x[1]).map(([k, v]) => `${k}=${encodeURIComponent(v)}`).join("&");
    const next = "#/explore/recordings" + (qs ? "?" + qs : "");
    if (location.hash !== next && window.history && window.history.replaceState) window.history.replaceState(null, "", next);
    renderFrameBrowse();
  }
  function bindFrameBrowse() {
    document.querySelectorAll("#whoRow .person-card").forEach((b) => {
      b.addEventListener("click", () => {
        frameView.s = b.dataset.who;
        frameView.ss = firstSessionWithFrames(frameView.s);
        syncFrameQuery();
      });
    });
    renderFrameBrowse();
  }


  const LOG_SAMPLE = [
    ["Ulysses", "dragstart", "Protein (g)"],
    ["Nadia", "set_dependent_variable", "Column 1"],
    ["Irma", "change_split_values", "Tuz (g) < 0.92"],
    ["Marcus", "emit_tree_data", "Column 1 · accuracy 0.522"],
    ["Zara", "set_focus_node", "Şeker (g)"],
    ["Shana", "data_context_change", "moveAttribute"],
    ["Melinda", "drop_attribute", "Yağ (g)"],
    ["Marco", "swap_focus_split", "Oneri"],
    ["Bruno", "change_tree_type", "classification"],
    ["Isabel", "refresh_tree", "data"],
  ];
  function pageLogs() {
    const excludedByDay = C.logs.rows_excluded_unmatched_by_day || {};
    const sessionDates = Object.keys(LOG_DAYS);
    const sessionLabel = { "2026-04-21": "CODAP Session 1", "2026-04-28": "CODAP Session 2" };
    const publicCount = (d) => (C.logs.rows_by_day[d] || 0) - (excludedByDay[d] || 0);
    const publicRows = sum(sessionDates.map(publicCount));
    const publicSessionTable = table(
      [{ t: "Session" }, { t: "Records", num: 1 }],
      sessionDates.map((d) => ({ cells: [h(sessionLabel[d]), num(publicCount(d))] })).concat([{ cells: [h("Total"), num(publicRows)] }]),
      { cls: "log-dict log-counts" }
    );
    const sampleRows = LOG_SAMPLE.map(([who, code, detail]) => `<tr>
        <td data-label="Participant">${h(who)}</td>
        <td data-label="Action">${h(ACTION[code] || code)}</td>
        <td data-label="Action code"><code>${h(code)}</code></td>
        <td data-label="Detail">${h(detail)}</td>
      </tr>`).join("");
    return `<div class="page wide">${exploreShell("logs", `
      ${crumbs([["Collected data", "#/collected"], ["CODAP platform logs"]])}
      <h1>CODAP platform logs</h1>
      <p class="lead log-lead">Platform logs record participants’ actions in CODAP Arbor, helping researchers understand how they interact with the decision-tree activity.</p>
      <h2 class="log-sample-title">Example log records</h2>
      <p class="log-caption">Selected records from the complete dataset.</p>
      <div class="table-wrap log-sample-wrap"><table class="log-examples">
        <colgroup><col class="log-c-who"><col class="log-c-action"><col class="log-c-code"><col class="log-c-detail"></colgroup>
        <thead><tr><th>Participant</th><th>Action</th><th>Action code</th><th>Detail</th></tr></thead>
        <tbody>${sampleRows}</tbody>
      </table></div>
      <h2>Complete dataset</h2>
      <section class="section-block" id="log-dataset">
        <div class="dataset-card log-dataset">
          <div class="ds-type">CC BY 4.0</div>
          <div class="ds-title">Complete CODAP Arbor Platform Logs</div>
          <p class="ds-desc">Explore the complete dataset for CODAP session 1 and CODAP session 2.</p>
          <a class="btn btn-primary frame-dataset-btn" href="${HF_LOGS}" target="_blank" rel="noopener">Explore the dataset on Hugging Face</a>
        </div>
      </section>
      ${tech("Technical details for majors", `<div class="log-tech">
        <h3>Sessions and dataset overview</h3>
        <p class="log-note">The public platform-log dataset is organized into two CODAP sessions. Each record belongs to one of these sessions, allowing visitors to explore participants' actions across the two activities.</p>
        ${publicSessionTable}
        <p class="log-note-label">Public dataset</p>
        <p class="log-note">The public file is <code>codap_log_anonymized.csv</code>. It contains ${num(publicRows)} records organized into CODAP Session 1 and CODAP Session 2. The columns are <code>id</code>, <code>student_id</code>, <code>session</code>, <code>action</code>, <code>timestamp_ms</code>, and <code>parameters</code>. They identify each event, the pseudonymized participant, the session, the recorded action, the elapsed time, and the details stored with that action.</p>
        <h3>Data fields</h3>
        ${table([{ t: "Column" }, { t: "Meaning" }], [
          { cells: ["<code>id</code>", "Unique identifier for a recorded event."] },
          { cells: ["<code>student_id</code>", "Pseudonymized participant identifier."] },
          { cells: ["<code>session</code>", "Identifies CODAP Session 1 or CODAP Session 2."] },
          { cells: ["<code>action</code>", "Code describing the recorded action."] },
          { cells: ["<code>timestamp_ms</code>", "Elapsed time in milliseconds within the participant's session."] },
          { cells: ["<code>parameters</code>", "Additional details associated with the action, stored as text."] },
        ], { cls: "log-dict" })}
        <h3>Action codes</h3>
        ${table([{ t: "Action code" }, { t: "Meaning" }], Object.entries(ACTION).map(([k, label]) => ({ cells: [`<code>${h(k)}</code>`, h(label)] })), { cls: "log-dict log-codes" })}
      </div>`)}`)}</div>`;
  }
  function logFindingsSection() {
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
    const present = rows.filter((r) => !String(r.cells[2]).includes("no data"));
    const totalEmits = STUDENTS.reduce((t, s) => t + Object.entries(LOG_DAYS).reduce((a, [d]) => a + (((logDays[s] || {})[d] || {}).emit_count || 0), 0), 0);
    const accuracies = STUDENTS.flatMap((s) => Object.keys(LOG_DAYS).map((d) => (logDays[s] || {})[d]).map((v) => v && v.last_emit_accuracy).filter((v) => typeof v === "number"));
    const avgAcc = accuracies.length ? accuracies.reduce((a, b) => a + b, 0) / accuracies.length : null;
    const byStudent = STUDENTS.map((s) => Object.entries(LOG_DAYS).reduce((a, [d]) => a + (((logDays[s] || {})[d] || {}).emit_count || 0), 0));
    const maxEmits = byStudent.length ? Math.max(...byStudent) : 0;
    const sessionsWithData = STUDENTS.reduce((t, s) => t + Object.keys(LOG_DAYS).filter((d) => (logDays[s] || {})[d]).length, 0);
    const L = C.logs;
    return `<h2 id="log-summaries">Key findings</h2>
      <p>These counts cover CODAP session 1 and CODAP session 2 only. A log records actions in CODAP Arbor. It does not show what a participant understood.</p>
      <div class="log-metrics">
        <div class="log-metric"><div class="lm-label">Total model attempts</div><div class="lm-name">${num(totalEmits)}</div><div class="lm-desc">Both class sessions</div></div>
        <div class="log-metric"><div class="lm-label">Mean last accuracy</div><div class="lm-name">${avgAcc != null ? num(avgAcc * 100, 1) + "%" : "–"}</div><div class="lm-desc">Mean of each session's last recorded accuracy</div></div>
        <div class="log-metric"><div class="lm-label">Most attempts</div><div class="lm-name">${num(maxEmits)}</div><div class="lm-desc">One participant, both class sessions</div></div>
        <div class="log-metric"><div class="lm-label">Sessions with a log</div><div class="lm-name">${num(sessionsWithData)}</div><div class="lm-desc">Participant × class session</div></div>
      </div>
      <dl class="terms compact-terms"><dt>Model attempts</dt><dd>Times the participant submitted a tree's results.</dd><dt>Predictors tried</dt><dd>Different variables placed into the tree.</dd><dt>One thing at a time</dt><dd>Share of steps where only one setting changed between attempts. This describes the log. It does not prove a planned experiment.</dd></dl>
      <h2>Results</h2>
      <p>${num(present.length)} of ${num(rows.length)} participant–session pairs have a log for these two class days. “No data” means that pair has no stored log.</p>
      ${table([{ t: "Participant" }, { t: "Session" }, { t: "Model attempts", num: 1 }, { t: "Last accuracy", num: 1 }, { t: "Predictors tried", num: 1 }, { t: "One thing at a time", num: 1 }], rows)}
      <h2>Interpretation</h2>
      <p>The table describes recorded interaction with CODAP Arbor. Last accuracy is the accuracy stored on the last model submission in that session. It is not a test score, and it is not evidence that the participant understood the tree.</p>
      <p>${methodLink("logs", "What these measures mean")}</p>
      ${tech("Technical details for majors", `<p class="log-note">The site data also stores a 7 April 2026 log for some participants. That day is not one of the two published class sessions, so those rows are left out of the counts and the table above.</p>
        <h3>Actions stored with the log file</h3>
        <p class="log-note">These totals come from every matched row used to build the site log, including the 7 April rows. They are not limited to the two class sessions.</p>
        ${table([{ t: "Action" }, { t: "Event code" }, { t: "Count", num: 1 }], Object.entries(L.action_types).sort((a, b) => b[1] - a[1]).map(([k, n]) => ({ cells: [h(ACTION[k] || k), `<code>${h(k)}</code>`, num(n)] })))}`)}`;
  }
  function pageNotebooks() {
    const pack = window.NOTEBOOKS || { teacher: null, students: [], final: [] };
    const guided = (pack.students || []).slice().sort((a, b) => a.pseudonym.localeCompare(b.pseudonym));
    const finals = (pack.final || []).slice().sort((a, b) => a.pseudonym.localeCompare(b.pseudonym));
    const guidedMissing = STUDENTS.filter((s) => !guided.some((row) => row.pseudonym === s));
    const byFinal = {};
    finals.forEach((s) => { byFinal[s.pseudonym] = s; });
    const row = (name, href, label) => `<li><span class="nb-who">${h(name)}</span><a class="nb-dl" href="${h(href)}" download>${h(label)}</a></li>`;
    const guidedRows = guided.map((s) => row(s.pseudonym, s.file, "Download")).join("");
    const finalRows = STUDENTS.slice().sort((a, b) => a.localeCompare(b)).map((name) => {
      if (name === "Marco") return `<li><span class="nb-who">Marco</span><span class="nb-kind">PDF</span><a class="nb-dl" href="downloads/notebooks/final/Marco.pdf" download>Download</a></li>`;
      const file = byFinal[name];
      if (!file) return "";
      const kind = String(file.file).toLowerCase().endsWith(".ipynb") ? "Notebook" : "";
      return `<li><span class="nb-who">${h(name)}</span>${kind ? `<span class="nb-kind">${kind}</span>` : ""}<a class="nb-dl" href="${h(file.file)}" download>Download</a></li>`;
    }).join("");
    return `<div class="page wide nb-page">${exploreShell("notebooks", `
      ${crumbs([["Collected data", "#/collected"], ["Python notebooks"]])}
      <h1>Python notebooks: learning to build decision trees</h1>
      <p class="lead">These materials show how the class learned to build a decision tree in Python. The teacher notebook sets out the guided work. The final homework asks students to use that process on a new dataset.</p>
      <section class="nb-section">
        <h2>Learning sequence</h2>
        <p>The three sessions are stages of one guided notebook, not three separate assignments. Weekly student files follow this notebook, so they are not listed as the main collection.</p>
        <ol class="nb-seq">
          <li><span class="n">1</span><h3>Colab Session 1</h3><p class="nb-kicker">Python foundations and data exploration</p><p>Students write to the screen, use variables and lists, import the libraries, and load and inspect the food table.</p></li>
          <li><span class="n">2</span><h3>Colab Session 2</h3><p class="nb-kicker">Preparing data and building a decision tree</p><p>Students separate features from the recommendation label, split training and test rows, and fit a decision tree.</p></li>
          <li><span class="n">3</span><h3>Colab Session 3</h3><p class="nb-kicker">Exploring tree depth and evaluating performance</p><p>Students compare trees of different depths and look at training and test error, including overfitting.</p></li>
        </ol>
      </section>
      <section class="nb-section">
        <h2>Teacher instructions for the Colab learning sequence</h2>
        <div class="nb-pack">
          <div class="nb-pack-row">
            <div>
              <p>This is the teacher's guided notebook used across Colab Sessions 1, 2, and 3. It structures the progression from Python foundations and data exploration to decision-tree construction and model evaluation.</p>
            </div>
            ${pack.teacher ? `<a class="nb-dl" href="${h(pack.teacher)}" download>Download teacher instruction notebook</a>` : ""}
          </div>
        </div>
      </section>
      <section class="nb-section">
        <h2>Final homework: guided application</h2>
        <p>The final assignment asks students to apply their Python and decision-tree skills to the lizard dataset. Start with the homework instructions, then use the supplied dataset to complete the activities.</p>
        <div class="nb-pack">
          <div class="nb-pack-row">
            <div>
              <h3>Homework instructions</h3>
              <p>The step-by-step assignment. It uses the lizard dataset below.</p>
            </div>
            <a class="nb-dl" href="downloads/notebooks/homework/final_homework_instructions.pdf" download>Download homework instructions (PDF)</a>
          </div>
          <div class="nb-pack-row">
            <div>
              <h3>Dataset for this assignment</h3>
              <p>The CSV used in the homework. 320 rows and 7 columns.</p>
            </div>
            <a class="nb-dl" href="downloads/notebooks/homework/lizard_data.csv" download>Download lizard dataset (CSV)</a>
          </div>
        </div>
      </section>
      <section class="nb-section">
        <h2>Student submissions</h2>
        <p>These files are the students' own work. Names are replaced by pseudonyms.</p>
        <ul class="nb-files nb-cohort">${finalRows}</ul>
      </section>
      <details class="nb-more">
        <summary>Guided session notebooks</summary>
        <div class="nb-more-body">
          <p>The student notebooks follow the teacher's guided activities. Each student is represented by their most recent available notebook; earlier submissions are preserved separately.</p>
          ${guidedMissing.length ? `<p class="nb-muted">${guidedMissing.map(h).join(", ")}: no notebook was found in the three guided-session folders.</p>` : ""}
          <ul class="nb-files">${guidedRows}</ul>
        </div>
      </details>
      ${tech("Technical details for majors", `<div class="log-tech">
        <h3>Guided learning sequence</h3>
        <p class="log-note">The teacher notebook, used in Google Colab, starts with <code>print()</code>, variables, and lists. It then loads the food table, separates measurements from the recommendation label, fits a decision tree, and compares trees of different depths. A <strong>feature</strong> is a column the tree may use. The <strong>target</strong> is the label it is asked to predict. <strong>Training rows</strong> are used to grow the tree. <strong>Test rows</strong> are held back, so the score is not only a memory of the rows used to fit it.</p>
        <h3>Python tools and libraries</h3>
        <p class="log-note"><code>pandas</code> reads a table and selects columns. <code>matplotlib</code> draws charts and the tree. scikit-learn supplies <code>DecisionTreeClassifier</code>, which grows a tree of yes-or-no questions, and the tools that score it. <code>max_depth</code> limits how many questions the tree may ask.</p>
        <h3>Decision-tree workflow</h3>
        <p class="log-note">In the food notebook the target column is <code>Öneri</code>. The product name is left out of the features. The homework uses <code>lizard_data.csv</code> instead. Text columns are turned into 0 and 1 columns with <code>get_dummies</code>, because the tree compares numbers, not words. The instruction splits 80% of the rows for training and 20% for testing, and keeps each category in proportion (<code>stratify</code>). <strong>Misclassification rate</strong> is 1 minus accuracy: the share of rows the tree labels incorrectly. Students compare that rate on training rows and test rows as the tree gets deeper. A deeper tree can follow the training rows more closely and then do worse on rows it has not seen. The instruction does not name a best depth.</p>
        <h3>Final homework</h3>
        <p class="log-note">The written assignment asks students to inspect the lizard table, write at least three questions of their own, and build a separate tree for each question. A question should point at one column as the target. Worked examples in the document use habitat, and they also name species and sex as columns a question can use. Students then choose a depth, draw the tree, and answer in their own words about the three class settings (data cards, CODAP, and Python), the data, the model's errors, and where a decision tree is not enough. The supplied table is named <code>lizard_data.csv</code>. One code sample in the document types that name with a hyphen. Public notebook copies use pseudonyms. Student code and written answers were not rewritten. The food table is not in this archive.</p>
      </div>`)}
    `)}</div>`;
  }
  function bindNotebookSearch() {}


  // ------------------------------------------------------------------ 04 Documentation
  const docShell = (active, body) => {
    const labels = { limitations: "Data Quality and Limitations", glossary: "Glossary", technical: "Technical documentation" };
    const trail = active ? [["Reference and documentation", "#/docs/technical"], [labels[active] || "Documentation"]] : [["Reference and documentation"]];
    return `${crumbs(trail)}<p class="kicker">Reference and documentation</p>${body}`;
  };

  function siteTableDictionaries() {
    const DICT = {
      "frames.csv": [`One selected screen frame (${num(F.length)} rows)`, [["student", "Pseudonym"], ["session", "codap_21apr or codap_28apr"], ["frame_id", "Frame name within the session"], ["time_s", "Seconds from the start of the recording"], ["trigger", "Why the frame was selected"], ["pixel_change_pct", "Share of the screen that changed"], ["speaker_role", "Who was speaking at that moment, if known"], ["primary_behavior", "Observed behaviour (one of nine codes)"], ["secondary_behavior", "A second behaviour, if any"], ["screen_context", "Tree, graph, table, mixed or menu"], ["deepen_phase", "Setup, building, tuning, evaluating or idle"], ["confidence", "The coder's own confidence"]]],
      "worksheet_responses.csv": [`One extracted worksheet value (${num(responseRows)} rows)`, [["student", "Pseudonym"], ["worksheet", "WS1 to WS15"], ["item", "Question or blank ID"], ["field_path", "Exact position of the value in the extraction file"], ["extracted_value", "What the student wrote, as read and cleaned"], ["item_check_correct", "Result of the check: True, False or empty"], ["item_check_flag", "Short code describing an error, if any"], ["source_file", "Extraction file the value came from"]]],
      "log_sessions.csv": ["One student in one CODAP session", [["student", "Pseudonym"], ["date", "Session date"], ["events", "All recorded actions"], ["span_minutes", "Minutes from first to last action"], ["emit_count", "Model attempts"], ["minutes_to_first_emit", "Minutes to the first attempt"], ["last_emit_accuracy", "Accuracy of the last attempt (0 to 1)"], ["accuracy_sd", "Standard deviation of accuracy across attempts"], ["predictor_drops", "Predictor placements"], ["unique_attributes", "Different predictors tried"], ["emit_tree_data … data_context_change", "Counts of the six modelling actions"]]],
      "episodes.csv": ["One episode of a session (from the video pipeline's Parquet tables)", [["student", "Pseudonym"], ["session", "Session ID"], ["episode_id", "Episode within the session"], ["category", "Episode category"], ["start_ms / end_ms / duration_ms", "Timing in milliseconds"], ["steps", "Observation steps in the episode"], ["assistance", "Independent or assisted"]]],
    };
    return Object.entries(DICT).map(([f, [desc, cols]]) => `<section class="dl"><h3><a href="data/${f}" download>${f}</a></h3><p>${h(desc)}</p>${tech("Data dictionary", table([{ t: "Column" }, { t: "Meaning" }], cols.map(([c, m]) => ({ cells: [`<code>${h(c)}</code>`, h(m)] }))))}</section>`).join("");
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
        I("Irma and Zara recordings", "Irma’s two CODAP videos are different files. The session 1 frames were extracted from the 21 April file and have no behaviour labels, so they are not included in behaviour shares. Zara’s stored CODAP video is the 21 April file. No session 2 video or frame manifest is published. Frames that had been extracted from that 21 April file under the session 2 name are not shown as a second session.", "Session comparisons use only the recording that belongs to that day. Missing behaviour labels are omitted, not treated as a zero share.", "Video fingerprints in <code>data_sources_2026/MANIFEST.json</code>. Irma session 1 manifest: <code>codap_arbor_21april_audio/Irma/Irma_video_extraction_manifest.json</code>."),
        gone.length && I("Original videos are not published", `Screen-recording videos are not part of this public archive and are not intended for release. The extracted frames are published on Hugging Face. For ${gone.length} of ${videoFilesListed} listed sessions the source video is not in the local data folder: ${gone.map((r) => `${h(r.student)} (${h(SESS_NAME[r.session])})`).join(", ")}.`, "Those frames cannot be re-extracted from a local video copy. The public record is the frame dataset.", `Listed in <code>MANIFEST.json</code> of ${h(C.inventory.generated_at.slice(0, 10))}. Some processing folders hold re-encoded copies (<code>*.video.webm</code>) of different size.`),
        low.length && I("Frames cover only part of some videos", `${low.map((r) => `${h(r.student)} (${h(SESS_NAME[r.session])}, ${num(r.frame_coverage * 100)}%)`).join(", ")}.`, "Activity in the later part of these sessions is not represented in the frames.", table([{ t: "Student" }, { t: "Session" }, { t: "Last frame" }, { t: "Length in manifest" }, { t: "Real length" }], low.map((r) => ({ cells: [h(r.student), h(SESS_NAME[r.session]), clock(r.manifest.last_s), r.manifest.profile_duration_seconds ? clock(r.manifest.profile_duration_seconds) : "–", clock(lengthOf(r))] }))) + "<p>The extractor recorded the videos as shorter than they are. WebM files often carry no length in their header.</p>"),
        noOcr.length && I(`No extracted answers for ${noOcr.join(" and ")}`, "No student answers were extracted for these worksheets.", "These worksheets add no evidence to the analysis.", "Stage files in <code>students/</code> record a failed extraction. No scanned student file for WS11 is in <code>All Documents/</code>. A file named “31 Mart 2026 Çalışma Kâğıdı 12.pdf” exists but was not processed."),
        WS11_IS_WS14 && I("WS11 extraction files repeat WS14", `For all ${STUDENTS.length} students, every path and value in the WS11 extraction is identical to that student’s WS14 extraction. The WS11 rubric uses different item identifiers.`, "The worksheet page does not present those values as WS11 survey answers. They are shown under WS14.", "Compared from the site data built from <code>students/*/WS11/extraction.json</code> and the WS14 OCR files."),
        Object.keys(missingBy).length && I("Some worksheets are missing for some students", Object.entries(missingBy).map(([s, l]) => `${h(s)}: ${l.map(h).join(", ")}`).join("; ") + ".", "These students have fewer worksheet data points than others.", missingWs.map((m) => `<code>${h(m.path)}</code>`).join("<br>")),
        C.notebooks.Marco && !C.notebooks.Marco.file && C.notebooks.Marco.extraction && I("One final project is a report, not a notebook", "Marco submitted a PDF report. The notebook details were taken from it.", "Notebook structure (cells, run order, errors) cannot be measured for this student.", ""),
      ]],
      ["Method and data differences", [
        I("Motion threshold is not the code default", `The extractor default is 0.005. The CODAP manifests store <code>motion_threshold_fraction</code> ${Object.entries(thr).map(([v, n]) => `${h(v)} (${n} sessions)`).join(", ")}, and the speech-enabled runs use that stored value rather than the default.`, "A higher threshold selects fewer frames. The recordings section states the stored values.", "0.005 remains the unused default in <code>scripts/dynamic_video_analytics.py</code>."),
        I("Video and log are not linked frame by frame", "The 2026 frame-coding files record the alignment as unavailable or do not record it.", "The site cannot show which log action belongs to which frame. Logs are shown separately.", `Training-bundle metadata (${tl.files} files) also says no event log was available, which is out of date: the log CSV files exist.`),
        I("No written visual evidence per frame", "The study write-up names <code>visual_evidence</code> and <code>confidence_status</code>. The frame files contain yes/no observation flags and <code>analysis_confidence</code> instead. That confidence field is the model’s own rating, not a measured accuracy.", "The evidence shown on this site is the coder's flags, not a written description.", ""),
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
      <h1>Data Quality and Limitations</h1>
      <p class="lead">Where the data are incomplete, duplicated, or differ from the written method, and what that means for the results. Each point is computed from the files. File-level details are in the <a href="#/docs/technical">technical documentation</a>.</p>
      <nav class="jump" aria-label="On this page">${limitationItems().map(([g], i) => `<a href="#/docs/limitations/note-${i}">${h(g)}</a>`).join("")}</nav>
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
  function coverageTable() {
    const stages = [["5 May", "Colab 1"], ["12 May", "Colab 2"], ["2 June", "Colab 3"]];
    const guided = {};
    ((window.NOTEBOOKS || {}).students || []).forEach((row) => { guided[row.pseudonym] = row.stage; });
    const tick = (on) => on ? '<span class="yes" title="Stored">✓</span>' : '<span class="na">·</span>';
    const head = [{ t: "Student" }]
      .concat(C.worksheets.map((w) => ({ t: w.code })))
      .concat(SESS.map((s) => ({ t: SESS_NAME[s.id] })))
      .concat(stages.map((pair) => ({ t: pair[1] })))
      .concat([{ t: "Notebook" }]);
    const rows = STUDENTS.map((s) => ({
      cells: [h(s)]
        .concat(C.worksheets.map((w) => tick(!!(C.ws[s][w.code] && C.ws[s][w.code].ocr))))
        .concat(SESS.map((ss) => tick(!!(C.sessions[s][ss.id] && C.sessions[s][ss.id].manifest))))
        .concat(stages.map((pair) => tick(guided[s] === pair[0])))
        .concat([tick(!!(C.notebooks[s] && C.notebooks[s].file))]),
    }));
    return table(head, rows, { cls: "coverage" });
  }
  function pageTechnical() {
    const inv = Object.assign({}, C.inventory);
    // The Python-session screen recordings are not part of this archive.
    inv.folders = inv.folders.filter((f) => !/Colab Python Screen Recordings/.test(f.folder));
    inv.file_count = sum(inv.folders.map((f) => f.files));
    inv.total_bytes = sum(inv.folders.map((f) => f.bytes));
    return `<div class="page wide">${docShell("technical", `
      <h1>Technical documentation</h1>
      <p class="lead">For researchers who want to trace values back to the project files. How each source was read is in <a href="#/methods">Processing</a>. Where the records are incomplete is in <a href="#/docs/limitations">Data Quality and Limitations</a>.</p>
      <nav class="jump" aria-label="On this page">
        <a href="#/docs/technical/rebuild">Rebuilding the site</a>
        <a href="#/docs/technical/folders">Raw data folders</a>
        <a href="#/docs/technical/tables">Analysis tables</a>
        <a href="#/docs/technical/class-data">Class datasets</a>
        <a href="#/docs/technical/coverage">Coverage by student</a>
        <a href="#/docs/technical/access">Access</a>
      </nav>
      <h2 id="rebuild">Rebuilding the site</h2>
      <p><code>python3 mmla_explorer/build_site_data.py</code> reads the project files and writes the site data. <code>python3 mmla_explorer/test_site_data.py</code> re-reads the sources and compares them with the site. Last build: ${h(C.built_at.replace("T", " "))}.</p>
      <h2 id="folders">Raw data folders</h2>
      <p>From <code>${h(inv.source)}</code> (${h(inv.generated_at.slice(0, 10))}): ${num(inv.file_count)} files, ${bytes(inv.total_bytes)}. The Python-session screen recordings are left out.</p>
      ${table([{ t: "Folder" }, { t: "Files", num: 1 }, { t: "Size", num: 1 }, { t: "Types" }], inv.folders.map((f) => ({ cells: [`<code>${h(f.folder)}</code>`, num(f.files), bytes(f.bytes), h(Object.entries(f.ext).map(([e, n]) => `${e} ${n}`).join(", "))] })))}
      <h2 id="tables">Analysis tables</h2>
      <h3>Session exports</h3>
      ${table([{ t: "Level" }, { t: "File" }, { t: "Contents" }], [
        { cells: ["Session", "<code>*_session_ml_features.parquet</code>", "One row per session with yes/no process features."] },
        { cells: ["Episode", "<code>*_episodes.parquet</code>", "Stretches of related activity with start, end, category and assistance."] },
        { cells: ["Episode × code", "<code>*_episode_process_codes.parquet</code>", "Each episode and process code: observed or not, with evidence counts."] },
      ])}
      <p class="small">Location: <code>training_datasets/2026/&lt;student&gt;/&lt;session&gt;/exports/tabular/</code>.</p>
      <h3>Site tables</h3>
      <p>The tables behind this site. Column definitions stay closed until you open them.</p>
      ${siteTableDictionaries()}
      <h2 id="class-data">Class datasets</h2>
      <p>The class datasets (food data, Xeno, Titanic and the lizard data) are not stored as separate files in the project folder. The food data exists only inside the students' saved CODAP documents, and those copies differ because students filtered or edited cases. They are therefore not offered here as a single download.</p>
      <h2 id="coverage">Coverage by student</h2>
      ${coverageTable()}
      <p class="small">A tick means a file is stored. A Colab tick is the guided notebook for that session date. A later file is not counted as an earlier session. Notebook is the final homework file. Marco’s final submission is a written report, so that cell is empty.</p>
      <h2 id="access">Access</h2>
      <p>All tables use pseudonyms only. They still contain student work, so sharing beyond the research team should follow the project's data protection rules (<code>DATA_PROTECTION.md</code> in the repository). The original Parquet tables stay in the repository and are described in the <a href="#/docs/technical">technical documentation</a>.</p>`)}</div>`;
  }

  // ------------------------------------------------------------------ 05 Findings
  function findingsCrumb(title) {
    return `<p class="kicker">Findings &amp; Research Insights</p>${crumbs([["Findings", "#/findings"], [title]])}`;
  }
  function relatedCollected(items) {
    return `<h2>Related collected data</h2><ul class="guide">${items.map(([href, label, note]) => `<li><a href="${href}">${label}</a><span>${note}</span></li>`).join("")}</ul>`;
  }
  function pageFindings() {
    const cards = [
      ["Worksheet findings", "Extracted responses, item scores, and worksheet summaries. A stored score is a pipeline result, not a reviewed conclusion about learning.", "#/findings/worksheets", "Explore worksheet findings"],
      ["Screen recording findings", "Coded behaviour on each participant’s session frames. A label names what is visible. It does not name what the participant understood.", "#/findings/recordings", "Explore screen recording findings"],
      ["Platform log findings", "Recorded actions in CODAP Arbor, including model attempts. A log does not show what a participant understood.", "#/findings/logs", "Explore platform log findings"],
      ["Python notebook findings", "What the inspection found in the final homework files. Pipeline rubric points are not a reviewed grade.", "#/findings/notebooks", "Explore Python notebook findings"],
    ];
    return `<div class="page find-page">
      ${crumbs([["Findings"]])}
      <h1>Findings &amp; Research Insights</h1>
      <p class="lead">Explore the findings derived from the worksheets, screen-recording frames, platform logs, and Python notebooks collected during the learning activities.</p>
      <div class="find-grid">
        ${cards.map(([title, text, href, action]) => `<a href="${href}"><h2>${title}</h2><p>${text}</p><span class="find-go">${action}</span></a>`).join("")}
      </div>
      <section class="find-profiles">
        <h2>Student profiles</h2>
        <p>Explore each participant’s research profile, bringing together the available evidence from worksheets, screen recordings, platform logs, and Python notebooks.</p>
        <a class="find-profile" href="#/findings/participants">
          <h3>Student profiles</h3>
          <p>${STUDENTS.length} pseudonyms. Each profile brings together worksheet scores, extracted frames, class-session logs, and the final Python assignment. These summaries describe the available records. They are not learning outcomes.</p>
          <span class="find-go">Open student profiles</span>
        </a>
      </section>
    </div>`;
  }
  function pageFindingWorksheets() {
    if (window.WorksheetFindings) return window.WorksheetFindings.index();
    return `<div class="page"><h1>Worksheet findings</h1><p>The findings script did not load.</p></div>`;
  }
  function pageFindingRecordings(q) {
    if (window.RecordingFindings) return window.RecordingFindings.page(q || {});
    return `<div class="page"><h1>Screen recording findings</h1><p>The findings script did not load.</p></div>`;
  }
  function pageFindingLogs() {
    return `<div class="page wide">${findingsCrumb("Platform log findings")}
      <h1>Platform log findings</h1>
      <p class="lead">CODAP Arbor writes a time-stamped line when it records an action. These summaries describe those lines for the two class sessions.</p>
      ${logFindingsSection()}
      ${relatedCollected([["#/explore/logs", "Platform logs", "Example records and the public log file. The full log stays with the collected data."]])}
    </div>`;
  }
  function pageFindingNotebooks() {
    const body = window.NotebookFindings
      ? window.NotebookFindings.page()
      : `<p class="lead">The findings script did not load.</p>`;
    return `<div class="page wide find-page">${findingsCrumb("Python notebook findings")}
      <h1>Python notebook findings</h1>
      ${body}
      ${relatedCollected([["#/explore/notebooks", "Python notebooks", "The guided notebook, the final homework instructions, the lizard dataset, and the student submissions."]])}
    </div>`;
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
  // Links from earlier versions of the site.
  const LEGACY = { how: "methods", students: "findings/participants", worksheets: "explore/worksheets", recordings: "explore/recordings", frames: "explore/frames", logs: "explore/logs", notebooks: "explore/notebooks", data: "docs/technical", notes: "docs/limitations", glossary: "docs/glossary", student: "explore/student", worksheet: "explore/worksheet", "explore/worksheet": "explore/worksheet" };
  function scrollToId(id) {
    const anchor = id && document.getElementById(id);
    if (!anchor || !anchor.scrollIntoView) return;
    anchor.scrollIntoView();
    const head = document.querySelector(".masthead");
    const h = head ? head.getBoundingClientRect().height : 0;
    if (h) window.scrollBy(0, -(h + 12));
  }
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
    else if (top === "collected") html = pageCollected();
    else if (top === "findings") {
      const sub = parts[1] || "";
      if (sub === "participants" || sub === "student-profiles") html = pageStudents();
      else if (sub === "worksheets") {
        html = parts[2] && window.WorksheetFindings
          ? window.WorksheetFindings.page(parts[2], q)
          : pageFindingWorksheets();
        after = () => { if (window.WorksheetFindings) window.WorksheetFindings.bind(); };
      }
      else if (sub === "recordings" || sub === "frames") {
        html = pageFindingRecordings(q);
        after = () => { if (window.RecordingFindings) window.RecordingFindings.bind(); };
      }
      else if (sub === "logs") html = pageFindingLogs();
      else if (sub === "notebooks") {
        html = pageFindingNotebooks();
        after = () => { if (window.NotebookFindings) window.NotebookFindings.bind(); };
      }
      else html = pageFindings();
    }
    else if (top === "methods") { html = pageMethods(); after = () => { const a = parts[1] && document.getElementById("m-" + parts[1]); if (a && a.scrollIntoView) a.scrollIntoView(); bindMethods(); }; }
    else if (top === "explore") {
      const sub = parts[1] || "";
      if (sub === "students" || sub === "") { location.replace("#/findings/participants" + (query ? "?" + query : "")); return; }
      if (sub === "student") html = pageStudent(parts[2], parts[3]);
      else if (sub === "worksheets") { html = pageWorksheets(); after = bindWsSearch; }
      else if (sub === "worksheet") { html = pageWorksheet(parts[2], q); after = bindRespFilter; }
      else if (sub === "recordings") { html = pageRecordings(q); after = bindFrameBrowse; }
      else if (sub === "frames") { location.replace("#/explore/recordings" + (query ? "?" + query : "")); return; }
      else if (sub === "logs") html = pageLogs();
      else if (sub === "notebooks") { html = pageNotebooks(); after = bindNotebookSearch; }
      else html = `<div class="page"><h1>Page not found</h1><p><a href="#/">Go to the overview</a></p></div>`;
    } else if (top === "docs") {
      const sub = parts[1] || "";
      if (!sub || sub === "downloads" || sub === "data") {
        location.replace("#/docs/technical" + (query ? "?" + query : ""));
        return;
      }
      if (sub === "limitations") {
        html = pageLimitations();
        after = () => scrollToId(parts[2]);
      }
      else if (sub === "glossary") html = pageGlossary();
      else if (sub === "technical") {
        html = pageTechnical();
        after = () => scrollToId(parts[2]);
      } else html = `<div class="page"><h1>Page not found</h1><p><a href="#/docs/limitations">Data Quality and Limitations</a> · <a href="#/docs/glossary">Glossary</a> · <a href="#/docs/technical">Technical documentation</a></p></div>`;
    } else html = `<div class="page"><h1>Page not found</h1><p><a href="#/">Go to the overview</a></p></div>`;
    app.innerHTML = html;
    tip.style.display = "none";
    const navKey = top === "explore" ? ({ student: "participants", worksheet: "worksheets" }[parts[1]] || parts[1] || "")
      : top === "findings" ? ({ worksheets: "findings-worksheets", recordings: "findings-recordings", frames: "findings-recordings", logs: "findings-logs", notebooks: "findings-notebooks", participants: "participants" }[parts[1]] || "findings")
      : top === "docs" ? (parts[1] || "docs") : top;
    const COLLECTED_DATA_KEYS = new Set(["collected", "worksheets", "recordings", "frames", "logs", "notebooks"]);
    document.querySelectorAll(".nav-link, .top-link").forEach((a) => {
      let on = false;
      const r = a.dataset.r;
      if (a.classList.contains("top-link")) {
        if (r === "") on = top === "";
        else if (r === "collected") on = top === "collected" || (top === "explore" && COLLECTED_DATA_KEYS.has(navKey));
        else if (r === "methods") on = top === "methods";
        else if (r === "findings") on = top === "findings" || navKey === "participants";
        else if (r === "docs") on = top === "docs";
        else on = r === navKey;
      } else if (r === "collected") on = top === "collected";
      else if (r === "methods") on = top === "methods";
      else if (r === "docs") on = top === "docs" && !parts[1];
      else on = a.dataset.r === navKey || (top === "docs" && r === (parts[1] || "docs"));
      a.classList.toggle("active", on);
      if (on && a.classList.contains("top-link")) a.setAttribute("aria-current", "page");
      else a.removeAttribute("aria-current");
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
