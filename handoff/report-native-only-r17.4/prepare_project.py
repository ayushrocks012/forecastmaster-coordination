"""Simplify the frozen native preview; keep all visuals built in."""
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import sys
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("native_r173", HERE.parent / "report-native-only-r17.3/prepare_project.py")
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
SPEC2 = importlib.util.spec_from_file_location("native_r174_model", HERE / "model.py")
MODEL = importlib.util.module_from_spec(SPEC2)
SPEC2.loader.exec_module(MODEL)
NAME = "ForecastMaster Native Only R17.4 TEST"
SAMPLE_NAME = "ForecastMaster Native Only R17.4 SAMPLE"
SOURCE_SHA256 = "c112e4df58902ceb1abce5cfba7cdebe4147e0fbd12a192d25106b4149f0b24e"
lit, color, projection, write = OLD.lit, OLD.color, OLD.projection, OLD.PP.write
BUILTINS = {"textbox", "slicer", "tableEx", "pivotTable", "lineChart", "cardVisual"}


def source_card(original):
    v = OLD.visual("source_status", "cardVisual", **{k: original["position"][k] for k in ("x", "y")},
                   w=1400, h=56, roles={"Data": {"projections": [projection("fm_native_measures", "N Source Caption", True, "Saved sources")]}})
    v["visual"]["objects"] = {
      "value": [{"properties": {"fontSize": lit(10), "fontColor": color(OLD.MUTED)}, "selector": {"id": "default"}}],
      "label": [{"properties": {"show": lit(False)}, "selector": {"id": "default"}}],
      "padding": [{"properties": {"paddingUniform": lit(8)}, "selector": {"id": "default"}}],
      "layout": [{"properties": {"paddingUniform": lit(0)}, "selector": {"id": "default"}}]}
    return v


def make_page():
    page, before = OLD.make_page()
    visuals = []
    removed = {"drivers_all", "drivers_clear", "tiers_all", "tiers_clear", "periods_all", "periods_clear",
               "rows_drivers", "rows_sectors", "rows_both", "summary_drivers", "summary_sectors", "month_readout"}
    for original in before:
        if original["name"] in removed:
            continue
        v = deepcopy(original)
        kind = v["visual"]["visualType"]
        old_y = v["position"]["y"]
        shift = (56 if old_y >= 616 else 0) + (36 if old_y >= 844 else 0) + (72 if old_y >= 1416 else 0)
        v["position"]["y"] -= shift
        if kind == "textbox":
            # Native paragraph height must not be squeezed by vertical padding.
            v["visual"]["visualContainerObjects"]["padding"][0]["properties"].update(top=lit(0), bottom=lit(0))
        if v["name"] == "edition":
            run = v["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]
            run["value"] = "R17.4 TEST · Built-in Power BI visuals only"
        if v["name"] == "source_status":
            v = source_card(v)
        elif v["name"] == "review_help":
            v["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = (
                "Review months control the chart and available summary years.\nUse the slicers' own Select all / clear options and Power BI's visual menus.")
        elif v["name"] == "review_months":
            data = v["visual"]["objects"]["data"][0]["properties"]
            # The native range renderer reads these UI bounds independently of
            # general.filter. Without them it showed 2023–2029 while querying 2026.
            data["startDate"] = {"expr": {"Literal": {"Value": "datetime'2026-01-01T00:00:00'"}}}
            data["endDate"] = {"expr": {"Literal": {"Value": "datetime'2026-12-01T00:00:00'"}}}
        elif v["name"] == "headline":
            v["position"]["height"] = 136
            v["visual"]["objects"]["columnHeaders"][0]["properties"]["columnAdjustment"] = lit("growToFit")
        elif v["name"] == "native_chart":
            v["visual"]["objects"]["zoom"] = [{"properties": {"show": lit(False), "showOnValueAxis": lit(False)}}]
            # A continuous date axis fits the reviewed months to the plot width
            # instead of introducing a categorical horizontal scroll viewport.
            v["visual"]["objects"]["categoryAxis"][0]["properties"]["axisType"] = lit("Scalar")
        elif v["name"] == "summary_both":
            v["name"] = "executive_summary"
            v.pop("isHidden", None)
            v["visual"]["query"]["queryState"]["Rows"] = {"projections": [
                projection("fm_native_scope", "GrowthDriver", label="Growth driver"),
                projection("fm_native_scope", "SectorLabel", label="Sector – growth driver")]}
            obj = v["visual"]["objects"]
            obj["rowHeaders"][0]["properties"].update(autoExpand=lit(False), showExpandCollapseButtons=lit(True))
            obj["columnHeaders"][0]["properties"].update(autoExpand=lit(True), columnAdjustment=lit("growToFit"))
            obj["subTotals"][0]["properties"]["rowSubtotals"] = lit(True)
            # Rows start at drivers. Columns retain all comparison levels;
            # pinning prevents an undefined percentage/amount parent display.
            query = v["visual"]["query"]["queryState"]
            v["visual"]["expansionStates"] = [{"roles": [role], "levels": [
                {"queryRefs": [q["queryRef"]], "identityKeys": [q["field"]],
                 "isCollapsed": role == "Rows", "isPinned": role == "Columns"}
                for q in query[role]["projections"]]} for role in ("Rows", "Columns")]
            header = v["visual"]["visualContainerObjects"]["visualHeader"][0]["properties"]
            for key in ("showDrillRoleSelector", "showDrillUpButton", "showDrillToggleButton",
                        "showDrillDownLevelButton", "showDrillDownExpandButton"):
                header[key] = lit(True)
            v["visual"]["drillFilterOtherVisuals"] = False
        elif v["name"] == "matching_files":
            for p in v["visual"]["query"]["queryState"]["Values"]["projections"]:
                if "format" in p:
                    p["format"] = "MMM yyyy"  # Visual-level syntax is .NET, not DAX/VBA.
            v["visual"]["objects"]["columnHeaders"][0]["properties"]["columnAdjustment"] = lit("growToFit")
        visuals.append(v)
    page["height"] -= 164
    page["visualInteractions"] = [{"source": source, "target": v["name"], "type": "NoFilter"}
        for source in ("native_chart", "matching_files", "executive_summary") for v in visuals if v["name"] != source]
    for i, v in enumerate(visuals):
        v["position"].update(z=i, tabOrder=i)
    return page, [OLD.normalize(v) for v in visuals]


def create(source_zip, destination):
    if destination.exists():
        raise ValueError("Use a new destination; preserve earlier reports.")
    if hashlib.sha256(source_zip.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected frozen R17.3 source ZIP.")
    with TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as z:
            z.extractall(tmp)
        source = next(Path(tmp).glob("*.Report"))
        report = destination / (NAME + ".Report")
        shutil.copytree(source, report)
        root = report / "definition"
        shutil.rmtree(root / "pages")
        shutil.rmtree(root / "bookmarks")
        page, visuals = make_page()
        write(root / "pages/native_demand/page.json", page)
        write(root / "pages/pages.json", {"$schema": OLD.PP.SCHEMA + "pagesMetadata/1.0.0/schema.json",
                                          "pageOrder": ["native_demand"], "activePageName": "native_demand"})
        for v in visuals:
            assert v["visual"]["visualType"] in BUILTINS
            write(root / "pages/native_demand/visuals" / v["name"] / "visual.json", v)
        write(root / "bookmarks/bookmarks.json", {"$schema": OLD.PP.SCHEMA + "bookmarksMetadata/1.0.0/schema.json", "items": []})
        write(destination / (NAME + ".pbip"), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
        assert (report / "definition.pbir").read_bytes() == (source / "definition.pbir").read_bytes()
        result = {"Stage": "NATIVE_ONLY_DRILL_PREVIEW", "CustomVisualCount": 0, "ActionButtonCount": 0,
                  "NativeVisualCount": len(visuals), "TESTBindingPreserved": True,
                  "CompanyModelIncluded": False, "RequiresTestFormatDisplayRepair": True,
                  "DesktopRenderingAndDrill": "PENDING", "ProductionReplacement": "NOT QUALIFIED"}
        write(destination / "PRESERVATION.json", result)
        return result


def create_sample(test_project, destination):
    if destination.exists():
        raise ValueError("Use a new sample folder.")
    shutil.copytree(test_project, destination)
    report = destination / (SAMPLE_NAME + ".Report")
    (destination / (NAME + ".Report")).rename(report)
    semantic = destination / (SAMPLE_NAME + ".SemanticModel")
    spec = importlib.util.spec_from_file_location("r174_sample_fixture", HERE.parent / "report-native-r17.2/tests/engine_fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    # Frozen scripts use the generic module name `model`. Isolate that import
    # from the new repair module when building/testing both in one process.
    previous = sys.modules.get("model")
    old_path = sys.path[:]
    try:
        sys.modules["model"] = MODEL.BASELINE
        spec.loader.exec_module(fixture)
    finally:
        sys.path[:] = old_path
        if previous is None:
            sys.modules.pop("model", None)
        else:
            sys.modules["model"] = previous
    original, *_ = fixture.build()
    database, changed = MODEL.patch_database(original)
    database["name"] = database["id"] = "ForecastMasterNativeSyntheticR174"
    for table in database["model"]["tables"]:
        assert all(p["source"]["type"] == "calculated" for p in table["partitions"])
    write(semantic / "definition.pbism", {"version": "4.0", "settings": {}})
    write(semantic / "model.bim", database)
    write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}}})
    project = json.loads((destination / (NAME + ".pbip")).read_text())
    project["artifacts"][0]["report"]["path"] = report.name
    (destination / (NAME + ".pbip")).unlink()
    write(destination / (SAMPLE_NAME + ".pbip"), project)
    edition = report / "definition/pages/native_demand/visuals/edition/visual.json"
    value = json.loads(edition.read_text())
    value["visual"]["objects"]["general"][0]["properties"]["paragraphs"][0]["textRuns"][0]["value"] = "R17.4 SAMPLE · Fabricated data · Built-in Power BI visuals only"
    write(edition, value)
    result = {"Stage": "NATIVE_ONLY_DRILL_SAMPLE", "FabricConnection": False, "FabricatedDataOnly": True,
              "NativeMeasurePropertiesRepaired": len(changed), "CustomVisualCount": 0, "DesktopRenderingAndDrill": "PENDING"}
    write(destination / "PRESERVATION.json", result)
    return result


zip_project = OLD.zip_project

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    a = parser.parse_args()
    print(json.dumps(create(a.source, a.destination), indent=2))
