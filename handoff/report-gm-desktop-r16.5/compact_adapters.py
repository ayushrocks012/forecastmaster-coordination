"""Focused production-only adapters; preserved approved HTML stays unchanged."""
def replace_span(text,start,end,new):
    assert text.count(start)==1 and text.count(end)==1,(start,end)
    a=text.index(start);b=text.index(end,a)
    return text[:a]+new+'\n '+text[b:]

def adapt(d,s,shell):
    d=replace_span(d,'function adsInfo(file)','function planFamily',"""function adsInfo(file){return sourceADSInfo(file);}
 function adsSelection(cycles,available=files,drivers=Object.keys(driverNames)){return selectADS(cycles,available,drivers);}""")
    d=replace_span(d,'function renderQuick()','function chartSeries',"""function renderQuick(){
  const scope=live.scope(state),selected=activeSectors(),drivers=selectedDrivers(),mode=state.combined?'total':state.view;
  $$('[data-graph-mode]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.graphMode===mode)));
  compactScope($('#fm-quick-scope'),{names:driverNames,driverIds:scope.driverIds,sectors:scope.sectors,selected:state.sectors,driverSelected:state.scopeDrivers,onChange:(ids,parents)=>{state.sectors=ids;state.scopeDrivers=parents;update();}});
  $('#fm-selected-scope').textContent=selected.length?drivers.map(id=>driverNames[id]).join(' + ')+' · '+selected.length+' of '+scope.sectors.filter(s=>state.scopeDrivers.includes(s.driver)).length+' available tiers · chart and table share this scope':'Choose a growth driver or forecast tier from the available sources';
  $('#fm-chart-scope').textContent=drivers.length+' growth drivers · '+selected.length+' forecast tiers'+(state.combined?' · selected total':'');
  $('#fm-graph-context').textContent=(!state.combined&&state.view==='hierarchy'?'Driver totals and selected sector lines · ':'Actuals and saved forecast · ')+state.trends[0]+'M trend uses the same selected scope';
  $('#fm-rank-period').closest('.fm-summary-context').hidden=(state.tableView==='driver'?drivers.length:selected.length)<2;
  renderAvailability();
 }
 function renderAvailability(){
  const node=$('#fm-availability'),wasOpen=node.open,issues=[];
  for(const combo of comboGroups())for(const metric of catalog.filter(m=>state.metrics.includes(m.id)))for(const window of new Set([...state.trends,...state.tableTrends])){
   const months=state.periods.flatMap(id=>periodMonths(id,combo,metric));if(state.trends.includes(window))for(let t=monthIndex(state.monthStart);t<=monthIndex(state.monthEnd);t++)months.push(t);
   if(!combo.files.some(f=>months.some(t=>t>cutoff(f,metric))))continue;
   const selected=activeSectors(),driverGroups=selectedDrivers().map(id=>selected.filter(s=>s.driver===id)),individual=selected.map(s=>[s]),scopes=[];
   if(state.combined)scopes.push(selected);else if(state.view==='driver')scopes.push(...driverGroups);else if(state.view==='sector')scopes.push(...individual);else scopes.push(...driverGroups,...individual);
   scopes.push(selected,...driverGroups);if(state.tableView==='sector'||state.tableView==='hierarchy')scopes.push(...individual);else scopes.push(...individual.filter(a=>state.expandedDrivers.includes(a[0].driver)));
   const seen=new Set();for(const subset of scopes){const key=subset.map(s=>s.id).join('|');if(!subset.length||seen.has(key))continue;seen.add(key);for(const issue of live.historyIssues(combo,subset,metric,window,state))issues.push({...issue,metric:metric.name});}
  }
  node.hidden=!issues.length;node.replaceChildren();if(!issues.length)return;
  const summary=document.createElement('summary'),list=document.createElement('ul');summary.textContent='Some trend comparisons unavailable · '+new Set(issues.map(i=>i.driver+'|'+i.sector)).size+' displayed scopes need complete history';
  for(const issue of issues.slice(0,10)){const item=document.createElement('li');item.textContent=(issue.driver?driverNames[issue.driver]+' · ':'')+issue.sector+' · '+issue.metric+': '+issue.window+'M history has '+issue.missing+' unavailable month'+(issue.missing===1?'':'s')+(issue.first?' ('+issue.first+' to '+issue.last+')':'')+'. The displayed scope needs a numeric monthly total throughout the training window.';list.append(item);}
  if(issues.length>10){const item=document.createElement('li');item.textContent=(issues.length-10)+' further incomplete comparisons. Narrow the driver/tier selection to inspect them.';list.append(item);}
  node.append(summary,list);node.open=wasOpen;
 }""")
    d=d.replace("function update(save=true){", "function update(save=true){\n  const eligible=new Set(live.scope(state).sectors.map(s=>s.id));if(state.sectors.some(id=>/^s[0-9]+$/.test(id))){state.sectors=[...eligible];state.expandedDrivers=[];state.scopeMigrated=true;}state.sectors=state.sectors.filter(id=>eligible.has(id));state.scopeDrivers=Array.isArray(state.scopeDrivers)?state.scopeDrivers.filter(id=>live.scope(state).driverIds.includes(id)):[...new Set(sectors.filter(s=>state.sectors.includes(s.id)).map(s=>s.driver))];state.sectors=state.sectors.filter(id=>sectors.some(s=>s.id===id&&state.scopeDrivers.includes(s.driver)));\n  for(const key of ['channels','subchannels'])dropdowns.get(key).node.hidden=!state.sections.includes('ef');")
    readout='<section class="fm-readout" id="fm-executive-readout" aria-label="Executive position" aria-live="polite"></section>'
    assert readout in d
    d=d.replace(readout,'').replace('<section class="fm-panel" aria-label="Demand comparison chart">',readout+'\n   <section class="fm-panel" aria-label="Demand comparison chart">')
    d=d.replace('<section class="fm-panel" aria-label="Demand comparison chart">','<details id="fm-availability" class="gm-availability" role="status" hidden></details>\n   <section class="fm-panel" aria-label="Demand comparison chart">')
    start=d.index('function renderExecutive()');end=d.index('function chartBenchmarkContext',start)
    executive=d[start:end].replace('periodOptions.filter(p=>state.periods.includes(p.id)).map(period=>','[period].map(period=>')
    executive=executive.replace("period.name+' · '+periodRangeLabel(months)+' · '+metric.name", "period.name+' · '+metric.name+(metric.unit==='£'?' · '+fx.label():'')")
    executive=executive.replace("${isPartialScope()?'Selected plan':'Total plan'}",'Plan')
    executive=executive.replace("Net ${delta==null?'variance':delta>0?'overcall':delta<0?'undercall':'variance'} vs ${trend}M", "${delta==null?'Variance':delta>0?'Overcall':delta<0?'Undercall':'Variance'} vs ${trend}M trend")
    executive=executive.replace('${escape(context)} · ${trend}M trend','${escape(context)}')
    d=d[:start]+executive+d[end:]
    d=d.replace('data-table-view="hierarchy" aria-pressed="false">Both</button>','data-table-view="hierarchy" aria-pressed="false">Drivers + sectors</button>')
    d=d.replace('+ Overcall / − Undercall · Plan minus trend · 6M / 12M / 24M are the actual-history windows used to fit each trend.','+ Overcall / − Undercall · Plan minus trend · Actual months are unchanged; trend variance applies to forecast months.')
    d=d.replace("state.sectors=sectors.map(s=>s.id);update();","state.sectors=live.scope(state).sectors.map(s=>s.id);update();")
    # Saved driver IDs are no authority for availability after a context change.
    d=d.replace("getSources:()=>pickedFiles()", "scopeOptions:()=>live.scope(state),getSources:()=>pickedFiles()")
    s=replace_span(s,'function renderScope()','function renderTree',"""function renderScope(){
  const scope=live.scope(state);
  compactScope($('#sb-scope'),{names:drivers,driverIds:scope.driverIds,sectors:scope.sectors,selected:state.sectors,driverSelected:state.scopeDrivers,onChange:(ids,parents)=>{state.sectors=ids;state.scopeDrivers=parents;update();}});
  $('#sb-scope-caption').textContent=state.sectors.length+' of '+scope.sectors.filter(s=>state.scopeDrivers.includes(s.driver)).length+' available tiers selected · graph and table share this scope';
 }""")
    s=s.replace("function update(save=true){", "function update(save=true){\n  const eligible=new Set(live.scope(state).sectors.map(s=>s.id));if(state.sectors.some(id=>/^s[0-9]+$/.test(id))){state.sectors=[...eligible];state.scopeMigrated=true;}state.sectors=state.sectors.filter(id=>eligible.has(id));state.scopeDrivers=Array.isArray(state.scopeDrivers)?state.scopeDrivers.filter(id=>live.scope(state).driverIds.includes(id)):[...new Set(sectors.filter(s=>state.sectors.includes(s.id)).map(s=>s.driver))];state.sectors=state.sectors.filter(id=>sectors.some(s=>s.id===id&&state.scopeDrivers.includes(s.driver)));")
    s=s.replace("state.sectors=sectors.map(s=>s.id);update();", "state.sectors=live.scope(state).sectors.map(s=>s.id);update();")
    s=s.replace("getTimings:()=>timings.slice()", "scopeOptions:()=>live.scope(state),getTimings:()=>timings.slice()")
    s=s.replace("data-channel-band=\"'+family.id+'\"", "data-channel-band=\"'+family.id+'\" data-channel-off=\"'+!on+'\"")
    shell=replace_span(shell,'function sources()','function refreshContext',"""function sources(){const s=apis[page].getState(),selected=new Set(apis.demand.sectors.filter(x=>s.sectors.includes(x.id)).map(x=>x.driver));return live.scope({...apis.demand.getState(),...s}).sources.filter(f=>selected.has(f.driver));}""")
    shell=shell.replace("'affiliates','cycles','sectors'","'affiliates','cycles','sectors','scopeDrivers'")
    shell=shell.replace("const details={};", "live.setScopeContext(()=>apis.demand.getState());\n const details={};")
    shell=shell.replace("const list=selected.length?", "const coverage=live.scope({...snap.demand,...s});\n  const list=selected.length?")
    shell=shell.replace("Object.values(details).forEach(d=>d.querySelector('[data-source-list]').innerHTML=list);", """const exclusions=coverage.excluded.length?'<div class="gm-coverage-note">'+esc(coverage.excluded.map(id=>names[id]).join(' · '))+' — '+(coverage.mode==='ads'?'no ADS source in this scope':'no selected custom source')+'. Not included in the selected total.</div>':'';
  const unresolved=coverage.issues.filter(i=>coverage.driverIds.includes(i.driver));
  const issues=(unresolved.length?'<div class="gm-coverage-note">'+esc(unresolved.map(i=>names[i.driver]+' · '+i.cycle+' · '+i.status).join(' / '))+' — affected complete totals remain unavailable.</div>':'')+(s.scopeMigrated?'<div class="gm-coverage-note">Legacy position-based selection was reset to available sources. Review the driver/tier choices.</div>':'');
  if($('#sb-plan-summary'))$('#sb-plan-summary').textContent=$('#fm-plan-summary').textContent;
  Object.values(details).forEach(d=>{d.querySelector('summary').textContent='Source details · '+coverage.driverIds.length+' available drivers'+(coverage.excluded.length?' · '+coverage.excluded.length+' without '+(coverage.mode==='ads'?'ADS':'a selected source'):'');d.querySelector('[data-source-list]').innerHTML=list+exclusions+issues;});""")
    for before,after in [('plot.getBoundingClientRect().width','plot.clientWidth'),('event.clientX-box.left','(event.clientX-box.left)/(box.width/plot.clientWidth)'),('event.clientY-box.top','(event.clientY-box.top)/(box.width/plot.clientWidth)')]:d=d.replace(before,after)
    for before,after in [('plot.getBoundingClientRect().width','plot.clientWidth'),('event.clientX-rect.left','(event.clientX-rect.left)/(rect.width/plot.clientWidth)'),('event.clientY-rect.top','(event.clientY-rect.top)/(rect.width/plot.clientWidth)')]:s=s.replace(before,after)
    return d,s,shell
