const {chromium}=require('./qa-deps.cjs').tool('playwright'),fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const rows=JSON.parse(fs.readFileSync(path.join(__dirname,'native-dax-raw.json'),'utf8').replace(/^\uFEFF/,''));
const columns={
 'fm_review_files[SourceRevisionID]':'FileID','fm_review_axis[Month]':'Month','[Numerator]':'Numerator','[Denominator]':'Denominator','[FileMetadata]':'FileMetadata','[Catalog]':'Catalog','[Context]':'Context','[Dimensions]':'Dimensions','[Bounds]':'Bounds',
 'fm_review_reference[Country]':'Country','fm_review_reference[DemandCycle]':'DemandCycle','fm_review_reference[GrowthDriver]':'GrowthDriver','fm_review_reference[SourceProfile]':'SourceProfile','fm_review_measures[MetricKey]':'MetricKey','fm_review_facts[Channel]':'Channel','fm_review_facts[SubChannel]':'SubChannel','fm_review_facts[Sector]':'Sector'};
const views={};for(const [name,result]of Object.entries(rows.Queries)){assert.equal(result.Status,'PASS');const names=Object.keys(columns);views[name]={table:{columns:names.map(n=>({displayName:n,roles:{[columns[n]]:true}})),rows:result.Rows.map(r=>names.map(n=>r[n]))}};}
(async()=>{
 const b=await chromium.launch(require('./qa-deps.cjs').browserOptions()),p=await b.newPage({viewport:{width:1440,height:1250}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto('file://'+path.join(__dirname,'harness.html'));await p.addScriptTag({path:path.join(__dirname,'native-visual.js')});await p.addScriptTag({path:path.join(__dirname,'engine.js')});
 const result=await p.evaluate(views=>{
  const decoded={};for(const [key,view]of Object.entries(views))decoded[key]=NativeReview.decode(view);
  const m=decoded['ims-market-units'];window.nativeDecoded=decoded;
  const state={affiliate:'UK',cycles:['2026-07','2026-10'],drivers:['Core Oral','Paed SIP'],profile:'Ext',metric:'ims-market-units',periodStart:36,periodEnd:59,reviewPeriods:['2026:FY'],periodsFollowContext:false,monthsFollowCycle:false};
  window.app=ReviewEngine.mount(document.getElementById('fm-review-preview'),m,state,s=>queueMicrotask(()=>app.update(decoded[s.metric])),()=>{});
  return {fileCount:m.files.length,parts:[...m.values.values()].flatMap(r=>r.parts).filter(p=>p.n!==null).length,context:m.context,dimensions:m.dimensions};
 },views);
 assert.equal(result.fileCount,4);assert.equal(result.parts,240);assert.deepEqual(result.context.cycles,['2026-07','2026-10']);assert.deepEqual(result.context.drivers,['Core Oral','Paed SIP']);
 const oop=result.dimensions.find(d=>d.channel==='Out of Pocket');assert.deepEqual([...oop.metrics].sort(),['ef-selling-units','ef-value']);
 const first=await p.evaluate(()=>app.snapshot());assert.deepEqual(first.months.find(m=>m.t===41).plans.map(p=>p.value),[564,3082]);
 await p.locator('[data-field=metric]').selectOption('ims-volume-share');await p.waitForTimeout(100);
 const share=await p.evaluate(()=>app.snapshot());assert.ok(Math.abs(share.months.find(m=>m.t===41).plans[1].value-(1041*.1+2041*.5)/3082)<1e-12);
 await p.locator('[data-field=channel]').selectOption('Out of Pocket');await p.waitForTimeout(100);
 const ef=await p.evaluate(()=>({s:app.getState(),snapshot:app.snapshot()}));assert.equal(ef.s.metric,'ef-selling-units');assert.deepEqual(ef.snapshot.months.find(m=>m.t===45).plans.map(p=>p.value),[0,0]);assert.deepEqual(errors,[]);
 await p.screenshot({path:path.join(__dirname,'native-feed-R04.png'),fullPage:true});await b.close();
 const legacyBrowser=await chromium.launch(require('./qa-deps.cjs').browserOptions()),legacyPage=await legacyBrowser.newPage();
 await legacyPage.goto('file://'+path.join(__dirname,'harness.html'));await legacyPage.addScriptTag({path:path.join(__dirname,'native-visual.js')});await legacyPage.addScriptTag({path:path.join(__dirname,'legacy-engine.js')});
 const legacy=await legacyPage.evaluate(view=>{const feed=NativeReview.decode(view);let requests=0;const app=LegacyEngine.mount(document.getElementById('fm-review-preview'),feed,{affiliate:'UK',cycle:'2026-07',driver:'Core Oral',profile:'Ext',metric:'ims-market-units',periodStart:36,periodEnd:59},()=>requests++,()=>{});return {context:feed.context,requests,snapshot:app.snapshot()};},views['legacy-single-cohort']);
 assert.equal(legacy.context.cycle,'2026-07');assert.equal(legacy.context.driver,'Core Oral');assert.equal(legacy.requests,0);assert.equal(legacy.snapshot.months.find(m=>m.t===41).plans[0].value,282);await legacyBrowser.close();
 const summary={Status:'PASS',NativeDaxQueries:4,NumericRowsPerMultiSelectionQuery:240,LegacySingleCohortNumericRows:60,Checks:['Native DAX includes four source identities across two cycles and two drivers','Native aggregate rows are not multiplied across reference groupings','Native compact availability maps to metric identities','Native units totals reconcile to the raw synthetic facts','Native shares use combined numerator and denominator','Native channel change selects the valid EF family','Native zero-valued EF month remains valid','Legacy R03.2 renderer remains usable with the upgraded single-cohort feed'],Evidence:result,Legacy:{context:legacy.context,scopeRequests:legacy.requests},PageErrors:errors};
 fs.writeFileSync(path.join(__dirname,'native-feed-results.json'),JSON.stringify(summary,null,2));console.log(JSON.stringify({Status:summary.Status,Checks:summary.Checks},null,2));
})().catch(e=>{console.error(e);process.exit(1)});
