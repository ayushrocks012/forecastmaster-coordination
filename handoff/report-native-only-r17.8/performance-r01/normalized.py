"""Normalize irrelevant presentation filters around exact R03 calculations.

No numeric expression is rewritten. Private aliases retain the original DAX;
public wrappers remove only filters that those expressions do not read. The
source guard consumes driver membership, not sector membership, so an explicit
driver set preserves its input while allowing reuse across sector rows.
"""
from copy import deepcopy

import prepared
import strictcells


def patch(database):
    fixed=deepcopy(database)
    before=prepared.adapter.planning.measures(database)
    after=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    names=('N Source OK','N Cutoff','N Fit Cutoff','N Plan','N Benchmark','N Fit Mean','N Fit Slope')
    if any(n.startswith('P Norm ') for n in before):
        raise ValueError('Normalization already installed')
    if any(text(before[n]['expression'])!=text(expected[n]['expression']) for n in names):
        raise ValueError('Unknown R03 expression')
    target=next(t for t in fixed['model']['tables'] if t['name']=='fm_native_measures')['measures']
    presentation=['fm_native_columns','fm_native_headline','fm_native_chart_trend','fm_native_view','fm_native_groups']
    for name in names:
        alias='P Norm '+name[2:]
        original=deepcopy(before[name]);original.update(name=alias,isHidden=True)
        target.append(original)
        remove=list(presentation)
        prefix=''
        if name in {'N Source OK','N Cutoff','N Fit Cutoff','N Fit Mean','N Fit Slope'}:
            remove+=['fm_native_periods','fm_review_axis']
        if name in {'N Source OK','N Cutoff','N Fit Cutoff','N Plan'}:
            remove+=['fm_native_trend']
        if name in {'N Source OK','N Cutoff','N Fit Cutoff'}:
            prefix="VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\n"
            remove+=['fm_native_scope']
        if name=='N Source OK':
            remove+=['fm_native_catalog','fm_native_metric','fm_native_currency','fm_native_display']
        args=["REMOVEFILTERS('"+t+"')" for t in remove]
        if prefix:
            args.append("TREATAS(_drivers,'fm_native_scope'[GrowthDriver])")
        after[name]['expression']=prefix+('RETURN ' if prefix else '')+'CALCULATE(['+alias+'],'+','.join(args)+')'
    return fixed
