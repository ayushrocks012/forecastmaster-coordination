"""One sector dimension for matrix rows and narrow serving facts.

Use a unique dimension rather than grouping prepared amounts through a repeated
source-sector table. Existing slicers continue through the scope bridge; raw
facts and complete fallbacks remain. No sector limit is introduced.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import probe
import regression

DIM='fm_sector_dimension'


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if any(t['name']==DIM for t in fixed['model']['tables']):raise ValueError('Sector dimension already installed')
    dimension='''DISTINCT(SELECTCOLUMNS('fm_native_scope',"GrowthDriver",'fm_native_scope'[GrowthDriver],
 "Sector",'fm_native_scope'[Sector],"SectorLabel",'fm_native_scope'[SectorLabel]))'''
    fixed['model']['tables'].append({'name':DIM,'isHidden':True,
        'columns':[{'name':n,'dataType':'string','type':'calculatedTableColumn','sourceColumn':'['+n+']','summarizeBy':'none'} for n in ('GrowthDriver','Sector','SectorLabel')],
        'partitions':[{'name':DIM,'mode':'import','source':{'type':'calculated','expression':dimension}}]})
    # Avoid a LOOKUPVALUE dependency back through the newly related dimension.
    wide=next(t for t in fixed['model']['tables'] if t['name']=='fm_leaf_kpi')
    label=next(c for c in wide['columns'] if c['name']=='SectorLabel')
    label['expression']='''VAR _id=LOOKUPVALUE('fm_leaf_series'[SourceID],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])
VAR _sector=LOOKUPVALUE('fm_leaf_series'[Sector],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])
VAR _driver=LOOKUPVALUE('fm_native_files'[GrowthDriver],'fm_native_files'[SourceRevisionID],_id)
RETURN IF(LEN(_sector)=0,"No forecast tier",_sector)&" – "&_driver'''
    changed=0
    for r in fixed['model']['relationships']:
        if r['toTable']=='fm_native_scope' and r['toColumn']=='SectorLabel':
            r['toTable']=DIM;r['toCardinality']='one';changed+=1
    if changed!=3:raise ValueError('Require narrow related source with three scope facts')
    fixed['model']['relationships'].append({'name':'SectorDimension-NativeScope','fromTable':'fm_native_scope',
        'fromColumn':'SectorLabel','fromCardinality':'many','toTable':DIM,'toColumn':'SectorLabel',
        'toCardinality':'one','crossFilteringBehavior':'bothDirections'})
    for name in ('N Plan','N Benchmark'):
        marker="ISINSCOPE('fm_native_scope'[SectorLabel])"
        if m[name]['expression'].count(marker)!=1:raise ValueError('Unknown prepared row domain')
        m[name]['expression']=m[name]['expression'].replace(marker,"ISINSCOPE('"+DIM+"'[SectorLabel])")
    return fixed


def query(original):
    return original.replace("'fm_native_scope'[GrowthDriver]","'"+DIM+"'[GrowthDriver]").replace(
        "'fm_native_scope'[SectorLabel]","'"+DIM+"'[SectorLabel]")


def build(destination,source):
    if destination.exists():raise ValueError('Preserve star dimension probe')
    binding=regression.checked(source)
    if binding.get('Prototype')!='narrow-prepared-leaf':raise ValueError('Require narrow facts')
    queries=json.loads((source/'queries.json').read_text())
    for q in queries:
        if q['model']=='candidate' and '-expanded/' in q['name']:q['query']=query(q['query'])
    queries.append({'name':'sector-dimension-population','model':'candidate','query':
        "EVALUATE ROW(\"Rows\",COUNTROWS('"+DIM+"'),\"Labels\",COUNTROWS(VALUES('"+DIM+"'[SectorLabel])))"})
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    (destination/'queries.json').write_text(json.dumps(queries))
    for n in ('baseline.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'sector-star-serving',
        'RowDimension':'One row per driver/sector label; uniqueness required and checked by relationship processing.',
        'RLSAndFabric':'Unqualified local snapshot only.'},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


def canonical(sets):
    replace={DIM+'[GrowthDriver]':'fm_native_scope[GrowthDriver]',DIM+'[SectorLabel]':'fm_native_scope[SectorLabel]'}
    return [{'columns':[replace.get(c,c) for c in s['columns']],
        'rows':[{replace.get(k,k):v for k,v in r.items()} for r in s['rows']]} for s in sets]


def verify(directory):
    binding=regression.checked(directory)
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    requested=json.loads((directory/'queries.json').read_text())
    if len(results)!=len(requested) or any('error' in r for r in results):raise AssertionError('Incomplete/failed sector star probe')
    by={r['name']:r for r in results};pairs=[]
    for name,old in by.items():
        if not name.endswith('/baseline'):continue
        new=by[name[:-8]+'candidate'];a=old['resultSets'];b=canonical(new['resultSets'])
        if '/full-core/' in name:a,b=probe.full_core_sets(a),probe.full_core_sets(b)
        if not probe.equal(a,b):raise AssertionError('Changed complete cell/format/colour/population: '+name)
        pairs.append({'Query':name[:-9],'R03Ms':old['elapsedMs'],'CandidateMs':new['elapsedMs']})
    if by['sector-dimension-population']['rows']!=[{'[Rows]':150,'[Labels]':150}]:raise AssertionError('Changed/duplicate sector dimension')
    if by['narrow-population']['rows']!=[binding['ExpectedNarrowPopulation']]:raise AssertionError('Changed serving population')
    return {'Stage':'LOCAL_SECTOR_STAR_SERVING_PROBE','Queries':len(results),'Pairs':pairs,'Mismatches':0,
        'SourceHashes':binding['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'CompanyOrDesktopQualified':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
