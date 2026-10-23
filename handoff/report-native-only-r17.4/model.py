"""Repair native formatting and the undefined collapsed-column summary context.

The original plan/trend/ratio/source/missing arithmetic is byte-preserved.
Only fm_native_measures format metadata and one summary display guard change.
"""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r174_baseline", HERE.parent / "report-native-r17.2/model.py")
BASELINE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BASELINE)


def expression_hash(value):
    return BASELINE.expression_hash(value)


def repairs():
    old = BASELINE.revised_measures()
    revised = {}
    for name, measure in old.items():
        if "formatStringDefinition" in measure:
            before = measure["formatStringDefinition"]["expression"]
            # Power BI scaling separators belong BEFORE the decimal point.
            after = before.replace('#,0.00,,', '#,0,,.00').replace('#,0.0,', '#,0,.0')
            assert before != after, name
            revised.setdefault(name, {})["formatStringDefinition"] = {"expression": after}
    revised.setdefault("N Summary Cell", {})["expression"] = '''VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])
RETURN IF(NOT _leaf,
 IF(NOT ISINSCOPE('fm_native_columns'[Comparison])&&[N Period Available]=1,[N Plan]),
''' + old["N Summary Cell"]["expression"] + ")"
    return old, revised


def patch_database(database):
    before = deepcopy(database)
    after = deepcopy(database)
    tables = [t for t in after["model"]["tables"] if t["name"] == "fm_native_measures"]
    if len(tables) != 1:
        raise ValueError("Expected one existing native measure table; no write.")
    expected, replacements = repairs()
    current = {m["name"]: m for m in tables[0]["measures"]}
    if set(current) != set(expected):
        raise ValueError("Unknown native measure inventory; inspect before changing TEST.")
    changed = []
    for name, original in expected.items():
        measure = current[name]
        edits = replacements.get(name, {})
        allowed = {expression_hash(original["expression"]), expression_hash(edits.get("expression", original["expression"]))}
        if expression_hash(measure["expression"]) not in allowed:
            raise ValueError("Unknown native expression; no write: " + name)
        old_format = original.get("formatStringDefinition")
        observed = measure.get("formatStringDefinition")
        if old_format:
            if not observed or expression_hash(observed["expression"]) not in {
                expression_hash(old_format["expression"]), expression_hash(edits.get("formatStringDefinition", old_format)["expression"])}:
                raise ValueError("Unknown native format; no write: " + name)
        elif observed:
            raise ValueError("Unexpected native dynamic format; no write: " + name)
        touched = False
        for key, value in edits.items():
            # Preserve annotations/metadata on format definitions as well.
            if key == "formatStringDefinition":
                if expression_hash(measure[key]["expression"]) != expression_hash(value["expression"]):
                    measure[key]["expression"] = value["expression"]
                    touched = True
            elif expression_hash(measure[key]) != expression_hash(value):
                measure[key] = value
                touched = True
        if touched:
            changed.append(name)
    # Exact preservation proof, allowing only declared format/summary properties.
    restored = deepcopy(after)
    restore_table = next(t for t in restored["model"]["tables"] if t["name"] == "fm_native_measures")
    original_table = next(t for t in before["model"]["tables"] if t["name"] == "fm_native_measures")
    original_by = {m["name"]: m for m in original_table["measures"]}
    for m in restore_table["measures"]:
        for key in replacements.get(m["name"], {}):
            m[key] = deepcopy(original_by[m["name"]][key])
    if restored != before or database != before:
        raise AssertionError("Unintended model change.")
    return after, changed
