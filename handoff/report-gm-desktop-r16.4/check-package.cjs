const {chromium}=require('C:\\Users\\Ayush\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});const page=await browser.newPage({viewport:{width:1480,height:1100},timezoneId:'Europe/London'});const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('file:///'+path.join(__dirname,'local-test/index.html').replace(/\\/g,'/'));
 const view=JSON.parse(fs.readFileSync(path.join(__dirname,'local-test/feed.json'),'utf8'));
 // Actual host-style timestamp strings, not the prototype's bare YYYY-MM values.
 const timestamps=await page.evaluate(v=>v.table.rows.map(r=>{const[y,m]=r[1].split('-').map(Number);return new Date(y,m-1,1).toISOString();}),view);
 view.table.rows.forEach((r,i)=>r[1]=timestamps[i]);
 const startup=await page.evaluate(v=>{
  window.testView=v;
  visual.update({dataViews:[],type:2});
  const first=document.getElementById('host').textContent;
  const segment={...v,metadata:{...v.metadata,segment:{}},table:{...v.table,rows:v.table.rows.slice(0,10000)}};
  visual.update({dataViews:[segment],type:2,operationKind:0});
  const loading=document.getElementById('host').textContent;
  const overlap=[...v.table.rows.slice(0,10000),structuredClone(v.table.rows[9999]),...v.table.rows.slice(10000)];
  visual.update({dataViews:[{...v,table:{...v.table,rows:overlap}}],type:2,operationKind:1});
  return {first,loading,failed:hostCalls.failed,fetch:hostCalls.fetch};
 },view);
 assert.match(startup.first,/Waiting for saved reporting data/);assert.match(startup.loading,/Loading the saved monthly data once/);assert.deepStrictEqual(startup.failed,[]);assert.equal(startup.fetch,1);
 await page.waitForTimeout(300);
 const initial=await page.evaluate(()=>({text:document.getElementById('host').innerText.slice(0,350),failed:hostCalls.failed,state:document.querySelector('#fm-connected-review-r15')?.reviewSession?.getState(),charts:document.querySelectorAll('svg').length}));
 fs.writeFileSync(path.join(__dirname,'local-test/initial.json'),JSON.stringify(initial,null,2));
 assert.deepStrictEqual(initial.failed,[]);assert(initial.state,'Expected packaged page to render');assert(initial.charts>0,'Expected real feed chart');
 const result=await page.evaluate(()=>{
  const demand=document.querySelector('#fm-connected-demand-r15').fmDesign,sop=document.querySelector('#fm-connected-sop-r15').sopDesign,root=document.querySelector('#fm-connected-review-r15'),fx=root.planFX;
  const combo=demand.combos()[0],subset=demand.activeSectors(),metric=demand.catalog.find(m=>m.id==='market-units'),months=demand.periodMonths('2026:FY',combo,metric);
  const plan=demand.amount(combo,subset,metric,months),trend=demand.amount(combo,subset,metric,months,12);
  root.reviewSession.navigate('sop');sop.setState({channels:['community'],targets:['community'],selectedMeasures:['market','abbott','share','pi','net','community'],showRunRate:true,showGrowth:true});
  const group=sop.groups()[0],row=id=>sop.rows.find(r=>r.id===id),sopMonths=sop.periodMonths(row('market'),'2026:FY','2026-10');
  const sopMarket=sop.localAmount(row('market'),group,sopMonths,'2026-10'),share=sop.localAmount(row('share'),group,sopMonths,'2026-10');
  const before=JSON.stringify(sop.getState());document.querySelector('#sb-graph-toggle').click();document.querySelector('#sb-graph-toggle').click();const after=JSON.stringify(sop.getState());
  fx.setState({currency:'USD',rates:{GBP:2}});sop.setState({display:'value'});const converted=sop.amount(row('abbott'),sop.groups()[0],sopMonths,'2026-10');
  fx.setState({rates:{GBP:0}});const zero=sop.amount(row('abbott'),sop.groups()[0],sopMonths,'2026-10');
  fx.setState({rates:{}});const missing=sop.amount(row('abbott'),sop.groups()[0],sopMonths,'2026-10');
  const times=[];for(let i=0;i<12;i++){const start=performance.now();sop.setState({grouping:i%2?'combined':'sector'});times.push(performance.now()-start);}
  root.reviewSession.navigate('demand');return {plan,trend,sopMarket,share,converted,zero,missing,hideRestores:before===after,hostCalls,tableHeaders:document.querySelectorAll('#sb-summary-panel th').length,times};
 });
 assert.equal(result.plan,62160);assert.equal(result.sopMarket,62160);assert(Math.abs(result.trend-62160)<1e-7);assert(Math.abs(result.share-0.1)<1e-10);
 assert.equal(result.converted,62160);assert.equal(result.zero,0);assert.equal(result.missing,null);assert(result.hideRestores);assert.equal(result.hostCalls.fetch,1);assert(result.tableHeaders>=6);
 // A new host delivery, including same-sized data, must invalidate every derived value.
 await page.evaluate(()=>{const next=structuredClone(testView);for(const r of next.table.rows)if(r[2]==='gm-market-units')r[6]+=1;visual.update({dataViews:[next],type:2});});
 const refreshed=await page.evaluate(()=>{const a=document.querySelector('#fm-connected-demand-r15').fmDesign,c=a.combos()[0],m=a.catalog.find(m=>m.id==='market-units');return a.amount(c,a.activeSectors(),m,a.periodMonths('2026:FY',c,m));});
 assert.equal(refreshed,62208);
 await page.evaluate(()=>document.querySelector('#fm-connected-review-r15').planFX.setState({currency:'local',rates:{}}));
 await page.screenshot({path:path.join(__dirname,'local-test/demand.png'),fullPage:true});
 await page.evaluate(()=>document.querySelector('#fm-connected-review-r15').reviewSession.navigate('sop'));
 assert(await page.locator('[data-fx-controls="sop"] [data-fx-open]').isVisible(),'Plan rates must remain visible on S&OP');
 await page.locator('[data-fx-controls="sop"] [data-fx-open]').click();
 assert(await page.locator('#cr-fx-dialog-sop').isVisible());
 await page.locator('#cr-fx-dialog-sop [data-fx-close]').click();
 await page.screenshot({path:path.join(__dirname,'local-test/sop.png'),fullPage:true});
 assert.deepStrictEqual(errors,[]);result.refreshed=refreshed;result.browserErrors=errors;result.startup=startup;result.overlapHandled=true;
 result.evidence='SYNTHETIC FIXTURE - packaged visual in headless Edge; no company connection';result.fixtureRows=view.table.rows.length;
 fs.writeFileSync(path.join(__dirname,'VALIDATION-BROWSER.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
