"""Diagnostic only: direct prepared-cell reads in the fixed healthy SAMPLE.

Removes admission and aggregate semantics intentionally. Never deploy this
model: SUM of sector Share is invalid. Verify every known leaf, not totals.
"""
import hashlib
import json
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression
import sector_dim


def build(destination, source):
    if destination.exists():raise ValueError('Preserve earlier diagnostic')
    bound=regression.checked(source)
    if bound.get('Prototype')!='prepared-executive-cells':raise ValueError('Require prepared-cell source')
    db=json.loads((source/'candidate.json').read_text());measures=prepared.adapter.planning.measures(db)
    for name,column,amount in [(cell_fact.VALUE,'Amount',True),(cell_fact.COLOR,'Color',False)]:
        measures[name]['expression']='VAR _display=[N Display]\nRETURN '+cell_fact.filtered(column,amount).replace(
            "FILTER(ALL('fm_executive_cells'[Scenario]),ISBLANK(_scenario)||'fm_executive_cells'[Scenario]=_scenario)",
            "KEEPFILTERS(VALUES('fm_executive_cells'[Scenario]))")
        measures[name]['expression']=measures[name]['expression'].replace('RETURN ',
            "RETURN IF(SELECTEDVALUE('fm_native_columns'[ColumnKey])=\"plan\"||SELECTEDVALUE('fm_native_columns'[Window]) IN VALUES('fm_native_trend'[Window]),",1)+')'
    measures[cell_fact.VALUE]['formatStringDefinition']['expression']='VAR _display=[N Display]\nRETURN '+cell_fact.filtered('FormatCode').replace(
        "FILTER(ALL('fm_executive_cells'[Scenario]),ISBLANK(_scenario)||'fm_executive_cells'[Scenario]=_scenario)",
        "KEEPFILTERS(VALUES('fm_executive_cells'[Scenario]))")
    queries=[];old=json.loads((source/'queries.json').read_text())
    for metric in ('market','share'):
        q=next(q['query'] for q in old if q['name']==metric+'-expanded/full-core/candidate')
        for name,model in [('normal','baseline'),('direct','candidate')]:
            queries.append({'name':metric+'/'+name,'model':model,'query':q})
    destination.mkdir(parents=True)
    shutil.copy2(source/'candidate.json',destination/'baseline.json')
    (destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('run_profile.ps1','launch_synthetic_engine.ps1'):shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'direct-prepared-cell-diagnostic',
        'SourceSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'Deployable':False,
        'Limit':'Fixed healthy leaf-only equivalence; invalid Share totals and missing admission.'},indent=2))
    return {'Directory':str(destination),'Queries':4}


def verify(directory):
    bound=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    queries=json.loads((directory/'queries.json').read_text());by={r['name']:r for r in results}
    if len(by)!=len(queries) or set(by)!={q['name'] for q in queries} or any('error' in r for r in results):
        raise AssertionError('Incomplete direct-cell diagnostic')
    def leaves(r):
        sets=sector_dim.canonical(r['resultSets'])
        rows=[r for r in sets[0]['rows'] if r.get('fm_native_scope[SectorLabel]') is not None]
        if len(rows)!=1500:raise AssertionError('Incomplete leaf population')
        return probe.full_core_sets([{**sets[0],'rows':rows}])
    pairs=[]
    for metric in ('market','share'):
        a,b=by[metric+'/normal'],by[metric+'/direct']
        if not probe.equal(leaves(a),leaves(b)):raise AssertionError('Changed known leaf outputs')
        pairs.append({'Metric':metric,'NormalMs':a['elapsedMs'],'DirectMs':b['elapsedMs']})
    return {'Stage':'LOCAL_DIRECT_PREPARED_CELL_DIAGNOSTIC','Pairs':pairs,'KnownLeafMismatches':0,
        'Files':bound['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'Deployable':False,'TaskOwnedEngineClosed':True,'CompanyOrDesktopAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
