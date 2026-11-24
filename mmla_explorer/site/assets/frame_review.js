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
   <h1>Etiketlenmiş frame'ler (651)</h1>
   <p>Stratified örneklemden insan kodlayıcı kararları ve makine etiketleri. Her satır bir frame'e karşılık gelir.</p>
   <form id="reviewSearch" style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">
    <input id="reviewFilterId" placeholder="ID ara (örn. R0025)" style="width:9rem">
    <select id="reviewFilterStudent"><option value="">Tüm öğrenciler</option></select>
    <select id="reviewFilterMatch"><option value="">Tüm eşleşmeler</option><option value="1">Eşleşti</option><option value="0">Farklı</option></select>
    <select id="reviewFilterLabel"><option value="">Tüm etiketler</option></select>
    <button type="submit">Filtrele</button>
    <button type="button" id="reviewReset">Sıfırla</button>
    <span id="reviewCount" style="margin-left:auto;align-self:center;font-size:.85rem;color:var(--text-secondary)"></span>
   </form>
   <div class="frame-review-grid">
    <section><h2>Frame listesi</h2><div id="reviewRecordList"></div></section>
    <section id="reviewRecordDetail"><h2>Görüntü ve karar</h2><p class="small">Listeden bir frame seçin.</p></section>
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
    img.src = f.img; img.alt = f.id + ' ekran görüntüsü'; img.loading = 'lazy';
    img.style.maxWidth='100%'; img.style.borderRadius='4px'; img.style.marginBottom='.75rem';
    detail.append(img);
   }
   const matchBadge = f.match
    ? '<span style="color:var(--green,#2a9d6a);font-weight:600">Eşleşti</span>'
    : '<span style="color:var(--red,#c0392b);font-weight:600">Farklı</span>';
   const rows = [
    ['Makine etiketi', label(f.ml) + (f.mc ? ' <small>(' + f.mc + ')</small>' : '')],
    ['İnsan etiketi',  label(f.hl) + (f.hc ? ' <small>(' + f.hc + ')</small>' : '')],
    ['Eşleşme',        matchBadge],
    ['Gözlemlenebilirlik', f.obs || '—'],
    ['İnsan eylemi',   f.act || '—'],
    ['Kanıt / gerekçe',f.ev  || '—'],
    ['Abstain',        f.abstain ? 'Evet' : 'Hayır'],
    ['Orijinal etiket',f.orig_hl || '—'],
    ['Zaman (s)',      f.t != null ? f.t : '—'],
    ['Oturum',         f.session || '—'],
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
