const assert = require('node:assert/strict');
const {CohortMath,seriesFor,monthIndex,monthISO}=require('./cohorts.cjs');
const checks=[];
function check(name,run){run();checks.push(name);}
const metric={id:'units',aggregation:'SUM',cutoffFamily:'IMS',unit:'Units'}, dims={channel:'all',subchannel:'all',sector:'all'};
const make=(id,cycle,driver,ims='2026-05')=>({id,filename:id+'.xlsm',label:id,cycle,driver,ims,ef:'2026-09'});
const july=make('july','2026-07','Core Oral'),oct=make('oct','2026-10','Core Oral','2026-08'),paed=make('paed','2026-07','Paed SIP');
const values=new Map();
for(let t=0;t<72;t++)for(const f of [july,oct,paed]){
 const base=f===oct?1000:100,cut=monthIndex(f.ims),n=t<=cut?base+t:(base+t)*2;
 values.set(f.id+'|'+monthISO(t),{parts:[{n,d:100,channel:'Community',subchannel:'',sector:'A',nm:0,dm:0}]});
}
const math=new CohortMath(values,metric,dims),one=f=>seriesFor([f],[f.cycle],[f.driver])[0];
check('July plan retains July saved forecast even when October has newer actuals',()=>assert.equal(math.value(one(july),41),282));
check('October plan retains its own revised historical actual',()=>assert.equal(math.value(one(oct),41),1041));
check('One series per selected cycle in driver totals',()=>assert.equal(seriesFor([july,paed],['2026-07','2026-10'],['Core Oral','Paed SIP']).length,2));
check('Selected driver total adds one saved source per driver',()=>assert.equal(math.value(seriesFor([july,paed],['2026-07'],['Core Oral','Paed SIP'])[0],41),564));
check('Missing selected driver blocks an incomplete total',()=>assert.equal(math.value(seriesFor([july],['2026-07'],['Core Oral','Paed SIP'])[0],41),null));
check('Multiple versions of a driver are not double counted',()=>assert.equal(math.value(seriesFor([july,{...july,id:'other'},paed],['2026-07'],['Core Oral','Paed SIP'])[0],41),null));
check('Each file has its own actual/forecast boundary',()=>{assert.equal(math.status(one(july),41),'F');assert.equal(math.status(one(oct),41),'A');});
check('Mixed driver cutoffs are explicitly marked mixed',()=>{const later={...paed,ims:'2026-06'};assert.equal(math.status(seriesFor([july,later],['2026-07'],['Core Oral','Paed SIP'])[0],41),'M');});
check('EF uses its separate explicit actual cutoff',()=>assert.equal(new CohortMath(values,{...metric,cutoffFamily:'EF'},dims).status(one(july),44),'A'));
check('A zero numeric source is available and remains zero',()=>{const v=new Map([['july|2026-01',{parts:[{n:0,d:0,channel:'Community',subchannel:'',sector:'A'}]}]]);assert.equal(new CohortMath(v,metric,dims).value(one(july),36),0);});
check('Blank members preserve reported subtotal; entirely blank month stays blank',()=>{const v=new Map([['july|2026-01',{parts:[{n:4,d:null,channel:'Community',subchannel:'',sector:'A'},{n:null,d:null,channel:'Community',subchannel:'',sector:'A'}]}]]);const m=new CohortMath(v,metric,dims);assert.equal(m.value(one(july),36),4);assert.equal(m.value(one(july),37),null);});
check('Missing whole driver month is not treated as a zero contributor',()=>{const v=new Map(values);v.delete('paed|2026-01');assert.equal(new CohortMath(v,metric,dims).value(seriesFor([july,paed],['2026-07'],['Core Oral','Paed SIP'])[0],36),null);});
check('Trends use a source own complete actual window',()=>{assert.equal(math.value(one(july),41,'t12'),141);assert.equal(math.value(one(oct),44,'t12'),1044);});
check('A gap in a training month prevents that trend',()=>{const v=new Map(values);v.delete('july|2026-01');assert.equal(new CohortMath(v,metric,dims).value(one(july),41,'t12'),null);});
check('Shares use combined numerators and denominators, not an average of shares',()=>{const v=new Map([['july|2026-01',{n:10,d:100}],['paed|2026-01',{n:450,d:900}],['july|2026-02',{n:10,d:200}],['paed|2026-02',{n:180,d:300}]]);const m=new CohortMath(v,{...metric,aggregation:'RATIO'},dims),s=seriesFor([july,paed],['2026-07'],['Core Oral','Paed SIP'])[0];assert.equal(m.value(s,36),.46);assert.equal(m.total(s,36,37),650/1500);});
check('A requested channel filters source components',()=>assert.equal(new CohortMath(values,metric,{...dims,channel:'Out of Pocket'}).value(one(july),41),null));
check('Year and month indices round trip across years',()=>{for(let t=-36;t<=240;t++)assert.equal(monthIndex(monthISO(t)),t);});
console.log(JSON.stringify({Status:'PASS',Passed:checks.length,Checks:checks},null,2));
