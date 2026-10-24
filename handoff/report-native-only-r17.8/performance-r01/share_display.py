"""Test static Share formatting and same-cell colour reuse, preserving numbers.

This adds a Share-only alias for a later native field-parameter experiment. It
does not change the generic numeric model or select a different UI yet. Static
percentage formatting avoids a separate per-cell dynamic-format evaluation.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import probe
import regression

NAME='P Share Summary'
FORMAT='0.0%;−0.0%;0.0%'


def patch(database):
    fixed=deepcopy(database)
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    if any(m['name']==NAME for m in target):raise ValueError('Share display already installed')
    target.append({'name':NAME,'isHidden':True,'expression':
        "IF(SELECTEDVALUE('fm_native_metric'[RowID])=\"share\",[N Summary Cell])",'formatString':FORMAT})
    return fixed


def query(original,reuse):
    old="\"N_Summary_Cell\", 'fm_native_measures'[N Summary Cell]"
    if original.count(old)!=1:raise ValueError('Unknown native value binding')
    changed=original.replace(old,"\"N_Summary_Cell\", 'fm_native_measures'["+NAME+']')
    old="IGNORE('fm_native_measures'[_N Summary Cell FormatString])"
    if changed.count(old)!=1:raise ValueError('Unknown format projection')
    changed=changed.replace(old,'IGNORE("'+FORMAT+'")')
    if reuse:
        old="VAR _value=CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),\n TREATAS({_window},'fm_native_trend'[Window]))"
        if changed.count(old)!=1:raise ValueError('Unknown original colour expression')
        changed=changed.replace(old,"VAR _value=IF(RIGHT(_key,3)=\"pct\",["+NAME+"],CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),\n TREATAS({_window},'fm_native_trend'[Window])))")
    return changed


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve previous Share display experiment')
    binding=regression.checked(source);regression.checked(runner)
    baseline=json.loads((source/'candidate.json').read_text())
    captured=json.loads((source/'queries.json').read_text())
    original=next(q['query'] for q in captured if q['name']=='share-expanded/full-core/candidate')
    queries=[{'name':label,'model':'candidate','query':q} for label,q in [
        ('original',original),('static-format',query(original,False)),('static-format-reuse',query(original,True))]]
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(baseline),ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/name,destination/name)
    if "foreach($kind in @('candidate'))" not in (destination/'run_profile.ps1').read_text():
        raise ValueError('One-model runner required')
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'static-share-display',
        'ExpectedPopulation':binding['ExpectedPopulation'],'UIFieldParameterBuilt':False,'CompanyAcceptance':False},indent=2))
    return {'Directory':str(destination),'Queries':3}


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(results)!=3 or any('error' in r for r in results):raise AssertionError('Incomplete/failed Share display test')
    original=probe.full_core_sets(results[0]['resultSets'])
    for r in results:
        if len(r['rows'])!=1560 or not probe.equal(original,probe.full_core_sets(r['resultSets'])):
            raise AssertionError('Changed Share cells/formats/colours/identities')
    return {'Stage':'LOCAL_STATIC_SHARE_DISPLAY_PROBE','Queries':3,'Mismatches':0,
        'Pairs':[{'Query':r['name'],'ElapsedMs':r['elapsedMs']} for r in results],
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'UIFieldParameterBuilt':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
