"""Share a format-free numeric kernel between displayed values and formats.

Public names, numeric values, exact compact formats and colour rules remain.
Unlike direct self reference, both public expressions name the same ordinary
numeric helper, which has no dynamic-format property of its own.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import bulkprobe
import prepared
import regression
import strictcells


def patch(database):
    fixed=deepcopy(database)
    old=prepared.adapter.planning.measures(database);current=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    for name in ('N Summary Cell','N Headline Cell'):
        helper='P Numeric '+name[2:]
        if helper in old or old[name]!=expected[name]:
            raise ValueError('Unknown R03 cell definition')
        fmt=old[name]['formatStringDefinition']['expression']
        if fmt.count('SELECTEDMEASURE()')!=1:raise ValueError('Unknown dynamic format')
        target.append({'name':helper,'isHidden':True,'expression':text(old[name]['expression'])})
        current[name]['expression']='['+helper+']'
        current[name]['formatStringDefinition']['expression']=fmt.replace('SELECTEDMEASURE()','['+helper+']')
    return fixed


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve previous numeric display prototype')
    binding=regression.checked(source);regression.checked(runner)
    baseline=json.loads((source/'candidate.json').read_text());candidate=patch(baseline)
    destination.mkdir(parents=True)
    for name,data in [('baseline',baseline),('candidate',candidate)]:
        (destination/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False))
    for name in ('queries.json','expected.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(runner/'run_profile.ps1',destination/'run_profile.ps1')
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'numeric-display-alias',
        'ExpectedPopulation':binding['ExpectedPopulation'],'Baseline':'qualified R03',
        'NewTablesRelationshipsSources':False,'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(bulkprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
