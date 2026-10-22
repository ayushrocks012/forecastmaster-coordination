/** Matching header geometry on both views; move existing controls, retain handlers. */
export function alignHeaders(container:HTMLElement){
 const doc=container.ownerDocument;
 for(const [kind,prefix]of [['demand','fm'],['sop','sb']]){
  const page=container.querySelector('#fm-connected-'+kind+'-r15') as HTMLElement;
  const main=page.querySelector(kind==='demand'?'.fm-content':'.sb-main') as HTMLElement;
  const calendar=page.querySelector(kind==='demand'?'.fm-months':'.sb-months') as HTMLElement;
  const previous=calendar.parentElement;const header=doc.createElement('div');header.className='gm-common-header';
  const row=doc.createElement('div');row.className='gm-common-calendar';row.append(calendar);
  let plan=page.querySelector('#fm-plan-summary') as HTMLElement;
  if(kind==='sop'){plan=doc.createElement('span');plan.id='sb-plan-summary';plan.textContent=container.querySelector('#fm-plan-summary')?.textContent||'Plan: ADS · automatic';}
  plan.classList.add('gm-common-plan');row.append(plan);
  const status=page.querySelector(kind==='demand'?'#fm-data-context':'#sb-cutoffs') as HTMLElement;
  const details=page.querySelector('.cr-source-details') as HTMLElement;
  const filters=page.querySelector('#'+prefix+'-filters') as HTMLElement;
  filters.classList.add('gm-common-filters');
  const display=page.querySelector(kind==='demand'?'#fm-display':'#sb-units') as HTMLElement;
  const displayField=display.parentElement;displayField.classList.add('gm-common-display');
  if(kind==='sop')for(let col=3;col<=4;col++){const blank=doc.createElement('div');blank.className='gm-filter-space';blank.style.gridColumn=String(col);blank.style.gridRow='1';blank.setAttribute('aria-hidden','true');filters.append(blank);}
  header.append(row,status,details,filters);main.prepend(header);
  if(previous){previous.hidden=true;previous.classList.add('gm-retired-header-row');}
  const scope=page.querySelector(kind==='demand'?'section[aria-label="Shared review selection"]':'section[aria-label="Growth driver and sector selection"]');scope?.classList.add('gm-common-scope');
  const title=scope?.querySelector(kind==='demand'?'.fm-paneltitle':'h2');if(title)title.textContent='Growth drivers, sectors & review summary period';
 }
 const demand=container.querySelector('#fm-connected-demand-r15');
 const period=demand.querySelector('#fm-period-field') as HTMLElement;period.hidden=true;
 const summary=demand.querySelector('section[aria-label="Executive summary"]')||demand.querySelector('#fm-summary')?.closest('section');
 if(summary){const head=summary.querySelector('.fm-panelhead'),toolbar=summary.querySelector('.fm-local-toolbar'),caption=toolbar?.querySelector(':scope > .fm-detail'),toggle=head?.querySelector('[data-section-toggle]'),trends=head?.querySelector('.fm-trends');if(caption){caption.classList.add('gm-summary-caption');head.insertBefore(caption,toggle||null);}if(trends)toolbar?.append(trends);summary.classList.add('gm-summary-panel');}
 const sop=container.querySelector('#fm-connected-sop-r15');
 (sop.querySelector('#sb-summary-periods') as HTMLElement).hidden=true;
 const actions=sop.querySelector('.sb-float-actions'),reset=doc.createElement('button');reset.type='button';reset.id='gm-reset-order';reset.textContent='Reset order';reset.title='Restore the grouped bridge order';actions?.append(reset);
 const hint=sop.querySelector('.sb-selector-intro');if(hint)hint.textContent='Channel → Sub-channel → Measure · Hold and drag to reorder';
 const mode=sop.querySelector('[data-table="periods"]');if(mode)mode.textContent='Periods';
 const note=sop.querySelector('.sb-note');if(note)note.textContent=note.textContent.replace('Source order','Review order');
}
