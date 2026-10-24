"""Pure matching R02 adapter; no Fabric client, processing or publication.

Preserve every incoming metadata property. The installed R01 guard admits only
its known expressions/formats, then the four qualified cell-evaluation edits
are applied using canonical DAX text, including service-returned line arrays.
Two explicitly guarded dynamic display definitions also change; numeric values
and every other property remain intact.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('r178_adapter_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


selection, planning, formats = [load(name) for name in ('model', 'matrix_planning', 'display_formats')]


def patch_database(database):
    fixed, selection_edits = selection.patch_database(database)
    expected = planning.measures(selection.patch_database(selection.original_database())[0])
    actual = planning.measures(fixed)
    cell_edits = planning.replacements()
    for name, expression in cell_edits.items():
        if selection.OLD.expression_hash(actual[name]['expression']) != selection.OLD.expression_hash(expected[name]['expression']):
            raise ValueError('Unknown R02 cell expression: ' + name)
        actual[name]['expression'] = expression
    fixed, format_edits = formats.patch_database(fixed)
    restored = deepcopy(fixed)
    old, restore = planning.measures(database), planning.measures(restored)
    edits = sorted(set(selection_edits) | set(cell_edits))
    for name in edits:
        restore[name]['expression'] = deepcopy(old[name]['expression'])
    for name in format_edits:
        restore[name]['formatStringDefinition'] = deepcopy(old[name]['formatStringDefinition'])
    if restored != database:
        raise AssertionError('Unrelated model property changed')
    return fixed, edits
