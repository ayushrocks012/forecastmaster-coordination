const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.platform==='win32'?path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'):'playwright'));
const near=(a,b)=>assert.ok(a===null?b===null:b!==null&&Math.abs(a-b)<=Math.max(1e-8,Math.abs(a)*1e-10),`${a} != ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1500},colorScheme:'light'}),errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  const f=page.frames().find(x=>x!==page.mainFrame());await f.waitForSelector('#fm-summary');
  const evaluate=(fn,arg)=>f.evaluate(fn,arg),pass=s=>checks.push(s);
  const set=(kind,patch)=>evaluate(({kind,patch})=>document.getElementById(kind==='demand'?'fm-connected-demand-r14':'fm-connected-sop-r14')[kind==='demand'?'fmDesign':'sopDesign'].setState(patch),{kind,patch});
  const get=()=>evaluate(()=>document.getElementById('fm-connected-review-r14').reviewSession.getState());
  const fx=patch=>evaluate(patch=>document.getElementById('fm-connected-review-r14').planFX.setState(patch),patch);
  const nav=kind=>f.locator('#cr-'+kind+'-tab').click();
  const ui=kind=>f.locator('[data-fx-controls="'+kind+'"]');
  const rateInput=kind=>ui(kind).locator('[data-fx-rate="uk"]');
  async function shot(name,width=1080){await page.setViewportSize({width,height:1500});await page.waitForTimeout(180);const h=await evaluate(()=>document.documentElement.scrollHeight);await page.locator('iframe').evaluate((n,h)=>{n.style.setProperty('height',h+'px','important');n.style.setProperty('max-height','none','important');},h+16);await page.setViewportSize({width,height:h+96});await page.waitForTimeout(100);await page.mouse.move(2,2);await page.screenshot({path:path.join(__dirname,name),fullPage:true});}

  assert.deepEqual((await get()).fx,{currency:'local',planYear:'2026',rates:{}});assert.equal(await ui('demand').isVisible(),false);
  await f.locator('#fm-display').selectOption('value');assert.equal(await ui('demand').isVisible(),true);assert.equal(await ui('demand').locator('[data-fx-currency]').inputValue(),'local');assert.match(await f.locator('#fm-summary-context').innerText(),/GBP/);
  await nav('sop');assert.equal(await ui('sop').isVisible(),true);assert.deepEqual((await get()).sop.selectedMeasures,[]);
  pass('Both Value headers offer local currency/USD and compact Plan rates. Selling units hides FX controls; no business exchange rate is fabricated or source measure preselected.');

  // Capture R13 as an independent numeric oracle, including prior/current/future years.
  const baselinePage=await browser.newPage();await baselinePage.goto(pathToFileURL(path.join(__dirname,'../connected-gm-review-r13/index.html')).href);
  const before=baselinePage.frames().find(x=>x!==baselinePage.mainFrame());await before.waitForSelector('#fm-summary');
  const demandSweep=(frame,id)=>frame.evaluate(id=>{
   const a=document.getElementById(id).fmDesign;a.setState({display:'value',cycles:['2026-10'],affiliates:['uk'],sectors:a.sectors.map(s=>s.id),channels:['community','hospital'],subchannels:['retail','homecare','hospital'],fileMode:'ads'},false);
   const combo=a.combos()[0],out=[];
   for(const subset of [a.sectors,a.sectors.slice(0,2)])for(const metric of a.catalog)for(const year of [2025,2026,2027])for(const kind of ['FY','YTD','YTG'])for(const trend of [0,6,12,24])out.push({value:a.amount(combo,subset,metric,a.periodMonths(year+':'+kind,combo,metric),trend),monetary:metric.unit==='£'});
   return out;
  },id);
  const sopSweep=(frame,id)=>frame.evaluate(id=>{
   const a=document.getElementById(id).sopDesign,out=[];
   for(const display of ['units','value']){a.setState({display,sectors:a.sectors.map(s=>s.id),grouping:'combined',table:'periods'},false);const group=a.groups()[0];for(const row of a.rows)for(const year of [2025,2026,2027])for(const period of ['FY','YTD','YTG'])for(const kind of ['amount','run-rate','growth'])out.push({value:a.summaryValue(row,group,{id:year+':'+period},'2026-10',kind),monetary:display==='value'&&!row.ratio&&kind!=='growth'});}
   return out;
  },id);
  const d0=await demandSweep(before,'fm-connected-demand-r13'),s0=await sopSweep(before,'fm-connected-sop-r13');
  const dLocal=await demandSweep(f,'fm-connected-demand-r14'),sLocal=await sopSweep(f,'fm-connected-sop-r14');
  assert.equal(d0.length,dLocal.length);assert.equal(s0.length,sLocal.length);d0.forEach((r,i)=>near(r.value,dLocal[i].value));s0.forEach((r,i)=>near(r.value,sLocal[i].value));
  await baselinePage.close();pass(`${d0.length} Demand amounts/trends and ${s0.length} S&OP amounts/run-rates/growth observations match saved R13 in Units/GBP, including 2025/2026/2027 business periods.`);

  await nav('demand');await set('demand',{display:'value',sections:['ims'],metrics:['market-value'],monthStart:'2025-01',monthEnd:'2027-12',periods:['2026:FY'],tableTrends:[6,12,24],graphOpen:true});
  const demandOriginalState=(await get()).demand;
  const demandLocal=await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.value)));
  const demandPercent=await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent));
  const demandDelta=await f.locator('#fm-summary [data-delta]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.delta)));
  await ui('demand').locator('[data-fx-currency]').selectOption('USD');assert.match(await ui('demand').locator('[data-fx-warning]').innerText(),/Plan rate required/);
  assert.ok(await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='')));assert.match(await f.locator('#fm-plots').innerText(),/Plan rate required/);
  assert.deepEqual(await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent)),demandPercent);
  pass('Missing FX leaves USD amounts/absolute variances unavailable, with an explicit rate-required message; business variance percentages remain available.');

  await ui('demand').locator('[data-fx-open]').click();assert.equal(await ui('demand').locator('[role="dialog"]').isVisible(),true);
  assert.equal(await rateInput('demand').inputValue(),'');await rateInput('demand').fill('2');await ui('demand').getByRole('button',{name:'Apply rates',exact:true}).click();
  assert.equal((await get()).fx.rates['uk|GBP|2026'],2);assert.equal(await ui('demand').locator('[data-fx-warning]').isVisible(),false);
  const dUsd=await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.value)));demandLocal.forEach((v,i)=>near(v*2,dUsd[i]));
  const deltas=await f.locator('#fm-summary [data-delta]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.delta)));demandDelta.forEach((v,i)=>near(v*2,deltas[i]));
  assert.deepEqual(await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent)),demandPercent);
  assert.match(await f.locator('#fm-summary-context').innerText(),/USD · 2026 plan rate/);assert.match(await f.locator('#fm-plots [data-axis="y"]').first().textContent(),/USD/);
  assert.match(await f.locator('#fm-summary').innerText(),/\$/);assert.doesNotMatch(await f.locator('#fm-summary').innerText(),/£/);
  await fx({rates:{'uk|GBP|2025':7,'uk|GBP|2026':2,'uk|GBP|2027':9}});
  const dUsdSweep=await demandSweep(f,'fm-connected-demand-r14'),sUsdSweep=await sopSweep(f,'fm-connected-sop-r14');
  d0.forEach((r,i)=>near(r.value==null?null:r.value*(r.monetary?2:1),dUsdSweep[i].value));s0.forEach((r,i)=>near(r.value==null?null:r.value*(r.monetary?2:1),sUsdSweep[i].value));
  pass(`The entered fixture rate 2 converts all monetary observations exactly once. Selected 2026 rate applies to 2025/2026/2027 amounts despite different stored rates for those years; Units, Share, variance % and business growth remain unchanged (${d0.length+s0.length} comparisons).`);

  await nav('sop');await set('sop',{display:'value',affiliates:['uk'],cycles:['2026-10'],channels:['community'],targets:['community','wholesaler'],selectedMeasures:['share','abbott','market','community','wholesaler'],sectors:['compact','juce'],monthStart:'2026-01',monthEnd:'2026-12',periods:['2026:FY','2026:YTD','2026:YTG'],showRunRate:true,showGrowth:true,table:'periods'});
  assert.equal(await ui('sop').locator('[data-fx-currency]').inputValue(),'USD');assert.match(await f.locator('#sb-table-context').innerText(),/USD · 2026 plan rate/);assert.equal(await f.locator('[data-value-axis="right"]').count(),1);
  const sopUSD=await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));
  const sopGrowth=await f.locator('#sb-summary [data-summary-kind="growth"] [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));
  const sopShare=await f.locator('#sb-summary [data-row="share"] [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));
  await ui('sop').locator('[data-fx-open]').click();assert.equal(await rateInput('sop').inputValue(),'2');
  await ui('sop').locator('[data-fx-year]').selectOption('2027');assert.equal(await rateInput('sop').inputValue(),'9');await rateInput('sop').fill('3');await ui('sop').getByRole('button',{name:'Apply rates',exact:true}).click();
  assert.equal((await get()).fx.planYear,'2027');assert.equal((await get()).fx.rates['uk|GBP|2026'],2);
  const sop3=await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>({value:n.dataset.value,percentage:n.closest('tr').dataset.row==='share'||n.closest('tr').dataset.summaryKind==='growth'})));
  sopUSD.forEach((v,i)=>near(v===''?null:Number(v)*(sop3[i].percentage?1:1.5),sop3[i].value===''?null:Number(sop3[i].value)));
  await nav('demand');assert.match(await ui('demand').locator('[data-fx-open]').innerText(),/2027/);
  await nav('sop');assert.equal((await get()).sop.showRunRate,true);
  pass('Currency, selected plan year and affiliate/year rates are shared bidirectionally. Changing 2027 to 3 scales S&OP money/run rates, preserves earlier-year entries, Share/right axis, business growth, explicit measures and both pages’ local choices.');

  await ui('sop').locator('[data-fx-open]').click();await rateInput('sop').fill('-1');await ui('sop').getByRole('button',{name:'Apply rates',exact:true}).click();assert.equal(await ui('sop').locator('[data-fx-error]').isVisible(),true);assert.equal(await rateInput('sop').getAttribute('aria-invalid'),'true');assert.equal((await get()).fx.rates['uk|GBP|2027'],3);
  await rateInput('sop').fill('not a rate');await ui('sop').getByRole('button',{name:'Apply rates',exact:true}).click();assert.equal((await get()).fx.rates['uk|GBP|2027'],3);
  await rateInput('sop').press('Escape');assert.equal(await ui('sop').locator('[role="dialog"]').isVisible(),false);assert.equal(await ui('sop').locator('[data-fx-open]').evaluate(n=>document.activeElement===n),true);
  await ui('sop').locator('[data-fx-open]').click();await rateInput('sop').fill('5');await ui('sop').getByRole('button',{name:'Cancel',exact:true}).click();assert.equal((await get()).fx.rates['uk|GBP|2027'],3);
  await ui('sop').locator('[data-fx-open]').click();await rateInput('sop').fill('0');await ui('sop').getByRole('button',{name:'Apply rates',exact:true}).click();
  assert.ok(await f.locator('#sb-summary [data-summary-kind="amount"]:not([data-row="share"]) [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='0')));
  assert.ok(await f.locator('#sb-summary [data-summary-kind="run-rate"] [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='0')));
  assert.deepEqual(await f.locator('#sb-summary [data-summary-kind="growth"] [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value)),sopGrowth);assert.deepEqual(await f.locator('#sb-summary [data-row="share"] [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value)),sopShare);
  await nav('demand');await set('demand',demandOriginalState);assert.ok(await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='0')));assert.deepEqual(await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent)),demandPercent);
  await ui('demand').locator('[data-fx-open]').click();await rateInput('demand').fill('');await ui('demand').getByRole('button',{name:'Apply rates',exact:true}).click();assert.equal(Object.hasOwn((await get()).fx.rates,'uk|GBP|2027'),false);assert.match(await ui('demand').locator('[data-fx-warning]').innerText(),/Plan rate required/);
  await fx({rates:{'uk|GBP|2027':true}});assert.deepEqual((await get()).fx.rates,{});
  pass('Invalid/negative/text/Boolean rates cannot replace a valid rate; Cancel/Escape discard edits and return focus. Numeric zero yields monetary zero while Share/growth/variance % remain unchanged. Clearing the rate restores unavailable USD amounts.');

  await fx({currency:'USD',planYear:'2026',rates:{'uk|GBP|2026':2,'uk|GBP|2027':3}});
  await set('demand',{display:'value',metrics:['market-value'],tableTrends:[12],periods:['2026:FY'],monthStart:'2026-01',monthEnd:'2026-12',graphOpen:true});
  await shot('plan-fx-demand.png');await ui('demand').locator('[data-fx-open]').click();await shot('plan-fx-editor.png');await rateInput('demand').press('Escape');
  await nav('sop');await shot('plan-fx-sop.png');await set('sop',{table:'monthly'});assert.equal(await f.locator('#sb-summary [data-summary-kind="run-rate"]').count(),0);assert.match(await f.locator('#sb-summary').innerText(),/\$/);await set('sop',{table:'periods'});
  const warm=requests.length;
  for(const kind of ['demand','sop']){
   await nav(kind);await ui(kind).locator('[data-fx-open]').click();
   for(const width of [1080,1024,736,390,320]){await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);assert.equal(await evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,kind+' overflow '+width);
    const rect=await ui(kind).locator('[role="dialog"]').boundingBox();assert.ok(rect.x>=-1&&rect.x+rect.width<=width+1,kind+' panel bounds '+width);assert.equal(await rateInput(kind).isVisible(),true);}
   await shot('plan-fx-'+kind+'-mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot('plan-fx-'+kind+'-dark.png');await page.emulateMedia({colorScheme:'light'});await ui(kind).locator('[data-fx-close]').click();
  }
  pass('Both value pages and rate panels fit 1080/1024/736/390/320px, with accessible keyboard controls, light/dark themes, dynamic axes/tooltips/table currency, and USD Monthly amounts; monthly run-rate suppression is retained.');

  const restored=await get();await evaluate(state=>{window.__fxSaves=[];window.openai.setWidgetState=async snapshot=>window.__fxSaves.push(snapshot);window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{schema:'fm-connected-gm-review-r14',state}}}}}));},restored);
  assert.deepEqual((await get()).fx,restored.fx);assert.equal(await evaluate(()=>window.__fxSaves.length),0);
  await ui('sop').locator('[data-fx-currency]').selectOption('local');const snapshot=await evaluate(()=>window.__fxSaves.at(-1));assert.equal(snapshot.modelContent.state.fx.currency,'local');assert.equal(snapshot.modelContent.state.fx.rates['uk|GBP|2027'],3);assert.ok(JSON.stringify(snapshot).length<16384);
  await ui('sop').locator('[data-fx-currency]').selectOption('USD');await set('sop',{display:'units'});assert.equal(await ui('sop').isVisible(),false);assert.doesNotMatch(await f.locator('#sb-summary').innerText(),/£|\$/);await set('sop',{display:'value'});assert.equal(await ui('sop').locator('[data-fx-currency]').inputValue(),'USD');
  assert.deepEqual(errors,[]);assert.equal(requests.length-warm,0);
  pass('Combined host restore includes currency, plan year and all entered annual rates without saving on restore. Meaningful edits persist one small snapshot. Units/Value and page navigation retain the chosen FX basis, with no script errors or warm network requests.');
  const result={schema:'FM_PLAN_RATE_REVIEW_R14_VALIDATION',checkedAt:new Date().toISOString(),checks,baselineDemandComparisons:d0.length,baselineSopComparisons:s0.length,usdComparisons:d0.length+s0.length,errors,warmNetworkRequests:requests.length-warm,fixtureRates:'2, 3, 7 and 9 are explicit artificial test inputs, never default business rates.',scope:'HTML only. UK is the sole actual sample affiliate; future affiliates/currencies require real source metadata. No Power BI, Fabric, application source or workbook was changed.'};
  fs.writeFileSync(path.join(__dirname,'plan-fx-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
