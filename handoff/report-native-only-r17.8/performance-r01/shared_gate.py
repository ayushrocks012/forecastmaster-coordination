"""Share exact prepared-cell eligibility across value, format and colour.

No guard is removed. The full current gate becomes one named measure; leaf
values/formats/colours reuse it and unsupported contexts retain exact fallback.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression

GATE='P Executive Prepared Eligible'


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if GATE in m:raise ValueError('Guard already shared')
    prefix=cell_fact.prefix()
    for name in (cell_fact.VALUE,cell_fact.COLOR):
        if not m[name]['expression'].startswith(prefix):raise ValueError('Unknown exact eligible-cell expression')
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    target.append({'name':GATE,'expression':prefix+'RETURN INT(_use)','isHidden':True})
    small='''VAR _display=[N Display]
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _use=['''+GATE+''']=1
'''
    for name in (cell_fact.VALUE,cell_fact.COLOR):
        m[name]['expression']=m[name]['expression'].replace(prefix,small,1)
    fmt=m[cell_fact.VALUE]['formatStringDefinition']
    if not fmt['expression'].startswith(prefix):raise ValueError('Unknown exact eligible-cell format')
    fmt['expression']=fmt['expression'].replace(prefix,small,1)
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve shared-gate run')
    b=regression.checked(source)
    if b.get('Prototype')!='prepared-executive-cells':raise ValueError('Unknown prepared-cell source')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**b,'Files':files,
        'Prototype':'shared-prepared-cell-guard','ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),
        'GuardExpressionsUnchanged':True,'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(cell_fact.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
