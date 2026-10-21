const {chromium}=require('./qa-deps.cjs').tool('playwright'),path=require('node:path'),fs=require('node:fs'),assert=require('node:assert/strict');
(async()=>{
 const b=await chromium.launch(require('./qa-deps.cjs').browserOptions()),p=await b.newPage({viewport:{width:1440,height:1250}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('file://'+path.join(__dirname,'harness.html'));
 for(const name of ['bridge-visual.js','engine.js','feed.js'])await p.addScriptTag({path:path.join(__dirname,name)});
 const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'native-dax-r04.2.json'),'utf8').replace(/^\uFEFF/,''));
 const result=await p.evaluate(raw=>{
  const roles={'fm_review_files[SourceRevisionID]':'FileID','fm_review_axis[Month]':'Month','[Numerator]':'Numerator','[Denominator]':'Denominator','[NumeratorMissing]':'NumeratorMissing','[DenominatorMissing]':'DenominatorMissing','[FileMetadata]':'FileMetadata','[Catalog]':'Catalog','[Context]':'Context','[Dimensions]':'Dimensions','[Bounds]':'Bounds','fm_review_measures[MetricKey]':'MetricKey','fm_review_facts[Channel]':'Channel','fm_review_facts[SubChannel]':'SubChannel','fm_review_facts[Sector]':'Sector'};
  const names=Object.keys(roles),columns=names.map(n=>({roles:{[roles[n]]:true}})),rows=[];
  for(let i=0;i<32;i++)for(const input of raw){
   const row={...input},suffix='-scenario-'+i;
   row['fm_review_files[SourceRevisionID]']+=suffix;
   if(row['[FileMetadata]']){const f=JSON.parse(row['[FileMetadata]']);f.id+=suffix;f.path+=suffix;f.filename+=suffix;f.profile=i%2?'Local':'Ext';row['[FileMetadata]']=JSON.stringify(f);}
   rows.push(names.map(n=>row[n]));
  }
  const view={table:{columns,rows}},started=performance.now(),feed=CycleFeed.decode(view),decodeMs=performance.now()-started;
  let queries=0;const root=document.getElementById('fm-review-preview');root.replaceChildren();const app=ReviewEngine.mount(root,feed,{affiliate:'UK',cycles:['2026-07','2026-10'],drivers:['Core Oral'],profile:'Ext',metric:'ims-market-units'},()=>queries++,()=>{});
  const times=[];
  for(let i=0;i<20;i++){const before=performance.now(),el=root.querySelector('[data-field=metric]');el.value=i%2?'ims-market-units':'ims-volume-share';el.dispatchEvent(new Event('change',{bubbles:true}));times.push(performance.now()-before);}
  const profile=root.querySelector('.fm-profile');profile.value='Local';profile.dispatchEvent(new Event('change',{bubbles:true}));
  const local=app.getState().profile,profileLoading=!root.querySelector('.fm-loading').hidden;
  app.destroy();
  // Verify a late old response cannot replace the cycle selected by the operator.
  const small={table:{columns,rows:raw.map(r=>names.map(n=>r[n]))},metadata:{objects:{general:{state:JSON.stringify({affiliate:'UK',cycles:['2026-07','2026-10'],drivers:['Core Oral'],profile:'Ext',metric:'ims-market-units'})}}}};
  const outer=document.createElement('div');document.body.append(outer);let fetches=0;
  const v=new NativeReview.Visual({element:outer,host:{applyJsonFilter:()=>{},persistProperties:()=>{},fetchMoreData:()=>{fetches++;return true;}}});v.update({dataViews:[small]});
  outer.querySelector('[data-multi=cycles] input[value="2026-07"]').click();
  const oct=structuredClone(small),ci=names.indexOf('[Context]');for(const r of oct.table.rows)if(r[ci])r[ci]=JSON.stringify({...JSON.parse(r[ci]),cycles:['2026-10'],cycle:'2026-10'});
  v.update({dataViews:[oct]});const snapshot=v.app.snapshot();v.update({dataViews:[small]});const staleIgnored=v.app.snapshot()===snapshot;
  v.update({dataViews:[{...oct,metadata:{segment:{}}}]});const partial={retainsCompleteView:v.app.snapshot()===snapshot,fetches};v.destroy();outer.remove();
  times.sort((a,b)=>a-b);return {rows:rows.length,files:feed.files.length,decodeMs,medianMs:times[10],p95Ms:times[19],queries,local,profileLoading,staleIgnored,partial};
 },fixture.Queries['complete-cycle'].Rows);
 assert.equal(result.rows,53984);assert.equal(result.files,128);assert.equal(result.queries,0);assert.equal(result.local,'Local');assert.equal(result.profileLoading,false);assert.equal(result.staleIgnored,true);assert.deepEqual(result.partial,{retainsCompleteView:true,fetches:1});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(__dirname,'cycle-stress-results.json'),JSON.stringify({Status:'PASS',...result,PageErrors:errors},null,2));console.log(JSON.stringify({Status:'PASS',...result},null,2));await b.close();
})().catch(e=>{console.error(e);process.exit(1)});
