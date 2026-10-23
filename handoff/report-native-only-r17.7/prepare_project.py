"""Native-only compact labels, end-of-line names, checkbox files, batched filters."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


OLD = load("r176_report", HERE.parent / "report-native-only-r17.6/prepare_project.py")
MODEL = load("r177_model", HERE / "model.py")
BASE, lit, projection, write = OLD.BASE, OLD.lit, OLD.projection, OLD.write
NAME = "ForecastMaster Native Only R17.7 TEST"
SAMPLE_NAME = "ForecastMaster Native Only R17.7 SAMPLE"
SOURCE_SHA256 = "613313682a6c3cd2a14d49736e54920772c4894aa5775fc922113f4e8be26410"


def apply_button(name, x, y):
    v = BASE.normalize(BASE.OLD.button(name, "Apply filters", x, y, 220, "ApplyAllSlicers", "", h=44))
    props = v["visual"]["visualContainerObjects"]["visualLink"][0]["properties"]
    props.clear(); props.update(show=lit(True), type=lit("ApplyAllSlicers"))
    v["visual"]["objects"]["icon"] = [{"properties": {"show": lit(False)}},
        {"properties": {"placement": lit("left")}, "selector": {"id": "default"}}]
    return v


def make_page():
    page, original = OLD.make_page()
    vs = {v["name"]: deepcopy(v) for v in original if v["name"] != "scope_heading"}
    vs["source_mode"] = BASE.slicer("source_mode", "fm_native_file_mode", "Mode", 20, 250, 340,
                                    "Source selection", "Automatic ADS", True)
    layout = {
        "heading": (20,8,948,36), "source_status": (20,50,948,36),
        "start_month": (980,8,210,72), "end_month": (1202,8,218,72),
        "affiliate": (20,98,160,64), "cycle": (192,98,176,64),
        "section": (380,98,240,64), "metric": (632,98,472,64), "display": (1116,98,304,64),
        "drivers": (20,174,340,64), "tiers": (372,174,450,64), "periods": (834,174,586,64),
        "source_mode": (20,250,340,64),
        "headline_title": (20,340,1068,24), "chart_trend": (1100,328,320,64),
        "headline": (20,404,1400,116),
        "chart_title": (20,548,1068,24), "view": (1100,536,320,64),
        "native_chart": (20,612,1400,340),
        "executive_title": (20,980,1068,24), "trend": (1100,968,320,64),
        "executive_summary": (20,1044,1400,320),
        "files_heading": (20,1392,1160,24), "matching_files": (20,1704,1400,164),
    }
    for name, rectangle in layout.items():
        vs[name]["position"].update(zip(("x", "y", "width", "height"), rectangle))
    for v in vs.values():
        if v["visual"]["visualType"] == "slicer":
            pad = v["visual"]["visualContainerObjects"]["padding"][0]["properties"]
            pad.update({key: lit(2) for key in ("top", "bottom", "left", "right")})
            v["visual"]["objects"]["header"][0]["properties"]["show"] = lit(True)
    vs["view"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Graph detail")
    vs["chart_trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Graph / review trend · one")
    vs["trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Table trends · multiple")
    heading = vs["heading"]["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    heading["value"] = "ForecastMaster · Demand review · R17.7 TEST"
    vs["apply_top"] = apply_button("apply_top", 1200, 266)
    vs["apply_files"] = apply_button("apply_files", 1200, 1382)
    vs["apply_note"] = BASE.text("apply_note", "Choose filters and files, then Apply filters.\nPending choices do not redraw the report until applied.",
                                  372,258,810,48,10,False,BASE.MUTED)
    vs["chart_key"] = BASE.text("chart_key", "Solid: actuals   Dashed: forecast   Dotted: selected trend. Labels start with the driver or sector.",
                                 20,580,1068,24,9,False,BASE.MUTED)
    # Keep original identities for full tooltips while using concise native
    # category labels. No series is dropped or arbitrarily restricted to Top N.
    chart = vs["native_chart"]["visual"]
    vs["native_chart"]["filterConfig"]["filters"] = [f for f in vs["native_chart"]["filterConfig"]["filters"]
        if f.get("field", {}).get("Measure", {}).get("Property") != "N Line Visible"]
    chart["query"]["queryState"]["Series"]["projections"] = [projection("fm_native_lines", "SeriesLabel", label="Series")]
    chart["objects"]["seriesLabels"] = [{"properties": {"show": lit(True), "fontSize": lit(10), "seriesMatchColor": lit(True)}}]
    chart["objects"]["legend"][0]["properties"].update(position=lit("Right"), fontSize=lit(10))
    chart["objects"]["valueAxis"][0]["properties"].update(labelDisplayUnits=lit(0), labelPrecision=lit(1))
    # Each saved scenario is a separate native matrix row group. Never sum
    # alternative versions into one forecast or invent a cross-version total.
    for name in ("headline", "executive_summary"):
        visual = vs[name]["visual"]
        rows = visual["query"]["queryState"]["Rows"]["projections"]
        rows.insert(0, projection("fm_native_scenario", "Scenario", label="Source version"))
        levels = [{"queryRefs": [p["queryRef"]], "identityKeys": [p["field"]],
                   "isCollapsed": i > 0, "isPinned": i == 0} for i, p in enumerate(rows[:-1])]
        visual["expansionStates"] = [s for s in visual.get("expansionStates", []) if s["roles"] != ["Rows"]]
        visual["expansionStates"].append({"roles": ["Rows"], "levels": levels,
            "root": {"children": [{"identityValues": [lit("Automatic ADS")["expr"]], "isToggled": True}]}})
    picker = BASE.slicer("file_picker", "fm_native_files", "FileChoiceLabel", 20, 1436, 1400,
                         "Saved files · check several without Ctrl; newest import first", single=False, mode="Basic")
    picker["position"]["height"] = 252
    picker["visual"]["objects"]["searchBox"] = [{"properties": {"show": lit(True)}}]
    picker["visual"]["objects"]["selection"][0]["properties"].update(singleSelect=lit(False), strictSingleSelect=lit(False))
    picker["visual"]["query"]["sortDefinition"] = {"sort": [{"field": BASE.PP.field("fm_native_files", "FileChoiceLabel"),
                                                             "direction": "Descending"}], "isDefaultSort": True}
    vs["file_picker"] = picker
    vs["matching_files"] = BASE.native_table("matching_files", 20,1704,1400,164, [
        ("fm_native_files", "GrowthDriver", False, "Growth driver"),
        ("fm_native_files", "SourceFileName", False, "File"),
        ("fm_native_files", "ImportedAtUTC", False, "Imported (UTC)", "dd MMM yyyy HH:mm:ss"),
        ("fm_native_files", "IMSActualsThrough", False, "IMS through", "MMM yyyy"),
        ("fm_native_files", "ExFactoryActualsThrough", False, "Ex-factory through", "MMM yyyy")])
    vs["matching_files"]["visual"]["objects"]["columnHeaders"][0]["properties"]["columnAdjustment"] = lit("growToFit")
    page["filterConfig"]["filters"] = [f for f in page["filterConfig"]["filters"]
        if f["field"].get("Column", {}).get("Expression", {}).get("SourceRef", {}).get("Entity") not in {
            "fm_native_file_mode", "fm_native_scenario"}]
    page["height"] = 1884
    page["visualInteractions"] = [{"source": source, "target": name, "type": "NoFilter"}
        for source in ("headline", "native_chart", "executive_summary", "matching_files") for name in vs if source != name]
    page["visualInteractions"].append({"source": "metric", "target": "section", "type": "NoFilter"})
    page["visualInteractions"].extend({"source": source, "target": target, "type": "NoFilter"}
        for source, targets in (("chart_trend", ("executive_summary",)), ("trend", ("headline", "native_chart")),
                               ("file_picker", ("source_mode", "affiliate", "cycle"))) for target in targets)
    for i, v in enumerate(vs.values()):
        v["position"].update(z=i, tabOrder=i)
    return page, list(vs.values())


def create(source_zip, destination):
    if destination.exists():
        raise ValueError("Use a new destination; preserve earlier versions.")
    if hashlib.sha256(source_zip.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected frozen R17.6 TEST ZIP.")
    with TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as archive: archive.extractall(tmp)
        source = next(Path(tmp).glob("*.Report"))
        report = destination / (NAME + ".Report")
        shutil.copytree(source, report)
        root = report / "definition"
        shutil.rmtree(root / "pages")
        page, visuals = make_page()
        write(root / "pages/native_demand/page.json", page)
        write(root / "pages/pages.json", {"$schema": BASE.PP.SCHEMA + "pagesMetadata/1.0.0/schema.json",
                                          "pageOrder": ["native_demand"], "activePageName": "native_demand"})
        for visual in visuals:
            assert visual["visual"]["visualType"] in {"textbox", "slicer", "cardVisual", "tableEx", "pivotTable", "lineChart", "actionButton"}
            write(root / "pages/native_demand/visuals" / visual["name"] / "visual.json", visual)
        write(destination / (NAME + ".pbip"), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
              "version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
        assert (report / "definition.pbir").read_bytes() == (source / "definition.pbir").read_bytes()
    write(destination / "PRESERVATION.json", {"Stage": "R177_NATIVE_REPORT_PREPARED", "CustomVisualCount": 0,
          "NativeVisuals": len(visuals), "TESTBindingPreserved": True, "RequiresR177TESTUpdateAndProcessing": True,
          "DesktopRenderingAndCompanySpeed": "PENDING"})


def sample_from_frozen(test_project, destination):
    if destination.exists(): raise ValueError("Use a new sample destination.")
    shutil.copytree(test_project, destination)
    report = destination / (SAMPLE_NAME + ".Report")
    (destination / (NAME + ".Report")).rename(report)
    semantic = destination / (SAMPLE_NAME + ".SemanticModel")
    with ZipFile(HERE.parent / "report-native-only-r17.6/candidate/ForecastMaster Native Only R17.6 SAMPLE.zip") as archive:
        for name in archive.namelist():
            if ".SemanticModel/" in name:
                relative = name.split(".SemanticModel/", 1)[1]
                if relative:
                    target = semantic / relative; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(archive.read(name))
    model_path = semantic / "model.bim"
    database, _ = MODEL.patch_database(json.loads(model_path.read_text()))
    write(model_path, database)
    write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}}})
    project = json.loads((destination / (NAME + ".pbip")).read_text())
    (destination / (NAME + ".pbip")).unlink(); project["artifacts"][0]["report"]["path"] = report.name
    write(destination / (SAMPLE_NAME + ".pbip"), project)
    heading = report / "definition/pages/native_demand/visuals/heading/visual.json"
    value = json.loads(heading.read_text()); value["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = "ForecastMaster · Demand review · R17.7 SAMPLE"
    write(heading, value)
    write(destination / "PRESERVATION.json", {"Stage": "R177_NATIVE_SAMPLE", "FabricatedDataOnly": True, "FabricConnection": False,
          "CompanySpeedAndRendering": "PENDING"})


zip_project = OLD.zip_project
