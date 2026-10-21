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
  const apiId='fm-sop-calendar-spacing-r12';
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
  for(const driver of ['core-oral','paed-sip']){assert.equal(share.units.rowRangesByDriver[driver].min,66);assert.equal(abbott.units.rowRangesByDriver[driver].min,67);assert.equal(share.value.rowRangesByDriver[driver].min,81);assert.equal(abbott.value.rowRangesByDriver[driver].min,82);}
  const audit=JSON.parse(fs.readFileSync(path.join(__dirname,'bridge-audit.json')));
  assert.equal(audit.status,'PASS');assert.equal(audit.sourceContextCount,13);assert.equal(audit.sectorDefinitions,29);assert.equal(audit.bindingIdentityMatches,1044);assert.equal(audit.sourceOrderChecks,58);assert.deepEqual(audit.findings,[]);
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
  assert.deepEqual(await frame.locator('#sb-summary thead th').allTextContents(),['Channel','Sub-channel','Measure','2026 FY','2026 YTD','2026 YTG']);
  assert.equal(await frame.locator('#sb-summary thead tr').count(),1);
  assert.equal(await frame.locator('#sb-summary tbody tr:not([data-row]):not(.sb-summary-spacer)').count(),0);
  assert.equal(await frame.locator('#sb-summary .sb-summary-spacer').count(),7);
  assert.equal(await frame.locator('#sb-summary .sb-summary-spacer [data-value]').count(),0);
  assert.equal(await frame.locator('[data-summary-channel="Community"]').count(),1);
  assert.equal(await frame.locator('[data-summary-channel="Community"]').getAttribute('rowspan'),'15');
  assert.equal(await frame.locator('[data-summary-channel="Community"]').evaluate(el=>{const r=document.createRange();r.selectNodeContents(el);return r.getClientRects().length;}),1,'Community label should remain a whole word');
  assert.equal(await frame.locator('[data-summary-context="community"]').getAttribute('rowspan'),'11');
  assert.equal(await frame.locator('[data-row="wholesaler"] [data-measure-label]').innerText(),'ADS units');
  await frame.locator('section[aria-label="S&OP summary"]').screenshot({path:path.join(__dirname,'summary-only.png')});
  const gapGeometry=await frame.locator('#sb-summary .sb-summary-spacer td').evaluateAll(ns=>ns.map(n=>({height:n.getBoundingClientRect().height,background:getComputedStyle(n).backgroundColor,parent:getComputedStyle(n.closest('section')).backgroundColor})));
  assert.ok(gapGeometry.every(g=>Math.abs(g.height-6)<1&&g.background!==g.parent));
  assert.equal(await frame.locator('[data-row="share"]+tr[data-spacing="measure"]+[data-row="abbott"]').count(),1);
  assert.equal(await frame.locator('#sb-summary [data-spacing="subchannel"]').count(),2);
  pass('One header row and merged labels remain. Seven visibly distinct 6px gaps separate each selected Community measure block and Sub-channel, including Share from Abbott IMS. Gap cells carry no values.');

  const baseChart=await frame.locator('#sb-charts').innerHTML(),baseSelection=(await get()).selectedMeasures;
  await frame.locator('#sb-show-run-rate').check();
  assert.equal(await frame.locator('[data-summary-kind="run-rate"]').count(),7);
  assert.equal(await frame.locator('[data-summary-kind="growth"]').count(),0);
  await frame.locator('#sb-show-growth').check();
  assert.equal(await frame.locator('[data-summary-kind="growth"]').count(),5);
  assert.equal(await frame.locator('[data-derived-row="share"]').count(),0);
  assert.equal(await frame.locator('[data-derived-row="pi"][data-summary-kind="growth"],[data-derived-row="net"][data-summary-kind="growth"]').count(),0);
  assert.equal(await frame.locator('#sb-charts').innerHTML(),baseChart,'Summary toggles must not redraw the graph');
  assert.deepEqual((await get()).selectedMeasures,baseSelection);
  assert.deepEqual(await rowIds(),['share','abbott','market','pi','net','community','wholesaler','ni']);
  const grid=await frame.locator('#sb-summary').evaluate(table=>{
   const pending=[],width=table.tHead.rows[0].cells.length,errors=[];
   [...table.tBodies[0].rows].forEach((row,index)=>{let col=0;for(const cell of row.cells){while(pending[col]>0)col++;for(let n=0;n<cell.colSpan;n++){if(pending[col+n]>0)errors.push('overlap '+index);pending[col+n]=cell.rowSpan;}col+=cell.colSpan;}for(let i=0;i<width;i++){if(!(pending[i]>0))errors.push('gap '+index+':'+i);pending[i]--;}if(pending.slice(width).some(n=>n>0))errors.push('overflow '+index);});return errors;
  });assert.deepEqual(grid,[],'Merged cells must correctly span derived and spacer rows');
  await shot('derived.png');await frame.locator('section[aria-label="S&OP summary"]').screenshot({path:path.join(__dirname,'summary-stats.png')});
  pass('Independent run-rate/growth switches add only bridge-eligible rows below amounts. Share stays percentage-only; PI/net omit growth. Merged-cell geometry includes derived/spacer rows, while graph markup and selected measures remain unchanged.');

  const derivedMath=await frame.evaluate(id=>{
   const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];let difference;
   for(const display of ['units','value']){
    a.setState({display,sectors:a.sectors.map(s=>s.id),grouping:'combined'});const g=a.groups()[0];
    for(const cycle of ['2026-10','2026-07'])for(const row of a.rows.filter(r=>!r.ratio))for(const period of ['FY','YTD','YTG']){
     const n=Number(cycle.slice(5,7))-(row.basis==='ims'?2:1),from=period==='YTG'?n:0,to=period==='YTD'?n:12,months=Array.from({length:to-from},(_,i)=>24+from+i),total=shift=>g.sectors.reduce((sum,s)=>sum+months.reduce((sum,t)=>sum+a.source(s,t+shift,cycle)[display][row.id],0),0),current=total(0),prior=total(-12),col={id:'2026:'+period};
     if(a.summaryRules.runRateEligibleIds.includes(row.id))out.push([a.summaryValue(row,g,col,cycle,'run-rate'),current/months.length]);
     if(a.summaryRules.growthEligibleIds.includes(row.id))out.push([a.summaryValue(row,g,col,cycle,'growth'),current/prior-1]);
    }
    if(display==='units'){const row=m.get('market'),months=Array.from({length:12},(_,i)=>24+i),v=t=>a.amount(row,g,[t],'2026-10'),mean=months.reduce((sum,t)=>sum+v(t)/v(t-12)-1,0)/12;difference=Math.abs(a.summaryValue(row,g,{id:'2026:FY'},'2026-10','growth')-mean);}
   }
   const g=a.groups()[0];return {out,difference,rateEdges:[a.runRate(0,12),a.runRate(12,0),a.runRate(null,12),a.runRate('12',12)],growthEdges:[a.growthRate(0,10),a.growthRate(10,0),a.growthRate(0,0),a.growthRate(null,5),a.growthRate(10,null),a.growthRate(-5,10)],unavailable:a.summaryValue(m.get('community'),g,{id:'2024:FY'},'2026-10','growth'),shareRate:a.summaryValue(m.get('share'),g,{id:'2026:FY'},'2026-10','run-rate')};
  },apiId);
  derivedMath.out.forEach(([a,b])=>near(a,b));assert.ok(derivedMath.difference>1e-8,'Growth is a ratio of totals, not a mean of monthly percentages');
  assert.deepEqual(derivedMath.rateEdges,[0,null,null,null]);assert.deepEqual(derivedMath.growthEdges,[-1,null,null,null,null,-1.5]);assert.equal(derivedMath.unavailable,null);assert.equal(derivedMath.shareRate,null);
  pass(`${derivedMath.out.length} direct fixture comparisons verify FY/YTD/YTG run-rate month counts and exact prior-year windows for Units/Value, both cycles and both cutoff bases. Zero current remains valid; missing/zero prior stays blank; growth uses complete totals.`);

  await set({...selected,showRunRate:true,showGrowth:true,display:'value'});
  assert.match(await frame.locator('[data-derived-row="wholesaler"][data-summary-kind="run-rate"]').innerText(),/£/);
  assert.doesNotMatch(await frame.locator('[data-derived-row="wholesaler"][data-summary-kind="growth"]').innerText(),/£/);
  await frame.locator('[data-table="monthly"]').click();
  assert.equal(await frame.locator('#sb-show-run-rate').isDisabled(),true);
  assert.equal(await frame.locator('[data-summary-kind="run-rate"]').count(),0);assert.equal(await frame.locator('[data-summary-kind="growth"]').count(),5);
  const monthGrowth=await frame.evaluate(id=>{const a=document.getElementById(id).sopDesign,row=a.rows.find(r=>r.id==='wholesaler'),g=a.groups()[0];return [a.summaryValue(row,g,{month:33},'2026-10','growth'),a.amount(row,g,[33],'2026-10')/a.amount(row,g,[21],'2026-10')-1];},apiId);near(...monthGrowth);
  await frame.locator('[data-table="periods"]').click();assert.equal(await frame.locator('[data-summary-kind="run-rate"]').count(),7);
  await frame.locator('#sb-show-run-rate').uncheck();assert.equal(await frame.locator('[data-summary-kind="growth"]').count(),5);
  await frame.locator('#sb-show-growth').uncheck();assert.equal(await frame.locator('[data-derived-row]').count(),0);
  await set(selected);
  pass('Run-rate Value rows retain GBP and growth rows remain percentages. Monthly columns suppress redundant run-rate rows while preserving the switch choice; monthly growth compares the same month last year. Switches remain independent.');
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
  const contextIds=catalog.displayOrder.filter(id=>catalog.bindings.find(b=>b.id===id).kind==='ads');
  assert.deepEqual(await frame.locator('[data-source-context]').evaluateAll(ns=>ns.map(n=>n.dataset.sourceContext)),contextIds);
  assert.ok(contextIds.indexOf('retail')<contextIds.indexOf('private'));
  assert.equal(await frame.locator('[data-channel="contracts"]').count(),1);
  assert.match(await frame.locator('.sb-channel-continuation').innerText(),/Contracts.*continued/s);
  for(const id of contextIds.filter(id=>id!=='community')){
   assert.deepEqual(await frame.locator(`[data-measures-for="${id}"] [data-measure]`).evaluateAll(ns=>ns.map(n=>n.dataset.measure)),[id]);
   await measure(id).click();assert.deepEqual(await rowIds(),catalog.displayOrder.filter(key=>key!==id));await measure(id).click();
  }
  assert.equal(await frame.locator('[data-summary-channel="Contracts"]').count(),2,'Source order resumes Contracts after Retail');
  assert.equal(await frame.locator('#sb-summary tbody [data-row]').count(),18);
  assert.equal(await frame.locator('#sb-summary .sb-summary-spacer').count(),17);
  assert.equal(await frame.locator('#sb-summary [data-spacing="channel"]').count(),5);
  assert.equal(await frame.locator('#sb-summary [data-spacing="subchannel"]').count(),7);
  assert.equal(await frame.locator('#sb-summary [data-spacing="measure"]').count(),5);
  assert.equal(await frame.locator('#sb-summary tbody tr:not([data-row]):not(.sb-summary-spacer)').count(),0);
  await shot('all-contexts.png');
  pass('All 13 selector contexts and summary records follow the audited source order, including Retail before Private Order/Internal Account. Every remaining context exposes only its own independently toggled ADS; Contracts continuation introduces no extra Channel filter.');
  await frame.locator('#sb-clear-rows').click();assert.deepEqual(await rowIds(),[]);
  await set(selected);const affiliate=frame.locator('[data-filter="affiliates"]');await affiliate.locator('button').click();
  await affiliate.locator('input[type="checkbox"]').uncheck();assert.deepEqual(await rowIds(),[]);
  await affiliate.locator('input[type="checkbox"]').check();await affiliate.locator('button').click();
  const scope=await get();await frame.locator('#sb-all-scope').click();const inclusive=await get();
  await frame.locator('[data-grouping="driver"]').click();assert.equal(await frame.locator('.sb-plot').count(),2);
  assert.equal(await frame.locator('#sb-summary thead th').first().innerText(),'Review scope');
  assert.equal(await frame.locator('#sb-summary .sb-summary-scope').count(),2);
  assert.deepEqual(await frame.locator('#sb-summary .sb-summary-scope').evaluateAll(ns=>ns.map(n=>n.rowSpan)),[15,15]);
  assert.equal(await frame.locator('#sb-summary tbody tr:not([data-row]):not(.sb-summary-spacer)').count(),0);
  assert.deepEqual((await get()).selectedMeasures,inclusive.selectedMeasures);assert.deepEqual((await get()).sectors,inclusive.sectors);
  await frame.locator('[data-grouping="sector"]').click();assert.equal(await frame.locator('.sb-plot').count(),4);
  await set(scope);
  pass('Select matches/all adds only the requested 18 source measures. Affiliate gates results. Total/Drivers/Sectors beside the graph changes presentation without changing included sectors or measures.');

  const originalPage=await browser.newPage();await originalPage.goto(pathToFileURL(path.join(__dirname,'../sop-section-visibility-r11/index.html')).href);
  const original=originalPage.frames().find(f=>f!==originalPage.mainFrame());await original.waitForSelector('#sb-summary');
  const snapshot=(f,id)=>f.evaluate(({id,ids})=>{const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];for(const display of ['units','value']){a.setState({display,sectors:['compact','juce'],grouping:'combined'});const g=a.groups()[0];for(const cycle of ['2026-10','2026-07'])for(const key of ids)for(const p of ['2026:FY','2026:YTD','2026:YTG'])out.push(a.amount(m.get(key),g,a.periodMonths(m.get(key),p,cycle),cycle));}return out;},{id,ids});
  const before=await snapshot(original,'fm-sop-section-visibility-r11'),after=await snapshot(frame,apiId);before.forEach((v,i)=>near(v,after[i]));await originalPage.close();
  pass(`${before.length} retained measure/period/cycle/dimension values match saved R11's synthetic observations exactly.`);

  const invariants=await frame.evaluate(id=>{const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];for(const display of ['units','value']){a.setState({display,sectors:a.sectors.map(s=>s.id)});const g=a.groups()[0];for(const t of [24,31,32,33,35]){const v=id=>a.amount(m.get(id),g,[t],'2026-10');out.push([v('community'),v('wholesaler')+v('ni')],[v('ads'),a.leaves.reduce((n,id)=>n+v(id),0)],[v('share'),v('abbott')/v('market')]);}for(const row of a.rows){const v=p=>a.amount(row,g,a.periodMonths(row,p,'2026-10'),'2026-10');if(!row.ratio)out.push([v('2026:FY'),v('2026:YTD')+v('2026:YTG')]);}}return out;},apiId);invariants.forEach(([a,b])=>near(a,b));
  pass(`${invariants.length} checks preserve Community/sector totals, weighted Share and FY=YTD+YTG in both dimensions; no arithmetic change accompanies the layout simplification.`);

  await set(selected);await set({periods:['2026:FY']});assert.equal((await get()).monthStart,selected.monthStart);
  await frame.locator('#sb-start').fill('2026-04');await frame.locator('#sb-start').dispatchEvent('change');assert.deepEqual((await get()).periods,['2026:FY']);
  await frame.locator('[data-table="monthly"]').click();assert.equal(await frame.locator('#sb-summary thead th').count(),12);
  await set(selected);await frame.locator('#sb-panel-toggle').click();assert.equal((await rowIds()).length,8);
  await frame.locator('#sb-panel-toggle').click();
  pass('Visible calendar dates constrain summary years, while named periods keep their complete business windows. Monthly columns use exact review months; hiding the selector preserves choices.');

  await set(selected);
  const periodPicker=frame.locator('[data-filter="periods"]'),periodChoices=()=>periodPicker.locator('.sb-options input').evaluateAll(ns=>ns.map(n=>n.value));
  await periodPicker.locator('button').click();assert.deepEqual(await periodChoices(),['2026:FY','2026:YTD','2026:YTG']);
  assert.equal(await periodPicker.locator('input[value="2027:FY"]').count(),0);
  await set({monthEnd:'2027-12'});assert.deepEqual(await periodChoices(),['2026:FY','2026:YTD','2026:YTG','2027:FY','2027:YTD','2027:YTG']);
  await periodPicker.locator('input[value="2027:FY"]').check();assert.equal(await frame.locator('#sb-summary th').filter({hasText:/^2027 FY$/}).count(),1);
  await shot('two-years.png');
  await set({monthEnd:'2026-12'});assert.equal(await periodPicker.locator('input[value="2027:FY"]').count(),0);assert.equal((await get()).periods.includes('2027:FY'),false);
  assert.deepEqual(await frame.locator('#sb-summary thead th').allTextContents(),['Channel','Sub-channel','Measure','2026 FY','2026 YTD','2026 YTG']);
  await periodPicker.locator('button').click();await shot('single-year.png');
  const amountFY=await frame.locator('[data-row="wholesaler"] [data-column="2026:FY"]').getAttribute('data-value');
  await set({monthStart:'2026-04',monthEnd:'2026-09'});assert.equal(await frame.locator('[data-row="wholesaler"] [data-column="2026:FY"]').getAttribute('data-value'),amountFY);
  assert.match(await frame.locator('#sb-table-context').innerText(),/FY is Jan–Dec/);
  await frame.locator('[data-table="monthly"]').click();assert.deepEqual((await frame.locator('#sb-summary thead th').allTextContents()).slice(3),['Apr 26','May 26','Jun 26','Jul 26','Aug 26','Sept 26']);
  await set({monthStart:'2027-01',monthEnd:'2027-12',table:'periods'});assert.deepEqual((await get()).periods,['2027:FY','2027:YTD','2027:YTG']);
  assert.deepEqual((await frame.locator('#sb-summary thead th').allTextContents()).slice(3),['2027 FY','2027 YTD','2027 YTG']);
  await set({periods:[]});await set({monthStart:'2026-01',monthEnd:'2026-12'});assert.deepEqual((await get()).periods,[],'Explicit clear must stay clear');
  await set({...selected,monthEnd:'2027-12',periods:['2026:YTG','2027:FY'],summaryOpen:false});
  await frame.locator('#sb-end').fill('2026-12');await frame.locator('#sb-end').dispatchEvent('change');assert.deepEqual((await get()).periods,['2026:YTG']);
  await frame.locator('#sb-summary-toggle').click();assert.deepEqual((await frame.locator('#sb-summary thead th').allTextContents()).slice(3),['2026 YTG']);
  await set({...selected,periods:['2026:FY'],monthStart:'2025-10',monthEnd:'2027-03'});
  const broad=await frame.evaluate(id=>document.getElementById(id).sopDesign.availablePeriods().map(p=>p.id),apiId);assert.equal(broad.length,9);assert.deepEqual([...new Set(broad.map(p=>p.slice(0,4)))],['2025','2026','2027']);
  await set(selected);
  pass('Summary choices and columns follow inclusive calendar years: 2026 excludes 2027; widening adds available choices, narrowing removes stale columns. Year changes retain selected period kinds; explicit clearing stays empty. Partial-year FY remains Jan-Dec, Monthly uses exact months, and hidden summaries refresh correctly.');

  await set({...selected,showRunRate:true,showGrowth:true});
  const visibilityBase=await get(),tableBefore=await frame.locator('#sb-summary').innerHTML();
  const sections=[['panelOpen','#sb-selector-body','#sb-panel-toggle'],['graphOpen','#sb-graph-body','#sb-graph-toggle'],['summaryOpen','#sb-summary-body','#sb-summary-toggle']];
  const withoutVisibility=s=>Object.fromEntries(Object.entries(s).filter(([k])=>!sections.some(([key])=>key===k)));
  const narrowChart=await frame.locator('.sb-plot svg').first().evaluate(n=>n.getBoundingClientRect().width);
  let visibilityChecks=0;
  for(const [key,body,button] of sections){
   assert.equal(await frame.locator(button).innerText(),'Hide');
   assert.equal(await frame.locator(button).getAttribute('aria-controls'),body.slice(1));
   const aligned=await frame.locator(button).evaluate(n=>{const h=n.parentElement.getBoundingClientRect(),b=n.getBoundingClientRect(),title=n.parentElement.querySelector('h2').getBoundingClientRect();return b.right>=h.right-14&&Math.abs(b.top-title.top)<15;});assert.ok(aligned,`${key} button not at top right`);
  }
  for(const index of [0,1,0,2,0,1,0,2]){
   const [key,,button]=sections[index];await frame.locator(button).click();await page.waitForTimeout(30);
   const current=await get();assert.deepEqual(withoutVisibility(current),withoutVisibility(visibilityBase));
   assert.equal(await frame.locator('#sb-summary').innerHTML(),tableBefore);
   for(const [k,body,b] of sections){assert.equal(await frame.locator(body).isVisible(),current[k]);assert.equal(await frame.locator(b).getAttribute('aria-expanded'),String(current[k]));assert.equal(await frame.locator(b).innerText(),current[k]?'Hide':'Show');}
   assert.equal(await frame.locator('#sb-graph-view').isVisible(),current.graphOpen);
   assert.equal(await frame.locator('#sb-summary-view').isVisible(),current.summaryOpen);
   if(!current.panelOpen&&current.graphOpen){const w=await frame.locator('.sb-plot svg').first().evaluate(n=>n.getBoundingClientRect().width);assert.ok(w>narrowChart+200);}
   if(!current.panelOpen&&!current.graphOpen&&!current.summaryOpen){
    for(const s of ['#sb-channel-panel','#sb-graph-panel','#sb-summary-panel'])assert.ok((await frame.locator(s).boundingBox()).height<70);
    await shot('all-hidden.png');
   }
   visibilityChecks++;
  }
  assert.deepEqual(await get(),visibilityBase);
  await frame.locator('#sb-graph-toggle').focus();await page.keyboard.press('Enter');assert.equal((await get()).graphOpen,false);
  await shot('graph-hidden.png');
  await set({display:'value',periods:['2026:YTG']});
  await frame.locator('#sb-graph-toggle').click();assert.ok((await frame.locator('#sb-graph-context').innerText()).startsWith('Value in GBP'));
  await frame.locator('#sb-summary-toggle').click();
  await set({periods:['2026:FY','2026:YTD'],showRunRate:false,showGrowth:true});
  await frame.locator('#sb-summary-toggle').click();
  assert.deepEqual(await frame.locator('#sb-summary thead th').allTextContents(),['Channel','Sub-channel','Measure','2026 FY','2026 YTD']);
  assert.equal(await frame.locator('[data-summary-kind="run-rate"]').count(),0);assert.equal(await frame.locator('[data-summary-kind="growth"]').count(),5);
  await frame.evaluate(({id})=>window.dispatchEvent(new CustomEvent('openai:set_globals',{detail:{globals:{widgetState:{modelContent:{schema:id,state:{...document.getElementById(id).sopDesign.getState(),panelOpen:false,graphOpen:true,summaryOpen:false}}}}}})),{id:apiId});
  assert.equal(await frame.locator('#sb-selector-body').isVisible(),false);assert.equal(await frame.locator('#sb-summary-body').isVisible(),false);assert.equal(await frame.locator('#sb-graph-body').isVisible(),true);
  await shot('graph-only.png');
  await set({...selected,panelOpen:false,graphOpen:false,summaryOpen:true,showRunRate:true,showGrowth:true});await shot('summary-only-view.png');
  await set(selected);
  pass('All eight visibility combinations work through local Hide/Show controls. Hidden sections retain compact accessible restore headings, selections and table values. Selector collapse widens/redraws the graph; keyboard restore, hidden-state updates and restored host state preserve current periods, Units/Value and derived-row settings.');

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
  const result={schema:'FM_SOP_CALENDAR_SPACING_R12_VALIDATION',checkedAt:new Date().toISOString(),checks,visibilityCombinations:visibilityChecks,sourceBindings:ids.length,auditedContexts:audit.sourceContextCount,sourceIdentityMatches:audit.bindingIdentityMatches,derivedComparisons:derivedMath.out.length,retainedValueComparisons:before.length,reconciliationComparisons:invariants.length,errors,warmNetworkRequests:requests.length-warm,note:'Synthetic HTML design and retained metadata qualification only; no live source binding, report deployment or Power BI speed claim.'};
  fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
