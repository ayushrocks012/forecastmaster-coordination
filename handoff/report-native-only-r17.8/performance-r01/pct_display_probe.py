"""Share static format and percent-only alerts, sourced from the current cell.

Amounts are intentionally neutral; percentage variance retains the same exact
absolute 5/10 percent thresholds. Numeric values and readable formats stay
unchanged. This is a UI experiment, not a business-formula change.
"""
import hashlib
import json
from pathlib import Path
import shutil

import probe
import regression
import share_display

COLOR='''VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
RETURN IF(HASONEVALUE('fm_native_columns'[ColumnKey])&&RIGHT(_key,3)="pct",
 VAR _value=[P Share Summary]
 RETURN IF(NOT ISBLANK(_value),VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3")))'''


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve percent-alert display attempt')
    binding=regression.checked(source);regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text())
    original=next(q['query'] for q in json.loads((source/'queries.json').read_text()) if q['name']=='share-expanded/full-core/candidate')
    changed=share_display.query(original,False)
    begin=changed.index('/* USER DAX BEGIN */')+len('/* USER DAX BEGIN */');end=changed.index('/* USER DAX END */')
    changed=changed[:begin]+'\n'+COLOR+'\n'+changed[end:]
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(share_display.patch(db),ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps([{'name':label,'model':'candidate','query':q} for label,q in [('original',original),('percent-alerts',changed)]]))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/name,destination/name)
    for path in (Path(__file__),Path(share_display.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'share-percent-alerts',
        'ExpectedPopulation':binding['ExpectedPopulation'],'PresentationChange':'Amounts neutral; same relative variance colours on pct cells only.',
        'FieldParameterUIBuilt':False,'DesktopVerified':False,'CompanyAcceptance':False},indent=2))
    return {'Directory':str(destination),'Queries':2}


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(results)!=2 or any('error' in r for r in results):raise AssertionError('Incomplete/failed percent display test')
    original=json.loads(json.dumps(results[0]['resultSets']))
    for r in original[0]['rows']:
        if not str(r['fm_native_columns[ColumnLabel]']).endswith('%'):
            r['[N GM Summary Color]']=None
    if len(original[0]['rows'])!=1560 or not probe.equal(probe.full_core_sets(original),probe.full_core_sets(results[1]['resultSets'])):
        raise AssertionError('Changed numeric/format/percent-alert/identity contract')
    return {'Stage':'LOCAL_PERCENT_ALERT_DISPLAY_PROBE','Queries':2,'MismatchesAgainstDeclaredPresentation':0,
        'Cells':1560,'Timings':[{'Query':r['name'],'ElapsedMs':r['elapsedMs']} for r in results],
        'PresentationChange':binding['PresentationChange'],'SourceHashes':binding['Files'],
        'ResultsSHA256':probe.digest(directory/'results.json'),'TaskOwnedEngineClosed':True,
        'FieldParameterUIBuilt':False,'DesktopVerified':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
