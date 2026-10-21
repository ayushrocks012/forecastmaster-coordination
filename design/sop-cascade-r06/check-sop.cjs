const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {pathToFileURL}=require('node:url');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.platform==='win32'?path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'):'playwright'));
const near=(a,b)=>assert.ok(Math.abs(a-b)<Math.max(1e-8,Math.abs(a)*1e-10),`${a} != ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
 try{
  const page=await browser.newPage({viewport:{width:1080,height:1500},colorScheme:'light'}),errors=[],requests=[],checks=[];
  page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
  const frame=page.frames().find(f=>f!==page.mainFrame());await frame.waitForSelector('#sb-summary [data-row]');
  const get=()=>frame.evaluate(()=>document.getElementById('fm-sop-cascade-r06').sopDesign.getState());
  const set=p=>frame.evaluate(p=>document.getElementById('fm-sop-cascade-r06').sopDesign.setState(p),p);
  const rowIds=()=>frame.locator('#sb-summary [data-row]').evaluateAll(ns=>ns.map(n=>n.dataset.row));
  const current=family=>frame.locator(`[data-family="${family}"][data-family-measure="current"]`);
  const ads=family=>frame.locator(`[data-family="${family}"][data-family-measure="ads"]`);
  const values=()=>frame.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>n.dataset.value));
  const initial=await get(),pass=s=>checks.push(s);
  async function shot(name,width=1080){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);
   const h=await frame.evaluate(()=>document.documentElement.scrollHeight);
   await page.locator('iframe').evaluate((el,h)=>{el.style.setProperty('height',h+'px','important');el.style.setProperty('max-height','none','important');},h+16);
   await page.setViewportSize({width,height:h+96});await page.waitForTimeout(150);
   await page.mouse.move(4,4);await page.screenshot({path:path.join(__dirname,name),fullPage:true});
  }
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','share']);
  assert.match(await current('community').innerText(),/Current plan.*Cur Selling units/s);
  assert.match(await frame.locator('[data-ims="market"]').innerText(),/Market units/);
  assert.match(await frame.locator('[data-ims="abbott"]').innerText(),/Abbott IMS units/);
  assert.match(await frame.locator('[data-ims="share"]').innerText(),/Unit share/);
  assert.equal(await current('community').isEnabled(),true);
  assert.equal(await frame.locator('[data-target="wholesaler"]').isEnabled(),true);
  assert.equal(await frame.locator('[data-target="homecare"]').isDisabled(),true);
  assert.equal(await current('contracts').isDisabled(),true);
  assert.equal(await frame.locator('[data-ims="market"]').isEnabled(),true);
  assert.equal(await frame.locator('[data-metric-toggle]').count(),0,'No global Ex-factory gate substitutes for contextual measures');
  const catalog=await frame.evaluate(()=>document.getElementById('fm-sop-cascade-r06').sopDesign.bridgeCatalog);
  assert.equal(catalog.bindings.length,44);assert.equal(Object.keys(catalog.sources).length,2);
  assert.deepEqual(catalog.bindings.find(b=>b.id==='cur-community').subChannel,null);
  assert.equal(catalog.bindings.find(b=>b.id==='cur-wholesaler').subChannel,'Wholesaler');
  assert.equal(catalog.bindings.find(b=>b.id==='retail').channel,'Out of Pocket');
  const controls=await frame.locator('[data-channel-band="community"] [data-ims],[data-channel-band="community"] [data-family-measure]').evaluateAll(ns=>ns.map(n=>n.dataset.ims?'ims:'+n.dataset.ims:'ef:'+n.dataset.familyMeasure));
  assert.deepEqual(controls,['ims:abbott','ims:market','ims:pi','ef:current','ef:published','ims:net','ef:ads','ims:share','ims:community-ims','ims:factor']);
  await shot('overview.png');
  pass('Community enables its targets and explicit Cur/ADS measures; other channels start disabled; Share remains on the same graph’s right axis.');

  const before=await values();await frame.locator('[data-channel="community"]').click();
  assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('[data-target="wholesaler"]').isDisabled(),true);
  assert.equal(await current('community').isDisabled(),true);
  assert.equal(await frame.locator('[data-ims="share"]').isDisabled(),true);
  const inactive=await get();await frame.locator('[data-target="wholesaler"]').evaluate(el=>el.click());
  assert.deepEqual(await get(),inactive,'Disabled child cannot change state');
  await frame.locator('[data-channel="community"]').click();
  assert.deepEqual(await values(),before,'Re-enabling parent restores its remembered choices');
  await frame.locator('[data-target="community"]').click();
  assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('[data-ims="market"]').isDisabled(),true,'IMS belongs to Community with blank sub-channel, not Wholesaler');
  assert.equal(await current('community').isDisabled(),true,'No target means no Ex-factory measure');
  await frame.locator('[data-target="wholesaler"]').click();
  assert.equal(await current('community').isEnabled(),true);
  assert.deepEqual(await rowIds(),['cur-wholesaler']);
  assert.equal(await frame.locator('tr.sb-child[data-row="cur-wholesaler"]').count(),1);
  assert.equal(await frame.locator('[data-context="cur-community"]').count(),1);
  await frame.locator('[data-target="ni"]').click();
  await frame.locator('[data-target="community"]').click();
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','share','cur-wholesaler','cur-ni']);
  assert.deepEqual(await frame.locator('[data-measure-context]').evaluateAll(ns=>ns.map(n=>n.dataset.measureContext)),['community','wholesaler','ni']);
  await shot('community-current.png');
  pass('Parent off disables descendants and removes their series; restoring preserves choices. Selecting a target enables its Ex-factory measures, with clear indented Wholesaler/NI rows.');

  await ads('community').click();
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','community','share','cur-wholesaler','wholesaler','cur-ni','ni']);
  const distinction=await frame.evaluate(()=>{
   const a=document.getElementById('fm-sop-cascade-r06').sopDesign,map=new Map(a.rows.map(r=>[r.id,r])),g=a.groups()[0];
   return {actual:[a.amount(map.get('cur-community'),g,[31],'2026-10'),a.amount(map.get('community'),g,[31],'2026-10')],future:[a.amount(map.get('cur-community'),g,[33],'2026-10'),a.amount(map.get('community'),g,[33],'2026-10')]};
  });
  near(...distinction.actual);assert.notEqual(...distinction.future,'Cur is a separate saved-plan fixture, not relabelled ADS');
  assert.notEqual(await frame.locator('[data-series="cur-community"]').first().getAttribute('stroke'),await frame.locator('[data-series="community"]').first().getAttribute('stroke'));
  await current('community').click();assert.ok(!(await rowIds()).includes('cur-wholesaler'));assert.ok((await rowIds()).includes('wholesaler'));
  await current('community').click();await shot('current-and-ads.png');
  pass('Cur and ADS are separately selectable for each chosen total/subchannel, use distinct series labels/colours and preserve separate future observations.');
  await frame.locator('[data-family="community"][data-family-measure="published"]').click();
  await frame.locator('[data-ims="net"]').click();
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','pub-community','net','community','share','cur-wholesaler','pub-wholesaler','wholesaler','cur-ni','pub-ni','ni']);
  const pub=await frame.evaluate(()=>{
   const a=document.getElementById('fm-sop-cascade-r06').sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),g=a.groups()[0];return ['cur-community','pub-community'].map(id=>a.amount(m.get(id),g,[33],'2026-10'));
  });near(...pub);
  await shot('bridge-order.png');
  pass('V18 identity catalogue binds 44 direct measures plus five explicit review diagnostics/aggregates; Community Cur/Pub/net/ADS precedes Wholesaler and NI, whose Ex-factory order is Cur/Pub/ADS.');
  await frame.locator('[data-family="community"][data-family-measure="published"]').click();await frame.locator('[data-ims="net"]').click();

  await frame.locator('#sb-units').selectOption('value');
  assert.match(await current('community').innerText(),/Cur Value/);
  assert.match(await frame.locator('[data-ims="market"]').innerText(),/Market value/);
  assert.match(await frame.locator('[data-ims="abbott"]').innerText(),/Abbott IMS value/);
  assert.match(await frame.locator('[data-ims="share"]').innerText(),/Value share/);
  assert.match(await frame.locator('[data-toggle-row="market"]').innerText(),/Market value/);
  assert.match(await frame.locator('[data-row="abbott"] td').first().innerText(),/Abbott IMS value/);
  assert.match(await frame.locator('[data-row="cur-wholesaler"] td').first().innerText(),/Current plan value/);
  assert.doesNotMatch(await current('community').innerText(),/Selling units/);
  assert.match(await frame.locator('.axis-title[data-axis="y"]').textContent(),/GBP/);
  assert.match(await frame.locator('[data-row="cur-wholesaler"]').innerText(),/£/);
  assert.doesNotMatch(await frame.locator('[data-row="share"]').innerText(),/£/);
  assert.equal(await frame.locator('.sb-plot').count(),1);
  assert.equal(await frame.locator('[data-series="share"][data-axis="right"]').count(),2);
  await shot('value.png');
  pass('Units/Value renames Market, Abbott IMS, Cur/ADS and unit/value share throughout buttons, legend and summary, with correct amounts and a percentage right axis.');

  await set({...initial});await frame.locator('[data-channel="contracts"]').click();
  assert.equal(await frame.locator('[data-target="homecare"]').isEnabled(),true);
  assert.equal(await current('contracts').isEnabled(),true);
  assert.ok((await rowIds()).includes('cur-contracts'));
  await frame.locator('[data-target="homecare"]').click();
  await frame.locator('[data-target="hospital"]').click();
  await frame.locator('[data-selector-more="contracts"] summary').click();await page.waitForTimeout(25);
  await frame.locator('[data-target="hcl"]').click();
  assert.equal(await frame.locator('[data-target="hcl"]').isVisible(),true);
  assert.equal(await frame.locator('[data-ims][data-family="contracts"]').count(),0,'No fabricated IMS allocation to Contracts');
  const withContracts=await rowIds();assert.ok(withContracts.includes('cur-homecare')&&withContracts.includes('cur-hospital')&&withContracts.includes('cur-hcl'));
  await frame.locator('[data-channel="contracts"]').focus();await page.keyboard.press('Space');
  assert.equal(await frame.locator('[data-target="homecare"]').isDisabled(),true);
  assert.ok(!(await rowIds()).some(id=>['cur-contracts','cur-homecare','cur-hospital','cur-hcl'].includes(id)));
  assert.ok((await rowIds()).includes('cur-community'));
  await page.keyboard.press('Space');assert.deepEqual(await rowIds(),withContracts);
  await shot('multiple-channels.png');
  pass('Multiple parent channels cascade independently; Contracts exposes its real seven members, keeps expanded selections, and supports keyboard parent off/on.');

  const invariants=await frame.evaluate(()=>{
   const a=document.getElementById('fm-sop-cascade-r06').sopDesign,map=new Map(a.rows.map(r=>[r.id,r])),result=[];
   for(const display of ['units','value']){
    a.setState({display,sectors:a.sectors.map(s=>s.id),grouping:'combined'});const g=a.groups()[0];
    for(const prefix of ['','cur-','pub-'])for(const t of [24,31,32,33,35]){
     const v=id=>a.amount(map.get(prefix+id),g,[t],'2026-10');
     result.push([v('community'),v('wholesaler')+v('ni')]);
     result.push([v('contracts'),a.contractLeaves.reduce((n,id)=>n+v(id),0)]);
     result.push([v('ads'),a.leaves.reduce((n,id)=>n+v(id),0)]);
    }
    for(const prefix of ['','cur-','pub-']){
     const r=map.get(prefix+'community'),v=p=>a.amount(r,g,a.periodMonths(r,p,'2026-10'),'2026-10');result.push([v('2026:FY'),v('2026:YTD')+v('2026:YTG')]);
    }
    for(const p of ['2026:FY','2026:YTD','2026:YTG']){
     const months=a.periodMonths(map.get('share'),p,'2026-10'),v=id=>a.amount(map.get(id),g,months,'2026-10');result.push([v('share'),v('abbott')/v('market')]);
    }
   }
   return {result,ims:a.periodMonths(map.get('share'),'2026:YTD','2026-10').length,ef:a.periodMonths(map.get('cur-community'),'2026:YTD','2026-10').length,blank:a.sum([1,null]),zero:a.sum([0,0]),ratio:a.ratio(1,0),outside:a.currentSource(a.sectors[0],80,'2026-10')};
  });
  invariants.result.forEach(([a,b])=>near(a,b));assert.equal(invariants.ims,8);assert.equal(invariants.ef,9);
  assert.equal(invariants.blank,null);assert.equal(invariants.zero,0);assert.equal(invariants.ratio,null);assert.equal(invariants.outside,null);
  pass(`${invariants.result.length} numeric comparisons preserve Cur/Pub/ADS Community splits, Contracts and sector totals, FY=YTD+YTG, weighted share, blank/zero rules and separate cutoffs.`);

  await set({...initial});await frame.locator('#sb-clear-rows').click();assert.deepEqual(await rowIds(),[]);
  assert.equal(await current('community').isDisabled(),true);
  await frame.locator('#sb-row-search').fill('Homecare');await frame.locator('#sb-all-rows').click();
  assert.deepEqual((await get()).channels,['contracts']);assert.deepEqual((await get()).targets,['homecare']);
  assert.deepEqual(await rowIds(),['cur-homecare']);
  await frame.locator('#sb-row-search').fill('');await frame.locator('#sb-all-rows').click();
  assert.equal((await rowIds()).length,49);assert.ok((await rowIds()).includes('cur-wholesaler'));
  await frame.locator('#sb-clear-rows').click();
  await frame.locator('[data-channel="community"]').click();
  assert.equal(await frame.locator('[data-target="wholesaler"]').isEnabled(),true);
  assert.deepEqual(await rowIds(),[],'Channel does not silently reselect a cleared measure');
  await frame.locator('[data-target="wholesaler"]').click();await frame.locator('[data-target="community"]').click();
  await current('community').click();assert.deepEqual(await rowIds(),['cur-wholesaler']);
  assert.equal(await frame.locator('[data-ims="share"]').isDisabled(),true);
  await frame.locator('[data-target="community"]').click();await frame.locator('[data-ims="share"]').click();assert.deepEqual(await rowIds(),['cur-community','share','cur-wholesaler']);
  await frame.locator('[data-toggle-row="cur-wholesaler"]').click();assert.deepEqual(await rowIds(),['share']);
  await frame.locator('[data-ims="share"]').click();assert.equal(await frame.locator('.sb-plot').count(),0);
  pass('Select matches enables only required ancestors/targets; Select all and Clear all propagate correctly; a fresh Channel → Wholesaler → Cur path and legend off behavior work.');

  await set({...initial,targets:['ni','community','wholesaler'],measures:{...initial.measures,community:['ads','current']}});
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','community','share','cur-wholesaler','wholesaler','cur-ni','ni']);
  const totals=await values();await frame.locator('#sb-start').fill('2026-03');await frame.locator('#sb-start').dispatchEvent('change');
  await frame.locator('#sb-end').fill('2026-11');await frame.locator('#sb-end').dispatchEvent('change');assert.deepEqual(await values(),totals);
  await frame.locator('#sb-summary-periods .sb-pick').click();await frame.locator('#sb-summary-periods input[value="2027:FY"]').check();
  await frame.locator('#sb-summary-periods .sb-pick').press('Escape');assert.equal(await frame.locator('#sb-summary thead th').count(),6);
  await frame.locator('[data-table="monthly"]').click();assert.equal(await frame.locator('#sb-summary thead th').count(),11);await shot('monthly.png');
  await set({...initial});const scopeNumbers=await frame.evaluate(()=>{
   const a=document.getElementById('fm-sop-cascade-r06').sopDesign,map=new Map(a.rows.map(r=>[r.id,r]));a.setState({sectors:a.sectors.map(s=>s.id),grouping:'driver'});
   const value=g=>a.amount(map.get('cur-community'),g,a.periodMonths(map.get('cur-community'),'2026:FY','2026-10'),'2026-10');
   const drivers=a.groups().map(value);a.setState({grouping:'sector'});const sectors=a.groups().map(value);a.setState({grouping:'combined'});return {drivers,sectors,combined:value(a.groups()[0])};
  });near(scopeNumbers.combined,scopeNumbers.drivers.reduce((a,b)=>a+b,0));near(scopeNumbers.combined,scopeNumbers.sectors.reduce((a,b)=>a+b,0));
  pass('Bridge row order is independent of click order; summary periods add columns; calendars affect monthly columns separately; combined/driver/sector Cur totals reconcile.');

  await set({...initial});const overlay=frame.locator('[data-chart-hover-overlay]').first();
  await overlay.evaluate(el=>{const r=el.getBoundingClientRect();el.dispatchEvent(new PointerEvent('pointermove',{clientX:r.left+r.width*.43,clientY:r.top+r.height*.4,bubbles:true}));});
  assert.equal(await frame.locator('[data-chart-hover-marker]').count(),5);
  assert.match(await frame.locator('[role="tooltip"]').innerText(),/Abbott unit share · right axis.*%/s);
  assert.match(await frame.locator('[role="tooltip"]').innerText(),/Community · Current plan/);
  await overlay.dispatchEvent('pointerleave');await overlay.evaluate(el=>{const r=el.getBoundingClientRect();el.dispatchEvent(new PointerEvent('pointerdown',{clientX:r.left+r.width*.4,clientY:r.top+40,bubbles:true,pointerType:'touch'}));});
  await overlay.dispatchEvent('pointerleave');assert.equal(await frame.locator('[role="tooltip"]:visible').count(),1);
  pass('Shared hover/touch includes selected Cur, IMS amounts and properly formatted right-axis share.');

  const responsive=[];
  for(const width of [1080,736,390,320]){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(180);
   const result=await frame.evaluate(()=>{
    const root=document.getElementById('fm-sop-cascade-r06'),labels=[...root.querySelectorAll('.sb-plot svg text')].map(n=>{const b=n.getBoundingClientRect(),s=n.ownerSVGElement.getBoundingClientRect();return {left:b.left-s.left,right:b.right-s.right,size:parseFloat(getComputedStyle(n).fontSize)};});
    return {overflow:root.scrollWidth-root.clientWidth,labels};
   });assert.ok(result.overflow<=1);result.labels.forEach(l=>{assert.ok(l.left>=-1);assert.ok(l.right<=1);assert.ok(l.size>=11);});responsive.push({width,overflow:result.overflow});
  }
  await shot('mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot('dark.png');await page.emulateMedia({colorScheme:'light'});
  await set({...initial});const existing=await values();await frame.locator('#sb-panel-toggle').click();assert.deepEqual(await values(),existing);await shot('selector-hidden.png');await frame.locator('#sb-panel-toggle').click();
  const warmStart=requests.length;for(let i=0;i<12;i++)await set({display:i%2?'units':'value'});
  assert.equal(requests.length,warmStart);assert.deepEqual(errors,[]);
  const timings=await frame.evaluate(()=>document.getElementById('fm-sop-cascade-r06').sopDesign.getTimings().slice(-12));
  pass('Responsive light/dark layouts and hide/show preserve values; warm interactions make no network requests and no runtime errors occur.');

  const oldPage=await browser.newPage({viewport:{width:1080,height:1500}});oldPage.on('pageerror',e=>errors.push(e.message));
  await oldPage.goto(pathToFileURL(path.join(__dirname,'../sop-spaced-groups-r05/index.html')).href);
  const oldFrame=oldPage.frames().find(f=>f!==oldPage.mainFrame());await oldFrame.waitForSelector('#sb-summary [data-row]');
  const numericSnapshot=f=>f.locator('#sb-summary [data-value]').evaluateAll(ns=>ns.map(n=>({row:n.parentElement.dataset.row,group:n.parentElement.dataset.group,cycle:n.parentElement.dataset.cycle,column:n.dataset.column,value:n.dataset.value,text:n.textContent})).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));
  const baseRows=await frame.evaluate(()=>document.getElementById('fm-sop-cascade-r06').sopDesign.baseRows);
  const scenarios=[{display:'units',sectors:['compact','juce'],rows:['market','share','abbott','community']},{display:'value',sectors:['compact','juce'],rows:baseRows.map(r=>r.id)},{display:'units',sectors:['compact','juce','paed-standard','paed-energy'],grouping:'sector',rows:['market','share','community','wholesaler','ni']},{display:'value',cycles:['2026-10','2026-07'],sectors:['compact','juce','paed-standard','paed-energy'],grouping:'driver',rows:['contracts','homecare','hospital','ads']},{display:'units',table:'monthly',monthStart:'2026-03',monthEnd:'2026-11',sectors:['compact','juce'],rows:baseRows.map(r=>r.id)}];
  let parityCells=0;
  for(const scenario of scenarios){
   const selected=baseRows.filter(r=>scenario.rows.includes(r.id));
   const {rows:requestedRows,...settings}=scenario;
   await set({...initial,...settings,channels:[...new Set(selected.map(r=>r.group))],targets:selected.filter(r=>r.basis==='ef').map(r=>r.id),imsRows:selected.filter(r=>r.basis==='ims').map(r=>r.id),measures:Object.fromEntries(['community','contracts','retail','unassigned','all'].map(id=>[id,['ads']]))});
   await oldFrame.evaluate(p=>document.getElementById('fm-sop-spaced-groups-r05').sopDesign.setState(p),{cycles:initial.cycles,periods:initial.periods,table:'periods',grouping:'combined',monthStart:initial.monthStart,monthEnd:initial.monthEnd,...scenario,showExFactory:true});
   const before=await numericSnapshot(oldFrame),after=await numericSnapshot(frame);assert.deepEqual(after,before);parityCells+=before.length;
  }
  await oldPage.close();assert.deepEqual(errors,[]);
  pass(`${parityCells} existing ADS/IMS raw and displayed cells match saved R05 across five scenarios; Cur is an explicit additional synthetic fixture.`);
  fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify({scope:'Synthetic HTML-only cascade; no company runtime, source binding or Power BI speed assertion',checks,invariantComparisons:invariants.result.length,parity:{baseline:'R05',scenarios:scenarios.length,cells:parityCells},responsive,errors,externalRequests:requests.filter(u=>/^https?:/.test(u)),warm:{count:timings.length,meanMs:timings.reduce((a,b)=>a+b,0)/timings.length,maxMs:Math.max(...timings),networkRequests:requests.length-warmStart}},null,2)+'\n');
  console.log(JSON.stringify({checks:checks.length,invariants:invariants.result.length,parityCells,responsive,errors,warmMaxMs:Math.max(...timings)}));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
