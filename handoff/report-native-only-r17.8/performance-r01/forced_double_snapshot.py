"""Normalize both exact-comparison operands to the declared DOUBLE type."""
import json
from pathlib import Path
import re
import shutil

import probe
import regression
import snapshot_cells


def build(destination,source):
    if destination.exists():raise ValueError('Preserve explicit type comparison attempt')
    bound=regression.checked(source)
    if bound.get('Prototype')!='stored-double-snapshot':raise ValueError('Require stored monthly reference')
    db=json.loads((source/'candidate.json').read_text())
    health=next(t for t in db['model']['tables'] if t['name']==snapshot_cells.HEALTH)['partitions'][0]['source']
    text=health['expression'];actual='"A",\'fm_current_monthly\'[Amount]'
    if text.count(actual)!=1:raise ValueError('Unknown stored native amount')
    text=text.replace(actual,'"A",CONVERT(\'fm_current_monthly\'[Amount],DOUBLE)')
    text,n=re.subn(r'"A",(\'fm_cache_monthly\'\[[a-z_]+\])',r'"A",CONVERT(\1,DOUBLE)',text)
    if n!=10:raise ValueError('Unknown prepared amount operands')
    health['expression']=text
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','native-preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'explicit-double-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,
        'Change':'CONVERT both numeric comparison operands to their declared DOUBLE; exact EXCEPT remains.'},indent=2))
    return {'Directory':str(destination),'Queries':26}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:3])),indent=2))
