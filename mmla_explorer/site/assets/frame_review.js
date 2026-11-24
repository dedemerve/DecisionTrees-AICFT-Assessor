/* Static labeled-frame browser — shows 651 human-coded frames (661 total minus 10 cached exemplars). */
(function(root){
 'use strict';

 const BEHAVIOR_LABELS = {
  EXPLORE_DATA:'Explore Data', SELECT_TARGET:'Select Target', BUILD_TREE:'Build Tree',
  TUNE_THRESHOLD:'Tune Threshold', EVALUATE_MODEL:'Evaluate Model', COMPARE_MODELS:'Compare Models',
  INTERPRET_RESULTS:'Interpret Results', IDLE_THINKING:'Idle / Thinking', OFF_TASK:'Off Task',
  INSUFFICIENT_EVIDENCE:'Abstain – Insufficient Evidence', UNOBSERVABLE:'Abstain – Unobservable',
  TAXONOMY_GAP:'Abstain – Taxonomy Gap'
 };

 function label(code){ return BEHAVIOR_LABELS[code] || code || '—'; }

 function page(){
  return `<div class="page wide frame-review-page">
   <p class="eyebrow">Behavior coding · human vs machine</p>
   <h1>Labelled frames (651)</h1>
   <p>Human coder decisions and machine labels from the stratified sample. Each row is one frame.</p>
   <form id="reviewSearch" style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">
    <input id="reviewFilterId" placeholder="Find by ID (e.g. R0025)" style="width:9rem">
    <select id="reviewFilterStudent"><option value="">All students</option></select>
    <select id="reviewFilterMatch"><option value="">All matches</option><option value="1">Matched</option><option value="0">Differs</option></select>
    <select id="reviewFilterLabel"><option value="">All labels</option></select>
    <button type="submit">Filter</button>
    <button type="button" id="reviewReset">Reset</button>
    <span id="reviewCount" style="margin-left:auto;align-self:center;font-size:.85rem;color:var(--text-secondary)"></span>
   </form>
   <div class="frame-review-grid">
    <section><h2>Frame list</h2><div id="reviewRecordList"></div></section>
    <section id="reviewRecordDetail"><h2>Image and decision</h2><p class="small">Select a frame from the list.</p></section>
   </div>
  </div>`;
 }

 function bind(){
  const list   = document.getElementById('reviewRecordList');
  const detail = document.getElementById('reviewRecordDetail');
  const count  = document.getElementById('reviewCount');
  if(!list) return;

  const all = (window.LABELED_FRAMES || []);

  /* Populate filter dropdowns */
  const students = [...new Set(all.map(f=>f.student))].sort();
  const selStudent = document.getElementById('reviewFilterStudent');
  students.forEach(s=>{ const o=document.createElement('option'); o.value=s; o.textContent=s; selStudent.append(o); });

  const labels = [...new Set(all.flatMap(f=>[f.ml,f.hl]).filter(Boolean))].sort();
  const selLabel = document.getElementById('reviewFilterLabel');
  labels.forEach(l=>{ const o=document.createElement('option'); o.value=l; o.textContent=label(l); selLabel.append(o); });

  let filtered = all.slice();
  let selected = '';

  function applyFilters(){
   const q   = document.getElementById('reviewFilterId').value.trim().toUpperCase();
   const stu = document.getElementById('reviewFilterStudent').value;
   const mat = document.getElementById('reviewFilterMatch').value;
   const lbl = document.getElementById('reviewFilterLabel').value;
   filtered = all.filter(f=>{
    if(q   && !f.id.includes(q))                        return false;
    if(stu && f.student !== stu)                         return false;
    if(mat === '1' && !f.match)                          return false;
    if(mat === '0' && f.match)                           return false;
    if(lbl && f.ml !== lbl && f.hl !== lbl)              return false;
    return true;
   });
   selected = '';
   draw();
  }

  function draw(){
   count.textContent = filtered.length + ' / ' + all.length + ' frame';
   list.replaceChildren();
   filtered.forEach(f=>{
    const b = document.createElement('button');
    b.className = 'frame-review-record' + (f.match ? '' : ' mismatch');
    b.type = 'button';
    b.dataset.id = f.id;
    b.innerHTML = `<span class="fr-id">${f.id}</span> <span class="fr-student">${f.student}</span> <span class="fr-label ${f.match?'match':'differ'}">${label(f.hl)}</span>`;
    b.onclick = ()=>{ selected = f.id; drawDetail(f); };
    if(f.id === selected) b.classList.add('active');
    list.append(b);
   });
   const sel = filtered.find(f=>f.id===selected);
   if(sel) drawDetail(sel); else { detail.replaceChildren(); const p=document.createElement('p'); p.className='small'; p.textContent='Listeden bir frame seçin.'; detail.append(p); }
  }

  function drawDetail(f){
   detail.replaceChildren();
   const h = document.createElement('h2'); h.textContent = f.id + ' · ' + f.student; detail.append(h);
   if(f.img){
    const img = document.createElement('img');
    img.src = f.img; img.alt = f.id + ' screenshot'; img.loading = 'lazy';
    img.style.maxWidth='100%'; img.style.borderRadius='4px'; img.style.marginBottom='.75rem';
    detail.append(img);
   }
   const matchBadge = f.match
    ? '<span style="color:var(--green,#2a9d6a);font-weight:600">Match</span>'
    : '<span style="color:var(--red,#c0392b);font-weight:600">Differs</span>';
   const rows = [
    ['Machine label',  label(f.ml) + (f.mc ? ' <small>(' + f.mc + ')</small>' : '')],
    ['Human label',    label(f.hl) + (f.hc ? ' <small>(' + f.hc + ')</small>' : '')],
    ['Match',          matchBadge],
    ['Observability',  f.obs || '—'],
    ['Human action',   f.act || '—'],
    ['Evidence',       f.ev  || '—'],
    ['Abstain',        f.abstain ? 'Yes' : 'No'],
    ['Original label', f.orig_hl || '—'],
    ['Timestamp (s)',  f.t != null ? f.t : '—'],
    ['Session',        f.session || '—'],
   ];
   rows.forEach(([title,val])=>{
    const p = document.createElement('p');
    p.innerHTML = `<strong>${title}:</strong> ${val}`;
    detail.append(p);
   });
  }

  document.getElementById('reviewSearch').onsubmit = e=>{ e.preventDefault(); applyFilters(); };
  document.getElementById('reviewReset').onclick   = ()=>{
   document.getElementById('reviewFilterId').value='';
   document.getElementById('reviewFilterStudent').value='';
   document.getElementById('reviewFilterMatch').value='';
   document.getElementById('reviewFilterLabel').value='';
   applyFilters();
  };

  applyFilters();
 }

 root.FrameReview = {page, bind};
})(window);
