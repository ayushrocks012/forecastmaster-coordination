"""Narrow prepared Plan/Benchmark facts with ordinary dimension relationships.

Remove the 48-column measure switch: metric, display and trend are physical
fact attributes. Raw facts, admission and grouped Share fallbacks stay intact.
All prepared blanks/zeros remain explicit. This remains a local snapshot.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import leaf_prepare
import leafprobe
import prepared
import regression

PLAN='fm_leaf_plans'
BENCH='fm_leaf_benchmarks'


def table(name,benchmark):
    columns=[('Key','int64'),('SourceID','string'),('SectorLabel','string'),('PeriodKey','string'),
        ('Scenario','string'),('Metric','string'),('Display','string'),*([('Window','int64')] if benchmark else []),('Amount','double')]
    parts=[]
    for metric in leaf_prepare.METRICS:
        for display in ('Units','Value'):
            for window in ((6,12,24) if benchmark else (0,)):
                fields=[json.dumps(n)+",'fm_leaf_kpi'["+n+']' for n in ('Key','SourceID','SectorLabel','PeriodKey','Scenario')]
                fields+=['"Metric",'+json.dumps(metric),'"Display",'+json.dumps(display)]
                if benchmark:fields+=['"Window",'+str(window)]
                fields+=['"Amount",\'fm_leaf_kpi\'['+leaf_prepare.field(metric,display,window)+']']
                parts.append("SELECTCOLUMNS('fm_leaf_kpi',"+','.join(fields)+')')
    expression='UNION('+','.join(parts)+')'
    return {'name':name,'isHidden':True,
        'columns':[{'name':n,'dataType':kind,'type':'calculatedTableColumn','sourceColumn':'['+n+']','summarizeBy':'none'} for n,kind in columns],
        'partitions':[{'name':name,'mode':'import','source':{'type':'calculated','expression':expression}}]}


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if any(t['name'] in (PLAN,BENCH) for t in fixed['model']['tables']):raise ValueError('Narrow facts already installed')
    fixed['model']['tables'].extend([table(PLAN,False),table(BENCH,True)])
    dims=[('SourceID','fm_native_files','SourceRevisionID','one'),('SourceID','fm_review_files','SourceRevisionID','one'),
        ('SectorLabel','fm_native_scope','SectorLabel','many'),('PeriodKey','fm_native_periods','PeriodKey','one'),
        ('Metric','fm_native_metric','RowID','one'),('Display','fm_native_display','Display','one')]
    for fact in (PLAN,BENCH):
        for i,(source,dimension,column,cardinality) in enumerate(dims+([('Window','fm_native_trend','Window','one')] if fact==BENCH else [])):
            fixed['model']['relationships'].append({'name':'Narrow-'+fact+'-'+str(i),'fromTable':fact,'fromColumn':source,
                'fromCardinality':'many','toTable':dimension,'toColumn':column,'toCardinality':cardinality,
                'crossFilteringBehavior':'oneDirection'})
    m['P Leaf Plan']['expression']="VAR _display=[N Display]\nRETURN CALCULATE(SUM('"+PLAN+"'[Amount]),TREATAS({_display},'"+PLAN+"'[Display]))"
    m['P Leaf Benchmark']['expression']="VAR _display=[N Display]\nVAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)\nRETURN CALCULATE(SUM('"+BENCH+"'[Amount]),REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'"+BENCH+"'[Window]),TREATAS({_display},'"+BENCH+"'[Display]))"
    for n,fact in [('N Plan',PLAN),('N Benchmark',BENCH)]:
        old="FILTER(ALL('fm_leaf_kpi'[Scenario]),ISBLANK(_scenario)||'fm_leaf_kpi'[Scenario]=_scenario)"
        if m[n]['expression'].count(old)!=1:raise ValueError('Require related leaf dispatch')
        m[n]['expression']=m[n]['expression'].replace(old,"FILTER(ALL('"+fact+"'[Scenario]),ISBLANK(_scenario)||'"+fact+"'[Scenario]=_scenario)")
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve narrow-fact probe')
    binding=regression.checked(source)
    if binding.get('Prototype')!='related-prepared-leaf':raise ValueError('Require related leaf source')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    queries=json.loads((source/'queries.json').read_text())
    queries.append({'name':'narrow-population','model':'candidate','query':"EVALUATE ROW(\"Plans\",COUNTROWS('"+PLAN+"'),\"Benchmarks\",COUNTROWS('"+BENCH+"'))"})
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('baseline.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    for path in (Path(__file__),Path(leaf_prepare.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'narrow-prepared-leaf',
        'ExpectedNarrowPopulation':{'[Plans]':252000,'[Benchmarks]':756000},'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def verify(directory):
    binding=regression.checked(directory);receipt=leafprobe.verify(directory)
    rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if next(r for r in rows if r['name']=='narrow-population')['rows']!=[binding['ExpectedNarrowPopulation']]:
        raise AssertionError('Changed narrow prepared population')
    receipt.update(Stage='LOCAL_NARROW_PREPARED_LEAF_PROBE',NarrowPopulation=binding['ExpectedNarrowPopulation'])
    return receipt


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
