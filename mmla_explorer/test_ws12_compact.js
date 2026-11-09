"use strict";
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const c={};c.window=c;c.globalThis=c;vm.createContext(c);
for(const f of ['data/core.js','data/score_extra.js','data/worksheet_docs.js','data/ws12_review.js','data/structural_stopping.js','assets/ws12_review.js','assets/structural_stopping.js','assets/worksheet_findings.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'site',f),'utf8'),c);
const R=c.WS12Review,before=JSON.stringify(c.WS12_REVIEW),html=c.WorksheetFindings.page('WS12');
assert.equal(R.columns.length,10);assert.deepStrictEqual(Array.from(R.columns.flatMap(x=>x.printed)).sort((a,b)=>a-b),Array.from({length:15},(_,i)=>i+1));
assert.equal((html.match(/data-cell-id=/g)||[]).length,130);assert.equal((html.match(/class="sr-name"/g)||[]).length,13);
assert(!html.includes('answer-key-row'));assert(!html.includes('<th scope="col">Expected'));assert(!html.includes('ROOT SPLIT VALID'));
assert(html.includes('class="answer-grid-toggle"'));assert(html.includes('there is no shared answer key'));
assert(html.includes('stat-row cols-4 find-headline'));
assert(html.includes('Answer grid and student results') && html.includes('id="class-analysis"'));
assert(html.includes('Blank / Tree role') && html.includes('Correct / Checked'));
assert(html.includes('63 / 130') && html.includes('Unverified groups'));
assert.equal((html.match(/class="sr-badge /g)||[]).length,13);
assert(!html.includes('Average score') && !html.includes('Median score'));
// The summary and diagnostic denominators exclude all unknown/stop cells.
for(const col of R.columns){
 const cells=c.WS12_REVIEW.groups.flatMap(g=>R.displayItems(g).filter(x=>x.id===col.id).flatMap(x=>g.students.map(()=>x)));
 const checked=cells.filter(x=>['correct','incorrect','partial','blank'].includes(x.status));
 const correct=checked.filter(x=>x.status==='correct').length;
 assert(html.includes(`data-label="Correct / Checked">${correct} / ${checked.length}</td>`));
}
const sample=values=>R.combinedStatus(values.map(status=>({status})));
for(const [values,expected] of [[['correct','correct'],'correct'],[['correct','incorrect'],'incorrect'],[['unknown','incorrect'],'incorrect'],[['correct','unknown'],'unknown'],[['structural_na','structural_na'],'structural_na'],[['structural_na','correct'],'unknown'],[['blank','blank'],'blank'],[['blank','correct'],'partial'],[['partial','correct'],'partial']])assert.equal(sample(values),expected);
const students=Array.from(html.matchAll(/<th class="gc-student-name" scope="row">([^<]*)<\/th>/g),m=>m[1]);
assert.deepStrictEqual(students,Array.from(c.CORE.students).filter(s=>c.WS12_REVIEW.groups.some(g=>g.students.includes(s))));
const tally={};c.WS12_REVIEW.groups.forEach(g=>{const view=R.displayItems(g);assert.equal(view.length,10);view.forEach(v=>tally[v.status]=(tally[v.status]||0)+g.students.length);assert(view.find(v=>v.id==='root_split').response.includes('|'));});
assert.deepStrictEqual(tally,{correct:55,structural_na:22,unknown:45,blank:8});assert.equal(JSON.stringify(c.WS12_REVIEW),before,'Rendering does not change any printed-item judgment or response');
const amy=R.displayItems(c.WS12_REVIEW.groups.find(g=>g.students.includes('Amy')));const bruno=R.displayItems(c.WS12_REVIEW.groups.find(g=>g.students.includes('Bruno')));
assert.equal(amy[0].response,'Enerji');assert.equal(bruno[0].response,'Doymuş Yağ');assert.notEqual(amy[1].response,bruno[1].response);
console.log('PASS compact WS12:130 cells,13 student disclosures,10 groups,15 unique printed items, student-specific responses, preserved source judgments.',tally);
