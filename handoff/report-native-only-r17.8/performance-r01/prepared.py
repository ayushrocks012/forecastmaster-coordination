"""Separate local prepared-component prototype; no Fabric or release mutation.

Materialize the existing per-source/sector/month validity grouping once at
refresh. Period, trend, weighted-share and matrix calculations remain R02.
Unqualified channel/FX/catalog contexts use the exact preserved R02 kernel.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
R02 = HERE.parent / 'ui-correction-r02'
TABLE = 'fm_perf_monthly'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


adapter = load('perf_r02_adapter', R02 / 'adapter.py')

PREPARATION = '''VAR _metrics=UNION(
 SELECTCOLUMNS(FILTER(ALL('fm_native_catalog'),
 'fm_native_catalog'[RowID] IN {"market","abbott","pi","net"}),
 "Metric",'fm_native_catalog'[RowID],"Display",'fm_native_catalog'[Display],
 "Component",'fm_native_catalog'[Component],"C",'fm_native_catalog'[Channel],
 "S",'fm_native_catalog'[SubChannel]),
 ROW("Metric","ef","Display","Units","Component","ef-ads-units","C","*","S","*"),
 ROW("Metric","ef","Display","Value","Component","ef-ads-value","C","*","S","*"))
RETURN GENERATE(_metrics,
 VAR _component=[Component] VAR _channel=[C] VAR _sub=[S]
 VAR _facts=FILTER(ALL('fm_review_facts'),
 'fm_review_facts'[ComponentKey]=_component
 &&(_channel="*"||'fm_review_facts'[Channel]=_channel)
 &&(_sub="*"||COALESCE('fm_review_facts'[SubChannel],"")=COALESCE(_sub,"")))
 VAR _group=GROUPBY(_facts,'fm_review_facts'[SourceRevisionID],
 'fm_review_facts'[Sector],'fm_review_facts'[Month],
 "Amount",SUMX(CURRENTGROUP(),'fm_review_facts'[Amount]),
 "Bad",SUMX(CURRENTGROUP(),INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount]))))
 RETURN SELECTCOLUMNS(FILTER(_group,[Bad]=0),
 "SourceRevisionID",'fm_review_facts'[SourceRevisionID],
 "Sector",'fm_review_facts'[Sector],"Month",'fm_review_facts'[Month],"Amount",[Amount]))'''


def expression(original, denominator=False):
    marker = 'VAR _date=SELECTEDVALUE'
    if original.count(marker) != 1:
        raise ValueError('Unknown R02 monthly kernel')
    prefix = original.split(marker)[0]
    role = '"market"' if denominator else 'IF(_row="share","abbott",_row)'
    numerator_guard = '_row="share"&&' if denominator else ''
    fallback = 'P R02 Monthly Denominator' if denominator else 'P R02 Monthly Numerator'
    return prefix + '''VAR _date=SELECTEDVALUE('fm_review_axis'[Month])
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _single=COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _fast=''' + numerator_guard + '''_row IN {"market","abbott","share","pi","net","ef"}
 &&NOT ISFILTERED('fm_review_facts')
 &&(_row<>"ef"||(ISEMPTY(EXCEPT(ALL('fm_review_facts'[Channel]),VALUES('fm_review_facts'[Channel])))
 &&ISEMPTY(EXCEPT(ALL('fm_review_facts'[SubChannel]),VALUES('fm_review_facts'[SubChannel])))))
 &&(_display="Units"||(_display="Value"&&SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"&&_single))
RETURN IF(_fast,
 VAR _pairs=SELECTCOLUMNS(GENERATE(_files,
  VAR _gd='fm_native_files'[GrowthDriver]
  RETURN SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"__Sector",'fm_native_scope'[Sector])),
  "ID",'fm_native_files'[SourceRevisionID],"Sector",[__Sector])
 VAR _metric=''' + role + '''
 RETURN IF(_sourceOK&&NOT ISBLANK(_date),
 CALCULATE(SUM('fm_perf_monthly'[Amount]),
 TREATAS(_pairs,'fm_perf_monthly'[SourceRevisionID],'fm_perf_monthly'[Sector]),
 TREATAS({_date},'fm_perf_monthly'[Month]),TREATAS({_metric},'fm_perf_monthly'[Metric]),
 TREATAS({_display},'fm_perf_monthly'[Display]))),[''' + fallback + '''])'''


def patch(database):
    fixed = deepcopy(database)
    tables = {t['name']: t for t in fixed['model']['tables']}
    if TABLE in tables:
        raise ValueError('Prepared prototype already installed')
    measures = adapter.planning.measures(fixed)
    expected = adapter.planning.measures(adapter.patch_database(adapter.selection.original_database())[0])
    rows = tables['fm_native_measures']['measures']
    for name in ('N Monthly Numerator', 'N Monthly Denominator'):
        original = adapter.selection.OLD.expression_text(measures[name]['expression'])
        if original != adapter.selection.OLD.expression_text(expected[name]['expression']):
            raise ValueError('Unknown R02 monthly expression')
        fallback = deepcopy(measures[name])
        fallback.update(name='P R02 ' + name[2:], isHidden=True)
        rows.append(fallback)
        measures[name]['expression'] = expression(original, name.endswith('Denominator'))
    fields = [('Metric', 'string'), ('Display', 'string'), ('Component', 'string'),
              ('C', 'string'), ('S', 'string'), ('SourceRevisionID', 'string'),
              ('Sector', 'string'), ('Month', 'dateTime'), ('Amount', 'double')]
    fixed['model']['tables'].append({'name': TABLE, 'isHidden': True,
        'columns': [{'name': n, 'dataType': t, 'type': 'calculatedTableColumn',
                     'sourceColumn': '[' + n + ']', 'summarizeBy': 'none'} for n, t in fields],
        'partitions': [{'name': TABLE, 'mode': 'import',
                        'source': {'type': 'calculated', 'expression': PREPARATION}}]})
    return fixed
