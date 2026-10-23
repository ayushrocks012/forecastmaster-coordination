"""Native month controls and bounded display guards; preserve amount arithmetic."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r175_model", HERE.parent / "report-native-only-r17.5/model.py")
OLD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OLD)
expression_hash = OLD.expression_hash


def baseline():
    result = OLD.baseline()
    for name, expression in OLD.replacements().items():
        result[name]["expression"] = expression
    return result


def replacements():
    before = baseline()
    start = "MIN('fm_native_start_month'[Month])"
    end = "MAX('fm_native_end_month'[Month])"
    valid = "HASONEVALUE('fm_native_metric'[RowID])"
    chart = before["N Chart Monthly"]["expression"]
    chart = chart.replace("MIN('fm_review_months'[Month])", start).replace("MAX('fm_review_months'[Month])", end)
    chart = chart.replace("RETURN IF(_mode&&", 'RETURN IF((_type<>"demand"||' + valid + ")&&" + start + "<=" + end + "&&_mode&&")
    assert chart != before["N Chart Monthly"]["expression"]
    summary = before["N Summary Cell"]["expression"]
    # Flatten only the comparison header. Existing leaf arithmetic is retained.
    summary = summary.replace("'fm_native_columns'[Comparison]", "'fm_native_columns'[ColumnLabel]")
    return {
        "N Chart Monthly": chart,
        "N Period Available": "VAR _start=" + start + " VAR _end=" + end + "\n"
            "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
            "RETURN IF(NOT ISBLANK(_start)&&NOT ISBLANK(_end)&&_start<=_end"
            "&&NOT ISBLANK(_y)&&_y>=YEAR(_start)&&_y<=YEAR(_end),1)",
        "N Headline Cell": "IF(" + valid + ",IF([N Source OK]=1&&[N Period Available]=1,\n" + before["N Headline Cell"]["expression"] + "))",
        "N Summary Cell": "IF(" + valid + ",IF([N Source OK]=1,\n" + summary + "))",
        "N Measure Caption": "IF(" + valid + ",\n" + before["N Measure Caption"]["expression"]
            + ',"Choose a measure in the selected section")',
    }


def month_tables():
    # Uses the existing monthly dictionary; never generates daily buckets or
    # reads source amount columns. Each bound is disconnected and independent.
    expression = '''DISTINCT(SELECTCOLUMNS('fm_review_months',
 "Month",DATE(YEAR('fm_review_months'[Month]),MONTH('fm_review_months'[Month]),1),
 "MonthLabel",FORMAT('fm_review_months'[Month],"mmm yyyy","en-GB")))'''
    return [{"name": "fm_native_" + side + "_month",
             "description": "R17.6 independent " + side + " month bound; monthly metadata only.",
             "columns": [{"name": "Month", "dataType": "dateTime", "type": "calculatedTableColumn",
                          "sourceColumn": "[Month]", "summarizeBy": "none", "formatString": "mmm yyyy"},
                         {"name": "MonthLabel", "dataType": "string", "type": "calculatedTableColumn",
                          "sourceColumn": "[MonthLabel]", "summarizeBy": "none", "sortByColumn": "Month"}],
             "partitions": [{"name": "fm_native_" + side + "_month", "mode": "import",
                             "source": {"type": "calculated", "expression": expression}}]}
            for side in ("start", "end")]


def original_columns():
    # The SAMPLE carries only fabricated amounts. This static helper is the
    # same seven-row definition used by the OneLake installer.
    with ZipFile(HERE.parent / "report-native-only-r17.5/candidate/ForecastMaster Native Only R17.5 SAMPLE.zip") as archive:
        db = json.loads(archive.read(next(p for p in archive.namelist() if p.endswith("/model.bim"))))
    return next(t for t in db["model"]["tables"] if t["name"] == "fm_native_columns")


def column_patch():
    old = original_columns()
    source = old["partitions"][0]["source"]["expression"]
    if isinstance(source, list):
        source = "\n".join(source)
    expression = 'ADDCOLUMNS(\n(' + source + '''),
 "ColumnLabel",SWITCH([ColumnKey],"plan","Plan",
 "6:abs","6M variance","6:pct","6M variance %",
 "12:abs","12M variance","12:pct","12M variance %",
 "24:abs","24M variance","24:pct","24M variance %"))'''
    column = {"name": "ColumnLabel", "dataType": "string", "type": "calculatedTableColumn",
              "sourceColumn": "[ColumnLabel]", "summarizeBy": "none", "sortByColumn": "Sort"}
    return source, expression, column


def fingerprints():
    return {name: {key: expression_hash(value if key == "expression" else value["expression"])
                   for key, value in measure.items() if key in {"expression", "formatStringDefinition"}}
            for name, measure in baseline().items()}


def patch_database(database):
    fixed = deepcopy(database)
    tables = {t["name"]: t for t in fixed["model"]["tables"]}
    expected, edits = fingerprints(), replacements()
    measures = tables.get("fm_native_measures", {}).get("measures", [])
    current = {m["name"]: m for m in measures}
    if set(current) != set(expected) or len(current) != len(measures):
        raise ValueError("Unexpected native measure inventory; no write.")
    changed = []
    for name, hashes in expected.items():
        allowed = {hashes["expression"]}
        if name in edits:
            allowed.add(expression_hash(edits[name]))
        if expression_hash(current[name]["expression"]) not in allowed:
            raise ValueError("Unknown native expression; require verified R17.5 first.")
        fmt = current[name].get("formatStringDefinition")
        if bool(fmt) != ("formatStringDefinition" in hashes) or (
                fmt and expression_hash(fmt["expression"]) != hashes["formatStringDefinition"]):
            raise ValueError("Unexpected native format; no write.")
        if name in edits and expression_hash(current[name]["expression"]) != expression_hash(edits[name]):
            current[name]["expression"] = edits[name]
            changed.append(name)
    for helper in month_tables():
        if helper["name"] in tables:
            actual = deepcopy(tables[helper["name"]])
            raw = actual["partitions"][0]["source"]["expression"]
            if isinstance(raw, list):
                actual["partitions"][0]["source"]["expression"] = "\n".join(raw)
            if actual != helper:
                raise ValueError("Unknown month helper; no write.")
        else:
            fixed["model"]["tables"].append(deepcopy(helper))
            changed.append(helper["name"])
    old_source, new_source, new_column = column_patch()
    columns = tables.get("fm_native_columns")
    if not columns or len(columns.get("partitions", [])) != 1:
        raise ValueError("Unexpected comparison helper; no write.")
    partition = columns["partitions"][0]
    source = partition.get("source", {})
    if source.get("type") != "calculated" or expression_hash(source.get("expression", "")) not in {
            expression_hash(old_source), expression_hash(new_source)}:
        raise ValueError("Unknown comparison helper expression; no write.")
    label = [c for c in columns.get("columns", []) if c["name"] == "ColumnLabel"]
    if label and (len(label) != 1 or label[0] != new_column):
        raise ValueError("Unknown comparison label; no write.")
    if expression_hash(source["expression"]) != expression_hash(new_source):
        source["expression"] = new_source
        changed.append("fm_native_columns.expression")
    if not label:
        columns["columns"].append(deepcopy(new_column))
        changed.append("fm_native_columns.ColumnLabel")
    # Prove every non-allowlisted object stays byte-for-byte equivalent as JSON.
    restored = deepcopy(fixed)
    original = {t["name"]: t for t in database["model"]["tables"]}
    allowed_tables = {"fm_native_measures", "fm_native_columns"} | {t["name"] for t in month_tables()}
    restored["model"]["tables"] = [deepcopy(original[t["name"]]) if t["name"] in allowed_tables else t
        for t in restored["model"]["tables"] if t["name"] in original]
    if restored != database:
        raise AssertionError("Unrelated model change; no write.")
    return fixed, changed
