"""Local monthly/statistics serving model, with exact R03 cache-miss fallback.

Normal complete Local/Units contexts use SUM/COUNT over prepared columns.
Aggregate Share fits aggregate MONTHLY ratios, never summed sector ratios or
summed sector Share slopes. No serving data is created in Fabric by this file.
"""
from copy import deepcopy

import prepared
import strictcells

FIELDS={(m,d):m+'_'+d.lower() for m in ('market','abbott','pi','net','ef') for d in ('Units','Value')}
ROW='''VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
'''


def helper(count=False,denominator=False):
    selector='_display' if denominator else 'IF(_row="share","abbott",_row)&"|"&_display'
    choices=DISPLAYS if denominator else FIELDS
    clauses=[]
    for item in choices:
        metric,display=('market',item) if denominator else item
        label=display if denominator else metric+'|'+display
        clauses.extend(['"'+label+'"',('COUNT' if count else 'SUM')+"('fm_cache_monthly'["+FIELDS[metric,display]+'])'])
    return ROW+'RETURN SWITCH('+selector+','+','.join(clauses)+')'


DISPLAYS=('Units','Value')


def body(original,monthly,benchmark):
    source=monthly[:monthly.index('VAR _date=')]
    period=original[:original.index('VAR _ratio=')]
    context=ROW+'''
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _single=COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _common=[N Fit Cutoff]
VAR _pairs=SELECTCOLUMNS(GENERATE(_files,
 VAR _gd='fm_native_files'[GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"__Sector",'fm_native_scope'[Sector])),
 "ID",'fm_native_files'[SourceRevisionID],"Sector",[__Sector])
VAR _keys=CALCULATETABLE(VALUES('fm_cache_series'[Key]),
 TREATAS(_pairs,'fm_cache_series'[SourceID],'fm_cache_series'[Sector]))
VAR _members=COUNTROWS(_keys)
VAR _eligible=_sourceOK&&NOT ISBLANK(_common)&&_members>0&&_members=COUNTROWS(_pairs)
 &&_row IN {"market","abbott","share","pi","net","ef"}&&NOT ISFILTERED('fm_review_facts')
 &&(_display="Units"||(_display="Value"&&_single&&SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"))
'''
    totals='''
VAR _ratio=_row="share"
VAR _startOrdinal=DATEDIFF(DATE(2000,1,1),_start,MONTH)
VAR _endOrdinal=DATEDIFF(DATE(2000,1,1),_end,MONTH)
VAR _cutOrdinal=DATEDIFF(DATE(2000,1,1),_cut,MONTH)
VAR _selectedMonths=FILTER(ALL('fm_cache_monthly'[Month]),
 'fm_cache_monthly'[Month]>=_startOrdinal&&'fm_cache_monthly'[Month]<=_endOrdinal)
VAR _num=CALCULATE([P Cache N],TREATAS(_keys,'fm_cache_monthly'[Key]),_selectedMonths)
VAR _numCount=CALCULATE([P Cache Count N],TREATAS(_keys,'fm_cache_monthly'[Key]),_selectedMonths)
VAR _den=IF(_ratio,CALCULATE([P Cache D],TREATAS(_keys,'fm_cache_monthly'[Key]),_selectedMonths))
VAR _denCount=IF(_ratio,CALCULATE([P Cache Count D],TREATAS(_keys,'fm_cache_monthly'[Key]),_selectedMonths))
VAR _validPeriod=NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&COUNTROWS(_selectedMonths)=_count
'''
    plan='''
VAR _ready=_eligible&&_validPeriod&&_numCount=_count*_members&&(_row<>"share"||_denCount=_count*_members)
RETURN IF(_ready,IF(_ratio,DIVIDE(_num,_den),_num),[P R03 Plan])'''
    bench='''
VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _stats=CALCULATETABLE('fm_cache_statistics',TREATAS(_keys,'fm_cache_statistics'[Key]),
 TREATAS({_row},'fm_cache_statistics'[Metric]),TREATAS({_display},'fm_cache_statistics'[Display]),
 TREATAS({_w},'fm_cache_statistics'[Window]))
VAR _fitReady=COUNTROWS(_stats)=_members&&SUMX(_stats,'fm_cache_statistics'[Ready])=_members
VAR _fitFirst=DATEDIFF(DATE(2000,1,1),_common,MONTH)-_w+1
VAR _trainingMonths=FILTER(ALL('fm_cache_monthly'[Month]),
 'fm_cache_monthly'[Month]>=_fitFirst&&'fm_cache_monthly'[Month]<_fitFirst+_w)
VAR _monthly=SUMMARIZECOLUMNS('fm_cache_monthly'[Month],TREATAS(_keys,'fm_cache_monthly'[Key]),_trainingMonths,
 "N",[P Cache N],"D",[P Cache D])
VAR _train=ADDCOLUMNS(_monthly,"X",'fm_cache_monthly'[Month]-_fitFirst+1,"Y",DIVIDE([N],[D]))
VAR _groupMean=IF(COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w,AVERAGEX(_train,[Y]))
VAR _mx=(_w+1)/2
VAR _groupSlope=IF(NOT ISBLANK(_groupMean),
 DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_groupMean)),SUMX(_train,POWER([X]-_mx,2))))
VAR _mean=IF(_ratio&&_members>1,_groupMean,SUMX(_stats,'fm_cache_statistics'[Mean]))
VAR _slope=IF(_ratio&&_members>1,_groupSlope,SUMX(_stats,'fm_cache_statistics'[Slope]))
VAR _actualMonths=FILTER(_selectedMonths,'fm_cache_monthly'[Month]<=_cutOrdinal)
VAR _futureMonths=FILTER(_selectedMonths,'fm_cache_monthly'[Month]>_cutOrdinal)
VAR _actualCount=MAX(0,MIN(_endOrdinal,_cutOrdinal)-_startOrdinal+1)
VAR _futureCount=_count-_actualCount
VAR _actual=CALCULATE([P Cache N],TREATAS(_keys,'fm_cache_monthly'[Key]),_actualMonths)
VAR _actualReady=CALCULATE([P Cache Count N],TREATAS(_keys,'fm_cache_monthly'[Key]),_actualMonths)=_actualCount*_members
VAR _futureDen=SUMMARIZECOLUMNS('fm_cache_monthly'[Month],TREATAS(_keys,'fm_cache_monthly'[Key]),_futureMonths,"D",[P Cache D])
VAR _future=IF(_ratio,SUMX(_futureDen,[D]*(_mean+_slope*('fm_cache_monthly'[Month]-_cutOrdinal+_w-(_w+1)/2))),
 SUMX(_futureMonths,_mean+_slope*('fm_cache_monthly'[Month]-_cutOrdinal+_w-(_w+1)/2)))
VAR _ready=_eligible&&_validPeriod&&_actualReady&&(_row<>"share"||_denCount=_count*_members)
 &&(_futureCount=0||(_fitReady&&NOT ISBLANK(_mean)&&NOT ISBLANK(_slope)))
RETURN IF(_ready,IF(_ratio,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_den),
 COALESCE(_actual,0)+COALESCE(_future,0)),[P R03 Benchmark])'''
    return source+context+period+totals+(bench if benchmark else plan)


def patch(database,tables):
    fixed=deepcopy(database)
    old=prepared.adapter.planning.measures(database)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    if {t['name'] for t in tables}!={'fm_cache_series','fm_cache_monthly','fm_cache_statistics'}:
        raise ValueError('Unknown serving preparation')
    if any(t['name'].startswith('fm_cache_') for t in fixed['model']['tables']):
        raise ValueError('Serving preparation already installed')
    for name in ('N Plan','N Benchmark','N Monthly Numerator','N Summary Cell','N Headline Cell'):
        if text(old[name]['expression'])!=text(expected[name]['expression']):
            raise ValueError('Unknown R03 expression: '+name)
    fixed['model']['tables'].extend(deepcopy(tables))
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    current=prepared.adapter.planning.measures(fixed)
    for name,expression in [('P Cache N',helper()),('P Cache Count N',helper(True)),
            ('P Cache D',helper(denominator=True)),('P Cache Count D',helper(True,True))]:
        target.append({'name':name,'expression':expression,'isHidden':True})
    for name in ('N Plan','N Benchmark'):
        fallback=deepcopy(old[name]);fallback.update(name='P R03 '+name[2:],isHidden=True)
        target.append(fallback)
        current[name]['expression']=body(text(old['N Plan']['expression']),text(old['N Monthly Numerator']['expression']),name=='N Benchmark')
    return fixed
