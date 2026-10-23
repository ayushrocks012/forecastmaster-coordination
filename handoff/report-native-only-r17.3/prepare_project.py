"""Native-only Demand Review preview, bound to the existing isolated TEST.

Report-only repair: no model, company values, custom visuals or service writes.
R17.2 stays frozen. The preview deliberately qualifies page one first.
"""
from copy import deepcopy
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile, ZIP_DEFLATED

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("r172_report", HERE.parent / "report-native-r17.2/prepare_project.py")
OLD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OLD)
PP = OLD.pp
NAME = "ForecastMaster Native Only R17.3 TEST"
SOURCE_SHA256 = "aea0d12b56e985246a0730a6095f4088e43ab451bc87d0f28f28ca30fa15dc16"
BUILTINS = {"textbox", "slicer", "tableEx", "pivotTable", "lineChart", "actionButton"}
INK, TEAL, MUTED, PALE = "#183B56", "#096B76", "#526879", "#EAF3F6"


def lit(value):
    # Semantic-query literals are typed, unlike JSON geometry/theme numbers.
    if isinstance(value, bool):
        raw = str(value).lower()
    elif isinstance(value, (int, float)):
        raw = str(value) + "D"
    else:
        raw = "'" + str(value).replace("'", "''") + "'"
    return {"expr": {"Literal": {"Value": raw}}}


def color(value):
    return {"solid": {"color": lit(value)}}


def projection(table, column, measure=False, label=None, fmt=None):
    result = {"field": PP.field(table, column, measure), "queryRef": table + "." + column,
              "nativeQueryRef": label or column}
    if label:
        result["displayName"] = label
    if fmt:
        result["format"] = fmt
    return result


def visual(name, kind, x, y, w, h, title="", roles=None):
    v = PP.visual(name, kind, x, y, w, h, title, roles)
    vco = v["visual"]["visualContainerObjects"]
    vco["title"][0]["properties"].update(fontSize=lit(12), fontColor=color(INK),
                                           alignment=lit("left"))
    vco["subTitle"] = [{"properties": {"show": lit(False)}}]
    vco["padding"] = [{"properties": {k: lit(8) for k in ("top", "bottom", "left", "right")}}]
    vco["border"] = [{"properties": {"show": lit(False)}}]
    return v


def text(name, value, x, y, w, h, size=12, bold=False, ink=INK):
    v = visual(name, "textbox", x, y, w, h)
    v["visual"].pop("query")
    v["visual"]["objects"] = {"general": [{"properties": {"paragraphs": [{
        "textRuns": [{"value": value, "textStyle": {"fontFamily": "Segoe UI",
          "fontSize": str(size) + "pt", "fontWeight": "bold" if bold else "normal", "color": ink}}],
        "horizontalTextAlignment": "left"}]}}]}
    v["visual"]["visualContainerObjects"]["background"][0]["properties"]["show"] = lit(False)
    return v


def slicer(name, table, column, x, y, w, label, default=None, single=False, mode="Dropdown"):
    v = visual(name, "slicer", x, y, w, 128 if mode == "Between" else 88,
               roles={"Values": {"projections": [projection(table, column)]}})
    general = {"responsive": lit(False), "selfFilterEnabled": lit(True)}
    if default is not None:
        general["filter"] = {"filter": PP.category_filter(table, column,
            default if isinstance(default, list) else [default])}
    v["visual"]["objects"] = {
      "data": [{"properties": {"mode": lit(mode)}}],
      "general": [{"properties": general}],
      "header": [{"properties": {"show": lit(True), "text": lit(label),
                                  "textSize": lit(10), "fontColor": color(INK)}}],
      "items": [{"properties": {"textSize": lit(11), "fontColor": color(INK)}}],
      "selection": [{"properties": {"singleSelect": lit(single), "strictSingleSelect": lit(single),
                                      "selectAllCheckboxEnabled": lit(not single)}}]}
    v["visual"]["syncGroup"] = {"groupName": "NativeOnly " + table + "." + column,
                                  "fieldChanges": False, "filterChanges": True}
    return v


def button(name, label, x, y, w, bookmark):
    v = OLD.button(name, label, x, y, w, "Bookmark", bookmark, h=40)
    return normalize(v)


def native_table(name, x, y, w, h, fields, title="", headers=True):
    v = visual(name, "tableEx", x, y, w, h, title,
               {"Values": {"projections": [projection(*f) for f in fields]}})
    v["visual"]["objects"] = {
        "columnHeaders": [{"properties": {"show": lit(headers), "fontSize": lit(10), "backColor": color(PALE)}}],
        "values": [{"properties": {"fontSize": lit(10)}}],
        "grid": [{"properties": {"rowPadding": lit(3), "gridVertical": lit(False)}}],
        "total": [{"properties": {"totals": lit(False)}}]}
    return v


def matrix(name, x, y, w, h, rows, measure, label, summary=False):
    roles = {"Rows": {"projections": [projection(*row) for row in rows]},
             "Columns": {"projections": [projection("fm_native_periods", "Label", label="Review period")]},
             "Values": {"projections": [projection("fm_native_measures", measure, True, label)]}}
    if summary:
        roles["Columns"]["projections"].extend([
            projection("fm_native_columns", "Comparison", label="Comparison"),
            projection("fm_native_columns", "ValueLabel", label="Variance unit")])
    v = visual(name, "pivotTable", x, y, w, h, roles=roles)
    v["visual"]["objects"] = {
      "grid": [{"properties": {"rowPadding": lit(3), "gridVertical": lit(False), "gridHorizontal": lit(True)}}],
      "rowHeaders": [{"properties": {"stepped": lit(True), "fontSize": lit(10), "autoExpand": lit(True)}}],
      "columnHeaders": [{"properties": {"fontSize": lit(10), "backColor": color(PALE),
                                         "autoExpand": lit(True), "autoSizeColumnWidth": lit(True)}}],
      "values": [{"properties": {"fontSize": lit(10)}}],
      "subTotals": [{"properties": {"rowSubtotals": lit(False), "columnSubtotals": lit(False)}}]}
    v["visual"]["visualContainerObjects"]["stylePreset"] = [{"properties": {"name": lit("None")}}]
    v["visual"]["expansionStates"] = [{"roles": [role], "levels": [
      {"queryRefs": [q["queryRef"]], "identityKeys": [q["field"]], "isCollapsed": False}
      for q in data["projections"][:-1]]} for role, data in roles.items()
      if role in {"Rows", "Columns"} and len(data["projections"]) > 1]
    # Automatic ADS is a physical page filter in this preview. The original
    # numeric measures still enforce source/cohort completeness. Do not apply
    # a source-scanning visual MEASURE filter over the matrix crossjoin.
    return v


def normalize(value):
    """Repair semantic literals and enforce unique projection aliases per visual."""
    v = deepcopy(value)
    def walk(node):
        if isinstance(node, dict):
            raw = node.get("Literal", {}).get("Value")
            if isinstance(raw, str) and re.fullmatch(r"-?\d+(?:\.\d+)?", raw):
                node["Literal"]["Value"] = raw + "D"
            for child in node.values():
                walk(child)
        elif isinstance(node, list):
            for child in node:
                walk(child)
    walk(v)
    used = set()
    for role in v.get("visual", {}).get("query", {}).get("queryState", {}).values():
        for p in role.get("projections", []):
            base = p.get("nativeQueryRef", p["queryRef"])
            alias, n = base, 2
            while alias in used:
                alias, n = base + str(n), n + 1
            p["nativeQueryRef"] = alias
            used.add(alias)
            p.pop("active", None)
    return v


def page_filter(table, column, value):
    return {"name": "NativeOnly_" + table + "_" + column, "field": PP.field(table, column),
            "type": "Categorical", "filter": PP.category_filter(table, column, [value])}


def make_page(affiliate="UK", cycle="2026-10"):
    page = {"$schema": PP.SCHEMA + "page/2.1.0/schema.json", "name": "native_demand",
      "displayName": "Demand review", "displayOption": "FitToWidth", "width": 1440, "height": 2024,
      "filterConfig": {"filters": [page_filter("fm_native_file_mode", "Mode", "Automatic ADS"),
          page_filter("fm_native_scenario", "Mode", "Automatic ADS"),
          page_filter("fm_native_currency", "Currency", "Local")]}}
    vs = []
    def add(v):
        vs.append(v)
        return v
    add(text("heading", "ForecastMaster · Demand review", 20, 12, 1050, 44, 19, True))
    add(text("edition", "R17.3 TEST · Built-in Power BI visuals only", 20, 58, 1050, 32, 10, ink=MUTED))
    add(text("basis", "Automatic ADS · Source currency", 1100, 24, 320, 50, 10, ink=MUTED))
    dates = add(slicer("review_months", "fm_review_months", "Month", 20, 100, 560, "Review months", mode="Between"))
    dates["visual"]["objects"]["general"][0]["properties"]["filter"] = {"filter": OLD.date_filter(cycle[:4])}
    add(text("review_help", "Review months control the visible chart and available summary years. Set bounds to month starts.\nUse Power BI's zoom, Focus mode and Export data from the visual menu.",
             612, 110, 808, 104, 11, ink=MUTED))
    add(native_table("source_status", 20, 240, 1400, 56,
      [("fm_native_measures", "N Source Caption", True, "Saved sources")], headers=False))
    for name, table, column, x, label, default in [
        ("affiliate", "fm_review_files", "Country", 20, "Affiliate", affiliate),
        ("cycle", "fm_review_files", "DemandCycle", 304, "Demand cycle", cycle),
        ("section", "fm_native_metric", "Section", 588, "Section", "IMS / Market"),
        ("metric", "fm_native_metric", "MetricLabel", 872, "Measure", "Market"),
        ("display", "fm_native_display", "Display", 1156, "Display", "Units")]:
        add(slicer(name, table, column, x, 312, 264, label, default, single=True))
    add(text("scope_heading", "Growth drivers, sectors & review summary period", 20, 416, 1400, 36, 12, True))
    for name, table, column, x, label, default in [
        ("drivers", "fm_native_scope", "GrowthDriver", 20, "Growth drivers", None),
        ("tiers", "fm_native_scope", "SectorLabel", 492, "Forecast tiers", None),
        ("periods", "fm_native_periods", "Label", 964, "Review summary period", [cycle[:4]+" FY", cycle[:4]+" YTD", cycle[:4]+" YTG"])]:
        v = add(slicer(name, table, column, x, 464, 456, label, default))
        PP.measure_filter(v, "N Period Available" if name == "periods" else "N Scope Available")
        add(button(name + "_all", "Select all", x, 560, 112, "native_demand_" + name + "_all"))
        add(button(name + "_clear", "Clear all", x+124, 560, 112, "native_demand_" + name + "_clear"))
    add(text("headline_title", "Review summary · selected total", 20, 616, 1400, 32, 12, True))
    add(matrix("headline", 20, 656, 1400, 172, [("fm_native_headline", "Label", False, "Selection")],
               "N Headline Cell", "Selected total"))
    for name, table, column, x, w, label, default, single in [
        ("chart_trend", "fm_native_chart_trend", "Label", 20, 300, "Headline trend", "12M", True),
        ("trend", "fm_native_trend", "Label", 344, 500, "Trend comparisons", ["12M"], False),
        ("view", "fm_native_view", "View", 868, 552, "Chart view", "Total", True)]:
        add(slicer(name, table, column, x, 844, w, label, default, single))
    chart = normalize(PP.chart("native_chart", "demand", 20, 948, 1400, 380))
    chart["visual"]["query"]["queryState"]["Category"]["showAll"] = False
    # Keep the measure's dynamic %, currency and k/m formats. Disable a SECOND
    # visual axis scale; Auto had produced "0Mm" over already-scaled formats.
    chart["visual"]["objects"].update({
      "lineStyles": [{"properties": {"strokeWidth": lit(2), "lineChartType": lit("linear"),
                    "showMarker": lit(True), "markerShape": lit("circle"), "markerSize": lit(4)}}],
      "valueAxis": [{"properties": {"showAxisTitle": lit(False), "labelDisplayUnits": lit(1), "labelPrecision": lit(2)}}],
      "legend": [{"properties": {"show": lit(True), "position": lit("Bottom"), "fontSize": lit(9), "showTitle": lit(False)}}],
      "zoom": [{"properties": {"show": lit(True), "showLabels": lit(True), "showTooltip": lit(True)}}]})
    chart["visual"]["objects"].pop("zoomSlider", None)
    chart["visual"]["visualContainerObjects"]["title"][0]["properties"].update(fontSize=lit(12), text=lit("Monthly demand · actuals, forecast and trend"))
    chart["visual"]["visualContainerObjects"]["subTitle"] = [{"properties": {"show": lit(False)}}]
    PP.measure_filter(chart, "N Line Visible")
    add(chart)
    add(native_table("month_readout", 20, 1344, 1400, 56,
      [("fm_native_measures", "N Selected Month", True, "Selected month"),
       ("fm_native_measures", "N Selected Monthly", True, "Monthly total · selected scope")]))
    add(text("executive_title", "Executive summary", 20, 1416, 440, 40, 12, True))
    for i, (mode, rows) in enumerate({"drivers": [("fm_native_scope", "GrowthDriver", False, "Growth driver")],
         "sectors": [("fm_native_scope", "SectorLabel", False, "Sector – growth driver")],
         "both": [("fm_native_scope", "GrowthDriver", False, "Growth driver"), ("fm_native_scope", "Sector", False, "Sector")]}.items()):
        add(button("rows_" + mode, mode.title(), 1024 + i*132, 1416, 124, "table_" + mode))
        t = add(matrix("summary_" + mode, 20, 1472, 1400, 320, rows, "N Summary Cell", "Value", summary=True))
        if mode != "drivers":
            t["isHidden"] = True
    add(text("files_heading", "Saved files · current affiliate and demand cycle", 20, 1808, 1400, 36, 12, True))
    add(native_table("matching_files", 20, 1856, 1400, 144, [
      ("fm_review_files", "GrowthDriver", False, "Growth driver"),
      ("fm_review_files", "SourceFileName", False, "File"),
      ("fm_review_files", "IMSActualsThrough", False, "IMS actuals through", "mmm yyyy"),
      ("fm_review_files", "ExFactoryActualsThrough", False, "Ex-factory actuals through", "mmm yyyy")]))
    # File table is metadata information, not an implicit source override.
    page["visualInteractions"] = [{"source": source, "target": v["name"],
      "type": "DataFilter" if source == "native_chart" and v["name"] == "month_readout" else "NoFilter"}
      for source in ("native_chart", "matching_files") for v in vs if v["name"] != source]
    for i, v in enumerate(vs):
        v["position"].update(z=i, tabOrder=i)
    return page, [normalize(v) for v in vs]


def create(source_zip, destination):
    if destination.exists():
        raise ValueError("Use a new destination; preserve earlier reports.")
    if hashlib.sha256(source_zip.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError("Unexpected frozen R17.2 report ZIP.")
    with TemporaryDirectory() as tmp:
        with ZipFile(source_zip) as z:
            z.extractall(tmp)
        source = next(Path(tmp).glob("*.Report"))
        report = destination / (NAME + ".Report")
        shutil.copytree(source, report)
        root = report / "definition"
        # Hard deletion in the NEW copy only: no fallback, refresh custom visual,
        # preference controller, pbiviz package or custom resource registration.
        shutil.rmtree(report / "CustomVisuals", ignore_errors=True)
        shutil.rmtree(root / "pages")
        shutil.rmtree(root / "bookmarks")
        config = json.loads((root / "report.json").read_text())
        config.pop("publicCustomVisuals", None)
        config.pop("organizationCustomVisuals", None)
        config["resourcePackages"] = [p for p in config.get("resourcePackages", []) if p.get("type") != "CustomVisual"]
        # A JSON theme is native formatting, not executable visual code.
        for pkg in config["resourcePackages"]:
            if pkg["name"] == "RegisteredResources":
                pkg["items"] = [{"name": "ForecastMasterNativeOnlyR173", "path": "fm-native-only-r173-theme.json", "type": "CustomTheme"}]
        config["themeCollection"]["customTheme"]["name"] = "ForecastMasterNativeOnlyR173"
        shutil.rmtree(report / "StaticResources/RegisteredResources", ignore_errors=True)
        PP.write(report / "StaticResources/RegisteredResources/fm-native-only-r173-theme.json", {
          "name": "ForecastMaster native only", "dataColors": ["#096B76", "#3185A2", "#766B90", "#9D652A", "#527C47"],
          "background": "#FFFFFF", "foreground": INK, "tableAccent": TEAL,
          "textClasses": {"label": {"fontFace": "Segoe UI", "fontSize": 10, "color": INK},
                          "title": {"fontFace": "Segoe UI", "fontSize": 12, "color": INK}}})
        PP.write(root / "report.json", config)
        page, vs = make_page()
        page_root = root / "pages/native_demand"
        PP.write(page_root / "page.json", page)
        PP.write(root / "pages/pages.json", {"$schema": PP.SCHEMA + "pagesMetadata/1.0.0/schema.json",
                                               "pageOrder": ["native_demand"], "activePageName": "native_demand"})
        for v in vs:
            if v["visual"]["visualType"] not in BUILTINS:
                raise AssertionError("Non-native visual: " + v["name"])
            PP.write(page_root / "visuals" / v["name"] / "visual.json", v)
        bookmarks = []
        for name, table, column in [("drivers", "fm_native_scope", "GrowthDriver"),
                                  ("tiers", "fm_native_scope", "SectorLabel"), ("periods", "fm_native_periods", "Label")]:
            for clear in (False, True):
                bookmarks.append(OLD.selection_bookmark("native_demand", name, table, column, clear))
        for mode in ("drivers", "sectors", "both"):
            bookmarks.append(PP.visibility_bookmark("table_"+mode, "native_demand", ["summary_"+mode],
                ["summary_"+m for m in ("drivers", "sectors", "both") if m != mode]))
        for b in bookmarks:
            PP.write(root / "bookmarks" / (b["name"] + ".bookmark.json"), normalize(b))
        PP.write(root / "bookmarks/bookmarks.json", {"$schema": PP.SCHEMA + "bookmarksMetadata/1.0.0/schema.json",
                    "items": [{"name": b["name"]} for b in bookmarks]})
        PP.write(destination / (NAME + ".pbip"), {"$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
          "version": "1.0", "artifacts": [{"report": {"path": report.name}}], "settings": {"enableAutoRecovery": True}})
        assert (report / "definition.pbir").read_bytes() == (source / "definition.pbir").read_bytes()
        return {"Stage": "NATIVE_ONLY_DEMAND_PREVIEW", "FrozenSourceZIP": SOURCE_SHA256,
          "ModelChanged": False, "CompanyAmountsIncluded": False, "CustomVisualCount": 0,
          "TESTBindingPreserved": True, "NativeVisualCount": len(vs),
          "DesktopRendering": "PENDING", "CompanyQueries": "PENDING", "ProductionReplacement": "NOT QUALIFIED"}


def zip_project(project, output):
    with ZipFile(output, "w", ZIP_DEFLATED) as z:
        for p in sorted(project.rglob("*")):
            if p.is_file():
                z.write(p, p.relative_to(project).as_posix())


def create_sample(test_project, destination):
    """Same native report, using only the frozen fabricated engine fixture."""
    if destination.exists():
        raise ValueError("Use a new sample destination.")
    sample_name = "ForecastMaster Native Only R17.3 SAMPLE"
    shutil.copytree(test_project, destination)
    report = destination / (sample_name + ".Report")
    (destination / (NAME + ".Report")).rename(report)
    semantic = destination / (sample_name + ".SemanticModel")
    model_name = "ForecastMasterNativeSyntheticR173"
    # Load only our synthetic generator. It constructs every source table from
    # fabricated literals and never reads a company service or model.
    spec = importlib.util.spec_from_file_location("r173_sample_fixture", HERE.parent / "report-native-r17.2/tests/engine_fixture.py")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)
    database, *_ = fixture.build()
    database["name"] = database["id"] = model_name
    for table in database["model"]["tables"]:
        for partition in table.get("partitions", []):
            if partition["source"]["type"] != "calculated":
                raise AssertionError("A sample source is not a fabricated calculated table.")
    PP.write(semantic / "definition.pbism", {"version": "4.0", "settings": {}})
    PP.write(semantic / "model.bim", database)
    PP.write(report / "definition.pbir", {"version": "4.0", "datasetReference": {"byPath": {"path": "../" + semantic.name}}})
    project = json.loads((destination / (NAME + ".pbip")).read_text())
    project["artifacts"][0]["report"]["path"] = report.name
    (destination / (NAME + ".pbip")).unlink()
    PP.write(destination / (sample_name + ".pbip"), project)
    page = report / "definition/pages/native_demand"
    PP.write(page / "visuals/edition/visual.json", text("edition", "R17.3 SAMPLE · Fabricated data · Built-in visuals only", 20, 58, 1050, 32, 10, ink=MUTED))
    # Synthetic countries/drivers are explicit; no fake company data is implied.
    sample_affiliate = json.loads((page / "visuals/affiliate/visual.json").read_text())
    assert "UK" in json.dumps(sample_affiliate)
    result = {"Stage": "NATIVE_ONLY_FABRICATED_SAMPLE", "Data": "FABRICATED ONLY", "FabricConnection": False,
              "CustomVisualCount": 0, "DesktopOpeningAndRendering": "PENDING"}
    PP.write(destination / "PRESERVATION.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    result = create(args.source, args.destination)
    PP.write(args.destination / "PRESERVATION.json", result)
    print(json.dumps(result, indent=2))
