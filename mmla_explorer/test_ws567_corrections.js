'use strict';
const fs = require('fs'), vm = require('vm'), assert = require('assert');
const root = __dirname + '/site/';
const ctx = {console}; ctx.window = ctx; vm.createContext(ctx);
for (const f of ['data/core.js','assets/worksheet_findings.js']) vm.runInContext(fs.readFileSync(root+f,'utf8'),ctx);
const ws5=ctx.WorksheetFindings.page('WS5'), ws6=ctx.WorksheetFindings.page('WS6'), ws7=ctx.WorksheetFindings.page('WS7');
assert(ws5.includes('Enerji ve Şeker'));
assert(ws6.includes('&gt; 11 | &lt; 11'), 'Recovered Sheila operators must remain visible, including her incorrect pair');
assert(ws6.includes('≤ 13.5 | &gt; 13.5'), 'Bruno constant-left inequalities must normalize to feature-left');
assert(ws7.includes('&lt; 7,7 g') && ws7.includes('≥ 180 kcal'));
const r=ctx.CORE.ws.Amy.WS7.ocr.responses;
assert.equal(r.find(x=>x.item==='WS7_1').value,'(blank)');
assert.equal(ctx.CORE.ws.Sheila.WS7.scoring.total_score,2);
for (const s of ctx.CORE.students.filter(s=>!['Melinda','Serena','Sheila'].includes(s))) assert.equal(ctx.CORE.ws[s].WS7.scoring.total_score,0,s);
// Same numeric threshold with a noncomplementary pair cannot receive a green cell.
const html=ws6.match(/<tr><th class="gc-student-name">Sheila<\/th>[\s\S]*?<\/tr>/)[0];
assert(html.includes('gc-wrong') && html.includes('&gt; 11 | &lt; 11'));
console.log('PASS WS5 multi-feature answer, WS6 operators and WS7 fixed-key responses/scores');
