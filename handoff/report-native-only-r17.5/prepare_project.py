"""Compact native-only R17.5 report; its small TEST update is separate.

Starts with the frozen R17.4 TEST ZIP. The three new report measures return
formatting text only. model.py supplies a separate two-chart-measure TEST patch.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r174_report", HERE.parent / "report-native-only-r17.4/prepare_project.py")
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
BASE = OLD.OLD
NAME = "ForecastMaster Native Only R17.5 TEST"
SAMPLE_NAME = "ForecastMaster Native Only R17.5 SAMPLE"
SOURCE_SHA256 = "8456cd5df59fe5ee8624985e09c148707b28e66b38aab22ecfc21d0c88b3e3d9"
lit, color, projection, write = OLD.lit, OLD.color, OLD.projection, OLD.write
FORMATTING = {
    "N R175 Line Style": '''VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])
RETURN SWITCH(TRUE(),_kind=1,"dashed",_kind IN {6,12,24},"dotted","solid")''',
    "N R175 Series Color": '''VAR _scope=SELECTEDVALUE('fm_native_lines'[ScopeLabel],"Selected total")
VAR _rank=RANKX(ALL('fm_native_lines'[ScopeLabel]),'fm_native_lines'[ScopeLabel],_scope,ASC,DENSE)
RETURN IF(_scope="Selected total","#096B76",SWITCH(MOD(_rank-1,6),
0,"#096B76",1,"#527C47",2,"#766B90",3,"#9D652A",4,"#3185A2","#A34560"))''',
    "N R175 Summary Color": '''IF(SELECTEDVALUE('fm_native_columns'[ColumnKey])="plan",
"#183B56",CALCULATE([N Variance Color],REMOVEFILTERS('fm_native_trend'),
TREATAS({SELECTEDVALUE('fm_native_columns'[Window])},'fm_native_trend'[Window])))''',
}


def style_measure(name):
    return {"expr": {"Measure": {"Expression": {"SourceRef": {
        "Schema": "extension", "Entity": "fm_native_measures"}}, "Property": name}}}


def extensions():
    measures = [
                {"name": name, "dataType": "Text", "expression": expression,
                 "hidden": True, "displayFolder": "Report formatting", "references": {
                     "unrecognizedReferences": False,
                     "measures": ([{"entity": "fm_native_measures", "name": "N Variance Color"}]
                                  if name == "N R175 Summary Color" else [])}}
                for name, expression in FORMATTING.items()]
    measures += [
        {"name":"N R175 Measure Selected", "dataType":"Integer", "hidden":True,
         "expression":"IF(HASONEVALUE('fm_native_metric'[RowID]),1,0)", "formatString":"0"},
        {"name":"N R175 Measure Caption", "dataType":"Text", "hidden":True,
         "expression":'''IF(HASONEVALUE('fm_native_metric'[RowID]),[N Measure Caption],
"Choose a measure under Section → Measure")''',
         "references":{"unrecognizedReferences":False,"measures":[{"entity":"fm_native_measures","name":"N Measure Caption"}]}}
    ]
    return {"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/reportExtension/1.0.0/schema.json",
            "name":"extension", "entities":[{"name":"fm_native_measures","measures":measures}]}


def require_selected_measure(v):
    BASE.PP.measure_filter(v,"N R175 Measure Selected")
    item = v["filterConfig"]["filters"][-1]
    item["field"]["Measure"]["Expression"]["SourceRef"]["Schema"] = "extension"
    item["filter"]["From"][0]["Schema"] = "extension"


def month_slicer():
    v = BASE.slicer("review_months", "fm_review_months", "Month", 1000, 8, 420,
                    "Review months · select first and last", single=False)
    v["position"]["height"] = 80
    v["visual"]["query"]["queryState"]["Values"]["projections"][0]["format"] = "MMM yyyy"
    v["visual"]["query"]["sortDefinition"] = {"sort": [{
        "field": BASE.PP.field("fm_review_months", "Month"), "direction": "Ascending"}], "isDefaultSort": True}
    predicate = BASE.PP.category_filter("fm_review_months", "Month", ["unused"])
    predicate["Where"][0]["Condition"]["In"]["Values"] = [
        [{"Literal": {"Value": "datetime'2025-01-01T00:00:00'"}}],
        [{"Literal": {"Value": "datetime'2027-12-01T00:00:00'"}}]]
    v["visual"]["objects"]["general"][0]["properties"]["filter"] = {"filter": predicate}
    # Existing numeric measures deliberately use MIN/MAX of this disconnected
    # month dictionary. This selector is a WINDOW BOUNDS control, not a sparse
    # list of months. Its label/caption must keep that contract explicit.
    return v


def expanded_columns(query):
    # Pin the active native column hierarchy, and explicitly expand named nodes.
    # R17.4 had levels only; receiving Desktop still opened at period parents.
    periods = [str(year) + " " + kind for year in range(2023, 2030)
               for kind in ("FY", "YTD", "YTG", "H1", "H2")]
    comparisons = ["Total Plan", "6M variance", "12M variance", "24M variance"]
    return {"roles": ["Columns"], "root": {"children": [
        {"identityValues": [lit(period)["expr"]], "isToggled": True, "children": [
            {"identityValues": [lit(comparison)["expr"]], "isToggled": True}
            for comparison in comparisons]} for period in periods]},
        "levels": [{"queryRefs": [q["queryRef"]], "identityKeys": [q["field"]],
                    "isCollapsed": False, "isPinned": True} for q in query["Columns"]["projections"][:-1]]}


def make_page():
    page, originals = OLD.make_page()
    keep = {v["name"]: deepcopy(v) for v in originals
            if v["name"] not in {"edition", "basis", "review_help", "section"}}
    layout = {
      "heading": (20,8,960,38), "source_status": (20,52,960,34),
      "affiliate": (20,100,140,80), "cycle": (172,100,176,80),
      "metric": (360,100,416,80), "display": (788,100,140,80),
      "chart_trend": (940,100,168,80), "view": (1120,100,300,80),
      "scope_heading": (20,192,1400,22),
      "drivers": (20,226,260,80), "tiers": (292,226,420,80),
      "periods": (724,226,420,80), "trend": (1156,226,264,80),
      "headline_title": (20,318,1400,22), "headline": (20,350,1400,104),
      "native_chart": (20,466,1400,280),
      "executive_title": (20,758,1400,28), "executive_summary": (20,798,1400,300),
      "files_heading": (20,1110,1400,22), "matching_files": (20,1142,1400,128),
    }
    for name, rectangle in layout.items():
        keep[name]["position"].update(zip(("x","y","width","height"), rectangle))
    keep["review_months"] = month_slicer()
    heading = keep["heading"]["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    heading.update(value="ForecastMaster · Demand review · R17.5 TEST")
    heading["textStyle"]["fontSize"] = "18pt"
    # One native Section -> Measure selector prevents a selected child measure
    # from removing its sibling section or persisting an incompatible pair.
    metric = keep["metric"]["visual"]
    metric["query"]["queryState"]["Values"]["projections"] = [
        projection("fm_native_metric", "Section", label="Section"),
        projection("fm_native_metric", "MetricLabel", label="Measure")]
    metric["objects"]["header"][0]["properties"]["text"] = lit("Section → Measure")
    metric.pop("syncGroup", None)
    keep["chart_trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Graph / headline trend")
    keep["trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Table comparisons")
    periods = keep["periods"]["visual"]["objects"]["general"][0]["properties"]
    periods["filter"] = {"filter": BASE.PP.category_filter("fm_native_periods", "Label",
                        ["2026 FY","2026 YTD","2026 YTG","2027 FY"])}
    summary = keep["executive_summary"]["visual"]
    query = summary["query"]["queryState"]
    for p in query["Columns"]["projections"]:
        p["active"] = True
    summary["expansionStates"] = [s for s in summary["expansionStates"] if s["roles"] == ["Rows"]]
    summary["expansionStates"].append(expanded_columns(query))
    summary["objects"]["columnHeaders"][0]["properties"]["columnAdjustment"] = lit("fitToContent")
    summary["objects"]["values"].append({"properties": {
        "fontColor": {"solid": {"color": style_measure("N R175 Summary Color")}}},
        "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                     "metadata": "fm_native_measures.N Summary Cell"}})
    # Native field-value formatting evaluated per categorical legend series.
    # These report measures return text; they never alter monthly numbers.
    chart = keep["native_chart"]["visual"]
    series = {"data": [{"roles": ["Series"]}], "hierarchyMatching": 1}
    chart["objects"]["lineStyles"] = [
        {"properties": {"strokeWidth": lit(2), "lineChartType": lit("linear"),
                         "lineStyle": lit("solid"), "showMarker": lit(False)}},
        {"properties": {"lineStyle": style_measure("N R175 Line Style")}, "selector": series}]
    chart["objects"]["dataPoint"] = [{"properties": {
        "fill": {"solid": {"color": style_measure("N R175 Series Color")}}}, "selector": series}]
    chart["objects"]["legend"][0]["properties"].update(matchLineColor=lit(True), legendMarkerRendering=lit("lineAndMarker"))
    chart["visualContainerObjects"]["title"][0]["properties"]["text"] = style_measure("N R175 Measure Caption")
    for name in ("headline","native_chart","executive_summary"):
        require_selected_measure(keep[name])
    keep["month_note"] = BASE.text("month_note", "Every month between the selected bounds is included.",
                                  1000,88,420,12,8,False,BASE.MUTED)
    keep["month_note"]["visual"]["visualContainerObjects"]["padding"][0]["properties"].update(top=lit(0),bottom=lit(0))
    page["height"] = 1286
    page["visualInteractions"] = [{"source": source, "target": name, "type": "NoFilter"}
        for source in ("native_chart", "matching_files", "executive_summary") for name in keep if name != source]
    for i, v in enumerate(keep.values()):
        v["position"].update(z=i,tabOrder=i)
    return page, list(keep.values())


def create(source_zip, destination):
    if destination.exists():
        raise ValueError("Use a new destination; keep earlier reports.")
    if hashlib.sha256(source_zip.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected frozen R17.4 TEST ZIP.")
    with TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as archive:
            archive.extractall(tmp)
        source = next(Path(tmp).glob("*.Report"))
        report = destination / (NAME + ".Report")
        shutil.copytree(source, report)
        root = report / "definition"
        shutil.rmtree(root / "pages")
        page, visuals = make_page()
        write(root / "pages/native_demand/page.json", page)
        write(root / "pages/pages.json", {"$schema": BASE.PP.SCHEMA + "pagesMetadata/1.0.0/schema.json",
              "pageOrder": ["native_demand"], "activePageName": "native_demand"})
        for v in visuals:
            assert v["visual"]["visualType"] in OLD.BUILTINS
            write(root / "pages/native_demand/visuals" / v["name"] / "visual.json", v)
        write(root / "reportExtensions.json", extensions())
        write(destination / (NAME + ".pbip"), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
              "version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
        assert (report / "definition.pbir").read_bytes() == (source / "definition.pbir").read_bytes()
    result = {"Stage": "NATIVE_ONLY_COMPACT_REPORT_R175", "CompanyModelChanged": False,
              "RequiresFabricSetupCell": True, "SourceArithmeticChanged": False,
              "TwoChartPresentationExpressionsRequireTestUpdate": True,
              "FormattingTextMeasures": len(FORMATTING), "SelectionGuardAndCaptionMeasures":2, "CustomVisualCount": 0,
              "TESTBindingPreserved": True, "Height": page["height"], "PreviousHeight": 1860,
              "NativeVisualCount": len(visuals), "DesktopRendering": "PENDING",
              "DynamicMatrixHeight": "Not implemented; fixed native viewport and Focus mode",
              "ProductionReplacement": "NOT QUALIFIED"}
    write(destination / "PRESERVATION.json", result)
    return result


def sample_from_frozen(test_project, destination):
    if destination.exists():
        raise ValueError("Use a new sample destination.")
    shutil.copytree(test_project, destination)
    report = destination / (SAMPLE_NAME + ".Report")
    (destination / (NAME + ".Report")).rename(report)
    semantic = destination / (SAMPLE_NAME + ".SemanticModel")
    with ZipFile(HERE.parent / "report-native-only-r17.4/candidate/ForecastMaster Native Only R17.4 SAMPLE.zip") as archive:
        for name in archive.namelist():
            if ".SemanticModel/" in name:
                relative = name.split(".SemanticModel/",1)[1]
                if relative:
                    target = semantic / relative
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(name))
    spec = importlib.util.spec_from_file_location("r175_sample_patch", HERE / "model.py")
    patch = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(patch)
    model_path = semantic / "model.bim"
    database, changed = patch.patch_database(json.loads(model_path.read_text()))
    assert set(changed) == {"N Chart Monthly","N Line Visible"}
    write(model_path,database)
    write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}}})
    project = json.loads((destination / (NAME + ".pbip")).read_text())
    (destination / (NAME + ".pbip")).unlink()
    project["artifacts"][0]["report"]["path"] = report.name
    write(destination / (SAMPLE_NAME + ".pbip"), project)
    heading = report / "definition/pages/native_demand/visuals/heading/visual.json"
    value = json.loads(heading.read_text())
    value["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = "ForecastMaster · Demand review · R17.5 SAMPLE"
    write(heading, value)
    write(destination / "PRESERVATION.json", {"Stage": "NATIVE_ONLY_COMPACT_SAMPLE_R175", "FabricConnection": False,
        "FabricatedDataOnly": True, "OnlyTwoChartExpressionsChanged": True, "CustomVisualCount": 0,
        "DesktopRendering": "PENDING"})


zip_project = OLD.zip_project
