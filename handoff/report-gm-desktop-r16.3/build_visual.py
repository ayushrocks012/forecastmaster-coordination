"""Port the preserved approved layout to typed, bundled Power BI code (no eval/CDN)."""
from pathlib import Path
import json,re,subprocess
from compact_adapters import adapt

HERE=Path(__file__).resolve().parent
DESIGN=HERE.parents[1]/'design/currency-plan-review-r15'
BRIDGE=json.loads((DESIGN/'bridge-catalog.json').read_text())
RULES=json.loads((DESIGN/'summary-rules.json').read_text())

def between(text,start,end,replacement):
    a=text.index(start);b=text.index(end,a)
    return text[:a]+replacement+'\n '+text[b:]

def line(text,start,replacement):
    a=text.index(start);b=text.index('\n',a)
    return text[:a]+replacement+text[b:]

fx=(DESIGN/'plan-fx.fragment.html').read_text()
fx=line(fx,"const sourceAffiliates=",'const sourceAffiliates=live.currencies,controls=new Map();')
d=(DESIGN/'demand.fragment.html').read_text()
d=line(d,'const driverNames=','const driverNames=live.drivers;')
d=line(d,'const sectors=','const sectors=live.sectors;')
d=line(d,'const cycleOptions=','const cycleOptions=live.cycles;')
d=line(d,'const channels=','const channels=live.channels;')
d=line(d,'const subchannels=','const subchannels=live.subchannels;')
d=line(d,'const periodOptions=',"const periodOptions=Array.from({length:Number(live.bounds.last.slice(0,4))-Number(live.bounds.first.slice(0,4))+1},(_,i)=>Number(live.bounds.first.slice(0,4))+i).flatMap(year=>['FY','YTD','YTG','H1','H2'].map(kind=>({id:year+':'+kind,name:year+' '+kind})));")
d=between(d,'const files=[];','function adsInfo','const files=live.files;')
d=d.replace("const defaults={affiliates:['uk']", "const defaults={affiliates:[live.affiliates[0]?.id]")
d=d.replace("cycles:['2026-10'],channels:['community','hospital']", "cycles:[live.cycles.at(-1)?.id],channels:channels.map(x=>x.id)")
d=d.replace("files:adsSelection(['2026-10']).files.map(f=>f.id)","files:adsSelection([live.cycles.at(-1)?.id]).files.map(f=>f.id)")
d=d.replace("periods:['2026:FY']","periods:[live.cycles.at(-1)?.id.slice(0,4)+':FY']")
d=d.replace("rankPeriod:'2026:FY'","rankPeriod:live.cycles.at(-1)?.id.slice(0,4)+':FY'")
d=d.replace("monthStart:'2025-01',monthEnd:'2027-12'","monthStart:live.cycles.at(-1)?.id.slice(0,4)+'-01',monthEnd:live.cycles.at(-1)?.id.slice(0,4)+'-12'")
d=line(d,'const cutoff=','const cutoff=(file,metric)=>live.cutoff(file,metric.section);')
d=d.replace("return [{id:'uk',name:'United Kingdom'}]","return live.affiliates")
d=d.replace("return files.filter(f=>state.cycles.includes(f.cycle))","return files.filter(f=>state.cycles.includes(f.cycle)&&state.affiliates.includes(f.affiliate.toLowerCase()))")
d=between(d,'function factor()','function variancePercent', '''function factor(){return subchannels.some(x=>state.channels.includes(x.channel)&&state.subchannels.includes(x.id))?1:0;}
 function comboGroups(){const map=new Map();for(const f of pickedFiles()){const family=planFamily(f),key=f.affiliate+'|'+f.cycle+'|'+family;if(!map.has(key))map.set(key,{key,cycle:f.cycle,scenario:family,files:[]});map.get(key).files.push(f);}return [...map.values()];}
 function localAmount(combo,subset,metric,months,window=0){return live.demand(combo,subset,metric,months,window,state,fx,false);}
 function amount(combo,subset,metric,months,window=0){return live.demand(combo,subset,metric,months,window,state,fx,true);}''')
d=d.replace("adsSelection(state.cycles,files,selectedDrivers())","adsSelection(state.cycles,availableFiles(),selectedDrivers())")
d=d.replace("state.affiliates.includes('uk')?'United Kingdom':'Choose an Affiliate'","live.affiliates.filter(a=>state.affiliates.includes(a.id)).map(a=>a.name).join(' · ')||'Choose an Affiliate'")
d=d.replace("c=monthIndex(combo.cycle)-(metric.section==='ef'?1:2)","c=combo.files.length?cutoff(combo.files[0],metric):null")
# Replace all sample provenance; the remaining labels are actual context, never a claimed refresh time.
d=d.replace('Design preview · sample data','Connected model · R16').replace('Illustrative values · sample sectors · saved actuals cutoff per file','Saved source observations · complete periods only').replace('Demo data · local interactions','Loaded data · local selections').replace('Sample refresh completed · 21 Oct 2026, 07:30 UTC','Model data loaded')
d=d.replace("if(state.fileMode==='ads')state.files=", "if(state.fileMode==='ads')state.files=")
s=(DESIGN/'sop.fragment.html').read_text()
s=s.replace('/* BRIDGE_MEASURE_CATALOG */',json.dumps(BRIDGE,separators=(',',':'))).replace('/* SOP_SUMMARY_RULES */',json.dumps(RULES,separators=(',',':')))
s=line(s,'const drivers=','const drivers=live.drivers;')
s=line(s,'const sectors=','const sectors=live.sectors;')
s=line(s,'const cycles=','const cycles=live.cycles;')
s=line(s,'const affiliates=','const affiliates=live.affiliates;')
s=line(s,'const periods=',"const periods=Array.from({length:Number(live.bounds.last.slice(0,4))-Number(live.bounds.first.slice(0,4))+1},(_,i)=>Number(live.bounds.first.slice(0,4))+i).flatMap(year=>['FY','YTD','YTG'].map(kind=>({id:year+':'+kind,name:year+' '+kind})));")
s=s.replace("affiliates:['uk'],cycles:['2026-10']","affiliates:[live.affiliates[0]?.id],cycles:[live.cycles.at(-1)?.id]")
s=s.replace("sectors:['compact','juce']","sectors:live.sectors.map(s=>s.id)")
s=s.replace("periods:['2026:FY','2026:YTD','2026:YTG'],monthStart:'2026-01',monthEnd:'2026-12'","periods:['FY','YTD','YTG'].map(k=>live.cycles.at(-1)?.id.slice(0,4)+':'+k),monthStart:live.cycles.at(-1)?.id.slice(0,4)+'-01',monthEnd:live.cycles.at(-1)?.id.slice(0,4)+'-12'")
s=line(s,'const cut=','const cut=(cycle,basis)=>live.cutFor(cycle,basis);')
s=between(s,'function source(sector','function groups()', 'function source(){throw Error("Synthetic source is not included in this report.");}')
s=s.replace("const activeRows=()=>state.affiliates.includes('uk')?",'const activeRows=()=>state.affiliates.length?')
s=between(s,'function localAmount(row','function periodMonths', '''function localAmount(row,group,months,cycle){return live.sop(row,group,months,cycle,state.display,fx,false);}
 function amount(row,group,months,cycle){return live.sop(row,group,months,cycle,state.display,fx,true);}''')
s=s.replace('Design preview · sample data','Connected model · R16').replace('Illustrative data · saved ADS source binding follows the approved review-page design','Saved source observations · complete periods only').replace('Illustrative data · local selections','Loaded data · local selections').replace(' · Sample data',' · Model data loaded')
shell=(DESIGN/'shell.fragment.html').read_text()
shell=line(shell,'const names=','const names=live.drivers;')
shell=shell.replace("if(!s.affiliates.includes('uk'))return [];",'')
shell=shell.replace('apis.demand.adsSelection(s.cycles,apis.demand.files,drivers)','apis.demand.adsSelection(s.cycles,apis.demand.files.filter(f=>s.affiliates.includes(f.affiliate.toLowerCase())),drivers)')
shell=shell.replace("month(index(c)-2)","month(live.cutFor(c,'ims'))").replace("month(index(c)-1)","month(live.cutFor(c,'ef'))")
shell=shell.replace("'Sample refresh: 21 Oct 2026, 07:30 UTC'","'Loaded from connected model'")
shell=shell.replace("let page=saved?.schema", "let page=saved?.schema")
shell=shell.replace("show(page,false,false);\n})();", "live.setSources(sources);show(initialState?.page||initialPage||page,false,false);\n})();")
d,s,shell=adapt(d,s,shell)
shell=shell.replace('<!-- PLAN_FX -->',fx).replace('<!-- DEMAND_PAGE -->',d).replace('<!-- SOP_PAGE -->',s)
shell=shell.replace('t%12','((t%12)+12)%12')
scripts=re.findall(r'<script>([\s\S]*?)</script>',shell)
assert len(scripts)==5 # FX, Demand, D3 placeholder, S&OP, shared navigation
scripts=[x for x in scripts if 'BUNDLED_D3' not in x]
assert len(scripts)==4
html=re.sub(r'<script>[\s\S]*?</script>','',shell)
html=html.replace('Connected model · R16','Connected model · R16.3')
# No demo JavaScript, embedded data generators or external runtime are shipped.
html+='''<style>#fm-connected-review-r15{color-scheme:light;overflow:visible;height:auto;background:#f5f7fa} .cr-live-alert{padding:9px 14px;background:#fff3cd;color:#5d4805;font:13px Segoe UI} .cr-nav{padding:8px 12px 0}</style>'''
html+='<style>'+(HERE/'compact.css').read_text()+'</style>'
header='''// @ts-nocheck
import * as d3 from 'd3';
import DOMPurify from 'dompurify';
import {createLive} from './live';
import {adsInfo as sourceADSInfo,selectADS} from './scope';
import {compactScope} from './scope-ui';
import {alignHeaders} from './layout';
function setHTML(el,markup){
 const tag=el.tagName?.toLowerCase(),table=['table','thead','tbody','tfoot','tr','colgroup'].includes(tag),svg=el.namespaceURI==='http://www.w3.org/2000/svg';
 const wrap=table?(tag==='table'?'table':tag==='tr'?'table><tbody><tr':'table><'+tag):svg?'svg':null;
 let text=String(markup);if(wrap)text='<'+wrap+'>'+text+'</'+wrap.split('><').reverse().join('></')+'>';
 const clean=DOMPurify.sanitize(text,{RETURN_DOM_FRAGMENT:true,ADD_TAGS:['style'],ADD_ATTR:['aria-controls'],USE_PROFILES:svg?{svg:true,svgFilters:true}:undefined});
 const parent=wrap?clean.querySelector(svg?'svg':tag):null;el.replaceChildren(...Array.from((parent||clean).childNodes));
}
const bridge='''+json.dumps(BRIDGE,separators=(',',':'))+''';
const template='''+json.dumps(html)+''';
export function mount(container,feed,initialState,onPersist,initialPage='demand'){
 const live=createLive(feed,bridge),observers=[],listeners=[];
 live.setScopeContext(()=>initialState?.demand||{});
 const ResizeObserver=class extends globalThis.ResizeObserver{constructor(fn){super(fn);observers.push(this);}};
 const document=new Proxy(globalThis.document,{get(target,key){if(key==='getElementById')return id=>container.querySelector('[id="'+id+'"]');const v=target[key];return typeof v==='function'?v.bind(target):v;}});
 const openai={widgetState:initialState?{modelContent:{schema:'fm-connected-gm-review-r15',state:initialState}}:null,setWidgetState:value=>onPersist(value.modelContent.state)};
 const window=new Proxy(globalThis.window,{get(target,key){if(key==='openai')return openai;if(key==='addEventListener')return (type,fn)=>{listeners.push([type,fn]);target.addEventListener(type,fn);};const v=target[key];return typeof v==='function'?v.bind(target):v;}});
 const frag=DOMPurify.sanitize(template,{RETURN_DOM_FRAGMENT:true,FORCE_BODY:true,ADD_TAGS:['style'],ADD_ATTR:['aria-controls']});container.replaceChildren(frag);
'''
tail='''
 alignHeaders(container);
 const session=container.querySelector('#fm-connected-review-r15').reviewSession;
 if(live.missingSOP){const message=globalThis.document.createElement('div');message.className='cr-live-alert';message.textContent='S&OP feed update required: run the included reporting setup before publication. Missing measures display —, never sample figures.';container.prepend(message);}
 return {getState:()=>session.getState(),destroy:()=>{observers.forEach(o=>o.disconnect());listeners.forEach(([t,f])=>globalThis.window.removeEventListener(t,f));},live};
}
'''
(HERE/'Visual/src/engine.ts').write_text(header+'\n'.join(scripts)+tail)
subprocess.run(['node',str(HERE/'sanitize_generated.cjs')],check=True)
print('Built production layout:',len(html),'HTML bytes; no synthetic arithmetic')
