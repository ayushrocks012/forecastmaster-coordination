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
  const get=()=>frame.evaluate(()=>document.getElementById('fm-sop-source-only-r07').sopDesign.getState());
  const set=p=>frame.evaluate(p=>document.getElementById('fm-sop-source-only-r07').sopDesign.setState(p),p);
  const rowIds=()=>frame.locator('#sb-summary [data-row]').evaluateAll(ns=>ns.map(n=>n.dataset.row));
  const measure=(family,kind='current')=>frame.locator(`[data-family="${family}"][data-family-measure="${kind}"]`);
  const pass=s=>checks.push(s),initial=await get();
  async function shot(name,width=1080){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(150);
   const h=await frame.evaluate(()=>document.documentElement.scrollHeight);
   await page.locator('iframe').evaluate((el,h)=>{el.style.setProperty('height',h+'px','important');el.style.setProperty('max-height','none','important');},h+16);
   await page.setViewportSize({width,height:h+96});await page.waitForTimeout(150);
   await page.mouse.move(4,4);await page.screenshot({path:path.join(__dirname,name),fullPage:true});
  }
  assert.deepEqual(initial.channels,[]);assert.deepEqual(initial.targets,[]);assert.deepEqual(initial.imsRows,[]);
  assert.ok(Object.values(initial.measures).every(v=>v.length===0));assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('#sb-charts svg').count(),0);await shot('empty.png');
  await frame.locator('[data-channel="community"]').click();
  assert.deepEqual((await get()).targets,[]);assert.deepEqual(await rowIds(),[]);
  assert.equal(await measure('community').isDisabled(),true);
  await frame.locator('[data-target="community"]').click();assert.deepEqual(await rowIds(),[]);
  assert.equal(await measure('community').isEnabled(),true);
  await frame.locator('[data-ims="abbott"]').click();assert.deepEqual(await rowIds(),['abbott']);
  assert.equal(await frame.locator('[data-series="abbott"]').count(),2);
  await frame.locator('[data-ims="abbott"]').click();assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('#sb-charts svg').count(),0);
  pass('Initial results are empty. Channel alone selects neither context nor measure; context alone is empty; selecting/removing the first measure adds/removes only that series and table row.');

  const catalog=await frame.evaluate(()=>document.getElementById('fm-sop-source-only-r07').sopDesign.bridgeCatalog);
  const ids=catalog.bindings.map(b=>b.id).sort(),apiIds=await frame.evaluate(()=>document.getElementById('fm-sop-source-only-r07').sopDesign.rows.map(r=>r.id).sort());
  assert.equal(ids.length,44);assert.deepEqual(apiIds,ids);assert.equal(catalog.derivedRows,undefined);
  assert.ok(!ids.some(id=>['contracts','cur-contracts','pub-contracts','factor','community-ims'].includes(id)));
  assert.equal(await frame.locator('[data-target="contracts"],[data-ims="factor"],[data-ims="community-ims"]').count(),0);
  assert.deepEqual(await frame.locator('[data-channel]').evaluateAll(ns=>ns.map(n=>n.textContent.replace(/[＋✓]/g,'').trim())),['Community','Contracts','Out of Pocket','Unassigned','Sector total']);
  assert.equal(catalog.bindings.find(b=>b.id==='cur-community').subChannel,null);
  assert.equal(catalog.bindings.find(b=>b.id==='retail').channel,'Out of Pocket');
  pass('All 44 available IDs match direct retained source bindings. No combined Contracts context, effective uplift, matched-IMS diagnostic or invented channel is selectable.');

  await frame.locator('[data-target="community"]').click();await frame.locator('[data-target="wholesaler"]').click();
  assert.equal(await frame.locator('[data-ims="market"]').isDisabled(),true);
  await measure('community').click();assert.deepEqual(await rowIds(),['cur-wholesaler']);
  await frame.locator('[data-target="ni"]').click();assert.deepEqual(await rowIds(),['cur-wholesaler','cur-ni']);
  await frame.locator('[data-channel="community"]').click();assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('[data-target="wholesaler"]').isDisabled(),true);
  const disabled=await get();await frame.locator('[data-target="wholesaler"]').evaluate(el=>el.click());assert.deepEqual(await get(),disabled);
  await frame.locator('[data-channel="community"]').click();assert.deepEqual(await rowIds(),['cur-wholesaler','cur-ni']);
  await frame.locator('[data-target="community"]').click();
  for(const id of ['abbott','market','pi','share'])await frame.locator(`[data-ims="${id}"]`).click();
  await measure('community','ads').click();
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','community','share','cur-wholesaler','wholesaler','cur-ni','ni']);
  const selected=await get();await shot('selected.png');
  pass('IMS requires Community blank sub-channel. Wholesaler/NI show only selected EF measures. Channel off disables/removes dependents, with valid remembered choices restored on re-enable.');

  await frame.locator('#sb-units').selectOption('value');
  assert.match(await frame.locator('[data-ims="abbott"]').innerText(),/IMS value/);
  assert.match(await frame.locator('[data-ims="market"]').innerText(),/Market value/);
  assert.match(await measure('community').innerText(),/Cur Value/);
  assert.match(await frame.locator('[data-row="cur-wholesaler"] td').first().innerText(),/value/);
  assert.match(await frame.locator('[data-row="cur-wholesaler"]').innerText(),/£/);
  assert.doesNotMatch(await frame.locator('[data-row="share"]').innerText(),/£/);
  assert.equal(await frame.locator('.sb-plot').count(),1);
  assert.equal(await frame.locator('[data-series="share"][data-axis="right"]').count(),2);
  await shot('value.png');
  pass('Units/Value changes IMS/Market/PI/Cur/Pub/ADS labels and formats; Share uses the same graph’s right percentage axis.');

  const affiliate=frame.locator('[data-filter="affiliates"]');await affiliate.locator('button').click();
  assert.equal(await affiliate.locator('input[type="checkbox"]').count(),1);
  await affiliate.locator('input[type="search"]').fill('United');assert.equal(await affiliate.locator('input[type="checkbox"]').count(),1);
  await affiliate.locator('input[type="checkbox"]').uncheck();assert.deepEqual(await rowIds(),[]);
  assert.equal(await frame.locator('#sb-charts svg').count(),0);
  await affiliate.locator('input[type="checkbox"]').check();await affiliate.locator('button').click();
  assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','community','share','cur-wholesaler','wholesaler','cur-ni','ni']);
  const imsSection=catalog.bindings.find(b=>b.id==='market').units.section;
  await set({sections:[imsSection]});assert.deepEqual(await rowIds(),['abbott','market','pi','share']);
  assert.equal(await measure('community').count(),0);
  await set({sections:initial.sections});
  await frame.locator('#sb-scope-search').fill('Juce');
  assert.equal(await frame.locator('[data-sector]').count(),1);assert.deepEqual((await get()).sectors,initial.sectors);
  await frame.locator('#sb-scope-search').fill('');
  pass('Affiliate is a searchable multi-select backed only by the confirmed UK sample; clearing it clears results. Source Section filters measures. Searching drivers does not change selection.');

  await set(initial);await frame.locator('[data-channel="contracts"]').click();assert.deepEqual(await rowIds(),[]);
  assert.equal(await measure('contracts').isDisabled(),true);await frame.locator('[data-target="homecare"]').click();
  await measure('contracts','ads').click();assert.deepEqual(await rowIds(),['homecare']);
  assert.equal(await frame.locator('[data-ims][data-family="contracts"]').count(),0);
  await frame.locator('[data-target="hospital"]').click();assert.deepEqual(await rowIds(),['homecare','hospital']);
  await shot('contracts.png');
  pass('Contracts has only real sub-channels. Channel alone adds nothing; Homecare/Hospital ADS appears only after explicit context and measure selection.');

  await frame.locator('#sb-clear-rows').click();await frame.locator('#sb-row-search').fill('Homecare');await frame.locator('#sb-all-rows').click();
  assert.deepEqual(await rowIds(),['cur-homecare','pub-homecare','homecare']);
  await frame.locator('#sb-row-search').fill('');await frame.locator('#sb-all-rows').click();
  assert.deepEqual((await rowIds()).slice().sort(),ids);
  assert.deepEqual(await rowIds(),catalog.displayOrder);
  await frame.locator('#sb-clear-rows').click();assert.deepEqual(await rowIds(),[]);
  pass('Explicit Select all/Select matches selects only direct source measures; Clear all empties results. Click order never changes bridge context/measure order.');

  const numeric=await frame.evaluate(()=>{
   const a=document.getElementById('fm-sop-source-only-r07').sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];
   for(const display of ['units','value']){
    a.setState({display,sectors:a.sectors.map(s=>s.id)});const g=a.groups()[0];
    for(const prefix of ['','cur-','pub-'])for(const t of [24,31,32,33,35]){
     const v=id=>a.amount(m.get(prefix+id),g,[t],'2026-10');out.push([v('community'),v('wholesaler')+v('ni')]);out.push([v('ads'),a.leaves.reduce((s,id)=>s+v(id),0)]);
    }
    for(const p of ['2026:FY','2026:YTD','2026:YTG']){const months=a.periodMonths(m.get('share'),p,'2026-10'),v=id=>a.amount(m.get(id),g,months,'2026-10');out.push([v('share'),v('abbott')/v('market')]);}
   }
   return out;
  });numeric.forEach(([a,b])=>near(a,b));
  pass(`${numeric.length} comparisons preserve source Community/sector totals and weighted shares in Units and Value without a derived Contracts display row.`);

  const baselinePage=await browser.newPage();await baselinePage.goto(pathToFileURL(path.join(__dirname,'../sop-cascade-r06/index.html')).href);
  const baselineFrame=baselinePage.frames().find(f=>f!==baselinePage.mainFrame());await baselineFrame.waitForSelector('#sb-summary');
  const snapshot=(f,id)=>f.evaluate(({id,ids})=>{const a=document.getElementById(id).sopDesign,m=new Map(a.rows.map(r=>[r.id,r])),out=[];for(const display of ['units','value']){a.setState({display,sectors:['compact','juce'],grouping:'combined'});const g=a.groups()[0];for(const rowId of ids)for(const p of ['2026:FY','2026:YTD','2026:YTG'])out.push(a.amount(m.get(rowId),g,a.periodMonths(m.get(rowId),p,'2026-10'),'2026-10'));}return out;},{id,ids});
  const old=await snapshot(baselineFrame,'fm-sop-cascade-r06'),now=await snapshot(frame,'fm-sop-source-only-r07');
  old.forEach((v,i)=>near(v,now[i]));await baselinePage.close();
  pass(`${old.length} retained direct-source measure/period/dimension values match the preserved R06 fixture exactly.`);

  await set(selected);const before=await get();await set({periods:['2026:FY']});assert.equal((await get()).monthStart,before.monthStart);
  await frame.locator('#sb-start').fill('2026-04');await frame.locator('#sb-start').dispatchEvent('change');assert.deepEqual((await get()).periods,['2026:FY']);
  await frame.locator('[data-table="monthly"]').click();assert.equal(await frame.locator('#sb-summary thead th').count(),11);
  await set(selected);await frame.locator('#sb-panel-toggle').click();assert.deepEqual(await rowIds(),['abbott','market','pi','cur-community','community','share','cur-wholesaler','wholesaler','cur-ni','ni']);
  await frame.locator('#sb-panel-toggle').click();
  pass('Month calendars and summary periods remain independent; Monthly follows calendars. Hiding the selector preserves selections and results.');

  const warm=requests.length;
  for(const width of [1080,736,390,320]){
   await page.setViewportSize({width,height:1500});await page.waitForTimeout(180);
   const overflow=await frame.evaluate(()=>document.documentElement.scrollWidth>document.documentElement.clientWidth+1);assert.equal(overflow,false,`overflow at ${width}`);
   const labels=await frame.locator('.sb-plot svg text').evaluateAll(ns=>ns.filter(n=>n.textContent.trim()).map(n=>{const b=n.getBoundingClientRect(),p=n.ownerSVGElement.getBoundingClientRect();return b.left>=p.left-1&&b.right<=p.right+1;}));assert.ok(labels.every(Boolean),`clipped labels at ${width}`);
  }
  await shot('mobile.png',390);await page.emulateMedia({colorScheme:'dark'});await shot('dark.png');
  await page.emulateMedia({colorScheme:'light'});await page.setViewportSize({width:1080,height:1500});await page.waitForTimeout(180);
  const overlay=frame.locator('[data-chart-hover-overlay="cross-series"]').first();await overlay.hover({position:{x:83,y:75}});
  assert.equal(await frame.locator('[data-chart-hover-guide]').count(),1);assert.equal(await frame.locator('[data-chart-hover-marker]').count(),10);
  assert.deepEqual(errors,[]);assert.equal(requests.length-warm,0);
  pass('Responsive light/dark layouts fit 1080/736/390/320px, with legible chart labels, cross-series hover and zero warm network requests or script errors.');
  const result={schema:'FM_SOP_SOURCE_ONLY_R07_VALIDATION',checkedAt:new Date().toISOString(),checks,numericComparisons:numeric.length,retainedValueComparisons:old.length,sourceBindings:ids.length,errors,warmNetworkRequests:requests.length-warm,note:'Synthetic local browser checks only; no live source binding or Power BI performance qualification.'};
  fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
