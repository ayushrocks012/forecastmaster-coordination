"""Preserve exported IEEE double values throughout snapshot preparation.

Use a fresh private module instance; preserve all older experiment sources and
their bound data. Missing Amount stays NaN/BLANK; blank string metadata remains
blank string. Rebuild monthly data AND the dependent period KPIs together.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import time

import cache_prepare
import leaf_prepare
import prepared
import probe
import regression


def read_round_trip(path):
    import pandas as pd
    options={'keep_default_na':False,'float_precision':'round_trip'}
    if path.name=='facts.csv':options['na_values']={'[Amount]':['']}
    frame=pd.read_csv(path,**options)
    frame.columns=[c.removeprefix('[').removesuffix(']') for c in frame.columns]
    return frame


def prepare(export):
    start=time.monotonic()
    cache=prepared.load('precise_private_cache',Path(cache_prepare.__file__))
    cache.read=read_round_trip
    monthly=cache.prepare(export)
    def cached_prepare(path):
        if path.resolve()!=export.resolve():raise ValueError('Changed export during preparation')
        return monthly
    cache.prepare=cached_prepare
    leaf=prepared.load('precise_private_leaf',Path(leaf_prepare.__file__));leaf.cache_prepare=cache
    kpi=leaf.prepare(export)
    return cache.tables(monthly)[:2],leaf.tables(kpi),{'PreparationMs':round((time.monotonic()-start)*1000),
        'Leaf':kpi['receipt'],'SourceHashes':{n:probe.digest(export/(n+'.csv')) for n in ('facts','files','catalog')},
        'Precision':'Round-trip IEEE double CSV parsing; no tolerance relaxed.'}


def build(destination,source,export):
    if destination.exists():raise ValueError('Preserve precise snapshot attempt')
    bound=regression.checked(source);regression.checked(export)
    if bound.get('Prototype')!='refresh-validated-snapshot':raise ValueError('Require validated snapshot model')
    monthly,kpis,receipt=prepare(export)
    db=deepcopy(json.loads((source/'candidate.json').read_text()));tables={t['name']:t for t in db['model']['tables']}
    for new in monthly+kpis:
        current=tables[new['name']]
        actual={c['name']:c['dataType'] for c in current['columns'] if c['type']=='calculatedTableColumn'}
        expected={c['name']:c['dataType'] for c in new['columns']}
        if actual!=expected:raise ValueError('Changed prepared table fields: '+new['name'])
        current['partitions']=new['partitions']
    regression.checked(export)
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','expected.json','preparation.json','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    (destination/'precise-preparation.json').write_text(json.dumps(receipt,indent=2))
    queries=json.loads((source/'queries.json').read_text())
    queries.sort(key=lambda q:q['name']!='snapshot-health')
    if queries[0]['name']!='snapshot-health':raise ValueError('Missing readiness preflight')
    (destination/'queries.json').write_text(json.dumps(queries))
    runner=(source/'run_profile.ps1').read_text()
    marker='  Write-Output ("Completed synthetic query "+$ordinal)'
    if runner.count(marker)!=1:raise ValueError('Unknown bound native runner')
    stop='''
  if($case.name -eq 'snapshot-health' -and ($results[-1].ContainsKey('error') -or $results[-1].rows.Count -ne 1 -or $results[-1].rows[0]['fm_serving_health[Ready]'] -ne 1)) {
   Write-Output 'Snapshot preflight refused; no broad benchmark.'; break
  }'''
    (destination/'run_profile.ps1').write_text(runner.replace(marker,marker+stop))
    for path in (Path(__file__),Path(cache_prepare.__file__),Path(leaf_prepare.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'precise-validated-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,
        'PrecisionGate':'Exact raw/prepared input comparison unchanged; full preparation rebuilt from round-trip parsed source exports.',
        'StopBeforeBroadTimingUnlessReady':True},indent=2))
    return {'Directory':str(destination),'Queries':len(queries),'PreparationMs':receipt['PreparationMs']}


if __name__=='__main__':
    import sys
    print(json.dumps(build(*(Path(s) for s in sys.argv[1:4])),indent=2))
