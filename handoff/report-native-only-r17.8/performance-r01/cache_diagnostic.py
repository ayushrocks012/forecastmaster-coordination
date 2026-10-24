"""Diagnose serving-cache admission versus execution cost; never a release.

The forced model deliberately omits fallback/admission at its final return.
It may be compared ONLY on the pinned complete fabricated contexts. Numeric
agreement there cannot qualify source errors, sparse inputs or another scope.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import regression

PLAN='RETURN IF(_ready,IF(_ratio,DIVIDE(_num,_den),_num),[P R03 Plan])'
BENCH='''RETURN IF(_ready,IF(_ratio,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_den),
 COALESCE(_actual,0)+COALESCE(_future,0)),[P R03 Benchmark])'''


def build(destination,source):
    if destination.exists():
        raise ValueError('Preserve previous diagnosis')
    regression.checked(source)
    normal=json.loads((source/'candidate.json').read_text())
    measures=prepared.adapter.planning.measures(normal)
    plan,bench=(measures[n]['expression'] for n in ('N Plan','N Benchmark'))
    if plan.count(PLAN)!=1 or bench.count(BENCH)!=1:
        raise ValueError('Unknown cache candidate')
    rows=next(t for t in normal['model']['tables'] if t['name']=='fm_native_measures')['measures']
    definitions={name:plan.replace(PLAN,'RETURN '+value) for name,value in [
        ('P Debug Ready','INT(_ready)'),('P Debug Eligible','INT(_eligible)'),
        ('P Debug Members','_members'),('P Debug Count','_numCount'),('P Debug Expected','_count*_members')]}
    definitions['P Debug Benchmark Ready']=bench.replace(BENCH,'RETURN INT(_ready)')
    rows.extend({'name':n,'expression':v,'isHidden':True} for n,v in definitions.items())
    forced=deepcopy(normal);fm=prepared.adapter.planning.measures(forced)
    fm['N Plan']['expression']=plan.replace(PLAN,'RETURN IF(_ratio,DIVIDE(_num,_den),_num)')
    fm['N Benchmark']['expression']=bench.replace(BENCH,'''RETURN IF(_ratio,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_den),
 COALESCE(_actual,0)+COALESCE(_future,0))''')
    old=json.loads((source/'queries.json').read_text())
    scalar=next(q['query'] for q in old if q['name']=='market/Units/candidate')
    projection='ROW("Monthly",[N Monthly],"Plan",[N Plan],"Benchmark",[N Benchmark],"Pct",[N Variance %])'
    if scalar.count(projection)!=1:
        raise ValueError('Unknown scalar projection')
    scalar=scalar.replace(projection,'ROW('+','.join('"'+n+'",['+n+']' for n in definitions)+')')
    queries=[{'name':'admission-values','model':'baseline','query':scalar}]
    for metric in ('market','share'):
        query=next(q['query'] for q in old if q['name']==metric+'-expanded/full-core/candidate')
        for name,model in [('normal','baseline'),('forced','candidate')]:
            queries.append({'name':metric+'/'+name,'model':model,'query':query})
    destination.mkdir(parents=True)
    for name,data in [('baseline',normal),('candidate',forced),('queries',queries)]:
        (destination/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Kind':'DIAGNOSTIC_NOT_ACCEPTANCE',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest(),
        'Limit':'Forced fallback-free results apply only to these pinned complete fake contexts. Never deploy the forced model.'},indent=2))
    return {'Directory':str(destination),'Queries':len(queries),'Acceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
