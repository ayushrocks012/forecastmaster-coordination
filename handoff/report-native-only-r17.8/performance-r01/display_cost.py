"""Measure display metadata overhead without selecting a stripped report.

The diagnostic constants are intentionally not a product candidate. All
numeric cells and dimension identities must match the unchanged native query.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

import probe
import regression


def build(destination,source,runner):
    if destination.exists():
        raise ValueError('Preserve prior display diagnostic')
    binding=regression.checked(source);regression.checked(runner)
    captured=json.loads((source/'queries.json').read_text());queries=[]
    for metric in ('market','share'):
        original=next(q['query'] for q in captured if q['name']==metric+'-expanded/full-core/candidate')
        for label,noformat,nocolor in [('original',False,False),('without-format',True,False),
                ('without-colour',False,True),('numeric-only',True,True)]:
            query=original
            if noformat:
                query,count=re.subn(r"IGNORE\('fm_native_measures'\[_N Summary Cell FormatString\]\)",'IGNORE("0.00")',query)
                if count!=1:raise ValueError('Unknown dynamic format query')
            if nocolor:
                query,count=re.subn(r"IGNORE\('fm_native_measures'\[N GM Summary Color\]\)",'IGNORE(BLANK())',query)
                if count!=1:raise ValueError('Unknown colour query')
            queries.append({'name':metric+'/'+label,'model':'candidate','query':query})
    destination.mkdir(parents=True)
    shutil.copy2(source/'candidate.json',destination/'candidate.json')
    (destination/'queries.json').write_text(json.dumps(queries))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/name,destination/name)
    if "foreach($kind in @('candidate'))" not in (destination/'run_profile.ps1').read_text():
        raise ValueError('One-model runner required')
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Kind':'DIAGNOSTIC_NOT_ACCEPTANCE',
        'ExpectedPopulation':binding['ExpectedPopulation'],'NumericModelChanged':False,
        'UIChangeQualified':False,'CompanyAcceptance':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(results)!=8 or any('error' in r for r in results):
        raise AssertionError('Incomplete/failed display diagnostic')
    by={r['name']:r for r in results}
    def project(row):
        return {k:v for k,v in row.items() if k not in {'[v_N_Summary_Cell_FormatString]','[N GM Summary Color]'}}
    timings=[]
    for metric in ('market','share'):
        original=by[metric+'/original']
        a=probe.full_core_sets([{**original['resultSets'][0],
            'rows':[project(r) for r in original['rows']]}])
        for label in ('original','without-format','without-colour','numeric-only'):
            current=by[metric+'/'+label]
            b=probe.full_core_sets([{**current['resultSets'][0],
                'rows':[project(r) for r in current['rows']]}])
            if len(current['rows'])!=1560 or not probe.equal(a,b):
                raise AssertionError('Changed numeric/dimension population')
            timings.append({'Query':current['name'],'ElapsedMs':current['elapsedMs'],'Cells':len(current['rows'])})
    return {'Stage':'LOCAL_DISPLAY_COST_DIAGNOSTIC','Timings':timings,'NumericMismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'UIChangeQualified':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
