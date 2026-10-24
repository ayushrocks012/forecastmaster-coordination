"""Freeze the exact prepared-sector prototype on the complete R03 workload."""
import hashlib
import json
from pathlib import Path
import shutil
import time

import bulk_fit
import bulkprobe
import leaf_model
import leaf_prepare
import regression


def build(destination,source,export,runner):
    if destination.exists():raise ValueError('Preserve prior leaf preparation attempt')
    binding=regression.checked(source);regression.checked(runner)
    baseline=json.loads((source/'candidate.json').read_text())
    start=time.monotonic();data=leaf_prepare.prepare(export);candidate=leaf_model.patch(baseline,data)
    data['receipt']['PreparationAndEncodingMs']=round((time.monotonic()-start)*1000)
    queries=json.loads((source/'queries.json').read_text())
    queries.append({'name':'leaf-population','model':'candidate','query':
        "EVALUATE ROW(\"Series\",COUNTROWS('fm_leaf_series'),\"KPIRows\",COUNTROWS('fm_leaf_kpi'))"})
    destination.mkdir(parents=True)
    for name,value in [('baseline',baseline),('candidate',candidate),('queries',queries),('preparation',data['receipt'])]:
        (destination/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    for name in ('expected.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(runner/'run_profile.ps1',destination/'run_profile.ps1')
    for path in (Path(__file__),Path(leaf_model.__file__),Path(leaf_prepare.__file__),Path(bulk_fit.__file__),Path(bulk_fit.bulk_exact.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'prepared-leaf-kpis',
        'ExpectedPopulation':binding['ExpectedPopulation'],'ExpectedLeafPopulation':{'[Series]':len(data['dimension']),'[KPIRows]':len(data['rows'])},
        'Baseline':'qualified R03','Freshness':'Immutable calculated SAMPLE export; no company integration.',
        'FullFormatsAndColoursRetained':True,'CompanyDeployment':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries),'Preparation':data['receipt']}


def verify(directory):
    binding=regression.checked(directory);receipt=bulkprobe.verify(directory)
    rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if next(r for r in rows if r['name']=='leaf-population')['rows']!=[binding['ExpectedLeafPopulation']]:
        raise AssertionError('Changed prepared leaf population')
    receipt.update(Stage='LOCAL_PREPARED_LEAF_KPI_PROBE',LeafPopulation=binding['ExpectedLeafPopulation'],
        Preparation=json.loads((directory/'preparation.json').read_text()),CompanyDeployment=False,
        Freshness=binding['Freshness'])
    return receipt


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:6])),indent=2))
