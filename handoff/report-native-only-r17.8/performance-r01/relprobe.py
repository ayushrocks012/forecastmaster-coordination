"""Freeze a relational index prototype against the complete large R03 sample."""
import hashlib
import json
from pathlib import Path
import shutil

import bulk_exact
import bulkprobe
import relational
import regression


def build(destination,source,runner):
    if destination.exists():
        raise ValueError('Preserve previous relational attempt')
    binding=regression.checked(source);regression.checked(runner)
    baseline=json.loads((source/'candidate.json').read_text());candidate=relational.patch(baseline)
    destination.mkdir(parents=True)
    for name,data in [('baseline',baseline),('candidate',candidate)]:
        (destination/(name+'.json')).write_text(json.dumps(data,ensure_ascii=False))
    for name in ('queries.json','expected.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(runner/'run_profile.ps1',destination/'run_profile.ps1')
    for p in (Path(__file__),Path(relational.__file__),Path(bulk_exact.__file__)):
        shutil.copy2(p,destination/p.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'relational-monthly',
        'ExpectedPopulation':binding['ExpectedPopulation'],'Baseline':'qualified R03',
        'OriginalTablesRelationshipsFormatsPreserved':True,'CompanyDeployment':False,
        'CompanyMigrationAndRLS':'Unqualified; calculated local copies only.'},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(bulkprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
