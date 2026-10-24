"""Whole-cell comparison of native dynamic versus fixed-measure matrix queries."""
import hashlib
import json
from pathlib import Path
import shutil

import probe
import regression
import static_values


def build(destination,source,runner):
    if destination.exists():
        raise ValueError('Preserve previous matrix-shape test')
    regression.checked(source);regression.checked(runner)
    db=json.loads((source/'candidate.json').read_text());candidate=static_values.patch(db)
    captured=json.loads((source/'queries.json').read_text())
    queries=[]
    for metric in ('market','share'):
        original=next(q['query'] for q in captured if q['name']==metric+'-expanded/full-core/candidate').replace('\r\n','\n')
        for label,q in [('dynamic',original),('fixed',static_values.query(original))]:
            queries.append({'name':metric+'/'+label,'model':'candidate','query':q})
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(candidate,ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for name in ('run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(runner/name,destination/name)
    if "foreach($kind in @('candidate'))" not in (destination/'run_profile.ps1').read_text():
        raise ValueError('Require established one-model runner')
    for p in (Path(__file__),Path(static_values.__file__)):
        shutil.copy2(p,destination/p.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'native-fixed-measure-shape',
        'SameNumericModelAndData':True,'Population':'504000 facts / 20 files / 2 cycles / 5 drivers / 150 sectors',
        'NativeQuerySourceSHA256':hashlib.sha256((source/'queries.json').read_bytes()).hexdigest(),
        'CompanyAcceptance':False,'FieldParameterUIBuilt':False},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def flatten(fixed,original):
    if len(fixed)!=1 or len(original)!=1:
        raise AssertionError('Unexpected result-set shape')
    dims=['fm_native_scope[GrowthDriver]','fm_native_scope[SectorLabel]',
        'fm_native_periods[Label]','fm_native_periods[SortIndex]','[IsGrandTotalRowTotal]','[IsDM1Total]']
    expected=set(dims+['[V'+k+']' for k in ('plan','abs','pct')]+['[F'+k+']' for k in ('plan','abs','pct')]+['[Color]'])
    if set(fixed[0]['columns'])!=expected:
        raise AssertionError('Unexpected fixed fields')
    rows=[]
    for row in fixed[0]['rows']:
        for kind,label,sort in [('plan','Plan',0),('abs','12M variance',120),('pct','12M variance %',121)]:
            value=row['[V'+kind+']']
            if value is None:
                continue
            rows.append({**{d:row[d] for d in dims},'fm_native_columns[ColumnLabel]':label,
                'fm_native_columns[Sort]':sort,'[N_Summary_Cell]':value,
                '[v_N_Summary_Cell_FormatString]':row['[F'+kind+']'],
                '[N GM Summary Color]':None if kind=='plan' else row['[Color]']})
    return [dict(original[0],rows=rows)]


def verify(directory):
    bound=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(results)!=4 or any('error' in r for r in results):
        raise AssertionError('Incomplete/failed shape test')
    by={r['name']:r for r in results};pairs=[]
    for metric in ('market','share'):
        old,new=(by[metric+'/'+n] for n in ('dynamic','fixed'))
        a=probe.full_core_sets(old['resultSets']);b=probe.full_core_sets(flatten(new['resultSets'],old['resultSets']))
        if not probe.equal(a,b):
            raise AssertionError('Value/format/colour/row mismatch: '+metric)
        sectors={r.get('fm_native_scope[SectorLabel]') for r in old['rows'] if r.get('fm_native_scope[SectorLabel]') is not None}
        if len(sectors)!=150 or len(old['rows'])!=1560:
            raise AssertionError('Changed complete matrix population')
        pairs.append({'Metric':metric,'DynamicMs':old['elapsedMs'],'FixedMs':new['elapsedMs'],
            'FlattenedCells':len(old['rows']),'Sectors':len(sectors)})
    return {'Stage':'LOCAL_NATIVE_FIXED_MEASURE_SHAPE_PROBE','Pairs':pairs,'Mismatches':0,
        'SourceHashes':bound['Files'],'TaskOwnedEngineClosed':True,'FieldParameterUIBuilt':False,'CompanyAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
