"""Remove wide file-row context transitions from the original monthly kernels.

Keep every original source/period/FX/amount rule. The per-file fact read already
filters SourceRevisionID explicitly. Its iteration therefore needs three scalar
identities, not the entire native file record with inherited column lineage.
Preserve blank identities while breaking that redundant row lineage.
"""
from copy import deepcopy

import prepared
import strictcells


def patch(database):
    fixed=deepcopy(database);old=prepared.adapter.planning.measures(database)
    current=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    marker='''VAR _members=GENERATE(_files,
 VAR _id='fm_native_files'[SourceRevisionID]
 VAR _gd='fm_native_files'[GrowthDriver]
 VAR _cc='fm_native_files'[Country]'''
    replacement='''VAR _fileScalars=SELECTCOLUMNS(_files,
 "__ID",IF(ISBLANK('fm_native_files'[SourceRevisionID]),BLANK(),'fm_native_files'[SourceRevisionID]&""),
 "__GD",IF(ISBLANK('fm_native_files'[GrowthDriver]),BLANK(),'fm_native_files'[GrowthDriver]&""),
 "__CC",IF(ISBLANK('fm_native_files'[Country]),BLANK(),'fm_native_files'[Country]&""))
VAR _members=GENERATE(_fileScalars,
 VAR _id=[__ID]
 VAR _gd=[__GD]
 VAR _cc=[__CC]'''
    for name in ('N Monthly Numerator','N Monthly Denominator'):
        expression=text(old[name]['expression'])
        if expression!=text(expected[name]['expression']) or expression.count(marker)!=1:
            raise ValueError('Unknown qualified monthly kernel')
        current[name]['expression']=expression.replace(marker,replacement)
    return fixed
