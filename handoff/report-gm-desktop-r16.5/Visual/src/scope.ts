// @ts-nocheck
/** Source availability is independent of current sector ticks. Never infer it
 * from the whole-model dimension list or silently choose a non-ADS fallback. */
export function scopeIdentity(kind,value){let hash=14695981039346656037n;for(const ch of JSON.stringify(value)){hash^=BigInt(ch.codePointAt(0));hash=BigInt.asUintN(64,hash*1099511628211n);}return kind+'_'+hash.toString(16).padStart(16,'0');}
export function adsInfo(file){
 const match=/^(Plan[ _-]*)?ADS(?:[ _-]+(\d+))?$/i.exec(String(file.scenario||'').trim());
 if(!match)return null;const revision=match[2]===undefined?0:Number(match[2]);
 if(!Number.isSafeInteger(revision))return null;
 return {priority:match[2]!==undefined?1:match[1]?3:2,revision,modified:Date.parse(file.modifiedUtc||'')||0};
}
export function selectADS(cycles,available,drivers){
 const files=[],issues=[],affiliates=[...new Set(available.map(f=>f.affiliate))];
 for(const affiliate of affiliates)for(const cycle of cycles)for(const driver of drivers){
  const candidates=available.filter(f=>f.affiliate===affiliate&&f.cycle===cycle&&f.driver===driver&&adsInfo(f)).sort((a,b)=>{const x=adsInfo(a),y=adsInfo(b);return y.priority-x.priority||y.revision-x.revision||y.modified-x.modified||a.id.localeCompare(b.id);});
  if(!candidates.length){issues.push({affiliate,cycle,driver,status:'MISSING'});continue;}
  if(candidates.length>1){const a=adsInfo(candidates[0]),b=adsInfo(candidates[1]);if(a.priority===b.priority&&a.revision===b.revision&&a.modified===b.modified){issues.push({affiliate,cycle,driver,status:'AMBIGUOUS'});continue;}}
  files.push(candidates[0]);
 }
 return {files,issues};
}
export function scopeResolver(files,sectors,rows){
 const byFile=new Map(),sectorIds=new Map(sectors.map(s=>[JSON.stringify([s.driver,s.raw]),s.id])),fileById=new Map(files.map(f=>[f.id,f]));
 for(const r of rows){const f=fileById.get(r.file);if(!f)continue;if(!byFile.has(r.file))byFile.set(r.file,new Set());byFile.get(r.file).add(sectorIds.get(JSON.stringify([f.driver,r.sector])));}
 const cache=new Map();
 return state=>{
  const key=JSON.stringify([state.affiliates,state.cycles,state.fileMode||'ads',state.fileMode==='custom'?state.files:[]]);if(cache.has(key))return cache.get(key);
  const pool=files.filter(f=>state.affiliates?.includes(f.affiliate.toLowerCase())&&state.cycles?.includes(f.cycle));
  const candidates=state.fileMode==='custom'?pool.filter(f=>state.files?.includes(f.id)):pool.filter(f=>adsInfo(f));
  const driverIds=[...new Set(candidates.map(f=>f.driver))];
  const selected=state.fileMode==='custom'?{files:candidates,issues:[]}:selectADS(state.cycles||[],pool,driverIds);
  // Use the preferred sources' actual membership. Retired ADS revisions must
  // not introduce tiers. Keep unresolved cohorts visible so ambiguity cannot
  // silently disappear from a complete selected total.
  const unresolved=candidates.filter(f=>selected.issues.some(i=>i.status==='AMBIGUOUS'&&i.affiliate===f.affiliate&&i.cycle===f.cycle&&i.driver===f.driver));
  const ids=new Set([...selected.files,...unresolved].flatMap(f=>[...(byFile.get(f.id)||[])]));
  const excluded=[...new Set(pool.map(f=>f.driver))].filter(id=>!driverIds.includes(id));
  const result={driverIds,sectors:sectors.filter(s=>ids.has(s.id)),sources:selected.files,issues:selected.issues,excluded,mode:state.fileMode||'ads'};
  cache.set(key,result);return result;
 };
}
