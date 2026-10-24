"""Diagnostic only: isolate raw parent/totals work after snapshot admission.

All leaf values/formats/colours must remain identical. Diagnostic parent values
are deliberately zero and are never deployable. Both measure variants use the
same one frozen model and exact input-bit verification.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression
import sector_dim
import snapshot_cells

VALUE='P Diagnostic Zero Parents'
COLOR='P Diagnostic Zero Parent Color'


def build(destination,source):
    if destination.exists():raise ValueError('Preserve snapshot parent diagnostic')
    bound=regression.checked(source)
    if bound.get('Prototype')!='native-bitwise-snapshot':raise ValueError('Require validated native snapshot')
    db=json.loads((source/'candidate.json').read_text());m=prepared.adapter.planning.measures(db)
    value=deepcopy(m[cell_fact.VALUE]);value['name']=VALUE
    marker='['+snapshot_cells.FULL+']'
    if value['expression'].count(marker)!=2:raise ValueError('Unknown exact raw fallback paths')
    value['expression']=value['expression'].replace(marker,'0')
    value['formatStringDefinition']['expression']=value['formatStringDefinition']['expression'].replace('['+cell_fact.VALUE+']','['+VALUE+']')
    colour=deepcopy(m[cell_fact.COLOR]);colour['name']=COLOR;colour['expression']=colour['expression'].replace('['+cell_fact.VALUE+']','['+VALUE+']')
    next(t for t in db['model']['tables'] if t['name']=='fm_native_measures')['measures'].extend([value,colour])
    old=json.loads((source/'queries.json').read_text());queries=[]
    for metric in ('market','share'):
        q=next(x['query'] for x in old if x['name']==metric+'-expanded/full-core/candidate')
        queries.append({'name':metric+'/normal','model':'candidate','query':q})
        changed=q.replace("'fm_native_measures'["+cell_fact.VALUE+']',"'fm_native_measures'["+VALUE+']').replace(
            "'fm_native_measures'[_"+cell_fact.VALUE+' FormatString]',"'fm_native_measures'[_"+VALUE+' FormatString]').replace(
            '['+cell_fact.COLOR+']','['+COLOR+']')
        queries.append({'name':metric+'/zero-parents','model':'candidate','query':changed})
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('bitwise-query.dax','verified-control.dax','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    script=(source/'run_profile.ps1').read_text().replace("foreach($kind in @('baseline','candidate'))","foreach($kind in @('candidate'))")
    (destination/'run_profile.ps1').write_text(script)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Prototype':'snapshot-parent-diagnostic',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'Deployable':False,'CompanyAction':False},indent=2))
    return {'Directory':str(destination),'Queries':4}


def verify(directory):
    bound=regression.checked(directory);rs=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    if len(rs)!=4 or any('error' in r for r in rs):raise AssertionError('Incomplete/failed parent diagnostic')
    by={r['name']:r for r in rs}
    def leaves(r):
        s=sector_dim.canonical(r['resultSets'])[0]
        rows=[r for r in s['rows'] if r.get('fm_native_scope[SectorLabel]') is not None]
        if len(rows)!=1500:raise AssertionError('Incomplete leaf set')
        return probe.full_core_sets([{**s,'rows':rows}])
    for metric in ('market','share'):
        if not probe.equal(leaves(by[metric+'/normal']),leaves(by[metric+'/zero-parents'])):raise AssertionError('Known leaf changed')
    return {'Stage':'LOCAL_SNAPSHOT_PARENT_DIAGNOSTIC','LeafMismatches':0,
        'Timings':[{'Query':r['name'],'Ms':r['elapsedMs']} for r in rs],'Deployable':False,
        'SourceHashes':bound['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),'TaskOwnedEngineClosed':True}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
