"""Separate reusable training work from period aggregation in the full kernel.

The complete grouped arithmetic passed the representative result comparisons,
but inlining history per period still cost seconds. Fit calculations now have
an explicit presentation-independent context; ordinary Units/Local rows do not
enter the FX transformation iterator. Both routes retain the same arithmetic.
"""
import bulk_exact
import prepared
import strictcells


def simplify(body):
    if body.count('VAR _singleRate=(')!=1 or body.count('\nVAR _cutoffs=')!=1:
        raise ValueError('Unknown rate declaration')
    body=body.replace('VAR _singleRate=(', 'VAR _singleRate=IF(_convert,(').replace('\nVAR _cutoffs=',')\nVAR _cutoffs=')
    marker='VAR _converted=GENERATE(_good,'
    if body.count(marker)!=1 or body.count('\nVAR _byCurrency=')!=1:
        raise ValueError('Unknown transformation iterator')
    body=body.replace(marker,'''VAR _simpleRows=ADDCOLUMNS(FILTER(_good,NOT _convert&&(NOT _value||_singleCurrency)),
 "CC",IF(_value,_singleCC,"Units"),"A",[Raw],"FX",0)
VAR _converted=UNION(_simpleRows,GENERATE(FILTER(_good,_convert||(_value&&NOT _singleCurrency)),''')
    return body.replace('\nVAR _byCurrency=',')\nVAR _byCurrency=')


def fit(plan,monthly,slope=False):
    body=simplify(bulk_exact.body(plan,monthly,False))
    start,end=body.index('VAR _y='),body.index('VAR _w=')
    body=body[:start]+body[end:]
    marker="VAR _trainDates=SELECTCOLUMNS(GENERATESERIES(1,_w),\"Date\",EDATE(_fitCut,[Value]-_w))"
    if body.count(marker)!=1:
        raise ValueError('Unknown training set')
    body=body.replace(marker,marker+'\nVAR _months=_trainDates')
    body=body[:body.index('VAR _denValid=')]
    result='DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_mean)),SUMX(_train,POWER([X]-_mx,2)))' if slope else '_mean'
    return body+'''
VAR _train=ADDCOLUMNS(_period,"X",DATEDIFF(EDATE(_fitCut,1-_w),[Date],MONTH)+1,
 "Y",IF(_ratio,DIVIDE([N],[D]),[N]))
VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=(_w+1)/2
VAR _mean=AVERAGEX(_train,[Y])
RETURN IF(_sourceOK&&NOT ISBLANK(_fitCut)&&_valid,'''+result+')'


def benchmark(plan,monthly):
    body=simplify(bulk_exact.body(plan,monthly,True))
    if body.count('VAR _searchDates=DISTINCT(UNION(_months,_trainDates))')!=1:
        raise ValueError('Unknown combined date scan')
    body=body.replace('VAR _searchDates=DISTINCT(UNION(_months,_trainDates))','VAR _searchDates=_months')
    start,end=body.index('VAR _train0='),body.index('VAR _values=')
    filters="REMOVEFILTERS('fm_review_axis'),REMOVEFILTERS('fm_native_periods'),REMOVEFILTERS('fm_native_columns'),REMOVEFILTERS('fm_native_headline')"
    return body[:start]+'''VAR _mean=IF(_end>_cut,CALCULATE([N Fit Mean],'''+filters+'''))
VAR _slope=IF(_end>_cut,CALCULATE([N Fit Slope],'''+filters+'''))
'''+body[end:]


def patch(database):
    fixed=bulk_exact.patch(database)
    old=prepared.adapter.planning.measures(database);current=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    for name in ('N Fit Mean','N Fit Slope'):
        if text(old[name]['expression'])!=text(expected[name]['expression']):
            raise ValueError('Unknown R03 training expression')
    plan=text(old['N Plan']['expression']);monthly=text(old['N Monthly Numerator']['expression'])
    current['N Plan']['expression']=simplify(current['N Plan']['expression'])
    current['N Benchmark']['expression']=benchmark(plan,monthly)
    current['N Fit Mean']['expression']=fit(plan,monthly)
    current['N Fit Slope']['expression']=fit(plan,monthly,True)
    return fixed
