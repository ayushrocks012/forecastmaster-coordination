// @ts-nocheck
/** Constant-height selection. The full catalogue is never expanded on the page. */
const widgets=new WeakMap();
export function compactScope(container,props){
 let widget=widgets.get(container);
 if(!widget){
  const doc=container.ownerDocument,fields=doc.createElement('div'),controls=[];
  fields.className='gm-scope-fields';container.replaceChildren(fields);
  for(const [kind,title]of [['driver','Growth drivers'],['sector','Forecast tiers']]){
   const field=doc.createElement('div'),label=doc.createElement('span'),button=doc.createElement('button'),popup=doc.createElement('div'),search=doc.createElement('input'),actions=doc.createElement('div'),list=doc.createElement('div'),status=doc.createElement('div');
   field.className='gm-scope-field';field.dataset.scopeField=kind;label.className='gm-scope-label';label.textContent=title;
   button.type='button';button.className='gm-scope-button';button.setAttribute('aria-label',title);button.setAttribute('aria-haspopup','dialog');button.setAttribute('aria-expanded','false');
   popup.className='gm-scope-popup';popup.hidden=true;popup.setAttribute('role','dialog');popup.setAttribute('aria-label',title+' selection');
   search.type='search';search.placeholder='Search '+title.toLowerCase()+'…';search.setAttribute('aria-label','Search '+title.toLowerCase());
   actions.className='gm-scope-actions';list.className='gm-scope-options';status.className='gm-scope-status';status.setAttribute('aria-live','polite');
   const control={kind,button,popup,search,list,status,signature:'',items:[]};controls.push(control);
   for(const [text,select]of [['Select all',true],['Clear all',false]]){const action=doc.createElement('button');action.type='button';action.textContent=text;action.addEventListener('click',()=>{const ids=new Set(control.items.flatMap(i=>i.ids)),next=new Set(widget.props.selected);for(const id of ids)if(select)next.add(id);else next.delete(id);widget.props.onChange([...next]);});actions.append(action);}
   popup.append(search,actions,list,status);field.append(label,button,popup);fields.append(field);
   const close=()=>{popup.hidden=true;button.setAttribute('aria-expanded','false');};control.close=close;
   button.addEventListener('click',()=>{const opening=popup.hidden;controls.forEach(c=>c.close());if(opening){search.value='';popup.hidden=false;button.setAttribute('aria-expanded','true');widget.render();search.focus();}});
   search.addEventListener('input',()=>widget.render());field.addEventListener('keydown',e=>{if(e.key==='Escape'){close();button.focus();}});
   // Outside interaction closes popovers without installing global listeners.
   (container.closest('#fm-connected-review-r15')||container).addEventListener('pointerdown',e=>{if(!field.contains(e.target))close();});
   list.addEventListener('change',e=>{const input=e.target;if(!input.matches('input[data-scope-option]'))return;const item=control.items.find(i=>i.id===input.dataset.scopeOption),next=new Set(widget.props.selected);for(const id of item.ids)if(input.checked)next.add(id);else next.delete(id);widget.props.onChange([...next]);});
  }
  widget={props,render(){
   const p=this.props,selected=new Set(p.selected),drivers=p.driverIds.slice().sort((a,b)=>p.names[a].localeCompare(p.names[b])).map(id=>({id,name:p.names[id],ids:p.sectors.filter(s=>s.driver===id).map(s=>s.id)}));
   for(const c of controls){
    const all=c.kind==='driver'?drivers:p.sectors.map(s=>({id:s.id,name:p.names[s.driver]+' · '+s.name,ids:[s.id]}));
    const chosen=all.filter(i=>i.ids.some(id=>selected.has(id))),complete=all.length&&all.every(i=>i.ids.every(id=>selected.has(id)));
    c.button.textContent=(complete?'All '+all.length+' '+(c.kind==='driver'?'available drivers':'available tiers'):chosen.length===1?chosen[0].name:chosen.length?chosen.length+' selected':'Choose '+(c.kind==='driver'?'growth drivers':'forecast tiers'))+' ▾';
    c.button.disabled=!all.length;
    if(c.popup.hidden)continue;
    const q=c.search.value.trim().toLowerCase();c.items=all.filter(i=>i.name.toLowerCase().includes(q));
    const signature=JSON.stringify(c.items.map(i=>[i.id,i.name]));
    if(c.signature!==signature){
     c.signature=signature;c.list.replaceChildren();
     for(const item of c.items){const label=doc.createElement('label'),input=doc.createElement('input');label.className='gm-scope-option';input.type='checkbox';input.dataset.scopeOption=item.id;label.append(input,doc.createTextNode(item.name));c.list.append(label);}
    }
    for(const input of c.list.querySelectorAll('input')){const item=c.items.find(i=>i.id===input.dataset.scopeOption),n=item.ids.filter(id=>selected.has(id)).length;input.checked=n===item.ids.length;input.indeterminate=n>0&&n<item.ids.length;}
    c.status.textContent=c.items.length?c.items.length+' matching '+(c.kind==='driver'?'drivers':'tiers'):'No matching choices';
   }
  }};
  widgets.set(container,widget);
 }
 widget.props=props;widget.render();
}
