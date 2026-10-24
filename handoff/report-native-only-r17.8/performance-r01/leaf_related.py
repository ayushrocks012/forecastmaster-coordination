"""Let storage group the prepared facts by the native row/period dimensions.

Only new serving columns/relationships are added; original relationships and
fact data stay intact. Source-scenario admission and source-specific sector
membership retain their guards. Missing prepared keys now use the complete
fallback, including newly imported files/sectors. RLS/Fabric remain unqualified.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import leafprobe
import prepared
import regression


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_leaf_kpi')
    if any(c['name']=='SourceID' for c in target['columns']):raise ValueError('Relationships already installed')
    expressions={
        'SourceID':"LOOKUPVALUE('fm_leaf_series'[SourceID],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])",
        'SectorLabel':'''VAR _id=LOOKUPVALUE('fm_leaf_series'[SourceID],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])
VAR _sector=LOOKUPVALUE('fm_leaf_series'[Sector],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])
RETURN LOOKUPVALUE('fm_native_scope'[SectorLabel],'fm_native_scope'[SourceRevisionID],_id,'fm_native_scope'[Sector],_sector)''',
        'PeriodKey':'''FORMAT('fm_leaf_kpi'[Year],"0")&":"&'fm_leaf_kpi'[Kind]''',
        'Scenario':"LOOKUPVALUE('fm_native_files'[Scenario],'fm_native_files'[SourceRevisionID],'fm_leaf_kpi'[SourceID])"}
    target['columns'].extend({'name':n,'dataType':'string','type':'calculated','expression':e,'summarizeBy':'none'} for n,e in expressions.items())
    for n,source,column,cardinality in [('Source','fm_native_files','SourceRevisionID','one'),
            ('Review','fm_review_files','SourceRevisionID','one'),('Scope','fm_native_scope','SectorLabel','many'),
            ('Period','fm_native_periods','PeriodKey','one')]:
        dest='SourceID' if n in ('Source','Review') else 'SectorLabel' if n=='Scope' else 'PeriodKey'
        fixed['model']['relationships'].append({'name':'Leaf-Serving-'+n,'fromTable':'fm_leaf_kpi','fromColumn':dest,
            'fromCardinality':'many','toTable':source,'toColumn':column,'toCardinality':cardinality,
            'crossFilteringBehavior':'oneDirection'})
    for n in ('N Plan','N Benchmark'):
        body=m[n]['expression']
        helper='P Leaf '+n[2:]
        marker="VAR _leaf=ISINSCOPE('fm_native_scope'[SectorLabel])"
        if body.count(marker)!=1:raise ValueError('Unknown thin domain')
        body=body.replace(marker,'''VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
'''+marker)
        old='''RETURN IF(NOT ISBLANK(_id)&&_currencyOK&&_validCut&&COUNTROWS(_keys)>0,
 IF(_sameCut,CALCULATE(['''+helper+'''],
 TREATAS(_keys,'fm_leaf_kpi'[Key]),TREATAS({_year},'fm_leaf_kpi'[Year]),
 TREATAS({_kind},'fm_leaf_kpi'[Kind]))'''
        new='''RETURN IF(NOT ISBLANK(_id)&&_currencyOK&&_validCut,
 IF(COUNTROWS(_keys)=1&&_sameCut,CALCULATE(['''+helper+'''],
 FILTER(ALL('fm_leaf_kpi'[Scenario]),ISBLANK(_scenario)||'fm_leaf_kpi'[Scenario]=_scenario))'''
        if body.count(old)!=1:raise ValueError('Unknown lookup/admission body')
        m[n]['expression']=body.replace(old,new)
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve relational leaf attempt')
    binding=regression.checked(source)
    if binding.get('Prototype')!='thin-prepared-leaf':raise ValueError('Require unchanged thin leaf model')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'related-prepared-leaf',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest(),
        'OriginalRelationshipsPreserved':True,'AddedServingRelationships':4,
        'NewFileOrSectorWithoutPreparedKey':'Complete grouped fallback; no blank-cache miss.',
        'FabricAndRLS':'Not qualified; local calculated SAMPLE only.'},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(leafprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
