"""Guarded eager cell evaluation for mixed actual/future matrix periods.

The numerical measures and formatting are unchanged. IF.EAGER keeps each
branch's returned value/blank rule, but changes the engine execution plan.
Qualify the whole generated matrix query, not just isolated scalar cells.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_planning_baseline', HERE / 'model.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)

HEADLINE = '''IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1&&[N Period Available]=1,
 VAR _key=SELECTEDVALUE('fm_native_headline'[Key])
 RETURN IF.EAGER(_key="plan",[N Plan],IF.EAGER(_key="variance",[N Headline Variance],IF.EAGER(_key="pct",[N Headline Variance %],BLANK())))))'''

SUMMARY = '''IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1,
VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])
RETURN IF(NOT _leaf,
 IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N Period Available]=1,[N Plan]),
VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _w=SELECTEDVALUE('fm_native_columns'[Window])
VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])
VAR _actualOnly=[N Actual Only]=1
RETURN IF([N Period Available]=1&&_allowed,
 IF.EAGER(_key="plan",[N Plan],IF.EAGER(_actualOnly,BLANK(),
 IF.EAGER(RIGHT(_key,3)="abs",
 CALCULATE([N Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),
 CALCULATE([N Variance %],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))))))))'''


def measures(db):
    return {m['name']: m for t in db['model']['tables'] if t['name'] == 'fm_native_measures'
            for m in t.get('measures', [])}


def replacements():
    before = measures(baseline.patch_database(baseline.original_database())[0])
    changed = {'N Headline Cell': HEADLINE, 'N Summary Cell': SUMMARY}
    for name in ('N Headline Variance', 'N Headline Variance %'):
        body = baseline.OLD.expression_text(before[name]['expression'])
        if body.count('RETURN IF(NOT _actual,') != 1:
            raise ValueError('Unknown actual-only admission expression')
        changed[name] = body.replace('RETURN IF(NOT _actual,', 'RETURN IF.EAGER(NOT _actual,')
    return changed


def patch_database(database):
    expected = measures(baseline.patch_database(baseline.original_database())[0])
    fixed = deepcopy(database)
    actual = measures(fixed)
    changes = replacements()
    for name in changes:
        if actual[name] != expected[name]:
            raise ValueError('Require exact R02 cell baseline: ' + name)
        actual[name]['expression'] = changes[name]
    restored = deepcopy(fixed)
    old, restore = measures(database), measures(restored)
    for name in changes:
        restore[name]['expression'] = deepcopy(old[name]['expression'])
    if restored != database:
        raise AssertionError('Unrelated model metadata changed')
    return fixed, sorted(changes)
