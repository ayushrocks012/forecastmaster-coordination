const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {pathToFileURL}=require('node:url');
const close=(a,b,label)=>assert.ok(Math.abs(a-b)<Math.max(1e-8,Math.abs(a)*1e-10),`${label}: ${a} vs ${b}`);
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1080,height:1200},colorScheme:'light'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
 const frame=page.frames().find(f=>f!==page.mainFrame());
 await frame.waitForSelector('.fm-total');
 const get=()=>frame.evaluate(()=>document.getElementById('fm-hierarchy-review').fmDesign.getState());
 const set=patch=>frame.evaluate(p=>document.getElementById('fm-hierarchy-review').fmDesign.setState(p),patch);
 const totals=()=>frame.locator('.fm-total').first().evaluate(row=>[...row.querySelectorAll('[data-value],[data-delta],[data-variance-percent]')].map(c=>c.dataset.value??c.dataset.delta??c.dataset.variancePercent));
 const baseline=await get(),baselineTotals=await totals();
 assert.equal(baseline.selectionLevel,'hierarchy');assert.equal(baseline.tableView,'hierarchy');
 assert.equal(await frame.locator('[data-scope-choice]').count(),6);
 assert.equal(await frame.locator('.fm-subtotal').count(),2);
 assert.equal(await frame.locator('.fm-hierarchy-child').count(),4);
 const order=await frame.locator('.fm-summary tbody tr').evaluateAll(rows=>rows.map(r=>r.dataset.driverRow||r.dataset.tierRow||'total'));
 assert.deepEqual(order,['total','oral','compact','juce','paed','paed-standard','paed-energy']);
 const indent=await frame.evaluate(()=>{const left=selector=>parseFloat(getComputedStyle(document.querySelector(selector+' td')).paddingLeft);return left('[data-tier-row="compact"]')-left('[data-driver-row="oral"]');});assert.ok(indent>=15,'Child tiers are visibly indented under their driver');
 const arithmetic=await frame.evaluate(()=>{
  const value=(selector,attribute)=>Number(document.querySelector(selector).getAttribute(attribute));
  const result={};
  for(const attribute of ['data-value','data-delta']){
   const cell=attribute==='data-value'?'[data-value]':'[data-trend-window="12"][data-delta]';
   result[attribute]={total:value('.fm-total '+cell,attribute),parents:['oral','paed'].map(id=>value(`[data-driver-row="${id}"] ${cell}`,attribute)),children:[['compact','juce'],['paed-standard','paed-energy']].map(ids=>ids.map(id=>value(`[data-tier-row="${id}"] ${cell}`,attribute)))};
  }
  return result;
 });
 for(const [label,v]of Object.entries(arithmetic)){close(v.total,v.parents.reduce((a,b)=>a+b,0),label+' grand total');v.parents.forEach((p,i)=>close(p,v.children[i].reduce((a,b)=>a+b,0),label+' subtotal'));}
 await page.screenshot({path:path.join(__dirname,'overview.png'),fullPage:true});
 await frame.locator('[data-scope-choice="juce"]').uncheck();
 assert.equal(await frame.locator('[data-scope-choice="oral"]').evaluate(e=>e.indeterminate),true);
 assert.equal(await frame.locator('[data-scope-choice="compact"]').isChecked(),true);
 assert.deepEqual((await get()).sectors,['compact','paed-standard','paed-energy']);
 assert.match(await frame.locator('[data-driver-row="oral"]').innerText(),/1 of 2 tiers/);
 assert.equal(await frame.locator('[data-tier-row="juce"]').count(),0);
 const partial=await get();
 for(const mode of ['driver','sector','hierarchy']){await frame.locator(`[data-selection-level="${mode}"]`).click();assert.deepEqual((await get()).sectors,partial.sectors);}
 await frame.locator('[data-scope-choice="oral"]').check();
 assert.equal(await frame.locator('[data-scope-choice="juce"]').isChecked(),true);
 await frame.locator('[data-scope-choice="paed"]').uncheck();
 assert.deepEqual((await get()).sectors.slice().sort(),['compact','juce']);
 assert.equal(await frame.locator('[data-scope-choice="paed-standard"]').isChecked(),false);
 assert.equal(await frame.locator('[data-scope-choice="paed-energy"]').isChecked(),false);
 await frame.locator('#fm-select-scope').click();
 for(const mode of ['driver','sector','hierarchy']){await frame.locator(`[data-table-view="${mode}"]`).click();assert.deepEqual(await totals(),baselineTotals);assert.equal((await get()).combined,true);}
 await frame.locator('[data-graph-mode="hierarchy"]').click();
 assert.equal(await frame.locator('.fm-plot').count(),2);
 assert.equal(await frame.locator('.fm-plot[data-driver="oral"] [data-kind="actual"]').count(),3);
 assert.equal(await frame.locator('.fm-plot[data-driver="paed"] [data-kind="actual"]').count(),3);
 const graph=await frame.evaluate(()=>{
  const api=document.getElementById('fm-hierarchy-review').fmDesign,metric=api.catalog.find(m=>m.id==='market-units');
  return ['oral','paed'].map(driver=>{const data=api.chartSeries(metric,driver);return {driver,series:data.series};});
 });
 for(const {driver,series}of graph)for(const kind of ['actual','forecast','trend']){
  const parent=series.find(s=>s.id.includes('|'+driver+'|')&&s.kind===kind);
  const children=series.filter(s=>!s.id.includes('|'+driver+'|')&&s.kind===kind);
  assert.equal(children.length,2);
  for(let i=0;i<parent.points.length;i++)if(parent.points[i].y!==null)close(parent.points[i].y,children.reduce((n,c)=>n+c.points[i].y,0),driver+' '+kind+' sum');
 }
 assert.deepEqual(await totals(),baselineTotals);
 await page.screenshot({path:path.join(__dirname,'both-views.png'),fullPage:true});
 await frame.locator('[data-table-view="sector"]').click();
 assert.equal((await get()).view,'hierarchy');
 for(const mode of ['total','driver','sector','hierarchy']){await frame.locator(`[data-graph-mode="${mode}"]`).click();assert.equal((await get()).tableView,'sector');assert.deepEqual(await totals(),baselineTotals);}
 await frame.locator('[data-table-view="hierarchy"]').click();
 await frame.locator('#fm-sort-gaps').click();
 const sorted=await frame.locator('.fm-summary tbody tr').evaluateAll(rows=>rows.slice(1).map(r=>({driver:r.dataset.driverRow,tier:r.dataset.tierRow})));
 for(let i=0;i<sorted.length;i+=3){assert.ok(sorted[i].driver);assert.ok(sorted[i+1].tier);assert.ok(sorted[i+2].tier);}
 assert.deepEqual(await totals(),baselineTotals);
 await frame.locator('#fm-selection-search').fill('Juce');
 assert.equal(await frame.locator('[data-scope-choice="oral"]').count(),1);
 assert.equal(await frame.locator('[data-scope-choice="juce"]').count(),1);
 assert.equal(await frame.locator('[data-scope-choice="paed"]').count(),0);
 assert.deepEqual(await totals(),baselineTotals,'Search choices does not filter data');
 await frame.locator('#fm-selection-search').fill('');
 await set({periods:['2026:FY','2026:YTG']});
 assert.equal(await frame.locator('[data-period-group]').count(),2);
 assert.equal(await frame.locator('.fm-hierarchy-child').count(),4);
 await set({metrics:['volume-share'],periods:['2026:FY']});
 const ratio=await frame.evaluate(()=>{
  const api=document.getElementById('fm-hierarchy-review').fmDesign,combo=api.combos()[0],subset=api.activeSectors(),months=Array.from({length:12},(_,i)=>24+i);
  const metric=id=>api.catalog.find(m=>m.id===id);
  return {table:Number(document.querySelector('.fm-total [data-value]').dataset.value),ratio:api.amount(combo,subset,metric('abbott-units'),months)/api.amount(combo,subset,metric('market-units'),months)};
 });close(ratio.table,ratio.ratio,'Share totals use weighted ratio');
 await set({...baseline,view:'hierarchy',combined:false});
 const dimensions=[];
 for(const width of [1024,736,390,320]){await page.setViewportSize({width,height:1200});await page.waitForTimeout(120);const d=await frame.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,plots:[...document.querySelectorAll('.fm-plot')].map(p=>({width:p.clientWidth,svg:p.querySelector('svg').viewBox.baseVal.width}))}));assert.ok(d.scroll<=d.width+1,JSON.stringify(d));for(const p of d.plots)assert.ok(Math.abs(p.svg-p.width)<=1);dimensions.push(d);}
 await frame.locator('#fm-clear-scope').click();assert.equal(await frame.locator('.fm-total').count(),0);assert.match(await frame.locator('#fm-plots').innerText(),/Select at least/);
 await frame.locator('#fm-select-scope').click();assert.equal(await frame.locator('.fm-total').count(),1);
 await page.setViewportSize({width:1080,height:1200});await page.emulateMedia({colorScheme:'dark'});await page.waitForTimeout(120);await page.screenshot({path:path.join(__dirname,'both-dark.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 const result={status:'PASS',checks:['Both selector shows parent and child checkboxes simultaneously','Driver selection selects all its tiers','Partial parent checkbox and subtotal are explicit','Switching selection level preserves scope','Table includes total, driver subtotals and child tiers','Subtotals and grand total avoid double counting','Variance subtotals reconcile','Table layout changes preserve totals','Both graph shows per-driver total and tiers simultaneously','Monthly actual, forecast and trend reconcile across levels','Graph and table grouping remain independent','Largest gaps retains parent-child grouping','Search does not change data selection','FY and YTG expand columns','Share totals recompute a weighted ratio','Clear all produces an empty state','Responsive Both mode','No JavaScript errors'],rowOrder:order,arithmetic,ratio,dimensions};
 fs.writeFileSync(path.join(__dirname,'validation-hierarchy.json'),JSON.stringify(result,null,2)+'\n');
 console.log(JSON.stringify(result,null,2));await browser.close();
})().catch(error=>{console.error(error);process.exit(1);});
