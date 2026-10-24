"""Refresh-validated serving snapshot; interactive file guards remain live.

At refresh compare every prepared monthly input, source/sector key, cutoff,
calendar and period key to the current raw model. If any check fails, use the
complete grouped calculation (never another unverified cache). A ready snapshot
can read leaf cells directly; arbitrary aggregate Share still uses raw totals.
Local experiment only. No Fabric ingestion/security integration is implied.
"""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import cache_prepare
import cell_fact
import prepared
import probe
import regression
import sector_dim

HEALTH='fm_serving_health'
KEY='ServingSourceSectorKey'
COMPATIBLE='P Snapshot Compatible'
FULL='P Snapshot Full Cell'


def key(source,sector):
    return 'FORMAT(LEN('+source+'),"0")&":"&'+source+'&'+sector


def health():
    definitions='''VAR _defs=UNION(SELECTCOLUMNS(FILTER('fm_native_catalog',
 'fm_native_catalog'[RowID] IN {"market","abbott","pi","net"}),
 "Metric",'fm_native_catalog'[RowID],"Display",'fm_native_catalog'[Display],
 "Comp",'fm_native_catalog'[Component],"C",'fm_native_catalog'[Channel],"SC",'fm_native_catalog'[SubChannel]),
 ROW("Metric","ef","Display","Units","Comp","ef-ads-units","C","*","SC","*"),
 ROW("Metric","ef","Display","Value","Comp","ef-ads-value","C","*","SC","*"))
VAR _actual0=GENERATE(_defs,
 VAR _comp=[Comp] VAR _c=[C] VAR _sc=[SC]
 VAR _facts=FILTER('fm_review_facts','fm_review_facts'[ComponentKey]=_comp
 &&(_c="*"||'fm_review_facts'[Channel]=_c)
 &&(_sc="*"||COALESCE('fm_review_facts'[SubChannel],"")=COALESCE(_sc,"")))
 VAR _group=GROUPBY(_facts,'fm_review_facts'[SourceRevisionID],'fm_review_facts'[Sector],'fm_review_facts'[Month],
 "Raw",SUMX(CURRENTGROUP(),'fm_review_facts'[Amount]),
 "Bad",SUMX(CURRENTGROUP(),INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount]))))
 RETURN SELECTCOLUMNS(_group,"ID",'fm_review_facts'[SourceRevisionID],"Sector",'fm_review_facts'[Sector],
 "Month",DATEDIFF(DATE(2000,1,1),'fm_review_facts'[Month],MONTH),"A",IF([Bad]=0,[Raw])))
VAR _actual=SELECTCOLUMNS(_actual0,"ID",[ID],"Sector",[Sector],"Month",[Month],"Metric",[Metric],"Display",[Display],"A",[A])
'''
    parts=[]
    for (metric,display),field in cache_prepare.FIELDS.items():
        parts.append('''SELECTCOLUMNS('fm_cache_monthly',"ID",LOOKUPVALUE('fm_cache_series'[SourceID],
 'fm_cache_series'[Key],'fm_cache_monthly'[Key]),"Sector",LOOKUPVALUE('fm_cache_series'[Sector],
 'fm_cache_series'[Key],'fm_cache_monthly'[Key]),"Month",'fm_cache_monthly'[Month],
 "Metric",'''+json.dumps(metric)+',"Display",'+json.dumps(display)+',"A",\'fm_cache_monthly\'['+field+'])')
    body=definitions+'VAR _expected=UNION('+','.join(parts)+''')
VAR _amounts=ISEMPTY(EXCEPT(_actual,_expected))&&ISEMPTY(EXCEPT(_expected,_actual))
VAR _scope=SELECTCOLUMNS('fm_native_scope',"ID",'fm_native_scope'[SourceRevisionID],"S",'fm_native_scope'[Sector])
VAR _series=SELECTCOLUMNS('fm_cache_series',"ID",'fm_cache_series'[SourceID],"S",'fm_cache_series'[Sector])
VAR _storedkeys=SELECTCOLUMNS('fm_leaf_series',"K",'fm_leaf_series'[Key],"ID",'fm_leaf_series'[SourceID],"S",'fm_leaf_series'[Sector])
VAR _monthlykeys=SELECTCOLUMNS('fm_cache_series',"K",'fm_cache_series'[Key],"ID",'fm_cache_series'[SourceID],"S",'fm_cache_series'[Sector])
VAR _keys=COUNTROWS(_scope)=COUNTROWS(_series)&&ISEMPTY(EXCEPT(_scope,_series))&&ISEMPTY(EXCEPT(_series,_scope))
 &&ISEMPTY(EXCEPT(_storedkeys,_monthlykeys))&&ISEMPTY(EXCEPT(_monthlykeys,_storedkeys))
VAR _source=SELECTCOLUMNS('fm_native_files',"ID",'fm_native_files'[SourceRevisionID],
 "IMS",'fm_native_files'[IMSActualsThrough],"EF",'fm_native_files'[ExFactoryActualsThrough])
VAR _review=SELECTCOLUMNS('fm_review_files',"ID",'fm_review_files'[SourceRevisionID],
 "IMS",'fm_review_files'[IMSActualsThrough],"EF",'fm_review_files'[ExFactoryActualsThrough])
VAR _stored=SELECTCOLUMNS(SUMMARIZE('fm_leaf_series','fm_leaf_series'[SourceID],'fm_leaf_series'[IMS],'fm_leaf_series'[EF]),
 "ID",'fm_leaf_series'[SourceID],"IMS",EDATE(DATE(2000,1,1),'fm_leaf_series'[IMS]),"EF",EDATE(DATE(2000,1,1),'fm_leaf_series'[EF]))
VAR _cuts=ISEMPTY(EXCEPT(_source,_stored))&&ISEMPTY(EXCEPT(_stored,_source))
 &&ISEMPTY(EXCEPT(_review,_stored))&&ISEMPTY(EXCEPT(_stored,_review))
VAR _calendar=SELECTCOLUMNS(VALUES('fm_cache_monthly'[Month]),"Month",EDATE(DATE(2000,1,1),'fm_cache_monthly'[Month]))
VAR _axis=SELECTCOLUMNS('fm_review_axis',"Month",'fm_review_axis'[Month])
VAR _cal=COUNTROWS(_axis)=COUNTROWS(_calendar)&&ISEMPTY(EXCEPT(_axis,_calendar))&&ISEMPTY(EXCEPT(_calendar,_axis))
 &&COUNTROWS(FILTER('fm_review_facts','fm_review_facts'[Month]<>DATE(YEAR('fm_review_facts'[Month]),MONTH('fm_review_facts'[Month]),1)))=0
VAR _periods=CROSSJOIN(SELECTCOLUMNS('fm_leaf_series',"Key",'fm_leaf_series'[Key]),
 SELECTCOLUMNS('fm_native_periods',"Year",'fm_native_periods'[Year],"Kind",'fm_native_periods'[PeriodType]))
VAR _kpi=SELECTCOLUMNS('fm_leaf_kpi',"Key",'fm_leaf_kpi'[Key],"Year",'fm_leaf_kpi'[Year],"Kind",'fm_leaf_kpi'[Kind])
VAR _coverage=COUNTROWS(_periods)=COUNTROWS(_kpi)&&ISEMPTY(EXCEPT(_periods,_kpi))&&ISEMPTY(EXCEPT(_kpi,_periods))
 &&COUNTROWS('fm_executive_cells')=COUNTROWS(_kpi)*84
VAR _share=COUNTROWS(FILTER('fm_native_catalog','fm_native_catalog'[RowID]="share"&&(
 'fm_native_catalog'[Component]<>LOOKUPVALUE('fm_native_catalog'[Component],'fm_native_catalog'[RowID],"abbott",'fm_native_catalog'[Display],'fm_native_catalog'[Display])
 ||'fm_native_catalog'[Denominator]<>LOOKUPVALUE('fm_native_catalog'[Component],'fm_native_catalog'[RowID],"market",'fm_native_catalog'[Display],'fm_native_catalog'[Display])
 ||'fm_native_catalog'[Channel]<>LOOKUPVALUE('fm_native_catalog'[Channel],'fm_native_catalog'[RowID],"abbott",'fm_native_catalog'[Display],'fm_native_catalog'[Display])
 ||'fm_native_catalog'[SubChannel]<>LOOKUPVALUE('fm_native_catalog'[SubChannel],'fm_native_catalog'[RowID],"abbott",'fm_native_catalog'[Display],'fm_native_catalog'[Display])
 ||'fm_native_catalog'[Channel]<>LOOKUPVALUE('fm_native_catalog'[Channel],'fm_native_catalog'[RowID],"market",'fm_native_catalog'[Display],'fm_native_catalog'[Display])
 ||'fm_native_catalog'[SubChannel]<>LOOKUPVALUE('fm_native_catalog'[SubChannel],'fm_native_catalog'[RowID],"market",'fm_native_catalog'[Display],'fm_native_catalog'[Display]))))=0
RETURN ROW("Ready",INT(_amounts&&_keys&&_cuts&&_cal&&_coverage&&_share),
 "Amounts",INT(_amounts),"Keys",INT(_keys),"Cutoffs",INT(_cuts),"Calendar",INT(_cal),"Coverage",INT(_coverage),"ShareDefinition",INT(_share))'''
    return {'name':HEALTH,'isHidden':True,
        'columns':[{'name':n,'dataType':'int64','type':'calculatedTableColumn','sourceColumn':'['+n+']','summarizeBy':'none'}
            for n in ('Ready','Amounts','Keys','Cutoffs','Calendar','Coverage','ShareDefinition')],
        'partitions':[{'name':HEALTH,'mode':'import','source':{'type':'calculated','expression':body}}]}


def patch(database,cache):
    fixed=deepcopy(database);tables={t['name']:t for t in fixed['model']['tables']};m=prepared.adapter.planning.measures(fixed)
    if HEALTH in tables or 'fm_cache_monthly' in tables:raise ValueError('Snapshot already added')
    fixed['model']['tables'].extend(deepcopy([t for t in cache['model']['tables'] if t['name'] in {'fm_cache_series','fm_cache_monthly'}]))
    if len(fixed['model']['tables'])!=len(tables)+2:raise ValueError('Require actual-export monthly source')
    tables['fm_native_scope']['columns'].append({'name':KEY,'dataType':'string','type':'calculated','isHidden':True,
        'summarizeBy':'none','expression':key("'fm_native_scope'[SourceRevisionID]","'fm_native_scope'[Sector]")})
    # Materialize the foreign key in the table source, before relationships.
    # A calculated column looking up the related row dimension creates a cycle.
    sector="LOOKUPVALUE('fm_leaf_series'[Sector],'fm_leaf_series'[Key],'fm_leaf_kpi'[Key])"
    cell=tables[cell_fact.FACT];source=cell['partitions'][0]['source']
    marker="SELECTCOLUMNS('fm_leaf_kpi',"
    if source['expression'].count(marker)!=84:raise ValueError('Unknown exact cell source')
    source['expression']=source['expression'].replace(marker,marker+json.dumps(KEY)+','+key("'fm_leaf_kpi'[SourceID]",sector)+',')
    cell['columns'].append({'name':KEY,'dataType':'string','type':'calculatedTableColumn','sourceColumn':'['+KEY+']',
        'isHidden':True,'summarizeBy':'none'})
    fixed['model']['relationships']=[r for r in fixed['model']['relationships'] if r['name']!='ExecutiveCell-2']
    fixed['model']['relationships'].append({'name':'ExecutiveCell-SourceScope','fromTable':cell_fact.FACT,'fromColumn':KEY,
        'fromCardinality':'many','toTable':'fm_native_scope','toColumn':KEY,'toCardinality':'one','crossFilteringBehavior':'oneDirection'})
    fixed['model']['tables'].append(health())
    target=tables['fm_native_measures']['measures']
    complete=m['N Summary Cell']['expression'].replace('[N Plan]','[P Grouped Plan]').replace('[N Benchmark]','[P Grouped Benchmark]')
    if complete==m['N Summary Cell']['expression']:raise ValueError('Unknown complete cell expression')
    target.append({'name':FULL,'isHidden':True,'expression':complete})
    target.append({'name':COMPATIBLE,'isHidden':True,'expression':'''VAR _row=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],SELECTEDVALUE('fm_review_files'[Country]))
RETURN INT(SUM('fm_serving_health'[Ready])=1&&HASONEVALUE('fm_review_files'[Country])&&HASONEVALUE('fm_review_files'[DemandCycle])
 &&_row IN {"market","abbott","share","pi","net","ef"}
 &&(_display="Units"||(_display="Value"&&(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"||_row="share")))
 &&(_display<>"Value"||NOT ISBLANK(_currency))
 &&NOT ISFILTERED('fm_review_facts')&&NOT ISFILTERED('fm_native_catalog')&&NOT ISFILTERED('fm_native_rows')
 &&NOT ISFILTERED('fm_native_currency_map'))'''})
    small='''VAR _display=[N Display]
VAR _scenario=IF(SELECTEDVALUE('fm_native_lines'[Chart])="demand",BLANK(),
 COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario])))
VAR _leaf=ISINSCOPE('''+"'"+sector_dim.DIM+"'[SectorLabel])"+'''
VAR _ready=['''+COMPATIBLE+''']=1
'''
    m[cell_fact.VALUE]['expression']=small+'''VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _w=SELECTEDVALUE('fm_native_columns'[Window])
RETURN IF(_ready,IF(_leaf,
 IF([N Source OK]=1&&[N Period Available]=1&&(_key="plan"||_w IN VALUES('fm_native_trend'[Window])),
 '''+cell_fact.filtered('Amount',True)+'''),['''+FULL+''']),['''+FULL+'''])'''
    oldfmt=m['N Summary Cell']['formatStringDefinition']['expression'].replace('SELECTEDMEASURE()','['+cell_fact.VALUE+']')
    m[cell_fact.VALUE]['formatStringDefinition']['expression']=small+'RETURN IF(_ready&&_leaf,'+cell_fact.filtered('FormatCode')+',('+oldfmt+'))'
    legacy=m[cell_fact.COLOR]['expression']
    m[cell_fact.COLOR]['expression']=small+'RETURN IF(_ready&&_leaf,'+cell_fact.filtered('Color')+',('+legacy+'))'
    return fixed


def build(destination,source,monthly):
    if destination.exists():raise ValueError('Preserve snapshot experiment')
    bound=regression.checked(source);other=regression.checked(monthly)
    if bound.get('Prototype')!='specialized-leaf-admission' or other.get('Prototype')!='source-prepared-cache':
        raise ValueError('Require bound prepared leaf and actual monthly snapshots')
    if probe.digest(source/'baseline.json')!=probe.digest(monthly/'baseline.json'):
        raise ValueError('Serving snapshots came from different raw model inputs')
    db=patch(json.loads((source/'candidate.json').read_text()),json.loads((monthly/'candidate.json').read_text()))
    destination.mkdir(parents=True);(destination/'candidate.json').write_text(json.dumps(db,ensure_ascii=False))
    for n in ('baseline.json','queries.json','expected.json','preparation.json','run_profile.ps1','launch_synthetic_engine.ps1'):
        shutil.copy2(source/n,destination/n)
    queries=[q for q in json.loads((destination/'queries.json').read_text()) if q['name']!='eligibility-count']
    queries.append({'name':'snapshot-health','model':'candidate','query':"EVALUATE '"+HEALTH+"'"})
    (destination/'queries.json').write_text(json.dumps(queries))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({**bound,'Files':files,'Prototype':'refresh-validated-snapshot',
        'ParentSHA256':probe.digest(source/'FROZEN-INPUTS.json'),'MonthlyParentSHA256':probe.digest(monthly/'FROZEN-INPUTS.json'),
        'CompanyDeployment':False,'AmountsCheckedAtRefresh':'Bidirectional exact EXCEPT of every core monthly source/sector amount, invalid group preserved as BLANK.',
        'StaleOrUnsupported':'Complete grouped raw fallback; not another cached Plan/Benchmark.'},indent=2))
    return {'Directory':str(destination),'Queries':len(queries)}


if __name__=='__main__':
    import sys
    print(json.dumps(cell_fact.verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
