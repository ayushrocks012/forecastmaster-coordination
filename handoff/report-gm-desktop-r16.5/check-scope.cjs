const assert=require('node:assert/strict'),fs=require('node:fs');
const{scopeResolver,selectADS}=require('./local-test/math/scope');
const files=[],sectors=[],rows=[];
function source(id,driver,scenario,cycle='2026-10',affiliate='UK',tier='Tier'){
 const f={id,driver,scenario,cycle,affiliate,modifiedUtc:'2026-10-01T00:00:00Z'};files.push(f);
 const s={id:'sector-'+id,driver,raw:tier,name:tier};sectors.push(s);rows.push({file:id,sector:tier});return f;
}
source('a','A','ADS');source('b','B','ADS_002');for(const d of ['C','D','E'])source(d,d,'Working_001');
source('july','A','ADS','2026-07','UK','Different July tier');source('ie','A','ADS','2026-10','IE','IE tier');
const resolve=scopeResolver(files,sectors,rows),state={affiliates:['uk'],cycles:['2026-10'],fileMode:'ads'};
const first=resolve(state);assert.deepEqual(first.driverIds,['A','B']);assert.equal(first.sectors.length,2);assert.deepEqual(first.excluded,['C','D','E']);assert.equal(first.sources.length,2);
assert.equal(resolve({...state,sectors:[]}),first,'Changing a tick must not change source availability');
assert.deepEqual(resolve({...state,cycles:['2026-07']}).sectors.map(s=>s.name),['Different July tier']);
assert.deepEqual(resolve({...state,affiliates:['ie']}).sources.map(f=>f.id),['ie']);
assert.equal(resolve({...state,affiliates:['unknown']}).driverIds.length,0);
assert.deepEqual(resolve({...state,fileMode:'custom',files:['C']}).driverIds,['C']);
assert.equal(resolve({...state,fileMode:'custom',files:[]}).sectors.length,0);
const multisource=resolve({...state,affiliates:['uk','ie']});assert.equal(multisource.sources.filter(f=>f.driver==='A').length,2,'Affiliates keep their own ADS source');
const mixed=resolve({...state,cycles:['2026-10','2026-07']});assert(mixed.issues.some(i=>i.driver==='B'&&i.cycle==='2026-07'&&i.status==='MISSING'));
const duplicate={...files[0],id:'duplicate'};const ambiguous=selectADS(['2026-10'],[files[0],duplicate],['A']);assert.equal(ambiguous.files.length,0);assert.equal(ambiguous.issues[0].status,'AMBIGUOUS');
const preference=[{...files[0],scenario:'ADS_010',id:'ten'},{...files[0],scenario:'ADS_002',id:'two'},{...files[0],id:'plain'},{...files[0],scenario:'Plan ADS',id:'plan'}];
assert.equal(selectADS(['2026-10'],preference,['A']).files[0].id,'plan');assert.equal(selectADS(['2026-10'],preference.slice(0,3),['A']).files[0].id,'plain');assert.equal(selectADS(['2026-10'],preference.slice(0,2),['A']).files[0].id,'ten');
source('preferred','A','Plan ADS','2026-10','UK','Preferred source tier');
const preferred=scopeResolver(files,sectors,rows)(state);assert.deepEqual(preferred.sectors.filter(s=>s.driver==='A').map(s=>s.name),['Preferred source tier']);
const unresolvedFiles=[files[0],duplicate],unresolvedRows=[rows[0],{file:duplicate.id,sector:'Tier'}];
const unresolved=scopeResolver(unresolvedFiles,sectors,unresolvedRows)(state);assert.equal(unresolved.sources.length,0);assert.equal(unresolved.sectors.length,1);assert.equal(unresolved.issues[0].status,'AMBIGUOUS');
const result={evidence:'SYNTHETIC source identities only',availableADSDrivers:2,excludedNonADSDrivers:3,cycleAffiliateAndCustomScope:true,actualPreferredFileSectorMembership:true,missingCycleRetained:true,ambiguousADSBlocked:true,ambiguousTierStillVisible:true,sourcePreferencePreserved:true,scopeCacheIndependentOfTicks:true};
fs.writeFileSync(__dirname+'/VALIDATION-SCOPE.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
