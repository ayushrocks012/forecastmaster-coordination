"""Retain exact cache-miss behavior behind a zero/one-row iterator.

Earlier IF and model-filter gates still planned the full fallback in healthy
contexts. This separate experiment evaluates each branch only under its own
zero/one-row iterator. A ready cache and an exact R03 fallback remain mutually
exclusive, including genuine BLANK and known-zero results.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import cache_diagnostic
import cacheprobe
import prepared
import regression


def patch(database):
    fixed=deepcopy(database);measures=prepared.adapter.planning.measures(fixed)
    for name,old,fast in [('N Plan',cache_diagnostic.PLAN,'IF(_ratio,DIVIDE(_num,_den),_num)'),
            ('N Benchmark',cache_diagnostic.BENCH,
             'IF(_ratio,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_den),COALESCE(_actual,0)+COALESCE(_future,0))')]:
        body=measures[name]['expression']
        if body.count(old)!=1:raise ValueError('Unknown original cache/fallback dispatch')
        slow='[P R03 '+name[2:]+']'
        measures[name]['expression']=body.replace(old,
            'VAR _fastResult=SUMX(FILTER({1},_ready),'+fast+')\n'+
            'VAR _fallbackResult=SUMX(FILTER({1},NOT _ready),'+slow+')\n'+
            'RETURN _fastResult+_fallbackResult')
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve previous iterator experiment')
    binding=regression.checked(source)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for name in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'iterator-dispatch-cache',
        'CompanyDeployment':False,'OriginalFallbackExpressionsPreserved':True},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(cacheprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
