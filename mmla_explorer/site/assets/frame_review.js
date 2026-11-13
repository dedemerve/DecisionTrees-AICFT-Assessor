/* Shared, account-free review view. Editing stays on the persistent service. */
(function(root){
 'use strict';
 const service='https://codap-frame-review.delightfuldrift2.chatgpt.site';
 let timer=null;
 function page(){return `<div class="page wide frame-review-page"><p class="eyebrow">Collaborative validation</p><h1>Frame değerlendirme</h1><p>Ortak kararlar beş saniyede bir güncellenir. Her kodlayıcının kararı ve yazdığı gerekçe ayrı saklanır.</p><p><a class="btn-primary" href="${service}/join.html" target="_blank" rel="noopener">Kayıt ekle / değerlendirmeye devam et</a> <a class="btn-secondary" href="${service}/shared.html" target="_blank" rel="noopener">Ortak görünümü ayrı aç</a></p><p class="small">Kayıtları görmek için hesap gerekmez. Kayıt eklemek için katılım kodu kullanılır; yazdıklarınız otomatik kaydedilir.</p><p id="reviewLiveStatus" role="status">Kayıtlar yükleniyor…</p><form id="reviewSearch"><label for="reviewFrameId">Örnek numarası</label> <input id="reviewFrameId" placeholder="Örn. R0025" pattern="[RrFf][0-9]{4}"> <button type="submit">Filtrele</button> <button type="button" id="reviewReset">Son kararlar</button></form><div class="frame-review-grid"><section><h2>Kaydedilen kararlar</h2><div id="reviewRecordList"></div></section><section id="reviewRecordDetail"><h2>Görüntü ve karar</h2></section></div></div>`;}
 function bind(){
  clearInterval(timer);const list=document.getElementById('reviewRecordList'),detail=document.getElementById('reviewRecordDetail'),status=document.getElementById('reviewLiveStatus');if(!list)return;
  let records=[],selected='',frame='',loading=false;
  const key=r=>r.reviewId+'|'+r.authorTag;
  function draw(){
   list.replaceChildren();for(const r of records){const b=document.createElement('button');b.className='frame-review-record';b.type='button';b.textContent=r.reviewId+' · '+r.author+' · '+(r.record.label||'Taslak');b.onclick=()=>{selected=key(r);draw();};list.append(b);}
   const r=records.find(r=>key(r)===selected)||records[0];detail.replaceChildren();
   if(!r){const p=document.createElement('p');p.textContent='Bu örnek için henüz ortak kayıt yok.';detail.append(p);return;}
   selected=key(r);const h=document.createElement('h2');h.textContent=r.reviewId+' · '+r.author;detail.append(h);
   if(r.image){const img=document.createElement('img');img.src=r.image;img.alt=r.reviewId+' ekran görüntüsü';img.loading='lazy';detail.append(img);}
   for(const [title,value] of [['Davranış',r.record.label||'Henüz seçilmedi'],['Gözlenen eylem',r.record.action||'—'],['Kanıt / gerekçe',r.record.evidence||'—'],['Not',r.record.note||'—'],['Durum',r.record.submitted?'Tamamlandı':'Taslak · yazım sürüyor'],['Kodlayıcı',r.author+' · '+r.authorTag],['Son kayıt',new Date(r.savedAt).toLocaleString('tr-TR',{timeZone:'Europe/Istanbul'})]]){const p=document.createElement('p'),b=document.createElement('strong');b.textContent=title+': ';p.append(b,document.createTextNode(value));detail.append(p);}
   const a=document.createElement('a');a.href=service+'/join.html?returnTo='+encodeURIComponent('/review.html#'+r.reviewId);a.target='_blank';a.rel='noopener';a.textContent='Bu frame için kendi kararını ekle';detail.append(a);
  }
  async function refresh(){
   if(!list.isConnected){clearInterval(timer);return;}if(loading)return;loading=true;
   try{const res=await fetch(service+'/api/shared'+(frame?'?frame='+encodeURIComponent(frame):''),{cache:'no-store'});const data=await res.json();if(!res.ok)throw Error(data.error||'Kayıtlar yüklenemedi.');if(!list.isConnected)return;records=data.records;draw();status.textContent='Canlı · '+(Number(data.counts?.records||0)+20)+' karar kaydı · '+new Date().toLocaleTimeString('tr-TR');}
   catch(error){status.textContent='Bağlantı bekleniyor: '+error.message;}finally{loading=false;}
  }
  document.getElementById('reviewSearch').onsubmit=e=>{e.preventDefault();frame=document.getElementById('reviewFrameId').value.trim().toUpperCase();selected='';refresh();};
  document.getElementById('reviewReset').onclick=()=>{frame='';selected='';document.getElementById('reviewFrameId').value='';refresh();};
  refresh();timer=setInterval(refresh,5000);
 }
 root.FrameReview={page,bind};
})(window);
