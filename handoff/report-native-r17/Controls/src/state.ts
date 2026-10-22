/** Pure preference encoding. No sales values or business calculations. */
export type Row = {id:string; channel:string; sub:string; label:string; display:string; c:number; s:number; m:number};
export type State = {channels:string[]; contexts:string[]; rows:string[]; rates:Record<string,number>; order:string[]};
export const fresh = ():State => ({channels:[],contexts:[],rows:[],rates:{},order:[]});
export function rateTokens(currency:string, value:number):string[] {
 if(!/^[A-Z]{3}$/.test(currency)||typeof value!=='number'||!Number.isFinite(value)||value<0) throw Error('Enter a finite non-negative plan rate.');
 if(currency==='USD')return [];
 const [mantissa,exponent]=value.toExponential(17).split('e'),digits=mantissa.replace('.','');
 const result=Array.from({length:6},(_,position)=>`fx:${currency}:${position}:${Number(digits.slice(position*3,position*3+3))}`);
 result.push(`fx:${currency}:6:${Number(exponent)-17}`);return result;
}
export function context(r:Row):string{return JSON.stringify([r.channel,r.sub]);}
export function reorder(order:string[], moved:string, before:string):string[] {
 const parent=(key:string)=>JSON.parse(key).slice(0,-1).join('|');
 if(moved===before||parent(moved)!==parent(before))return order;
 const next=order.filter(k=>k!==moved),at=next.indexOf(before);if(at<0)return order;next.splice(at,0,moved);return next;
}
export function rowTokens(rows:Row[],state:State):string[] {
 const channels=[...new Set(rows.map(r=>r.channel))],position=(key:string,fallback:number)=>{
  const siblings=state.order.filter(k=>JSON.parse(k).slice(0,-1).join('|')===JSON.parse(key).slice(0,-1).join('|'));
  return siblings.includes(key)?siblings.indexOf(key):fallback;
 };
 return rows.filter(r=>state.channels.includes(r.channel)&&state.contexts.includes(context(r))&&state.rows.includes(r.id)).flatMap(r=>{
  const c=position(JSON.stringify(['channel',r.channel]),channels.indexOf(r.channel));
  const s=position(JSON.stringify(['sub',r.channel,r.sub]),r.s);
  const m=position(JSON.stringify(['measure',r.channel,r.sub,r.id]),r.m);
  return ['Units','Value'].map(display=>`row:${r.id}:${display}:${c}:${s}:${m}`);
 });
}
export function tokens(rows:Row[],state:State):string[]{
 const all={...state,channels:[...new Set(rows.map(r=>r.channel))],contexts:[...new Set(rows.map(context))],rows:[...new Set(rows.map(r=>r.id))]};
 const order=[...new Set(rowTokens(rows,all).map(token=>{const [,id,,c,s,m]=token.split(':');return `order:${id}:${c}:${s}:${m}`;}))];
 return [...new Set(['none',...rowTokens(rows,state),...state.channels.map(k=>'saved-channel:'+k),...state.contexts.map(k=>'saved-context:'+k),
  ...state.rows.map(k=>'saved-row:'+k),...order,...Object.entries(state.rates).flatMap(([c,v])=>rateTokens(c,v))])];
}
