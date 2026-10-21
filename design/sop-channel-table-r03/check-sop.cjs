const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const {chromium} = require(process.env.PLAYWRIGHT_MODULE || (process.platform === 'win32'
  ? path.join(process.env.USERPROFILE,'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright')
  : 'playwright'));
const near = (a,b) => assert.ok(Math.abs(a-b) < Math.max(1e-8,Math.abs(a)*1e-10), `${a} != ${b}`);

(async () => {
  const browser = await chromium.launch({headless:true,...(process.platform==='win32'?{channel:'msedge'}:{})});
  try {
    const page = await browser.newPage({viewport:{width:1080,height:1400},colorScheme:'light'});
    const errors=[], requests=[], checks=[];
    page.on('pageerror', e=>errors.push(e.message));
    page.on('request', r=>requests.push(r.url()));
    await page.goto(pathToFileURL(path.join(__dirname,'index.html')).href);
    const frame=page.frames().find(f=>f!==page.mainFrame());
    await frame.waitForSelector('#sb-summary [data-row]');
    const get=()=>frame.evaluate(()=>document.getElementById('fm-sop-channel-table-r03').sopDesign.getState());
    const set=patch=>frame.evaluate(p=>document.getElementById('fm-sop-channel-table-r03').sopDesign.setState(p),patch);
    const rowIds=()=>frame.locator('#sb-summary [data-row]').evaluateAll(nodes=>nodes.map(n=>n.dataset.row));
    const initial=await get();
    const pass=text=>checks.push(text);
    async function shot(name,width=1080) {
      await page.setViewportSize({width,height:1400});
      await page.waitForTimeout(150);
      const height=await frame.evaluate(()=>document.documentElement.scrollHeight);
      await page.locator('iframe').evaluate((el,h)=>{el.style.setProperty('height',h+'px','important');el.style.setProperty('max-height','none','important');},height+16);
      await page.setViewportSize({width,height:height+96});
      await page.waitForTimeout(150);
      await page.screenshot({path:path.join(__dirname,name),fullPage:true});
    }
    assert.deepEqual(await rowIds(),['market','abbott','community']);
    assert.equal(await frame.locator('[data-series="market"]').count(),2);
    await shot('overview.png');
    pass('Useful default: Community Market, Abbott and Ex-factory ADS share the graph and table.');

    const initialNumbers=await frame.locator('#sb-summary [data-value]').evaluateAll(nodes=>nodes.map(n=>n.dataset.value));
    const placement=await frame.evaluate(()=>{
      const panel=document.getElementById('sb-channel-panel').getBoundingClientRect(),plot=document.querySelector('.sb-content').getBoundingClientRect(),filters=document.getElementById('sb-filters').getBoundingClientRect(),scope=document.getElementById('sb-scope').getBoundingClientRect();
      return {left:panel.left,right:panel.right,plotLeft:plot.left,top:panel.top,filterBottom:filters.bottom,scopeBottom:scope.bottom,position:getComputedStyle(document.getElementById('sb-channel-panel')).position};
    });
    assert.ok(placement.right<placement.plotLeft);
    assert.ok(placement.filterBottom<placement.top&&placement.scopeBottom<placement.top);
    assert.equal(placement.position,'sticky');
    assert.equal(await frame.locator('[data-filter="channels"]').count(),0,'The sidebar is the only channel selector');
    assert.equal(await frame.locator('#sb-filters [data-filter="periods"]').count(),1);
    assert.deepEqual(await frame.locator('.sb-choice-table thead th').allTextContents(),['Channel','Subchannel']);
    assert.equal(await frame.locator('.sb-choice-table [data-measure]').count(),21);
    assert.equal(await frame.locator('.sb-channel-column [data-measure="community"]').count(),1);
    assert.equal(await frame.locator('.sb-subchannel-column [data-measure="wholesaler"]').count(),1);
    assert.equal(await frame.locator('.sb-subchannel-column [data-measure="homecare"]').count(),1);
    assert.ok(await frame.locator('.sb-channel-column [data-measure="community"]').boundingBox());
    assert.equal(await frame.locator('[data-chart]').count(),0);
    await frame.locator('#sb-panel-toggle').click();
    assert.equal(await frame.locator('#sb-channel-panel').isVisible(),false);
    assert.equal(await frame.locator('#sb-panel-toggle').getAttribute('aria-expanded'),'false');
    assert.deepEqual(await frame.locator('#sb-summary [data-value]').evaluateAll(nodes=>nodes.map(n=>n.dataset.value)),initialNumbers);
    await shot('selector-hidden.png');
    await frame.locator('#sb-panel-toggle').click();
    assert.equal(await frame.locator('#sb-channel-panel').isVisible(),true);
    pass('Desktop selector sits on the left below periods and scope; hiding it preserves the data and expands the review.');
    await frame.locator('#sb-clear-rows').click();
    await frame.locator('[data-measure="market"]').click();
    assert.deepEqual(await rowIds(),['market']);
    assert.equal(await frame.locator('[data-series="abbott"]').count(),0);
    await frame.locator('[data-measure="abbott"]').click();
    await frame.locator('[data-measure="wholesaler"]').click();
    assert.deepEqual(await rowIds(),['market','abbott','wholesaler']);
    assert.equal(await frame.locator('[data-context="community"]').count(),1);
    assert.equal(await frame.locator('tr.sb-child[data-row="wholesaler"]').count(),1);
    assert.equal(await frame.locator('[data-series="community"]').count(),0);
    await frame.locator('[data-measure="community"]').click();
    assert.equal(await frame.locator('[data-context="community"]').count(),0);
    assert.deepEqual(await rowIds(),['market','abbott','community','wholesaler']);
    await frame.locator('[data-toggle-row="market"]').click();
    assert.deepEqual(await rowIds(),['abbott','community','wholesaler']);
    assert.equal(await frame.locator('[data-measure="market"]').getAttribute('aria-pressed'),'false');
    await frame.locator('[data-measure="wholesaler"]').focus();
    await page.keyboard.press('Space');
    assert.equal(await frame.locator('[data-measure="wholesaler"]').getAttribute('aria-pressed'),'false');
    assert.ok(!(await rowIds()).includes('wholesaler'));
    await page.keyboard.press('Space');
    assert.equal(await frame.locator('[data-measure="wholesaler"]').getAttribute('aria-pressed'),'true');
    pass('One click on/off and keyboard Space keep buttons, plotted lines and table rows synchronized without selecting children automatically.');

    await set({...initial,rows:['market','share','abbott','pi','net','factor','community','wholesaler','ni']});
    assert.equal(await frame.locator('.sb-plot[data-kind="ratio"]').count(),1);
    assert.equal(await frame.locator('.sb-plot[data-kind="amount"]').count(),1);
    await frame.locator('#sb-units').selectOption('value');
    assert.match(await frame.locator('#sb-summary').innerText(),/£/);
    assert.match(await frame.locator('.sb-plot[data-kind="amount"] .axis-title[data-axis="y"]').textContent(),/GBP/);
    assert.match(await frame.locator('[data-row="share"]').innerText(),/%/);
    assert.doesNotMatch(await frame.locator('[data-row="share"]').innerText(),/£/);
    await shot('community-value.png');
    pass('Value updates amount charts and table together; share/factor retain a separate percentage graph.');

    const invariants=await frame.evaluate(()=>{
      const a=document.getElementById('fm-sop-channel-table-r03').sopDesign;
      const result=[], map=new Map(a.rows.map(r=>[r.id,r]));
      for(const display of ['units','value']){
        a.setState({display,sectors:a.sectors.map(s=>s.id),grouping:'combined',channels:['community','contracts','retail','unassigned']});
        const group=a.groups()[0];
        for(const t of [24,31,32,33,35]){
          const v=id=>a.amount(map.get(id),group,[t],'2026-10');
          result.push([v('community'),v('wholesaler')+v('ni')]);
          result.push([v('contracts'),a.contractLeaves.reduce((n,id)=>n+v(id),0)]);
          result.push([v('ads'),a.leaves.reduce((n,id)=>n+v(id),0)]);
          result.push([v('net'),v('abbott')-v('pi')]);
        }
        for(const id of ['2026:FY','2026:YTD','2026:YTG']){
          const months=a.periodMonths(map.get('share'),id,'2026-10');
          const amount=row=>a.amount(map.get(row),group,months,'2026-10');
          result.push([amount('share'),amount('abbott')/amount('market')]);
          result.push([amount('factor'),(amount('community-ims')-amount('net'))/amount('net')]);
          const fy=a.amount(map.get('ads'),group,a.periodMonths(map.get('ads'),'2026:FY','2026-10'),'2026-10');
          const ytd=a.amount(map.get('ads'),group,a.periodMonths(map.get('ads'),'2026:YTD','2026-10'),'2026-10');
          const ytg=a.amount(map.get('ads'),group,a.periodMonths(map.get('ads'),'2026:YTG','2026-10'),'2026-10');
          result.push([fy,ytd+ytg]);
        }
      }
      const ims=a.periodMonths(map.get('market'),'2026:YTD','2026-10');
      const ef=a.periodMonths(map.get('community'),'2026:YTD','2026-10');
      return {result,ims,ef,blank:a.sum([1,null]),zero:a.sum([0,0]),ratio:a.ratio(4,0),outside:a.source(a.sectors[0],80,'2026-10')};
    });
    invariants.result.forEach(([a,b])=>near(a,b));
    assert.equal(invariants.ims.length,8);assert.equal(invariants.ef.length,9);
    assert.equal(invariants.blank,null);assert.equal(invariants.zero,0);assert.equal(invariants.ratio,null);assert.equal(invariants.outside,null);
    pass(`${invariants.result.length} reconciliation comparisons: Community split, seven Contracts channels, eleven ADS leaves, net IMS, weighted percentages and FY=YTD+YTG; blanks/zero preserved.`);

    await set({...initial,channels:['community','contracts'],rows:[],search:'contracts'});
    const shown=await frame.locator('[data-measure]').evaluateAll(nodes=>nodes.map(n=>n.dataset.measure));
    await frame.locator('#sb-all-rows').click();
    assert.deepEqual((await get()).rows,shown);
    assert.equal(shown.length,8);
    await set({search:'',rows:['community','wholesaler','ni','contracts','homecare','hospital','ads']});
    assert.equal(await frame.locator('tr.sb-child').count(),4);
    await set({chart:'build'});
    assert.equal((await get()).chart,'lines','Legacy bar-mode state cannot restore bars');
    const composition=await frame.evaluate(()=>{
      const a=document.getElementById('fm-sop-channel-table-r03').sopDesign;
      return a.buildComponents().map(c=>({id:c.id,label:c.label,assigned:c.assigned}));
    });
    const assigned=composition.flatMap(c=>c.assigned);
    assert.equal(assigned.length,11);assert.equal(new Set(assigned).size,11);
    assert.deepEqual(composition.find(c=>c.id==='contracts').assigned,['hcl','competitor','nursing','private','internal']);
    assert.match(composition.find(c=>c.id==='contracts').label,/remaining/);
    assert.deepEqual(composition.find(c=>c.id==='ads').assigned,['retail','unassigned']);
    assert.doesNotMatch(await frame.locator('[data-toggle-row="contracts"]').innerText(),/remaining/);
    assert.equal(await frame.locator('[data-toggle-row="community"]').count(),1);
    assert.equal(await frame.locator('[data-stack-component]').count(),0);
    assert.equal(await frame.locator('[data-series]').count(),14);
    assert.ok((await frame.locator('[data-series]').evaluateAll(nodes=>nodes.map(n=>+n.getAttribute('stroke-width')))).every(width=>width===1.8));
    await shot('channel-lines.png');
    await set({rows:[],search:'Wholesaler'});
    assert.equal(await frame.locator('[data-measure="community"]').count(),1,'Search retains the parent context');
    await frame.locator('#sb-all-rows').click();
    assert.deepEqual((await get()).rows,['wholesaler'],'Select matches does not add a context-only parent');
    assert.equal(await frame.locator('[data-context="community"]').count(),1);
    await set({search:''});
    pass('Two-column channel/subchannel buttons retain parent context; search selects matches only; lean lines show full parent and child values, with no bar mode.');

    await set({...initial,channels:['community','contracts'],rows:['market','abbott','community','wholesaler','ni','contracts','homecare','hospital'],sectors:['compact','juce','paed-standard','paed-energy'],grouping:'driver'});
    assert.equal(await frame.locator('[data-row="market"]').count(),2);
    assert.equal(await frame.locator('.sb-plot[data-kind="amount"]').count(),2);
    const driverTotals=await frame.locator('[data-row="community"] [data-column="2026:FY"]').evaluateAll(nodes=>nodes.map(n=>+n.dataset.value));
    await frame.locator('#sb-grouping').selectOption('combined');
    const combined=+await frame.locator('[data-row="community"] [data-column="2026:FY"]').getAttribute('data-value');
    near(combined,driverTotals.reduce((a,b)=>a+b,0));
    await frame.locator('#sb-grouping').selectOption('sector');
    assert.equal(await frame.locator('[data-row="community"]').count(),4);
    const sectorTotals=await frame.locator('[data-row="community"] [data-column="2026:FY"]').evaluateAll(nodes=>nodes.map(n=>+n.dataset.value));
    near(combined,sectorTotals.reduce((a,b)=>a+b,0));
    await set({cycles:['2026-10','2026-07'],sectors:['compact']});
    assert.equal(await frame.locator('[data-row="community"]').count(),2);
    assert.equal(await frame.locator('.sb-plot[data-kind="amount"]').count(),2);
    pass('Combined, driver and sector scope totals agree; multiple cycles remain separately labelled.');

    await set({...initial,rows:['market','community','wholesaler','ni']});
    const before=await frame.locator('#sb-summary [data-value]').evaluateAll(nodes=>nodes.map(n=>n.dataset.value));
    await frame.locator('#sb-start').fill('2026-03');await frame.locator('#sb-start').dispatchEvent('change');
    await frame.locator('#sb-end').fill('2026-11');await frame.locator('#sb-end').dispatchEvent('change');
    assert.deepEqual(await frame.locator('#sb-summary [data-value]').evaluateAll(nodes=>nodes.map(n=>n.dataset.value)),before);
    await frame.locator('[data-table="monthly"]').click();
    assert.equal(await frame.locator('#sb-summary thead th').count(),11);
    assert.equal(await frame.locator('#sb-filters [data-filter="periods"]').isVisible(),true);
    assert.match(await frame.locator('#sb-summary thead').innerText(),/Mar 26.*Nov 26/s);
    await shot('monthly.png');
    await frame.locator('[data-table="periods"]').click();
    assert.deepEqual((await get()).periods,initial.periods);
    assert.equal((await get()).monthStart,'2026-03');
    pass('Calendar changes preserve FY/YTD/YTG totals; Monthly follows the visible calendars and leaves summary choices intact.');

    await set({...initial,rows:['market','abbott','community']});
    const overlay=frame.locator('[data-chart-hover-overlay]').first();
    await overlay.evaluate(el=>{const r=el.getBoundingClientRect();el.dispatchEvent(new PointerEvent('pointermove',{clientX:r.left+r.width*.437,clientY:r.top+r.height*.4,bubbles:true}));});
    assert.equal(await frame.locator('[data-chart-hover-marker]').count(),3);
    assert.equal(await frame.locator('[role="tooltip"]:visible').count(),1);
    await overlay.dispatchEvent('pointerleave');
    assert.equal(await frame.locator('[role="tooltip"]:visible').count(),0);
    await overlay.evaluate(el=>{const r=el.getBoundingClientRect();el.dispatchEvent(new PointerEvent('pointerdown',{clientX:r.left+r.width*.6,clientY:r.top+r.height*.4,bubbles:true,pointerType:'touch'}));});
    await overlay.dispatchEvent('pointerleave');
    assert.equal(await frame.locator('[role="tooltip"]:visible').count(),1);
    pass('Cross-series hover markers and touch-pinned details work.');

    const responsive=[];
    for(const width of [1080,736,390,320]){
      await page.setViewportSize({width,height:1500});await page.waitForTimeout(180);
      const layout=await frame.evaluate(()=>{
        const root=document.getElementById('fm-sop-channel-table-r03');
        const over=root.scrollWidth-root.clientWidth;
        const labels=[...root.querySelectorAll('.sb-plot svg text')].map(n=>{const b=n.getBoundingClientRect(),s=n.ownerSVGElement.getBoundingClientRect();return {left:b.left-s.left,right:b.right-s.right,size:parseFloat(getComputedStyle(n).fontSize)};});
        const splitWords=[...root.querySelectorAll('.sb-choice-table [data-measure]')].filter(button=>{const n=button.children[1]?.firstChild;if(!n||n.nodeType!==3||/\s/.test(n.textContent))return false;const range=document.createRange();range.selectNodeContents(n);return range.getClientRects().length>1;}).map(button=>button.dataset.measure);
        return {over,labels,viewport:innerWidth,splitWords};
      });
      assert.ok(layout.over<=1,`page overflow ${width}: ${layout.over}`);
      assert.deepEqual(layout.splitWords,[],`Single-word channel labels should remain intact at ${width}`);
      layout.labels.forEach(l=>{assert.ok(l.left>=-1,`label left ${width}: ${l.left}`);assert.ok(l.right<=1,`label right ${width}: ${l.right}`);assert.ok(l.size>=11);});
      responsive.push({width,innerWidth:layout.viewport,overflow:layout.over});
    }
    await shot('mobile.png',390);
    await page.emulateMedia({colorScheme:'dark'});await shot('dark.png');
    await page.emulateMedia({colorScheme:'light'});
    await set({rows:[]});assert.equal(await frame.locator('#sb-summary [data-row]').count(),0);
    assert.equal(await frame.locator('.sb-plot').count(),0);
    await set({rows:initial.rows,sectors:[]});assert.equal(await frame.locator('.sb-plot').count(),0);
    await set({...initial});
    const warmStart=requests.length;
    for(let i=0;i<12;i++)await set({display:i%2?'units':'value',rows:i%2?['market','abbott','community']:['community','wholesaler','ni']});
    const timings=await frame.evaluate(()=>document.getElementById('fm-sop-channel-table-r03').sopDesign.getTimings().slice(-12));
    assert.equal(requests.length,warmStart);assert.deepEqual(errors,[]);
    pass('Responsive/light-dark rendering, empty selections and warm local interactions pass without JavaScript errors or network requests.');
    const oldPage=await browser.newPage({viewport:{width:1080,height:1400}});
    oldPage.on('pageerror',e=>errors.push(e.message));
    await oldPage.goto(pathToFileURL(path.join(__dirname,'../sop-build-up-r01/index.html')).href);
    const oldFrame=oldPage.frames().find(f=>f!==oldPage.mainFrame());
    await oldFrame.waitForSelector('#sb-summary [data-row]');
    const allRows=await frame.evaluate(()=>document.getElementById('fm-sop-channel-table-r03').sopDesign.rows.map(r=>r.id));
    const scenarios=[initial,{...initial,display:'value',rows:allRows},{...initial,cycles:['2026-10','2026-07'],grouping:'driver',sectors:['compact','juce','paed-standard','paed-energy'],rows:['community','contracts','homecare','hospital','ads']},{...initial,grouping:'sector',sectors:['compact','juce','paed-standard','paed-energy'],periods:['2026:FY','2026:YTG'],rows:['market','share','abbott','pi','factor','community','wholesaler','ni']},{...initial,table:'monthly',monthStart:'2026-03',monthEnd:'2026-11',rows:allRows}];
    const numericSnapshot=f=>f.locator('#sb-summary [data-value]').evaluateAll(nodes=>nodes.map(n=>({row:n.parentElement.dataset.row,group:n.parentElement.dataset.group,cycle:n.parentElement.dataset.cycle,column:n.dataset.column,value:n.dataset.value,text:n.textContent})).sort((a,b)=>JSON.stringify(a).localeCompare(JSON.stringify(b))));
    let parityCells=0;
    for(const scenario of scenarios){
      await set(scenario);
      await oldFrame.evaluate(p=>document.getElementById('fm-sop-build-up').sopDesign.setState(p),scenario);
      const before=await numericSnapshot(oldFrame),after=await numericSnapshot(frame);
      assert.deepEqual(after,before,'Layout change retains every raw and displayed amount');parityCells+=before.length;
    }
    await oldPage.close();assert.deepEqual(errors,[]);
    pass(`${parityCells} raw/formatted cells match the preserved R01 design across five scope, cycle, unit and table scenarios.`);
    fs.writeFileSync(path.join(__dirname,'validation.json'),JSON.stringify({scope:'Synthetic HTML-only design; no company runtime or Power BI speed assertion',checks,responsive,invariantComparisons:invariants.result.length,parity:{scenarios:scenarios.length,cells:parityCells},errors,externalRequests:requests.filter(u=>/^https?:/.test(u)),warm:{count:timings.length,meanMs:timings.reduce((a,b)=>a+b,0)/timings.length,maxMs:Math.max(...timings),networkRequests:requests.length-warmStart}},null,2)+'\n');
    console.log(JSON.stringify({checks:checks.length,invariants:invariants.result.length,parityCells,responsive,errors,warmMaxMs:Math.max(...timings)}));
  } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
