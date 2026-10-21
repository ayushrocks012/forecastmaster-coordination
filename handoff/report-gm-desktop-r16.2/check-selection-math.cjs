const assert=require('node:assert/strict'),fs=require('node:fs');
const{createLive}=require('./local-test/math/live'),bridge=require('../../design/currency-plan-review-r15/bridge-catalog.json');
const file={id:'fixture',path:'synthetic/ADS.xlsm',filename:'UK_Driver_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm',affiliate:'UK',driver:'Driver',cycle:'2026-10',ims:'2026-08',ef:'2026-09'};
const rows=[],map=new Map();
for(const sector of ['Complete','One missing history month'])for(let t=0;t<48;t++){
 if(sector==='One missing history month'&&t===21)continue;
 const r={file:file.id,month:`${2024+Math.floor(t/12)}-${String(t%12+1).padStart(2,'0')}`,component:'gm-market-units',sector,channel:'Community',subchannel:'',n:100+t+(t>=32?50:0),missing:0};
 rows.push(r);const key=JSON.stringify([r.file,r.month,r.component]);if(!map.has(key))map.set(key,[]);map.get(key).push(r);
}
const a=createLive({rows,files:[file],byFileMonthComponent:map,bounds:{first:'2024-01',last:'2027-12'}},bridge),combo={files:a.files},metric={id:'market-units',section:'ims',component:'market',unit:'Units'},fy=Array.from({length:12},(_,i)=>24+i),ytg=[32,33,34,35],ytd=fy.slice(0,8);
const complete=a.sectors.filter(s=>s.raw==='Complete'),amount=(scope,months,trend=0)=>a.demand(combo,scope,metric,months,trend,null,null,false);
assert.equal(amount(a.sectors,fy),3508);assert.equal(amount(a.sectors,fy,12),null);
const issues=a.historyIssues(combo,a.sectors,metric,12,null);assert.equal(issues.length,1);assert.equal(issues[0].missing,1);assert.equal(issues[0].first,'2025-09');assert.equal(issues[0].last,'2026-08');
assert.equal(amount(complete,fy),1754);assert.equal(amount(complete,fy,12),1554);assert.equal(amount(complete,fy)-amount(complete,fy,12),200);
assert.equal(amount(complete,ytg)-amount(complete,ytg,12),200);assert.equal(amount(complete,ytd)-amount(complete,ytd,12),0);
assert.equal(amount(a.sectors,fy,12),null,'Reselecting the incomplete tier must withhold the benchmark again');
const reverseMap=new Map();for(const r of rows.slice().reverse()){const key=JSON.stringify([r.file,r.month,r.component]);if(!reverseMap.has(key))reverseMap.set(key,[]);reverseMap.get(key).push(r);}
const reordered=createLive({rows:rows.slice().reverse(),files:[file],byFileMonthComponent:reverseMap,bounds:a.bounds},bridge),saved=new Set(complete.map(s=>s.id)),restored=reordered.sectors.filter(s=>saved.has(s.id));
assert.deepEqual(restored.map(s=>s.raw),['Complete']);assert.equal(reordered.demand({files:reordered.files},restored,metric,fy,0,null,null,false),1754);
const result={evidence:'SYNTHETIC calculation selection regression',allTierPlan:3508,allTierBenchmark:null,selectedTierPlan:1754,selectedTierBenchmark:1554,selectedVariance:200,ytgVariance:200,ytdVariance:0,missingHistoryExplained:issues[0],reselectionRestoresUnavailability:true,stableSelectionAfterSourceReorder:true,noImputation:true};
fs.writeFileSync(__dirname+'/VALIDATION-SELECTION-MATH.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
