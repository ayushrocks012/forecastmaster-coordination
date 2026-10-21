const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || (process.platform === 'win32'
  ? path.join(process.env.USERPROFILE, '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
  : 'playwright'));
const near = (a, b) => assert.ok(Math.abs(a-b) < Math.max(1e-9, Math.abs(a)*1e-10), `${a} != ${b}`);
const hash = data => crypto.createHash('sha256').update(data).digest('hex');

(async () => {
  const browser = await chromium.launch({headless:true, ...(process.platform === 'win32' ? {channel:'msedge'} : {})});
  try {
    const page = await browser.newPage({viewport:{width:1080,height:1200},colorScheme:'light'});
    const errors = [], requests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => requests.push(request.url()));
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
    const frame = page.frames().find(f => f !== page.mainFrame());
    await frame.waitForSelector('.fm-total');
    const get = () => frame.evaluate(() => document.getElementById('fm-executive-gm-review').fmDesign.getState());
    const set = patch => frame.evaluate(p => document.getElementById('fm-executive-gm-review').fmDesign.setState(p), patch);
    const initial = await get();
    const tableNumbers = f => f.locator('#fm-summary [data-value],#fm-summary [data-delta],#fm-summary [data-variance-percent]').evaluateAll(cells => cells.map(c => ({value:c.dataset.value ?? c.dataset.delta ?? c.dataset.variancePercent,text:c.textContent.trim()})));
    const initialTotal = await frame.locator('.fm-total').innerText();

    assert.deepEqual(await frame.locator('#fm-filters [data-filter]').evaluateAll(nodes => nodes.map(n => n.dataset.filter)), ['cycles','periods','channels','subchannels','sections','metrics']);
    assert.equal(await frame.locator('[data-selection-level]').count(),0,'One shared hierarchy has no duplicate selection-layout toolbar');
    const placement = await frame.evaluate(() => document.querySelector('[data-filter="periods"]').compareDocumentPosition(document.getElementById('fm-executive-readout')));
    assert.ok(placement & 4,'Review period is above the executive position');
    assert.equal(initial.tableView,'driver');
    assert.equal(await frame.locator('.fm-hierarchy-child').count(),0);
    assert.equal(await frame.locator('[data-expand-driver]').count(),2);
    assert.equal(await frame.locator('[data-scope-choice]').count(),6);
    assert.equal(initial.monthEnd,'2026-12');
    assert.match(await frame.locator('#fm-data-context').innerText(),/Sample refresh completed/);
    assert.match(await frame.locator('#fm-executive-readout').innerText(),/Offsetting driver movements.*Core Oral: Overcall.*Paed SIP: Undercall/s);
    assert.match(await frame.locator('#fm-summary thead').innerText(),/Δ Units/);

    async function shot(name) {
      await page.waitForTimeout(140);
      const height = await frame.evaluate(() => document.documentElement.scrollHeight);
      await page.locator('iframe').evaluate((element,h) => {element.style.setProperty('height',h+'px','important');element.style.setProperty('max-height','none','important');},height+16);
      await page.setViewportSize({width:1080,height:height+96});
      await page.waitForTimeout(140);
      await page.screenshot({path:path.join(__dirname,name),fullPage:true});
    }
    await shot('overview.png');

    await frame.locator('[data-expand-driver="oral"]').click();
    assert.equal(await frame.locator('.fm-hierarchy-child').count(),2);
    assert.equal(await frame.locator('[data-expand-driver="oral"]').getAttribute('aria-expanded'),'true');
    assert.equal(await frame.locator('.fm-total').innerText(),initialTotal,'Expanding rows changes presentation only');
    await frame.locator('[data-expand-driver="paed"]').click();
    assert.equal(await frame.locator('.fm-hierarchy-child').count(),4);
    await shot('expanded-drivers.png');
    await frame.locator('[data-table-view="sector"]').click();
    assert.equal(await frame.locator('.fm-sector-row').count(),4);
    assert.equal(await frame.locator('.fm-subtotal').count(),0);
    assert.equal(await frame.locator('.fm-tier-parent').count(),4);
    assert.equal(await frame.locator('.fm-total').innerText(),initialTotal);
    await shot('sectors.png');

    await frame.locator('[data-table-view="hierarchy"]').click();
    assert.equal(await frame.locator('.fm-subtotal').count(),2);
    assert.equal(await frame.locator('.fm-hierarchy-child').count(),4);
    await frame.locator('[data-scope-choice="juce"]').uncheck();
    assert.equal(await frame.locator('[data-scope-choice="oral"]').evaluate(e => e.indeterminate),true);
    assert.match(await frame.locator('.fm-total td').first().innerText(),/Selected total/);
    assert.match(await frame.locator('#fm-executive-readout').innerText(),/Selected plan/);
    assert.match(await frame.locator('#fm-chart-title').innerText(),/Selected total/);
    assert.match(await frame.locator('[data-driver-row="oral"]').innerText(),/1 of 2 tiers/);
    const partialNumbers = await tableNumbers(frame);
    await frame.locator('#fm-selection-search').fill('Juce');
    assert.equal(await frame.locator('[data-scope-choice="oral"]').count(),1);
    assert.equal(await frame.locator('[data-scope-choice="paed"]').count(),0);
    assert.deepEqual(await tableNumbers(frame),partialNumbers,'Search finds choices without changing selected data');
    await frame.locator('#fm-selection-search').fill('');
    await frame.locator('#fm-select-scope').click();

    await frame.locator('#fm-compare-periods').click();
    assert.deepEqual((await get()).periods,['2026:FY','2026:YTG']);
    assert.equal(await frame.locator('[data-overview-period]').count(),2);
    assert.equal(await frame.locator('[data-period-group]').count(),2);
    await frame.locator('#fm-rank-period').selectOption('2026:YTG');
    await frame.locator('#fm-rank-window').selectOption('6');
    await frame.locator('#fm-sort-gaps').click();
    assert.equal((await get()).rankPeriod,'2026:YTG');
    assert.match(await frame.locator('#fm-ranking-caption').innerText(),/2026 YTG.*6M trend/);
    assert.equal(await frame.locator('[data-period-group="2026:FY"]').count(),1,'Ranking does not replace the displayed periods');
    const ranked=await frame.locator('#fm-summary tbody tr:not(.fm-total)').evaluateAll(rows=>rows.map(row=>({driver:row.dataset.driverRow,tier:row.dataset.tierRow,gap:Math.abs(Number(row.querySelector('[data-period="2026:YTG"][data-trend-window="6"][data-delta]').dataset.delta))})));
    const parents=ranked.filter(row=>row.driver);assert.ok(parents[0].gap>=parents[1].gap);
    for(let i=0;i<ranked.length;i+=3){assert.ok(ranked[i].driver);assert.ok(ranked[i+1].tier);assert.ok(ranked[i+2].tier);assert.ok(ranked[i+1].gap>=ranked[i+2].gap);}
    await shot('fy-and-ytg.png');
    const frozen = await frame.evaluate(() => {
      const wrap=document.querySelector('.fm-summarywrap'),cell=document.querySelector('.fm-total td');
      const before=cell.getBoundingClientRect().left;wrap.scrollLeft=500;
      return {before,after:cell.getBoundingClientRect().left,scroll:wrap.scrollLeft,position:getComputedStyle(cell).position};
    });
    assert.ok(frozen.scroll>0);assert.equal(frozen.position,'sticky');assert.ok(Math.abs(frozen.before-frozen.after)<1);
    await frame.locator('.fm-summarywrap').evaluate(e => e.scrollLeft=0);

    await set({...initial,periods:['2026:YTG']});
    assert.equal((await get()).monthEnd,'2026-12');
    await set({periods:['2027:FY']});
    assert.equal((await get()).monthEnd,'2027-12');
    await frame.locator('#fm-compare-periods').click();
    assert.ok((await get()).periods.includes('2027:FY'),'Quick comparison retains other periods');
    await set({...initial});
    await frame.locator('.fm-custom-dates summary').click();
    await frame.locator('#fm-month-end').fill('2027-12');
    await frame.locator('#fm-month-end').dispatchEvent('change');
    assert.equal((await get()).chartRangeMode,'custom');
    await set({periods:['2026:YTG']});
    assert.equal((await get()).monthEnd,'2027-12','Custom dates survive period changes');
    await frame.locator('#fm-follow-period').check();
    assert.equal((await get()).monthEnd,'2026-12','Following review restores the matching end date');
    await frame.locator('.fm-custom-dates summary').click();

    await set({...initial,combined:false,view:'hierarchy',tableView:'hierarchy'});
    assert.equal(await frame.locator('.fm-plot').count(),2);
    const selection = (await get()).sectors;
    await frame.locator('[data-table-view="sector"]').click();
    assert.equal((await get()).view,'hierarchy');
    for(const mode of ['total','driver','sector','hierarchy']) {
      await frame.locator(`[data-graph-mode="${mode}"]`).click();
      assert.equal((await get()).tableView,'sector');
      assert.deepEqual((await get()).sectors,selection);
    }
    await frame.locator('[data-table-view="hierarchy"]').click();
    await shot('driver-and-sectors.png');

    const baselinePage=await browser.newPage({viewport:{width:1080,height:1200}});
    baselinePage.on('pageerror',e=>errors.push(e.message));
    await baselinePage.goto(pathToFileURL(path.join(__dirname,'../executive-period-review-r09/index.html')).href);
    const old=baselinePage.frames().find(f=>f!==baselinePage.mainFrame());await old.waitForSelector('.fm-total');
    const scenarios=[
      {name:'all tiers FY',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY'],cycles:['2026-10'],sections:['ims'],metrics:['market-units']}},
      {name:'FY and YTG',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY','2026:YTG'],cycles:['2026-10'],sections:['ims'],metrics:['market-units']}},
      {name:'partial sectors',patch:{tableView:'hierarchy',sectors:['compact','paed-energy'],periods:['2026:FY'],cycles:['2026-10'],sections:['ims'],metrics:['market-units']}},
      {name:'weighted share',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY','2026:YTG'],cycles:['2026-10'],sections:['ims'],metrics:['volume-share']}},
      {name:'value',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY'],cycles:['2026-10'],sections:['ims'],metrics:['market-value']}},
      {name:'multiple cycles and measures',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY','2026:YTG'],cycles:['2026-10','2026-07'],sections:['ims'],metrics:['market-units','volume-share']}},
      {name:'ex-factory cutoff',patch:{tableView:'hierarchy',sectors:initial.sectors,periods:['2026:FY','2026:YTG'],cycles:['2026-10'],sections:['ef'],metrics:['ef-units']}}
    ];
    const parity=[];
    for(const scenario of scenarios) {
      const patch={...scenario.patch,sortGaps:false,tableTrends:[6,12,24],fileMode:'ads'};
      await set(patch);await old.evaluate(p=>document.getElementById('fm-executive-period-review').fmDesign.setState(p),patch);
      const before=await tableNumbers(old),after=await tableNumbers(frame);
      assert.deepEqual(after,before,scenario.name+' retains all raw and formatted numeric cells');
      parity.push({scenario:scenario.name,cells:after.length,sha256:hash(JSON.stringify(after))});
    }
    await set({...initial,metrics:['volume-share']});assert.match(await frame.locator('#fm-summary thead').innerText(),/Δ pp/);
    await set({...initial,metrics:['market-value']});assert.match(await frame.locator('#fm-summary thead').innerText(),/Δ £/);
    await set({...initial});
    const total = await frame.evaluate(() => {
      const api=document.getElementById('fm-executive-gm-review').fmDesign,combo=api.combos()[0],metric=api.catalog.find(m=>m.id==='market-units');
      const months=api.periodMonths('2026:FY',combo,metric),subset=api.activeSectors();
      return {plan:api.amount(combo,subset,metric,months),delta:api.amount(combo,subset,metric,months)-api.amount(combo,subset,metric,months,12)};
    });
    const baselineTotalReceipt=JSON.parse(fs.readFileSync(path.join(__dirname,'../executive-period-review-r09/validation-period-review.json'),'utf8')).compare[0];
    near(total.plan,baselineTotalReceipt.plan);near(total.delta,baselineTotalReceipt.delta);
    await baselinePage.close();

    const dimensions=[];
    for(const width of [1024,736,390,320]) {
      await page.setViewportSize({width,height:1200});await page.waitForTimeout(130);
      const d=await frame.evaluate(()=>({width:document.documentElement.clientWidth,scroll:document.documentElement.scrollWidth,plots:[...document.querySelectorAll('.fm-plot')].map(p=>({width:p.clientWidth,svg:p.querySelector('svg').viewBox.baseVal.width}))}));
      assert.ok(d.scroll<=d.width+1,JSON.stringify(d));for(const plot of d.plots)assert.ok(Math.abs(plot.width-plot.svg)<=1);
      dimensions.push(d);
    }
    await frame.locator('#fm-clear-scope').click();assert.equal(await frame.locator('.fm-total').count(),0);
    await frame.locator('#fm-select-scope').click();assert.equal(await frame.locator('.fm-total').count(),1);
    await page.setViewportSize({width:1080,height:1200});
    await set({...initial,periods:['2026:FY','2026:YTG'],tableView:'hierarchy'});
    await page.emulateMedia({colorScheme:'dark'});await shot('dark.png');
    await page.emulateMedia({colorScheme:'light'});await set({...initial});
    const beforeRequests=requests.length;
    const warm=[];
    for(let i=0;i<20;i++) {
      await set({sectors:i%2?initial.sectors:['compact','juce'],tableView:i%3===0?'sector':'driver'});
      await frame.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
      warm.push(await frame.evaluate(()=>document.getElementById('fm-executive-gm-review').fmDesign.getPerformance().at(-1)));
    }
    assert.equal(requests.length,beforeRequests,'Warm interactions make no file or network requests');
    const sorted=warm.map(x=>x.renderMs).sort((a,b)=>a-b),p95=sorted[Math.ceil(sorted.length*.95)-1];
    assert.ok(p95<200,`Synthetic warm render p95 ${p95}ms exceeds design target`);
    await set({...initial});
    assert.equal(await frame.locator('.fm-variance-track,.fm-variance-bar,.fm-variance-zero').count(),0);
    assert.equal(await frame.locator('table').count(),2,'Only the executive summary and source list remain');
    assert.deepEqual(errors,[]);

    const result={status:'PASS',sourceSha256:hash(fs.readFileSync(path.join(__dirname,'review.fragment.html'))),baseline:'../executive-period-review-r09',checks:[
      'Review period beside cycle and above overview', 'Default chart ends at selected review period',
      'Custom chart dates retained; follow-review restores alignment', 'Offsetting driver movements remain explicit',
      'One shared searchable driver/sector hierarchy', 'Drivers expand without changing scope or totals',
      'Flat sector comparison and Both rows remain available', 'Graph/table presentation choices remain independent',
      'Ranking explicitly selects period and trend window', 'Row names remain frozen during horizontal scrolling',
      'Partial scope is labelled Selected total/Selected plan', 'Variance headings distinguish Units, pounds and percentage points',
      'All raw and formatted values match R09 across seven scenarios', 'ADS policy has a separate regression check',
      'Empty selections remain explicit', 'No variance bars or monthly detail table',
      'Responsive at 1024, 736, 390 and 320 pixels', 'Light and dark screenshots',
      'Warm local interactions make no requests', 'No JavaScript errors'
    ],parity,total,frozen,dimensions,syntheticPerformance:{targetMs:200,samples:warm,renderP95Ms:p95,productionPowerBI:'NOT_MEASURED'}};
    fs.writeFileSync(path.join(__dirname,'validation-gm-review.json'),JSON.stringify(result,null,2)+'\n');
    console.log(JSON.stringify({status:result.status,checks:result.checks,parity,total,dimensions,renderP95Ms:p95},null,2));
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
