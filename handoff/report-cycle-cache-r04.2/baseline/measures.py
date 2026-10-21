"""Native DAX measures for the connected Review meeting report."""
from textwrap import dedent

from contract import AXIS, FACTS, FILES, MEASURES, MODES, MONTHS, PERIODS, REFERENCE, SERIES

M = {}

def add(name, expression, fmt="#,0.0", folder="Forecast review", dynamic=False):
    M[name] = {"expression":dedent(expression).strip(),"formatString":fmt,"displayFolder":folder,"dynamic":dynamic}

add("FM Reference ID", f"""
    VAR _explicit = SELECTEDVALUE('{REFERENCE}'[SourceRevisionID])
    VAR _cohort = CALCULATETABLE(VALUES('{FILES}'[SourceRevisionID]), REMOVEFILTERS('{FILES}'[FileLabel]))
    VAR _fallback = SELECTEDVALUE('{FILES}'[SourceRevisionID])
    VAR _hasExplicit = ISFILTERED('{REFERENCE}'[FileLabel]) || ISFILTERED('{REFERENCE}'[SourceRevisionID])
    VAR _chosen = IF(_hasExplicit, _explicit, _fallback)
    RETURN IF(NOT ISBLANK(_chosen) && CONTAINS(_cohort, '{FILES}'[SourceRevisionID], _chosen), _chosen)
""", "", "Forecast review\\Context")
add("FM Metric Ready", f"IF(HASONEVALUE('{MEASURES}'[MetricKey]), 1, 0)", "0", "Forecast review\\Context")
add("FM Cohort Ready", f"""
    IF(HASONEVALUE('{FILES}'[Country]) && HASONEVALUE('{FILES}'[DemandCycle]) &&
        HASONEVALUE('{FILES}'[GrowthDriver]) && HASONEVALUE('{FILES}'[SourceProfile]), 1, 0)
""", "0", "Forecast review\\Context")
add("FM Cutoff", f"""
    VAR _id = [FM Reference ID]
    RETURN IF(ISBLANK(_id), BLANK(),
        IF(SELECTEDVALUE('{MEASURES}'[CutoffFamily]) = "EF",
            LOOKUPVALUE('{FILES}'[ExFactoryActualsThrough], '{FILES}'[SourceRevisionID], _id),
            LOOKUPVALUE('{FILES}'[IMSActualsThrough], '{FILES}'[SourceRevisionID], _id)))
""", "MMM yyyy", "Forecast review\\Context")
add("FM Evaluation Month", f"COALESCE(SELECTEDVALUE('{AXIS}'[Month]), SELECTEDVALUE('{MONTHS}'[Month]))", "MMM yyyy", "Forecast review\\Context")
add("FM Reference Option Visible", f"""
    VAR _id = SELECTEDVALUE('{REFERENCE}'[SourceRevisionID])
    VAR _cohort = CALCULATETABLE(VALUES('{FILES}'[SourceRevisionID]), REMOVEFILTERS('{FILES}'[FileLabel]))
    RETURN IF(NOT ISBLANK(_id) && CONTAINS(_cohort, '{FILES}'[SourceRevisionID], _id), 1, 0)
""", "0", "Forecast review\\Visibility")
add("FM Dimension Option Visible", f"""
    VAR _ids = VALUES('{FILES}'[SourceRevisionID])
    RETURN IF(CALCULATE(COUNTROWS('{FACTS}'), TREATAS(_ids, '{FACTS}'[SourceRevisionID])) > 0, 1, 0)
""", "0", "Forecast review\\Visibility")
add("FM Period In Range", f"""
    VAR _first = MINX(ALLSELECTED('{MONTHS}'), '{MONTHS}'[Month])
    VAR _last = MAXX(ALLSELECTED('{MONTHS}'), '{MONTHS}'[Month])
    VAR _year = SELECTEDVALUE('{PERIODS}'[Year])
    RETURN IF(NOT ISBLANK(_year) && _year >= YEAR(_first) && _year <= YEAR(_last), 1, 0)
""", "0", "Forecast review\\Visibility")
add("FM Chart Month Visible", f"""
    VAR _first = MINX(ALLSELECTED('{MONTHS}'), '{MONTHS}'[Month])
    VAR _last = MAXX(ALLSELECTED('{MONTHS}'), '{MONTHS}'[Month])
    VAR _cut = [FM Cutoff]
    VAR _start = IF(ISBLANK(_cut), _first, MIN(_first, EDATE(_cut, -11)))
    VAR _month = SELECTEDVALUE('{AXIS}'[Month])
    RETURN IF(NOT ISBLANK(_month) && _month >= _start && _month <= _last, 1, 0)
""", "0", "Forecast review\\Visibility")
add("FM Plan Selected", f"""
    VAR _kind = SELECTEDVALUE('{SERIES}'[SeriesKind])
    VAR _id = SELECTEDVALUE('{SERIES}'[SourceRevisionID])
    VAR _referenceOnly = SELECTEDVALUE('{MODES}'[Mode], "Selected files") = "Reference only"
    VAR _ids = VALUES('{FILES}'[SourceRevisionID])
    VAR _explicitSelection = ISFILTERED('{FILES}'[FileLabel])
    RETURN IF(_kind = "PLAN" && [FM Cohort Ready] = 1 &&
        IF(_referenceOnly, _id = [FM Reference ID], _explicitSelection && CONTAINS(_ids, '{FILES}'[SourceRevisionID], _id)), 1, 0)
""", "0", "Forecast review\\Visibility")
add("FM Raw Metric", f"""
    VAR _numKey = SELECTEDVALUE('{MEASURES}'[NumeratorKey])
    VAR _denKey = SELECTEDVALUE('{MEASURES}'[DenominatorKey])
    VAR _num = CALCULATE(SUM('{FACTS}'[Amount]), TREATAS({{_numKey}}, '{FACTS}'[ComponentKey]))
    VAR _den = CALCULATE(SUM('{FACTS}'[Amount]), TREATAS({{_denKey}}, '{FACTS}'[ComponentKey]))
    RETURN IF([FM Metric Ready] <> 1 || ISBLANK(_num), BLANK(),
        IF(SELECTEDVALUE('{MEASURES}'[Aggregation]) = "RATIO",
            IF(ISBLANK(_den), BLANK(), DIVIDE(_num, _den)), _num))
""", dynamic=True)
add("FM Reference Month", f"""
    VAR _id = [FM Reference ID]
    VAR _month = [FM Evaluation Month]
    RETURN IF(ISBLANK(_id) || ISBLANK(_month) || [FM Cohort Ready] <> 1, BLANK(),
        CALCULATE([FM Raw Metric], TREATAS({{_id}}, '{FACTS}'[SourceRevisionID]), TREATAS({{_month}}, '{FACTS}'[Month])))
""", dynamic=True)
add("FM Reference Weight", f"""
    VAR _id = [FM Reference ID]
    VAR _month = [FM Evaluation Month]
    VAR _key = SELECTEDVALUE('{MEASURES}'[DenominatorKey])
    VAR _weight = CALCULATE(SUM('{FACTS}'[Amount]), TREATAS({{_id}}, '{FACTS}'[SourceRevisionID]),
        TREATAS({{_month}}, '{FACTS}'[Month]), TREATAS({{_key}}, '{FACTS}'[ComponentKey]))
    RETURN IF(SELECTEDVALUE('{MEASURES}'[Aggregation]) <> "RATIO", 1,
        IF(ISBLANK(_weight), BLANK(), _weight))
""", folder="Forecast review\\Aggregation")

for length in (12,24):
    training = f"""
        VAR _cut = [FM Cutoff]
        VAR _first = EDATE(_cut, -{length-1})
        VAR _dates = FILTER(ALL('{AXIS}'), '{AXIS}'[Month] >= _first && '{AXIS}'[Month] <= _cut)
        VAR _points = ADDCOLUMNS(_dates, "__y", CALCULATE([FM Reference Month], REMOVEFILTERS('{MONTHS}')))
        VAR _valid = FILTER(_points, NOT ISBLANK([__y]))
    """
    for coefficient, column in (("Slope","Slope1"),("Intercept","Intercept")):
        add(f"FM {coefficient} {length}", training + f"""
            VAR _meanX = AVERAGEX(_valid, '{AXIS}'[MonthIndex])
            VAR _meanY = AVERAGEX(_valid, [__y])
            VAR _slope = DIVIDE(
                SUMX(_valid, ('{AXIS}'[MonthIndex]-_meanX)*([__y]-_meanY)),
                SUMX(_valid, POWER('{AXIS}'[MonthIndex]-_meanX,2)))
            RETURN IF(ISBLANK(_cut) || COUNTROWS(_valid) <> {length}, BLANK(),
                {'_slope' if coefficient=='Slope' else "_meanY - _slope * _meanX"})
        """, folder="Forecast review\\Regression")
    add(f"FM Trend {length} Month", f"""
        VAR _month = [FM Evaluation Month]
        VAR _cut = [FM Cutoff]
        VAR _a = [FM Intercept {length}]
        VAR _b = [FM Slope {length}]
        RETURN IF(ISBLANK(_month) || ISBLANK(_cut), BLANK(),
            IF(_month <= _cut, [FM Reference Month],
                IF(ISBLANK(_a) || ISBLANK(_b), BLANK(), _a + _b * DATEDIFF(DATE(2000,1,1), _month, MONTH))))
    """, dynamic=True)

add("FM Series Month", f"""
    VAR _kind = SELECTEDVALUE('{SERIES}'[SeriesKind])
    VAR _month = [FM Evaluation Month]
    VAR _cut = [FM Cutoff]
    VAR _id = SELECTEDVALUE('{SERIES}'[SourceRevisionID])
    RETURN IF(ISBLANK(_month) || ISBLANK(_cut) || [FM Cohort Ready] <> 1, BLANK(),
        SWITCH(_kind,
            "ACTUAL", IF(_month <= _cut, [FM Reference Month]),
            "TREND12", [FM Trend 12 Month],
            "TREND24", [FM Trend 24 Month],
            "PLAN", IF([FM Plan Selected] = 1,
                IF(_month <= _cut, [FM Reference Month],
                    CALCULATE([FM Raw Metric], TREATAS({{_id}}, '{FACTS}'[SourceRevisionID]), TREATAS({{_month}}, '{FACTS}'[Month]))))))
""", dynamic=True)
add("FM Series Weight", f"""
    VAR _kind = SELECTEDVALUE('{SERIES}'[SeriesKind])
    VAR _id = SELECTEDVALUE('{SERIES}'[SourceRevisionID])
    VAR _month = [FM Evaluation Month]
    VAR _key = SELECTEDVALUE('{MEASURES}'[DenominatorKey])
    VAR _usePlan = _kind = "PLAN" && _month > [FM Cutoff]
    VAR _weight = CALCULATE(SUM('{FACTS}'[Amount]), TREATAS({{_id}}, '{FACTS}'[SourceRevisionID]),
        TREATAS({{_month}}, '{FACTS}'[Month]), TREATAS({{_key}}, '{FACTS}'[ComponentKey]))
    RETURN IF(SELECTEDVALUE('{MEASURES}'[Aggregation]) <> "RATIO", 1,
        IF(_usePlan, IF(ISBLANK(_weight), BLANK(), _weight), [FM Reference Weight]))
""", folder="Forecast review\\Aggregation")
add("FM Chart Value", "[FM Series Month]", dynamic=True)

def aggregate_rows(dates, expression, actual_filter="", weight="[FM Reference Weight]"):
    return f"""
        VAR _dates = {dates}
        VAR _rows = ADDCOLUMNS(_dates,
            "__value", CALCULATE({expression}, REMOVEFILTERS('{MONTHS}')),
            "__weight", CALCULATE({weight}, REMOVEFILTERS('{MONTHS}')))
        VAR _eligible = {actual_filter or '_rows'}
        VAR _ratio = SELECTEDVALUE('{MEASURES}'[Aggregation]) = "RATIO"
        VAR _bad = COUNTROWS(FILTER(_eligible, ISBLANK([__value]) || (_ratio && ISBLANK([__weight]))))
        RETURN IF(COUNTROWS(_eligible) = 0 || _bad > 0, BLANK(),
            IF(_ratio, DIVIDE(SUMX(_eligible, [__value] * [__weight]), SUMX(_eligible, [__weight])), SUMX(_eligible, [__value])))
    """

add("FM Monthly Total", aggregate_rows(
    f"FILTER(ALL('{AXIS}'), '{AXIS}'[Month] IN VALUES('{MONTHS}'[Month]))",
    "[FM Series Month]",
    f"FILTER(_rows, SELECTEDVALUE('{SERIES}'[SeriesKind]) <> \"ACTUAL\" || '{AXIS}'[Month] <= [FM Cutoff])",
    weight="[FM Series Weight]"
), dynamic=True)
add("FM Monthly Value", f"IF(ISINSCOPE('{MONTHS}'[Month]), [FM Series Month], [FM Monthly Total])", dynamic=True)

for suffix,expression in (("Plan","[FM Series Month]"),("Trend 12M","[FM Trend 12 Month]"),("Trend 24M","[FM Trend 24 Month]")):
    add("FM Period " + suffix, f"""
        VAR _year = SELECTEDVALUE('{PERIODS}'[Year])
        VAR _kind = SELECTEDVALUE('{PERIODS}'[PeriodType])
        VAR _cut = [FM Cutoff]
        VAR _split = MONTH(_cut)
        VAR _first = DATE(_year, IF(_kind = "YTG", _split + 1, 1), 1)
        VAR _last = IF(_kind = "YTD", DATE(_year, _split, 1), DATE(_year,12,1))
        VAR _visible = [FM Period In Range] = 1 && [FM Plan Selected] = 1 && NOT ISBLANK(_cut) && NOT ISBLANK(_year)
        RETURN IF(NOT _visible || _first > _last, BLANK(),
            {aggregate_rows(f"FILTER(ALL('{AXIS}'), '{AXIS}'[Month] >= _first && '{AXIS}'[Month] <= _last)", expression, weight='[FM Series Weight]' if suffix=='Plan' else '[FM Reference Weight]')})
    """, dynamic=True)

for length in (12,24):
    add(f"FM Delta {length}", f"""
        VAR _plan = [FM Period Plan]
        VAR _trend = [FM Period Trend {length}M]
        RETURN IF(ISBLANK(_plan) || ISBLANK(_trend), BLANK(), _plan - _trend)
    """, dynamic=True)
    add(f"FM Delta {length} Percent", f"DIVIDE([FM Delta {length}], [FM Period Trend {length}M])", "+0.0%;-0.0%;0.0%")
    add(f"FM Delta {length} Display", f"""
        VAR _value = [FM Delta {length}]
        RETURN IF(ISBLANK(_value), BLANK(),
            IF(SELECTEDVALUE('{MEASURES}'[Unit]) = "%", FORMAT(_value*100, "+0.00;-0.00;0.00") & " pp",
                FORMAT(_value, "+#,0;-#,0;0")))
    """, "")

add("FM Report Context", f"""
    VAR _id = [FM Reference ID]
    VAR _filename = LOOKUPVALUE('{FILES}'[SourceFileName], '{FILES}'[SourceRevisionID], _id)
    VAR _status = LOOKUPVALUE('{FILES}'[PublicationStatus], '{FILES}'[SourceRevisionID], _id)
    VAR _unit = SELECTEDVALUE('{MEASURES}'[Unit])
    RETURN SWITCH(TRUE(), [FM Cohort Ready] <> 1, "Choose one affiliate, demand cycle and growth driver.",
        [FM Metric Ready] <> 1, "Choose one measure.",
        ISBLANK(_id), "Choose a reference file, or select one forecast file to use it as the reference.",
        "Actuals through " & FORMAT([FM Cutoff], "MMM yyyy") & "  |  " & _unit & "  |  " & _status & "  |  Reference: " & _filename)
""", "")
add("FM Chart Title", f"COALESCE(SELECTEDVALUE('{MEASURES}'[Measure]), \"Choose a measure\")", "")
add("FM Training Context", """
    VAR _cut = [FM Cutoff]
    RETURN IF(ISBLANK(_cut), BLANK(),
        "12M: " & FORMAT(EDATE(_cut,-11),"MMM yyyy") & "–" & FORMAT(_cut,"MMM yyyy") &
        "  |  24M: " & FORMAT(EDATE(_cut,-23),"MMM yyyy") & "–" & FORMAT(_cut,"MMM yyyy") &
        IF(ISBLANK([FM Slope 12]), "  |  12M requires complete actual history", "") &
        IF(ISBLANK([FM Slope 24]), "  |  24M requires complete actual history", ""))
""", "")
add("FM File Count", f"""
    VAR _n = COUNTROWS(VALUES('{FILES}'[SourceRevisionID]))
    RETURN FORMAT(_n,"0") & IF(ISFILTERED('{FILES}'[FileLabel]), " files selected", " matching files · choose files to plot")
""", "")
add("FM Method Note", """
    "FY = Jan–Dec · YTD = Jan–cutoff month · YTG = remaining months, repeated for each comparison year. " &
    "Monthly totals follow workbook numeric sums; blank members remain unreported. Shares use weighted totals; differences show pp and relative %. Entirely unreported months stay blank. " &
    "Trend is linear and may extend beyond normal bounds."
""", "")

DYNAMIC_FORMAT = f'SWITCH(SELECTEDVALUE(\'{MEASURES}\'[Unit]), "%", "0.00%", "£", "£#,0.0;£(#,0.0);£0", "#,0.0;(#,0.0);0")'

def tmdl_measure(name, definition, indent="\t\t"):
    expr = definition["expression"]
    lines = [indent + "measure '"+name.replace("'","''")+"' ="]
    lines.extend(indent+"\t\t"+line for line in expr.splitlines())
    if not definition["dynamic"]:
        lines.append(indent+"\tformatString: "+definition["formatString"] if definition["formatString"] else indent+'\tformatString: ""')
    lines.append(indent+"\tdisplayFolder: "+definition["displayFolder"])
    if definition["dynamic"]:
        lines.extend([indent+"\tformatStringDefinition =",indent+"\t\t\t"+DYNAMIC_FORMAT])
    return "\n".join(lines)

def model_script():
    return "createOrReplace\n\n\tref table '"+MEASURES+"'\n\n"+"\n\n".join(tmdl_measure(name,d) for name,d in M.items())+"\n"
