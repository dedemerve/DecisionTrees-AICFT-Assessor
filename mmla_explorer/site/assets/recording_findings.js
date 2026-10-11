/* Screen recording findings.
   Counts come from the listed frames in window.FRAMES and are checked against
   the behaviour totals stored on each session in window.CORE.
   A count is the number of listed frames with that label. It is not minutes
   spent, and it is not a measure of understanding.
   Episode categories are a different scheme and are not drawn in these colours. */
(function (root) {
  "use strict";

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
  const BEH = Object.fromEntries(BEHAV.map((b) => [b[0], { label: b[1], desc: b[2], color: "var(" + b[3] + ")" }]));
  const SESSION_LABEL = {
    codap_21apr: { name: "CODAP session 1", date: "21 April 2026" },
    codap_28apr: { name: "CODAP session 2", date: "28 April 2026" },
  };

  const h = (v) => String(v == null ? "" : v)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  const num = (v, d = 0) => (v == null || Number.isNaN(Number(v))) ? "–" :
    Number(v).toLocaleString("en-GB", { maximumFractionDigits: d, minimumFractionDigits: 0 });
  const pct = (a, b) => b ? num(100 * a / b, 1) + "%" : "–";
  const clock = (s) => {
    if (s == null || Number.isNaN(Number(s))) return "–";
    s = Math.round(Number(s));
    const hh = Math.floor(s / 3600), mm = Math.floor((s % 3600) / 60), ss = s % 60;
    return (hh ? hh + ":" + String(mm).padStart(2, "0") : mm) + ":" + String(ss).padStart(2, "0");
  };
  const tipAttr = (html) => ` data-tip="${h(html)}"`;
  const labelOf = (code) => BEH[code] ? BEH[code].label : String(code || "").replace(/_/g, " ");
  const colorOf = (code) => BEH[code] ? BEH[code].color : "var(--rule-strong)";
  const sessionMeta = (meta) => SESSION_LABEL[meta.id] || { name: meta.label || meta.id, date: meta.date || "" };

  function countOf(frames, key) {
    const counts = {};
    frames.forEach((f) => {
      const code = f[key];
      if (!code) return;
      counts[code] = (counts[code] || 0) + 1;
    });
    return counts;
  }

  function orderedCodes(counts) {
    const keys = BEHAV.map((b) => b[0]).filter((k) => counts[k]);
    Object.keys(counts).forEach((k) => { if (!BEH[k]) keys.push(k); });
    return keys;
  }

  function sameCounts(a, b) {
    if (!a || !b) return false;
    const keys = new Set(Object.keys(a).concat(Object.keys(b)));
    let ok = true;
    keys.forEach((k) => { if ((a[k] || 0) !== (b[k] || 0)) ok = false; });
    return ok;
  }

  function runsOf(frames) {
    const runs = [];
    frames.forEach((f) => {
      const code = f.b || "";
      const last = runs[runs.length - 1];
      if (last && last.code === code) {
        last.n += 1;
        last.end = f.t;
      } else {
        runs.push({ code: code, n: 1, start: f.t, end: f.t });
      }
    });
    return runs;
  }

  function analyze(core, frames) {
    const sessions = (core.sessions_meta || []).map((meta) => Object.assign({ id: meta.id }, sessionMeta(meta)));
    const byStudent = {};
    (core.students || []).forEach((student) => {
      byStudent[student] = {};
      sessions.forEach((ss) => {
        const rec = (core.sessions[student] && core.sessions[student][ss.id]) || {};
        const listed = (frames || []).filter((f) => f.s === student && f.ss === ss.id).slice().sort((a, b) => a.t - b.t);
        const coded = listed.filter((f) => f.b);
        const primary = countOf(coded, "b");
        const fileCounts = rec.coding && rec.coding.behaviors ? rec.coding.behaviors : null;
        const manifestFrames = rec.manifest ? rec.manifest.frames : null;
        const kept = rec.manifest && rec.manifest.summary ? rec.manifest.summary.total_frames_extracted : null;
        const episodes = core.episodes && core.episodes[student] && core.episodes[student][ss.id]
          ? (core.episodes[student][ss.id].episodes || []) : [];
        const confidence = {};
        coded.forEach((f) => { if (f.cf) confidence[f.cf] = (confidence[f.cf] || 0) + 1; });
        byStudent[student][ss.id] = {
          id: ss.id,
          name: ss.name,
          date: ss.date,
          hasRecording: !!(rec.manifest || listed.length),
          listed: listed.length,
          manifestFrames: manifestFrames,
          coded: coded.length,
          uncoded: listed.length - coded.length,
          primary: primary,
          fileCounts: fileCounts,
          countsMatch: fileCounts ? sameCounts(primary, fileCounts) : false,
          framesCodedFile: rec.coding ? rec.coding.frames_coded : null,
          secondary: countOf(listed, "b2"),
          runs: runsOf(listed),
          thumbs: listed.filter((f) => f.th).map((f) => ({ id: f.id, t: f.t, b: f.b || "", th: f.th })),
          duplicateOf: rec.same_video_file_as || [],
          coverage: typeof rec.frame_coverage === "number" ? rec.frame_coverage : null,
          kept: typeof kept === "number" ? kept : null,
          codingSource: rec.coding ? rec.coding.source : "",
          confidence: confidence,
          episodes: episodes.map((e) => ({
            id: e.id, category: e.category, start: e.start_ms, end: e.end_ms, assistance: e.assistance,
          })),
          episodeSource: core.episodes && core.episodes[student] && core.episodes[student][ss.id]
            ? core.episodes[student][ss.id].episodes_source : "",
        };
      });
    });
    return { students: core.students || [], sessions: sessions, byStudent: byStudent };
  }

  function data() {
    if (!root.CORE) return null;
    return analyze(root.CORE, root.FRAMES || []);
  }

  function swatch(code) {
    return `<i class="sw" style="background:${colorOf(code)}"></i>`;
  }

  function countTable(counts, denom, kind) {
    const keys = orderedCodes(counts);
    if (!keys.length) return "";
    const rows = keys.map((code) => {
      const known = !!BEH[code];
      const meaning = known ? BEH[code].desc : (kind === "second" ? "Stored as a second label. It is not one of the nine primary codes." : "Not in the nine-code list.");
      return `<tr><td>${swatch(code)}${h(known ? BEH[code].label : code)}</td><td>${h(meaning)}</td><td class="num">${num(counts[code])}</td><td class="num">${pct(counts[code], denom)}</td></tr>`;
    }).join("");
    return `<div class="table-wrap"><table><thead><tr><th>${kind === "second" ? "Second label" : "Observed behaviour"}</th><th>Meaning</th><th class="num">Frames</th><th class="num">Share</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function ribbon(model) {
    if (!model.runs.length) return "";
    const total = model.runs.reduce((a, r) => a + r.n, 0);
    const bars = model.runs.map((run) => {
      const name = run.code ? labelOf(run.code) : "No label";
      const text = `<b>${h(name)}</b><br>${num(run.n)} listed frame${run.n === 1 ? "" : "s"} · ${clock(run.start)}–${clock(run.end)}`;
      return `<div style="flex:${run.n};background:${run.code ? colorOf(run.code) : "var(--rule-strong)"}"${tipAttr(text)}></div>`;
    }).join("");
    const first = model.runs[0].start;
    const last = model.runs[model.runs.length - 1].end;
    return `<div class="run-ribbon" role="img" aria-label="Order of listed frames by primary behaviour">${bars}</div>
      <div class="axis"><span>First frame ${clock(first)}</span><span>Last frame ${clock(last)}</span></div>
      <p class="small">Each coloured segment is consecutive listed frames with the same primary label. Width follows how many of the ${num(total)} listed frames are in that segment.</p>`;
  }

  function thumbs(model, student) {
    if (!model.thumbs.length) {
      return `<p class="missing-line">Preview images for this session are not stored on this site. The counts above still use the listed frames.</p>`;
    }
    const figs = model.thumbs.map((f) => {
      const name = f.b ? labelOf(f.b) : "No label";
      const cap = `${student} · ${model.name} · ${clock(f.t)} · ${name}`;
      return `<figure><button type="button" class="thumb" data-zoom="thumbs/${h(f.th)}" data-cap="${h(cap)}"><img loading="lazy" src="thumbs/${h(f.th)}" alt="${h(cap)}"></button><figcaption><span class="mono">${clock(f.t)}</span><span class="beh-line"><i style="background:${f.b ? colorOf(f.b) : "var(--rule-strong)"}"></i>${h(name)}</span></figcaption></figure>`;
    }).join("");
    return `<p class="small">${num(model.thumbs.length)} preview images are stored for this session, spaced through the recording. The counts above use every listed frame, not only these pictures.</p><div class="thumbs frame-grid">${figs}</div>`;
  }

  function episodes(model) {
    if (!model.episodes.length) return "";
    const rows = model.episodes.map((e) => `<tr><td><code>${h(e.id)}</code></td><td>${h(e.category || "–")}</td><td>${clock((e.start || 0) / 1000)}</td><td>${clock((e.end || 0) / 1000)}</td><td>${h(e.assistance || "–")}</td></tr>`).join("");
    return `<h3>Episode table</h3>
      <p>This table is a separate coding scheme stored with the session. Its categories are not the nine frame labels, and they are not drawn in those colours.</p>
      <div class="table-wrap"><table><thead><tr><th>Episode</th><th>Category</th><th>From</th><th>To</th><th>Assistance</th></tr></thead><tbody>${rows}</tbody></table></div>`;
  }

  function limits(model) {
    const items = [];
    if (model.duplicateOf.length) {
      const names = model.duplicateOf.map((id) => (SESSION_LABEL[id] && SESSION_LABEL[id].name) || id).join(" and ");
      items.push(`This video is the same file as the ${names} video. The counts on this page describe this listing. They are not a second recording.`);
    }
    if (model.coverage != null && model.coverage < 0.8) {
      items.push(`Frames cover the first ${num(model.coverage * 100)}% of the recording. Later activity is not in these frames.`);
    }
    if (model.kept != null && model.manifestFrames != null && model.kept !== model.manifestFrames) {
      items.push(`The extraction summary reports ${num(model.kept)} kept frames. The listed frames and the behaviour coding use ${num(model.manifestFrames)}. The table above uses the listed frames.`);
    }
    if (model.uncoded) {
      items.push(`${num(model.uncoded)} listed frame${model.uncoded === 1 ? " has" : "s have"} no primary label. ${model.uncoded === 1 ? "It is" : "They are"} left out of the behaviour shares.`);
    }
    if (model.fileCounts && !model.countsMatch) {
      items.push("The behaviour totals in the coding file do not match the listed frames. The table uses the listed frames.");
    }
    items.push("A label describes the visible activity on that frame. It does not describe what the participant understood.");
    items.push("Original videos are not published. The pictures on this page are extracted frames.");
    return `<ul>${items.map((x) => `<li>${h(x)}</li>`).join("")}</ul>`;
  }

  function sessionPanel(pack, student, sessionId) {
    const model = pack.byStudent[student] && pack.byStudent[student][sessionId];
    if (!model) return `<p class="empty">That session is not in this archive.</p>`;
    if (!model.hasRecording) {
      const episodeNote = model.episodes.length
        ? `<p>An episode table is stored for this session, and no extracted frames are on record. Those episodes are not shown as frame findings.</p>`
        : "";
      return `<h3 class="preview-heading">${h(student)} · ${h(model.name)}</h3>
        <div class="empty-session"><p>No screen recording frames are on record for ${h(student)}, ${h(model.name)}.</p></div>
        ${episodeNote}`;
    }
    if (!model.coded) {
      return `<h3 class="preview-heading">${h(student)} · ${h(model.name)}</h3>
        <p>${num(model.listed)} frames are listed for this session. Behaviour coding for these frames is unavailable.</p>
        <p><a href="#/explore/recordings?s=${encodeURIComponent(student)}&amp;ss=${encodeURIComponent(model.id)}">Open the collected frames for this session</a></p>
        ${thumbs(model, student)}`;
    }
    const denom = model.coded;
    const stack = `<div class="stack" role="img" aria-label="Share of coded frames by behaviour">${orderedCodes(model.primary).map((code) =>
      `<div style="flex:${model.primary[code]};background:${colorOf(code)}"${tipAttr(`<b>${h(labelOf(code))}</b><br>${num(model.primary[code])} frames · ${pct(model.primary[code], denom)}`)}></div>`).join("")}</div>`;
    const legend = `<div class="legend">${orderedCodes(model.primary).map((code) => `<span><i style="background:${colorOf(code)}"></i>${h(labelOf(code))}</span>`).join("")}</div>`;
    const agree = model.countsMatch ? `<p class="small">These totals match the behaviour counts stored in the coding file (${num(model.framesCodedFile)} coded frames).</p>` : "";
    const confKeys = Object.keys(model.confidence);
    const conf = confKeys.length ? `<p class="small">Coder confidence stored on the labelled frames: ${confKeys.map((k) => `${num(model.confidence[k])} ${h(k.toLowerCase())}`).join(", ")}. This is the coder’s confidence in the label, not a judgment of the participant.</p>` : "";
    const secondKeys = Object.keys(model.secondary);
    const second = secondKeys.length ? `<h3>Second label</h3>
      <p>Some frames also store a second label. It is not the primary code, and it is not added into the shares above. The share in this table is out of the ${num(model.listed)} listed frames.</p>
      ${countTable(model.secondary, model.listed, "second")}` : "";
    return `<h3 class="preview-heading">${h(student)} · ${h(model.name)} <span class="small">${h(model.date)}</span></h3>
      <p>${num(model.listed)} frames are listed. ${num(model.coded)} have a primary behaviour label. The shares below use those ${num(denom)} labelled frames as the denominator.</p>
      ${stack}${legend}
      <h3>Observed behaviour</h3>
      ${countTable(model.primary, denom, "primary")}
      ${agree}${conf}
      <h3>Order of coded frames</h3>
      ${ribbon(model)}
      ${second}
      <h3>Preview frames</h3>
      ${thumbs(model, student)}
      <p><a href="#/explore/recordings?s=${encodeURIComponent(student)}&amp;ss=${encodeURIComponent(model.id)}">Open the collected frames for this session</a></p>
      ${episodes(model)}
      <h3>Limitations</h3>
      ${limits(model)}
      ${model.codingSource ? `<details class="tech"><summary>Source path</summary><div class="tech-body"><div class="src">${h(model.codingSource)}</div></div></details>` : ""}`;
  }

  function tabs(pack, student, sessionId) {
    const available = pack.sessions.filter((ss) => pack.byStudent[student][ss.id].hasRecording);
    if (!available.length) {
      return `<div class="empty-session"><p>No screen recording frames are on record for ${h(student)}.</p></div>`;
    }
    const buttons = available.map((ss) => {
      const model = pack.byStudent[student][ss.id];
      const sub = model.coded ? `${ss.date} · ${num(model.coded)} labelled frames` : `${ss.date} · Coding unavailable`;
      return `<button type="button" role="tab" class="sess-tab" data-ss="${h(ss.id)}" aria-selected="${sessionId === ss.id ? "true" : "false"}"><span>${h(ss.name)}</span><span class="when">${h(sub)}</span></button>`;
    }).join("");
    let current = available[0].id;
    if (sessionId && pack.byStudent[student][sessionId]) current = sessionId;
    const hidden = pack.sessions.filter((ss) => ss.id !== current && !pack.byStudent[student][ss.id].hasRecording && pack.byStudent[student][ss.id].episodes.length);
    const aside = hidden.length ? `<p class="small rec-note">${hidden.map((ss) => h(ss.name)).join(" and ")} ${hidden.length === 1 ? "has" : "have"} an episode table and no extracted frames. Those episodes are not shown as frame findings.</p>` : "";
    return `<h2 class="sess-heading">Choose a session</h2><div class="sess-tabs" role="tablist">${buttons}</div>${aside}<div id="recSession" data-ss="${h(current)}">${sessionPanel(pack, student, current)}</div>`;
  }

  function page(q) {
    const pack = data();
    q = q || {};
    if (!pack) return `<div class="page"><h1>Screen recording findings</h1><p>Data files are missing.</p></div>`;
    const student = pack.students.indexOf(q.s) !== -1 ? q.s : "";
    const sessionId = student ? (q.ss || "") : "";
    const who = pack.students.map((s) => `<button type="button" class="person-card${s === student ? " on" : ""}" data-who="${h(s)}" aria-pressed="${s === student ? "true" : "false"}"><span class="person-name">${h(s)}</span></button>`).join("");
    const body = student ? tabs(pack, student, sessionId) : `<p class="frame-prompt">Choose a participant, then a session, to read the coded behaviour for that recording.</p>`;
    return `<div class="page wide find-page" id="recFind" data-student="${h(student)}" data-session="${h(sessionId)}">
      <p class="kicker">Findings</p>
      <nav class="crumbs" aria-label="Breadcrumb"><a href="#/findings">Findings</a><span aria-hidden="true">/</span><span aria-current="page">Screen recording findings</span></nav>
      <h1>Screen recording findings</h1>
      <p class="lead">Each listed frame can carry one primary behaviour label. The label names what is visible on that frame. It does not name what the participant understood. Counts are the number of listed frames with that label.</p>
      <section class="section-block" id="rec-explore">
        <h2>Choose a participant</h2>
        <div class="person-grid" id="recWho">${who}</div>
        <div id="recOut">${body}</div>
      </section>
      <h2>Collected frames</h2>
      <p>The frame images, including the preview subset on this site, stay with the collected data. <a href="#/explore/recordings">Open the screen recording frames</a>. Original videos are not published.</p>
      <p><a href="#/methods/recordings">How frames were selected and coded</a></p>
    </div>`;
  }

  function bind() {
    const rootEl = document.getElementById("recFind");
    if (!rootEl || rootEl.dataset.bound === "1") return;
    rootEl.dataset.bound = "1";
    const pack = data();
    if (!pack) return;
    const view = { s: rootEl.dataset.student || "", ss: rootEl.dataset.session || "" };
    const paint = () => {
      document.querySelectorAll("#recWho .person-card").forEach((b) => {
        const on = b.dataset.who === view.s;
        b.classList.toggle("on", on);
        b.setAttribute("aria-pressed", on ? "true" : "false");
      });
      const out = document.getElementById("recOut");
      if (!out) return;
      out.innerHTML = view.s ? tabs(pack, view.s, view.ss) : `<p class="frame-prompt">Choose a participant, then a session, to read the coded behaviour for that recording.</p>`;
      out.querySelectorAll(".sess-tab").forEach((b) => {
        b.addEventListener("click", () => {
          view.ss = b.dataset.ss;
          sync();
        });
      });
    };
    const sync = () => {
      const qs = [["s", view.s], ["ss", view.ss]].filter((x) => x[1]).map(([k, v]) => k + "=" + encodeURIComponent(v)).join("&");
      const next = "#/findings/recordings" + (qs ? "?" + qs : "");
      if (location.hash !== next && root.history && root.history.replaceState) root.history.replaceState(null, "", next);
      paint();
    };
    document.querySelectorAll("#recWho .person-card").forEach((b) => {
      b.addEventListener("click", () => {
        view.s = b.dataset.who;
        const first = pack.sessions.find((ss) => pack.byStudent[view.s][ss.id].hasRecording);
        view.ss = first ? first.id : "";
        sync();
      });
    });
    paint();
  }

  root.RecordingFindings = { analyze: analyze, page: page, bind: bind };
})(typeof window !== "undefined" ? window : globalThis);
