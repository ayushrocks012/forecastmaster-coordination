"""Freeze a narrow whole-result R03/bulk-kernel comparison before broader runs."""
import hashlib
import json
from pathlib import Path
import shutil

import bulkcells
import probe
import regression

HERE=Path(__file__).resolve().parent


def build(destination, source, runner):
    if destination.exists():
        raise ValueError('Preserve prior bulk probe')
    binding=regression.checked(source)
    regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text())
    candidate=bulkcells.patch(db)
    if any(p['source']['type']!='calculated' for t in candidate['model']['tables'] for p in t.get('partitions',[])):
        raise ValueError('Calculated sample only')
    queries=json.loads((source/'queries.json').read_text())
    if len(queries)!=21:
        raise ValueError('Unexpected probe population')
    destination.mkdir(parents=True)
    for name,value in [('baseline',db),('candidate',candidate),('queries',queries)]:
        (destination/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    shutil.copy2(source/'expected.json',destination/'expected.json')
    shutil.copy2(source/'launch_synthetic_engine.ps1',destination/'launch_synthetic_engine.ps1')
    # Reuse the established two-model runner, with QueryEnd tracing only.
    script=(runner/'run_profile.ps1').read_text()
    if "foreach($kind in @('baseline','candidate'))" not in script:
        raise ValueError('Require the established paired-model runner')
    (destination/'run_profile.ps1').write_text(script)
    for path in (HERE/'bulkprobe.py',HERE/'bulkcells.py'):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,
        'Prototype':'bulk-month-kernels','Baseline':'qualified R03 strict shared cells',
        'SourceProbeSHA256':probe.digest(source/'FROZEN-INPUTS.json'),
        'NativeQuerySourceSHA256':binding['NativeQuerySourceSHA256'],
        'ExpectedPopulation':binding['ExpectedPopulation'],'NewTables':False},indent=2))
    return {'Queries':len(queries),'Directory':str(destination)}


def verify(directory):
    # Probe validator's non-serving population contract is the same as strictcells.
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    requested=json.loads((directory/'queries.json').read_text())
    by={r['name']:r for r in results}
    if len(by)!=len(results) or set(by)!={r['name'] for r in requested} or any('error' in r for r in results):
        raise AssertionError({'IncompleteOrFailed':[r.get('name') for r in results if 'error' in r]})
    expected=json.loads((directory/'expected.json').read_text())
    pairs=[]
    for name,left in by.items():
        if not name.endswith('/baseline'):
            continue
        right=by[name[:-8]+'candidate']
        a,b=left['resultSets'],right['resultSets']
        if '/full-core/' in name:
            a,b=probe.full_core_sets(a),probe.full_core_sets(b)
        if not all(s['rows'] for s in a) or not probe.equal(a,b):
            raise AssertionError('Value/format/colour/population mismatch: '+name)
        key=name[:-9]
        if key in expected and (len(left['rows'])!=1 or not probe.equal(expected[key],left['rows'][0])):
            raise AssertionError('Independent scalar oracle: '+key)
        if '/full-core/' in name:
            sectors={r.get('fm_native_scope[SectorLabel]') for r in left['rows'] if r.get('fm_native_scope[SectorLabel]') is not None}
            if len(sectors)!=150:
                raise AssertionError('Not all sectors')
        pairs.append({'Query':key,'R03Ms':left['elapsedMs'],'BulkMs':right['elapsedMs']})
    if by['prepared-population']['rows']!=[{'[Facts]':504000,'[Files]':20,'[Scope]':600,'[Sectors]':150}]:
        raise AssertionError('Changed population')
    return {'Stage':'LOCAL_BULK_KERNEL_PROBE','Queries':len(results),'Pairs':pairs,'Mismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
