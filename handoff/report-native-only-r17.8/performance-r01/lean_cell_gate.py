"""Equivalent admission specialized to one sector/country/cycle/driver.

In that domain a complete unique cohort is exactly one chosen source. Check
that source directly, source-specific scope membership, stored/current cutoffs,
axis, currency and cell coverage. Every unsupported/missing-cache case retains
the original fallback. This is local-only pending independent/edge acceptance.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression
import routed_cells
import sector_dim
import shared_gate


EXPRESSION='''VAR _leaf=ISINSCOPE('''+"'"+sector_dim.DIM+"'[SectorLabel])"+'''
VAR _country=SELECTEDVALUE('fm_review_files'[Country])
VAR _cycle=SELECTEDVALUE('fm_review_files'[DemandCycle])
VAR _driver=SELECTEDVALUE('fm_native_scope'[GrowthDriver])
VAR _row=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _window=SELECTEDVALUE('fm_native_columns'[Window])
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _chosen=INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))
VAR _ids=CALCULATETABLE(VALUES('fm_native_files'[SourceRevisionID]),
 REMOVEFILTERS('fm_native_files'),TREATAS(_chosen,'fm_native_files'[SourceRevisionID]),
 TREATAS({_country},'fm_native_files'[Country]),TREATAS({_cycle},'fm_native_files'[DemandCycle]),
 TREATAS({_driver},'fm_native_files'[GrowthDriver]),
 FILTER(ALL('fm_native_files'[Scenario]),ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario))
VAR _id=IF(COUNTROWS(_ids)=1,MAXX(_ids,'fm_native_files'[SourceRevisionID]))
VAR _cut=IF(_row="ef",LOOKUPVALUE('fm_native_files'[ExFactoryActualsThrough],'fm_native_files'[SourceRevisionID],_id),
 LOOKUPVALUE('fm_native_files'[IMSActualsThrough],'fm_native_files'[SourceRevisionID],_id))
VAR _stored=IF(_row="ef",CALCULATE(MAX('fm_leaf_series'[EF]),TREATAS({_id},'fm_leaf_series'[SourceID])),
 CALCULATE(MAX('fm_leaf_series'[IMS]),TREATAS({_id},'fm_leaf_series'[SourceID])))
VAR _validCut=NOT ISBLANK(_cut)&&_cut>=DATE(2000,1,1)&&_cut<DATE(2100,1,1)
 &&_cut=DATE(YEAR(_cut),MONTH(_cut),1)&&NOT ISBLANK(_stored)&&_cut=EDATE(DATE(2000,1,1),_stored)
VAR _currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_country)
VAR _member=CALCULATE(COUNTROWS('fm_native_scope'),KEEPFILTERS(TREATAS({_id},'fm_native_scope'[SourceRevisionID])))
VAR _count=CALCULATE(COUNTROWS('fm_executive_cells'),TREATAS({_display},'fm_executive_cells'[Display]),
 FILTER(ALL('fm_executive_cells'[Scenario]),ISBLANK(_scenario)||'fm_executive_cells'[Scenario]=_scenario))
VAR _domain=_leaf&&HASONEVALUE('fm_review_files'[Country])&&HASONEVALUE('fm_review_files'[DemandCycle])
 &&HASONEVALUE('fm_native_scope'[GrowthDriver])&&HASONEVALUE('fm_native_scope'[Sector])
 &&HASONEVALUE('fm_native_metric'[RowID])&&_row IN {"market","abbott","share","pi","net","ef"}
 &&(_display="Units"||(_display="Value"&&(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"||_row="share")))
 &&(_display<>"Value"||NOT ISBLANK(_currency))
 &&(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel]))
 &&(_key="plan"||_window IN VALUES('fm_native_trend'[Window]))
 &&NOT ISFILTERED('fm_review_facts')&&NOT ISFILTERED('fm_native_catalog')&&NOT ISFILTERED('fm_native_rows')
 &&NOT ISFILTERED('fm_native_currency_map')&&[P Leaf Axis Safe]=1&&[N Period Available]=1
RETURN INT(_domain&&NOT ISBLANK(_id)&&_validCut&&_member=1&&_count=1)'''


def build(destination,source):
    if destination.exists():raise ValueError('Preserve specialized guard attempt')
    b=regression.checked(source)
    if b.get('Prototype') not in {'actual-value-presentation','routed-prepared-cells'}:raise ValueError('Unknown prepared parent')
    db=deepcopy(json.loads((source/'candidate.json').read_text()));m=prepared.adapter.planning.measures(db)
    if shared_gate.GATE not in m:raise ValueError('Missing shared admission')
    m[shared_gate.GATE]['expression']=EXPRESSION
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    queries=json.loads((destination/'queries.json').read_text())
    query=routed_cells.eligibility_query(next(q['query'] for q in queries if q['name']=='share-expanded/full-core/candidate'))
    queries=[q for q in queries if q['name']!='eligibility-count']
    queries.append({'name':'eligibility-count','model':'candidate','query':query})
    (destination/'queries.json').write_text(json.dumps(queries))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    shutil.copy2(Path(routed_cells.__file__),destination/'routed_cells.py')
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**b,'Files':files,'Prototype':'specialized-leaf-admission',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'CompanyDeployment':False,
        'AdmissionProof':'One country/cycle/driver plus one chosen source is the exact complete unique source cohort; source-specific scope membership is checked.'},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


if __name__=='__main__':
    import sys
    print(json.dumps(cell_fact.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
