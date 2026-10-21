// @ts-nocheck
import {currentFiles, importedAt} from './files';
export const numeric = x => typeof x === 'number' && Number.isFinite(x);
export const index = iso => (Number(iso.slice(0,4))-2024)*12+Number(iso.slice(5,7))-1;
export const iso = t => `${2024+Math.floor(t/12)}-${String(((t%12)+12)%12+1).padStart(2,'0')}`;
const sum = xs => xs.length && xs.every(numeric) ? xs.reduce((a,b)=>a+b,0) : null;

/** One complete, immutable host delivery. Every derived cache dies on replacement. */
export function createLive(feed, bridge) {
 const metrics = new Map();
 for (const r of feed.rows) {
  // Preserve the query's raw blank identities; null and empty text can be
  // distinct aggregate groups even though both display as No sub-channel.
  const key = r.queryKey || JSON.stringify([r.file,r.month,r.component,r.sector,r.channel,r.subchannel]);
  if (metrics.has(key)) throw Error('Duplicate monthly component. Complete totals withheld.');
  metrics.set(key, r);
 }
 const rawFiles=currentFiles(feed.files), driverNames=[...new Set(rawFiles.map(f=>f.driver))].sort();
 const drivers=Object.fromEntries(driverNames.map((s,i)=>['d'+i,s]));
 const driverId=s=>Object.keys(drivers).find(k=>drivers[k]===s);
 const files=rawFiles.map(f=>{
  const name=f.filename||f.path||f.id, match=name.replace(/\.(xlsm|xlsx)$/i,'').match(/_IMS[- ][^_]+_(.+)$/i);
  const scenario=match?.[1] || name.replace(/\.(xlsm|xlsx)$/i,'').match(/(Plan[ _-]*ADS|ADS(?:_\d+)?|[^_]+_\d+)$/i)?.[1] || name;
  // The installed projection has business £ amounts. No unverified country -> FX mapping.
  const currency=f.currency || (/^(UK|United Kingdom)$/i.test(f.affiliate)?'GBP':null);
  return {...f,rawDriver:f.driver,driver:driverId(f.driver),name,scenario,modifiedUtc:importedAt(f)?new Date(importedAt(f)).toISOString():'',currency};
 });
 const sourceById=new Map(files.map(f=>[f.id,f]));
 const sectors=[];const seen=new Set();
 for(const r of feed.rows){const f=sourceById.get(r.file);if(!f)continue;const key=JSON.stringify([f.driver,r.sector]);if(seen.has(key))continue;seen.add(key);sectors.push({id:'s'+sectors.length,name:r.sector||'No forecast tier',driver:f.driver,raw:r.sector,color:sectors.length%6+1});}
 sectors.sort((a,b)=>a.driver.localeCompare(b.driver)||a.name.localeCompare(b.name));
 const affiliates=[...new Set(files.map(f=>f.affiliate))].map(a=>({id:a.toLowerCase(),name:a,currency:files.find(f=>f.affiliate===a)?.currency}));
 const cycles=[...new Set(files.map(f=>f.cycle))].sort().map(c=>({id:c,name:new Date(c+'-01T12:00:00Z').toLocaleDateString('en-GB',{month:'long',year:'numeric',timeZone:'UTC'})}));
 const contexts=[...new Map(feed.rows.filter(r=>r.component.startsWith('ef-ads')).map(r=>[JSON.stringify([r.channel,r.subchannel]),{id:JSON.stringify([r.channel,r.subchannel]),name:r.subchannel||'—',channel:r.channel,raw:r.subchannel}])).values()];
 const channels=[...new Set(contexts.map(c=>c.channel))].map(c=>({id:c,name:c}));
 const cache=new Map(), fits=new Map();
 function read(file,sector,t,component,channel=null,subchannel=null){
  const key=JSON.stringify([file.id,sector.raw,t,component,channel,subchannel]);if(cache.has(key))return cache.get(key);
  const rows=feed.byFileMonthComponent.get(JSON.stringify([file.id,iso(t),component]))||[];
  const values=rows.filter(r=>r.sector===sector.raw&&(channel===null||r.channel===channel)&&(subchannel===null||r.subchannel===subchannel));
  // A source blank is unavailable; it cannot become a partial period or numeric zero.
  const v=values.length&&values.every(r=>r.missing===0&&numeric(r.n))?sum(values.map(r=>r.n)):null;cache.set(key,v);return v;
 }
 function cutoff(file,basis){const v=file[basis==='ef'?'ef':'ims'];return /^\d{4}-\d{2}$/.test(v||'')?index(v):null;}
 function fit(file,sector,metric,n,filters){
  const k=JSON.stringify([file.id,sector.id,metric.id,n,filters]);if(fits.has(k))return fits.get(k);
  const end=cutoff(file,metric.section),points=Array.from({length:n},(_,i)=>{const t=end-n+1+i;return {x:t,y:point(file,sector,metric,t,0,filters)}});
  if(end===null||points.some(p=>!numeric(p.y))){fits.set(k,null);return null;}
  const mx=points.reduce((a,p)=>a+p.x,0)/n,my=points.reduce((a,p)=>a+p.y,0)/n;
  const b=points.reduce((a,p)=>a+(p.x-mx)*(p.y-my),0)/points.reduce((a,p)=>a+(p.x-mx)**2,0),f={a:my-b*mx,b};fits.set(k,f);return f;
 }
 function parts(file,sector,metric,t,trend=0,filters=null){
  const components={market:'gm-market-units',abbott:'gm-abbott-units',marketValue:'gm-market-value',abbottValue:'gm-abbott-value',ef:'ef-ads-units',efValue:'ef-ads-value'};
  const get=c=>{
   if(metric.section!=='ef')return read(file,sector,t,components[c],'Community','');
   const ctx=contexts.filter(x=>filters?.channels.includes(x.channel)&&filters?.subchannels.includes(x.id));
   return sum(ctx.map(x=>read(file,sector,t,components[c],x.channel,x.raw)));
  };
  let n=get(metric.component),d=metric.denominator?get(metric.denominator):null;
  if(trend&&t>cutoff(file,metric.section)){const f=fit(file,sector,metric,trend,filters);n=f?(metric.denominator?(numeric(d)?(f.a+f.b*t)*d:null):f.a+f.b*t):null;}
  return {n,d};
 }
 function point(file,sector,metric,t,trend,filters){const p=parts(file,sector,metric,t,trend,filters);return metric.denominator?numeric(p.n)&&numeric(p.d)&&p.d!==0?p.n/p.d:null:p.n;}
 function demand(combo,subset,metric,months,trend,filters,fx,convert){
  if(!months.length||!subset.length)return null;const contributions=[],den=[];
  for(const sector of subset){const sources=combo.files.filter(f=>f.driver===sector.driver);if(sources.length!==1)return null;const f=sources[0];
   for(const t of months){const p=parts(f,sector,metric,t,trend,filters);if(!numeric(p.n)||(metric.denominator&&!numeric(p.d)))return null;contributions.push({currency:f.currency,value:p.n});if(metric.denominator)den.push(p.d);}}
  if(metric.denominator){const d=sum(den);return d!==null&&d!==0?sum(contributions.map(p=>p.value))/d:null;}
  return convert&&metric.unit==='£'?fx.total(contributions):sum(contributions.map(p=>p.value));
 }
 let selectedSources=()=>files;
 function sop(row,group,months,cycle,display,fx,convert){
  if(!group.sectors.length||!months.length)return null;const values=[],den=[];const b=bridge.bindings.find(b=>b.id===row.id);if(!b)return null;
  for(const sector of group.sectors){const fs=selectedSources().filter(f=>f.driver===sector.driver&&f.cycle===cycle);if(fs.length!==1)return null;const f=fs[0];
   for(const t of months){const sourceId=row.id==='share'?'abbott':b.units.measure==='ADS Selling units'?'leaf':row.id;
    const c=sourceId==='leaf'?(display==='units'?'ef-ads-units':'ef-ads-value'):'gm-'+sourceId+'-'+display,n=read(f,sector,t,c,b.channel,b.subChannel||'');if(!numeric(n))return null;values.push({currency:f.currency,value:n});if(row.id==='share'){const d=read(f,sector,t,'gm-market-'+display,b.channel,b.subChannel||'');if(!numeric(d))return null;den.push(d);}}}
  if(row.id==='share'){const d=sum(den);return d!==null&&d!==0?sum(values.map(p=>p.value))/d:null;}
  return convert&&display==='value'?fx.total(values):sum(values.map(p=>p.value));
 }
 return {files,sectors,drivers,affiliates,cycles,channels,subchannels:contexts,read,cutoff,fit,demand,sop,sourceById,bounds:feed.bounds,setSources:f=>selectedSources=f,
  currencies:affiliates.filter(a=>a.currency).map(a=>({id:a.id,currency:a.currency,symbol:a.currency==='GBP'?'£':a.currency+' '})),
  cutFor:(cycle,basis)=>{const cs=selectedSources().filter(f=>f.cycle===cycle).map(f=>cutoff(f,basis));return cs.length&&cs.every(numeric)&&new Set(cs).size===1?cs[0]:null;},
  missingSOP:!feed.rows.some(r=>r.component==='gm-pi-units'),stats:()=>({cached:cache.size,fits:fits.size,transport:feed.diagnostics})};
}

export function decode(view){
 const columns=view?.table?.columns||[],ix={};for(const r of ['FileID','Month','MetricKey','Channel','SubChannel','Sector','Numerator','NumeratorMissing','FileMetadata','Bounds'])ix[r]=columns.findIndex(c=>c.roles?.[r]);
 const files=new Map(),rows=[],byFileMonthComponent=new Map(),delivered=new Map(),calendarKeys=new Map();let bounds=null;
 const diagnostics={receivedRows:0,repeatedDeliveryRows:0,metadataOnlyRows:0,blankVariantRows:0,distinctRows:0};
 const blank=v=>v===null||v===undefined;
 const dimension=(v,role,at)=>{if(blank(v))return '';if(typeof v!=='string')throw Error(`FM_FEED_DIMENSION: invalid ${role} type at row ${at+1}. Totals withheld.`);return v;};
 const token=v=>blank(v)?['blank']:['text',v];
 for(const [at,r] of (view?.table?.rows||[]).entries()){
  diagnostics.receivedRows++;
  if(r[ix.FileMetadata]){const f=JSON.parse(r[ix.FileMetadata]),old=files.get(f.id);if(old&&JSON.stringify(old)!==JSON.stringify(f))throw Error(`FM_FEED_METADATA: source metadata disagrees at row ${at+1}. Refresh the report; totals withheld.`);files.set(f.id,f);}
  if(r[ix.Bounds]){const next=JSON.parse(r[ix.Bounds]);if(bounds&&JSON.stringify(bounds)!==JSON.stringify(next))throw Error(`FM_FEED_BOUNDS: calendar metadata disagrees at row ${at+1}. Refresh the report; totals withheld.`);bounds=next;}
  // Metadata carrier rows are not observations. Keep their metadata above.
  const n=blank(r[ix.Numerator])?null:r[ix.Numerator],missing=blank(r[ix.NumeratorMissing])?null:r[ix.NumeratorMissing];
  if(n===null&&missing===null){diagnostics.metadataOnlyRows++;continue;}
  // Power BI DateTime is a client wall-clock calendar value. Zoned wire strings
  // must become Dates before reading local month fields, as in the working feed.
  // Slicing 2026-03-31T23:00Z to YYYY-MM turns an April BST month into March.
  let date=r[ix.Month];
  if(typeof date==='number'||(typeof date==='string'&&/T.*(?:Z|[+-]\d{2}:\d{2})$/.test(date)))date=new Date(date);
  const isDate=Object.prototype.toString.call(date)==='[object Date]';
  const dateIdentity=isDate?['datetime',date.getTime()]:token(date);
  if(isDate)date=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}`;else date=String(date||'').slice(0,7);
  const file=dimension(r[ix.FileID],'FileID',at),component=dimension(r[ix.MetricKey],'MetricKey',at);
  if(!file||!component||!/^\d{4}-(0[1-9]|1[0-2])$/.test(date))throw Error(`FM_FEED_GRAIN: invalid monthly identity at row ${at+1}. Totals withheld.`);
  const dims=['Channel','SubChannel','Sector'].map(role=>dimension(r[ix[role]],role,at));
  const rawDims=['Channel','SubChannel','Sector'].map(role=>token(r[ix[role]]));
  const queryKey=JSON.stringify([file,dateIdentity,component,...rawDims]);
  const previous=delivered.get(queryKey);
  if(previous){
   // These are already aggregated query rows, not raw fact transactions.
   // Count an exact delivery repeat once; never SUM or choose between conflicts.
   if(previous.row.n!==n||previous.row.missing!==missing)throw Error(`FM_FEED_CONFLICT: repeated aggregate disagrees at rows ${previous.at+1} and ${at+1}. Totals withheld.`);
   diagnostics.repeatedDeliveryRows++;continue;
  }
  const calendarKey=JSON.stringify([file,date,component,...rawDims]);
  const calendar=calendarKeys.get(calendarKey),dateSignature=JSON.stringify(dateIdentity);
  if(calendar&&calendar.dateSignature!==dateSignature)throw Error(`FM_FEED_MONTH_GRAIN: different source dates collapse into one month at rows ${calendar.at+1} and ${at+1}. Totals withheld.`);
  calendarKeys.set(calendarKey,{dateSignature,at});
  const businessKey=JSON.stringify([file,dateIdentity,component,...dims]);
  if(calendarKeys.has('business:'+businessKey))diagnostics.blankVariantRows++;
  calendarKeys.set('business:'+businessKey,true);
  const row={file,month:date,component,channel:dims[0],subchannel:dims[1],sector:dims[2],n,missing,queryKey};
  delivered.set(queryKey,{row,at});
  rows.push(row);const key=JSON.stringify([file,date,component]);if(!byFileMonthComponent.has(key))byFileMonthComponent.set(key,[]);byFileMonthComponent.get(key).push(row);
 }
 diagnostics.distinctRows=rows.length;
 return {files:[...files.values()],rows,byFileMonthComponent,bounds,diagnostics};
}
