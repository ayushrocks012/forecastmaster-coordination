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
 }
}
