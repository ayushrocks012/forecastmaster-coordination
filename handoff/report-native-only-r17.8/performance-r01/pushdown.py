"""Replace source-membership callbacks by equivalent storage filters only.

No tables, relationships, formats, amount/period/regression arithmetic or file
admission policy change. The R02 Selected-files constant is explicitly guarded.
"""
from copy import deepcopy

import prepared


def parts():
    base = prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]
    value = prepared.adapter.selection.OLD.expression_text(prepared.adapter.planning.measures(base)['N Monthly Numerator']['expression'])
    start = value.index('VAR _poolAvailable =')
    driver = value.index('VAR _driver =', start)
    pool = value.index('VAR _pool =', driver)
    files = value.index('VAR _files =', pool)
    ids = value.index('VAR _ids =', files)
    return value[start:driver], value[pool:files], value[files:ids]


def filter_table(driver=False, scenario=False):
    filters = ["REMOVEFILTERS('fm_native_files')",
        "TREATAS(_country,'fm_native_files'[Country])",
        "TREATAS(_cycles,'fm_native_files'[DemandCycle])",
        "TREATAS(_chosen,'fm_native_files'[SourceRevisionID])"]
    if driver:
        filters.append("TREATAS(_driver,'fm_native_files'[GrowthDriver])")
    if scenario:
        filters.append("FILTER(ALL('fm_native_files'[Scenario]),ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario)")
    return "CALCULATETABLE('fm_native_files'," + ','.join(filters) + ')\n'


def patch(database):
    fixed = deepcopy(database)
    old = parts()
    replacements = ['VAR _poolAvailable = ' + filter_table(),
                    'VAR _pool = ' + filter_table(True),
                    'VAR _files = ' + filter_table(True, True)]
    changed = []
    for measure in prepared.adapter.planning.measures(fixed).values():
        body = prepared.adapter.selection.OLD.expression_text(measure['expression'])
        if 'VAR _poolAvailable =' not in body:
            continue
        if 'VAR _custom = "Selected files" = "Selected files"' not in body or any(body.count(part) != 1 for part in old):
            raise ValueError('Unknown source policy or membership shape: ' + measure['name'])
        for before, after in zip(old, replacements):
            body = body.replace(before, after)
        measure['expression'] = body
        changed.append(measure['name'])
    if not changed:
        raise ValueError('No matching source callback kernels')
    restored = deepcopy(fixed)
    original = prepared.adapter.planning.measures(database)
    for name in changed:
        prepared.adapter.planning.measures(restored)[name]['expression'] = deepcopy(original[name]['expression'])
    if restored != database:
        raise AssertionError('Unrelated model change')
    return fixed
