// @ts-nocheck
/** Presentation permutations only. Never change a row's business parent. */
const sequence=(base,saved)=>[...new Set([...(Array.isArray(saved)?saved:[]).filter(id=>base.includes(id)),...base])];
export function makeReviewOrder(rows,families,sourceOrder,contextFor,saved={}){
 const source=sourceOrder.map(id=>rows.find(r=>r.id===id)).filter(Boolean),baseChannels=families.filter(f=>source.some(r=>r.group===f.id)).map(f=>f.id);
 const order={channels:sequence(baseChannels,saved?.channels),targets:{},measures:{},flat:[]};
 for(const channel of order.channels){const targets=source.filter(r=>r.group===channel&&r.basis==='ef').map(r=>r.id);order.targets[channel]=sequence(targets,saved?.targets?.[channel]);for(const target of order.targets[channel]){const ids=source.filter(r=>contextFor(r)===target).map(r=>r.id);order.measures[target]=sequence(ids,saved?.measures?.[target]);order.flat.push(...order.measures[target]);}}
 return order;
}
export function moveReviewItem(order,kind,parent,id,target,after=false){
 const next=JSON.parse(JSON.stringify(order)),items=kind==='channel'?next.channels:kind==='target'?next.targets[parent]:kind==='measure'?next.measures[parent]:null;
 if(!items||id===target||!items.includes(id)||!items.includes(target))return null;
 items.splice(items.indexOf(id),1);items.splice(items.indexOf(target)+(after?1:0),0,id);delete next.flat;return next;
}
