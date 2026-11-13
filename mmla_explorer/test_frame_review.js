const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const elements=new Map();function element(){return {textContent:'',value:'',isConnected:true,children:[],append(...v){this.children.push(...v);},replaceChildren(){this.children=[];}};}
for(const id of ['reviewRecordList','reviewRecordDetail','reviewLiveStatus','reviewSearch','reviewFrameId','reviewReset'])elements.set(id,element());
let timer,fetches=0;
const record={reviewId:'R0025',author:'Kodlayıcı 1',authorTag:'owner',image:'https://huggingface.co/frame.jpg',savedAt:'2026-11-13T15:00:00Z',record:{label:'BUILD_TREE',action:'Gözlenen eylem',evidence:'Kanıt',submitted:false}};
const context={window:{},document:{getElementById:id=>elements.get(id),createElement:element,createTextNode:x=>x},fetch:async()=>({ok:true,json:async()=>{fetches++;return {records:[record],counts:{records:1}};}}),setInterval:f=>(timer=f,1),clearInterval(){},Date,Number,Error,encodeURIComponent};
vm.runInNewContext(fs.readFileSync(path.join(__dirname,'site/assets/frame_review.js'),'utf8'),context);
assert(context.window.FrameReview.page().includes('Kayıt ekle'));
context.window.FrameReview.bind();
setImmediate(async()=>{
 assert.equal(fetches,1);assert(elements.get('reviewLiveStatus').textContent.includes('Canlı'));
 assert(elements.get('reviewRecordDetail').children.some(x=>x.src==='https://huggingface.co/frame.jpg'));
 record.record.action='Güncellenen karar';await timer();
 assert(elements.get('reviewRecordDetail').children.some(x=>x.children?.includes('Güncellenen karar')));
 const index=fs.readFileSync(path.join(__dirname,'site/index.html'),'utf8');assert(index.includes('href="#/review"'));assert(index.indexOf('assets/frame_review.js')<index.indexOf('assets/app.js'));
 console.log('PASS frame review route, navigation, public API view, image and automatic live updates.');
});
