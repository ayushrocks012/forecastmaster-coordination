"""Native calculation-group comparison columns over the prepared model.

Replace the report's disconnected comparison switch, not the original business
measures. Items transform only the new Executive value; other report measures
and the approved custom chart retain their behavior. Native Desktop still needs
its own inspection and generated-query qualification after this probe.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import probe
import regression

TABLE='fm_exec_calc'
VALUE='P Executive Value'
COLOR='P Executive Color'


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if any(t['name']==TABLE for t in fixed['model']['tables']):raise ValueError('Calculation group already installed')
    fmt=m['N Summary Cell']['formatStringDefinition']['expression']
    old='RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"'
    if fmt.count(old)!=1:raise ValueError('Unknown exact compact formatter')
    items=[]
    for kind,w,label,ordinal in [('plan',0,'Plan',0),*[(k,w,str(w)+'M variance'+(' %' if k=='pct' else ''),w*10+(k=='pct')) for w in (6,12,24) for k in ('abs','pct')]]:
        if kind=='plan':
            numeric='SELECTEDMEASURE()'
        else:
            result='_p-_b' if kind=='abs' else 'DIVIDE(_p-_b,ABS(_b))'
            numeric='''VAR _allowed='''+str(w)+''' IN VALUES('fm_native_trend'[Window])
VAR _p=SELECTEDMEASURE()
VAR _b=CALCULATE([N Benchmark],REMOVEFILTERS('fm_native_trend'),TREATAS({'''+str(w)+'''},'fm_native_trend'[Window]))
RETURN IF(_allowed&&[N Actual Only]<>1&&NOT ISBLANK(_p)&&NOT ISBLANK(_b),'''+result+')'
        expression='IF(ISSELECTEDMEASURE(['+VALUE+']),('+numeric+'),SELECTEDMEASURE())'
        body='"0.0%;−0.0%;0.0%"' if kind=='pct' else '('+fmt.replace(old,'FALSE()')+')'
        items.append({'name':label,'ordinal':int(ordinal),'expression':expression,
            'formatStringDefinition':{'expression':'IF(ISSELECTEDMEASURE(['+VALUE+']),'+body+',SELECTEDMEASUREFORMATSTRING())'}})
    fixed['model']['tables'].append({'name':TABLE,'isHidden':True,
        'calculationGroup':{'precedence':10,'calculationItems':items},
        'columns':[{'name':'Comparison','dataType':'string','sourceColumn':'Name','sortByColumn':'Order'},
            {'name':'Order','dataType':'int64','sourceColumn':'Ordinal','isHidden':True,'summarizeBy':'none'}],
        'partitions':[{'name':TABLE,'mode':'import','source':{'type':'calculationGroup'}}]})
    fixed['model']['discourageImplicitMeasures']=True
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    target.append({'name':VALUE,'expression':'''IF(HASONEVALUE('fm_native_metric'[RowID])&&[N Source OK]=1&&[N Period Available]=1,[N Plan])''',
        'formatStringDefinition':{'expression':fmt.replace(old,"RIGHT(SELECTEDVALUE('"+TABLE+"'[Comparison],\"\"),1)=\"%\"")}})
    target.append({'name':COLOR,'isHidden':True,'expression':'''VAR _item=SELECTEDVALUE('''+"'"+TABLE+"'[Comparison])"+'''
VAR _window=SWITCH(_item,"6M variance",6,"6M variance %",6,"12M variance",12,"12M variance %",12,"24M variance",24,"24M variance %",24)
RETURN IF(HASONEVALUE('fm_native_metric'[RowID])&&NOT ISBLANK(_window)
 &&_window IN VALUES('fm_native_trend'[Window])&&[N Source OK]=1&&[N Period Available]=1&&[N Actual Only]<>1,
 VAR _value=CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),TREATAS({_window},'fm_native_trend'[Window]))
 RETURN IF(NOT ISBLANK(_value),VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3")))'''})
    return fixed


def query(original):
    begin=original.index('/* USER DAX BEGIN */')+len('/* USER DAX BEGIN */');end=original.index('/* USER DAX END */')
    changed=original[:begin]+'\n['+COLOR+']\n'+original[end:]
    return changed.replace("'fm_native_columns'[ColumnLabel]","'"+TABLE+"'[Comparison]").replace(
        "'fm_native_columns'[Sort]","'"+TABLE+"'[Order]").replace(
        "'fm_native_measures'[N Summary Cell]","'fm_native_measures'["+VALUE+']').replace(
        "'fm_native_measures'[_N Summary Cell FormatString]","'fm_native_measures'[_"+VALUE+' FormatString]')


def build(destination,source):
    if destination.exists():raise ValueError('Preserve calculation-group probe')
    binding=regression.checked(source)
    before=json.loads((source/'candidate.json').read_text());candidate=patch(before)
    queries=json.loads((source/'queries.json').read_text())
    for q in queries:
        if q['model']=='candidate' and '-expanded/' in q['name']:q['query']=query(q['query'])
    destination.mkdir(parents=True)
    for n,data in [('baseline',json.loads((source/'baseline.json').read_text())),('candidate',candidate),('queries',queries)]:
        (destination/(n+'.json')).write_text(json.dumps(data,ensure_ascii=False))
    for n in ('expected.json','preparation.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    runner=(source/'run_profile.ps1').read_text()
    old="if($p.Source -isnot [Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource])"
    new="if($p.Source -isnot [Microsoft.AnalysisServices.Tabular.CalculatedPartitionSource] -and !($t.Name -eq '"+TABLE+"' -and $p.Source -is [Microsoft.AnalysisServices.Tabular.CalculationGroupSource]))"
    if runner.count(old)!=1:raise ValueError('Unknown calculated-only runner admission')
    (destination/'run_profile.ps1').write_text(runner.replace(old,new))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'executive-calculation-group',
        'RunnerAdmission':'Calculated SAMPLE plus only the named built-in calculation-group partition; no external connection.',
        'DesktopOrCompanyQualified':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def canonical(sets):
    replace={TABLE+'[Comparison]':'fm_native_columns[ColumnLabel]',TABLE+'[Order]':'fm_native_columns[Sort]'}
    return [{'columns':[replace.get(c,c) for c in s['columns']],
        'rows':[{replace.get(k,k):v for k,v in row.items()} for row in s['rows']]} for s in sets]


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    by={r['name']:r for r in results}
    if len(results)!=22 or any('error' in r for r in results):raise AssertionError('Incomplete/failed calculation-group probe')
    pairs=[]
    for name,old in by.items():
        if not name.endswith('/baseline'):continue
        new=by[name[:-8]+'candidate'];a=old['resultSets'];b=canonical(new['resultSets'])
        if '/full-core/' in name:a,b=probe.full_core_sets(a),probe.full_core_sets(b)
        if not probe.equal(a,b):raise AssertionError('Value/format/colour/population mismatch: '+name)
        pairs.append({'Query':name[:-9],'R03Ms':old['elapsedMs'],'CandidateMs':new['elapsedMs']})
    return {'Stage':'LOCAL_EXECUTIVE_CALCULATION_GROUP_PROBE','Pairs':pairs,'Mismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'DesktopOrCompanyQualified':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
