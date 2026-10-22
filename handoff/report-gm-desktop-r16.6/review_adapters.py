"""R16.4 presentation changes; numeric source and aggregate engine are unchanged."""
from compact_adapters import replace_span

def refine(d,s,shell):
    d=d.replace("  renderAvailability();", "  reviewPeriods($('#fm-quick-scope .gm-scope-fields'),{options:validOptions('periods'),selected:state.periods,onChange:ids=>{state.periods=ids;update();}});\n  renderAvailability();")
    s=s.replace("  $('#sb-scope-caption').textContent=", "  reviewPeriods($('#sb-scope .gm-scope-fields'),{options:availablePeriods(),selected:state.periods,onChange:ids=>{state.periods=ids;update();}});\n  $('#sb-scope-caption').textContent=")
    d=replace_span(d,'function renderExecutive()','function chartBenchmarkContext',r'''function actualOnly(period,combo,metric){
  const months=periodMonths(period.id,combo,metric);return months.length>0&&combo.files.length>0&&combo.files.every(f=>Number.isFinite(cutoff(f,metric))&&months.every(t=>t<=cutoff(f,metric)));
 }
 function renderExecutive(){
  const metrics=catalog.filter(m=>state.metrics.includes(m.id)),combos=comboGroups(),subset=activeSectors(),periods=periodOptions.filter(p=>state.periods.includes(p.id)),trend=state.trends[0];
  if(!subset.length||!periods.length||!combos.length||!metrics.length){$('#fm-executive-readout').replaceChildren();return;}
  $('#fm-executive-readout').innerHTML=combos.flatMap(combo=>metrics.map(metric=>{
   const title=metric.name+(metric.unit==='£'?' · '+fx.label():''),context=shortCycle(combo.cycle)+' · '+combo.scenario;
   const values=periods.map(period=>{const months=periodMonths(period.id,combo,metric),plan=amount(combo,subset,metric,months),actual=actualOnly(period,combo,metric),benchmark=actual?null:amount(combo,subset,metric,months,trend),delta=plan==null||benchmark==null?null:plan-benchmark,percent=actual?null:variancePercent(combo,subset,metric,months,trend);return {period,plan,actual,delta,percent};});
   return '<div class="gm-position" data-executive-position="'+escape(combo.key+'|'+metric.id)+'"><div class="gm-position-head"><strong>'+escape(title)+'</strong><span>'+escape(context)+'</span></div><div class="gm-position-scroll"><table class="gm-position-table"><thead><tr><th scope="col">Selection</th>'+values.map(v=>'<th scope="col" data-overview-period="'+v.period.id+'">'+escape(v.period.name)+'</th>').join('')+'</tr></thead><tbody><tr><th scope="row">Plan</th>'+values.map(v=>'<td class="gm-position-plan" data-headline-plan="'+v.period.id+'" data-value="'+(v.plan==null?'':v.plan)+'">'+compact(v.plan,metric.unit)+'</td>').join('')+'</tr><tr><th scope="row">vs '+trend+'M trend</th>'+values.map(v=>'<td data-headline-variance="'+v.period.id+'" '+(v.actual?'data-actual-only="true"':'data-delta="'+(v.delta==null?'':v.delta)+'"')+'>'+ (v.actual?'<span class="gm-actual-only">Actuals only</span>':v.delta==null?'—':(v.delta>0?'Overcall ':v.delta<0?'Undercall ':'')+deltaLabel(v.delta,metric.unit)+(v.percent==null?'':' ('+signedPercent(v.percent)+')'))+'</td>').join('')+'</tr></tbody></table></div></div>';
  })).join('');
 }''')
    # Actuals-only periods need one amount column, rather than repeated zero variances.
    a=d.index('function renderSummary()');b=d.index('function updateScrollNote',a);summary=d[a:b]
    summary=summary.replace("  const span=1+state.tableTrends.length*2,colCount=1+dimensions.length+periods.length*span,depth=state.tableTrends.length?3:2;", "  const compared=p=>!combos.length||!metrics.length||!combos.every(c=>metrics.every(m=>actualOnly(p,c,m))),trendsFor=p=>compared(p)?state.tableTrends:[],spanFor=p=>1+trendsFor(p).length*2,colCount=1+dimensions.length+periods.reduce((n,p)=>n+spanFor(p),0),hasTrends=periods.some(p=>trendsFor(p).length),depth=hasTrends?3:2;")
    summary=summary.replace('for(const trend of state.tableTrends)', 'for(const trend of trendsFor(period))')
    summary=summary.replace('${span}', '${spanFor(period)}').replace('${state.tableTrends.length?2:1}', '${hasTrends?2:1}').replace('if(state.tableTrends.length){header', 'if(hasTrends){header')
    summary=summary.replace('periods.length*(100+state.tableTrends.length*170)', 'periods.reduce((n,p)=>n+100+trendsFor(p).length*170,0)')
    d=d[:a]+summary+d[b:]
    # Preserve all existing review-period choices and share them when switching view.
    s=s.replace("['FY','YTD','YTG'].map(kind", "['FY','YTD','YTG','H1','H2'].map(kind")
    s=s.replace("const start=kind==='YTG'?month+1:0,end=kind==='YTD'?month:11;", "const start=kind==='YTG'?month+1:kind==='H2'?6:0,end=kind==='YTD'?month:kind==='H1'?5:11;")
    shell=shell.replace("'scopeDrivers','monthStart'", "'scopeDrivers','periods','monthStart'")
    # Source identities stay immutable; presentation uses one ordered hierarchy.
    s=s.replace(" const availableRows=()=>allRows;", """ let orderKey='',orderCache;
 function sopOrder(){const key=JSON.stringify(state.reviewOrder||{});if(!orderCache||key!==orderKey){orderKey=key;orderCache=makeReviewOrder(allRows,families,bridgeOrder,contextFor,state.reviewOrder);}return orderCache;}
 const availableRows=()=>allRows;""")
    s=s.replace('.sort((a,b)=>bridgeOrder.indexOf(a.id)-bridgeOrder.indexOf(b.id))', '.sort((a,b)=>sopOrder().flat.indexOf(a.id)-sopOrder().flat.indexOf(b.id))')
    s=s.replace("  for(const target of bridgeOrder.map(id=>rowMap.get(id)).filter(r=>r.basis==='ef')){const last=segments.at(-1);if(last?.id===target.group)last.targets.push(target);else segments.push({id:target.group,targets:[target]});}", "  const ordered=sopOrder();for(const id of ordered.channels)segments.push({id,targets:ordered.targets[id].map(id=>rowMap.get(id))});")
    s=s.replace("measures:bridgeOrder.map(id=>rowMap.get(id)).filter(r=>contextFor(r)===target.id)", "measures:sopOrder().measures[target.id].map(id=>rowMap.get(id))")
    s=s.replace("data-control-key=\"'+type+'-'+id+'\"", "data-control-key=\"'+type+'-'+id+'\" data-order-kind=\"'+type+'\" data-order-id=\"'+id+'\" data-order-parent=\"'+(type==='channel'?'root':type==='target'?rowMap.get(id).group:contextFor(rowMap.get(id)))+'\" aria-description=\"Hold and drag to reorder within this parent. Alt plus Up or Down also moves this item.\"")
    s=s.replace("scopeOptions:()=>live.scope(state)", "getReviewOrder:()=>JSON.parse(JSON.stringify(sopOrder())),setReviewOrder:order=>{state.reviewOrder=order;update();},resetReviewOrder:()=>{delete state.reviewOrder;update();},scopeOptions:()=>live.scope(state)")
    return d,s,shell
