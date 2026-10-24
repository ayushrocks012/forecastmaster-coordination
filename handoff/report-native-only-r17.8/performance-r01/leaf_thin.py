"""Reuse exact cohort admission and one source identity across sector rows.

The leaf domain is unchanged. Source admission remains the exact original
guard, normalized only over dimensions it never reads. Single-country/cycle/
driver admission proves one source; scope-sector membership still intersects
that source with every current scope/tier filter. Out-of-domain contexts keep
the complete grouped fallback. Numeric helper switches use direct metric labels.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil

import bulkprobe
import leaf_model
import leaf_prepare
import prepared
import regression

UNUSED=('fm_native_periods','fm_native_columns','fm_native_headline','fm_native_chart_trend',
        'fm_native_trend','fm_review_axis','fm_native_metric','fm_native_catalog','fm_native_display',
        'fm_native_currency','fm_native_view','fm_native_groups')
LABELS={'market':'Market','abbott':'Abbott IMS','share':'Share %','pi':'PI','net':'IMS minus PI','ef':'Ex-factory ADS'}


def normalize(name):
    args=["REMOVEFILTERS('"+n+"')" for n in (*UNUSED,'fm_native_scope')]
    return "VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\nRETURN CALCULATE(["+name+'],'+','.join(args)+",TREATAS(_drivers,'fm_native_scope'[GrowthDriver]))"


SOURCE='''VAR _countries=VALUES('fm_review_files'[Country])
VAR _cycles=VALUES('fm_review_files'[DemandCycle])
VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _chosen=INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))
VAR _ids=CALCULATETABLE(VALUES('fm_native_files'[SourceRevisionID]),
 TREATAS(_chosen,'fm_native_files'[SourceRevisionID]),TREATAS(_countries,'fm_native_files'[Country]),
 TREATAS(_cycles,'fm_native_files'[DemandCycle]),TREATAS(_drivers,'fm_native_files'[GrowthDriver]),
 FILTER(ALL('fm_native_files'[Scenario]),ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario))
RETURN IF([N Source OK]=1&&COUNTROWS(_ids)=1,MAXX(_ids,'fm_native_files'[SourceRevisionID]))'''


def helper(benchmark):
    def metric(window):
        clauses=[]
        for row,label in LABELS.items():
            clauses.extend([json.dumps(label),'IF(_units,SUM(\'fm_leaf_kpi\'['+leaf_prepare.field(row,'Units',window)+
                ']),SUM(\'fm_leaf_kpi\'['+leaf_prepare.field(row,'Value',window)+']))'])
        return "SWITCH(SELECTEDVALUE('fm_native_metric'[MetricLabel]),"+','.join(clauses)+')'
    return 'VAR _units=[N Display]="Units"\nRETURN '+(
        "SWITCH(SELECTEDVALUE('fm_native_trend'[Window],12),"+','.join(str(w)+','+metric(w) for w in (6,12,24))+')'
        if benchmark else metric(0))


def body(original,benchmark):
    marker='RETURN IF(_domain,'
    if original.count(marker)!=1 or original.count('VAR _pairs=SELECTCOLUMNS(GENERATE(_files,')!=1:
        raise ValueError('Unknown prepared leaf body')
    fallback='[P Grouped '+('Benchmark' if benchmark else 'Plan')+']'
    keep=original[:original.index(marker)+len(marker)]
    return keep+'''
VAR _id=[P Leaf Source ID]
VAR _cut=IF(_row="ef",CALCULATE(MAX('fm_native_files'[ExFactoryActualsThrough]),
 TREATAS({_id},'fm_native_files'[SourceRevisionID])),CALCULATE(MAX('fm_native_files'[IMSActualsThrough]),
 TREATAS({_id},'fm_native_files'[SourceRevisionID])))
VAR _validCut=NOT ISBLANK(_cut)&&_cut>=DATE(2000,1,1)&&_cut<DATE(2100,1,1)
VAR _currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],
 SELECTEDVALUE('fm_review_files'[Country]))
VAR _currencyOK=_display<>"Value"||NOT ISBLANK(_currency)
VAR _sectors=CALCULATETABLE(VALUES('fm_native_scope'[Sector]),
 KEEPFILTERS(TREATAS({_id},'fm_native_scope'[SourceRevisionID])))
VAR _keys=CALCULATETABLE(VALUES('fm_leaf_series'[Key]),
 TREATAS({_id},'fm_leaf_series'[SourceID]),TREATAS(_sectors,'fm_leaf_series'[Sector]))
VAR _stored=IF(_row="ef",CALCULATE(MAX('fm_leaf_series'[EF]),TREATAS(_keys,'fm_leaf_series'[Key])),
 CALCULATE(MAX('fm_leaf_series'[IMS]),TREATAS(_keys,'fm_leaf_series'[Key])))
VAR _sameCut=_cut=DATE(YEAR(_cut),MONTH(_cut),1)&&_stored=DATEDIFF(DATE(2000,1,1),_cut,MONTH)
RETURN IF(NOT ISBLANK(_id)&&_currencyOK&&_validCut&&COUNTROWS(_keys)>0,
 IF(_sameCut,CALCULATE(['''+('P Leaf Benchmark' if benchmark else 'P Leaf Plan')+'''],
 TREATAS(_keys,'fm_leaf_kpi'[Key]),TREATAS({_year},'fm_leaf_kpi'[Year]),
 TREATAS({_kind},'fm_leaf_kpi'[Kind])),'''+fallback+')),'+fallback+')'


def patch(database):
    fixed=deepcopy(database);m=prepared.adapter.planning.measures(fixed)
    if 'P Leaf Source ID' in m or 'P Leaf Plan' not in m:
        raise ValueError('Require untouched leaf prototype')
    if any(m[n]['expression']!=leaf_model.helper(n=='P Leaf Benchmark') for n in ('P Leaf Plan','P Leaf Benchmark')):
        raise ValueError('Unknown leaf lookup')
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    target.extend({'name':n,'expression':e,'isHidden':True} for n,e in [
        ('P Leaf Cohort Guard',m['N Source OK']['expression']),('P Leaf Source Inner',SOURCE),
        ('P Leaf Source ID',normalize('P Leaf Source Inner'))])
    m['N Source OK']['expression']=normalize('P Leaf Cohort Guard')
    for n in ('N Plan','N Benchmark'):
        m[n]['expression']=body(m[n]['expression'],n=='N Benchmark')
    for n in ('P Leaf Plan','P Leaf Benchmark'):
        m[n]['expression']=helper(n=='P Leaf Benchmark')
    return fixed


def build(destination,source):
    if destination.exists():raise ValueError('Preserve previous thin-leaf attempt')
    binding=regression.checked(source)
    if binding.get('Prototype')!='prepared-leaf-kpis':raise ValueError('Require original prepared leaf prototype')
    destination.mkdir(parents=True)
    (destination/'candidate.json').write_text(json.dumps(patch(json.loads((source/'candidate.json').read_text())),ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    for path in (Path(__file__),Path(leaf_model.__file__),Path(leaf_prepare.__file__)):
        shutil.copy2(path,destination/path.name)
    files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**binding,'Files':files,'Prototype':'thin-prepared-leaf',
        'SourceCandidateSHA256':hashlib.sha256((source/'candidate.json').read_bytes()).hexdigest()},indent=2))
    return {'Directory':str(destination),'Queries':len(json.loads((source/'queries.json').read_text()))}


if __name__=='__main__':
    import sys
    print(json.dumps(bulkprobe.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:4])),indent=2))
