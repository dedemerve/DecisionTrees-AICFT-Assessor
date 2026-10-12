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

  const SCREEN = new Set(["TREE", "GRAPH", "TABLE", "MIXED", "CODAP"]);

  function transitionsOf(runs) {
    const counts = {};
    let pairs = 0;
    for (let i = 0; i < runs.length - 1; i++) {
      const from = runs[i].code;
      const to = runs[i + 1].code;
      if (!from || !to || from === to) continue;
      pairs += 1;
      const key = from + "\t" + to;
      counts[key] = (counts[key] || 0) + 1;
    }
    const rows = Object.keys(counts).map((key) => {
      const parts = key.split("\t");
      return { from: parts[0], to: parts[1], n: counts[key] };
    }).sort((a, b) => b.n - a.n || a.from.localeCompare(b.from) || a.to.localeCompare(b.to));
    return { pairs: pairs, rows: rows };
  }

  function topCode(counts) {
    let best = "";
    let n = 0;
    Object.keys(counts).forEach((code) => {
      if (counts[code] > n) { best = code; n = counts[code]; }
    });
    return { code: best, n: n };
  }

  function thirdsOf(frames) {
    const coded = frames.filter((f) => f.b);
    if (coded.length < 15) return { parts: null, uneven: false };
    const t0 = coded[0].t;
    const t1 = coded[coded.length - 1].t;
    if (!(typeof t0 === "number" && typeof t1 === "number") || t1 - t0 < 600) return { parts: null, uneven: false };
    const span = t1 - t0;
    const parts = [0, 1, 2].map((i) => {
      const from = t0 + span * i / 3;
      const to = t0 + span * (i + 1) / 3;
      const rows = coded.filter((f) => (i < 2 ? f.t >= from && f.t < to : f.t >= from && f.t <= t1));
      const counts = countOf(rows, "b");
      const top = topCode(counts);
      return { from: from, to: i === 2 ? t1 : to, n: rows.length, counts: counts, top: top.code, topN: top.n };
    });
    if (parts.some((p) => p.n < 5)) return { parts: null, uneven: true };
    return { parts: parts, uneven: false };
  }

  function examplesOf(frames, runs) {
    const coded = frames.filter((f) => f.b);
    const counts = countOf(coded, "b");
    const ranked = orderedCodes(counts).slice().sort((a, b) => counts[b] - counts[a] || a.localeCompare(b));
    const chosen = [];
    if (ranked[0]) chosen.push(ranked[0]);
    if (ranked[1] && coded.length && counts[ranked[1]] / coded.length >= 0.15) chosen.push(ranked[1]);
    return chosen.slice(0, 2).map((code) => {
      const runsOfCode = runs.filter((r) => r.code === code).slice().sort((a, b) => b.n - a.n || a.start - b.start);
      if (!runsOfCode.length) return null;
      const run = runsOfCode[0];
      const mid = (Number(run.start) + Number(run.end)) / 2;
      const inside = frames.filter((f) => f.b === code && f.th && SCREEN.has(f.sc) && f.t >= run.start && f.t <= run.end);
      if (!inside.length) return null;
      inside.sort((a, b) => Math.abs(a.t - mid) - Math.abs(b.t - mid) || a.t - b.t);
      const frame = inside[0];
      return { code: code, t: frame.t, id: frame.id, th: frame.th, runN: run.n, inRun: true };
    }).filter(Boolean);
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
        const secondary = countOf(listed, "b2");
        const secondaryFrameCount = listed.filter((f) => f.b2).length;
        const runs = runsOf(listed);
        const thirds = thirdsOf(coded);
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
          secondary: secondary,
          secondaryFrameCount: secondaryFrameCount,
          runs: runs,
          transitions: transitionsOf(runs),
          thirds: thirds.parts,
          timeUneven: thirds.uneven,
          examples: examplesOf(listed, runs),
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
    return `<div class="table-wrap"><table><thead><tr><th>${kind === "second" ? "Second label" : "Behaviour"}</th><th>Meaning</th><th class="num">Frames</th><th class="num">Share</th></tr></thead><tbody>${rows}</tbody></table></div>`;
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
      <p class="small">The timeline shows the order of listed frames by primary behaviour label. Segment width reflects the number of consecutive frames in each segment, not necessarily elapsed time. These ${num(total)} listed frames are the width.</p>`;
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
    if (model.timeUneven) {
      items.push("The labelled frames are too uneven across the session clock to compare the beginning, middle, and end.");
    }
    items.push("Labels describe the visible activity in the extracted frames. They do not, by themselves, establish the participant's understanding or learning.");
    return `<ul>${items.map((x) => `<li>${h(x)}</li>`).join("")}</ul>`;
  }

  function rankedLabels(model) {
    return orderedCodes(model.primary).slice().sort((a, b) => model.primary[b] - model.primary[a] || a.localeCompare(b));
  }

  function standsOut(model) {
    const lines = [];
    const denom = model.coded;
    const ranked = rankedLabels(model);
    if (!ranked.length || !denom) return lines;
    const first = ranked[0];
    const second = ranked[1];
    const firstN = model.primary[first];
    const secondN = second ? model.primary[second] : 0;
    const close = second && Math.abs(firstN - secondN) / denom < 0.05;
    if (close) {
      lines.push("The two largest shares are close. " + labelOf(first) + " is " + num(firstN) + " of " + num(denom) + " labelled frames (" + pct(firstN, denom) + "), and " + labelOf(second) + " is " + num(secondN) + " of " + num(denom) + " (" + pct(secondN, denom) + ").");
    } else if (firstN / denom >= 0.5) {
      lines.push(labelOf(first) + " is the most frequent primary label: " + num(firstN) + " of " + num(denom) + " labelled frames (" + pct(firstN, denom) + ").");
      if (second) lines.push(labelOf(second) + " is the next largest share, " + num(secondN) + " of " + num(denom) + " (" + pct(secondN, denom) + ").");
    } else {
      lines.push("No primary label reaches half of the labelled frames. The largest share is " + labelOf(first) + ", " + num(firstN) + " of " + num(denom) + " (" + pct(firstN, denom) + ")." + (second ? " " + labelOf(second) + " is next, " + num(secondN) + " of " + num(denom) + " (" + pct(secondN, denom) + ")." : ""));
    }
    const change = model.transitions && model.transitions.rows[0];
    if (change && change.n >= 3 && model.transitions.pairs) {
      lines.push("The primary label changes " + num(model.transitions.pairs) + " times from one uninterrupted segment of listed frames to the next. The most repeated change is " + labelOf(change.from) + " followed by " + labelOf(change.to) + ", " + num(change.n) + " of those " + num(model.transitions.pairs) + " changes.");
    }
    const shift = clockShift(model);
    if (shift) {
      const early = model.thirds[0];
      const late = model.thirds[2];
      const earlyN = early.counts[shift.code] || 0;
      const lateN = late.counts[shift.code] || 0;
      lines.push("The session clock, from " + clock(early.from) + " to " + clock(late.to) + ", is split into three equal parts. In the first part, " + labelOf(shift.code) + " is " + num(earlyN) + " of " + num(early.n) + " labelled frames (" + pct(earlyN, early.n) + "). In the last part, it is " + num(lateN) + " of " + num(late.n) + " (" + pct(lateN, late.n) + ").");
    }
    return lines;
  }

  function clockShift(model) {
    const parts = model.thirds;
    if (!parts || parts.length !== 3) return null;
    const codes = {};
    parts.forEach((part) => Object.keys(part.counts).forEach((code) => { codes[code] = true; }));
    let best = null;
    Object.keys(codes).forEach((code) => {
      const a = (parts[0].counts[code] || 0) / parts[0].n;
      const b = (parts[2].counts[code] || 0) / parts[2].n;
      const diff = Math.abs(a - b);
      if (diff >= 0.2 && (!best || diff > best.diff)) best = { code: code, diff: diff };
    });
    return best;
  }

  function otherSession(pack, student, model) {
    const other = pack.sessions.find((ss) => ss.id !== model.id && pack.byStudent[student][ss.id].coded >= 20);
    if (!other || model.coded < 20) return null;
    return pack.byStudent[student][other.id];
  }

  function evidenceHtml(pack, student, model) {
    const blocks = [];
    const trans = model.transitions;
    if (trans && trans.pairs) {
      const repeated = trans.rows.filter((row) => row.n >= 2).slice(0, 4);
      let body = "<p>A change is counted when one uninterrupted segment is followed by a different primary label. Frames that stay on the same label are one segment. The denominator is the " + num(trans.pairs) + " changes in this session.</p>";
      if (repeated.length) {
        body += "<div class=\"table-wrap\"><table><thead><tr><th>From</th><th>To</th><th class=\"num\">Changes</th><th class=\"num\">Share of changes</th></tr></thead><tbody>"
          + repeated.map((row) => "<tr><td>" + swatch(row.from) + h(labelOf(row.from)) + "</td><td>" + swatch(row.to) + h(labelOf(row.to)) + "</td><td class=\"num\">" + num(row.n) + "</td><td class=\"num\">" + pct(row.n, trans.pairs) + "</td></tr>").join("")
          + "</tbody></table></div>";
      } else {
        body += "<p>No change happens more than once.</p>";
      }
      blocks.push("<h4>Changes between segments</h4>" + body);
    }
    const shift = clockShift(model);
    if (shift && model.thirds) {
      const names = ["First third", "Middle third", "Last third"];
      const rows = model.thirds.map((part, i) => {
        const n = part.counts[shift.code] || 0;
        return "<tr><td>" + names[i] + "</td><td>" + clock(part.from) + "–" + clock(part.to) + "</td><td class=\"num\">" + num(part.n) + "</td><td class=\"num\">" + num(n) + " of " + num(part.n) + " (" + pct(n, part.n) + ")</td></tr>";
      }).join("");
      blocks.push("<h4>Across the session clock</h4><p>Each third is an equal share of the clock from the first labelled frame to the last. The count is labelled frames in that interval, not minutes of activity.</p><div class=\"table-wrap\"><table><thead><tr><th>Part</th><th>Clock</th><th class=\"num\">Labelled frames</th><th class=\"num\">" + h(labelOf(shift.code)) + "</th></tr></thead><tbody>" + rows + "</tbody></table></div>");
    }
    if (model.examples && model.examples.length) {
      const figs = model.examples.map((ex) => {
        const where = "Stored preview nearest the middle of the longest uninterrupted " + labelOf(ex.code) + " run (" + num(ex.runN) + " listed frames).";
        const alt = student + ", " + model.name + ", " + clock(ex.t) + ", " + labelOf(ex.code);
        return "<figure><img loading=\"lazy\" src=\"thumbs/" + h(ex.th) + "\" alt=\"" + h(alt) + "\"><figcaption><b>" + h(labelOf(ex.code)) + "</b> · " + clock(ex.t) + "<br>" + h(where) + " It shows that moment, not every frame with this label.</figcaption></figure>";
      }).join("");
      blocks.push("<h4>Stored previews</h4><p>Each picture is chosen by a fixed rule: the CODAP-screen preview nearest the middle of the longest run of a frequent label. Menus are not used.</p><div class=\"rec-shots\">" + figs + "</div>");
    }
    const other = otherSession(pack, student, model);
    if (other) {
      const codes = orderedCodes(Object.assign({}, model.primary, other.primary));
      const diffs = codes.map((code) => {
        const here = model.primary[code] || 0;
        const there = other.primary[code] || 0;
        return { code: code, here: here, there: there, diff: Math.abs(here / model.coded - there / other.coded) };
      }).filter((row) => row.diff >= 0.15).sort((a, b) => b.diff - a.diff).slice(0, 3);
      let body = "<p>" + h(other.name) + " has " + num(other.coded) + " labelled frames. This session has " + num(model.coded) + ". Shares use each session’s own labelled frames. A difference here is a difference in coded activity.</p>";
      if (diffs.length) {
        body += "<div class=\"table-wrap\"><table><thead><tr><th>Behaviour</th><th class=\"num\">This session</th><th class=\"num\">" + h(other.name) + "</th></tr></thead><tbody>"
          + diffs.map((row) => "<tr><td>" + swatch(row.code) + h(labelOf(row.code)) + "</td><td class=\"num\">" + num(row.here) + " of " + num(model.coded) + " (" + pct(row.here, model.coded) + ")</td><td class=\"num\">" + num(row.there) + " of " + num(other.coded) + " (" + pct(row.there, other.coded) + ")</td></tr>").join("")
          + "</tbody></table></div>";
      } else {
        body += "<p>No primary label differs by 15 percentage points or more.</p>";
      }
      blocks.push("<h4>Compared with " + h(other.name) + "</h4>" + body);
    }
    const cohort = pack.students.filter((s) => pack.byStudent[s][model.id].coded > 0);
    const focus = rankedLabels(model)[0];
    if (focus && cohort.length >= 5) {
      const shares = cohort.map((s) => {
        const rec = pack.byStudent[s][model.id];
        return (rec.primary[focus] || 0) / rec.coded;
      });
      const mid = median(shares);
      const mine = (model.primary[focus] || 0) / model.coded;
      if (Math.abs(mine - mid) >= 0.15) {
        blocks.push("<h4>This session across participants</h4><p>" + num(cohort.length) + " participants have labelled frames for " + h(model.name) + ". " + h(labelOf(focus)) + " is " + pct(model.primary[focus], model.coded) + " of " + h(student) + "’s " + num(model.coded) + " labelled frames. The median share of " + h(labelOf(focus)) + " in that group is " + num(100 * mid, 1) + "% of each participant’s own labelled frames. A higher share means more frames with that label.</p>");
      }
    }
    if (!blocks.length) return "";
    return "<details class=\"find-fold\" id=\"recEvidence\"><summary>Explore the evidence</summary><div class=\"find-fold-body\">" + blocks.join("") + "</div></details>";
  }

  function median(xs) {
    if (!xs.length) return null;
    const a = xs.slice().sort((x, y) => x - y);
    const i = Math.floor(a.length / 2);
    return a.length % 2 ? a[i] : (a[i - 1] + a[i]) / 2;
  }

  function sessionPanel(pack, student, sessionId) {
    const model = pack.byStudent[student] && pack.byStudent[student][sessionId];
    if (!model) return `<p class="empty">That session is not in this archive.</p>`;
    if (!model.hasRecording) {
      return `<h3 class="preview-heading">${h(student)} · ${h(model.name)}</h3>
        <div class="empty-session"><p>No screen recording frames are on record for ${h(student)}, ${h(model.name)}.</p></div>`;
    }
    if (!model.coded) {
      return `<h3 class="preview-heading">${h(student)} · ${h(model.name)}</h3>
        <p>${num(model.listed)} frames are listed for this session. They do not have behaviour labels, so they are not included in behaviour shares. Labels from another session are not copied onto them.</p>
        <p><a href="#/explore/recordings?s=${encodeURIComponent(student)}&amp;ss=${encodeURIComponent(model.id)}">Explore collected frames for this session</a></p>`;
    }
    const denom = model.coded;
    const stack = `<div class="stack" role="img" aria-label="Share of coded frames by behaviour">${orderedCodes(model.primary).map((code) =>
      `<div style="flex:${model.primary[code]};background:${colorOf(code)}"${tipAttr(`<b>${h(labelOf(code))}</b><br>${num(model.primary[code])} frames · ${pct(model.primary[code], denom)}`)}></div>`).join("")}</div>`;
    const legend = `<div class="legend">${orderedCodes(model.primary).map((code) => `<span><i style="background:${colorOf(code)}"></i>${h(labelOf(code))}</span>`).join("")}</div>`;
    const collected = `<p><a href="#/explore/recordings?s=${encodeURIComponent(student)}&amp;ss=${encodeURIComponent(model.id)}">Explore collected frames for this session</a></p>`;
    return `<h3 class="preview-heading">${h(student)} · ${h(model.name)}</h3>
      <p>${num(model.listed)} frames are listed. ${num(model.coded)} have a primary behaviour label. Shares use those ${num(denom)} labelled frames as the denominator.</p>
      <h3>Observed behaviour</h3>
      ${stack}${legend}
      ${countTable(model.primary, denom, "primary")}
      <h3>Order of coded frames</h3>
      ${ribbon(model)}
      <h3>What stands out?</h3>
      ${standsOut(model).map((line) => `<p>${h(line)}</p>`).join("")}
      ${evidenceHtml(pack, student, model)}
      ${collected}
      <h3>Limitations</h3>
      ${limits(model)}`;
  }

  function tabs(pack, student, sessionId) {
    const available = pack.sessions.filter((ss) => pack.byStudent[student][ss.id].hasRecording);
    if (!available.length) {
      return `<div class="empty-session"><p>No screen recording frames are on record for ${h(student)}.</p></div>`;
    }
    const buttons = available.map((ss) => {
      const model = pack.byStudent[student][ss.id];
      const sub = model.coded ? `${num(model.coded)} labelled frames` : "Coding unavailable";
      return `<button type="button" role="tab" class="sess-tab" data-ss="${h(ss.id)}" aria-selected="${sessionId === ss.id ? "true" : "false"}"><span>${h(ss.name)}</span><span class="when">${h(sub)}</span></button>`;
    }).join("");
    let current = available[0].id;
    if (sessionId && pack.byStudent[student][sessionId]) current = sessionId;
    return `<h2 class="sess-heading">Choose a session</h2><div class="sess-tabs" role="tablist">${buttons}</div><div id="recSession" data-ss="${h(current)}">${sessionPanel(pack, student, current)}</div>`;
  }

  function page(q) {
    const pack = data();
    q = q || {};
    if (!pack) return `<div class="page"><h1>Screen recording findings</h1><p>Data files are missing.</p></div>`;
    const student = pack.students.indexOf(q.s) !== -1 ? q.s : "";
    const sessionId = student ? (q.ss || "") : "";
    const who = pack.students.map((s) => `<button type="button" class="person-card${s === student ? " on" : ""}" data-who="${h(s)}" aria-pressed="${s === student ? "true" : "false"}"><span class="person-name">${h(s)}</span></button>`).join("");
    const body = student ? tabs(pack, student, sessionId) : `<p class="frame-prompt">Choose a participant, then a session, to read the coded behaviour for that recording.</p><p><a href="#/explore/recordings">Explore collected frames</a></p>`;
    return `<div class="page wide find-page" id="recFind" data-student="${h(student)}" data-session="${h(sessionId)}">
      <p class="kicker">Findings</p>
      <nav class="crumbs" aria-label="Breadcrumb"><a href="#/findings">Findings</a><span aria-hidden="true">/</span><span aria-current="page">Screen recording findings</span></nav>
      <h1>Screen recording findings</h1>
      <p class="lead">Each frame is coded with a primary behaviour label describing the activity visible in that frame. The results below summarise the distribution and order of these labels; they do not establish what the participant understood.</p>
      <section class="section-block" id="rec-explore">
        <h2>Choose a participant</h2>
        <div class="person-grid" id="recWho">${who}</div>
        <div id="recOut">${body}</div>
      </section>
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
      out.innerHTML = view.s ? tabs(pack, view.s, view.ss) : `<p class="frame-prompt">Choose a participant, then a session, to read the coded behaviour for that recording.</p><p><a href="#/explore/recordings">Explore collected frames</a></p>`;
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
