"""Prepare period/training sets once, retaining exact R02 fallback semantics."""
from copy import deepcopy

import prepared


def setup(original):
    value = prepared.expression(original)
    definitions, rest = value.split('RETURN IF(_fast,', 1)
    pairs = rest[rest.index('VAR _pairs='):rest.index('VAR _metric=')]
    return definitions, pairs


def filters(months, metric):
    return "TREATAS(_pairs,'fm_perf_monthly'[SourceRevisionID],'fm_perf_monthly'[Sector])," + \
        "TREATAS(" + months + ",'fm_perf_monthly'[Month]),TREATAS({_display},'fm_perf_monthly'[Display])," + \
        "TREATAS({" + metric + "},'fm_perf_monthly'[Metric])"


def plan(original, monthly):
    definitions, pairs = setup(monthly)
    period = original[:original.index('VAR _ratio=')]
    numerator = filters('_months', '_metric')
    denominator = filters('_months', '"market"')
    return definitions + '\nRETURN IF(_fast,\n' + pairs + period + '''
VAR _metric=IF(_row="share","abbott",_row)
VAR _num=CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + numerator + ''')
VAR _numMonths=CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + numerator + ''')
VAR _den=IF(_row="share",CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + denominator + '''))
VAR _denMonths=IF(_row="share",CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + denominator + '''))
RETURN IF(_sourceOK&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_numMonths=_count,
 IF(_row="share",IF(_denMonths=_count,DIVIDE(_num,_den)),_num)),[P R02 Plan])'''


def fit(monthly, slope=False):
    definitions, pairs = setup(monthly)
    # The month set is generated before grouping; Share divides the aggregate
    # monthly components, never sector percentages or precomputed Share slopes.
    return definitions + '\nRETURN IF(_fast,\n' + pairs + '''
VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Month",EDATE(_cut,[Value]-_w))
VAR _metric=IF(_row="share","abbott",_row)
VAR _train0=SUMMARIZECOLUMNS('fm_perf_monthly'[Month],
 TREATAS(_pairs,'fm_perf_monthly'[SourceRevisionID],'fm_perf_monthly'[Sector]),
 TREATAS(_dates,'fm_perf_monthly'[Month]),TREATAS({_display},'fm_perf_monthly'[Display]),
 "N",CALCULATE(SUM('fm_perf_monthly'[Amount]),TREATAS({_metric},'fm_perf_monthly'[Metric])),
 "D",IF(_row="share",CALCULATE(SUM('fm_perf_monthly'[Amount]),TREATAS({"market"},'fm_perf_monthly'[Metric]))))
VAR _train=ADDCOLUMNS(_train0,"X",DATEDIFF(EDATE(_cut,1-_w),'fm_perf_monthly'[Month],MONTH)+1,
 "Y",IF(_row="share",DIVIDE([N],[D]),[N]))
VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=(_w+1)/2 VAR _my=AVERAGEX(_train,[Y])
RETURN IF(_sourceOK&&NOT ISBLANK(_cut)&&_valid,
 ''' + ('DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2)))' if slope else '_my') + \
        '),[P R02 Fit ' + ('Slope' if slope else 'Mean') + '])'


def patch(database):
    fixed = prepared.patch(database)
    old = prepared.adapter.planning.measures(database)
    current = prepared.adapter.planning.measures(fixed)
    table = next(t for t in fixed['model']['tables'] if t['name'] == 'fm_native_measures')
    text = prepared.adapter.selection.OLD.expression_text
    monthly = text(old['N Monthly Numerator']['expression'])
    changes = {'N Plan': plan(text(old['N Plan']['expression']), monthly),
               'N Fit Mean': fit(monthly), 'N Fit Slope': fit(monthly, True)}
    for name, expression in changes.items():
        fallback = deepcopy(old[name])
        fallback.update(name='P R02 ' + name[2:], isHidden=True)
        table['measures'].append(fallback)
        current[name]['expression'] = expression
    return fixed
