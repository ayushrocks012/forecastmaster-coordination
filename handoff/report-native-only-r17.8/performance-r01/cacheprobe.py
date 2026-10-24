"""Freeze a generic source-prepared cache candidate against the full R03 sample."""
import hashlib
import json
from pathlib import Path
import shutil
import time

import bulkprobe
import cache_prepare
import cached_model
import probe
import regression

HERE=Path(__file__).resolve().parent


def build(destination,source,export,runner):
    if destination.exists():
        raise ValueError('Preserve previous cache probe')
    binding=regression.checked(source);regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text())
    if any(p['source']['type']!='calculated' for t in db['model']['tables'] for p in t.get('partitions',[])):
        raise ValueError('Calculated SAMPLE only')
    start=time.monotonic()
    data=cache_prepare.prepare(export)
    tables=cache_prepare.tables(data)
    data['receipt']['EncodeTablesAndPrepareTotalMs']=round((time.monotonic()-start)*1000)
    candidate=cached_model.patch(db,tables)
    queries=json.loads((source/'queries.json').read_text())
    if len(queries)!=21:
        raise ValueError('Unknown native source population')
    queries.append({'name':'cache-population','model':'candidate','query':'''EVALUATE ROW(
 "Series",COUNTROWS('fm_cache_series'),"Monthly",COUNTROWS('fm_cache_monthly'),"Statistics",COUNTROWS('fm_cache_statistics'))'''})
    destination.mkdir(parents=True)
    for name,value in [('baseline',db),('candidate',candidate),('queries',queries),('preparation',data['receipt'])]:
        (destination/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    for name in ('expected.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/name,destination/name)
    shutil.copy2(runner/'run_profile.ps1',destination/'run_profile.ps1')
    for name in ('cacheprobe.py','cache_prepare.py','cached_model.py'):
        shutil.copy2(HERE/name,destination/name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'source-prepared-cache',
        'Baseline':'qualified R03','SourceProbeSHA256':probe.digest(source/'FROZEN-INPUTS.json'),
        'ExpectedPopulation':binding['ExpectedPopulation'],'SourceExport':data['receipt']['SourceExportProof'],
        'ExpectedCachePopulation':{'[Series]':600,'[Monthly]':50400,'[Statistics]':21600},
        'CompanyDeployment':False,'CacheFreshness':'Immutable fabricated snapshot; no company auto-refresh integration is claimed.'},indent=2))
    return {'Directory':str(destination),'Queries':len(queries),'Preparation':data['receipt']}


def verify(directory):
    bound=regression.checked(directory)
    receipt=bulkprobe.verify(directory)
    rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    population=next(r for r in rows if r['name']=='cache-population')
    if population.get('rows')!=[bound['ExpectedCachePopulation']]:
        raise AssertionError('Wrong prepared population')
    receipt.update(Stage='LOCAL_SOURCE_PREPARED_CACHE_PROBE',CachePopulation=population['rows'],
        Preparation=json.loads((directory/'preparation.json').read_text()),CompanyDeployment=False,
        CacheFreshness=bound['CacheFreshness'])
    return receipt


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:6])),indent=2))
