"""Reuse regression coefficients, and add native file/series metadata on TEST."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("r176_model", HERE.parent / "report-native-only-r17.6/model.py")
OLD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(OLD)
expression_hash = OLD.expression_hash


def baseline():
    result = OLD.baseline()
    for name, expression in OLD.replacements().items():
        result[name]["expression"] = expression
    return result


TRAIN = '''VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])
VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN
 CALCULATE([N Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))
VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=AVERAGEX(_train,[X]) VAR _my=AVERAGEX(_train,[Y])
'''


def fit_measures():
    return {
        "N Fit Mean": TRAIN + "RETURN IF(NOT ISBLANK(_cut)&&_valid,_my)",
        "N Fit Slope": TRAIN + '''RETURN IF(NOT ISBLANK(_cut)&&_valid,
 DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2))))''',
    }


def performance_edits():
    old = baseline()
    trend = '''VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _m=SELECTEDVALUE('fm_review_axis'[Month])
RETURN IF(NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,[N Monthly],
 VAR _mean=CALCULATE([N Fit Mean],REMOVEFILTERS('fm_review_axis'))
 VAR _slope=CALCULATE([N Fit Slope],REMOVEFILTERS('fm_review_axis'))
 RETURN IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),
 _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))))'''
    # Identical named-period/month masks, observed numerator, weighted future
    # denominator and missing-month rules. Fit each scope/window outside the
    # forecast-month iterator instead of re-training in every projected month.
    benchmark = old["N Benchmark"]["expression"]
    head = benchmark[:benchmark.index("VAR _values=")]
    benchmark = head + '''VAR _ratio=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")="share"
VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _mean=IF(_end>_cut,CALCULATE([N Fit Mean],REMOVEFILTERS('fm_review_axis')))
VAR _slope=IF(_end>_cut,CALCULATE([N Fit Slope],REMOVEFILTERS('fm_review_axis')))
VAR _base=ADDCOLUMNS(_months,"D",VAR _m=[Date] RETURN IF(_ratio,
 CALCULATE([N Monthly Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))
VAR _values=ADDCOLUMNS(_base,"N",VAR _m=[Date]
 VAR _forecast=IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),
 _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))
 RETURN IF(_m>_cut,IF(_ratio,IF(NOT ISBLANK(_forecast)&&NOT ISBLANK([D]),_forecast*[D]),_forecast),
 CALCULATE([N Monthly Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))
VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count
RETURN IF(NOT ISBLANK([N Fit Cutoff])&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,
 IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT ISBLANK([D])))=_count,
 DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))'''
    plan = old["N Plan"]["expression"]
    ratio = '''VAR _ratio=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")="share"'''
    assert plan.count(ratio) == 1
    plan = plan.replace(ratio, "")
    plan = plan.replace("VAR _values=", ratio + "\nVAR _values=", 1)
    target = '''"D",VAR _m=[Date] RETURN CALCULATE([N Monthly Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))'''
    # Preserve the source's spacing verbatim outside this denominator branch.
    spaced = '''"D",VAR _m=[Date] RETURN CALCULATE([N Monthly Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))'''
    assert spaced in plan
    plan = plan.replace(target, '''"D",VAR _m=[Date] RETURN IF(_ratio,CALCULATE([N Monthly Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))''')
    result = {"N Trend Monthly": trend, "N Benchmark": benchmark, "N Plan": plan,
            "N Variance %": '''VAR _p=[N Plan] VAR _b=[N Benchmark]
RETURN IF(NOT ISBLANK(_p)&&NOT ISBLANK(_b),DIVIDE(_p-_b,ABS(_b)))'''}
    for name in ("N Monthly Numerator", "N Monthly Denominator"):
        body = old[name]["expression"]
        target = "VAR _memberFacts=CALCULATETABLE('fm_review_facts',REMOVEFILTERS('fm_review_facts'),"
        assert body.count(target) == 1
        body = body.replace(target, '''VAR _memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',
  "Sector",'fm_review_facts'[Sector],"Amount",'fm_review_facts'[Amount],"MissingCells",'fm_review_facts'[MissingCells]),REMOVEFILTERS('fm_review_facts'),''')
        body = body.replace("GROUPBY(_memberFacts,'fm_review_facts'[Sector]", "GROUPBY(_memberFacts,[Sector]")
        body = body.replace("SUMX(CURRENTGROUP(),'fm_review_facts'[Amount])", "SUMX(CURRENTGROUP(),[Amount])")
        body = body.replace("INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount]))", "INT([MissingCells]<>0||ISBLANK([Amount]))")
        result[name] = body
    return result


def replacements():
    result = {}
    # The picker filters native metadata, leaving original tables untouched.
    # Intersect its IDs with the original country/cycle/file context. Automatic
    # ADS still ignores manual choices, as in the existing _custom branch.
    before = baseline()
    old_chosen = "VAR _chosen = VALUES('fm_review_files'[SourceRevisionID])"
    new_chosen = "VAR _chosen = INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))"
    old_explicit = "ISFILTERED('fm_review_files'[FileLabel])"
    new_explicit = "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel]))"
    for name, measure in before.items():
        body = measure["expression"]
        if old_chosen in body:
            assert body.count(old_chosen) == 1 and body.count(old_explicit) == 1
            result[name] = body.replace(old_chosen, new_chosen).replace(old_explicit, new_explicit)
    result.update(performance_edits())
    for name, body in list(result.items()):
        if old_chosen in body:
            result[name] = body.replace(old_chosen, new_chosen).replace(old_explicit, new_explicit)
    caption = result["N Source Caption"]
    result["N Source Caption"] = '''IF(SELECTEDVALUE('fm_native_file_mode'[Mode],"Automatic ADS")="Selected files",
 IF(ISFILTERED('fm_native_files'[FileChoiceLabel]),
 "Selected files · "&FORMAT(COUNTROWS(INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),
 VALUES('fm_native_files'[SourceRevisionID]))),"0")&" file(s) · comparisons separated by saved scenario",
 "Choose saved files below, then Apply filters"),
''' + caption + ")"
    for name in ("N Headline Cell", "N Summary Cell"):
        body = before[name]["expression"]
        result[name] = 'IF(HASONEVALUE(\'fm_native_scenario\'[Scenario]),\n' + body + ")"
    # Preserve the exact native line admission rule but evaluate it inside the
    # value body, avoiding the external visual value-filter constraint pass.
    result["N Chart Monthly"] = "IF([N Line Visible]=1,\n" + before["N Chart Monthly"]["expression"] + ")"
    return result


def original_helper(name):
    with ZipFile(HERE.parent / "report-native-only-r17.6/candidate/ForecastMaster Native Only R17.6 SAMPLE.zip") as archive:
        db = json.loads(archive.read(next(p for p in archive.namelist() if p.endswith("/model.bim"))))
    return next(t for t in db["model"]["tables"] if t["name"] == name)


def helper_patches():
    files = original_helper("fm_native_files")["partitions"][0]["source"]["expression"]
    lines = original_helper("fm_native_lines")["partitions"][0]["source"]["expression"]
    extra = '''"ImportedAtUTC",[_Imported],
 "FileChoiceLabel",[SourceFileName]&" | "&IF(ISBLANK([_Imported]),"Import time unavailable",
 FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")&" | "&[SourceRevisionID],
 '''
    needle = 'RETURN SELECTCOLUMNS(_ranked,\n '
    assert files.count(needle) == 1
    new_files = files.replace(needle, needle + extra)
    new_lines = 'ADDCOLUMNS(\n(' + lines + '''),"SeriesLabel",
 [ScopeLabel]&" · "&SWITCH([LineKind],0,"Actual",1,"Forecast",FORMAT([LineKind],"0")&"M trend")
 &IF([Mode]="Selected files"," · "&[Scenario],"")&" · "&[DemandCycle])'''
    def column(name, datatype):
        return {"name": name, "dataType": datatype, "type": "calculatedTableColumn",
                "sourceColumn": "[" + name + "]", "summarizeBy": "none"}
    imported = column("ImportedAtUTC", "dateTime"); imported["formatString"] = "dd mmm yyyy hh:mm:ss"
    choice = column("FileChoiceLabel", "string"); choice["sortByColumn"] = "ImportedAtUTC"
    return {
        "fm_native_files": (files, new_files, [imported, choice]),
        "fm_native_lines": (lines, new_lines, [column("SeriesLabel", "string")]),
    }


RELATIONSHIP = {"name": "NativeR17-Scenario-Mode", "fromTable": "fm_native_scenario", "fromColumn": "Mode",
                "toTable": "fm_native_file_mode", "toColumn": "Mode"}


def fingerprints():
    return {name: {key: expression_hash(value if key == "expression" else value["expression"])
                   for key, value in measure.items() if key in {"expression", "formatStringDefinition"}}
            for name, measure in baseline().items()}


def patch_database(database):
    fixed = deepcopy(database)
    tables = {t["name"]: t for t in fixed["model"]["tables"]}
    if len(tables) != len(fixed["model"]["tables"]) or sum(n.startswith("fm_native_") for n in tables) != 24:
        raise ValueError("Expected verified R17.6 native tables; no write.")
    expected, edits, fits = fingerprints(), replacements(), fit_measures()
    measure_list = tables.get("fm_native_measures", {}).get("measures", [])
    current = {m["name"]: m for m in measure_list}
    if len(current) != len(measure_list) or set(current) not in (set(expected), set(expected) | set(fits)):
        raise ValueError("Unexpected native measures; no write.")
    changed = []
    for name, hashes in expected.items():
        allowed = {hashes["expression"]} | ({expression_hash(edits[name])} if name in edits else set())
        if expression_hash(current[name]["expression"]) not in allowed:
            raise ValueError("Unknown native body; require R17.6 first.")
        fmt = current[name].get("formatStringDefinition")
        if bool(fmt) != ("formatStringDefinition" in hashes) or (
                fmt and expression_hash(fmt["expression"]) != hashes["formatStringDefinition"]):
            raise ValueError("Unexpected numeric format; no write.")
        if name in edits and expression_hash(current[name]["expression"]) != expression_hash(edits[name]):
            current[name]["expression"] = edits[name]
            changed.append(name)
    for name, expression in fits.items():
        if name in current:
            if expression_hash(current[name]["expression"]) != expression_hash(expression):
                raise ValueError("Unknown fit helper; no write.")
        else:
            measure_list.append({"name": name, "expression": expression, "displayFolder": "Native performance", "isHidden": True})
            changed.append(name)
    for name, (before, after, columns) in helper_patches().items():
        table = tables[name]
        if len(table.get("partitions", [])) != 1:
            raise ValueError("Unexpected helper partitions; no write.")
        source = table["partitions"][0].get("source", {})
        if source.get("type") != "calculated" or expression_hash(source.get("expression", "")) not in {
                expression_hash(before), expression_hash(after)}:
            raise ValueError("Unknown file/line helper; no write.")
        if expression_hash(source["expression"]) != expression_hash(after):
            source["expression"] = after
            changed.append(name + ".expression")
        for col in columns:
            existing = [c for c in table["columns"] if c["name"] == col["name"]]
            if existing and existing != [col]:
                raise ValueError("Unknown file/line column; no write.")
            if not existing:
                table["columns"].append(deepcopy(col))
                changed.append(name + "." + col["name"])
    rels = fixed["model"].get("relationships", [])
    found = [r for r in rels if r["name"] == RELATIONSHIP["name"]]
    if found != [RELATIONSHIP]:
        raise ValueError("Unexpected source-mode relationship; no write.")
    restored = deepcopy(fixed)
    original = {t["name"]: t for t in database["model"]["tables"]}
    allowed = {"fm_native_measures", "fm_native_files", "fm_native_lines"}
    restored["model"]["tables"] = [deepcopy(original[t["name"]]) if t["name"] in allowed else t for t in restored["model"]["tables"]]
    restored["model"]["relationships"] = deepcopy(database["model"].get("relationships", []))
    if "relationships" not in database["model"]:
        restored["model"].pop("relationships", None)
    if restored != database:
        raise AssertionError("Unrelated model mutation; no write.")
    return fixed, changed
