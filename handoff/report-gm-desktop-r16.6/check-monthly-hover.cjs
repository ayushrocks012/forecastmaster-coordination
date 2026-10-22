const{chromium}=require('C:\\Users\\Ayush\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\node_modules\\playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const url=(folder)=>'file:///'+path.join(folder,'local-test/index.html').replace(/\\/g,'/');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true}),page=await browser.newPage({viewport:{width:1480,height:1050},timezoneId:'Europe/London'}),errors=[];page.on('pageerror',e=>errors.push(String(e)));
 const feed=JSON.parse(fs.readFileSync(path.join(__dirname,'local-test/feed.json')));
 async function setup(folder,view=feed){await page.goto(url(folder));await page.evaluate(v=>{window.feed=v;visual.update({dataViews:[v],viewport:{width:1440,height:2400},type:2});window.d=document.querySelector('#fm-connected-demand-r15').fmDesign;window.s=document.querySelector('#fm-connected-sop-r15').sopDesign;window.session=document.querySelector('#fm-connected-review-r15').reviewSession;d.setState({display:'units',monthStart:'2026-01',monthEnd:'2026-12',combined:true,view:'driver',trends:[12]});},view);}
 async function hover(mode,position,event='pointermove'){
  return page.evaluate(({mode,position,event})=>{const plot=document.querySelector(mode==='demand'?'.fm-plot':'.sb-plot'),hit=plot.querySelector('[data-chart-hit]'),box=hit.getBoundingClientRect(),scale=plot.getBoundingClientRect().width/plot.clientWidth,months=mode==='demand'?d.chartSeries(d.catalog.find(m=>m.id===d.getState().metrics[0])).months:s.chartMonths(),inset=mode==='sop'?4*scale:0,unit=(box.width-2*inset)/Math.max(1,months.length-1),clientX=box.left+inset+unit*position,clientY=box.top+box.height/2;
   hit.dispatchEvent(new PointerEvent(event,{bubbles:true,clientX,clientY}));const tip=plot.querySelector('[role=tooltip]'),marker=[...plot.querySelectorAll('[data-chart-hover-marker]')].map(e=>Number(e.getAttribute('cx'))),guide=plot.querySelector('[data-chart-hover-guide]');return {text:tip.innerText,hidden:tip.hidden,rows:[...tip.querySelectorAll('div')].filter(e=>e.querySelector('span')).map(e=>({name:e.querySelector('span').textContent,value:e.querySelector('span:last-child').textContent})),marker,guide:Number(guide?.getAttribute('x1')),expectedX:Number(hit.getAttribute('x'))+(mode==='sop'?4:0)+(Number(hit.getAttribute('width'))-(mode==='sop'?8:0))/Math.max(1,months.length-1)*Math.round(position)};},{mode,position,event});
 }
 async function sop(){await page.evaluate(()=>{session.navigate('sop');s.setState({channels:['community'],targets:['community'],selectedMeasures:['market','abbott','share'],display:'units',grouping:'combined'});});}
 // Reproduce the defect in the preserved candidate with the exact same feed.
 await setup(path.resolve(__dirname,'../report-gm-desktop-r16.4'));
 const beforeD=await hover('demand',4.05),afterD=await hover('demand',4.25);assert.notEqual(beforeD.text,afterD.text);assert.equal(beforeD.text.split('\n')[0],afterD.text.split('\n')[0]);await sop();const beforeS=await hover('sop',4.05),afterS=await hover('sop',4.25);assert.notEqual(beforeS.text,afterS.text);assert.equal(beforeS.text.split('\n')[0],afterS.text.split('\n')[0]);
 await setup(__dirname);const checks=[];
 for(const mode of ['demand','sop']){
  if(mode==='sop')await sop();
  for(const width of [1440,720,1152]){
   await page.evaluate(w=>visual.update({viewport:{width:w,height:w*2400/1440},type:4}),width);
   const samples=[];for(const offset of [-.4,-.1,0,.01,.02,.4])samples.push(await hover(mode,4+offset));
   for(const sample of samples){assert.equal(sample.text,samples[0].text,'Tooltip must stay stable for the same nearest month');assert.match(sample.text,/May 26/);assert(Math.abs(sample.guide-sample.expectedX)<.01);assert(sample.marker.every(x=>Math.abs(x-sample.guide)<.01));}
   const expected=await page.evaluate(mode=>mode==='demand'?d.chartSeries(d.catalog.find(m=>m.id===d.getState().metrics[0])).series.filter(s=>s.points[4]?.y!=null).map(s=>s.points[4].y):s.activeRows().map(r=>s.amount(r,s.groups()[0],[28],'2026-10')),mode);
   const values=samples[0].rows.map(r=>Number(r.value.replace(/[^0-9.-]/g,''))/(r.value.includes('%')?100:1));assert.equal(values.length,expected.length);for(let i=0;i<expected.length;i++)assert(Math.abs(values[i]-expected[i])<1e-8,'Tooltip must equal the monthly model observation');
   assert.match((await hover(mode,4.6)).text,/Jun 26/);
   assert.match((await hover(mode,0)).text,/Jan 26/);assert.match((await hover(mode,11)).text,/Dec 26/);
   const pinned=await hover(mode,4,'pointerdown');assert.equal((await hover(mode,5)).text,pinned.text,'Pinned month must stay fixed');await hover(mode,4,'pointerdown');assert.match((await hover(mode,5)).text,/Jun 26/);
   checks.push({mode,width,stableWithinMonth:true,exactMonthlyValues:true,guideAndMarkersSnapped:true,boundariesAndPin:true});
  }
 }
 // Value conversion, forecast amounts, monthly trend and weighted Share must
 // also use the exact selected month's value.
 for(const mode of ['demand','sop']){
  await page.evaluate(mode=>{session.navigate(mode);document.querySelector('#fm-connected-review-r15').planFX.setState({currency:'USD',rates:{GBP:1.32}});(mode==='demand'?d:s).setState({display:'value'});},mode);
  const sample=await hover(mode,9.1);assert.match(sample.text,/Oct 26/);assert.equal(sample.text,(await hover(mode,9.35)).text);
  const expected=await page.evaluate(mode=>mode==='demand'?d.chartSeries(d.catalog.find(m=>m.id===d.getState().metrics[0])).series.filter(s=>s.points[9]?.y!=null).map(s=>s.points[9].y):s.activeRows().map(r=>s.amount(r,s.groups()[0],[33],'2026-10')),mode);
  const values=sample.rows.map(r=>Number(r.value.replace(/[^0-9.-]/g,''))/(r.value.includes('%')?100:1));assert.equal(values.length,expected.length);for(let i=0;i<expected.length;i++){const formatted=sample.rows[i].value.includes('%')?Number((expected[i]*100).toFixed(1))/100:Math.round(expected[i]);assert.equal(values[i],formatted,'USD tooltip must show the monthly point with the existing display precision');}
 }
 // A valid month beside a missing month still has its own tooltip. Blank is never
 // interpolated from neighbours, while numeric zero remains visible.
 const missing=structuredClone(feed);for(const r of missing.table.rows)if(r[2]==='gm-market-units'&&r[1]==='2026-05'){r[6]=null;r[7]=1;}else if(r[2]==='gm-market-units'&&r[1]==='2026-04'){r[6]=0;r[7]=0;}
 await setup(__dirname,missing);assert.match((await hover('demand',3.1)).text,/Apr 26/);assert.equal((await hover('demand',3.1)).rows[0].value,'0');assert.match((await hover('demand',4.1)).text,/No data for this month/);assert.equal((await hover('demand',4.1)).rows.length,0);assert((await hover('demand',5.1)).rows.length>0);
 await sop();await page.evaluate(()=>s.setState({selectedMeasures:['market']}));assert.equal((await hover('sop',3.1)).rows[0].value,'0');assert.match((await hover('sop',4.1)).text,/No data for this month/);assert((await hover('sop',5.1)).rows.length>0);
 // The endpoint tooltip must not require another month, including a one-month view.
 for(const mode of ['demand','sop']){await page.evaluate(mode=>{session.navigate(mode);(mode==='demand'?d:s).setState({monthStart:'2026-06',monthEnd:'2026-06'});},mode);const one=await hover(mode,0);assert.match(one.text,/Jun 26/);assert(one.rows.length>0);}
 assert.deepEqual(errors,[]);const calls=await page.evaluate(()=>hostCalls);assert.equal(calls.fetch,0);assert.deepEqual(calls.failed,[]);
 const result={evidence:'SYNTHETIC packaged visual in Edge; native receiving check pending',priorR16_4InterpolationReproducedInBothViews:true,monthlyHoverChecks:checks,weightedShareExact:true,USDValueForecastAndTrendExact:true,missingMonthNeverInterpolated:true,numericZeroVisible:true,validMonthBesideGapVisible:true,oneMonthAndFinalMonthSupported:true,modelFetches:calls.fetch,browserErrors:errors};fs.writeFileSync(path.join(__dirname,'VALIDATION-MONTHLY-HOVER.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
