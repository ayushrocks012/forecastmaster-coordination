const {chromium}=require('./qa-deps.cjs').tool('playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const root=path.resolve(__dirname,'..'),checks=[],errors=[];
const catalog=JSON.parse(fs.readFileSync(path.join(__dirname,'fixture-catalog.json')));
const html='<!doctype html><meta charset="utf-8"><style>html,body{margin:0;}'+fs.readFileSync(path.join(root,'Visual/style/visual.less'),'utf8')+'</style><div id="fm-review-preview"></div>';
fs.writeFileSync(path.join(__dirname,'harness.html'),html);
(async()=>{
 const browser=await chromium.launch(require('./qa-deps.cjs').browserOptions());
 const page=await browser.newPage({viewport:{width:1450,height:1200}});global.qaPage=page;page.on('pageerror',e=>errors.push(e.message));page.setDefaultTimeout(5000);
 await page.goto('file://'+path.join(__dirname,'harness.html'));await page.addScriptTag({path:path.join(__dirname,'engine.js')});
 await page.evaluate(catalog=>{
  const files=[];for(const cycle of ['2026-07','2026-10'])for(const driver of ['Core Oral','Paed SIP']){const id=cycle+'-'+driver;files.push({id,filename:`UK_${driver}_Bridge_${cycle==='2026-07'?'Jul':'Oct'} 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm`,fullLabel:id+' · Imported 2026-10-19T13:00:00Z · '+id,path:cycle+'/'+id+'.xlsm',affiliate:'UK',cycle,driver,profile:'Ext',ims:cycle==='2026-07'?'2026-05':'2026-08',ef:cycle==='2026-07'?'2026-06':'2026-09'});}
  files.push({...files[0],id:'older-core-july',filename:'UK_Core Oral_Bridge_Jul 26_EF-Jun 26_IMS-May 26_Older.xlsm',fullLabel:'older-core-july · Imported 2026-10-18T13:00:00Z · old',path:'older.xlsm'});
  files.push({...files[0],id:'july-infant',driver:'Infant',filename:'UK_Infant_Bridge_Jul 26_EF-Jun 26_IMS-May 26_ADS.xlsm',fullLabel:'july-infant · Imported 2026-10-19T13:00:00Z · infant',path:'infant.xlsm'});
  window.fixtureFiles=files;window.savedStates=[];
  window.makeFeed=s=>{
   const values=new Map(),months=t=>`${2023+Math.floor(t/12)}-${String(t%12+1).padStart(2,'0')}`;
   const metric=catalog.find(m=>m.id===s.metric),cohort=files.filter(f=>f.affiliate===s.affiliate&&s.cycles.includes(f.cycle)&&s.drivers.includes(f.driver)&&f.profile===s.profile);
   for(const f of cohort)for(let t=0;t<60;t++){
    const base=f.cycle==='2026-10'?(f.driver==='Core Oral'?1000:2000):100,cut=f.cycle==='2026-10'?43:40,market=(base+t)*(t>cut?2:1),share=f.driver==='Core Oral'?.1:.5;
    const channel=metric.cutoffFamily==='EF'?'Out of Pocket':'Community';
    values.set(f.id+'|'+months(t),{parts:[{channel,subchannel:'',sector:'A',n:metric.cutoffFamily==='EF'?(t===45?0:market*3):metric.aggregation==='RATIO'?market*share:market,d:metric.aggregation==='RATIO'?market:null,nm:0,dm:0}]});
   }
   return {files,catalog,bounds:{first:'2023-01',last:'2027-12'},context:{...s,schema:4},dimensions:[{channel:'Community',subchannel:'',sector:'A',metrics:catalog.filter(m=>m.cutoffFamily==='IMS').map(m=>m.id)},{channel:'Out of Pocket',subchannel:'',sector:'A',metrics:catalog.filter(m=>m.cutoffFamily==='EF').map(m=>m.id)}],values};
  };
  const initial={affiliate:'UK',cycles:['2026-07'],drivers:['Core Oral'],profile:'Ext',metric:'ims-market-units'};
  window.app=ReviewEngine.mount(document.getElementById('fm-review-preview'),makeFeed(initial),null,s=>queueMicrotask(()=>app.update(makeFeed(s))),s=>savedStates.push(s));
 },catalog);
 async function stable(){await page.waitForTimeout(60);assert.equal(await page.locator('.fm-loading').getAttribute('hidden'),'');}
 async function check(name,fn){await fn();checks.push(name);}
 await stable();
 await check('Initial saved-source view renders with feed schema 4',async()=>assert.equal((await page.evaluate(()=>app.snapshot())).plans.length,1));
 await page.locator('[data-multi=cycles] summary').click();await page.locator('[data-multi=cycles] input[value="2026-10"]').check();await page.locator('[data-multi=cycles] summary').click();await stable();
 await check('Two cycles are selectable without dropping the first',async()=>assert.deepEqual(await page.evaluate(()=>app.getState().cycles),['2026-07','2026-10']));
 await check('Both saved plans use their own June values and actual/forecast status',async()=>{const s=await page.evaluate(()=>app.snapshot()),m=s.months.find(m=>m.t===41);assert.deepEqual(m.plans.map(p=>p.value),[282,1041]);const row=page.locator('[data-monthly-series="2026-07-Core Oral"] [data-month-index="41"]');assert.equal(await row.getAttribute('data-status'),'F');assert.equal(await page.locator('[data-monthly-series="2026-10-Core Oral"] [data-month-index="41"]').getAttribute('data-status'),'A');});
 await page.locator('[data-multi=drivers] summary').click();await page.locator('[data-multi=drivers] input[value="Paed SIP"]').check();await page.locator('[data-multi=drivers] summary').click();await stable();
 await check('Driver multi-selection produces one total per cycle',async()=>{const s=await page.evaluate(()=>app.snapshot());assert.equal(s.plans.length,2);assert.deepEqual(s.months.find(m=>m.t===41).plans.map(p=>p.value),[564,3082]);});
 await page.locator('.fm-file-query').fill('Older');await page.getByRole('checkbox',{name:/Plot forecast/}).check();await page.waitForTimeout(50);
 await check('Duplicate driver versions visibly block an unsafe total',async()=>assert.match(await page.locator('.fm-loading').textContent(),/Select one version for Core Oral/));
 await page.getByRole('checkbox',{name:/Plot forecast/}).uncheck();await page.locator('.fm-file-query').fill('');await stable();
 await page.locator('.fm-file-query').fill('2026-10-Paed SIP');await page.getByRole('checkbox',{name:/Plot forecast/}).uncheck();await page.waitForTimeout(40);
 await check('Missing selected driver is reported instead of displaying a partial total',async()=>{assert.match(await page.locator('.fm-loading').textContent(),/Select a file for Paed SIP/);assert.equal(await page.evaluate(()=>app.snapshot()),null);});
 await page.getByRole('checkbox',{name:/Plot forecast/}).check();await page.locator('.fm-file-query').fill('');await stable();
 await page.locator('[data-field=channel]').selectOption('Out of Pocket');await stable();
 await check('Out of Pocket changes the unavailable IMS choice to a supported EF measure',async()=>{const s=await page.evaluate(()=>app.getState());assert.equal(s.family,'Ex-Factory');assert.equal(s.metric,'ef-selling-units');assert.match(await page.locator('.fm-availability').textContent(),/Selected Ex-factory Selling Units for/);assert.equal(await page.locator('[data-field=family] option[value="IMS / Market"]').count(),0);});
 await check('Reported zero remains an available metric and displays zero',async()=>{const s=await page.evaluate(()=>app.snapshot());assert.deepEqual(s.months.find(m=>m.t===45).plans.map(p=>p.value),[0,0]);assert.equal(await page.locator('[data-field=metric] option[value="ef-selling-units"]').textContent(),'Ex-factory Selling Units');});
 await page.locator('[data-field=channel]').selectOption('Community');await stable();
 await check('Family availability updates again when the channel changes',async()=>assert.equal(await page.locator('[data-field=family] option[value="Ex-Factory"]').count(),0));
 await page.locator('[data-field=metric]').selectOption('ims-volume-share');await stable();
 await check('Aggregate volume share is market-weighted across drivers',async()=>{const s=await page.evaluate(()=>app.snapshot());const actual=s.months.find(m=>m.t===41).plans[1].value;assert.ok(Math.abs(actual-(1041*.1+2041*.5)/(1041+2041))<1e-12);});
 await check('Each comparison series has its own visible cutoff marker',async()=>assert.equal(await page.locator('[data-source-cutoff]').count(),2));
 await page.screenshot({path:path.join(__dirname,'R04-multi-cycle-driver-preview.png'),fullPage:true});
 await check('Multi-select state is persisted',async()=>{const s=await page.evaluate(()=>savedStates.at(-1));assert.deepEqual(s.cycles,['2026-07','2026-10']);assert.equal(s.drivers.length,2);});
 await page.locator('.fm-file-query').fill('2026-10-Core Oral');await page.getByRole('radio').check();await page.locator('.fm-file-query').fill('');await stable();
 await page.locator('[data-multi=cycles] summary').click();await page.locator('[data-multi=cycles] input[value="2026-07"]').uncheck();await stable();await check('Driver choices cascade to the selected cycle',async()=>assert.equal(await page.locator('[data-multi=drivers] input[value="Infant"]').count(),0));await page.locator('[data-multi=cycles] input[value="2026-07"]').check();await page.locator('[data-multi=cycles] summary').click();await stable();
 await check('Expanding cycle selection preserves an explicit October benchmark Base',async()=>assert.equal(await page.evaluate(()=>app.getState().reference),'2026-10-Core Oral'));
 await page.locator('[data-multi=drivers] summary').click();await page.locator('[data-multi=drivers] input[value="Infant"]').check();await page.locator('[data-multi=drivers] summary').click();await page.waitForTimeout(40);
 await check('A driver with no October file remains visible and prevents an incomplete all-driver total',async()=>{assert.match(await page.locator('.fm-loading').textContent(),/Select a file for Infant \(2026-10\)/);assert.equal(await page.locator('[data-multi=drivers] input[value="Infant"]').count(),1);});
 await page.locator('[data-multi=drivers] summary').click();await page.locator('[data-multi=drivers] input[value="Infant"]').uncheck();await page.locator('[data-multi=drivers] summary').click();await stable();
 await page.evaluate(()=>{
  const source=fixtureFiles.find(f=>f.id==='2026-10-Core Oral');
  for(let i=0;i<100;i++)fixtureFiles.push({...source,id:'edited-core-'+i,fullLabel:'Edited · Imported '+new Date(Date.UTC(2026,9,19,18,i)).toISOString()+' · same file'});
  app.update(makeFeed(app.getState()));
 });await stable();
 await check('One hundred imports of one path still produce one current file card',async()=>assert.equal(await page.locator('.fm-files-count').textContent(),'5 available · 2 comparison series'));
 await check('The plotted file and Base move together to its newest saved data',async()=>{const s=await page.evaluate(()=>app.getState());assert.equal(s.reference,'edited-core-99');assert.ok(s.selected.includes('edited-core-99'));assert.ok(!s.selected.includes('2026-10-Core Oral'));});
 await check('Separately named scenarios remain selectable',async()=>{await page.locator('.fm-file-query').fill('Older');assert.equal(await page.getByRole('checkbox',{name:/Plot forecast/}).count(),1);await page.locator('.fm-file-query').fill('');});
 await check('Selectors contain no unavailable-option labels',async()=>assert.equal(await page.locator('option').filter({hasText:'no data for this selection'}).count(),0));
 await page.locator('[data-file-action=clear]').click();await page.waitForTimeout(70);
 await page.evaluate(()=>{fixtureFiles.push({...fixtureFiles.find(f=>f.id==='edited-core-99'),id:'edited-core-next',fullLabel:'Edited · Imported 2026-10-20T12:00:00Z · same file'});app.update(makeFeed(app.getState()));});await page.waitForTimeout(70);
 await check('A refresh preserves Clear all instead of plotting files again',async()=>assert.deepEqual(await page.evaluate(()=>app.getState().selected),[]));
 await page.locator('[data-file-action=undo]').click();await stable();
 await check('Undo restores the current file and cannot resurrect an obsolete import',async()=>{const s=await page.evaluate(()=>app.getState());assert.ok(s.selected.includes('edited-core-next'));assert.equal(s.reference,'edited-core-next');});
 await page.evaluate(()=>{const s=app.getState(),feed=makeFeed(s);feed.context.schema=3;app.update(feed);});
 await check('An old model feed shows the upgrade instruction immediately',async()=>{assert.match(await page.locator('.fm-loading').textContent(),/Upgrade_Visual_Feed_R04/);assert.equal(await page.evaluate(()=>app.snapshot()),null);});
 assert.deepEqual(errors,[]);await browser.close();
 const result={Status:'PASS',Passed:checks.length,Checks:checks,PageErrors:errors};fs.writeFileSync(path.join(__dirname,'browser-results.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result,null,2));
})().catch(async e=>{if(global.qaPage){fs.writeFileSync(path.join(__dirname,'browser-failure.html'),await global.qaPage.content());await global.qaPage.screenshot({path:path.join(__dirname,'browser-failure.png'),fullPage:true});}fs.writeFileSync(path.join(__dirname,'browser-failure.json'),JSON.stringify({error:e.message,stack:e.stack,checks,errors},null,2));console.error(e);process.exit(1);});
