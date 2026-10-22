const assert=require('node:assert/strict'),fs=require('node:fs');const{createLive}=require('./local-test/math/live'),bridge=require('../../design/currency-plan-review-r15/bridge-catalog.json');
const iso=t=>`${2024+Math.floor(t/12)}-${String(t%12+1).padStart(2,'0')}`;
const file={id:'synthetic',filename:'UK_Driver_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm',affiliate:'UK',driver:'Driver',cycle:'2026-10',ims:'2026-08',ef:'2026-09',currency:'GBP'};
const rows=[];for(let t=0;t<48;t++)for(const sector of ['A','B','C'])for(const display of ['units','value'])for(const id of ['abbott','market','pi','net']){const n=id==='market'?(sector==='A'?100:sector==='B'?300:600)+t:id==='abbott'?(sector==='A'?20:sector==='B'?60:120)+t:id==='pi'?5:15+t;rows.push({file:file.id,sector,month:iso(t),component:`gm-${id}-${display}`,channel:'Community',subchannel:'',n:n*(display==='value'?5:1),missing:0});}
function make(input=rows,files=[file],constructor=createLive){const byFileMonthComponent=new Map();for(const r of input){const k=JSON.stringify([r.file,r.month,r.component]);if(!byFileMonthComponent.has(k))byFileMonthComponent.set(k,[]);byFileMonthComponent.get(k).push(r);}const a=constructor({rows:input,byFileMonthComponent,files,bounds:{first:'2024-01',last:'2027-12'}},bridge);a.setSources(()=>a.files);return a;}
const metric=(id,display)=>({id:id+'-'+display,section:'ims',component:id==='market'?(display==='units'?'market':'marketValue'):(display==='units'?'abbott':'abbottValue'),unit:display==='units'?'Units':'£'});
const ratio=display=>({...metric('abbott',display),id:'share-'+display,denominator:display==='units'?'market':'marketValue',unit:'%'}),demand=(a,m,months,fx=null,convert=false,trend=0,scope=a.sectors)=>a.demand({files:a.files},scope,m,months,trend,null,fx,convert);
const equal=(a,b)=>{if(a===null||b===null)assert.equal(a,b);else assert(Math.abs(a-b)<1e-8,`${a} != ${b}`);};
// The absent Abbott side must not delete the valid Market contribution.
const gap=rows.map(r=>r.sector==='C'&&r.component.startsWith('gm-abbott')&&r.month.startsWith('2024')?{...r,n:null,missing:1}:r),a=make(gap),months=Array.from({length:12},(_,i)=>i);
for(const display of ['units','value']){const n=demand(a,metric('abbott',display),months),d=demand(a,metric('market',display),months),share=demand(a,ratio(display),months);equal(share,n/d);equal(a.sop({id:'share'},{sectors:a.sectors},months,'2026-10',display,null,false),n/d);assert.equal(demand(a,ratio(display),months,null,false,0,a.sectors.filter(s=>s.raw==='C')),null);}
// Reproduce the older fault using the identical synthetic observations.
const old=make(gap,[file],require('./local-test/r16-5-before/live').createLive);assert.notEqual(demand(old,ratio('value'),months),demand(a,ratio('value'),months));
let seed=123456;const rnd=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/2**32;};let assertions=0;
for(let test=0;test<60;test++){
 const input=rows.map(r=>{const missing=rnd()<.12;return {...r,n:missing?null:rnd()<.08?0:r.n,missing:missing?1:0};}),live=make(input);
 const window=Array.from({length:test%2?12:4},(_,i)=>test%2?24+i:32+i);
 for(const display of ['units','value']){
  const oracle=id=>{const totals=window.map(t=>input.filter(r=>r.month===iso(t)&&r.component===`gm-${id}-${display}`&&r.missing===0&&Number.isFinite(r.n)).map(r=>r.n));return totals.some(v=>!v.length)?null:totals.flat().reduce((a,b)=>a+b,0);};
  for(const id of ['market','abbott','pi','net']){const expected=oracle(id);equal(live.sop({id},{sectors:live.sectors},window,'2026-10',display,null,false),expected);if(['market','abbott'].includes(id))equal(demand(live,metric(id,display),window),expected);assertions++;}
  const n=oracle('abbott'),d=oracle('market'),expected=n===null||d===null||d===0?null:n/d;equal(demand(live,ratio(display),window),expected);equal(live.sop({id:'share'},{sectors:live.sectors},window,'2026-10',display,null,false),expected);assertions+=2;
 }
}
// Share is a ratio of period amounts, not an average of monthly percentages.
const vary=make(rows.map(r=>r.component==='gm-market-units'&&r.month==='2026-02'?{...r,n:r.n*9}:r));const nm=[24,25];equal(demand(vary,ratio('units'),nm),demand(vary,metric('abbott','units'),nm)/demand(vary,metric('market','units'),nm));
// Mixed value currencies are weighted in one currency; FX changes invalidate fits.
const eur={...file,id:'eur',affiliate:'EU',driver:'Other driver',currency:'EUR',filename:'EU_Driver_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm'},mixed=[...rows,...rows.map(r=>({...r,file:'eur',sector:'EUR '+r.sector,n:r.component.includes('abbott')?r.n*2:r.n}))],multi=make(mixed,[file,eur]);
let rates={GBP:2,EUR:3};const fx={getState:()=>({currency:'USD',rates}),total:xs=>xs.length&&xs.every(p=>Number.isFinite(rates[p.currency]))?xs.reduce((s,p)=>s+p.value*rates[p.currency],0):null};
for(const r of [rates,{GBP:3,EUR:1}]){rates=r;const n=demand(multi,metric('abbott','value'),[24,25],fx,true),d=demand(multi,metric('market','value'),[24,25],fx,true);equal(demand(multi,ratio('value'),[24,25],fx,true),n/d);equal(multi.sop({id:'share'},{sectors:multi.sectors},[24,25],'2026-10','value',fx,true),n/d);const points=Array.from({length:12},(_,i)=>{const t=20+i,n=demand(multi,metric('abbott','value'),[t],fx,true),d=demand(multi,metric('market','value'),[t],fx,true);return {x:t,y:n/d};}),mx=25.5,my=points.reduce((s,p)=>s+p.y,0)/12,b=points.reduce((s,p)=>s+(p.x-mx)*(p.y-my),0)/points.reduce((s,p)=>s+(p.x-mx)**2,0);equal(demand(multi,ratio('value'),[32],fx,true,12),my+b*(32-mx));}
rates={GBP:2};assert.equal(demand(multi,ratio('value'),[24],fx,true),null);rates={GBP:0,EUR:0};assert.equal(demand(multi,ratio('value'),[24],fx,true),null);
const unknown=make(mixed,[{...file,affiliate:'Unknown A',currency:null},{...eur,affiliate:'Unknown B',currency:null}]);assert.equal(demand(unknown,ratio('value'),[24],fx,true),null);
const oneCurrency=make();rates={GBP:0};equal(demand(oneCurrency,ratio('value'),[24],fx,true),demand(oneCurrency,ratio('value'),[24]));
const result={evidence:'SYNTHETIC independent calculation oracle; live reconciliation pending',oldAsymmetricMissingShareDefectReproduced:true,independentNumeratorAndDenominatorTotals:true,singleTierMissingPreserved:true,randomOracleAssertions:assertions,unitsAndValueAmounts:true,zeroAndEmptyPopulation:true,weightedPeriodNotAveragePercent:true,multiCurrencyWeightsAndMissingRates:true,singleCurrencyShareFXNeutral:true};fs.writeFileSync(__dirname+'/VALIDATION-RATIOS.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
