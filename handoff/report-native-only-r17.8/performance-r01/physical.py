"""Separate physical-source serving prototype, with exact legacy fallback.

Source selection and scope propagate through relationships. Reusable ordinal
moments support an arbitrary admitted cutoff; Share totals still fit monthly
aggregate ratios. No source-specific cutoff is baked into the moments.
"""
from copy import deepcopy

import prepared
import star
import moments

ORDINAL = 'AmountMonth'


def filters(table, months, metric=None):
    result = "TREATAS(" + months + ",'" + table + "'[Month]),TREATAS({_display},'" + table + "'[Display])"
    if metric:
        result += ",TREATAS({" + metric + "},'" + table + "'[Metric])"
    return result


def sum_value(table, column, months, metric=None):
    return "CALCULATE(SUM('" + table + "'[" + column + ']),' + filters(table, months, metric) + ')'


def fit(context, slope=False):
    def aggregate(column):
        return 'IF(_shareLeaf,' + sum_value(moments.SHARE, column, '_dates') + ',' + sum_value(prepared.TABLE, column, '_dates', '_metric') + ')'
    return context + '''
VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Month",EDATE(_cut,[Value]-_w))
VAR _metric=IF(_row="share","abbott",_row)
VAR _shareLeaf=_row="share"&&HASONEVALUE('fm_perf_sector'[P SectorKey])
 &&CALCULATE(DISTINCTCOUNT('fm_perf_share'[SourceRevisionID]),''' + filters(moments.SHARE, '_dates') + ''')=1
VAR _coverage=IF(_shareLeaf,CALCULATE(DISTINCTCOUNT('fm_perf_share'[Month]),''' + filters(moments.SHARE, '_dates') + '''),
 CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + filters(prepared.TABLE, '_dates', '_metric') + '''))
VAR _sum=''' + aggregate('Amount') + '''
VAR _weighted=''' + aggregate(ORDINAL) + '''
VAR _center=DATEDIFF(DATE(2000,1,1),_cut,MONTH)-(_w-1)/2
RETURN IF(_row="share"&&NOT _shareLeaf,[P Group Fit ''' + ('Slope' if slope else 'Mean') + '''],
 IF(_sourceOK&&NOT ISBLANK(_cut)&&_coverage=_w,
 ''' + ('DIVIDE(_weighted-_center*_sum,_w*(_w*_w-1)/12)' if slope else 'DIVIDE(_sum,_w)') + '))'


def remove_virtual_sources(body):
    return body.replace("TREATAS(_ids,'fm_perf_monthly'[SourceRevisionID]),", '')


def patch(database):
    fixed = star.patch(database)
    tables = {table['name']: table for table in fixed['model']['tables']}
    original = prepared.adapter.planning.measures(database)
    current = prepared.adapter.planning.measures(fixed)
    text = prepared.adapter.selection.OLD.expression_text
    old_context = star.source_context(text(original['N Monthly Numerator']['expression']))
    context = '''VAR _sourceOK=[N Source OK]=1
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _date=SELECTEDVALUE('fm_review_axis'[Month])'''
    for name in star.NAMES:
        measure = current[star.fast_name(name)]
        body = text(measure['expression'])
        if old_context in body:
            body = body.replace(old_context, context)
        measure['expression'] = remove_virtual_sources(body)
    # Natural source filtering must not replace the legacy per-line scenario
    # projection in an SOP/legacy chart context.
    current['P Perf Eligible']['expression'] = current['P Perf Eligible']['expression'].replace(
        'RETURN INT(', "RETURN INT(NOT ISFILTERED('fm_native_lines')&&NOT ISFILTERED('fm_native_scenario'[Scenario])&&")
    target = tables['fm_native_measures']['measures']
    for role in ('Mean', 'Slope'):
        group = deepcopy(current['P Fast Fit ' + role])
        group['name'] = 'P Group Fit ' + role
        target.append(group)
        current['P Fast Fit ' + role]['expression'] = fit(context, role == 'Slope')

    source = tables[prepared.TABLE]['partitions'][0]['source']
    source['expression'] = 'VAR _base=(' + source['expression'] + ')\nRETURN ADDCOLUMNS(_base,"' + ORDINAL + '",[Amount]*DATEDIFF(DATE(2000,1,1),[Month],MONTH))'
    tables[prepared.TABLE]['columns'].append({'name': ORDINAL, 'dataType': 'double',
        'type': 'calculatedTableColumn', 'sourceColumn': '[' + ORDINAL + ']', 'summarizeBy': 'none'})
    share_expression = moments.share_source()
    marker = ',"Fit6"'
    if share_expression.count(marker) != 1:
        raise ValueError('Unknown Share preparation')
    share_expression = share_expression[:share_expression.index(marker)] + ',"' + ORDINAL + '",[Y]*DATEDIFF(DATE(2000,1,1),[Month],MONTH))'
    fields = [('SourceRevisionID', 'string'), ('Sector', 'string'), ('Month', 'dateTime'),
              ('Display', 'string'), (star.KEY, 'string'), ('Amount', 'double'), (ORDINAL, 'double')]
    fixed['model']['tables'].append({'name': moments.SHARE, 'isHidden': True,
        'columns': [{'name': n, 'dataType': kind, 'type': 'calculatedTableColumn', 'sourceColumn': '[' + n + ']', 'summarizeBy': 'none'} for n, kind in fields],
        'partitions': [{'name': moments.SHARE, 'mode': 'import', 'source': {'type': 'calculated', 'expression': share_expression}}]})
    fixed['model']['relationships'].append({'name': 'Perf-Sector-Share', 'fromTable': moments.SHARE,
        'fromColumn': star.KEY, 'toTable': star.DIM, 'toColumn': star.KEY})
    for fact in (prepared.TABLE, moments.SHARE):
        for source_name in ('fm_review_files', 'fm_native_files'):
            fixed['model']['relationships'].append({'name': 'Perf-Source-' + source_name + '-' + fact,
                'fromTable': fact, 'fromColumn': 'SourceRevisionID', 'toTable': source_name,
                'toColumn': 'SourceRevisionID'})
    # Future Share remains a denominator-weighted sum of the fitted monthly
    # ratio. Ordinal moments allow different admitted source cutoffs.
    value = current['P Fast Benchmark']['expression']
    start = value.index('VAR _dFuture=')
    end = value.index('RETURN IF(_sourceOK', start)
    current['P Fast Benchmark']['expression'] = value[:start] + '''VAR _futureD=''' + sum_value(prepared.TABLE, 'Amount', '_futureMonths', '"market"') + '''
VAR _futureDX=''' + sum_value(prepared.TABLE, ORDINAL, '_futureMonths', '"market"') + '''
VAR _center=DATEDIFF(DATE(2000,1,1),_cut,MONTH)-(_w-1)/2
VAR _future=IF(_row="share",_mean*_futureD+_slope*(_futureDX-_center*_futureD),
 SUMX(_futureMonths,_mean+_slope*(DATEDIFF(_cut,[Date],MONTH)+_w-(_w+1)/2)))
''' + value[end:]
    return fixed
