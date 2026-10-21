// @ts-nocheck
import * as d3 from "d3";
import { template } from "./template";
import DOMPurify from "dompurify";
function setHTML(el,markup){const dest=el instanceof HTMLTemplateElement?el.content:el;const isTable=el.tagName==="TABLE";const fragment=DOMPurify.sanitize(isTable?"<table>"+markup+"</table>":markup,{RETURN_DOM_FRAGMENT:true});dest.replaceChildren(...(isTable?Array.from(fragment.querySelector("table").childNodes):[fragment]));}
export function mount(container, initialFeed, initialState, onScope, onPersist){

  const root=container;
  const templateNode=document.createElement('template');setHTML(templateNode,template);
  const monthNames=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  let feed=initialFeed;
  let sourceCycles=[],versions=[],catalog={};
  const defaults={affiliate:'UK',cycle:'2026-07',driver:'Core Oral',sector:'all',channel:'all',subchannel:'all',family:'IMS / Market',metric:'ims-market-units',periodStart:36,periodEnd:59,reviewPeriods:null,reviewSchema:3,periodsFollowContext:true,monthsFollowCycle:true,selected:[],reference:'',hidden:[],fileSearch:'',filePage:0,selectedOnly:false,undoSelection:null};
  const apps=[];
  const saved=initialState?{modelContent:{state:initialState}}:null;
  function label(t){const x=Math.round(t);return monthNames[((x%12)+12)%12]+' '+String(2023+Math.floor(x/12)).slice(-2);}
  function fullLabel(t){return monthNames[((t%12)+12)%12]+' '+String(2023+Math.floor(t/12));}
  function windowLabel(start,end){const a=monthNames[((start%12)+12)%12],b=monthNames[((end%12)+12)%12];return start===end?a:a+'–'+b;}
  function monthISO(t){return String(2023+Math.floor(t/12))+'-'+String(((t%12)+12)%12+1).padStart(2,'0');}
  function cycleIndex(value){const [year,month]=value.split('-').map(Number);return (year-2023)*12+month-1;}
  function periodLabel(key){const [year,kind]=key.split(':');return year+' '+kind;}
  function migrate(value){const result=Object.assign({},value||{});if(result.cycle&&/^\d+$/.test(result.cycle))result.cycle=monthISO(36+Number(result.cycle));if(!Number.isInteger(result.periodStart)&&result.year){const first=(Number(result.year)-2023)*12;result.periodStart=first+Number(result.from||0);result.periodEnd=first+Number(result.to===undefined?11:result.to);}if(!Array.isArray(result.reviewPeriods)){result.reviewPeriods=null;result.periodsFollowContext=true;}result.reviewSchema=3;delete result.periodsFollowCycle;delete result.year;delete result.from;delete result.to;delete result.display;delete result.history;return result;}
  const previous=saved&&saved.modelContent;
  const oldChoices=previous&&(previous.state||(previous.layouts||[]).find(a=>a.id==='fm-planner')?.state||(previous.layouts||[])[0]?.state);
  const sharedState=Object.assign({},defaults,migrate(oldChoices));sharedState.selected=[...sharedState.selected];sharedState.hidden=[...sharedState.hidden];sharedState.reviewPeriods=sharedState.reviewPeriods===null?null:[...sharedState.reviewPeriods];
  let periodChange='',periodNotice='',requestedScope='',initialised=false;
  function esc(v){return String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
  function scope(){return {affiliate:sharedState.affiliate,cycle:sharedState.cycle,driver:sharedState.driver,profile:sharedState.profile||'Ext',metric:sharedState.metric,sector:sharedState.sector,channel:sharedState.channel,subchannel:sharedState.subchannel};}
  function scopeKey(s){return JSON.stringify(['affiliate','cycle','driver','profile','metric'].map(k=>s?.[k]||''));}
  function redraw(){apps.forEach(a=>a.render());}
  function sum(values){return values.reduce((a,b)=>a+b,0);}
  function fit(values){
    if(values.some(v=>v.y===null||!Number.isFinite(v.y)))return {a:null,b:null,value:()=>null};
    const n=values.length,mx=sum(values.map(v=>v.x))/n,my=sum(values.map(v=>v.y))/n;
    const den=sum(values.map(v=>(v.x-mx)**2));if(!den)return {a:null,b:null,value:()=>null};
    const b=sum(values.map(v=>(v.x-mx)*(v.y-my)))/den,a=my-b*mx;return {a,b,value:t=>a+b*t};
  }
  function save(){onPersist(JSON.parse(JSON.stringify(sharedState)));}
  function refreshInventory(){
    const colors=['--fm-plan','--fm-indi','--fm-anuja'];
    const all=feed.files||[],st=sharedState;
    if(!all.length||!feed.catalog?.length)return false;
    if(!initialised){
      const chosen=all.find(f=>f.affiliate===st.affiliate&&f.cycle===st.cycle&&f.driver===st.driver)||all[0];
      st.affiliate=chosen.affiliate;st.cycle=chosen.cycle;st.driver=chosen.driver;st.profile=st.profile||chosen.profile;
      initialised=true;
    }
    const choices=all.filter(f=>f.affiliate===st.affiliate);
    if(!choices.some(f=>f.cycle===st.cycle))st.cycle=choices.map(f=>f.cycle).sort().at(-1)||all[0].cycle;
    const cohort=choices.filter(f=>f.cycle===st.cycle);
    if(!cohort.some(f=>f.driver===st.driver))st.driver=cohort[0]?.driver||all[0].driver;
    const profiles=cohort.filter(f=>f.driver===st.driver).map(f=>f.profile);
    if(!profiles.includes(st.profile))st.profile=profiles[0];
    const records=cohort.filter(f=>f.driver===st.driver&&f.profile===st.profile).sort((a,b)=>{const rank=f=>/V18_Ext/i.test(f.filename)?0:/Indi_001/i.test(f.filename)?1:2;return rank(a)-rank(b)||a.filename.localeCompare(b.filename)||String(b.fullLabel||'').localeCompare(String(a.fullLabel||''));});
    versions=records.map((f,i)=>({...f,label:shortLabel(f)+(records.filter(x=>shortLabel(x)===shortLabel(f)).length>1?' · '+f.id.slice(0,6):''),color:colors[i%3],dash:i<3?null:['7 3','7 3 2 3','2 3'][Math.floor(i/3)%3]}));
    if(!versions.some(f=>f.id===st.reference)){st.reference=versions[0]?.id||'';st.selected=versions.slice(0,2).map(f=>f.id);}
    catalog={};for(const m of feed.catalog){const v={...m,denominator:m.aggregation==='RATIO'?'d':null,field:'n',numerator:'n'};(catalog[m.family]??=[]).push(v);}
    if(!catalog[st.family])st.family=Object.keys(catalog)[0];
    if(!catalog[st.family].some(m=>m.id===st.metric))st.metric=catalog[st.family][0].id;
    sourceCycles=[...new Set(choices.map(f=>f.cycle))].sort().map(c=>({cycle:c,first:cycleIndex(feed.bounds.first),last:cycleIndex(feed.bounds.last),revisionCount:records.length}));
    return true;
  }
  function shortLabel(f){
    let name=(f.filename||f.fullLabel||f.id).replace(/\.(xlsx|xlsm)$/i,'');
    if(name.includes(' · '))name=name.split(' · ')[0];
    const m=name.match(/_(?:IMS-[^_]+|IMS [^_]+)_(.+)$/i);if(m)return m[1];
    const demo=name.match(/_(V\d+(?:_Ext)?|Indi_\d+|Anuja_\d+)$/i);return demo?demo[1]:name;
  }
  function makeApp(id){
    const app=root.querySelector('#'+id);app.appendChild(templateNode.content.cloneNode(true));
    const old=saved&&saved.modelContent&&saved.modelContent.layouts&&saved.modelContent.layouts.find(a=>a.id===id);
    const state=sharedState;
    const design=Object.assign({chartHeight:278,fileWidth:246},old&&old.design||{});
    const api={id:id,state:state,design:design,render:render};apps.push(api);
    let current=null,pinned=false;
    const metric=()=>catalog[state.family].find(m=>m.id===state.metric)||catalog[state.family][0];
    const source=()=>sourceCycles.find(c=>c.cycle===state.cycle)||sourceCycles.find(c=>c.cycle===defaults.cycle);
    const cutoff=()=>{const ref=versions.find(f=>f.id===state.reference);const value=ref?.[metric().cutoffFamily==='EF'?'ef':'ims'];return value&&/^\d{4}-\d{2}$/.test(value)?cycleIndex(value):null;};
    const period=()=>({start:state.periodStart,end:state.periodEnd});
    const periodName=()=>state.periodStart%12===0&&state.periodEnd%12===11&&Math.floor(state.periodStart/12)===Math.floor(state.periodEnd/12)?'FY '+String(2023+Math.floor(state.periodStart/12)):label(state.periodStart)+'–'+label(state.periodEnd);
    const availableVersions=()=>versions.slice(0,source().revisionCount);
    const picked=()=>availableVersions().filter(v=>state.selected.includes(v.id));
    function amounts(t,v){
      const row=feed.values.get(v+'|'+monthISO(t));if(!row)return {n:null,d:null};
      const parts=(row.parts||[row]).filter(p=>!row.parts||['channel','subchannel','sector'].every(k=>state[k]==='all'||p[k]===state[k]));
      // The workbook sums reported numeric members. An inactive Product may be blank.
      // MissingCells remains a coverage diagnostic; it is not a whole-month veto.
      // No reported numeric member means unavailable, never a fabricated zero.
      const total=k=>{if(parts.some(p=>p[k]!==null&&p[k]!==undefined&&(typeof p[k]!=='number'||!Number.isFinite(p[k]))))return null;const reported=parts.map(p=>p[k]).filter(v=>typeof v==='number'&&Number.isFinite(v));return reported.length?sum(reported):null;};
      return {n:total('n'),d:total('d')};
    }
    function sourceCoverage(){
      const ids=new Set([state.reference,...picked().map(v=>v.id)]);let blankMembers=false;
      for(const [key,row] of feed.values){const split=key.lastIndexOf('|');if(!ids.has(key.slice(0,split)))continue;const t=cycleIndex(key.slice(split+1));if(t<Math.min(state.periodStart,current.end-23)||t>state.periodEnd)continue;const parts=(row.parts||[row]).filter(p=>!row.parts||['channel','subchannel','sector'].every(k=>state[k]==='all'||p[k]===state[k]));if(parts.some(p=>p.nm>0||(metric().denominator&&p.dm>0))){blankMembers=true;break;}}
      const notes=[];if(blankMembers)notes.push('Source includes blank members: totals sum reported numeric values, as in the workbook. Entirely unreported months stay blank.');if(current.fit12.a===null)notes.push('Trend 12M unavailable: its training window has an unreported month.');if(current.fit24.a===null)notes.push('Trend 24M unavailable: its training window has an unreported month.');return notes.join(' ');
    }
    function raw(t,v){const a=amounts(t,v);return metric().denominator?(a.n===null||a.d===null||a.d===0?null:a.n/a.d):a.n;}
    function isPercent(){return !!metric().denominator;}
    function unit(){return isPercent()?'%':metric().unit;}
    function number(v,compact=true,as=unit()){if(v===null||v===undefined||!Number.isFinite(v))return '—';if(as==='%')return (v*100).toFixed(2)+'%';if(as==='pp')return (v*100).toFixed(2)+' pp';const abs=Math.abs(v),prefix=as==='£'?'£':'';return prefix+(compact&&abs>=1e6?(v/1e6).toFixed(2)+'m':compact&&abs>=1000?(v/1000).toFixed(1)+'k':v.toLocaleString('en-GB',{maximumFractionDigits:0}));}
    function signed(v,as=unit()){return v===null||!Number.isFinite(v)?'—':(v<0?'−':v>0?'+':'')+number(Math.abs(v),true,as);}
    function native(type,t){if(current.end===null)return null;if(t<=current.end)return raw(t,state.reference);if(type==='t12')return current.fit12.value(t);if(type==='t24')return current.fit24.value(t);return raw(t,type);}
    function shown(type,t){return native(type,t);}
    function totalNative(type,start,end,actualOnly=false){const m=metric();let numerator=0,denominator=0;for(let t=start;t<=end;t++){if(actualOnly&&t>current.end)continue;const value=native(type,t);if(value===null||!Number.isFinite(value))return null;if(m.denominator){const own=t>current.end&&!['t12','t24'].includes(type);const weight=amounts(t,own?type:state.reference).d;if(weight===null||!Number.isFinite(weight))return null;numerator+=value*weight;denominator+=weight;}else numerator+=value;}return m.denominator?(denominator===0?null:numerator/denominator):numerator;}
    function shownTotal(type,actualOnly=false){const p=period(),last=actualOnly?Math.min(p.end,current.end):p.end;if(last<p.start)return null;return totalNative(type,p.start,last,actualOnly);}
    function selectOptions(field,items){const el=app.querySelector('[data-field='+field+']');el.replaceChildren();for(const [value,label] of items)el.add(new Option(label,value));}
    function configure(){
      const all=feed.files;
      selectOptions('affiliate',[...new Set(all.map(f=>f.affiliate))].sort().map(x=>[x,x==='UK'?'United Kingdom':x==='IE'?'Ireland':x]));
      selectOptions('cycle',sourceCycles.map(c=>[c.cycle,fullLabel(cycleIndex(c.cycle))]));
      selectOptions('driver',[...new Set(all.filter(f=>f.affiliate===state.affiliate&&f.cycle===state.cycle).map(f=>f.driver))].sort().map(x=>[x,x]));
      selectOptions('family',Object.keys(catalog).map(x=>[x,x]));
      selectOptions('metric',catalog[state.family].map(m=>[m.id,m.label]));
      const dims=feed.dimensions||[];
      for(const field of ['sector','channel','subchannel']){
        const rows=field==='subchannel'&&state.channel!=='all'?dims.filter(d=>d.channel===state.channel):dims;
        const opts=[...new Set(rows.map(d=>d[field]))].sort();
        selectOptions(field,[['all',field==='sector'?'All sectors':field==='channel'?'All channels':'All subchannels'],...opts.map(x=>[x,x||'(Blank)'])]);
      }
      const bounds=source();state.periodStart=Math.max(bounds.first,Math.min(bounds.last,state.periodStart));state.periodEnd=Math.max(state.periodStart,Math.min(bounds.last,state.periodEnd));
      const ids=new Set(availableVersions().map(v=>v.id));state.selected=state.selected.filter(v=>ids.has(v));
      app.querySelectorAll('[data-field]').forEach(el=>el.value=state[el.dataset.field]);
      app.querySelectorAll('[data-month]').forEach(el=>{el.value=monthISO(state[el.dataset.month]);el.min=monthISO(bounds.first);el.max=monthISO(bounds.last);});
      const profile=app.querySelector('.fm-profile');profile.replaceChildren();[...new Set(all.filter(f=>f.affiliate===state.affiliate&&f.cycle===state.cycle&&f.driver===state.driver).map(f=>f.profile))].forEach(p=>profile.add(new Option(p,p)));profile.value=state.profile;
      const end=cutoff(),points=n=>Array.from({length:n},(_,i)=>{const t=end-n+1+i;return {x:t,y:end===null?null:raw(t,state.reference)};});
      current={end,fit12:fit(points(12)),fit24:fit(points(24))};
    }
    function filename(v){return v.fullLabel||v.path||v.filename||v.id;}
    function latestCopy(v){return versions.filter(x=>x.path&&x.path===v?.path).sort((a,b)=>String(b.fullLabel||'').localeCompare(String(a.fullLabel||'')))[0]||v;}
    function files(){
      const all=availableVersions(),query=state.fileSearch.trim().toLocaleLowerCase(),matching=all.filter(v=>(!state.selectedOnly||state.selected.includes(v.id))&&(!query||filename(v).toLocaleLowerCase().includes(query))),pageSize=3,pageCount=Math.max(1,Math.ceil(matching.length/pageSize));state.filePage=Math.max(0,Math.min(pageCount-1,state.filePage));const first=state.filePage*pageSize;
      app.querySelector('[data-file-action=latest]').disabled=!versions.some(v=>(state.selected.includes(v.id)||v.id===state.reference)&&latestCopy(v).id!==v.id);app.querySelector('[data-file-action=clear]').disabled=!state.selected.length;app.querySelector('[data-file-action=undo]').hidden=!state.undoSelection;app.querySelector('[data-selected-only]').checked=state.selectedOnly;
      app.querySelector('.fm-files-count').textContent=all.length+' available · '+picked().length+' plotted';app.querySelector('.fm-file-query').value=state.fileSearch;app.querySelector('.fm-file-page-count').textContent=matching.length?(first+1)+'–'+Math.min(first+pageSize,matching.length)+' of '+matching.length:state.selectedOnly&&!state.selected.length?'No selected files':'No matching files';app.querySelector('[data-file-page=previous]').disabled=state.filePage===0;app.querySelector('[data-file-page=next]').disabled=state.filePage===pageCount-1;
      const list=app.querySelector('.fm-file-list');list.replaceChildren();matching.slice(first,first+pageSize).forEach(v=>{
        const row=document.createElement('div');row.className='fm-file'+(state.reference===v.id?' is-reference':'');
        const plot=document.createElement('input');plot.type='checkbox';plot.checked=state.selected.includes(v.id);plot.setAttribute('aria-label','Plot forecast '+v.label);plot.addEventListener('change',()=>{state.selected=plot.checked?Array.from(new Set(state.selected.concat(v.id))):state.selected.filter(x=>x!==v.id);state.hidden=state.hidden.filter(x=>x!==v.id);state.undoSelection=null;redraw();save();});
        const base=document.createElement('input');base.type='radio';base.name='fm-base-'+id;base.checked=state.reference===v.id;base.setAttribute('aria-label','Use '+esc(v.label)+' actuals and trend reference');base.addEventListener('change',()=>{state.reference=v.id;redraw();save();});
        const text=document.createElement('div');setHTML(text,'<div class="fm-version"><i style="background:var('+v.color+')"></i><span>'+esc(v.label)+'</span></div><div class="fm-file-name"></div>');text.querySelector('.fm-file-name').textContent=v.path||v.filename||filename(v);text.title=filename(v);const imported=String(v.fullLabel||'').match(/ · Imported ([^·]+) · /);if(imported){const stamp=document.createElement('small');stamp.className='fm-import-time';const when=new Date(imported[1].trim());stamp.textContent='Imported '+(Number.isNaN(when.getTime())?imported[1].trim():when.toLocaleString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})+' UTC')+' · '+v.id.slice(0,8);text.appendChild(stamp);}if(state.reference===v.id){const note=document.createElement('div');note.className='fm-reference-label';note.textContent='Actuals + trend reference';text.appendChild(note);}row.append(plot,base,text);list.appendChild(row);
      });
    }
    function periodOptions(){
      const p=period(),firstYear=2023+Math.floor(p.start/12),lastYear=2023+Math.floor(p.end/12),split=((current.end%12)+12)%12+1,out=[];
      for(let year=firstYear;year<=lastYear;year++){
        const first=(year-2023)*12,last=first+11;
        for(const kind of ['FY','YTD','YTG']){
          const start=kind==='YTG'?first+split:first,end=kind==='YTD'?first+split-1:last;
          out.push({key:year+':'+kind,year:year,kind:kind,start:start,end:end,available:start<=end&&start>=source().first&&end<=source().last});
        }
      }
      return out;
    }
    function syncPeriods(){
      current.periodOptions=periodOptions();const valid=new Set(current.periodOptions.map(p=>p.key)),cycleYear=Number(state.cycle.slice(0,4)),suggested=current.periodOptions.filter(p=>p.kind==='FY'||p.year===cycleYear).map(p=>p.key),previous=state.reviewPeriods||[],removed=previous.filter(key=>!valid.has(key));
      if(state.reviewPeriods===null||state.periodsFollowContext)state.reviewPeriods=suggested;
      else{state.reviewPeriods=current.periodOptions.filter(p=>previous.includes(p.key)).map(p=>p.key);}
      if(periodChange){periodNotice=periodChange==='cycle'?'Comparison selections cleared for '+fullLabel(cycleIndex(state.cycle))+'. Choose periods from the refreshed list.':removed.length?'Removed '+removed.map(periodLabel).join(', ')+' · no longer valid for '+(periodChange==='months'?'the selected month range':'this measure’s actuals cutoff')+'.':'';periodChange='';}
    }
    function reviewData(){return state.reviewPeriods.map(key=>{const option=current.periodOptions.find(p=>p.key===key),{start,end,kind,available}=option,value=type=>available?totalNative(type,start,end):null,b12=value('t12'),b24=value('t24');return {key:key,label:periodLabel(key),kind:kind,start:start,end:end,available:available,actualOnly:available&&end<=current.end,window:available?windowLabel(start,end):'No months',benchmark12:b12,benchmark24:b24,files:picked().map(v=>{const plan=value(v.id),delta12=plan===null||b12===null?null:plan-b12,delta24=plan===null||b24===null?null:plan-b24;return {id:v.id,label:v.label,plan:plan,delta12:delta12,delta24:delta24,relative12:delta12===null||b12===null||b12===0?null:delta12/b12,relative24:delta24===null||b24===null||b24===0?null:delta24/b24};})};});}
    function reviewControls(){
      const chips=app.querySelector('.fm-period-chips');chips.replaceChildren();state.reviewPeriods.forEach(key=>{const button=document.createElement('button');button.type='button';button.className='fm-period-chip cursor-interaction';button.textContent=periodLabel(key)+' ×';button.setAttribute('aria-label','Remove '+periodLabel(key));button.addEventListener('click',()=>{state.reviewPeriods=state.reviewPeriods.filter(p=>p!==key);state.periodsFollowContext=false;periodNotice='';redraw();save();});chips.appendChild(button);});
      const add=app.querySelector('.fm-add-period');add.replaceChildren(new Option('Add period…',''));current.periodOptions.forEach(option=>{const item=new Option(periodLabel(option.key),option.key);item.disabled=state.reviewPeriods.includes(option.key);add.appendChild(item);});add.disabled=current.periodOptions.every(option=>state.reviewPeriods.includes(option.key));add.value='';add.setAttribute('aria-label','Add comparison period');
      const status=app.querySelector('.fm-period-status');status.textContent=periodNotice;status.hidden=!periodNotice;
    }
    function summary(){
      reviewControls();app.querySelector('.fm-calls-period').textContent=(metric().cutoffFamily==='IMS'?'IMS':'Ex-factory')+' actuals: '+fullLabel(current.end)+' · '+unit();
      const table=app.querySelector('.fm-period-table'),diffUnit=isPercent()?'pp':unit();let html='<thead><tr><th scope="col">Period</th><th scope="col">Months</th><th scope="col">File</th><th scope="col">Actuals + plan</th><th scope="col">Trend 12M</th><th scope="col">Δ 12M'+(isPercent()?' (pp)':'')+'</th><th scope="col">Δ 12M %</th><th scope="col">Trend 24M</th><th scope="col">Δ 24M'+(isPercent()?' (pp)':'')+'</th><th scope="col">Δ 24M %</th></tr></thead><tbody>';
      current.review.forEach(p=>p.files.forEach((file,i)=>{html+='<tr class="'+(i===0?'fm-period-start':'')+'" data-review-period="'+p.key+'" data-file="'+esc(file.id)+'">';if(i===0)html+='<td class="fm-period-name" rowspan="'+p.files.length+'">'+p.label+'</td><td class="fm-window" rowspan="'+p.files.length+'">'+p.window+'</td>';html+='<td class="fm-file-cell">'+esc(file.label)+'</td><td>'+number(file.plan)+'</td><td>'+number(p.benchmark12)+'</td><td class="fm-delta">'+signed(file.delta12,diffUnit)+'</td><td>'+signed(file.relative12,'%')+'</td><td>'+number(p.benchmark24)+'</td><td class="fm-delta">'+signed(file.delta24,diffUnit)+'</td><td>'+signed(file.relative24,'%')+'</td></tr>';}));
      if(!picked().length||!state.reviewPeriods.length)html+='<tr><td colspan="10" class="fm-empty">'+(!picked().length?'Select at least one forecast file.':'Choose comparison periods for the '+fullLabel(cycleIndex(state.cycle))+' cycle.')+'</td></tr>';
      const split=((current.end%12)+12)%12;setHTML(table,html+'</tbody>');app.querySelector('.fm-calls-note').textContent='Same calendar split in every year: YTD Jan–'+monthNames[split]+' · YTG '+(split===11?'no remaining months':monthNames[split+1]+'–Dec')+' · Values use actuals or forecasts from the selected source · Δ: + overcall / − undercall · No total across overlapping periods.';
    }
    function matrix(){
      const p=period(),rows=[{id:'actual',label:'Actuals · '+versions.find(v=>v.id===state.reference).label,actual:true}];picked().forEach(v=>rows.push({id:v.id,label:'Plan · '+v.label}));rows.push({id:'t12',label:'Trend 12M'},{id:'t24',label:'Trend 24M'});
      let html='<thead><tr><th>Series</th><th class="fm-total">'+periodName()+'</th>';for(let t=p.start;t<=p.end;t++)html+='<th class="'+(t>current.end?'fm-forecast-cell':'')+'">'+label(t)+(t<=current.end?' A':' F')+'</th>';html+='</tr></thead><tbody>';
      rows.forEach(row=>{html+='<tr data-monthly-series="'+esc(row.id)+'"><td>'+esc(row.label)+'</td><td class="fm-total">'+(row.actual?'Actual ':'')+number(shownTotal(row.actual?state.reference:row.id,!!row.actual))+'</td>';for(let t=p.start;t<=p.end;t++){const v=row.actual?(t<=current.end?shown(state.reference,t):null):shown(row.id,t);html+='<td data-month-index="'+t+'" class="'+(t>current.end?'fm-forecast-cell':'')+'">'+number(v)+'</td>';}html+='</tr>';});setHTML(app.querySelector('.fm-month-table'),html+'</tbody>');
      app.querySelector('.fm-matrix-unit').textContent=metric().denominator?'Weighted share %':metric().unit;
      app.querySelector('.fm-matrix-note').textContent='A = actual · F = forecast. Every Plan/Trend row uses Base actuals through '+label(current.end)+', then its own forecast/projection. '+(metric().denominator?'Share totals use market weights.':'Monthly values reconcile with their period totals.');
    }
    function context(){
      setHTML(app.querySelector('.fm-context'),'<span><strong>Actuals through '+label(current.end)+'</strong></span><span>Forecast from '+label(current.end+1)+'</span>');
      app.querySelector('.fm-chart-title').textContent=metric().label;app.querySelector('.fm-chart-unit').textContent=unit();
      setHTML(app.querySelector('.fm-plot-note'),'<span>12M fit: '+label(current.end-11)+'–'+label(current.end)+'</span><span>24M fit: '+label(current.end-23)+'–'+label(current.end)+'</span><span>Base: '+esc(versions.find(v=>v.id===state.reference).label)+'</span>');
      const coverage=sourceCoverage();if(coverage){const note=document.createElement('span');note.className='fm-coverage-note';note.textContent=coverage;app.querySelector('.fm-plot-note').appendChild(note);}
      app.querySelector('.fm-weights-note').textContent=metric().denominator?'Share basis: weighted totals; each plan uses its own future denominator':'Totals: one source vintage per forecast · linear 12M / 24M benchmarks';
    }
    function chart(){
      const body=app.querySelector('.fm-plot'),width=body.clientWidth,height=body.clientHeight;if(width<130||height<140)return;
      pinned=false;const tip=body.querySelector('.fm-tip');tip.hidden=true;d3.select(body).selectAll('svg').remove();const p=period();const start=Math.min(p.start,Math.max(source().first,current.end-11));const end=p.end;
      const defs=[{id:'actual',name:'Actuals',color:'--fm-actual',dash:null}];picked().forEach(v=>defs.push({id:v.id,name:v.label,color:v.color,dash:v.dash||null}));defs.push({id:'t12',name:'Trend 12M',color:'--fm-t12',dash:'8 4'},{id:'t24',name:'Trend 24M',color:'--fm-t24',dash:'2 4'});
      const legend=app.querySelector('.fm-legend');legend.replaceChildren();defs.forEach(s=>{const b=document.createElement('button');b.type='button';b.className='cursor-interaction';b.setAttribute('aria-pressed',String(!state.hidden.includes(s.id)));b.setAttribute('aria-label','Show '+esc(s.name)+' on chart');const sw=document.createElement('i');sw.style.borderTopColor='var('+s.color+')';sw.style.borderTopStyle=s.dash?'dashed':'solid';b.append(sw,document.createTextNode(s.name));b.addEventListener('click',()=>{state.hidden=state.hidden.includes(s.id)?state.hidden.filter(x=>x!==s.id):state.hidden.concat(s.id);redraw();save();});legend.appendChild(b);});
      const series=defs.filter(s=>!state.hidden.includes(s.id)).map(s=>Object.assign({},s,{points:[]}));series.forEach(s=>{for(let t=start;t<=end;t++){if(s.id==='actual'?t<=current.end:t>=current.end){const value=shown(s.id==='actual'?state.reference:s.id,t);s.points.push({x:t,y:value});}}});
      const values=series.flatMap(s=>s.points.filter(v=>v.y!==null&&Number.isFinite(v.y)).map(v=>v.y)),extent=d3.extent(values.length?values:[0,1]),spread=Math.max(extent[1]-extent[0],Math.abs(extent[1])*.08,.00001),m={left:64,right:16,top:23,bottom:44};const x=d3.scaleLinear().domain([start,end===start?end+1:end]).range([m.left+3,width-m.right-3]);const y=d3.scaleLinear().domain([extent[0]-spread*.12,extent[1]+spread*.15]).nice(5).range([height-m.bottom-3,m.top+3]);
      const color=k=>'var('+k+')',svg=d3.select(body).append('svg').attr('viewBox','0 0 '+width+' '+height).attr('role','img').attr('aria-label',metric().label+' actuals, separate forecast revisions, and linear 12 and 24 month projections');svg.append('title').text(metric().label+' review');
      svg.append('defs').append('clipPath').attr('id','fm-clip-'+id).append('rect').attr('x',m.left).attr('y',m.top).attr('width',width-m.left-m.right).attr('height',height-m.top-m.bottom);svg.append('rect').attr('data-chart-frame','').attr('x',m.left).attr('y',m.top).attr('width',width-m.left-m.right).attr('height',height-m.top-m.bottom).attr('fill','none').attr('stroke',color('--fm-line'));
      const axisFormat=v=>isPercent()?(v*100).toFixed(0)+'%':Math.abs(v)>=1e6?(v/1e6).toFixed(1)+'m':Math.abs(v)>=1000?(v/1000).toFixed(1)+'k':v.toFixed(0);const maxTicks=width<390?4:width<570?5:7,step=Math.max(1,Math.ceil((end-start+1)/maxTicks));const ticks=d3.range(start,end+1,step);
      svg.append('g').attr('transform','translate(0,'+(height-m.bottom)+')').call(d3.axisBottom(x).tickValues(ticks).tickFormat(label)).call(g=>g.selectAll('text').attr('dy','1em'));svg.append('g').attr('transform','translate('+m.left+',0)').call(d3.axisLeft(y).ticks(4).tickFormat(axisFormat));
      svg.append('text').attr('class','axis-title').attr('data-axis','y').attr('x',m.left).attr('y',12).text(unit());svg.append('text').attr('class','axis-title').attr('data-axis','x').attr('x',(m.left+width-m.right)/2).attr('y',height-2).attr('text-anchor','middle').text('Demand month');
      const plot=svg.append('g').attr('clip-path','url(#fm-clip-'+id+')');if(current.end>=start&&current.end<end){const fx=x(current.end+.5);plot.append('rect').attr('x',fx).attr('y',m.top).attr('width',Math.max(0,width-m.right-fx)).attr('height',height-m.top-m.bottom).attr('fill',color('--fm-future'));plot.append('line').attr('x1',fx).attr('x2',fx).attr('y1',m.top).attr('y2',height-m.bottom).attr('stroke',color('--fm-muted')).attr('stroke-dasharray','3 4');svg.append('text').attr('x',fx+6).attr('y',m.top+12).text(width-fx>75?'Forecast':'F');}
      const path=d3.line().defined(v=>v.y!==null&&Number.isFinite(v.y)).x(v=>x(v.x)).y(v=>y(v.y));series.forEach(s=>{plot.append('path').datum(s.points).attr('data-series',s.id).attr('fill','none').attr('stroke',color(s.color)).attr('stroke-width',s.id==='actual'?2.5:2).attr('stroke-dasharray',s.dash).attr('d',path);if(s.points.length===1)plot.append('circle').attr('cx',x(s.points[0].x)).attr('cy',y(s.points[0].y)).attr('r',3).attr('fill',color(s.color));});
      if(!values.length)svg.append('text').attr('x',(width+m.left)/2).attr('y',height/2).attr('text-anchor','middle').text('Select a chart series');
      const hover=plot.append('g').style('display','none'),guide=hover.append('line').attr('data-chart-hover-guide','').attr('y1',m.top).attr('y2',height-m.bottom).attr('stroke',color('--fm-muted'));
      function show(event){const pos=d3.pointer(event,svg.node()),t=Math.round(Math.max(start,Math.min(end,x.invert(pos[0]))));guide.attr('x1',x(t)).attr('x2',x(t));hover.selectAll('circle').remove();let html='<strong>'+label(t)+'</strong>',count=0;series.forEach(s=>{const a=s.points;if(!a.length||t<a[0].x||t>a[a.length-1].x)return;const point=a.find(p=>p.x===Math.round(t));if(!point||point.y===null||!Number.isFinite(point.y))return;const value=point.y;hover.append('circle').attr('data-chart-hover-marker','').attr('cx',x(t)).attr('cy',y(value)).attr('r',3).attr('fill',color(s.color));html+='<div><span>'+esc(s.name)+'</span><span>'+number(value,false)+'</span></div>';count++;});if(!count){tip.hidden=true;hover.style('display','none');return;}hover.style('display',null);setHTML(tip,html);tip.hidden=false;tip.style.left=Math.max(4,Math.min(width-tip.offsetWidth-4,pos[0]+12))+'px';tip.style.top=Math.max(3,Math.min(height-tip.offsetHeight-4,pos[1]-tip.offsetHeight-10))+'px';}
      svg.append('rect').attr('data-chart-hit','').attr('data-chart-hover-overlay','cross-series').attr('x',m.left).attr('y',m.top).attr('width',width-m.left-m.right).attr('height',height-m.top-m.bottom).attr('fill','transparent').on('pointermove',event=>{if(!pinned)show(event);}).on('pointerleave',()=>{if(!pinned){tip.hidden=true;hover.style('display','none');}}).on('pointerdown',event=>{pinned=!pinned;show(event);});
    }
    function render(){
      if(!refreshInventory())return;
      app.style.setProperty('--fm-chart-height',design.chartHeight+'px');app.style.setProperty('--fm-side',design.fileWidth+'px');configure();const requested=scopeKey(scope()),actual=scopeKey(feed.context);
      if(requested!==actual){files();showLoading('Loading monthly aggregates for this selection…');if(requestedScope!==requested){requestedScope=requested;onScope(scope());}return;}
      requestedScope=requested;showLoading('');
      if(current.end===null){showLoading('This source has no explicit actuals cutoff for the selected measure. Choose another Base file.');files();return;}
      syncPeriods();current.review=reviewData();files();context();summary();matrix();chart();const p=period();
      api.snapshot={sourceCycle:state.cycle,cutoff:current.end,metric:metric().id,unit:unit(),fit12:{a:current.fit12.a,b:current.fit12.b,start:current.end-11,end:current.end},fit24:{a:current.fit24.a,b:current.fit24.b,start:current.end-23,end:current.end},benchmark12:shownTotal('t12'),benchmark24:shownTotal('t24'),plans:picked().map(v=>({id:v.id,value:shownTotal(v.id)})),period:p,periodOptions:current.periodOptions,review:current.review,months:Array.from({length:p.end-p.start+1},(_,i)=>{const t=p.start+i;return {t:t,weight:metric().denominator?amounts(t,state.reference)[metric().denominator]:1,trend12:native('t12',t),trend24:native('t24',t),plans:picked().map(v=>({id:v.id,value:native(v.id,t)}))};})};
    }
    const profile=document.createElement('select');profile.className='fm-profile';profile.setAttribute('aria-label','Source profile');app.querySelector('.fm-file-help').appendChild(profile);
    profile.addEventListener('change',()=>{state.profile=profile.value;state.reference='';state.selected=[];state.undoSelection=null;redraw();save();});
    app.querySelectorAll('[data-field]').forEach(el=>el.addEventListener('change',()=>{
      state[el.dataset.field]=el.value;const field=el.dataset.field;
      if(['affiliate','cycle','driver'].includes(field)){state.reference='';state.selected=[];state.undoSelection=null;state.filePage=0;}
      if(field==='cycle'){periodChange='cycle';state.reviewPeriods=[];state.periodsFollowContext=false;const first=Math.floor(cycleIndex(state.cycle)/12)*12;if(state.monthsFollowCycle){state.periodStart=first;state.periodEnd=first+11;}}
      if(field==='channel')state.subchannel='all';
      if(field==='family')state.metric=catalog[state.family][0].id;
      if(['family','metric'].includes(field))periodChange='measure';
      redraw();save();
    }));
    app.querySelectorAll('[data-month]').forEach(el=>el.addEventListener('change',()=>{if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(el.value)){redraw();return;}const value=cycleIndex(el.value);if(value===state[el.dataset.month])return;if(value<source().first||value>source().last){redraw();return;}state.monthsFollowCycle=false;state[el.dataset.month]=value;if(state.periodStart>state.periodEnd){if(el.dataset.month==='periodStart')state.periodEnd=value;else state.periodStart=value;}periodChange='months';redraw();save();}));
    app.querySelector('.fm-add-period').addEventListener('change',event=>{const key=event.target.value;if(current.periodOptions.some(p=>p.key===key)&&!state.reviewPeriods.includes(key)){state.reviewPeriods.push(key);state.periodsFollowContext=false;periodNotice='';redraw();save();}});
    app.querySelector('.fm-file-query').addEventListener('input',event=>{state.fileSearch=event.target.value;state.filePage=0;redraw();save();});
    app.querySelectorAll('[data-file-page]').forEach(button=>button.addEventListener('click',()=>{state.filePage+=button.dataset.filePage==='next'?1:-1;redraw();save();}));
    app.querySelector('[data-selected-only]').addEventListener('change',event=>{state.selectedOnly=event.target.checked;state.filePage=0;redraw();save();});
    app.querySelectorAll('[data-file-action]').forEach(button=>button.addEventListener('click',()=>{
      if(button.dataset.fileAction==='latest'){state.undoSelection={ids:[...state.selected],hidden:[...state.hidden],reference:state.reference};state.selected=[...new Set(picked().map(v=>latestCopy(v).id))];state.reference=latestCopy(versions.find(v=>v.id===state.reference))?.id||state.reference;state.filePage=0;}
      if(button.dataset.fileAction==='clear'&&state.selected.length){state.undoSelection={ids:[...state.selected],hidden:[...state.hidden]};state.selected=[];}
      if(button.dataset.fileAction==='undo'&&state.undoSelection){if(state.undoSelection.reference)state.reference=state.undoSelection.reference;state.selected=[...state.undoSelection.ids];state.hidden=[...state.undoSelection.hidden];state.undoSelection=null;}
      if(button.dataset.fileAction==='reference'){state.selected=[state.reference];state.hidden=state.hidden.filter(key=>key!==state.reference);state.fileSearch='';state.undoSelection=null;}
      state.filePage=0;redraw();save();
    }));
    render();const observer=new ResizeObserver(()=>{if(scopeKey(scope())===scopeKey(feed.context))chart();});observer.observe(app.querySelector('.fm-plot'));api.destroy=()=>observer.disconnect();
  }
  const appNode=document.createElement('div');appNode.className='fm-app fm-meeting';appNode.id='fm-meeting';root.appendChild(appNode);
  const loading=document.createElement('div');loading.className='fm-loading';loading.hidden=true;loading.setAttribute('role','status');root.prepend(loading);
  function showLoading(message){loading.textContent=message;loading.hidden=!message;appNode.querySelectorAll('.fm-chart,.fm-calls,.fm-matrix').forEach(n=>{n.style.opacity=message?'.32':'';n.style.pointerEvents=message?'none':'';});}
  makeApp('fm-meeting');
  root.fmPreview={apps:apps};

  return {update(next){feed=next;redraw();},getState(){return JSON.parse(JSON.stringify(sharedState));},snapshot(){return apps[0].snapshot;},destroy(){apps.forEach(a=>a.destroy());root.replaceChildren();}};

}
