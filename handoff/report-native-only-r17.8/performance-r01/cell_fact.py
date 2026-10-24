"""Prepared native Executive cells: numeric amount, exact format and alert.

Leaf queries read one physical cell. Parent/arbitrary aggregate Share remains
the complete original calculation. Missing cache keys, changed cutoffs and
unsupported filters fall back. No financial source data or UI policy changes.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import leaf_prepare
import prepared
import probe
import regression
import sector_dim

FACT='fm_executive_cells'
VALUE='P Executive Cell'
COLOR='P Executive Cell Color'
PREPARED_CUT='P Executive Prepared Cut'


def normalize(name):
    tables=(sector_dim.DIM,'fm_native_scope','fm_native_periods','fm_native_columns','fm_native_headline',
            'fm_native_chart_trend','fm_native_trend')
    return "VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\nRETURN CALCULATE(["+name+'],'+','.join(
        "REMOVEFILTERS('"+n+"')" for n in tables)+",TREATAS(_drivers,'fm_native_scope'[GrowthDriver]))"


def arithmetic(metric,display,window,kind,color=False):
    if kind=='plan':return 'BLANK()' if color else "'fm_leaf_kpi'["+leaf_prepare.field(metric,display,0)+']'
    cut='EF' if metric=='ef' else 'IMS'
    body="VAR _p='fm_leaf_kpi'["+leaf_prepare.field(metric,display,0)+"]\nVAR _b='fm_leaf_kpi'["+leaf_prepare.field(metric,display,window)+''']
VAR _cut=LOOKUPVALUE('fm_leaf_series'['''+cut+'''],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])
VAR _end=('fm_leaf_kpi'[Year]-2000)*12+SWITCH('fm_leaf_kpi'[Kind],"YTD",MOD(_cut,12),"H1",5,11)
VAR _pair=NOT ISBLANK(_p)&&NOT ISBLANK(_b)&&_end>_cut
'''
    if color:
        return body+'''VAR _pct=IF(_pair,DIVIDE(_p-_b,ABS(_b)))
RETURN IF(NOT ISBLANK(_pct),VAR _size=ABS(_pct)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3"))'''
    return body+'RETURN IF(_pair,'+('_p-_b' if kind=='abs' else 'DIVIDE(_p-_b,ABS(_b))')+')'


def table():
    columns=[('SourceID','string'),('SectorLabel','string'),('PeriodKey','string'),('Scenario','string'),
        ('Metric','string'),('Display','string'),('ColumnKey','string'),('Amount','double'),('Color','string')]
    parts=[]
    for metric in leaf_prepare.METRICS:
        for display in ('Units','Value'):
            for kind,w in [('plan',0),*[(k,w) for w in (6,12,24) for k in ('abs','pct')]]:
                key='plan' if kind=='plan' else str(w)+':'+kind
                fields=[json.dumps(n)+",'fm_leaf_kpi'["+n+']' for n in ('SourceID','SectorLabel','PeriodKey','Scenario')]
                fields+=['"Metric",'+json.dumps(metric),'"Display",'+json.dumps(display),'"ColumnKey",'+json.dumps(key),
                    '"Amount",('+arithmetic(metric,display,w,kind)+')','"Color",('+arithmetic(metric,display,w,kind,True)+')']
                parts.append("SELECTCOLUMNS('fm_leaf_kpi',"+','.join(fields)+')')
    fmt='''VAR _row='''+"'"+FACT+"'[Metric]"+'''
VAR _pct=RIGHT('''+"'"+FACT+"'[ColumnKey],3)=\"pct\""+'''
VAR _country=LOOKUPVALUE('fm_native_files'[Country],'fm_native_files'[SourceRevisionID],'''+"'"+FACT+"'[SourceID])"+'''
VAR _ccy=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_country)
VAR _symbol=IF('''+"'"+FACT+"'[Display]=\"Units\",\"\",SWITCH(_ccy,\"GBP\",\"£\",\"EUR\",\"€\",\"USD\",\"$\",\"\"))"+'''
VAR _value='''+"'"+FACT+"'[Amount]"+'''
VAR _abs=ABS(_value)
VAR _display=IF(_value<0,"−","")&_symbol&SWITCH(TRUE(),
 _abs>=1000000,FORMAT(_abs/1000000,"#,0.00","en-GB")&"m",
 _abs>=1000,FORMAT(_abs/1000,"#,0.0","en-GB")&"k",FORMAT(_abs,"#,0","en-GB"))
VAR _literal=UNICHAR(34)&_display&UNICHAR(34)
RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",_literal&";"&_literal&";"&_literal)'''
    return {'name':FACT,'isHidden':True,
        'columns':[{'name':n,'dataType':t,'type':'calculatedTableColumn','sourceColumn':'['+n+']','summarizeBy':'none'} for n,t in columns]+
            [{'name':'FormatCode','dataType':'string','type':'calculated','expression':fmt,'summarizeBy':'none'}],
        'partitions':[{'name':FACT,'mode':'import','source':{'type':'calculated','expression':'UNION('+','.join(parts)+')'}}]}


def prefix():
    return '''VAR _leaf=ISINSCOPE('''+"'"+sector_dim.DIM+"'[SectorLabel])"+'''
VAR _row=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],SELECTEDVALUE('fm_review_files'[Country]))
VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _w=SELECTEDVALUE('fm_native_columns'[Window])
VAR _allowed=_key="plan"||_w IN VALUES('fm_native_trend'[Window])
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _pcut=['''+PREPARED_CUT+''']
VAR _meta=HASONEVALUE('fm_native_metric'[RowID])&&[N Source OK]=1&&[N Period Available]=1
VAR _domain=_leaf&&_meta&&_allowed&&HASONEVALUE('fm_review_files'[Country])&&HASONEVALUE('fm_review_files'[DemandCycle])
 &&_row IN {"market","abbott","share","pi","net","ef"}&&(_display<>"Value"||NOT ISBLANK(_currency))
 &&(_display="Units"||(_display="Value"&&(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"||_row="share")))
 &&NOT ISFILTERED('fm_review_facts')&&NOT ISFILTERED('fm_native_catalog')&&NOT ISFILTERED('fm_native_rows')
 &&NOT ISFILTERED('fm_native_currency_map')&&NOT ISBLANK(_pcut)&&[N Cutoff]=_pcut&&[N Fit Cutoff]=_pcut
VAR _count=CALCULATE(COUNTROWS('''+"'"+FACT+"'),TREATAS({_display},'"+FACT+"'[Display]),"+'''
 FILTER(ALL('''+"'"+FACT+"'[Scenario]),ISBLANK(_scenario)||'"+FACT+"'[Scenario]=_scenario))"+'''
VAR _use=_domain&&_count=1
'''


def filtered(column,amount=False):
    return "CALCULATE("+('SUM' if amount else 'SELECTEDVALUE')+"('"+FACT+"'["+column+"]),TREATAS({_display},'"+FACT+"'[Display]),FILTER(ALL('"+FACT+"'[Scenario]),ISBLANK(_scenario)||'"+FACT+"'[Scenario]=_scenario))"


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if any(t['name']==FACT for t in fixed['model']['tables']):raise ValueError('Prepared cells already installed')
    fixed['model']['tables'].append(table())
    for i,(source,dimension,column) in enumerate([('SourceID','fm_native_files','SourceRevisionID'),('SourceID','fm_review_files','SourceRevisionID'),
            ('SectorLabel',sector_dim.DIM,'SectorLabel'),('PeriodKey','fm_native_periods','PeriodKey'),
            ('Metric','fm_native_metric','RowID'),('Display','fm_native_display','Display'),('ColumnKey','fm_native_columns','ColumnKey')]):
        fixed['model']['relationships'].append({'name':'ExecutiveCell-'+str(i),'fromTable':FACT,'fromColumn':source,'fromCardinality':'many',
            'toTable':dimension,'toColumn':column,'toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    for name in ('N Cutoff','N Fit Cutoff'):
        alias='P Executive Original '+name[2:]
        target.append({'name':alias,'expression':m[name]['expression'],'isHidden':True})
        m[name]['expression']=normalize(alias)
    # Keep all source-scenario dependencies in place, including View/Display.
    m['N Source OK']['expression']=normalize('P Leaf Cohort Guard')
    m['P Leaf Source ID']['expression']=normalize('P Leaf Source Inner')
    cut='''VAR _id=[P Leaf Source ID]
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _ef=NOT(_row IN {"market","abbott","share","pi","net"})
VAR _ordinal=IF(_ef,CALCULATE(MAX('fm_leaf_series'[EF]),TREATAS({_id},'fm_leaf_series'[SourceID])),
 CALCULATE(MAX('fm_leaf_series'[IMS]),TREATAS({_id},'fm_leaf_series'[SourceID])))
RETURN IF(NOT ISBLANK(_id)&&NOT ISBLANK(_ordinal),EDATE(DATE(2000,1,1),_ordinal))'''
    target.extend([{'name':'P Executive Prepared Cut Inner','expression':cut,'isHidden':True},
        {'name':PREPARED_CUT,'expression':normalize('P Executive Prepared Cut Inner'),'isHidden':True}])
    oldfmt=m['N Summary Cell']['formatStringDefinition']['expression']
    target.append({'name':VALUE,'expression':prefix()+'RETURN IF(_use,'+filtered('Amount',True)+',[N Summary Cell])',
        'formatStringDefinition':{'expression':prefix()+'RETURN IF(_use,'+filtered('FormatCode')+',('+oldfmt+'))'}})
    # Retain the exact model/report-local colour contract for every fallback.
    legacy='''VAR _window=SELECTEDVALUE('fm_native_columns'[Window])
RETURN IF(HASONEVALUE('fm_native_metric'[RowID])&&HASONEVALUE('fm_native_columns'[ColumnKey])&&_key<>"plan"
 &&_window IN VALUES('fm_native_trend'[Window])&&[N Source OK]=1&&[N Period Available]=1&&[N Actual Only]<>1,
 VAR _value=CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),TREATAS({_window},'fm_native_trend'[Window]))
 RETURN IF(NOT ISBLANK(_value),VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3")))'''
    target.append({'name':COLOR,'isHidden':True,'expression':prefix()+'RETURN IF(_use,'+filtered('Color')+',('+legacy+'))'})
    return fixed


def query(original):
    changed=sector_dim.query(original)
    begin=changed.index('/* USER DAX BEGIN */')+len('/* USER DAX BEGIN */');end=changed.index('/* USER DAX END */')
    changed=changed[:begin]+'\n['+COLOR+']\n'+changed[end:]
    return changed.replace("'fm_native_measures'[N Summary Cell]","'fm_native_measures'["+VALUE+']').replace(
        "'fm_native_measures'[_N Summary Cell FormatString]","'fm_native_measures'[_"+VALUE+' FormatString]')


def build(destination,source):
    if destination.exists():raise ValueError('Preserve prepared cell attempt')
    binding=regression.checked(source)
    if binding.get('Prototype')!='sector-star-serving':raise ValueError('Require sector star source')
    db=patch(json.loads((source/'candidate.json').read_text()))
    queries=json.loads((source/'queries.json').read_text())
    for q in queries:
        if q['model']=='candidate' and '-expanded/' in q['name']:
            # Already uses the sector dimension; replacement is idempotent.
            q['query']=query(q['query'])
    queries.append({'name':'prepared-cell-population','model':'candidate','query':"EVALUATE ROW(\"Cells\",COUNTROWS('"+FACT+"'))"})
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('baseline.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    for p in (Path(__file__),Path(leaf_prepare.__file__)):
        shutil.copy2(p,destination/p.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'prepared-executive-cells',
        'ExpectedPreparedCells':1764000,'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries),'ExpectedPreparedCells':1764000}


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    requested=json.loads((directory/'queries.json').read_text())
    by={r['name']:r for r in results}
    if len(by)!=len(results) or set(by)!={r['name'] for r in requested} or any('error' in r for r in results):
        raise AssertionError({'Failed':[r['name'] for r in results if 'error' in r]})
    expected=json.loads((directory/'expected.json').read_text());pairs=[]
    for name,old in by.items():
        if not name.endswith('/baseline'):continue
        new=by[name[:-8]+'candidate'];a,b=old['resultSets'],sector_dim.canonical(new['resultSets'])
        if '/full-core/' in name:a,b=probe.full_core_sets(a),probe.full_core_sets(b)
        if not all(s['rows'] for s in a) or not probe.equal(a,b):
            raise AssertionError('Changed complete value/format/colour/population: '+name)
        key=name[:-9]
        if key in expected and (len(old['rows'])!=1 or not probe.equal(expected[key],old['rows'][0])):
            raise AssertionError('Independent scalar oracle: '+key)
        if '/full-core/' in name:
            labels={r.get('fm_native_scope[SectorLabel]') for r in old['rows'] if r.get('fm_native_scope[SectorLabel]') is not None}
            if len(labels)!=150:raise AssertionError('Incomplete sector population')
        pairs.append({'Query':key,'R03Ms':old['elapsedMs'],'CandidateMs':new['elapsedMs']})
    required={'prepared-population':{'[Facts]':504000,'[Files]':20,'[Scope]':600,'[Sectors]':150},
        'leaf-population':binding['ExpectedLeafPopulation'],'narrow-population':binding['ExpectedNarrowPopulation'],
        'sector-dimension-population':{'[Rows]':150,'[Labels]':150},
        'prepared-cell-population':{'[Cells]':binding['ExpectedPreparedCells']}}
    for name,expected_rows in required.items():
        if by[name]['rows']!=[expected_rows]:raise AssertionError('Population changed: '+name)
    return {'Stage':'LOCAL_PREPARED_CELL_PROBE','Queries':len(results),'Pairs':pairs,'Mismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'CompanyOrDesktopQualified':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
