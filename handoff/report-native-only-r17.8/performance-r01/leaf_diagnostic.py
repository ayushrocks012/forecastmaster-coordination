"""Isolate aggregate fallback cost; constants are diagnostic only, never release."""
import hashlib
import json
from pathlib import Path
import shutil

import probe
import regression


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve leaf diagnostic attempt')
    binding=regression.checked(source);regression.checked(runner)
    captured=json.loads((source/'queries.json').read_text());queries=[]
    for metric in ('market','share'):
        original=next(q['query'] for q in captured if q['name']==metric+'-expanded/full-core/candidate')
        changed='DEFINE\nMEASURE \'fm_native_measures\'[P Grouped Plan]=0\nMEASURE \'fm_native_measures\'[P Grouped Benchmark]=0\n'+original[6:]
        for label,query in [('normal',original),('zero-aggregate-diagnostic',changed)]:
            queries.append({'name':metric+'/'+label,'model':'candidate','query':query})
    destination.mkdir(parents=True)
    shutil.copy2(source/'candidate.json',destination/'candidate.json')
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Kind':'DIAGNOSTIC_NOT_ACCEPTANCE',
        'ExpectedPopulation':binding['ExpectedPopulation'],'Limit':'Aggregate zeros are intentionally invalid. Only leaf equality diagnoses branch use.'},indent=2))
    return {'Directory':str(destination),'Queries':4}


def verify(directory):
    binding=regression.checked(directory)
    rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(rows)!=4 or any('error' in r for r in rows):raise AssertionError('Incomplete/failed leaf diagnostic')
    by={r['name']:r for r in rows};timings=[]
    for metric in ('market','share'):
        old,new=[by[metric+'/'+v] for v in ('normal','zero-aggregate-diagnostic')]
        def leaves(r):
            sets=json.loads(json.dumps(r['resultSets']))
            sets[0]['rows']=[x for x in sets[0]['rows'] if x['fm_native_scope[SectorLabel]'] is not None]
            if len(sets[0]['rows'])!=1500:raise AssertionError('Changed leaf population')
            return probe.full_core_sets(sets)
        if not probe.equal(leaves(old),leaves(new)):raise AssertionError('Some leaf cells took the aggregate fallback')
        timings.append({'Metric':metric,'NormalMs':old['elapsedMs'],'ZeroAggregateMs':new['elapsedMs'],'UnchangedLeafCells':1500})
    return {'Stage':'LOCAL_LEAF_BRANCH_COST_DIAGNOSTIC','Timings':timings,'LeafMismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'Deployable':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
