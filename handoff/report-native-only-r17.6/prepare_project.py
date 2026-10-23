"""R17.6: independent native controls and simpler summary queries."""
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


OLD = load("r175_report", HERE.parent / "report-native-only-r17.5/prepare_project.py")
MODEL = load("r176_model", HERE / "model.py")
BASE = OLD.BASE
NAME = "ForecastMaster Native Only R17.6 TEST"
SAMPLE_NAME = "ForecastMaster Native Only R17.6 SAMPLE"
SOURCE_SHA256 = "10e16888e578d6f5420b20b12c7842da1e7a0fe06da5ff0a3524a6885fe45fa3"
lit, projection, write = OLD.lit, OLD.projection, OLD.write


def month_slicer(side, x, default):
    v = BASE.slicer(side + "_month", "fm_native_" + side + "_month", "MonthLabel",
                    x, 8, 200, side.capitalize() + " month", default=default, single=True)
    v["position"]["height"] = 80
    return v


def make_page():
    page, before = OLD.make_page()
    vs = {v["name"]: deepcopy(v) for v in before if v["name"] not in {"review_months", "month_note"}}
    _, r174 = OLD.OLD.make_page()
    section = next(v for v in r174 if v["name"] == "section")
    vs["section"] = deepcopy(section)
    metric = vs["metric"]["visual"]
    metric["query"]["queryState"]["Values"]["projections"] = [projection("fm_native_metric", "MetricLabel", label="Measure")]
    metric["objects"]["header"][0]["properties"]["text"] = lit("Measure")
    vs["start_month"] = month_slicer("start", 1008, "Jan 2025")
    vs["end_month"] = month_slicer("end", 1220, "Dec 2027")
    layout = {
        "heading": (20,8,976,38), "source_status": (20,52,976,40),
        "affiliate": (20,108,160,80), "cycle": (192,108,176,80),
        "section": (380,108,252,80), "metric": (644,108,440,80), "display": (1096,108,324,80),
        "scope_heading": (20,200,1400,22),
        "drivers": (20,234,320,80), "tiers": (352,234,520,80), "periods": (884,234,536,80),
        "headline_title": (20,342,1090,24), "chart_trend": (1122,326,298,80),
        "headline": (20,418,1400,108),
        "view": (1122,538,298,80), "native_chart": (20,630,1400,280),
        "executive_title": (20,938,1090,24), "trend": (1122,922,298,80),
        "executive_summary": (20,1014,1400,300),
        "files_heading": (20,1326,1400,22), "matching_files": (20,1360,1400,128),
    }
    for name, rectangle in layout.items():
        vs[name]["position"].update(zip(("x", "y", "width", "height"), rectangle))
    # Source caption: enough height, reduced inner padding, then a 16px gap.
    card = vs["source_status"]["visual"]
    card["objects"]["padding"][0]["properties"]["paddingUniform"] = lit(2)
    for key in ("top", "bottom"):
        card["visualContainerObjects"]["padding"][0]["properties"][key] = lit(2)
    heading = vs["heading"]["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
    heading["value"] = "ForecastMaster · Demand review · R17.6 TEST"
    vs["chart_trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Graph / review trend · single")
    vs["trend"]["visual"]["objects"]["header"][0]["properties"]["text"] = lit("Table trends · multiple")
    # Put chart-view controls in their own heading band; no overlap with plot.
    vs["chart_title"] = BASE.text("chart_title", "Monthly demand", 20, 554, 1090, 28, 12, True)
    # A value filter on a disconnected control must not drive the summary
    # query's row domain. Gate the existing display measures inside their body.
    for name in ("headline", "native_chart", "executive_summary"):
        config = vs[name].get("filterConfig", {})
        config["filters"] = [f for f in config.get("filters", [])
                             if f.get("field", {}).get("Measure", {}).get("Property") != "N R175 Measure Selected"]
        if not config["filters"]:
            vs[name].pop("filterConfig", None)
    summary = vs["executive_summary"]["visual"]
    q = summary["query"]["queryState"]
    q["Columns"]["projections"] = [projection("fm_native_periods", "Label", label="Review period"),
                                     projection("fm_native_columns", "ColumnLabel", label="Comparison")]
    for p in q["Columns"]["projections"]:
        p["active"] = True
    summary["expansionStates"] = [s for s in summary["expansionStates"] if s["roles"] == ["Rows"]]
    first = q["Columns"]["projections"][0]
    # Explicitly expand period parents. There is no third comparison/unit
    # hierarchy and no eager nested expansion for every comparison node.
    parents = [str(year) + " " + kind for year in range(2023, 2030)
               for kind in ("FY", "YTD", "YTG", "H1", "H2")]
    summary["expansionStates"].append({"roles": ["Columns"], "root": {"children": [
        {"identityValues": [lit(period)["expr"]], "isToggled": True} for period in parents]}, "levels": [
        {"queryRefs": [first["queryRef"]], "identityKeys": [first["field"]], "isCollapsed": False, "isPinned": True}]})
    # Formatting should not run a second benchmark calculation for every cell.
    summary["objects"]["values"] = [item for item in summary["objects"]["values"] if "selector" not in item]
    vs["native_chart"]["visual"]["visualContainerObjects"]["title"][0]["properties"]["text"] = {
        "expr": BASE.PP.field("fm_native_measures", "N Measure Caption", True)}
    page["height"] = 1504
    page["visualInteractions"] = [{"source": source, "target": name, "type": "NoFilter"}
        for source in ("headline", "native_chart", "matching_files", "executive_summary") for name in vs if name != source]
    # Section always exposes BOTH sections. Its selected child must not prune it.
    page["visualInteractions"].append({"source": "metric", "target": "section", "type": "NoFilter"})
    page["visualInteractions"].extend({"source": source, "target": target, "type": "NoFilter"}
        for source, targets in (("chart_trend", ("executive_summary",)), ("trend", ("headline", "native_chart")))
        for target in targets)
    for i, visual in enumerate(vs.values()):
        visual["position"].update(z=i, tabOrder=i)
    return page, list(vs.values())


def create(source_zip, destination):
    if destination.exists():
        raise ValueError("Use a new destination; preserve earlier reports.")
    if hashlib.sha256(source_zip.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Expected frozen R17.5 TEST ZIP.")
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
        for visual in visuals:
            assert visual["visual"]["visualType"] in OLD.OLD.BUILTINS
            write(root / "pages/native_demand/visuals" / visual["name"] / "visual.json", visual)
        extension = OLD.extensions()
        extension["entities"][0]["measures"] = [m for m in extension["entities"][0]["measures"]
            if m["name"] in {"N R175 Line Style", "N R175 Series Color"}]
        write(root / "reportExtensions.json", extension)
        write(destination / (NAME + ".pbip"), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
              "version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
        assert (report / "definition.pbir").read_bytes() == (source / "definition.pbir").read_bytes()
    result = {"Stage": "NATIVE_ONLY_R176_PREPARED", "CustomVisualCount": 0,
              "NativeVisualCount": len(visuals), "TESTBindingPreserved": True,
              "NewMonthlyDictionaries": 2, "RequiresTESTMetadataUpdateAndRefresh": True,
              "SummaryVisualMeasureFilters": 0, "DynamicMatrixHeight": False,
              "CompanyQueryMemoryAndNumericalAcceptance": "PENDING", "DesktopRendering": "PENDING"}
    write(destination / "PRESERVATION.json", result)
    return result


def sample_from_frozen(test_project, destination):
    if destination.exists():
        raise ValueError("Use a new sample destination.")
    shutil.copytree(test_project, destination)
    report = destination / (SAMPLE_NAME + ".Report")
    (destination / (NAME + ".Report")).rename(report)
    semantic = destination / (SAMPLE_NAME + ".SemanticModel")
    with ZipFile(HERE.parent / "report-native-only-r17.5/candidate/ForecastMaster Native Only R17.5 SAMPLE.zip") as archive:
        for name in archive.namelist():
            if ".SemanticModel/" in name:
                relative = name.split(".SemanticModel/", 1)[1]
                if relative:
                    target = semantic / relative
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(name))
    model_path = semantic / "model.bim"
    database, _ = MODEL.patch_database(json.loads(model_path.read_text()))
    write(model_path, database)
    write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}}})
    project = json.loads((destination / (NAME + ".pbip")).read_text())
    (destination / (NAME + ".pbip")).unlink()
    project["artifacts"][0]["report"]["path"] = report.name
    write(destination / (SAMPLE_NAME + ".pbip"), project)
    heading = report / "definition/pages/native_demand/visuals/heading/visual.json"
    value = json.loads(heading.read_text())
    value["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = "ForecastMaster · Demand review · R17.6 SAMPLE"
    write(heading, value)
    write(destination / "PRESERVATION.json", {"Stage": "NATIVE_ONLY_SAMPLE_R176", "FabricConnection": False,
          "FabricatedDataOnly": True, "CustomVisualCount": 0, "DesktopRenderingAndQueryPerformance": "PENDING"})


zip_project = OLD.zip_project
