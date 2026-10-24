"""Quantify per-row admission overhead after relational preparation.

Direct sums and fixed guards are diagnostic only: aggregate Share is knowingly
invalid. All 1,500 leaf cells, formats and colours must remain identical in the
pinned healthy Market/Share contexts; this cannot qualify another selection.
"""
import hashlib
import json
from pathlib import Path
import shutil

import probe
import regression


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve direct diagnostic')
    binding=regression.checked(source);regression.checked(runner)
    captured=json.loads((source/'queries.json').read_text());queries=[]
    direct="MEASURE 'fm_native_measures'[N Plan]=[P Leaf Plan]\nMEASURE 'fm_native_measures'[N Benchmark]=[P Leaf Benchmark]"
    fixed=direct+"\nMEASURE 'fm_native_measures'[N Source OK]=1\nMEASURE 'fm_native_measures'[N Cutoff]=DATE(2026,8,1)\nMEASURE 'fm_native_measures'[N Fit Cutoff]=DATE(2026,8,1)"
    for metric in ('market','share'):
        original=next(q['query'] for q in captured if q['name']==metric+'-expanded/full-core/candidate')
        for label,define in [('normal',''),('direct',direct),('direct-fixed-guards',fixed)]:
            q=original if not define else 'DEFINE\n'+define+'\n'+original[6:]
            queries.append({'name':metric+'/'+label,'model':'candidate','query':q})
    destination.mkdir(parents=True)
    shutil.copy2(source/'candidate.json',destination/'candidate.json')
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Kind':'DIAGNOSTIC_NOT_ACCEPTANCE',
        'ExpectedPopulation':binding['ExpectedPopulation'],'Limit':'Direct sums are invalid aggregate Share; constants valid only for the fixed healthy fake scope.'},indent=2))
    return {'Directory':str(destination),'Queries':6}


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(results)!=6 or any('error' in r for r in results):raise AssertionError('Incomplete/failed direct diagnostic')
    by={r['name']:r for r in results};timings=[]
    def leaves(r):
        sets=json.loads(json.dumps(r['resultSets']))
        sets[0]['rows']=[x for x in sets[0]['rows'] if x['fm_native_scope[SectorLabel]'] is not None]
        if len(sets[0]['rows'])!=1500:raise AssertionError('Changed leaf population')
        return probe.full_core_sets(sets)
    for metric in ('market','share'):
        old=leaves(by[metric+'/normal'])
        for label in ('normal','direct','direct-fixed-guards'):
            r=by[metric+'/'+label]
            if not probe.equal(old,leaves(r)):raise AssertionError('Changed known healthy leaf values/formats/colours')
            timings.append({'Query':r['name'],'ElapsedMs':r['elapsedMs'],'LeafCells':1500})
    return {'Stage':'LOCAL_DIRECT_LEAF_DIAGNOSTIC','Timings':timings,'LeafMismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'Deployable':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
