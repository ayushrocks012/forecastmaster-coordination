import powerbi from 'powerbi-visuals-api';
import {fresh,State,Row,context,reorder,tokens} from './state';
import {catalog} from './catalog';
import IVisual=powerbi.extensibility.visual.IVisual;
import VisualConstructorOptions=powerbi.extensibility.visual.VisualConstructorOptions;
import VisualUpdateOptions=powerbi.extensibility.visual.VisualUpdateOptions;
import IVisualHost=powerbi.extensibility.visual.IVisualHost;
/** The only non-native component: selection, hierarchy order and plan rates.
 * It emits a model-column filter. Charts, summary cells and exports are native.
 */
export class Visual implements IVisual {
 private host:IVisualHost;private root:HTMLElement;private state:State=fresh();private rows:Row[]=[];
 private moved='';private signature='';private received='';private error='';private currencies:string[]=['GBP'];private fxOnly=false;
 constructor(options:VisualConstructorOptions){this.host=options.host;this.root=options.element;this.root.classList.add('fm-native-controls');}
 public getFormattingModel():powerbi.visuals.FormattingModel{return {cards:[]};}
 public update(options:VisualUpdateOptions):void {
  const view=options.dataViews?.[0],table=view?.table;
  this.fxOnly=view?.metadata?.objects?.general?.variant==='fx';
  const saved=view?.metadata?.objects?.general?.preferences;
  if(typeof saved==='string'){try {const parsed=JSON.parse(saved);if(parsed.version===1){
   const valid=parsed.state;if(!valid||!['channels','contexts','rows','order'].every(k=>Array.isArray(valid[k])&&valid[k].every(v=>typeof v==='string')))throw Error('Invalid preference arrays.');
   if(!valid.rates||Object.entries(valid.rates).some(([c,v])=>!/^[A-Z]{3}$/.test(c)||typeof v!=='number'||!Number.isFinite(v)||v<0))throw Error('Invalid saved rates.');
   if(valid.order.some(k=>{try{const a=JSON.parse(k);return !Array.isArray(a)||!['channel','sub','measure'].includes(a[0])||!a.every(v=>typeof v==='string');}catch{return true;}}))throw Error('Invalid saved order.');
   this.state={...fresh(),...valid};
  }}catch{this.error='Saved preferences could not be read. Reset this control.';}}
  const filters=options.jsonFilters as unknown as {target?:{table?:string;column?:string};values?:string[]}[];
  const incoming=filters?.find(f=>f.target?.table==='fm_native_state'&&f.target?.column==='Token'&&Array.isArray(f.values));
  if(incoming&&JSON.stringify([...incoming.values].sort())!==this.received){
   incoming.values=incoming.values.filter(t=>typeof t==='string');
   this.received=JSON.stringify([...incoming.values].sort());const chosen=incoming.values.filter(t=>t.startsWith('row:')).map(t=>t.split(':'));
   const ids=[...new Set(chosen.map(t=>t[1]))],selected=catalog.filter(r=>ids.includes(r.id));
   this.state.rows=ids;this.state.channels=[...new Set(selected.map(r=>r.channel))];this.state.contexts=[...new Set(selected.map(context))];
   if(incoming.values.some(t=>t.startsWith('order:'))){
    this.state.rows=incoming.values.filter(t=>t.startsWith('saved-row:')).map(t=>t.slice(10));
    this.state.channels=incoming.values.filter(t=>t.startsWith('saved-channel:')).map(t=>t.slice(14));
    this.state.contexts=incoming.values.filter(t=>t.startsWith('saved-context:')).map(t=>t.slice(14));
   }
   const chunks=new Map<string,Map<number,number>>();for(const token of incoming.values.filter(t=>t.startsWith('fx:'))){const [,c,p,d]=token.split(':');if(!chunks.has(c))chunks.set(c,new Map());chunks.get(c)?.set(Number(p),Number(d));}
   this.state.rates={};for(const [c,parts] of chunks){if(parts.size!==7)continue;const mantissa=Array.from({length:6},(_,i)=>String(parts.get(i)).padStart(3,'0')).join('');const rate=Number(mantissa+'e'+parts.get(6));if(Number.isFinite(rate))this.state.rates[c]=rate;}
   const savedOrder=incoming.values.filter(t=>t.startsWith('order:')).map(t=>t.split(':'));
   const orderMap=new Map<string,number>();for(const t of savedOrder.length?savedOrder:chosen){const r=catalog.find(row=>row.id===t[1]);if(!r)continue;const offset=t[0]==='order'?2:3;orderMap.set(JSON.stringify(['channel',r.channel]),Number(t[offset]));orderMap.set(JSON.stringify(['sub',r.channel,r.sub]),Number(t[offset+1]));orderMap.set(JSON.stringify(['measure',r.channel,r.sub,r.id]),Number(t[offset+2]));}
   this.state.order=[...orderMap.keys()].sort((a,b)=>{const pa=JSON.parse(a).slice(0,-1).join('|'),pb=JSON.parse(b).slice(0,-1).join('|');return pa.localeCompare(pb)||(orderMap.get(a)??0)-(orderMap.get(b)??0);});
  }
  if(table){const index=(role:string)=>table.columns.findIndex(c=>c.roles?.[role]);
   const ix=['RowID','Channel','SubChannel','Measure','Display','ChannelRank','SubRank','MeasureRank'].map(index);
   this.rows=table.rows.map(row=>({id:String(row[ix[0]]),channel:String(row[ix[1]]),sub:String(row[ix[2]]||''),label:String(row[ix[3]]),display:String(row[ix[4]]),c:Number(row[ix[5]]),s:Number(row[ix[6]]),m:Number(row[ix[7]])}));
  }
  const currencyColumn=view?.metadata?.objects?.general?.currencies;if(typeof currencyColumn==='string')this.currencies=currencyColumn.split(',').map(c=>c.trim()).filter(c=>/^[A-Z]{3}$/.test(c));
  this.render();
 }
 private element<K extends keyof HTMLElementTagNameMap>(kind:K,text='',parent:HTMLElement=this.root):HTMLElementTagNameMap[K]{const el=document.createElement(kind);el.textContent=text;parent.append(el);return el;}
 private button(text:string,on:boolean,action:()=>void,parent:HTMLElement):HTMLButtonElement{
  const b=this.element('button',(on?'✓ ':'')+text,parent);b.type='button';b.className=on?'selected':'';b.setAttribute('aria-pressed',String(on));b.onclick=()=>{action();this.commit();};return b;
 }
 private toggle(key:'channels'|'contexts'|'rows',value:string):void{this.state[key]=this.state[key].includes(value)?this.state[key].filter(x=>x!==value):[...this.state[key],value];}
 private drag(el:HTMLElement,key:string):void{
  el.draggable=true;el.title='Hold and drag within this level. Alt + ↑ / ↓ also works.';
  el.ondragstart=e=>{this.moved=key;e.dataTransfer?.setData('text/plain',key);};
  el.ondragover=e=>e.preventDefault();el.ondrop=e=>{e.preventDefault();this.ensureOrder();this.state.order=reorder(this.state.order,this.moved,key);this.commit();};
  el.onkeydown=e=>{if(!e.altKey||!['ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();this.ensureOrder();
   const parent=JSON.parse(key).slice(0,-1).join('|'),same=this.state.order.filter(k=>JSON.parse(k).slice(0,-1).join('|')===parent),i=same.indexOf(key),target=same[i+(e.key==='ArrowUp'?-1:1)];
   if(!target)return;if(e.key==='ArrowUp')this.state.order=reorder(this.state.order,key,target);else this.state.order=reorder(this.state.order,target,key);this.commit();};
 }
 private ensureOrder():void{
  const keys:string[]=[];for(const r of this.rows){keys.push(JSON.stringify(['channel',r.channel]),JSON.stringify(['sub',r.channel,r.sub]),JSON.stringify(['measure',r.channel,r.sub,r.id]));}
  for(const key of keys)if(!this.state.order.includes(key))this.state.order.push(key);
 }
 private commit():void {
  try{
   // The Power BI filter-schema URI is an identifier prescribed by the SDK.
   // eslint-disable-next-line powerbi-visuals/no-http-string
   const filter={$schema:'http://powerbi.com/product/schema#basic',filterType:1,target:{table:'fm_native_state',column:'Token'},operator:'In',values:tokens(catalog,this.state)};
   const signature=JSON.stringify(filter);if(signature!==this.signature){
    const old=this.received;this.received=JSON.stringify([...filter.values].sort());
    try{this.host.applyJsonFilter(filter as powerbi.IFilter,'general','filter',powerbi.FilterAction.merge);this.signature=signature;}catch(error){this.received=old;throw error;}
   }
   this.host.persistProperties({merge:[{objectName:'general',selector:null,properties:{preferences:JSON.stringify({version:1,state:this.state})}}]});
   this.error='';this.render();
  }catch(error){this.error=error instanceof Error?error.message:String(error);this.render();}
 }
 private render():void{
  this.root.replaceChildren();const head=this.element('div');head.className='head';this.element('strong',this.fxOnly?'Plan rates':'Build your view',head);
  const fx=this.element('details');fx.open=this.fxOnly;this.element('summary','Plan rates · currency → USD',fx);
  for(const c of this.currencies){if(c==='USD')continue;const label=this.element('label',c+'  =  ',fx),input=this.element('input','',label);input.type='number';input.min='0';input.step='any';input.placeholder='Enter rate';if(Object.hasOwn(this.state.rates,c))input.value=String(this.state.rates[c]);
   input.onchange=()=>{if(!input.value.trim())delete this.state.rates[c];else{const v=Number(input.value);if(!Number.isFinite(v)||v<0){this.error='Enter a finite non-negative rate.';this.render();return;}this.state.rates[c]=v;}this.commit();};this.element('span',' USD',label);}
  if(this.fxOnly){if(this.error)this.element('p',this.error).setAttribute('role','alert');return;}
  const actions=this.element('div');actions.className='actions';
  this.button('Select all',false,()=>{this.state.channels=[...new Set(this.rows.map(r=>r.channel))];this.state.contexts=[...new Set(this.rows.map(context))];this.state.rows=[...new Set(this.rows.map(r=>r.id))];},actions);
  this.button('Clear all',false,()=>{this.state.channels=[];this.state.contexts=[];this.state.rows=[];},actions);
  this.button('Reset order',false,()=>{this.state.order=[];},actions);
  if(this.error){const warning=this.element('p',this.error);warning.setAttribute('role','alert');}
  this.element('p','Channel → Sub-channel → Measure · Hold and drag to reorder');
  if(!this.rows.length){this.element('p','No channel measures are available for this selection. Select an affiliate, cycle and growth driver.');return;}
  this.ensureOrder();
  const order=(a:string,b:string)=>this.state.order.indexOf(a)-this.state.order.indexOf(b);
  const table=this.element('div');table.className='selection';
  const header=this.element('div','',table);header.className='row header';for(const t of ['Channel','Sub-channel','Measure'])this.element('span',t,header);
  const channels=[...new Set(this.rows.map(r=>r.channel))].sort((a,b)=>order(JSON.stringify(['channel',a]),JSON.stringify(['channel',b])));
  for(const channel of channels){const family=this.rows.filter(r=>r.channel===channel),band=this.element('div','',table);band.className='band';const ccell=this.element('div','',band);
   const cbutton=this.button(channel,this.state.channels.includes(channel),()=>this.toggle('channels',channel),ccell);this.drag(cbutton,JSON.stringify(['channel',channel]));
   const children=this.element('div','',band);children.className='children';
   const subs=[...new Set(family.map(r=>r.sub))].sort((a,b)=>order(JSON.stringify(['sub',channel,a]),JSON.stringify(['sub',channel,b])));
   for(const sub of subs){const choices=family.filter(r=>r.sub===sub),row=this.element('div','',children);row.className='context';const scell=this.element('div','',row),ck=context(choices[0]);
    const sb=this.button(sub||'—',this.state.contexts.includes(ck),()=>this.toggle('contexts',ck),scell);sb.disabled=!this.state.channels.includes(channel);this.drag(sb,JSON.stringify(['sub',channel,sub]));
    const mcell=this.element('div','',row);mcell.className='measures';
    const unique=[...new Map(choices.map(r=>[r.id,r])).values()].sort((a,b)=>order(JSON.stringify(['measure',channel,sub,a.id]),JSON.stringify(['measure',channel,sub,b.id])));
    for(const choice of unique){const b=this.button(choice.label,this.state.rows.includes(choice.id),()=>this.toggle('rows',choice.id),mcell);b.disabled=!this.state.channels.includes(channel)||!this.state.contexts.includes(ck);this.drag(b,JSON.stringify(['measure',channel,sub,choice.id]));}
   }
  }
 }
}
