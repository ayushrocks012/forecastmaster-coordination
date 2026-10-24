"""Compose the prepared path with the complete grouped fallback, not R03 loops.

No cache-miss context is removed. The full grouped Plan/Benchmark/training
expressions preserve the original source, blank, FX and weighted Share rules;
they avoid planning hundreds of calls into the old monthly iterator graph.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import bulk_fit
import cacheprobe
import prepared
import regression


def patch(database,baseline):
    fixed=deepcopy(database)
    current=prepared.adapter.planning.measures(fixed)
    old=prepared.adapter.planning.measures(baseline)
    complete=prepared.adapter.planning.measures(bulk_fit.patch(baseline))
    if any(n not in current for n in ('P R03 Plan','P R03 Benchmark')):
        raise ValueError('Require original complete cache dispatch')
    for n in ('N Plan','N Benchmark'):
        if current['P R03 '+n[2:]]['expression']!=old[n]['expression']:
            raise ValueError('Unknown original fallback')
        current['P R03 '+n[2:]]['expression']=complete[n]['expression']
    for n in ('N Fit Mean','N Fit Slope'):
        if current[n]['expression']!=old[n]['expression']:
            raise ValueError('Unknown original training graph')
        current[n]['expression']=complete[n]['expression']
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve previous complete-cache experiment')
    binding=regression.checked(source)
    baseline=json.loads((source/'baseline.json').read_text())
    candidate=patch(json.loads((source/'candidate.json').read_text()),baseline)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(candidate,ensure_ascii=False))
    for name in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    for path in (Path(__file__),Path(bulk_fit.__file__),Path(bulk_fit.bulk_exact.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'cache-complete-grouped-fallback',
        'CompanyDeployment':False,'OriginalFallbackSemantics':'Complete grouped rewrite; broad regression remains required.'},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(cacheprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
