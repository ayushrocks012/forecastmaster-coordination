"""Bounded native TEST revision: pushdown filters and R16.6 period behavior.

No source data or production API calls. The receiving installer updates TEST only.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "report-native-onelake-r17.1"))
import onelake_model as om
nm = om.nm

PERIODS = r'''
VAR _years = DISTINCT(SELECTCOLUMNS('fm_review_axis', "Y", YEAR([Month])))
RETURN GENERATE(_years, VAR _year = [Y]
 RETURN SELECTCOLUMNS(DATATABLE("K", STRING, "S", INTEGER,
 {{"FY",0},{"YTD",1},{"YTG",2},{"H1",3},{"H2",4}}),
 "Year", _year, "PeriodType", [K], "PeriodKey", FORMAT(_year,"0") & ":" & [K],
 "Label", FORMAT(_year,"0") & " " & [K], "SortIndex", _year * 10 + [S]))
'''


def original_measures():
    """Exact frozen R17.1 expressions, without allocating its large static tables."""
    measures = {m["name"]: deepcopy(m) for m in nm.measures()}
    chart = measures["N Chart Monthly"]
    old = '''VAR _token=SELECTEDVALUE('fm_native_lines'[Token])
VAR _selected=_type="demand" || _token IN SELECTCOLUMNS(ALLSELECTED('fm_native_state'),"T",'fm_native_state'[Token]) && ISFILTERED('fm_native_state'[Token])'''
    new = '''VAR _display=SELECTEDVALUE('fm_native_lines'[Display])
VAR _selected=_type="demand" || ISFILTERED('fm_native_state'[Token]) && COUNTROWS(
 FILTER(ALLSELECTED('fm_native_state'),'fm_native_state'[Kind]="row"
 &&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0'''
    assert chart["expression"].count(old) == 1
    chart["expression"] = chart["expression"].replace(old, new)
    return measures


def revised_measures():
    measures = original_measures()
    for measure in measures.values():
        measure["expression"] = measure["expression"].replace("'fm_review_periods'", "'fm_native_periods'")
    # Filter only dimension dictionaries in the formula engine; let the storage
    # engine select Source/Month/Sector/Component before materialising member facts.
    old = '''VAR _facts=FILTER(ALL('fm_review_facts'),'fm_review_facts'[SourceRevisionID]=_id && 'fm_review_facts'[Month]=_date
   && 'fm_review_facts'[Sector]=_sec && (_channel="*" || 'fm_review_facts'[Channel]=_channel)
   && (_sub="*" || COALESCE('fm_review_facts'[SubChannel],"")=_sub)
   && (_channel<>"*" || 'fm_review_facts'[Channel] IN _selectedChannels && 'fm_review_facts'[SubChannel] IN _selectedSubs)
   && 'fm_review_facts'[ComponentKey]=_component)'''
    new = '''VAR _facts=CALCULATETABLE('fm_review_facts',REMOVEFILTERS('fm_review_facts'),
   TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),
   TREATAS({_sec},'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),
   FILTER(ALL('fm_review_facts'[Channel]),IF(_channel="*",'fm_review_facts'[Channel] IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),
   FILTER(ALL('fm_review_facts'[SubChannel]),IF(_sub="*",'fm_review_facts'[SubChannel] IN _selectedSubs,COALESCE('fm_review_facts'[SubChannel],"")=_sub)))'''
    for name in ("N Monthly Numerator", "N Monthly Denominator"):
        assert measures[name]["expression"].count(old) == 1
        measures[name]["expression"] = measures[name]["expression"].replace(old, new)
        text=measures[name]["expression"]
        start=text.index(" VAR _sectors=",text.index("VAR _members="))
        end=text.index("VAR _available=",start)
        # One fact retrieval per file/month/component, then group the already
        # filtered rows by sector. Missing checks remain PER SECTOR; a bad leaf
        # is excluded from an aggregate, never changed into numeric zero.
        text=text[:start]+''' VAR _sectors=SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"Sector",'fm_native_scope'[Sector])
 VAR _memberFacts=CALCULATETABLE('fm_review_facts',REMOVEFILTERS('fm_review_facts'),
  TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),
  TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),
  FILTER(ALL('fm_review_facts'[Channel]),IF(_channel="*",'fm_review_facts'[Channel] IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),
  FILTER(ALL('fm_review_facts'[SubChannel]),IF(_sub="*",'fm_review_facts'[SubChannel] IN _selectedSubs,COALESCE('fm_review_facts'[SubChannel],"")=_sub)))
 VAR _bySector=GROUPBY(_memberFacts,'fm_review_facts'[Sector],
  "RawAmount",SUMX(CURRENTGROUP(),'fm_review_facts'[Amount]),
  "BadCells",SUMX(CURRENTGROUP(),INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount]))))
 RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),
  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),
  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && (ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))
''' + text[end:]
        measures[name]["expression"]=text
    measures["N Scope Available"]["expression"] = nm.SOURCES + '''VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)
VAR _candidateIds=SELECTCOLUMNS(_admitted,"ID",'fm_native_files'[SourceRevisionID])
RETURN IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN _candidateIds))>0,1)'''
    measures["N Catalog Available"]["expression"] = nm.SOURCES + '''VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)
VAR _candidateIds=SELECTCOLUMNS(_admitted,"ID",'fm_native_files'[SourceRevisionID])
VAR _component=SELECTEDVALUE('fm_native_catalog'[Component])
VAR _channel=SELECTEDVALUE('fm_native_catalog'[Channel])
VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])
RETURN IF(CALCULATE(COUNTROWS('fm_review_facts'),REMOVEFILTERS('fm_review_facts'),
 TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS({_component},'fm_review_facts'[ComponentKey]),
 TREATAS({_channel},'fm_review_facts'[Channel]),
 FILTER(ALL('fm_review_facts'[SubChannel]),COALESCE('fm_review_facts'[SubChannel],"")=_sub))>0,1)'''
    # Keep the original metadata-only cohort guard on scenario visibility. It
    # suppresses unselected saved versions even in native visual filter queries.
    # R16.6 period masks apply the earliest saved cutoff MONTH to the named year.
    # A mixed-cutoff trend fit remains unavailable, matching live.scopeFit.
    measures["N Fit Cutoff"] = deepcopy(measures["N Cutoff"])
    measures["N Fit Cutoff"]["name"] = "N Fit Cutoff"
    measures["N Cutoff"]["expression"] = measures["N Cutoff"]["expression"].replace(
        "_sourceOK && COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff])",
        "_sourceOK && COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])))=0,MINX(_dates,[Cutoff])")
    measures["N Trend Monthly"]["expression"] = measures["N Trend Monthly"]["expression"].replace(
        "VAR _cut=[N Cutoff]", "VAR _cut=[N Fit Cutoff]")
    windows = '''VAR _y=SELECTEDVALUE('fm_native_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N Cutoff]
VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)
VAR _namedCut=DATE(_y,MONTH(_cut),1)
VAR _start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)
VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)
'''
    for name in ("N Period Months", "N Plan", "N Benchmark", "N Growth %"):
        text = measures[name]["expression"]
        if name == "N Growth %":
            end = text.index("VAR _count=")
        elif name == "N Period Months":
            end = text.index("RETURN IF(")
        else:
            end = text.index("VAR _count=")
        measures[name]["expression"] = windows + text[end:]
    measures["N Benchmark"]["expression"] = measures["N Benchmark"]["expression"].replace(
        "RETURN IF(NOT ISBLANK(_y)", "RETURN IF(NOT ISBLANK([N Fit Cutoff])&&NOT ISBLANK(_y)")
    measures["N Variance %"]["expression"] = "DIVIDE([N Variance],ABS([N Benchmark]))"
    actual_only = '''VAR _year=SELECTEDVALUE('fm_native_periods'[Year])
VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N Cutoff]
VAR _end=SWITCH(_kind,"YTD",DATE(_year,MONTH(_cut),1),"H1",DATE(_year,6,1),DATE(_year,12,1))
VAR _actualOnly=NOT ISBLANK(_cut)&&NOT ISBLANK(_year)&&_end<=_cut
'''
    measures["N Actual Only"] = dict(name="N Actual Only",expression=actual_only+"RETURN INT(_actualOnly)",
                                     formatString="0",displayFolder="Native review",isHidden=True)
    for name in ("N Headline Variance", "N Headline Variance %"):
        text = measures[name]["expression"]
        start = text.index("VAR _year=")
        end = text.index("RETURN IF(")
        text = text[:start] + "VAR _actual=[N Actual Only]=1\n" + text[end:]
        measures[name]["expression"] = text
    text = measures["N Summary Cell"]["expression"]
    start = text.index("VAR _actualOnly=")
    end = text.index("RETURN IF(")
    measures["N Summary Cell"]["expression"] = text[:start] + "VAR _actualOnly=[N Actual Only]=1\n" + text[end:]
    # Multiple table trend choices now also overlay the requested chart trends.
    measures["N Chart Monthly"]["expression"] = measures["N Chart Monthly"]["expression"].replace(
        "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)", "_kind IN VALUES('fm_native_trend'[Window])")
    # The line-label crossjoin is filtered cheaply before evaluating monthly data.
    measures["N Line Visible"] = dict(name="N Line Visible",expression='''VAR _view=SELECTEDVALUE('fm_native_lines'[ViewType])
VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])
VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])
VAR _cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])
VAR _chart=SELECTEDVALUE('fm_native_lines'[Chart])
RETURN IF(_view IN VALUES('fm_native_view'[View])
 && _mode=SELECTEDVALUE('fm_native_file_mode'[Mode],"Automatic ADS")
 && _cycle IN VALUES('fm_review_files'[DemandCycle])
 && (_chart="sop" || _kind IN {0,1} || _kind IN VALUES('fm_native_trend'[Window])),1)''',
        formatString="0",displayFolder="Native review",isHidden=True)
    # A native monthly readout can receive a chart point's category selection.
    measures["N Selected Month"] = dict(name="N Selected Month",expression='''IF(HASONEVALUE('fm_review_axis'[Month]),
 FORMAT(SELECTEDVALUE('fm_review_axis'[Month]),"mmm yyyy"))''',displayFolder="Native review",isHidden=True)
    measures["N Selected Monthly"] = deepcopy(measures["N Monthly"])
    measures["N Selected Monthly"].update(name="N Selected Monthly",expression="IF(HASONEVALUE('fm_review_axis'[Month]),[N Monthly])")
    measures["N Headline Cell"] = deepcopy(measures["N Plan"])
    measures["N Headline Cell"].update(name="N Headline Cell",expression='''SWITCH(SELECTEDVALUE('fm_native_headline'[Key]),
 "plan",[N Plan],"variance",[N Headline Variance],"pct",[N Headline Variance %])''')
    measures["N Measure Caption"] = dict(name="N Measure Caption",expression='''VAR _name=SELECTEDVALUE('fm_native_metric'[MetricLabel],"Selected measures")
RETURN IF(CONTAINSSTRING(_name,"%"),_name,_name & IF([N Display]="Value"," value"," units"))''',
        displayFolder="Native review",isHidden=True)
    measures["N Group Visible"] = dict(name="N Group Visible",expression='''VAR _cycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])
VAR _gd=SELECTEDVALUE('fm_native_groups'[ScopeDriver]) VAR _sec=SELECTEDVALUE('fm_native_groups'[ScopeSector])
VAR _sector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1
VAR _scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)
 &&(NOT _sector||'fm_native_scope'[Sector]=_sec))
RETURN IF(_cycle IN VALUES('fm_review_files'[DemandCycle])&&COUNTROWS(_scope)>0,1)''',
        displayFolder="Native review",formatString="0",isHidden=True)
    for name in ("N SOP Plan","N SOP Run Rate","N SOP Growth %","N SOP Monthly","N SOP Monthly Growth %"):
        body = measures[name]["expression"]
        measures[name]["expression"] = '''VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])
VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])
VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1
VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])
VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),
 (LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)
 &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))
VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),
 NOT HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)
RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group Visible]<>1,BLANK(),CALCULATE(
''' + body + ''',KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))'''
    for measure in measures.values():
        if "formatStringDefinition" not in measure:
            continue
        measure["formatStringDefinition"]["expression"] = '''VAR _row=COALESCE(SELECTEDVALUE('fm_native_rows'[RowID]),SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _pct=RIGHT(SELECTEDVALUE('fm_native_columns'[ColumnKey],""),3)="pct"
 || SELECTEDVALUE('fm_native_headline'[Key])="pct"
VAR _countries=VALUES('fm_review_files'[Country])
VAR _ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] IN _countries),'fm_native_currency_map'[Currency])
VAR _symbol=IF([N Display]="Units","",IF(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="USD","$",
 SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))
VAR _value=ABS(SELECTEDMEASURE())
VAR _number=SWITCH(TRUE(),_value>=1000000,"#,0.00,," & UNICHAR(34)&"m"&UNICHAR(34),
 _value>=1000,"#,0.0," & UNICHAR(34)&"k"&UNICHAR(34),"#,0")
RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'''
    return measures


def expression_hash(expression):
    text = "\n".join(expression) if isinstance(expression, list) else expression
    return hashlib.sha256(text.strip().replace("\r\n","\n").encode()).hexdigest()


def period_table():
    columns = [("Y","int64"),("Year","int64"),("PeriodType","string"),
               ("PeriodKey","string"),("Label","string"),("SortIndex","int64")]
    return {"name":"fm_native_periods","description":"R17.2 native FY/YTD/YTG/H1/H2 metadata; amounts remain in original facts.",
            "columns":[dict(name=n,dataType=t,type="calculatedTableColumn",sourceColumn="["+n+"]",summarizeBy="none",
                            **({"sortByColumn":"SortIndex"} if n=="Label" else {})) for n,t in columns],
            "partitions":[{"name":"fm_native_periods","mode":"import","source":{"type":"calculated","expression":PERIODS}}]}


def headline_table():
    return {"name":"fm_native_headline","columns":[
        {"name":"Key","dataType":"string","type":"calculatedTableColumn","sourceColumn":"[Key]","summarizeBy":"none"},
        {"name":"Label","dataType":"string","type":"calculatedTableColumn","sourceColumn":"[Label]","summarizeBy":"none","sortByColumn":"Sort"},
        {"name":"Sort","dataType":"int64","type":"calculatedTableColumn","sourceColumn":"[Sort]","summarizeBy":"none"}],
        "partitions":[{"name":"fm_native_headline","mode":"import","source":{"type":"calculated","expression":
         'DATATABLE("Key",STRING,"Label",STRING,"Sort",INTEGER,{{"plan","Plan",0},{"variance","Overcall / Undercall",1},{"pct","Variance %",2}})'}}]}


def patch_database(database):
    after = deepcopy(database)
    tables = {t["name"]:t for t in after["model"]["tables"]}
    if "fm_native_measures" not in tables or "fm_native_lines" not in tables:
        raise ValueError("Expected the installed R17.1 TEST; no update.")
    old = original_measures()
    revised = revised_measures()
    current = {m["name"]:m for m in tables["fm_native_measures"]["measures"]}
    changes = []
    for name, replacement in revised.items():
        if name in current:
            value = current[name]
            new = deepcopy(value)
            new["expression"] = replacement["expression"]
            if "formatStringDefinition" in replacement:
                new["formatStringDefinition"] = deepcopy(replacement["formatStringDefinition"])
            if value == new:
                continue
            if name not in old or expression_hash(value["expression"]) != expression_hash(old[name]["expression"]):
                raise ValueError("Unknown native measure expression; inspect before applying: " + name)
            value.update(new)
        else:
            tables["fm_native_measures"]["measures"].append(deepcopy(replacement))
        changes.append(name)
    for expected in (period_table(),headline_table()):
        if expected["name"] in tables:
            existing = tables[expected["name"]]
            if expression_hash(existing["partitions"][0]["source"]["expression"]) != expression_hash(expected["partitions"][0]["source"]["expression"]):
                raise ValueError("Unexpected existing native helper; no update.")
        else:
            after["model"]["tables"].append(expected)
            changes.append(expected["name"])
    relationship = {"name":"NativeR172-Groups-View","fromTable":"fm_native_groups","fromColumn":"ViewType",
                    "toTable":"fm_native_view","toColumn":"View"}
    matches = [r for r in after["model"].get("relationships",[]) if r["name"]==relationship["name"]]
    if matches and any(matches[0].get(k)!=v for k,v in relationship.items()):
        raise ValueError("Unexpected native grouping relationship; no update.")
    if not matches:
        after["model"].setdefault("relationships",[]).append(relationship)
        changes.append(relationship["name"])
    # Restrict changes to this measure table and the single new native helper.
    restored = deepcopy(after)
    original = {t["name"]:t for t in database["model"]["tables"]}
    restored["model"]["tables"] = [deepcopy(original[t["name"]]) if t["name"]=="fm_native_measures" else t
        for t in restored["model"]["tables"] if t["name"] not in {"fm_native_periods","fm_native_headline"} or t["name"] in original]
    if not any(r["name"]==relationship["name"] for r in database["model"].get("relationships",[])):
        restored["model"]["relationships"] = [r for r in restored["model"].get("relationships",[]) if r["name"]!=relationship["name"]]
        if "relationships" not in database["model"]:
            restored["model"].pop("relationships",None)
    if restored != database:
        raise AssertionError("Unrelated model change; no update.")
    return after, changes
