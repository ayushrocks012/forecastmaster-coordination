"""Isolated Demand serving model: physical scope relation and batched kernels.

The eight original kernels are retained as a fully rewired legacy graph. Fast
calculations never call a monthly dispatcher inside a training/month iterator.
"""
from copy import deepcopy
import re

import prepared

DIM = 'fm_perf_sector'
KEY = 'P SectorKey'
NAMES = ('N Monthly Numerator', 'N Monthly Denominator', 'N Monthly',
         'N Fit Mean', 'N Fit Slope', 'N Plan', 'N Benchmark', 'N Trend Monthly')


def fast_name(name):
    return 'P Fast ' + name[2:]


def legacy_name(name):
    return 'P Legacy ' + name[2:]


def source_context(original):
    return prepared.expression(original).split('VAR _fast=')[0]


def conditions():
    return '''VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _currencies=SELECTCOLUMNS(VALUES('fm_review_files'[Country]),"CC",
 LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],'fm_review_files'[Country]))
RETURN INT(_row IN {"market","abbott","share","pi","net","ef"}&&NOT ISFILTERED('fm_review_facts')
 &&(_row<>"ef"||(ISEMPTY(EXCEPT(ALL('fm_review_facts'[Channel]),VALUES('fm_review_facts'[Channel])))
 &&ISEMPTY(EXCEPT(ALL('fm_review_facts'[SubChannel]),VALUES('fm_review_facts'[SubChannel])))))
 &&(_display="Units"||(_display="Value"&&SELECTEDVALUE('fm_native_currency'[Currency],"USD")="Local"
 &&COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)))'''


def filt(months, metric):
    return "TREATAS(_ids,'fm_perf_monthly'[SourceRevisionID]),TREATAS(" + months + ",'fm_perf_monthly'[Month])," + \
        "TREATAS({_display},'fm_perf_monthly'[Display]),TREATAS({" + metric + "},'fm_perf_monthly'[Metric])"


def monthly(context, denominator=False):
    return context + '\nVAR _metric=' + ('"market"' if denominator else 'IF(_row="share","abbott",_row)') + \
        '\nRETURN IF(_sourceOK&&NOT ISBLANK(_date)' + ('&&_row="share"' if denominator else '') + \
        ",CALCULATE(SUM('fm_perf_monthly'[Amount])," + filt('{_date}', '_metric') + '))'


def fit(context, slope=False):
    return context + '''
VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Month",EDATE(_cut,[Value]-_w))
VAR _metric=IF(_row="share","abbott",_row)
VAR _train0=SUMMARIZECOLUMNS('fm_perf_monthly'[Month],
 TREATAS(_ids,'fm_perf_monthly'[SourceRevisionID]),TREATAS(_dates,'fm_perf_monthly'[Month]),
 TREATAS({_display},'fm_perf_monthly'[Display]),
 "N",CALCULATE(SUM('fm_perf_monthly'[Amount]),TREATAS({_metric},'fm_perf_monthly'[Metric])),
 "D",IF(_row="share",CALCULATE(SUM('fm_perf_monthly'[Amount]),TREATAS({"market"},'fm_perf_monthly'[Metric]))))
VAR _train=ADDCOLUMNS(_train0,"X",DATEDIFF(EDATE(_cut,1-_w),'fm_perf_monthly'[Month],MONTH)+1,
 "Y",IF(_row="share",DIVIDE([N],[D]),[N]))
VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=(_w+1)/2 VAR _my=AVERAGEX(_train,[Y])
RETURN IF(_sourceOK&&NOT ISBLANK(_cut)&&_valid,
 ''' + ('DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2)))' if slope else '_my') + ')'


def plan(context, period):
    num, den = filt('_months', '_metric'), filt('_months', '"market"')
    return context + period + '''
VAR _metric=IF(_row="share","abbott",_row)
VAR _num=CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + num + ''')
VAR _numMonths=CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + num + ''')
VAR _den=IF(_row="share",CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + den + '''))
VAR _denMonths=IF(_row="share",CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + den + '''))
RETURN IF(_sourceOK&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_numMonths=_count,
 IF(_row="share",IF(_denMonths=_count,DIVIDE(_num,_den)),_num))'''


def benchmark(context, period):
    return context + period + '''
VAR _metric=IF(_row="share","abbott",_row)
VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _actualMonths=FILTER(_months,[Date]<=_cut)
VAR _futureMonths=FILTER(_months,[Date]>_cut)
VAR _actualCount=COUNTROWS(_actualMonths) VAR _futureCount=COUNTROWS(_futureMonths)
VAR _actual=CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + filt('_actualMonths', '_metric') + ''')
VAR _actualCoverage=CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + filt('_actualMonths', '_metric') + ''')
VAR _mean=IF(_futureCount>0,CALCULATE([P Fast Fit Mean],REMOVEFILTERS('fm_review_axis')))
VAR _slope=IF(_futureCount>0,CALCULATE([P Fast Fit Slope],REMOVEFILTERS('fm_review_axis')))
VAR _d=IF(_row="share",CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + filt('_months', '"market"') + '''))
VAR _dCoverage=IF(_row="share",CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + filt('_months', '"market"') + '''))
VAR _dFuture=SUMMARIZECOLUMNS('fm_perf_monthly'[Month],
 ''' + filt('_futureMonths', '"market"') + ''',"D",SUM('fm_perf_monthly'[Amount]))
VAR _future=IF(_row="share",SUMX(_dFuture,[D]*(_mean+_slope*(DATEDIFF(_cut,'fm_perf_monthly'[Month],MONTH)+_w-(_w+1)/2))),
 SUMX(_futureMonths,_mean+_slope*(DATEDIFF(_cut,[Date],MONTH)+_w-(_w+1)/2)))
RETURN IF(_sourceOK&&NOT ISBLANK([N Fit Cutoff])&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0
 &&COALESCE(_actualCoverage,0)=_actualCount&&(_futureCount=0||(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope))),
 IF(_row="share",IF(_dCoverage=_count,DIVIDE(COALESCE(_actual,0)+COALESCE(_future,0),_d)),
 COALESCE(_actual,0)+COALESCE(_future,0)))'''


def patch(database):
    fixed = prepared.patch(database)
    tables = {t['name']: t for t in fixed['model']['tables']}
    measures = prepared.adapter.planning.measures(fixed)
    original = prepared.adapter.planning.measures(database)
    target = tables['fm_native_measures']['measures']
    # Discard the earlier monthly dispatcher aliases; the full legacy graph is
    # independently wired, so fast branches cannot recursively enter it.
    target[:] = [m for m in target if not m['name'].startswith('P R02 ')]
    text = prepared.adapter.selection.OLD.expression_text
    pattern = re.compile(r'\[(' + '|'.join(re.escape(n) for n in sorted(NAMES, key=len, reverse=True)) + r')\]')
    context = source_context(text(original['N Monthly Numerator']['expression']))
    period = text(original['N Plan']['expression']).split('VAR _ratio=')[0]
    fast = {'N Monthly Numerator': monthly(context), 'N Monthly Denominator': monthly(context, True),
        'N Monthly': 'VAR _row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market") RETURN IF(_row="share",DIVIDE([P Fast Monthly Numerator],[P Fast Monthly Denominator]),[P Fast Monthly Numerator])',
        'N Fit Mean': fit(context), 'N Fit Slope': fit(context, True),
        'N Plan': plan(context, period), 'N Benchmark': benchmark(context, period),
        'N Trend Monthly': '''VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
 VAR _m=SELECTEDVALUE('fm_review_axis'[Month])
 RETURN IF(NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,[P Fast Monthly],
 VAR _mean=CALCULATE([P Fast Fit Mean],REMOVEFILTERS('fm_review_axis'))
 VAR _slope=CALCULATE([P Fast Fit Slope],REMOVEFILTERS('fm_review_axis'))
 RETURN IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),_mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))))'''}
    target.append({'name': 'P Perf Eligible', 'expression': conditions(), 'isHidden': True})
    for name in NAMES:
        legacy = deepcopy(original[name])
        legacy.update(name=legacy_name(name), expression=pattern.sub(lambda m: '[' + legacy_name(m[1]) + ']', text(legacy['expression'])), isHidden=True)
        accelerated = deepcopy(original[name])
        accelerated.update(name=fast_name(name), expression=fast[name], isHidden=True)
        target.extend([legacy, accelerated])
        measures[name]['expression'] = 'IF([P Perf Eligible]=1,[' + fast_name(name) + '],[' + legacy_name(name) + '])'
    for name, expression in [('fm_native_scope', 'FORMAT(LEN([GrowthDriver]),"0")&":"&[GrowthDriver]&[Sector]'),
            (prepared.TABLE, 'VAR _driver=LOOKUPVALUE(\'fm_native_files\'[GrowthDriver],\'fm_native_files\'[SourceRevisionID],[SourceRevisionID]) RETURN FORMAT(LEN(_driver),"0")&":"&_driver&[Sector]')]:
        tables[name]['columns'].append({'name': KEY, 'dataType': 'string', 'type': 'calculated', 'expression': expression, 'isHidden': True})
    cols = ['GrowthDriver', 'Sector', 'SectorLabel', KEY]
    fixed['model']['tables'].append({'name': DIM,
        'columns': [{'name': n, 'dataType': 'string', 'type': 'calculatedTableColumn', 'sourceColumn': '[' + n + ']', 'summarizeBy': 'none'} for n in cols],
        'partitions': [{'name': DIM, 'mode': 'import', 'source': {'type': 'calculated', 'expression':
            'DISTINCT(SELECTCOLUMNS(\'fm_native_scope\',' + ','.join('"' + n + '",\'fm_native_scope\'[' + n + ']' for n in cols) + '))'}}]})
    for name, direction in [('fm_native_scope', 'bothDirections'), (prepared.TABLE, 'oneDirection')]:
        fixed['model']['relationships'].append({'name': 'Perf-Sector-' + name, 'fromTable': name, 'fromColumn': KEY,
            'toTable': DIM, 'toColumn': KEY, 'crossFilteringBehavior': direction})
    return fixed
