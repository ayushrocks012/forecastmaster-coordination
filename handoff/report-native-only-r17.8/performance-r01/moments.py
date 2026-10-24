"""Prepared centered regression contributions; aggregate Share stays nonlinear."""
from copy import deepcopy

import prepared
import star

SHARE = 'fm_perf_share'


def weight_sum(table, months, metric=None):
    if table == prepared.TABLE:
        filters = star.filt(months, metric)
    else:
        filters = "TREATAS(_ids,'fm_perf_share'[SourceRevisionID]),TREATAS(" + months + ",'fm_perf_share'[Month]),TREATAS({_display},'fm_perf_share'[Display])"
    return 'SWITCH(_w,' + ','.join(str(w) + ",CALCULATE(SUM('" + table + "'[Fit" + str(w) + ']),' + filters + ')' for w in (6, 12, 24)) + ')'


def fit(context, slope=False):
    gold = star.filt('_dates', '_metric')
    share = "TREATAS(_ids,'fm_perf_share'[SourceRevisionID]),TREATAS(_dates,'fm_perf_share'[Month]),TREATAS({_display},'fm_perf_share'[Display])"
    return context + '''
VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Month",EDATE(_cut,[Value]-_w))
VAR _metric=IF(_row="share","abbott",_row)
VAR _shareLeaf=_row="share"&&HASONEVALUE('fm_perf_sector'[P SectorKey])&&COUNTROWS(_files)=1
VAR _coverage=IF(_shareLeaf,CALCULATE(DISTINCTCOUNT('fm_perf_share'[Month]),''' + share + '''),
 CALCULATE(DISTINCTCOUNT('fm_perf_monthly'[Month]),''' + gold + '''))
VAR _sum=IF(_shareLeaf,CALCULATE(SUM('fm_perf_share'[Amount]),''' + share + '''),
 CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + gold + '''))
VAR _weighted=IF(_shareLeaf,''' + weight_sum(SHARE, '_dates') + ',' + weight_sum(prepared.TABLE, '_dates', '_metric') + ''')
RETURN IF(_row="share"&&NOT _shareLeaf,[P Group Fit ''' + ('Slope' if slope else 'Mean') + '''],
 IF(_sourceOK&&NOT ISBLANK(_cut)&&_coverage=_w,
 ''' + ('DIVIDE(_weighted,_w*(_w*_w-1)/12)' if slope else 'DIVIDE(_sum,_w)') + '))'


def share_source():
    keys = ['SourceRevisionID', 'Sector', 'Month', 'Display', star.KEY]
    def projection(metric, amount):
        return "SELECTCOLUMNS(FILTER(ALL('fm_perf_monthly'),'fm_perf_monthly'[Metric]=\"" + metric + '\"),' + \
            ','.join('"' + key + '",\'fm_perf_monthly\'[' + key + ']' for key in keys) + \
            ',"' + amount + '\",\'fm_perf_monthly\'[Amount])'
    prefix = 'VAR _n=' + projection('abbott', 'N') + '\nVAR _d=' + projection('market', 'D') + '''
VAR _joined=ADDCOLUMNS(NATURALINNERJOIN(_n,_d),"Y",DIVIDE([N],[D]))
VAR _valid=FILTER(_joined,NOT ISBLANK([Y]))
RETURN SELECTCOLUMNS(_valid,'''
    columns = ','.join('"' + key + '",[' + key + ']' for key in keys) + ',"Amount",[Y]'
    for window in (6, 12, 24):
        columns += ',"Fit' + str(window) + '''",VAR _id=[SourceRevisionID]
 VAR _cut=LOOKUPVALUE('fm_native_files'[IMSActualsThrough],'fm_native_files'[SourceRevisionID],_id)
 RETURN [Y]*(DATEDIFF(_cut,[Month],MONTH)+''' + str((window - 1) / 2) + ')'
    return prefix + columns + ')'


def patch(database):
    fixed = star.patch(database)
    tables = {t['name']: t for t in fixed['model']['tables']}
    source = tables[prepared.TABLE]['partitions'][0]['source']
    expression = 'VAR _base=(' + source['expression'] + ')\nRETURN ADDCOLUMNS(_base,'
    terms = []
    for window in (6, 12, 24):
        terms.append('"Fit' + str(window) + '''",VAR _id=[SourceRevisionID]
 VAR _cut=IF([Metric]="ef",LOOKUPVALUE('fm_native_files'[ExFactoryActualsThrough],'fm_native_files'[SourceRevisionID],_id),
 LOOKUPVALUE('fm_native_files'[IMSActualsThrough],'fm_native_files'[SourceRevisionID],_id))
 RETURN [Amount]*(DATEDIFF(_cut,[Month],MONTH)+''' + str((window - 1) / 2) + ')')
        tables[prepared.TABLE]['columns'].append({'name': 'Fit' + str(window), 'dataType': 'double',
            'type': 'calculatedTableColumn', 'sourceColumn': '[Fit' + str(window) + ']', 'summarizeBy': 'none'})
    source['expression'] = expression + ','.join(terms) + ')'
    fields = [('SourceRevisionID', 'string'), ('Sector', 'string'), ('Month', 'dateTime'),
              ('Display', 'string'), (star.KEY, 'string'), ('Amount', 'double')]
    fields += [('Fit' + str(w), 'double') for w in (6, 12, 24)]
    fixed['model']['tables'].append({'name': SHARE, 'isHidden': True,
        'columns': [{'name': n, 'dataType': t, 'type': 'calculatedTableColumn', 'sourceColumn': '[' + n + ']', 'summarizeBy': 'none'} for n, t in fields],
        'partitions': [{'name': SHARE, 'mode': 'import', 'source': {'type': 'calculated', 'expression': share_source()}}]})
    fixed['model']['relationships'].append({'name': 'Perf-Sector-Share', 'fromTable': SHARE, 'fromColumn': star.KEY,
        'toTable': star.DIM, 'toColumn': star.KEY})
    measures = prepared.adapter.planning.measures(fixed)
    target = tables['fm_native_measures']['measures']
    for name in ('Mean', 'Slope'):
        group = deepcopy(measures['P Fast Fit ' + name])
        group['name'] = 'P Group Fit ' + name
        target.append(group)
    original = prepared.adapter.planning.measures(database)
    context = star.source_context(prepared.adapter.selection.OLD.expression_text(original['N Monthly Numerator']['expression']))
    measures['P Fast Fit Mean']['expression'] = fit(context)
    measures['P Fast Fit Slope']['expression'] = fit(context, True)
    value = measures['P Fast Benchmark']['expression']
    start = value.index('VAR _dFuture=')
    end = value.index('RETURN IF(_sourceOK', start)
    value = value[:start] + '''VAR _futureD=CALCULATE(SUM('fm_perf_monthly'[Amount]),''' + star.filt('_futureMonths', '"market"') + ''')
VAR _futureDX=''' + weight_sum(prepared.TABLE, '_futureMonths', '"market"') + '''
VAR _future=IF(_row="share",_mean*_futureD+_slope*_futureDX,
 SUMX(_futureMonths,_mean+_slope*(DATEDIFF(_cut,[Date],MONTH)+_w-(_w+1)/2)))
''' + value[end:]
    measures['P Fast Benchmark']['expression'] = value
    return fixed
