"use strict";
const assert=require('assert'),fs=require('fs'),vm=require('vm'),path=require('path');
const site=path.join(__dirname,'site');const c={};c.window=c;c.globalThis=c;vm.createContext(c);
const load=f=>vm.runInContext(fs.readFileSync(path.join(site,f),'utf8'),c,{filename:f});
for(const f of ['data/core.js','data/score_extra.js','data/worksheet_docs.js','data/ws12_review.js','data/structural_stopping.js','assets/ws12_review.js'])load(f);
const before={};c.WS12_REVIEW.groups.forEach(g=>g.items.forEach(i=>before[g.page+'|'+i.item]=JSON.stringify(i)));
const other={};c.CORE.students.forEach(s=>Object.keys(c.CORE.ws[s]).filter(w=>!['WS6','WS12'].includes(w)).forEach(w=>other[s+w]=JSON.stringify(c.CORE.ws[s][w])));
load('assets/structural_stopping.js');load('assets/worksheet_findings.js');
assert.equal(c.WS12_REVIEW.version,'20261109-v3-stopping');let changed=0;
c.WS12_REVIEW.groups.forEach(g=>g.items.forEach(i=>{
 const different=before[g.page+'|'+i.item]!==JSON.stringify(i);if(different)changed+=1;
 if(g.page===6 && ['04','06','07','10','11'].some(n=>i.item==='WS12_P'+n)){
  assert(different);assert.equal(i.status,'structural_na');assert.equal(i.score,null);assert(i.researcher_override);assert(i.decision_origin.includes('researcher'));assert(i.previous_status==='blank'||i.previous_status==='unknown');
 }else assert(!different,g.page+' '+i.item+' unchanged');
}));assert.equal(changed,5,'One shared group, five fields, two students');
const html=c.WorksheetFindings.page('WS12');assert(html.includes('| · Valid stop'));assert(html.includes('human applicability codes'));assert(html.includes('downloads/stopping_review/ws12_scoring.json'));
const ws6=c.WorksheetFindings.page('WS6');assert.equal((ws6.match(/data-verdict="structural_na"/g)||[]).length,3,'Zara three distinct displayed fields');assert(ws6.includes('accepted stops (separate)'));assert(ws6.includes('researcher_confirmed_applicability'));
const group=c.WS12_REVIEW.groups.find(g=>g.page===6);assert.equal(group.status_counts.structural_na,5);assert.equal(group.status_counts.unknown,4);assert.equal(group.status_counts.correct,6);
const counts={};c.WS12_REVIEW.groups.forEach(g=>g.items.forEach(i=>counts[i.status]=(counts[i.status]||0)+g.students.length));assert.deepStrictEqual(counts,{correct:76,structural_na:40,unknown:71,blank:8});
c.CORE.students.forEach(s=>Object.keys(c.CORE.ws[s]).filter(w=>!['WS6','WS12'].includes(w)).forEach(w=>assert.equal(JSON.stringify(c.CORE.ws[s][w]),other[s+w])));
const index=fs.readFileSync(path.join(site,'index.html'),'utf8');assert(index.indexOf('data/structural_stopping.js')<index.indexOf('assets/ws12_review.js'));assert(index.indexOf('assets/structural_stopping.js')<index.indexOf('assets/worksheet_findings.js'));
console.log('PASS accepted-stop provenance,13 participant display corrections, no substantive score inflation, unchanged other data, script order.',counts);
