"""Guarded summary display formats that also survive native CSV export.

Both cell measures stay numeric and unscaled. Only their dynamic format
definitions change; every other model property is compared after restoration.
Literal sections prevent CSV treating VBA scale commas as grouping commas.
Three explicit sections prevent an additional implicit negative sign.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_format_baseline', HERE / 'model.py')
baseline = importlib.util.module_from_spec(spec)
spec.loader.exec_module(baseline)
NAMES = ('N Headline Cell', 'N Summary Cell')


def measures(database):
    return {m['name']: m for t in database['model']['tables'] if t['name'] == 'fm_native_measures'
            for m in t.get('measures', [])}


def replacements():
    old = measures(baseline.original_database())
    result = {}
    for name in NAMES:
        expression = baseline.OLD.expression_text(old[name]['formatStringDefinition']['expression'])
        prefix, separator, _ = expression.partition('VAR _value=ABS(SELECTEDMEASURE())')
        if not separator or expression.count(separator) != 1:
            raise ValueError('Unknown original display definition: ' + name)
        result[name] = prefix + '''VAR _value=SELECTEDMEASURE()
VAR _abs=ABS(_value)
VAR _display=IF(_value<0,"−","")&_symbol&SWITCH(TRUE(),
 _abs>=1000000,FORMAT(_abs/1000000,"#,0.00","en-GB")&"m",
 _abs>=1000,FORMAT(_abs/1000,"#,0.0","en-GB")&"k",FORMAT(_abs,"#,0","en-GB"))
VAR _literal=UNICHAR(34)&_display&UNICHAR(34)
RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",_literal&";"&_literal&";"&_literal)'''
    return result


def patch_database(database):
    expected = measures(baseline.original_database())
    fixed = deepcopy(database)
    actual = measures(fixed)
    edits = replacements()
    for name, expression in edits.items():
        incoming = actual[name]['formatStringDefinition']['expression']
        original = expected[name]['formatStringDefinition']['expression']
        if baseline.OLD.expression_hash(incoming) != baseline.OLD.expression_hash(original):
            raise ValueError('Unknown original display definition: ' + name)
        actual[name]['formatStringDefinition']['expression'] = expression
    restored = deepcopy(fixed)
    old, restore = measures(database), measures(restored)
    for name in edits:
        restore[name]['formatStringDefinition'] = deepcopy(old[name]['formatStringDefinition'])
    if restored != database:
        raise AssertionError('A property outside the two display definitions changed')
    return fixed, sorted(edits)
