"""Native matrix measure families instead of one disconnected column switch.

No business kernel changes. Static numeric fields share the same row/period
context, allowing Plan/Benchmark results to be reused by values, formats and
colours. A native field-parameter UI is considered only after query proof.
"""
from copy import deepcopy

import prepared

ADMIT="HASONEVALUE('fm_native_metric'[RowID])&&[N Source OK]=1&&[N Period Available]=1"
PALETTE='''IF(NOT ISBLANK(_value),VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3"))'''


def name(kind,window=12):
    return 'P Fixed Plan' if kind=='plan' else 'P Fixed '+str(window)+'M '+{'abs':'Variance','pct':'Variance %','color':'Color'}[kind]


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(database)
    fmt=prepared.adapter.selection.OLD.expression_text(m['N Summary Cell']['formatStringDefinition']['expression'])
    declaration='RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"'
    if fmt.count(declaration)!=1:
        raise ValueError('Unknown qualified numeric formatter')
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    for kind,window in [('plan',0),*[(k,w) for w in (6,12,24) for k in ('abs','pct','color')]]:
        n=name(kind,window)
        if n in m:
            raise ValueError('Static family already installed')
        if kind=='plan':
            expression='IF('+ADMIT+',[N Plan])'
        else:
            source='N Variance' if kind=='abs' else 'N Variance %'
            value='CALCULATE(['+source+"],REMOVEFILTERS('fm_native_trend'),TREATAS({"+str(window)+"},'fm_native_trend'[Window]))"
            gate='IF('+ADMIT+'&&[N Actual Only]<>1,'
            expression=gate+('VAR _value='+value+' RETURN '+PALETTE if kind=='color' else value)+')'
        measure={'name':n,'expression':expression,'isHidden':True}
        if kind!='color':
            measure['formatStringDefinition']={'expression':fmt.replace(declaration,'TRUE()' if kind=='pct' else 'FALSE()')}
        target.append(measure)
    return fixed


def query(original,window=12):
    # Preserve the exact native filters and row/period rollups. Only the
    # comparison-column dimension and numeric projections change.
    source=original[:original.index('VAR __DS0PrimaryWindowed')].rstrip()
    for field in ('ColumnLabel','Sort'):
        marker="\t\t\t'fm_native_columns'["+field+'],\n'
        if source.count(marker)!=1:
            raise ValueError('Unknown captured column dimension')
        source=source.replace(marker,'')
    marker='''"N_Summary_Cell", 'fm_native_measures'[N Summary Cell],
			"v_N_Summary_Cell_FormatString", IGNORE('fm_native_measures'[_N Summary Cell FormatString]),
			"N GM Summary Color", IGNORE('fm_native_measures'[N GM Summary Color])'''
    if source.count(marker)!=1:
        raise ValueError('Unknown captured native projections')
    projections=[]
    for kind in ('plan','abs','pct'):
        n=name(kind,window)
        projections.extend(['"V'+kind+'",\'fm_native_measures\'['+n+']',
            '"F'+kind+'",IGNORE(\'fm_native_measures\'[_'+n+' FormatString])'])
    projections.append('"Color",IGNORE(\'fm_native_measures\'['+name('color',window)+'])')
    return source.replace(marker,',\n'.join(projections))+'\nEVALUATE __DS0Core'
