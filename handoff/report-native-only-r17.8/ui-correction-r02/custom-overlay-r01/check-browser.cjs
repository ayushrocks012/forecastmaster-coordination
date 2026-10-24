const fs = require('node:fs'), path = require('node:path'), assert = require('node:assert/strict');
const {chromium} = require('C:\\Users\\Ayush\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright');
(async () => {
 const directory = process.argv[2], browser = await chromium.launch({channel:'msedge',headless:true});
 try {
  const page = await browser.newPage({viewport:{width:1450,height:650},timezoneId:'Europe/London'}), errors=[];
  page.on('pageerror',e=>errors.push(String(e)));
  await page.goto('file:///'+path.join(directory,'index.html').replace(/\\/g,'/'));
  const feed=JSON.parse(fs.readFileSync(path.join(directory,'feed.json'),'utf8'));
  await page.evaluate(v=>window.feed=v,feed);
  const dimensions=[[1400,360],[840,300],[560,300],[400,260],[1000,420]],readings=[];
  for(const [width,height] of dimensions){
   const result=await page.evaluate(({width,height})=>{
    const start=performance.now();visual.update({type:2,viewport:{width,height},dataViews:[feed]});
    const paths=[...document.querySelectorAll('path[data-series]')];
    return {width,height,elapsedMs:performance.now()-start,series:paths.length,
     points:paths.reduce((n,p)=>n+Number(p.dataset.points),0),scopes:document.querySelectorAll('.fm-overlay-legend button').length,
     invalid:paths.some(p=>/NaN|Infinity/.test(p.getAttribute('d'))),
     texts:[...document.querySelectorAll('svg text')].map(n=>n.textContent),failures:hostCalls.failed,
     cutoffs:document.querySelectorAll('[data-actuals-cutoff]').length,
     periods:document.querySelectorAll('[data-review-period]').length,
     styles:paths.every(p=>p.dataset.kind==='0'||p.dataset.kind==='1'?!p.getAttribute('stroke-dasharray'):p.getAttribute('stroke-dasharray')==='7 4')};
   },{width,height});
   assert.equal(result.series,450);assert.equal(result.points,18900);assert.equal(result.scopes,150);
   assert.equal(result.invalid,false);assert.deepEqual(result.failures,[]);
   assert(result.texts.includes('Jan 2023'));assert(result.texts.includes('Dec 2029'));
   assert(result.texts.includes('Actuals through Aug 2026'));assert.equal(result.cutoffs,1);assert.equal(result.periods,4);assert(result.styles);readings.push(result);
  }
  await page.locator('.fm-overlay-tools input').fill('Sector 05.30');
  const focused=await page.evaluate(()=>({paths:document.querySelectorAll('path[data-series]').length,
    active:[...document.querySelectorAll('path[data-series]')].filter(p=>p.getAttribute('opacity')==='1').length}));
  assert.equal(focused.paths,450);assert.equal(focused.active,3);
  await page.locator('.fm-overlay-tools input').fill('Driver 05');
  const driverFocus=await page.evaluate(()=>({paths:document.querySelectorAll('path[data-series]').length,
   active:[...document.querySelectorAll('path[data-series]')].filter(p=>p.getAttribute('opacity')==='1').length}));
  assert.equal(driverFocus.paths,450);assert.equal(driverFocus.active,90);
  await page.locator('.fm-overlay-tools input').fill('Sector 05.30');
  const hit=page.locator('rect[role=button]');await hit.focus();await hit.press('ArrowRight');
  assert((await page.locator('.fm-overlay-tooltip').innerText()).includes('Feb 2023'));
  assert((await page.locator('.fm-overlay-tooltip').innerText()).includes('Sector 05.30'));
  await hit.press('Enter');assert((await page.locator('.fm-overlay-tooltip').innerText()).includes('pinned'));await hit.press('Escape');
  const edge=await page.evaluate(()=>{
   const update=v=>visual.update({type:2,viewport:{width:1000,height:360},dataViews:[v]});
   hostCalls.failed=[];const repeat=structuredClone(feed);repeat.table.rows.push(structuredClone(repeat.table.rows[0]));update(repeat);
   const repeatedPoints=[...document.querySelectorAll('path[data-series]')].reduce((s,p)=>s+Number(p.dataset.points),0);
   const conflict=structuredClone(repeat);conflict.table.rows.at(-1)[4]+=1;update(conflict);
   const conflictWithheld=document.querySelectorAll('path[data-series]').length===0&&document.body.textContent.includes('Conflicting');
   hostCalls.failed=[];window.fetchAllowed=true;update({...feed,metadata:{segment:{}},table:{...feed.table,rows:feed.table.rows.slice(0,10000)}});
   const partialWithheld=!document.querySelector('path[data-series]')&&document.body.textContent.includes('Loading the complete');
   window.fetchAllowed=false;update({...feed,metadata:{segment:{}}});
   const refusedWithheld=!document.querySelector('path[data-series]')&&document.body.textContent.includes('Partial lines are withheld');
   window.fetchAllowed=true;hostCalls.failed=[];update({...feed,table:{...feed.table,rows:[]}});
   const emptyBlank=!document.querySelector('path[data-series]')&&document.body.textContent.includes('Select a saved file');
   const row=structuredClone(feed.table.rows[0]);row[4]=0;update({...feed,table:{...feed.table,rows:[row]}});
   const zeroPreserved=document.querySelector('path[data-series]')?.getAttribute('data-points')==='1';
   row[4]=-.2;row[5]=JSON.stringify({...JSON.parse(row[5]),metric:'share',unit:'%'});row[1]='negative';row[2]='<img src=x onerror=alert(1)>';
   update({...feed,table:{...feed.table,rows:[row]}});
   const safeText=!document.querySelector('img')&&document.querySelector('.fm-overlay-count').textContent===row[2];
   const ratio=document.querySelector('svg').textContent.includes('%');
   update(feed);
   const original=[...document.querySelectorAll('path[data-series]')].find(p=>p.dataset.scope==='Sector 05.30 – Driver 05'&&p.dataset.kind==='0').getAttribute('stroke');
   const reduced=structuredClone(feed);reduced.table.rows=reduced.table.rows.filter(r=>r[2]==='Sector 05.30 – Driver 05');update(reduced);
   const stableColor=document.querySelector('path[data-kind="0"]').getAttribute('stroke')===original;
   const actualColor=document.querySelector('path[data-kind="0"]').getAttribute('stroke');
   const forecastColor=document.querySelector('path[data-kind="1"]').getAttribute('stroke');
   const distinctActualForecast=actualColor!==forecastColor;
   const singleScopeCompact=!document.querySelector('.fm-overlay-tools input')&&!document.querySelector('.fm-overlay-legend')
    &&document.querySelector('svg').getAttribute('viewBox')==='0 0 1000 330';
   const mixed=structuredClone(reduced);mixed.table.rows[0][5]=JSON.stringify({...JSON.parse(mixed.table.rows[0][5]),metric:'share',unit:'%'});update(mixed);
   const mixedWithheld=!document.querySelector('path[data-series]')&&document.body.textContent.includes('Mixed measure contexts');
   hostCalls.failed=[];const different=structuredClone(reduced);different.table.rows=different.table.rows.map(r=>{r[5]=JSON.stringify({...JSON.parse(r[5]),cutoff:'2026-09'});return r;});update(different);
   const changedCutoffText=document.querySelector('svg').textContent;
   const changedCutoff=/Actuals through Sept? 2026/.test(changedCutoffText);
   update(feed);
   return {repeatedPoints,conflictWithheld,partialWithheld,refusedWithheld,emptyBlank,zeroPreserved,safeText,ratio,stableColor,distinctActualForecast,singleScopeCompact,mixedWithheld,changedCutoff,fetches:hostCalls.fetch};
  });
  assert.equal(edge.repeatedPoints,18900);for(const key of ['conflictWithheld','partialWithheld','refusedWithheld','emptyBlank','zeroPreserved','safeText','ratio','stableColor','distinctActualForecast','singleScopeCompact','mixedWithheld','changedCutoff'])assert.equal(edge[key],true,key);
  assert.equal(edge.fetches,2);assert.deepEqual(errors,[]);
  await page.screenshot({path:path.join(directory,'complete-overlay.png')});
  const receipt={Stage:'LOCAL_CUSTOM_OVERLAY_BROWSER_VERIFIED',FabricatedOnly:true,Scopes:150,Series:450,Points:18900,
   Readings:readings,FocusedWithoutRemovingData:focused,WholeDriverFocus:driverFocus,Edges:edge,BrowserErrors:errors,DesktopHostAcceptance:false};
  fs.writeFileSync(path.join(directory,'BROWSER-VALIDATION.json'),JSON.stringify(receipt,null,2)+'\n');console.log(JSON.stringify(receipt));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
