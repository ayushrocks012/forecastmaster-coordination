"""Keep exact fallback semantics behind an explicit internal evaluation gate.

A diagnostic proved 12s with the conditional legacy branch versus 2.6s for the
same complete cached results alone. This tests a gated additive composition,
without removing missing-data, catalog or FX fallback behavior.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import cache_diagnostic
import prepared
import regression


def patch(database):
    fixed=deepcopy(database)
    measures=prepared.adapter.planning.measures(fixed)
    if any(t['name']=='fm_cache_path' for t in fixed['model']['tables']):
        raise ValueError('Gate already installed')
    fixed['model']['tables'].append({'name':'fm_cache_path','isHidden':True,
        'columns':[{'name':'Legacy','dataType':'int64','type':'calculatedTableColumn','sourceColumn':'[Legacy]','summarizeBy':'none'}],
        'partitions':[{'name':'fm_cache_path','mode':'import','source':{'type':'calculated','expression':'DATATABLE("Legacy",INTEGER,{{0},{1}})'}}]})
    for name,marker,fast in [
        ('N Plan',cache_diagnostic.PLAN,'IF(_ratio,DIVIDE(_num,_den),_num)'),
        ('N Benchmark',cache_diagnostic.BENCH,'''IF(_ratio,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_den),
 COALESCE(_actual,0)+COALESCE(_future,0))''')]:
        expression=measures[name]['expression']
        if expression.count(marker)!=1:
            raise ValueError('Unknown prepared kernel')
        fallback='P R03 '+name[2:]
        original=measures[fallback]['expression']
        if original.startswith('IF(SELECTEDVALUE('):
            raise ValueError('Unknown fallback wrapper')
        measures[fallback]['expression']='IF(SELECTEDVALUE(\'fm_cache_path\'[Legacy],1)=1,\n'+original+')'
        measures[name]['expression']=expression.replace(marker,
            'RETURN IF(_ready,'+fast+')+CALCULATE(['+fallback+'''],
 TREATAS({INT(NOT _ready)},'fm_cache_path'[Legacy]))''')
    return fixed


def build(destination,source):
    if destination.exists():
        raise ValueError('Preserve previous gate test')
    binding=regression.checked(source)
    before=json.loads((source/'candidate.json').read_text())
    after=patch(before)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(after,ensure_ascii=False))
    for name in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    for path in (Path(__file__),Path(cache_diagnostic.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'source-cache-gated-fallback',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest(),
        'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
