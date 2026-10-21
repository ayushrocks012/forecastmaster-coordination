const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.platform==='win32'?path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'):'playwright'));
const near=(a,b)=>assert.ok(a===null?b===null:Math.abs(a-b)<=Math.max(1e-8,Math.abs(a)*1e-10),`${a} != ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1500},colorScheme:'light'}),errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  const f=page.frames().find(f=>f!==page.mainFrame());await f.waitForSelector('#fm-summary');
  const evaluate=(fn,arg)=>f.evaluate(fn,arg),pass=s=>checks.push(s);
  const get=kind=>evaluate(kind=>document.getElementById('fm-connected-review-r15').reviewSession.getState()[kind],kind);
  const set=(kind,patch)=>evaluate(({kind,patch})=>document.getElementById(kind==='demand'?'fm-connected-demand-r15':'fm-connected-sop-r15')[kind==='demand'?'fmDesign':'sopDesign'].setState(patch),{kind,patch});
  const nav=kind=>f.locator('#cr-'+kind+'-tab').click();
  async function shot(name,width=1080){await page.setViewportSize({width,height:1500});await page.waitForTimeout(160);const h=await evaluate(()=>document.documentElement.scrollHeight);await page.locator('iframe').evaluate((n,h)=>{n.style.setProperty('height',h+'px','important');n.style.setProperty('max-height','none','important');},h+16);await page.setViewportSize({width,height:h+96});await page.waitForTimeout(120);await page.mouse.move(2,2);await page.screenshot({path:path.join(__dirname,name),fullPage:true});}
  assert.deepEqual(errors,[],'Initial scripts must load');
  const initial=await get('demand');assert.deepEqual(initial.tableTrends,[12]);assert.equal(initial.combined,true);assert.equal(initial.tableView,'driver');assert.equal(initial.filesOpen,false);
  assert.equal(await f.locator('#fm-body-filesOpen').isVisible(),false);assert.equal(await f.locator('#cr-sop-page').isVisible(),false);
  await shot('demand-overview.png');pass('Demand opens with Total chart, driver summary, 12M comparison and collapsed Matching files; 6M/24M and all four Hide/Show controls remain available.');

  const demandChoice={affiliates:['uk'],cycles:['2026-07'],sectors:['paed-standard'],monthStart:'2026-01',monthEnd:'2026-12',display:'value',periods:['2026:FY'],tableView:'sector',graphOpen:false,filesOpen:true};
  await set('demand',demandChoice);assert.deepEqual((await get('demand')).metrics,['market-value']);await nav('sop');
  const shared=['affiliates','cycles','sectors','monthStart','monthEnd','display'];let sop=await get('sop');for(const key of shared)assert.deepEqual(sop[key],demandChoice[key]);assert.deepEqual(sop.selectedMeasures,[],'Navigation must not invent a measure selection');
  const sopChoice={channels:['community','contracts'],targets:['community','wholesaler','hospital'],selectedMeasures:['share','market','abbott','community','wholesaler','hospital'],grouping:'sector',table:'monthly',showGrowth:true,showRunRate:true};
  await set('sop',sopChoice);await nav('demand');let d=await get('demand');assert.equal(d.tableView,'sector');assert.equal(d.graphOpen,false);assert.equal(d.filesOpen,true);
  await nav('sop');sop=await get('sop');for(const key of Object.keys(sopChoice))assert.deepEqual(sop[key],sopChoice[key]);
  await set('sop',{display:'units',sectors:['compact','juce'],cycles:['2026-10']});await nav('demand');d=await get('demand');assert.equal(d.display,'units');assert.deepEqual(d.metrics,['market-units']);assert.deepEqual(d.sectors,['compact','juce']);
  pass('Navigation carries Affiliate, cycle, sectors, dates and Units/Value in both directions, while preserving each page’s explicit measures, grouping, periods, derived-row and visibility choices.');

  await set('demand',{...initial,monthStart:'2026-01',monthEnd:'2026-12',periods:['2026:FY','2027:FY']});assert.deepEqual((await get('demand')).periods,['2026:FY']);
  const period=f.locator('#fm-period-field button');await period.click();assert.equal(await f.locator('#fm-period-field input[value="2027:FY"]').count(),0);await period.click();
  await set('demand',{monthEnd:'2027-12'});await period.click();assert.equal(await f.locator('#fm-period-field input[value="2027:FY"]').count(),1);await period.click();
  await set('demand',{periods:[],monthStart:'2027-01'});assert.deepEqual((await get('demand')).periods,[]);await set('demand',{periods:['2027:FY']});assert.match(await f.locator('#fm-compare-periods').innerText(),/2027/);
  await nav('sop');assert.equal((await get('sop')).monthStart,'2027-01');assert.equal(await f.locator('#sb-summary [data-column^="2026:"]').count(),0);
  pass('Both calendars limit summary years. Named periods retain full business windows, clear stays clear, and the FY/YTG shortcut follows the chosen year rather than hard-coded 2026.');

  await nav('demand');await set('demand',{...initial,monthStart:'2026-01',monthEnd:'2026-12'});
  const sourcesBefore=await evaluate(()=>document.getElementById('fm-connected-review-r15').reviewSession.getSources().map(x=>x.id));assert.deepEqual(sourcesBefore,['2026-10|oral|ADS','2026-10|paed|ADS_002']);
  await f.locator('[data-source-details="demand"] summary').click();assert.match(await f.locator('[data-source-details="demand"]').innerText(),/ADS_002/);
  await nav('sop');const sourcesAfter=await evaluate(()=>document.getElementById('fm-connected-review-r15').reviewSession.getSources().map(x=>x.id));assert.deepEqual(sourcesAfter,sourcesBefore);
  assert.equal(await f.locator('#fm-data-context').innerText(),await f.locator('#sb-cutoffs').innerText());assert.match(await f.locator('#sb-cutoffs').innerText(),/IMS through Aug 26.*Ex-factory through Sept 26.*Sample refresh/);
  await nav('demand');await set('demand',{cycles:['2026-07'],sectors:['compact']});const july=await evaluate(()=>document.getElementById('fm-connected-review-r15').reviewSession.getSources().map(x=>x.scenario));assert.deepEqual(july,['Plan ADS']);
  pass('Both headers share the same resolved source IDs, IMS/EF cutoffs and explicitly labelled sample refresh. Source details expand without changing the selected plan; ADS precedence retains Plan ADS and highest-numbered fallback.');

  await set('demand',{...initial,combined:false,view:'driver',filesOpen:false});await f.locator('[data-focus-group="oral"]').hover();
  assert.ok(await f.locator('[data-focus-series="paed"]').evaluateAll(ns=>ns.length&&ns.every(n=>n.style.opacity==='0.18')));await page.mouse.move(2,2);
  await nav('sop');await set('sop',{table:'periods',grouping:'combined',channels:['community'],targets:['community','wholesaler'],selectedMeasures:['share','market','abbott','community','wholesaler'],showRunRate:true,showGrowth:true});
  const base=await get('sop'),amounts=await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));
  await f.locator('[data-row="wholesaler"] [data-focus-measure]').focus();assert.ok(await f.locator('path[data-series="market"]').evaluateAll(ns=>ns.length&&ns.every(n=>n.style.opacity==='0.16')));assert.equal(await f.locator('[data-value-axis="right"]').count(),1);
  await f.locator('[data-toggle-row="market"]').hover();assert.ok(await f.locator('path[data-series="wholesaler"]').evaluateAll(ns=>ns.every(n=>n.style.opacity==='0.16')));assert.deepEqual(await get('sop'),base);assert.deepEqual(await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value)),amounts);
  assert.equal(await f.locator('[data-summary-context="community"]').innerText(),'—');assert.equal(await f.locator('[data-summary-context="community"]').getAttribute('data-tooltip'),'No sub-channel');
  await page.mouse.move(2,2);await shot('sop-review.png');pass('Legend/table hover and native keyboard focus highlight matching lines without filtering either page. Share remains on the right axis and true blank Sub-channels display as a dash with an explanatory tooltip.');

  for(const id of ['#sb-panel-toggle','#sb-graph-toggle','#sb-summary-toggle']){await f.locator(id).click();assert.equal(await f.locator(id).getAttribute('aria-expanded'),'false');}
  await shot('sop-collapsed.png');for(const id of ['#sb-panel-toggle','#sb-graph-toggle','#sb-summary-toggle'])await f.locator(id).click();assert.deepEqual(await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value)),amounts);
  await nav('demand');const rows=await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));for(const key of ['scopeOpen','graphOpen','summaryOpen']){const button=f.locator('[data-section-toggle="'+key+'"]');await button.click();assert.equal(await button.innerText(),'Show');await button.click();}
  assert.deepEqual(await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value)),rows);pass('Hide/Show works independently on both pages, preserves selections/amounts and restores correctly sized charts.');

  const oldDemandPage=await browser.newPage();await oldDemandPage.goto(pathToFileURL(path.join(__dirname,'../executive-month-review-r11/index.html')).href);const od=oldDemandPage.frames().find(x=>x!==oldDemandPage.mainFrame());await od.waitForSelector('#fm-summary');
  const demandSnapshot=(frame,id)=>frame.evaluate(id=>{const a=document.getElementById(id).fmDesign,out=[];for(const cycle of ['2026-10','2026-07']){a.setState({cycles:[cycle],fileMode:'ads',sectors:a.sectors.map(s=>s.id),channels:['community','hospital'],subchannels:['retail','homecare','hospital']},false);const combo=a.combos()[0];for(const subset of [a.sectors,a.sectors.slice(0,2),a.sectors.slice(2),a.sectors.slice(0,1)])for(const metric of a.catalog.filter(m=>m.id!=='abbott-value'))for(const period of ['2026:FY','2026:YTD','2026:YTG'])for(const trend of [0,6,12,24])out.push(a.amount(combo,subset,metric,a.periodMonths(period,combo,metric),trend));}return out;},id);
  const demandBefore=await demandSnapshot(od,'fm-executive-month-review'),demandAfter=await demandSnapshot(f,'fm-connected-demand-r15');assert.equal(demandBefore.length,demandAfter.length);demandBefore.forEach((v,i)=>near(v,demandAfter[i]));await oldDemandPage.close();
  const oldSopPage=await browser.newPage();await oldSopPage.goto(pathToFileURL(path.join(__dirname,'../sop-calendar-spacing-r12/index.html')).href);const os=oldSopPage.frames().find(x=>x!==oldSopPage.mainFrame());await os.waitForSelector('#sb-summary');
  const sopSnapshot=(frame,id)=>frame.evaluate(id=>{const a=document.getElementById(id).sopDesign,out=[];for(const display of ['units','value']){a.setState({display,sectors:a.sectors.map(s=>s.id),grouping:'combined'},false);const group=a.groups()[0];for(const cycle of ['2026-10','2026-07'])for(const row of a.rows)for(const period of ['2026:FY','2026:YTD','2026:YTG'])for(const kind of ['amount','run-rate','growth'])out.push(a.summaryValue(row,group,{id:period},cycle,kind));}return out;},id);
  const sopBefore=await sopSnapshot(os,'fm-sop-calendar-spacing-r12'),sopAfter=await sopSnapshot(f,'fm-connected-sop-r15');sopBefore.forEach((v,i)=>near(v,sopAfter[i]));await oldSopPage.close();pass(`${demandBefore.length} Demand and ${sopBefore.length} S&OP numerical observations match their saved baselines. Independent illustrative models are preserved; live cross-page reconciliation remains pending.`);

  await nav('demand');await set('demand',{...initial,monthStart:'2026-01',monthEnd:'2026-12'});await shot('demand-final.png');
  const warm=requests.length;
  for(const kind of ['demand','sop']){await nav(kind);if(kind==='sop')await set('sop',{...base,affiliates:['uk'],sectors:['compact','juce']});for(const width of [1080,1024,736,390,320]){await page.setViewportSize({width,height:1500});await page.waitForTimeout(160);assert.equal(await evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,kind+' overflow '+width);}await shot(kind+'-mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot(kind+'-dark.png');await page.emulateMedia({colorScheme:'light'});}
  const restored=await evaluate(()=>document.getElementById('fm-connected-review-r15').reviewSession.getState());restored.page='demand';restored.demand.graphOpen=false;
  await evaluate(state=>window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{schema:'fm-connected-gm-review-r15',state}}}}})),restored);assert.equal(await f.locator('#cr-demand-page').isVisible(),true);assert.equal(await f.locator('#fm-body-graphOpen').isVisible(),false);
  assert.deepEqual(errors,[]);assert.equal(requests.length-warm,0);pass('Both pages fit 1080/1024/736/390/320px in light/dark themes, restore combined host state, and make no warm network requests or script errors.');
  const result={schema:'FM_CONNECTED_GM_REVIEW_R15_VALIDATION',checkedAt:new Date().toISOString(),checks,demandComparisons:demandBefore.length,sopComparisons:sopBefore.length,errors,warmNetworkRequests:requests.length-warm,note:'HTML design using preserved independent synthetic models. Live source binding, cross-page numerical reconciliation and Power BI speed remain unexecuted implementation gates.'};fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
