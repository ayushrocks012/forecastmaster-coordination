"""Evaluate each cell's Plan and Benchmark once, preserving R02 admission.

No serving tables or relationships. Eager output selection is retained to
avoid the previously observed mixed-period strict-plan engine failure.
"""
from copy import deepcopy

import prepared

PAIR = '''VAR _plan=[N Plan]
VAR _benchmark=CALCULATE([N Benchmark],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))
VAR _pair=NOT ISBLANK(_plan)&&NOT ISBLANK(_benchmark)
VAR _variance=IF(_pair,_plan-_benchmark)
VAR _percent=IF(_pair,DIVIDE(_plan-_benchmark,ABS(_benchmark)))'''

SUMMARY = '''IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1,
VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])
RETURN IF(NOT _leaf,
 IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N Period Available]=1,[N Plan]),
VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _w=SELECTEDVALUE('fm_native_columns'[Window])
VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])
VAR _actualOnly=[N Actual Only]=1
''' + PAIR + '''
RETURN IF([N Period Available]=1&&_allowed,
 IF.EAGER(_key="plan",_plan,IF.EAGER(_actualOnly,BLANK(),
 IF.EAGER(RIGHT(_key,3)="abs",_variance,_percent)))))))'''

HEADLINE = '''IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1&&[N Period Available]=1,
VAR _key=SELECTEDVALUE('fm_native_headline'[Key])
VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)
VAR _actualOnly=[N Actual Only]=1
''' + PAIR + '''
RETURN IF.EAGER(_key="plan",_plan,IF.EAGER(_key="variance",IF.EAGER(NOT _actualOnly,_variance),
 IF.EAGER(_key="pct",IF.EAGER(NOT _actualOnly,_percent),BLANK())))))'''


def patch(database):
    fixed = deepcopy(database)
    old = prepared.adapter.planning.measures(database)
    current = prepared.adapter.planning.measures(fixed)
    expected = prepared.adapter.planning.measures(prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0])
    for name, value in [('N Summary Cell', SUMMARY), ('N Headline Cell', HEADLINE)]:
        if prepared.adapter.selection.OLD.expression_hash(old[name]['expression']) != prepared.adapter.selection.OLD.expression_hash(expected[name]['expression']):
            raise ValueError('Unknown R02 cell: ' + name)
        current[name]['expression'] = value
    restored = deepcopy(fixed)
    for name in ('N Summary Cell', 'N Headline Cell'):
        prepared.adapter.planning.measures(restored)[name]['expression'] = deepcopy(old[name]['expression'])
    if restored != database:
        raise AssertionError('Unrelated model change')
    return fixed
