// @ts-nocheck
import {moveReviewItem} from './review-order';
/** Hold and drag within siblings. Capture handlers survive selector rerenders. */
export function hierarchyDrag(root,api){
 const doc=root.ownerDocument,controller=new AbortController(),opts={signal:controller.signal};let pending=null,drag=null,timer=null,target=null,ghost=null,suppressClick=false,cancelled=false;
 const clearTarget=()=>{target?.node.classList.remove('gm-drop-before','gm-drop-after');target=null;};
 const clean=()=>{clearTimeout(timer);pending=null;clearTarget();ghost?.remove();ghost=null;root.classList.remove('gm-dragging');drag=null;};
 const activate=()=>{if(!pending)return;drag=pending;root.classList.add('gm-dragging');ghost=doc.createElement('div');ghost.className='gm-order-ghost';ghost.style.cssText='position:fixed;z-index:2147483647;pointer-events:none;background:white;color:#15334a;border:1px solid #087b87;border-radius:4px;padding:8px 12px;box-shadow:0 3px 12px #0003;font:13px Segoe UI';ghost.style.left=(drag.x+12)+'px';ghost.style.top=(drag.y+10)+'px';ghost.textContent=drag.node.textContent;doc.body.append(ghost);};
 function dropNode(event){
  const under=doc.elementFromPoint(event.clientX,event.clientY);if(!under||!root.contains(under))return null;
  if(drag.kind==='channel'){const band=under.closest('[data-channel-band]');return band?.querySelector('[data-order-kind="channel"]');}
  if(drag.kind==='target'){const row=under.closest('[data-source-context]');return row?.querySelector('[data-order-kind="target"]');}
  return under.closest('[data-order-kind="measure"]');
 }
 root.addEventListener('pointerdown',e=>{const node=e.target.closest('button[data-order-kind]');if(!node||node.disabled||e.button!==0)return;cancelled=false;pending={node,kind:node.dataset.orderKind,parent:node.dataset.orderParent,id:node.dataset.orderId,x:e.clientX,y:e.clientY,pointer:e.pointerId};timer=setTimeout(activate,200);},opts);
 doc.addEventListener('pointermove',e=>{if(!pending)return;if(!drag&&Math.hypot(e.clientX-pending.x,e.clientY-pending.y)>5){clearTimeout(timer);activate();}if(!drag)return;e.preventDefault();ghost.style.left=(e.clientX+12)+'px';ghost.style.top=(e.clientY+10)+'px';clearTarget();const node=dropNode(e);if(node&&node.dataset.orderKind===drag.kind&&node.dataset.orderParent===drag.parent&&node.dataset.orderId!==drag.id){const box=(drag.kind==='channel'?node.closest('[data-channel-band]'):node).getBoundingClientRect(),after=e.clientY>box.top+box.height/2;target={node,id:node.dataset.orderId,after};node.classList.add(after?'gm-drop-after':'gm-drop-before');}
  const viewport=root.closest('.gm-review-viewport');if(viewport){const box=viewport.getBoundingClientRect();if(e.clientY>box.bottom-45)viewport.scrollTop+=18;else if(e.clientY<box.top+45)viewport.scrollTop-=18;}
 },{...opts,passive:false});
 doc.addEventListener('pointerup',()=>{const moved=drag&&target?moveReviewItem(api.getReviewOrder(),drag.kind,drag.parent,drag.id,target.id,target.after):null;const wasDrag=!!drag||cancelled;clean();cancelled=false;if(wasDrag){suppressClick=true;setTimeout(()=>suppressClick=false,0);}if(moved)api.setReviewOrder(moved);},opts);
 doc.addEventListener('pointercancel',clean,opts);
 root.addEventListener('click',e=>{if(suppressClick&&e.target.closest('[data-order-kind]')){suppressClick=false;e.preventDefault();e.stopImmediatePropagation();}}, {...opts,capture:true});
 root.addEventListener('keydown',e=>{if(e.key==='Escape'){if(drag)cancelled=true;clean();return;}if(!e.altKey||!['ArrowUp','ArrowDown'].includes(e.key))return;const node=e.target.closest('[data-order-kind]');if(!node||node.disabled)return;const kind=node.dataset.orderKind,parent=node.dataset.orderParent,id=node.dataset.orderId,order=api.getReviewOrder(),items=kind==='channel'?order.channels:kind==='target'?order.targets[parent]:order.measures[parent],index=items.indexOf(id),next=items[index+(e.key==='ArrowDown'?1:-1)];if(!next)return;e.preventDefault();const result=moveReviewItem(order,kind,parent,id,next,e.key==='ArrowDown');if(result){api.setReviewOrder(result);root.querySelector('[data-order-kind="'+kind+'"][data-order-id="'+id+'"]')?.focus({preventScroll:true});}},opts);
 return ()=>{clean();controller.abort();};
}
