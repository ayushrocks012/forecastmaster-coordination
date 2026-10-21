const {chromium}=require('./qa-deps.cjs').tool('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch(require('./qa-deps.cjs').browserOptions()),page=await browser.newPage({viewport:{width:1440,height:1250}}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));await page.goto('file://'+path.join(__dirname,'harness.html'));
 for(const name of ['engine.js','bridge-visual.js','feed.js'])await page.addScriptTag({path:path.join(__dirname,name)});
 const fixture=JSON.parse(fs.readFileSync(path.join(__dirname,'native-dax-r04.2.json'),'utf8').replace(/^\uFEFF/,''));
 const initial=await page.evaluate(queries=>{
  const roles={'fm_review_files[SourceRevisionID]':'FileID','fm_review_axis[Month]':'Month','[Numerator]':'Numerator','[Denominator]':'Denominator','[FileMetadata]':'FileMetadata','[Catalog]':'Catalog','[Context]':'Context','[Dimensions]':'Dimensions','[Bounds]':'Bounds','fm_review_measures[MetricKey]':'MetricKey','fm_review_facts[Channel]':'Channel','fm_review_facts[SubChannel]':'SubChannel','fm_review_facts[Sector]':'Sector'};
  const names=Object.keys(roles),rows=[];
  for(const [metric,result]of Object.entries(queries))if(metric!=='legacy-single-cohort')for(const raw of result.Rows){const r={...raw};if(r['[Context]'])r['[Context]']=JSON.stringify({...JSON.parse(r['[Context]']),schema:5,complete:true});rows.push(names.map(n=>r[n]));}
  window.view={table:{columns:names.map(n=>({roles:{[roles[n]]:true}})),rows}};window.feed=CycleFeed.decode(view);window.requests=[];
  window.app=ReviewEngine.mount(document.getElementById('fm-review-preview'),feed,{affiliate:'UK',cycles:['2026-07','2026-10'],drivers:['Core Oral','Paed SIP'],profile:'Ext',metric:'ims-market-units',periodStart:36,periodEnd:59,reviewPeriods:['2026:FY'],periodsFollowContext:false,monthsFollowCycle:false},s=>requests.push(s),()=>{});
  return {rows:rows.length,requests:requests.length,snapshot:app.snapshot(),values:feed.metricValues.size};
 },{'complete-cycle':fixture.Queries['complete-cycle']});
 assert.equal(initial.requests,0);assert.equal(initial.values,7);assert.deepEqual(initial.snapshot.months.find(m=>m.t===41).plans.map(p=>p.value),[564,3082]);
 const timings=[];
 async function select(selector,value){const elapsed=await page.evaluate(({selector,value})=>{const start=performance.now(),el=document.querySelector(selector);el.value=value;el.dispatchEvent(new Event('change',{bubbles:true}));return performance.now()-start;},{selector,value});timings.push(elapsed);assert.equal(await page.locator('.fm-loading').getAttribute('hidden'),'');}
 await select('[data-field=metric]','ims-volume-share');
 const share=await page.evaluate(()=>app.snapshot());assert.ok(Math.abs(share.months.find(m=>m.t===41).plans[1].value-(1041*.1+2041*.5)/3082)<1e-12);
 await select('[data-field=channel]','Out of Pocket');assert.equal(await page.evaluate(()=>app.getState().metric),'ef-selling-units');assert.deepEqual((await page.evaluate(()=>app.snapshot())).months.find(m=>m.t===45).plans.map(p=>p.value),[0,0]);
 await select('[data-field=channel]','all');await select('[data-field=family]','IMS / Market');
 for(let i=0;i<12;i++)await select('[data-field=metric]',i%2?'ims-market-units':'ims-volume-share');
 assert.equal(await page.evaluate(()=>requests.length),0,'No host query for any loaded-cycle measure or dimension switch');
 // A driver set is also local, and availability must use that set's file identities.
 await page.locator('[data-multi=drivers] summary').click();await page.locator('[data-multi=drivers] input[value="Paed SIP"]').uncheck();await page.locator('[data-multi=drivers] summary').click();assert.equal(await page.evaluate(()=>requests.length),0);
 const availability=await page.evaluate(()=>{
  const f={catalog:[{id:'ratio',aggregation:'RATIO'},{id:'sum',aggregation:'SUM'}],presence:new Map([['a',new Map([['x',{channel:'A',subchannel:'',sector:'S',metrics:new Map([['ratio',1],['sum',1]])}]])],['b',new Map([['x',{channel:'A',subchannel:'',sector:'S',metrics:new Map([['ratio',2]])}]])]])};
  return {one:CycleFeed.dimensionsFor(f,[{id:'a'}])[0].metrics,both:CycleFeed.dimensionsFor(f,[{id:'a'},{id:'b'}])[0].metrics};
 });assert.deepEqual(availability.one,['sum']);assert.deepEqual(availability.both,['ratio','sum']);
 const host=await page.evaluate(()=>{
  const applied=[];const element=document.createElement('div'),v=new NativeReview.Visual({element,host:{applyJsonFilter:f=>applied.push(f),persistProperties:()=>{}}});
  document.body.append(element);v.update({dataViews:[view]});v.filter({affiliate:'UK',cycles:['2026-10'],drivers:['Core Oral'],profile:'Ext',metric:'ef-selling-units'});
  const actual=applied.at(-1);v.destroy();element.remove();return actual;
 });assert.deepEqual(host.map(f=>f.target.column),['Country','DemandCycle']);
 // Explicitly incomplete metadata must ask for the full cycle, even if its key matches.
 const incomplete=await page.evaluate(()=>{const root=document.createElement('div');document.body.append(root);let queries=0;const test=ReviewEngine.mount(root,{...feed,context:{...feed.context,complete:false}},{...app.getState()},()=>queries++,()=>{});const result={queries,loading:!root.querySelector('.fm-loading').hidden};test.destroy();root.remove();return result;});assert.equal(incomplete.queries,1);assert.equal(incomplete.loading,true);
 const missingDriver=await page.evaluate(()=>{const root=document.createElement('div');document.body.append(root);let count=0;const next={...feed,files:feed.files.map((f,i)=>i===0?{...f,driver:'Infant'}:f),context:{...feed.context,cycles:['2026-07']}};const test=ReviewEngine.mount(root,next,{...app.getState(),cycles:['2026-07','2026-10'],drivers:['Infant','Paed SIP'],selected:[],selectionsInitialised:false},()=>count++,()=>{});test.destroy();root.remove();return count;});assert.equal(missingDriver,1,'A cycle load starts even while the selected driver set is incomplete');
 const replacement=await page.evaluate(()=>{
  const copy=structuredClone(view);for(const row of copy.table.rows){const roles=copy.table.columns;const ni=roles.findIndex(c=>c.roles.Numerator),mi=roles.findIndex(c=>c.roles.MetricKey);if(row[mi]==='ims-market-units'&&typeof row[ni]==='number')row[ni]*=2;}
  app.update(CycleFeed.decode(copy));return app.snapshot();
 });assert.equal(replacement.months.find(m=>m.t===41).plans.find(p=>p.value===2082)?.value,2082,'A new model feed replaces cached values');
 // Progressive fetch cannot present an old complete chart as if it were the new result.
 const segment=await page.evaluate(()=>{let fetch=0;const el=document.createElement('div'),v=new NativeReview.Visual({element:el,host:{fetchMoreData:()=>{fetch++;return false;}}});v.update({dataViews:[{...view,metadata:{segment:{}}}]});return {fetch,text:el.textContent};});assert.equal(segment.fetch,1);assert.match(segment.text,/Partial results are not displayed/);
 assert.deepEqual(errors,[]);await page.screenshot({path:path.join(__dirname,'cycle-cache.png'),fullPage:true});await browser.close();
 const sorted=[...timings].sort((a,b)=>a-b),summary={Status:'PASS',FixtureRows:initial.rows,LocalChanges:timings.length,HostQueriesForLocalChanges:0,MedianMs:sorted[Math.floor(sorted.length*.5)],P95Ms:sorted[Math.floor(sorted.length*.95)],MaxMs:sorted.at(-1),Checks:['Per-metric data isolation','Weighted share reconciliation','Zero-valued EF month','Channel availability fallback','Driver-set availability','No model query for local changes','Incomplete cycle handshake','Refresh replaces loaded values','Fetch limit reports incomplete result'],PageErrors:errors};
 fs.writeFileSync(path.join(__dirname,'cycle-cache-results.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify(summary,null,2));
})().catch(e=>{console.error(e);process.exit(1)});
