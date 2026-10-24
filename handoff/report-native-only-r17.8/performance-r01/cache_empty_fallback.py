"""Neutralize unused legacy input instead of trusting a conditional branch.

When cache admission succeeds, the R03 fallback sees an empty source-ID set
and returns blank through its own original guards. When admission fails, its
current source IDs are retained. Original fallback expressions are unmodified.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import regression


def patch(database):
    fixed=deepcopy(database);measures=prepared.adapter.planning.measures(fixed)
    marker="IF(SELECTEDVALUE('fm_cache_path'[Legacy],1)=1,\n"
    for name in ('N Plan','N Benchmark'):
        alias='P R03 '+name[2:]
        old=measures[alias]['expression']
        if not old.startswith(marker) or not old.endswith(')'):
            raise ValueError('Unknown gated legacy body')
        measures[alias]['expression']=old[len(marker):-1]
        expression=measures[name]['expression']
        return_marker='RETURN IF(_ready,'
        if expression.count(return_marker)!=1:
            raise ValueError('Unknown cache output shape')
        expression=expression.replace(return_marker,
            "VAR _legacyIDs=FILTER(VALUES('fm_native_files'[SourceRevisionID]),NOT _ready)\n"+return_marker)
        old_filter="TREATAS({INT(NOT _ready)},'fm_cache_path'[Legacy])"
        if expression.count(old_filter)!=1:
            raise ValueError('Unknown fallback gate')
        measures[name]['expression']=expression.replace(old_filter,
            "KEEPFILTERS(TREATAS(_legacyIDs,'fm_native_files'[SourceRevisionID]))")
    fixed['model']['tables']=[t for t in fixed['model']['tables'] if t['name']!='fm_cache_path']
    return fixed


def build(destination,source):
    if destination.exists():
        raise ValueError('Preserve previous empty-source experiment')
    binding=regression.checked(source)
    before=json.loads((source/'candidate.json').read_text());after=patch(before)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(after,ensure_ascii=False))
    for name in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'source-cache-lean-empty-fallback',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest(),
        'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
