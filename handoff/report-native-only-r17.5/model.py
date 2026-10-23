"""Two chart-presentation fixes; retain all source and business arithmetic."""
from copy import deepcopy
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r174_cell_frozen", HERE.parent / "report-native-only-r17.4/UPDATE EXISTING TEST TO R17.4.py")
R174 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(R174)
expression_hash = R174.expression_hash


def baseline():
    measures = deepcopy(R174.EXPECTED)
    for name, edits in R174.REPLACEMENTS.items():
        for key, value in edits.items():
            if key == "formatStringDefinition":
                measures[name][key]["expression"] = value["expression"]
            else:
                measures[name][key] = value
    return measures


def replacements():
    old = baseline()
    chart = old["N Chart Monthly"]["expression"]
    assert chart.count("_kind=1&&_month>_cut") == 1
    assert chart.count("_kind IN VALUES('fm_native_trend'[Window])") == 1
    chart = chart.replace("_kind=1&&_month>_cut", '_kind=1&&(_month>_cut||_type="demand"&&_month=_cut)')
    chart = chart.replace("_kind IN VALUES('fm_native_trend'[Window])",
                          "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)")
    membership = '''CONTAINS(VALUES('fm_native_lines'[ViewType]),'fm_native_lines'[ViewType],SELECTEDVALUE('fm_native_view'[View],"Total"))'''
    assert chart.count("SELECTEDVALUE('fm_native_lines'[ViewType]) IN VALUES('fm_native_view'[View])") == 1
    chart = chart.replace("SELECTEDVALUE('fm_native_lines'[ViewType]) IN VALUES('fm_native_view'[View])", membership)
    visible = old["N Line Visible"]["expression"]
    assert visible.count("_kind IN VALUES('fm_native_trend'[Window])") == 1
    visible = visible.replace("_kind IN VALUES('fm_native_trend'[Window])",
                              "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)")
    assert visible.count("_view IN VALUES('fm_native_view'[View])") == 1
    visible = visible.replace("_view IN VALUES('fm_native_view'[View])", membership)
    return {"N Chart Monthly": chart, "N Line Visible": visible}


def fingerprints():
    return {name: {key: expression_hash(value if key == "expression" else value["expression"])
                   for key, value in measure.items() if key in {"expression","formatStringDefinition"}}
            for name, measure in baseline().items()}


def patch_database(database):
    fixed = deepcopy(database)
    tables = [t for t in fixed["model"]["tables"] if t["name"] == "fm_native_measures"]
    if len(tables) != 1:
        raise ValueError("Expected existing native measures; no write.")
    current = {m["name"]: m for m in tables[0]["measures"]}
    expected, edits = fingerprints(), replacements()
    if set(current) != set(expected) or len(current) != len(tables[0]["measures"]):
        raise ValueError("Unexpected native measure inventory; no write.")
    changed = []
    for name, hashes in expected.items():
        allowed = {hashes["expression"]}
        if name in edits:
            allowed.add(expression_hash(edits[name]))
        if expression_hash(current[name]["expression"]) not in allowed:
            raise ValueError("Unknown native expression; no write.")
        fmt = current[name].get("formatStringDefinition")
        if bool(fmt) != ("formatStringDefinition" in hashes):
            raise ValueError("Unexpected format inventory; no write.")
        if fmt and expression_hash(fmt["expression"]) != hashes["formatStringDefinition"]:
            raise ValueError("R17.4 format repair not confirmed; no write.")
        if name in edits and expression_hash(current[name]["expression"]) != expression_hash(edits[name]):
            current[name]["expression"] = edits[name]
            changed.append(name)
    restored = deepcopy(fixed)
    restore_table = next(t for t in restored["model"]["tables"] if t["name"] == "fm_native_measures")
    original = next(t for t in database["model"]["tables"] if t["name"] == "fm_native_measures")
    old_by_name = {m["name"]:m for m in original["measures"]}
    for measure in restore_table["measures"]:
        if measure["name"] in edits:
            measure["expression"] = deepcopy(old_by_name[measure["name"]]["expression"])
    if restored != database:
        raise AssertionError("Unrelated metadata mutation; no write.")
    return fixed, changed
