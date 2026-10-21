const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.platform==='win32'?path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'):'playwright'));
const near=(a,b)=>assert.ok(a===null?b===null:b!==null&&Math.abs(a-b)<Math.max(1e-8,Math.abs(a)*1e-10),`${a} != ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1500},colorScheme:'light'}),errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);const f=page.frames().find(x=>x!==page.mainFrame());await f.waitForSelector('#fm-summary');
  const evaluate=(fn,arg)=>f.evaluate(fn,arg),pass=s=>checks.push(s),ui=kind=>f.locator('[data-fx-controls="'+kind+'"]');
  const get=()=>evaluate(()=>document.getElementById('fm-connected-review-r15').reviewSession.getState());
  const fx=patch=>evaluate(p=>document.getElementById('fm-connected-review-r15').planFX.setState(p),patch);
  const set=(kind,patch)=>evaluate(({kind,patch})=>document.getElementById(kind==='demand'?'fm-connected-demand-r15':'fm-connected-sop-r15')[kind==='demand'?'fmDesign':'sopDesign'].setState(patch),{kind,patch});
  const nav=kind=>f.locator('#cr-'+kind+'-tab').click();
  async function shot(name,width=1080){await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);const h=await evaluate(()=>document.documentElement.scrollHeight);await page.locator('iframe').evaluate((n,h)=>{n.style.setProperty('height',h+'px','important');n.style.setProperty('max-height','none','important');},h+16);await page.setViewportSize({width,height:h+96});await page.waitForTimeout(100);await page.mouse.move(2,2);await page.screenshot({path:path.join(__dirname,name),fullPage:true});}
  assert.deepEqual((await get()).fx,{currency:'local',rates:{}});assert.equal(await ui('demand').locator('[data-fx-open]').isVisible(),true);assert.equal(await ui('demand').locator('[data-fx-currency]').isVisible(),false);
  await ui('demand').locator('[data-fx-open]').click();assert.equal(await ui('demand').locator('[data-fx-rate="GBP"]').count(),1);assert.doesNotMatch(await ui('demand').locator('[role=dialog]').innerText(),/Plan year|2026|United Kingdom|Affiliate/);assert.match(await ui('demand').locator('[role=dialog]').innerText(),/1 GBP =/);await ui('demand').locator('[data-fx-close]').click();
  pass('Plan rates is visible in Units and Value. The editor lists source-currency-to-USD quotes only, with no country or plan-year fields and no prefilled business rate.');

  await set('demand',{display:'value',metrics:['market-value'],periods:['2026:FY'],tableTrends:[6,12,24]});
  const money=await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.value))),delta=await f.locator('#fm-summary [data-delta]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.delta))),percent=await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent));
  await ui('demand').locator('[data-fx-currency]').selectOption('USD');assert.match(await ui('demand').locator('[data-fx-warning]').innerText(),/required · GBP/);assert.ok(await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='')));
  await ui('demand').locator('[data-fx-open]').click();await ui('demand').locator('[data-fx-rate="GBP"]').fill('2');await ui('demand').locator('[data-fx-rate="GBP"]').press('Enter');assert.deepEqual((await get()).fx,{currency:'USD',rates:{GBP:2}});
  const usd=await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.value))),usdDelta=await f.locator('#fm-summary [data-delta]').evaluateAll(ns=>ns.map(n=>Number(n.dataset.delta)));money.forEach((v,i)=>near(v*2,usd[i]));delta.forEach((v,i)=>near(v*2,usdDelta[i]));assert.deepEqual(await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent)),percent);assert.match(await f.locator('#fm-summary-context').innerText(),/USD · plan rate/);
  await shot('currency-demand.png');await ui('demand').locator('[data-fx-open]').click();await shot('currency-editor.png');await ui('demand').locator('[data-fx-close]').click();
  pass('Demand USD totals/absolute variances convert once with a currency-keyed rate; variance percentages retain local business meaning. Missing FX yields unavailable USD, with a currency-only warning.');

  await nav('sop');await set('sop',{display:'value',channels:['community'],targets:['community','wholesaler'],selectedMeasures:['share','market','abbott','community','wholesaler'],showRunRate:true,showGrowth:true,monthStart:'2026-01',monthEnd:'2026-12'});
  assert.equal(await ui('sop').locator('[data-fx-currency]').inputValue(),'USD');await fx({currency:'local'});
  const baseline=await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>({value:n.dataset.value,percentage:n.closest('tr').dataset.row==='share'||n.closest('tr').dataset.summaryKind==='growth'})));
  await ui('sop').locator('[data-fx-currency]').selectOption('USD');const sopUSD=await f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));baseline.forEach((r,i)=>near(r.value===''?null:Number(r.value)*(r.percentage?1:2),sopUSD[i]===''?null:Number(sopUSD[i])));assert.equal(await f.locator('[data-value-axis="right"]').count(),1);assert.match(await f.locator('#sb-table-context').innerText(),/USD · plan rate/);
  await ui('sop').locator('[data-fx-open]').click();assert.equal(await ui('sop').locator('[data-fx-rate="GBP"]').inputValue(),'2');await ui('sop').locator('[data-fx-rate="GBP"]').fill('3');await ui('sop').getByRole('button',{name:'Apply rates',exact:true}).click();await nav('demand');assert.equal((await get()).fx.rates.GBP,3);
  pass('Both pages share the same GBP-to-USD rate. S&OP amounts/monthly run rates scale; Share and growth remain unchanged, and Share stays on the right axis.');

  const multi=await evaluate(()=>{
   const make=document.getElementById('fm-connected-review-r15').planFX.createModel;
   // Synthetic plumbing fixtures only: never appended to either page’s Affiliate list.
   const metadata=[{id:'fixture-a',currency:'GBP'},{id:'fixture-b',currency:'EUR'},{id:'fixture-c',currency:'GBP'},{id:'fixture-d',currency:'USD'}];
   const m=make(metadata,{rates:{GBP:2,EUR:3}});m.setContext({affiliates:['fixture-a','fixture-b'],display:'value'});
   const result={currencies:m.currencies,initial:m.getState(),total:m.total([{currency:'GBP',value:100},{currency:'EUR',value:100},{currency:'USD',value:100}]),deduplicated:m.selectedCurrencies(['fixture-a','fixture-c']),usdRate:m.rate('USD')};
   m.setState({currency:'USD',rates:{GBP:2}});result.missing=m.missing();result.incomplete=m.total([{currency:'GBP',value:100},{currency:'EUR',value:100}]);
   m.setState({currency:'local',rates:{GBP:2,EUR:3}});result.mixedLocal=m.total([{currency:'GBP',value:100},{currency:'EUR',value:100}]);m.setContext({affiliates:['fixture-a','fixture-b'],display:'value'});result.forced=m.getState().currency;
   m.setState({currency:'USD',rates:{GBP:2,EUR:0}});result.zero=m.total([{currency:'GBP',value:100},{currency:'EUR',value:100},{currency:'USD',value:100}]);
   m.setState({currency:'local',rates:{GBP:2,EUR:3}});m.setContext({affiliates:['fixture-a','fixture-c'],display:'units'});m.setContext({affiliates:['fixture-a','fixture-c'],display:'value'});result.sameCurrencyDefault=m.getState().currency;result.sameCurrencyTotal=m.total([{currency:'GBP',value:100},{currency:'GBP',value:100}]);
   m.setState({currency:'USD',rates:{GBP:true,EUR:'3'}});result.invalid=m.getState().rates;result.invalidTotal=m.total([{currency:'GBP',value:100}]);return result;
  });
  assert.deepEqual(multi.currencies,['EUR','GBP','USD']);assert.equal(multi.initial.currency,'USD');assert.equal(multi.total,600);assert.deepEqual(multi.deduplicated,['GBP']);assert.equal(multi.usdRate,1);assert.deepEqual(multi.missing,['EUR']);assert.equal(multi.incomplete,null);assert.equal(multi.mixedLocal,null);assert.equal(multi.forced,'USD');assert.equal(multi.zero,300);assert.equal(multi.sameCurrencyDefault,'USD');assert.equal(multi.sameCurrencyTotal,400);assert.deepEqual(multi.invalid,{});assert.equal(multi.invalidTotal,null);
  pass('Synthetic multi-affiliate fixtures default Value to USD, deduplicate rates by source currency, convert GBP/EUR contributions before summing, leave USD unchanged, and reject partial or mixed-local totals. One missing required rate withholds the complete USD total; numeric zero is preserved.');

  await ui('demand').locator('[data-fx-open]').click();await ui('demand').locator('[data-fx-rate="GBP"]').fill('-1');await ui('demand').getByRole('button',{name:'Apply rates',exact:true}).click();assert.equal(await ui('demand').locator('[data-fx-error]').isVisible(),true);assert.equal((await get()).fx.rates.GBP,3);await ui('demand').getByRole('button',{name:'Cancel',exact:true}).click();
  await ui('demand').locator('[data-fx-open]').click();await ui('demand').locator('[data-fx-rate="GBP"]').fill('');await ui('demand').getByRole('button',{name:'Apply rates',exact:true}).click();assert.deepEqual((await get()).fx.rates,{});await fx({rates:{GBP:0}});assert.ok(await f.locator('#fm-summary [data-value]').evaluateAll(ns=>ns.length&&ns.every(n=>n.dataset.value==='0')));assert.deepEqual(await f.locator('#fm-summary [data-variance-percent]').evaluateAll(ns=>ns.map(n=>n.dataset.variancePercent)),percent);
  await fx({rates:{GBP:2}});await nav('sop');await shot('currency-sop.png');const warm=requests.length;
  for(const kind of ['demand','sop']){await nav(kind);await ui(kind).locator('[data-fx-open]').click();for(const width of [1080,736,390,320]){await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);assert.equal(await evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false);const r=await ui(kind).locator('[role=dialog]').boundingBox();assert.ok(r.x>=-1&&r.x+r.width<=width+1);}
   await shot('currency-'+kind+'-mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot('currency-'+kind+'-dark.png');await page.emulateMedia({colorScheme:'light'});await ui(kind).locator('[data-fx-close]').click();}
  const restored=await get();await evaluate(state=>window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{schema:'fm-connected-gm-review-r15',state}}}}})),restored);assert.deepEqual((await get()).fx,restored.fx);assert.deepEqual(Object.keys((await get()).fx),['currency','rates']);assert.deepEqual(errors,[]);assert.equal(requests.length-warm,0);
  pass('Blank/zero/invalid edits, Cancel, host restore and both narrow light/dark layouts work. State has currency/rates only; no FX year survives. No script errors or warm network requests.');
  const result={schema:'FM_CURRENCY_PLAN_R15_VALIDATION',checkedAt:new Date().toISOString(),checks,errors,warmNetworkRequests:requests.length-warm,note:'UK/GBP is the only real illustrative base shown in the UI. Multi-affiliate/currency cases are explicit isolated plumbing fixtures; live multi-affiliate sources and Power BI remain unimplemented.'};fs.writeFileSync(path.join(__dirname,'currency-validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
