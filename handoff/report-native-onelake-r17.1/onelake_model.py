"""Isolated OneLake qualification model; no production API or storage writes.

The source tables stay Direct Lake. Calculated reporting metadata avoids SQL
views and keeps metadata refresh inside the semantic-model dependency graph.
References from calculated tables to Direct Lake are a receiving preview gate.
R17 business-measure differences remain open; this is not a parity release.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys

R17 = Path(__file__).resolve().parents[1] / "report-native-r17"
sys.path.insert(0, str(R17))
import native_model as nm


FILES = r'''
VAR _base = SELECTCOLUMNS('fm_review_files',
 "SourceRevisionID", [SourceRevisionID], "SourceFileName", [SourceFileName],
 "SourceRelativePath", [SourceRelativePath], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver],
 "IMSActualsThrough", [IMSActualsThrough], "ExFactoryActualsThrough", [ExFactoryActualsThrough],
 "PublicationStatus", [PublicationStatus], "FileLabel", [FileLabel])
VAR _stem = ADDCOLUMNS(_base, "_Stem",
 SUBSTITUTE(SUBSTITUTE(UPPER([SourceFileName]), ".XLSM", ""), ".XLSX", ""))
VAR _parsed = ADDCOLUMNS(_stem,
 "_Revision", VAR _s = [_Stem] VAR _p = SEARCH("_ADS_", _s, 1, 0)
  VAR _tail = TRIM(IF(_p > 0, MID(_s, _p + 5, LEN(_s))))
  VAR _digits = IF(LEFT(_tail, 1) IN {"+", "-"}, MID(_tail, 2, LEN(_tail)), _tail)
  VAR _valid = LEN(_digits) > 0 && COUNTROWS(FILTER(GENERATESERIES(1, MAX(1, LEN(_digits))),
   NOT (MID(_digits, [Value], 1) IN {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}))) = 0
  RETURN IF(_p > 0 && _valid, IFERROR(CONVERT(_tail, INTEGER), BLANK())),
 "_Imported", VAR _label = [FileLabel] VAR _p = SEARCH(" · Imported ", _label, 1, 0)
  VAR _tail = IF(_p > 0, MID(_label, _p + 12, LEN(_label)))
  VAR _end = SEARCH(" · ", _tail, 1, 0)
  VAR _iso = IF(_end > 0, LEFT(_tail, _end - 1), _tail)
  VAR _date = IFERROR(DATE(VALUE(LEFT(_iso, 4)), VALUE(MID(_iso, 6, 2)),
   VALUE(MID(_iso, 9, 2))), BLANK())
  VAR _time = IFERROR(TIME(VALUE(MID(_iso, 12, 2)), VALUE(MID(_iso, 15, 2)),
   VALUE(MID(_iso, 18, 2))), BLANK())
  VAR _zone = MAX(SEARCH("+", _iso, 20, 0), SEARCH("-", _iso, 20, 0))
  VAR _offset = IF(_zone > 0,
   IFERROR((VALUE(MID(_iso, _zone + 1, 2)) * 60 + VALUE(MID(_iso, _zone + 4, 2))) / 1440, 0), 0)
  VAR _fraction = IF(MID(_iso, 20, 1) = ".",
   IFERROR(VALUE("0" & MID(_iso, 20, IF(_zone > 0, _zone - 20,
    LEN(SUBSTITUTE(_iso, "Z", "")) - 19))) / 86400, 0), 0)
  RETURN IF(_p > 0 && NOT ISBLANK(_date) && NOT ISBLANK(_time),
   _date + _time + _fraction - IF(_zone > 0 && MID(_iso, MAX(1, _zone), 1) = "-", -_offset, _offset)))
VAR _versions = ADDCOLUMNS(_parsed,
 "ADSPriority", SWITCH(TRUE(),
  RIGHT([_Stem], 9) IN {"_PLAN_ADS", "_PLAN-ADS", "_PLAN ADS"}
   || RIGHT([_Stem], 8) = "_PLANADS", 3,
  RIGHT([_Stem], 4) = "_ADS", 2,
  NOT ISBLANK([_Revision]) && [_Revision] = INT([_Revision]), 1, 0),
 "ADSRevision", COALESCE([_Revision], 0),
 "Scenario", VAR _s = [_Stem] VAR _ims = SEARCH("_IMS", _s, 1, 0)
  VAR _start = IF(_ims > 0, SEARCH("_", _s, _ims + 4, 0), 0)
  RETURN IF(_start > 0, MID(_s, _start + 1, 200), _s))
VAR _ranked = ADDCOLUMNS(_versions,
 "PreferenceRank", VAR _c = [Country] VAR _cycle = [DemandCycle] VAR _driver = [GrowthDriver]
  VAR _p = [ADSPriority] VAR _r = [ADSRevision] VAR _i = [_Imported]
  RETURN 1 + COUNTROWS(DISTINCT(SELECTCOLUMNS(FILTER(_versions,
   [Country] = _c && [DemandCycle] = _cycle && [GrowthDriver] = _driver
   && ([ADSPriority] > _p || ([ADSPriority] = _p && [ADSRevision] > _r)
    || ([ADSPriority] = _p && [ADSRevision] = _r && [_Imported] > _i))),
   "P", [ADSPriority], "R", [ADSRevision], "I", [_Imported]))),
 "PreferenceTies", VAR _c = [Country] VAR _cycle = [DemandCycle] VAR _driver = [GrowthDriver]
  VAR _p = [ADSPriority] VAR _r = [ADSRevision] VAR _i = [_Imported]
  RETURN COUNTROWS(FILTER(_versions, [Country] = _c && [DemandCycle] = _cycle
   && [GrowthDriver] = _driver && [ADSPriority] = _p && [ADSRevision] = _r
   && [_Imported] == _i)))
RETURN SELECTCOLUMNS(_ranked,
 "SourceRevisionID", [SourceRevisionID], "SourceFileName", [SourceFileName],
 "SourceRelativePath", [SourceRelativePath], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver],
 "IMSActualsThrough", [IMSActualsThrough], "ExFactoryActualsThrough", [ExFactoryActualsThrough],
 "PublicationStatus", [PublicationStatus], "FileLabel", [FileLabel],
 "ADSPriority", [ADSPriority], "ADSRevision", [ADSRevision],
 "PreferenceRank", [PreferenceRank], "PreferenceTies", [PreferenceTies], "Scenario", [Scenario])
'''

SCOPE = r'''
VAR _pairs = DISTINCT(SELECTCOLUMNS('fm_review_facts',
 "_Source", [SourceRevisionID], "_Sector", COALESCE([Sector], "")))
VAR _files = SELECTCOLUMNS('fm_native_files',
 "SourceRevisionID", [SourceRevisionID], "Country", [Country],
 "DemandCycle", [DemandCycle], "GrowthDriver", [GrowthDriver])
RETURN GENERATE(_files, VAR _id = [SourceRevisionID] VAR _driver = [GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_pairs, [_Source] = _id),
 "Sector", [_Sector], "SectorLabel", IF(LEN([_Sector]) = 0, "No forecast tier", [_Sector]) & " – " & _driver))
'''

GROUPS = r'''
DISTINCT(UNION(
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Total",
  "ScopeDriver", "", "ScopeSector", "", "ScopeLabel", "Selected total", "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Drivers",
  "ScopeDriver", [GrowthDriver], "ScopeSector", "", "ScopeLabel", [GrowthDriver], "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Sectors",
  "ScopeDriver", [GrowthDriver], "ScopeSector", [Sector], "ScopeLabel", [SectorLabel], "IsSector", 1),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Both",
  "ScopeDriver", [GrowthDriver], "ScopeSector", "", "ScopeLabel", [GrowthDriver], "IsSector", 0),
 SELECTCOLUMNS('fm_native_scope', "DemandCycle", [DemandCycle], "ViewType", "Both",
  "ScopeDriver", [GrowthDriver], "ScopeSector", [Sector], "ScopeLabel", [SectorLabel], "IsSector", 1)))
'''

SCENARIO = r'''
UNION(ROW("Mode", "Automatic ADS", "Scenario", "Automatic ADS"),
 DISTINCT(SELECTCOLUMNS('fm_native_files', "Mode", "Selected files", "Scenario", [Scenario])))
'''

# The old SQL view multiplied every possible drag rank into the chart lines.
# A chart identity needs just RowID and Display; DAX checks the selected rows.
# Table ordering still uses the original state/rows tables, with all rank tokens.
LINES = r'''
VAR _groups = CROSSJOIN('fm_native_groups', 'fm_native_scenario')
VAR _demand = CROSSJOIN(_groups, 'fm_native_display',
 DATATABLE("K", INTEGER, {{0}, {1}, {6}, {12}, {24}}))
VAR _sop = CROSSJOIN(_groups, 'fm_native_catalog', DATATABLE("K", INTEGER, {{0}, {1}}))
RETURN UNION(
 SELECTCOLUMNS(_demand,
 "DemandCycle", [DemandCycle], "ViewType", [ViewType], "ScopeDriver", [ScopeDriver],
 "ScopeSector", [ScopeSector], "ScopeLabel", [ScopeLabel], "IsSector", [IsSector],
 "Mode", [Mode], "Scenario", [Scenario], "Chart", "demand", "Token", "none", "RowID", "",
 "Display", [Display], "LineKind", [K],
 "LineLabel", [DemandCycle] & " · " & [Scenario] & " · " & [ScopeLabel] & " · " &
 SWITCH([K], 0, "Actuals", 1, "Forecast", [K] & "M trend"), "LineSort", [K]),
 SELECTCOLUMNS(_sop,
 "DemandCycle", [DemandCycle], "ViewType", [ViewType], "ScopeDriver", [ScopeDriver],
 "ScopeSector", [ScopeSector], "ScopeLabel", [ScopeLabel], "IsSector", [IsSector],
 "Mode", [Mode], "Scenario", [Scenario], "Chart", "sop", "Token", "", "RowID", [RowID],
 "Display", [Display], "LineKind", [K],
 "LineLabel", [DemandCycle] & " · " & [Scenario] & " · " & [ScopeLabel] & " · " &
 [Channel] & " · " & IF(LEN([SubChannel]) = 0, "—", [SubChannel]) & " · " &
 [Measure] & " · " & IF([K] = 0, "Actuals", "Forecast"), "LineSort", [SourceOrder] * 100 + [K]))
'''

EXPRESSIONS = {"files": FILES, "scope": SCOPE, "groups": GROUPS,
               "scenario": SCENARIO, "lines": LINES}


def datatable(rows):
    """Constant-only DAX metadata. Never accepts a live data frame."""
    types = []
    for key, value in rows[0].items():
        types.extend([json.dumps(key), "INTEGER" if isinstance(value, int) else "STRING"])
    def cell(value):
        return str(value) if isinstance(value, int) else '"' + value.replace('"', '""') + '"'
    records = ["{" + ",".join(cell(row[key]) for key in rows[0]) + "}" for row in rows]
    return "DATATABLE(" + ",".join(types) + ",{\n" + ",\n".join(records) + "\n})"


def extend_onelake(database):
    """Pure additive transform. The caller creates a NEW model, never updates one."""
    original = database["model"]
    fact = next(t for t in original["tables"] if t["name"] == "fm_review_facts")
    if len(fact.get("partitions", [])) != 1:
        raise ValueError("Expected exactly one existing fact partition.")
    partition = fact["partitions"][0]
    source = partition.get("source", {})
    expression = next((e.get("expression", "") for e in original.get("expressions", [])
                       if e["name"] == source.get("expressionSource")), "")
    expression = "\n".join(expression) if isinstance(expression, list) else expression
    if (partition.get("mode") != "directLake" or source.get("type") != "entity"
            or "azurestorage.datalake" not in expression.lower()
            or any(x in expression.lower() for x in ("sql.database", "onelake.sqlanalytics"))):
        raise ValueError("This adapter requires the confirmed Direct Lake on OneLake route.")
    after = nm.extend_model(database)
    old_names = {t["name"] for t in original["tables"]}
    static = nm.static_tables()
    for table in after["model"]["tables"]:
        if table["name"] in old_names:
            continue
        short = table["name"].removeprefix("fm_native_")
        expression = EXPRESSIONS[short] if short in EXPRESSIONS else datatable(static[short])
        table["partitions"] = [{"name": table["name"], "mode": "import",
                                 "source": {"type": "calculated", "expression": expression}}]
        table["description"] = "OneLake R17.1 TEST metadata. Direct Lake calculated-table preview gate."
        for column in table.get("columns", []):
            column["type"] = "calculatedTableColumn"
            column["sourceColumn"] = "[" + column["name"] + "]"
    existing_relationships = deepcopy(original.get("relationships", []))
    added_relationships = after["model"]["relationships"][len(existing_relationships):]
    after["model"]["relationships"] = existing_relationships + [r for r in added_relationships
        if r.get("name") != "NativeR17-Lines-State"]
    measures = next(t for t in after["model"]["tables"] if t["name"] == "fm_native_measures")["measures"]
    chart = next(m for m in measures if m["name"] == "N Chart Monthly")
    old = '''VAR _token=SELECTEDVALUE('fm_native_lines'[Token])
VAR _selected=_type="demand" || _token IN SELECTCOLUMNS(ALLSELECTED('fm_native_state'),"T",'fm_native_state'[Token]) && ISFILTERED('fm_native_state'[Token])'''
    new = '''VAR _display=SELECTEDVALUE('fm_native_lines'[Display])
VAR _selected=_type="demand" || ISFILTERED('fm_native_state'[Token]) && COUNTROWS(
 FILTER(ALLSELECTED('fm_native_state'),'fm_native_state'[Kind]="row"
 &&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0'''
    if chart["expression"].count(old) != 1:
        raise ValueError("R17 chart selection contract changed; inspect before adapting.")
    chart["expression"] = chart["expression"].replace(old, new)
    # Verify all old model JSON values, including roles and original relationships.
    restored = deepcopy(after)
    restored["model"]["tables"] = [t for t in restored["model"]["tables"] if t["name"] in old_names]
    if "relationships" in original:
        restored["model"]["relationships"] = deepcopy(original["relationships"])
    else:
        restored["model"].pop("relationships", None)
    if restored != database:
        raise AssertionError("An existing model value changed.")
    return after
