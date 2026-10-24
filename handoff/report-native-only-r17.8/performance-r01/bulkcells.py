"""Isolated R03 bulk-month Plan/Benchmark experiment; not a receiving adapter.

Collect the required physical fact groups once per kernel instead of calling
the source/member/month kernel repeatedly. Preserve the exact R03 kernels as
fallbacks for converted currency and unsupported catalog/filter contexts.
No new serving table, relationship or source mutation is needed.
"""
from copy import deepcopy

import prepared
import strictcells


def body(original, monthly, benchmark):
    source = monthly[:monthly.index('VAR _date=')]
    period = original[:original.index('VAR _ratio=')]
    # _cut remains the existing guarded cutoff, including mixed-date refusal.
    context = '''
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _single=COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _fast=_row IN {"market","abbott","share","pi","net","ef"}
 &&NOT ISFILTERED('fm_review_facts')
 &&(_display="Units"||(_display="Value"&&_single&&SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"))
RETURN IF(_fast,
'''
    aggregate = '''
VAR _ratio=_row="share"
VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _fitCut=[N Fit Cutoff]
VAR _definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row&&'fm_native_catalog'[Display]=_display)
VAR _numComponent=IF(_row="ef","ef-ads-"&LOWER(_display),MAXX(_definition,'fm_native_catalog'[Component]))
VAR _denComponent=IF(_ratio,MAXX(_definition,'fm_native_catalog'[Denominator]))
VAR _channel=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[Channel]))
VAR _sub=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[SubChannel]))
VAR _pairs=SELECTCOLUMNS(GENERATE(_files,
 VAR _gd='fm_native_files'[GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"__Sector",'fm_native_scope'[Sector])),
 "ID",'fm_native_files'[SourceRevisionID],"Sector",[__Sector])
VAR _needed=FILTER(ALL('fm_review_axis'[Month]),
 ('fm_review_axis'[Month]>=_start&&'fm_review_axis'[Month]<=_end)
 ||('fm_review_axis'[Month]>=EDATE(_fitCut,1-_w)&&'fm_review_axis'[Month]<=_fitCut))
VAR _groups=CALCULATETABLE(SUMMARIZECOLUMNS(
 'fm_review_facts'[SourceRevisionID],'fm_review_facts'[Sector],
 'fm_review_facts'[Month],'fm_review_facts'[ComponentKey],
 "Raw",SUM('fm_review_facts'[Amount]),
 "Bad",SUMX('fm_review_facts',INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount])))),
 REMOVEFILTERS('fm_review_facts'),
 TREATAS(_pairs,'fm_review_facts'[SourceRevisionID],'fm_review_facts'[Sector]),
 TREATAS(_needed,'fm_review_facts'[Month]),
 TREATAS({_numComponent,_denComponent},'fm_review_facts'[ComponentKey]),
 FILTER(ALL('fm_review_facts'[Channel]),_channel="*"||'fm_review_facts'[Channel]=_channel),
 FILTER(ALL('fm_review_facts'[SubChannel]),_sub="*"||COALESCE('fm_review_facts'[SubChannel],"")=COALESCE(_sub,"")))
VAR _good=FILTER(_groups,[Bad]=0)
VAR _monthly0=GROUPBY(_good,'fm_review_facts'[Month],
 "N",SUMX(CURRENTGROUP(),IF('fm_review_facts'[ComponentKey]=_numComponent,[Raw])),
 "D",SUMX(CURRENTGROUP(),IF(_ratio&&'fm_review_facts'[ComponentKey]=_denComponent,[Raw])))
VAR _monthly=SELECTCOLUMNS(_monthly0,"Date",CONVERT('fm_review_facts'[Month],DATETIME),"N",[N],"D",[D])
VAR _period=NATURALLEFTOUTERJOIN(_months,_monthly)
VAR _planValid=COUNTROWS(FILTER(_period,NOT ISBLANK([N])))=_count
VAR _denValid=COUNTROWS(FILTER(_period,NOT ISBLANK([D])))=_count
VAR _plan=IF(_planValid,IF(_ratio,IF(_denValid,DIVIDE(SUMX(_period,[N]),SUMX(_period,[D]))),SUMX(_period,[N])))
'''
    trend = '''
VAR _train0=FILTER(_monthly,[Date]>=EDATE(_fitCut,1-_w)&&[Date]<=_fitCut)
VAR _train=ADDCOLUMNS(_train0,"X",DATEDIFF(EDATE(_fitCut,1-_w),[Date],MONTH)+1,
 "Y",IF(_ratio,DIVIDE([N],[D]),[N]))
VAR _fitValid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=(_w+1)/2
VAR _mean=IF(_fitValid,AVERAGEX(_train,[Y]))
VAR _slope=IF(_fitValid,DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_mean)),SUMX(_train,POWER([X]-_mx,2))))
VAR _values=ADDCOLUMNS(_period,"BN",VAR _m=[Date]
 VAR _forecast=IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),
 _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))
 RETURN IF(_m<=_cut,[N],IF(_ratio,
 IF(NOT ISBLANK(_forecast)&&NOT ISBLANK([D]),_forecast*[D]),_forecast)))
VAR _benchValid=COUNTROWS(FILTER(_values,NOT ISBLANK([BN])))=_count
VAR _benchmark=IF(NOT ISBLANK(_fitCut)&&_benchValid,
 IF(_ratio,IF(_denValid,DIVIDE(SUMX(_values,[BN]),SUMX(_period,[D]))),SUMX(_values,[BN])))
'''
    result = '_benchmark' if benchmark else '_plan'
    fallback = 'P R03 Benchmark' if benchmark else 'P R03 Plan'
    return source + context + period + aggregate + (trend if benchmark else '') + '''
RETURN IF(_sourceOK&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0,
 ''' + result + '),[' + fallback + '])'


def patch(database):
    fixed = deepcopy(database)
    old = prepared.adapter.planning.measures(database)
    expected = prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text = prepared.adapter.selection.OLD.expression_text
    rows = next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    current = prepared.adapter.planning.measures(fixed)
    for name in ('N Plan','N Benchmark','N Monthly Numerator','N Summary Cell','N Headline Cell'):
        if text(old[name]['expression']) != text(expected[name]['expression']):
            raise ValueError('Unknown R03 kernel/cell: '+name)
    for name in ('N Plan','N Benchmark'):
        fallback = deepcopy(old[name])
        fallback.update(name='P R03 '+name[2:],isHidden=True)
        if fallback['name'] in old:
            raise ValueError('Bulk kernel already installed')
        rows.append(fallback)
        current[name]['expression']=body(text(old['N Plan']['expression']),
            text(old['N Monthly Numerator']['expression']),name=='N Benchmark')
    return fixed
