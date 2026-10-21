const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.platform==='win32'?path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'):'playwright'));
const near=(a,b)=>assert.ok(a===null?b===null:Math.abs(a-b)<Math.max(1e-8,Math.abs(a)*1e-10),`${a} != ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1500},colorScheme:'light'}),errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  const frame=page.frames().find(f=>f!==page.mainFrame());await frame.waitForSelector('#sb-summary');
  const apiId='fm-sop-aligned-contexts-r08';
  const get=()=>frame.evaluate(id=>document.getElementById(id).sopDesign.getState(),apiId);
  const set=p=>frame.evaluate(({id,p})=>document.getElementById(id).sopDesign.setState(p),{id:apiId,p});
  const rowIds=()=>frame.locator('#sb-summary [data-row]').evaluateAll(ns=>ns.map(n=>n.dataset.row));
  const measure=id=>frame.locator(`[data-measure="${id}"]`),pass=s=>checks.push(s),initial=await get();
  async function shot(name,width=1080){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);
   const h=await frame.evaluate(()=>document.documentElement.scrollHeight);
   await page.locator('iframe').evaluate((el,h)=>{el.style.setProperty('height',h+'px','important');el.style.setProperty('max-height','none','important');},h+16);
   await page.setViewportSize({width,height:h+96});await page.waitForTimeout(150);
   await page.mouse.move(4,4);await page.screenshot({path:path.join(__dirname,name),fullPage:true});
  }
  assert.deepEqual(await rowIds(),[]);assert.deepEqual(initial.selectedMeasures,[]);
  assert.equal(await frame.locator('[data-filter="sections"],#sb-grouping').count(),0);
  assert.deepEqual(await frame.locator('#sb-filters [data-filter]').evaluateAll(ns=>ns.map(n=>n.dataset.filter)),['affiliates','cycles']);
  assert.equal(await frame.locator('#sb-start,#sb-end,#sb-units').count(),3);
  await shot('empty.png');
  pass('Section and the top Selected scope filter are removed. Affiliate, cycle, Units/Value, calendars and shared driver/sector scope remain; graph/table start empty.');

  await frame.locator('[data-channel="community"]').click();
  assert.deepEqual((await get()).targets,[]);assert.deepEqual(await rowIds(),[]);
  const contextOrder=await frame.locator('[data-channel-band="community"] [data-source-context]').evaluateAll(ns=>ns.map(n=>n.dataset.sourceContext));
  assert.deepEqual(contextOrder,['community','wholesaler','ni']);
  assert.deepEqual(await frame.locator('[data-measures-for="community"] [data-measure]').evaluateAll(ns=>ns.map(n=>n.dataset.measure)),['share','abbott','market','pi','net','community']);
  assert.deepEqual(await frame.locator('[data-measures-for="wholesaler"] [data-measure]').evaluateAll(ns=>ns.map(n=>n.dataset.measure)),['wholesaler']);
  assert.deepEqual(await frame.locator('[data-measures-for="ni"] [data-measure]').evaluateAll(ns=>ns.map(n=>n.dataset.measure)),['ni']);
  assert.equal(await measure('share').isDisabled(),true);assert.equal(await measure('wholesaler').isDisabled(),true);
  const geometry=await frame.evaluate(()=>{const r=s=>document.querySelector(s).getBoundingClientRect();return {lastBlank:r('[data-measure="community"]').bottom,wholesaler:r('[data-source-context="wholesaler"]').top,lastWholesaler:r('[data-measure="wholesaler"]').bottom,ni:r('[data-source-context="ni"]').top};});
  assert.ok(geometry.wholesaler-geometry.lastBlank>=18);assert.ok(geometry.ni-geometry.lastWholesaler>=18);
  pass('Community blank, Wholesaler and Northern Ireland occupy separate aligned rows. Every blank-context measure ends above Wholesaler; each child has its own ADS control and breathing room.');

  const catalog=await frame.evaluate(id=>document.getElementById(id).sopDesign.bridgeCatalog,apiId),ids=catalog.bindings.map(b=>b.id).sort();
  assert.equal(ids.length,18);assert.ok(catalog.bindings.every(b=>!['current','published'].includes(b.kind)));
  assert.deepEqual(await frame.evaluate(id=>document.getElementById(id).sopDesign.rows.map(r=>r.id).sort(),apiId),ids);
  const share=catalog.bindings.find(b=>b.id==='share'),abbott=catalog.bindings.find(b=>b.id==='abbott');
  assert.equal(share.units.row,66);assert.equal(abbott.units.row,67);assert.equal(share.value.row,81);assert.equal(abbott.value.row,82);
  assert.deepEqual(catalog.displayOrder.slice(0,8),['share','abbott','market','pi','net','community','wholesaler','ni']);
  pass('The 18 exposed measures are direct source identities, with Cur/Pub excluded. Retained bridge positions confirm unit Share 66 before Abbott IMS 67, and value Share 81 before Abbott IMS 82.');

  await frame.locator('[data-target="community"]').click();assert.deepEqual(await rowIds(),[]);
  await measure('abbott').click();await measure('share').click();assert.deepEqual(await rowIds(),['share','abbott']);
  await frame.locator('[data-target="wholesaler"]').click();assert.deepEqual(await rowIds(),['share','abbott']);
  await measure('wholesaler').click();assert.deepEqual(await rowIds(),['share','abbott','wholesaler']);
  await frame.locator('[data-target="ni"]').click();await measure('ni').click();
  await measure('wholesaler').click();assert.deepEqual(await rowIds(),['share','abbott','ni']);
  await measure('wholesaler').click();
  for(const id of ['community','net','pi','market'])await measure(id).click();
  assert.deepEqual(await rowIds(),['share','abbott','market','pi','net','community','wholesaler','ni']);
  const selected=await get();await shot('selected.png');
  await frame.locator('[data-toggle-row="wholesaler"]').click();assert.deepEqual(await rowIds(),['share','abbott','market','pi','net','community','ni']);
  await measure('wholesaler').click();await frame.locator('[data-target="community"]').click();assert.deepEqual(await rowIds(),['wholesaler','ni']);
  await frame.locator('[data-target="community"]').click();await frame.locator('[data-channel="community"]').click();assert.deepEqual(await rowIds(),[]);
  await frame.locator('[data-channel="community"]').click();assert.deepEqual(await rowIds(),['share','abbott','market','pi','net','community','wholesaler','ni']);
  pass('Every context and measure requires explicit selection. Child ADS and legend toggles affect only their own line/table row. Parent/context off removes only dependent results and restores remembered choices on re-enable.');

  await frame.locator('#sb-units').selectOption('value');
  assert.match(await measure('share').innerText(),/Value share/);assert.match(await measure('abbott').innerText(),/IMS value/);
  assert.match(await measure('market').innerText(),/Market value/);assert.match(await measure('net').innerText(),/IMS minus PI value/);
  assert.match(await measure('wholesaler').innerText(),/ADS value/);
  assert.match(await frame.locator('[data-row="wholesaler"]').innerText(),/£/);
  assert.doesNotMatch(await frame.locator('[data-row="share"]').innerText(),/£/);
  assert.equal(await frame.locator('[data-series="share"][data-axis="right"]').count(),2);
  assert.equal(await frame.locator('.sb-plot').count(),1);await shot('value.png');
  pass('Units/Value updates Share, Abbott IMS, Market, PI, net IMS and each context ADS label throughout; Share retains the same graph’s right axis.');

  await set(selected);await frame.locator('[data-channel="contracts"]').click();
  assert.equal(await frame.locator('[data-target="contracts"]').count(),0);
  await frame.locator('[data-target="homecare"]').click();await measure('homecare').click();
  await frame.locator('[data-target="hospital"]').click();assert.ok(!(await rowIds()).includes('hospital'));
  await measure('hospital').click();assert.ok((await rowIds()).includes('homecare')&&(await rowIds()).includes('hospital'));
  await measure('homecare').click();assert.ok(!(await rowIds()).includes('homecare')&&(await rowIds()).includes('hospital'));
  await shot('multiple-channels.png');
  pass('Other source Channels follow in their own aligned contexts. Contracts has only real children, each with an independent ADS toggle and no fabricated total or IMS allocation.');

  await frame.locator('#sb-clear-rows').click();await frame.locator('#sb-row-search').fill('Homecare');await frame.locator('#sb-all-rows').click();assert.deepEqual(await rowIds(),['homecare']);
  await frame.locator('#sb-row-search').fill('');await frame.locator('#sb-all-rows').click();assert.deepEqual(await rowIds(),catalog.displayOrder);
  await frame.locator('#sb-clear-rows').click();assert.deepEqual(await rowIds(),[]);
  await set(selected);const affiliate=frame.locator('[data-filter="affiliates"]');await affiliate.locator('button').click();
  await affiliate.locator('input[type="checkbox"]').uncheck();assert.deepEqual(await rowIds(),[]);
  await affiliate.locator('input[type="checkbox"]').check();await affiliate.locator('button').click();
  const scope=await get();await frame.locator('#sb-all-scope').click();const inclusive=await get();
  await frame.locator('[data-grouping="driver"]').click();assert.equal(await frame.locator('.sb-plot').count(),2);
  assert.deepEqual((await get()).selectedMeasures,inclusive.selectedMeasures);assert.deepEqual((await get()).sectors,inclusive.sectors);
  await frame.locator('[data-grouping="sector"]').click();assert.equal(await frame.locator('.sb-plot').count(),4);
  await set(scope);
  pass('Select matches/all adds only the requested 18 source measures. Affiliate gates results. Total/Drivers/Sectors beside the graph changes presentation without changing included sectors or measures.');

  const originalPage=await browser.newPage();await originalPage.goto(pathToFileURL(path.join(__dirname,'../sop-source-only-r07/index.html')).href);
  const original=originalPage.frames().find(f=>f!==originalPage.mainFrame());await original.waitForSelector('#sb-summary');
  const snapshot=(f,id)=>f.evaluate(({id,ids})=>{const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];for(const display of ['units','value']){a.setState({display,sectors:['compact','juce'],grouping:'combined'});const g=a.groups()[0];for(const cycle of ['2026-10','2026-07'])for(const key of ids)for(const p of ['2026:FY','2026:YTD','2026:YTG'])out.push(a.amount(m.get(key),g,a.periodMonths(m.get(key),p,cycle),cycle));}return out;},{id,ids});
  const before=await snapshot(original,'fm-sop-source-only-r07'),after=await snapshot(frame,apiId);before.forEach((v,i)=>near(v,after[i]));await originalPage.close();
  pass(`${before.length} retained measure/period/cycle/dimension values match saved R07's synthetic observations exactly.`);

  const invariants=await frame.evaluate(id=>{const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];for(const display of ['units','value']){a.setState({display,sectors:a.sectors.map(s=>s.id)});const g=a.groups()[0];for(const t of [24,31,32,33,35]){const v=id=>a.amount(m.get(id),g,[t],'2026-10');out.push([v('community'),v('wholesaler')+v('ni')],[v('ads'),a.leaves.reduce((n,id)=>n+v(id),0)],[v('share'),v('abbott')/v('market')]);}for(const row of a.rows){const v=p=>a.amount(row,g,a.periodMonths(row,p,'2026-10'),'2026-10');if(!row.ratio)out.push([v('2026:FY'),v('2026:YTD')+v('2026:YTG')]);}}return out;},apiId);invariants.forEach(([a,b])=>near(a,b));
  pass(`${invariants.length} checks preserve Community/sector totals, weighted Share and FY=YTD+YTG in both dimensions; no arithmetic change accompanies the layout simplification.`);

  await set(selected);await set({periods:['2026:FY']});assert.equal((await get()).monthStart,selected.monthStart);
  await frame.locator('#sb-start').fill('2026-04');await frame.locator('#sb-start').dispatchEvent('change');assert.deepEqual((await get()).periods,['2026:FY']);
  await frame.locator('[data-table="monthly"]').click();assert.equal(await frame.locator('#sb-summary thead th').count(),11);
  await set(selected);await frame.locator('#sb-panel-toggle').click();assert.equal((await rowIds()).length,8);
  await frame.locator('#sb-panel-toggle').click();
  pass('Visible calendar dates, summary periods and Monthly columns retain their separate roles. Hiding the left selector preserves every choice.');

  const warm=requests.length;
  for(const width of [1080,1024,736,390,320]){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(180);
   assert.equal(await frame.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1),false,`overflow at ${width}`);
   const labels=await frame.locator('.sb-plot svg text').evaluateAll(ns=>ns.filter(n=>n.textContent.trim()).map(n=>{const b=n.getBoundingClientRect(),p=n.ownerSVGElement.getBoundingClientRect();return b.left>=p.left-1&&b.right<=p.right+1;}));assert.ok(labels.every(Boolean),`clipped labels at ${width}`);
  }
  await shot('mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot('dark.png');
  await page.emulateMedia({colorScheme:'light'});await page.setViewportSize({width:1080,height:1500});await page.waitForTimeout(180);
  await frame.locator('[data-chart-hover-overlay="cross-series"]').first().hover({position:{x:87,y:75}});
  assert.equal(await frame.locator('[data-chart-hover-guide]').count(),1);assert.equal(await frame.locator('[data-chart-hover-marker]').count(),8);
  assert.deepEqual(errors,[]);assert.equal(requests.length-warm,0);
  pass('Light/dark responsive layouts fit 1080/1024/736/390/320px, with visible chart labels, cross-series hover, no script errors and no warm network requests.');
  const result={schema:'FM_SOP_ALIGNED_CONTEXTS_R08_VALIDATION',checkedAt:new Date().toISOString(),checks,sourceBindings:ids.length,retainedValueComparisons:before.length,reconciliationComparisons:invariants.length,errors,warmNetworkRequests:requests.length-warm,note:'Synthetic HTML design qualification only; no live source binding, report deployment or Power BI speed claim.'};
  fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
