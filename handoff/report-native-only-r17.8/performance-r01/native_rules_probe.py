"""Static Share value fields with native rules sourced from the existing pct.

The numerical model stays R03. No colour DAX is requested: native matrix rules
can use its already projected percentage value, including for absolute columns.
Query equivalence is checked here; actual Desktop rules remain a separate gate.
"""
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import probe
import regression
import share_display
import staticprobe
import static_values


def patch(database):
    fixed=static_values.patch(database)
    measures=prepared.adapter.planning.measures(fixed)
    for kind,w in [('plan',0),*[(k,w) for w in (6,12,24) for k in ('abs','pct')]]:
        m=measures[static_values.name(kind,w)]
        m.pop('formatStringDefinition')
        m['formatString']=share_display.FORMAT
        m['expression']="IF(SELECTEDVALUE('fm_native_metric'[RowID])=\"share\",("+m['expression']+'))'
    return fixed


def query(original):
    changed=static_values.query(original.replace('\r\n','\n'))
    for kind in ('plan','abs','pct'):
        name=static_values.name(kind,12)
        old="IGNORE('fm_native_measures'[_"+name+' FormatString])'
        if changed.count(old)!=1:raise ValueError('Unknown fixed format projection')
        changed=changed.replace(old,'IGNORE("'+share_display.FORMAT+'")')
    old="IGNORE('fm_native_measures'["+static_values.name('color',12)+'])'
    if changed.count(old)!=1:raise ValueError('Unknown colour projection')
    return changed.replace(old,"IGNORE('fm_native_measures'["+static_values.name('pct',12)+'])')


def build(destination,source,runner):
    if destination.exists():raise ValueError('Preserve native rules experiment')
    binding=regression.checked(source);regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text())
    original=next(q['query'] for q in json.loads((source/'queries.json').read_text()) if q['name']=='share-expanded/full-core/candidate')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(db),ensure_ascii=False))
    rules=query(original)
    mapped=rules.replace("\"Color\",IGNORE('fm_native_measures'["+static_values.name('pct',12)+'])',
        "\"Color\",IGNORE('fm_native_measures'["+static_values.name('color',12)+'])')
    mapped='DEFINE\nMEASURE \'fm_native_measures\'['+static_values.name('color',12)+']=VAR _value=['+static_values.name('pct',12)+'] RETURN '+static_values.PALETTE+'\n'+mapped[6:]
    (destination/'queries.json').write_text(json.dumps([{'name':label,'model':'candidate','query':q} for label,q in [('original',original),('native-rules',rules),('mapped-rules',mapped)]]))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/name,destination/name)
    for path in (Path(__file__),Path(static_values.__file__),Path(share_display.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'native-share-rules',
        'ExpectedPopulation':binding['ExpectedPopulation'],'DesktopRulesVerified':False,
        'FieldParameterUIBuilt':False,'CompanyAcceptance':False},indent=2))
    return {'Directory':str(destination),'Queries':3}


def verify(directory):
    binding=regression.checked(directory)
    rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(rows)!=3 or any('error' in r for r in rows):raise AssertionError('Incomplete/failed native rules test')
    old=rows[0]
    expected=probe.full_core_sets(old['resultSets'])
    for new in rows[1:]:
        fixed=json.loads(json.dumps(new['resultSets']))
        if new['name']=='native-rules':
            for r in fixed[0]['rows']:
                pct=r['[Color]']
                r['[Color]']=None if pct is None else '#E5F2E6' if abs(pct)<=.05 else '#FFF3CD' if abs(pct)<=.10 else '#F9E1E3'
        actual=probe.full_core_sets(staticprobe.flatten(fixed,old['resultSets']))
        if len(old['rows'])!=1560 or not probe.equal(expected,actual):
            raise AssertionError('Changed values/formats/native-rule input/identities')
    return {'Stage':'LOCAL_NATIVE_RULE_INPUTS_VERIFIED','Queries':3,'Mismatches':0,'Cells':1560,
        'Timings':[{'Query':r['name'],'ElapsedMs':r['elapsedMs']} for r in rows],
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'DesktopRulesVerified':False,'FieldParameterUIBuilt':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
