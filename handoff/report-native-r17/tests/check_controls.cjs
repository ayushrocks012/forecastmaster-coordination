const fs=require('fs'),path=require('path'),assert=require('assert');
const runtime=process.env.FM_PLAYWRIGHT || 'C:\\Users\\Ayush\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright';
const {chromium}=require(runtime);
(async()=>{
 const root=process.argv[2],browser=await chromium.launch({channel:'msedge',headless:true});
 try {const page=await browser.newPage({viewport:{width:1100,height:1400}});page.setDefaultTimeout(8000);const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('file:///'+path.join(root,'controls.html').replace(/\\/g,'/'));
 const view=JSON.parse(fs.readFileSync(path.join(root,'controls-view.json'),'utf8'));
 await page.evaluate(v=>{window.testView=v;visual.update({dataViews:[v],jsonFilters:[],type:2});},view);
 const host=page.locator('#host');let checks=0;
 await host.getByRole('button',{name:'Community',exact:true}).click();checks++;
 let values=await page.evaluate(()=>calls.filters.at(-1).values);assert(!values.some(t=>t.startsWith('row:')),'Channel must not select descendants');checks++;
 await host.locator('button:not([disabled])').filter({hasText:/^—$/}).click();
 await host.getByRole('button',{name:'Market units',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);
 assert(values.some(t=>t.startsWith('row:market:Units:'))&&values.some(t=>t.startsWith('row:market:Value:')),'Units/Value must share the selection');checks++;
 await host.getByRole('button',{name:'Wholesaler',exact:true}).click();
 await host.locator('.context').filter({has:page.getByRole('button',{name:/Wholesaler$/})}).getByRole('button',{name:'ADS units',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(values.some(t=>t.startsWith('row:wholesaler:'))&&!values.some(t=>t.startsWith('row:community:')),'Wholesaler must not add the parent ADS');checks++;
 await host.getByRole('button',{name:/Community$/}).click();await page.evaluate(()=>echo());
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(!values.some(t=>t.startsWith('row:'))&&values.includes('saved-row:market'),'Gating must retain disabled choices');checks++;
 // Restore the full filter into a second page's FX-only control, edit the rate,
 // then bring it back. Hidden descendant choices and order must survive.
 await page.evaluate(()=>{window.fxVisual=ForecastMasterNativeControlsR17.default.create({element:document.getElementById('fx'),host:mockHost(fxCalls)});fxVisual.update({dataViews:[{...testView,metadata:{objects:{general:{variant:'fx',currencies:'GBP'}}}}],jsonFilters:[calls.filters.at(-1)],type:2});});
 await page.locator('#fx input').fill('1.32');await page.locator('#fx input').press('Tab');
 values=await page.evaluate(()=>fxCalls.filters.at(-1).values);assert(values.includes('saved-row:market')&&values.filter(t=>t.startsWith('fx:GBP:')).length===7);checks++;
 await page.evaluate(()=>visual.update({dataViews:[{...testView,metadata:{objects:{general:{variant:'sop',currencies:'GBP',preferences:calls.preferences}}}}],jsonFilters:[fxCalls.filters.at(-1)],type:2}));
 await host.getByRole('button',{name:'Community',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(values.some(t=>t.startsWith('row:market:'))&&values.some(t=>t.startsWith('row:wholesaler:')));checks++;
 await host.getByRole('button',{name:/Community$/}).press('Alt+ArrowDown');
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(values.includes('row:market:Units:1:0:2'),'Channel keyboard movement must change only channel rank');checks++;
 await host.getByRole('button',{name:'Reset order',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(values.includes('row:market:Units:0:0:2'));checks++;
 await host.getByRole('button',{name:'Clear all',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert(!values.some(t=>t.startsWith('row:'))&&values.filter(t=>t.startsWith('fx:GBP:')).length===7,'Clear selections must retain rates');checks++;
 await host.getByRole('button',{name:'Select all',exact:true}).click();
 values=await page.evaluate(()=>calls.filters.at(-1).values);assert.equal(values.filter(t=>t.startsWith('row:Units:')).length,0);assert.equal(values.filter(t=>t.startsWith('row:')).length,36);checks++;
 assert.deepStrictEqual(errors,[]);checks++;
 const result={Checks:checks,Status:'PASS',Errors:errors,Evidence:'Packaged control in headless Edge with mocked Power BI host; not native host filter/sync acceptance.'};
 fs.writeFileSync(path.join(root,'VALIDATION-CONTROLS.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
