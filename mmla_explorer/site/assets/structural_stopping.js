/* Apply documented human-adjudicated applicability exceptions after base WS12 checks. */
(function(root){
 "use strict";
 const policy=root.STRUCTURAL_STOPPING;
 if(!policy||!root.WS12_REVIEW||!root.CORE)return;
 if(root.WS12_REVIEW.version!=="20261109-v2")throw Error("Stopping review requires its frozen base WS12 revision.");
 // Mutate the same object retained by the renderer; do not replace that reference.
 Object.assign(root.WS12_REVIEW,policy.ws12_merged_review);
 const data=root.WS12_REVIEW;
 const meta=root.CORE.worksheets.find(w=>w.code==="WS12");
 if(meta)meta.rubric_data=data.rubric;
 data.groups.forEach(g=>g.students.forEach(student=>{
  const rec=root.CORE.ws[student].WS12;
  rec.revision=data.version;
  rec.stage.scoring.source="downloads/stopping_review/ws12_scoring.json";
  rec.stage.scoring.items=g.items;
  rec.stage.scoring.n_review=g.status_counts.unknown||0;
  rec.ocr.checks=g.items.map(it=>({check:"item_checks."+it.item,correct:it.status==="correct"?true:it.status==="incorrect"?false:null,flag:it.status,note:it.note,detail:{status:it.status,page:it.page,accepted_as_correct_action:it.status==="structural_na",decision_origin:it.decision_origin||it.method}}));
 }));
})(typeof window!=="undefined"?window:globalThis);
