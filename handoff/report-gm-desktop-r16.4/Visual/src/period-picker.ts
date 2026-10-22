// @ts-nocheck
/** The same searchable review-period control on both views. */
const mounted=new WeakMap();
export function reviewPeriods(container,props){
 let ui=mounted.get(container);
 if(!ui){
  const doc=container.ownerDocument,node=doc.createElement('div'),label=doc.createElement('span'),button=doc.createElement('button'),popup=doc.createElement('div'),search=doc.createElement('input'),actions=doc.createElement('div'),list=doc.createElement('div'),status=doc.createElement('div');
  node.className='gm-scope-field gm-period-field';node.dataset.scopeField='period';label.className='gm-scope-label';label.textContent='Review summary period';
  button.type='button';button.className='gm-scope-button';button.setAttribute('aria-label','Review summary period');button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-expanded','false');
  popup.className='gm-scope-popup';popup.hidden=true;popup.setAttribute('role','dialog');popup.setAttribute('aria-label','Review summary period selection');search.type='search';search.placeholder='Search periods…';search.setAttribute('aria-label','Search review summary periods');actions.className='gm-scope-actions';list.className='gm-scope-options';status.className='gm-scope-status';
  ui={props,render(){const p=this.props,chosen=p.options.filter(o=>p.selected.includes(o.id));button.textContent=(chosen.length===1?chosen[0].name:chosen.length?chosen.length+' selected':'Choose review periods')+' ▾';button.title=chosen.map(o=>o.name).join(' · ');if(popup.hidden)return;const q=search.value.trim().toLowerCase(),items=p.options.filter(o=>o.name.toLowerCase().includes(q));list.replaceChildren();for(const item of items){const row=doc.createElement('label'),input=doc.createElement('input');row.className='gm-scope-option';input.type='checkbox';input.checked=p.selected.includes(item.id);input.value=item.id;input.addEventListener('change',()=>p.onChange(input.checked?[...new Set([...p.selected,item.id])]:p.selected.filter(id=>id!==item.id)));row.append(input,doc.createTextNode(item.name));list.append(row);}status.textContent=items.length+' matching periods';this.items=items;},close(){popup.hidden=true;button.setAttribute('aria-expanded','false');}};
  for(const [text,on]of [['Select all',true],['Clear all',false]]){const b=doc.createElement('button');b.type='button';b.textContent=text;b.addEventListener('click',()=>{const ids=new Set(ui.items.map(i=>i.id)),next=new Set(ui.props.selected);for(const id of ids)if(on)next.add(id);else next.delete(id);ui.props.onChange([...next]);});actions.append(b);}
  button.addEventListener('click',()=>{const open=popup.hidden;if(open){search.value='';popup.hidden=false;button.setAttribute('aria-expanded','true');ui.render();search.focus();}else ui.close();});search.addEventListener('input',()=>ui.render());node.addEventListener('keydown',e=>{if(e.key==='Escape'){ui.close();button.focus();}});
  (container.closest('#fm-connected-review-r15')||container).addEventListener('pointerdown',e=>{if(!node.contains(e.target))ui.close();});popup.append(search,actions,list,status);node.append(label,button,popup);container.append(node);mounted.set(container,ui);
 }
 ui.props=props;ui.render();
}
