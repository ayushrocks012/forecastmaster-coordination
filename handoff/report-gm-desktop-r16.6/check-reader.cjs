const assert=require('node:assert/strict'),fs=require('node:fs');
const{decode,createLive}=require('./local-test/math/live');
const bridge=require('../../design/currency-plan-review-r15/bridge-catalog.json');
const roles=['FileID','Month','MetricKey','Channel','SubChannel','Sector','Numerator','NumeratorMissing','FileMetadata','Bounds'];
const columns=roles.map(r=>({displayName:r,roles:{[r]:true}}));
const file={id:'fixture',path:'synthetic/ADS.xlsm',filename:'UK_Driver_Bridge_Oct 26_EF-Sep 26_IMS-Aug 26_ADS.xlsm',affiliate:'UK',driver:'Driver',cycle:'2026-10',ims:'2026-08',ef:'2026-09'};
const bounds={first:'2026-01',last:'2026-12'};
const row=(n=20,sub='',missing=0,month='2026-01')=>['fixture',month,'gm-market-units','Community',sub,'Tier',n,missing,JSON.stringify(file),JSON.stringify(bounds)];
const view=rows=>({table:{columns,rows}});
const first=row(),baseline=decode(view([first]));
const before=require('./local-test/r16-before/live');
assert.throws(()=>before.createLive(before.decode(view([first,structuredClone(first)])),bridge),/Duplicate monthly component\. Complete totals withheld/);
const originalTZ=process.env.TZ;process.env.TZ='Europe/London';
const bstRows=[row(20,'',0,'2026-03-01T00:00:00.000Z'),row(30,'',0,'2026-03-31T23:00:00.000Z')];
assert.throws(()=>before.createLive(before.decode(view(bstRows)),bridge),/Duplicate monthly component/);
const bst=decode(view(bstRows));assert.deepEqual(bst.rows.map(r=>r.month),['2026-03','2026-04']);
for(const asDate of [s=>new Date(s),s=>new Date(s).getTime()]){
 const formats=bstRows.map(r=>{const next=structuredClone(r);next[1]=asDate(r[1]);return next;});
 assert.deepEqual(decode(view(formats)).rows.map(r=>r.month),['2026-03','2026-04']);
}
const fall=decode(view([row(20,'',0,'2026-09-30T23:00:00.000Z'),row(30,'',0,'2026-11-01T00:00:00.000Z')]));assert.deepEqual(fall.rows.map(r=>r.month),['2026-10','2026-11']);
const timezoneChecks=[];
for(const zone of ['Europe/London','UTC','America/New_York','Asia/Kolkata']){
 process.env.TZ=zone;
 const calendar=Array.from({length:84},(_,i)=>new Date(2023+Math.floor(i/12),i%12,1));
 const delivered=calendar.map((d,i)=>row(i,'',0,d.toISOString())),feed=decode(view(delivered));
 const expected=Array.from({length:84},(_,i)=>`${2023+Math.floor(i/12)}-${String(i%12+1).padStart(2,'0')}`);
 assert.deepEqual(feed.rows.map(r=>r.month),expected);assert.equal(new Set(feed.rows.map(r=>r.month)).size,84);
 timezoneChecks.push({zone,sourceMonths:84,decodedMonths:84});
}
if(originalTZ===undefined)delete process.env.TZ;else process.env.TZ=originalTZ;
const metric={id:'market-units',component:'market',section:'ims',unit:'Units'};
function amount(feed){const a=createLive(feed,bridge);return a.demand({files:a.files},a.sectors,metric,[24],0,null,null,false);}
assert.equal(amount(baseline),20);
const overlap=decode(view([first,structuredClone(first),structuredClone(first)]));
assert.equal(overlap.rows.length,1);assert.equal(overlap.diagnostics.repeatedDeliveryRows,2);assert.equal(amount(overlap),20);
assert.throws(()=>decode(view([first,row(21)])),/FM_FEED_CONFLICT/);
assert.throws(()=>decode(view([first,row(20,'',1)])),/FM_FEED_CONFLICT/);
assert.throws(()=>decode(view([row(0),row(null)])),/FM_FEED_CONFLICT/);
const zero=decode(view([row(0),row(0)]));assert.equal(amount(zero),0);assert.equal(zero.rows.length,1);
// Null and empty text are separate original groups. Both business-blank
// sub-channel contributions count; equal amounts do not make them replays.
const aliases=decode(view([row(20,null),row(30,''),row(30,'')]));
assert.equal(aliases.rows.length,2);assert.equal(aliases.diagnostics.blankVariantRows,1);assert.equal(amount(aliases),50);
const equalBlankGroups=decode(view([row(20,null),row(20,'')]));assert.equal(amount(equalBlankGroups),40);
const missingBlankGroup=decode(view([row(20,null),row(null,'',1)]));assert.equal(amount(missingBlankGroup),null);
const metadata=decode(view([row(null,'',null),first]));assert.equal(metadata.rows.length,1);assert.equal(metadata.files.length,1);assert.equal(metadata.diagnostics.metadataOnlyRows,1);assert.equal(amount(metadata),20);
assert.throws(()=>decode(view([row(20,'',0,'2026-01-01'),row(20,'',0,'2026-01-02')])),/FM_FEED_MONTH_GRAIN/);
const contexts=decode(view([first,['fixture','2026-01','gm-market-units','Contracts','Hospital','Tier',30,0,null,null]]));assert.equal(contexts.rows.length,2);assert.equal(amount(contexts),20);
const bad=structuredClone(first);bad[4]=false;assert.throws(()=>decode(view([bad])),/FM_FEED_DIMENSION/);
const changedMeta=structuredClone(first);changedMeta[8]=JSON.stringify({...file,ims:'2026-07'});assert.throws(()=>decode(view([first,changedMeta])),/FM_FEED_METADATA/);
const changedBounds=structuredClone(first);changedBounds[9]=JSON.stringify({...bounds,last:'2027-12'});assert.throws(()=>decode(view([first,changedBounds])),/FM_FEED_BOUNDS/);
// Replay an entire 10k-row boundary without inflating its count or subtotal.
const large=Array.from({length:10001},(_,i)=>['fixture','2026-01','gm-market-units','Community','','Tier '+i,i,0,i?null:JSON.stringify(file),i?null:JSON.stringify(bounds)]);
const merged=decode(view([...large.slice(0,10000),structuredClone(large[9999]),...large.slice(10000)]));
assert.equal(merged.rows.length,10001);assert.equal(merged.diagnostics.repeatedDeliveryRows,1);assert.equal(merged.rows.reduce((s,r)=>s+r.n,0),10000*10001/2);
const result={evidence:'SYNTHETIC decoder regression; company payload not available',reportedR16ErrorReproduced:true,bstTimestampRegressionReproduced:true,timezoneChecks,dateObjectsAndEpochs:true,exactRepeatsCountOnce:true,conflictingAmountsBlocked:true,conflictingMissingCountsBlocked:true,zeroPreserved:true,distinctBlankGroupsRetained:true,metadataOnlyRowsExcluded:true,differentDatesNotFoldedTogether:true,sourceMetadataConflictBlocked:true,calendarMetadataConflictBlocked:true,largeBoundaryRows:merged.rows.length,largeBoundarySum:merged.rows.reduce((s,r)=>s+r.n,0)};
fs.writeFileSync(__dirname+'/VALIDATION-READER.json',JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
