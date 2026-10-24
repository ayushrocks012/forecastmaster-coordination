"""Diagnostic only: isolate guard costs over the same direct physical cells.

Never deploy: most queries intentionally omit required checks and aggregate
format/Share semantics. Only known healthy leaf outputs are compared.
"""
import json
from pathlib import Path

import cell_diagnostic
import cell_fact
import prepared
import probe
import regression
import sector_dim


def build(destination,source):
    cell_diagnostic.build(destination,source)
    db=json.loads((destination/'candidate.json').read_text());m=prepared.adapter.planning.measures(db)
    direct=m[cell_fact.VALUE]['expression']
    target=next(t for t in db['model']['tables'] if t['name']=='fm_native_measures')['measures']
    target.append({
        'name':'P Diagnostic Direct Cell','expression':direct,'isHidden':True})
    originals=json.loads((destination/'queries.json').read_text());queries=[]
    guards={'direct':'TRUE()','source':'[N Source OK]=1','period':'[N Period Available]=1',
        'prepared-cut':'NOT ISBLANK([P Executive Prepared Cut])',
        'cutoffs':'[N Cutoff]=[P Executive Prepared Cut]&&[N Fit Cutoff]=[P Executive Prepared Cut]',
        'count':"COUNTROWS('fm_executive_cells')=1"}
    formulas={label:'IF('+guard+',[P Diagnostic Direct Cell])' for label,guard in guards.items()}
    formulas.update({'aggregate-fallback':"IF(ISINSCOPE('"+sector_dim.DIM+"'[SectorLabel]),[P Diagnostic Direct Cell],[N Summary Cell])",
        'full-value-gate':cell_fact.prefix()+'RETURN IF(_use,[P Diagnostic Direct Cell],[N Summary Cell])'})
    for label,expr in formulas.items():
        target.append({'name':'P Diagnostic '+label,'expression':expr,
            'formatStringDefinition':dict(m[cell_fact.VALUE]['formatStringDefinition'])})
    for metric in ('market','share'):
        raw=next(q['query'] for q in originals if q['name']==metric+'/direct')
        for label in formulas:
            queries.append({'model':'candidate','name':metric+'/'+label,'query':
                raw.replace("'fm_native_measures'["+cell_fact.VALUE+']',"'fm_native_measures'[P Diagnostic "+label+']').replace(
                    "'fm_native_measures'[_"+cell_fact.VALUE+' FormatString]',"'fm_native_measures'[_P Diagnostic "+label+' FormatString]')})
    (destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    script=(destination/'run_profile.ps1').read_text()
    marker="foreach($kind in @('baseline','candidate'))"
    if script.count(marker)!=1:raise ValueError('Unknown native runner')
    (destination/'run_profile.ps1').write_text(script.replace(marker,"foreach($kind in @('candidate'))"))
    (destination/Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    binding=json.loads((destination/'FROZEN-INPUTS.json').read_text())
    binding['Files']={p.name:probe.digest(p) for p in destination.iterdir() if p.name!='FROZEN-INPUTS.json'}
    binding.update(Prototype='prepared-cell-guard-diagnostic',Deployable=False)
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps(binding,indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def verify(directory):
    bound=regression.checked(directory);rows=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    qs=json.loads((directory/'queries.json').read_text());by={r['name']:r for r in rows}
    if len(by)!=len(rows) or set(by)!={q['name'] for q in qs} or any('error' in r for r in rows):raise AssertionError('Incomplete/failed guard diagnostic')
    def leaves(r):
        s=sector_dim.canonical(r['resultSets'])[0]
        rs=[row for row in s['rows'] if row.get('fm_native_scope[SectorLabel]') is not None]
        if len(rs)!=1500:raise AssertionError('Guard lost healthy leaf cells')
        return probe.full_core_sets([{**s,'rows':rs}])
    for metric in ('market','share'):
        expected=leaves(by[metric+'/direct'])
        for name,r in by.items():
            if name.startswith(metric+'/') and not probe.equal(expected,leaves(r)):raise AssertionError('Guard changed known leaves')
    return {'Stage':'LOCAL_PREPARED_CELL_GUARD_DIAGNOSTIC','KnownLeafMismatches':0,
        'Timings':[{'Query':r['name'],'Ms':r['elapsedMs']} for r in rows],
        'SourceHashes':bound['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'Deployable':False,'TaskOwnedEngineClosed':True}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
