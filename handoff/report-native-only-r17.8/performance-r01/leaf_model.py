"""Prepared leaf lookups with exact grouped aggregate/out-of-domain fallback.

The fast domain is one actual sector row, one country/cycle, six native metrics,
Units/Local (or single-currency Share) with no explicit fact/catalog override.
Every other context retains the complete grouped calculation. No sector cap,
cohort guard, invalid/empty state or weighted aggregate Share rule is removed.
"""
import bulk_fit
import leaf_prepare
import prepared


def helper(benchmark):
    clauses=[]
    for metric in leaf_prepare.METRICS:
        for display in ('Units','Value'):
            for window in ((6,12,24) if benchmark else (0,)):
                selector=metric+'|'+display+'|'+str(window)
                clauses.extend(['"'+selector+'"',"SUM('fm_leaf_kpi'["+leaf_prepare.field(metric,display,window)+'])'])
    return '''VAR _row=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _w='''+("SELECTEDVALUE('fm_native_trend'[Window],12)" if benchmark else '0')+'''
RETURN SWITCH(_row&"|"&_display&"|"&FORMAT(_w,"0"),'''+','.join(clauses)+')'


def body(prefix,benchmark,data):
    fallback='[P Grouped '+('Benchmark' if benchmark else 'Plan')+']'
    before='''VAR _row=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _year=SELECTEDVALUE('fm_native_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType])
VAR _window=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _leaf=ISINSCOPE('fm_native_scope'[SectorLabel])&&HASONEVALUE('fm_native_scope'[Sector])
 &&HASONEVALUE('fm_native_scope'[GrowthDriver])&&HASONEVALUE('fm_review_files'[Country])
 &&HASONEVALUE('fm_review_files'[DemandCycle])
VAR _domain=_leaf&&_row IN {"market","abbott","pi","net","ef","share"}
 &&_kind IN {"FY","YTD","YTG","H1","H2"}&&NOT ISBLANK(_year)
 &&_year>='''+str(data['receipt']['YearMin'])+'&&_year<='+str(data['receipt']['YearMax'])+'''
 &&(_display="Units"||(_display="Value"&&(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"||_row="share")))
 &&NOT ISFILTERED('fm_review_facts')&&NOT ISFILTERED('fm_native_catalog')
 &&[P Leaf Axis Safe]=1'''+('&&_window IN {6,12,24}' if benchmark else '')+'''
RETURN IF(_domain,
'''
    inside=prefix+'''
VAR _cut=[N Cutoff]
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _currencyOK=_display<>"Value"||COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _pairs=SELECTCOLUMNS(GENERATE(_files,VAR _gd='fm_native_files'[GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"__Sector",'fm_native_scope'[Sector])),
 "ID",'fm_native_files'[SourceRevisionID],"Sector",[__Sector])
VAR _series=CALCULATETABLE('fm_leaf_series',TREATAS(_pairs,'fm_leaf_series'[SourceID],'fm_leaf_series'[Sector]))
VAR _cutOrdinal=IF(NOT ISBLANK(_cut),DATEDIFF(DATE(2000,1,1),_cut,MONTH))
VAR _sameCut=COUNTROWS(FILTER(_series,IF(_row="ef",'fm_leaf_series'[EF],'fm_leaf_series'[IMS])<>_cutOrdinal))=0
VAR _keys=SELECTCOLUMNS(_series,"K",'fm_leaf_series'[Key])
RETURN IF(_sourceOK&&_currencyOK&&NOT ISBLANK(_cut),
 IF(_sameCut,CALCULATE(['''+('P Leaf Benchmark' if benchmark else 'P Leaf Plan')+'''],
 TREATAS(_keys,'fm_leaf_kpi'[Key]),TREATAS({_year},'fm_leaf_kpi'[Year]),
 TREATAS({_kind},'fm_leaf_kpi'[Kind])),'''+fallback+'))'
    return before+inside+','+fallback+')'


def patch(database,data):
    fixed=bulk_fit.patch(database)
    old=prepared.adapter.planning.measures(database);current=prepared.adapter.planning.measures(fixed)
    if any(t['name'].startswith('fm_leaf_') for t in fixed['model']['tables']):
        raise ValueError('Leaf serving already installed')
    fixed['model']['tables'].extend(leaf_prepare.tables(data))
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    for n in ('N Plan','N Benchmark'):
        target.append({'name':'P Grouped '+n[2:],'expression':current[n]['expression'],'isHidden':True})
    prefix=prepared.adapter.selection.OLD.expression_text(old['N Monthly Numerator']['expression'])
    prefix=prefix[:prefix.index('VAR _date=')]
    minimum=data['minMonth'];maximum=data['maxMonth']
    safe="""VAR _dates=ALL('fm_review_axis'[Month])
RETURN INT(COUNTROWS(_dates)="""+str(maximum-minimum+1)+'''
 &&MINX(_dates,'fm_review_axis'[Month])=EDATE(DATE(2000,1,1),'''+str(minimum)+''')
 &&MAXX(_dates,'fm_review_axis'[Month])=EDATE(DATE(2000,1,1),'''+str(maximum)+''')
 &&COUNTROWS(FILTER(_dates,'fm_review_axis'[Month]<>DATE(YEAR('fm_review_axis'[Month]),MONTH('fm_review_axis'[Month]),1)))=0)'''
    for n,e in [('P Leaf Plan',helper(False)),('P Leaf Benchmark',helper(True)),('P Leaf Axis Safe',safe)]:
        target.append({'name':n,'expression':e,'isHidden':True})
    for n in ('N Plan','N Benchmark'):
        current[n]['expression']=body(prefix,n=='N Benchmark',data)
    return fixed
