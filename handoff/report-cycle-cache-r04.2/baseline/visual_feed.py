"""Aggregate-only native data feed for the coordinated Review meeting visual."""
from contract import *
from measures import M, add

def quoted(expression):
    # JSON string escaping in DAX; no source text becomes executable markup.
    e=expression
    for a,b in [("UNICHAR(92)","UNICHAR(92) & UNICHAR(92)"),("UNICHAR(34)","UNICHAR(92) & UNICHAR(34)"),("UNICHAR(13)",'""'),("UNICHAR(10)",'UNICHAR(92) & "n"'),("UNICHAR(9)",'UNICHAR(92) & "t"')]:
        e=f"SUBSTITUTE({e}, {a}, {b})"
    return f"UNICHAR(34) & {e} & UNICHAR(34)"

def obj(fields):
    parts=[]
    for key,value in fields.items():
        parts.append(f'"""{key}"":" & {value}')
    return '"{" & '+ ' & "," & '.join(parts)+' & "}"'

folder="Forecast review\\Visual feed"
for suffix,column,keyfield in [('Numerator','Amount','NumeratorKey'),('Denominator','Amount','DenominatorKey'),('Numerator Missing','MissingCells','NumeratorKey'),('Denominator Missing','MissingCells','DenominatorKey')]:
    add('FM UI '+suffix, f"""
        VAR _id = SELECTEDVALUE('{FILES}'[SourceRevisionID])
        VAR _month = SELECTEDVALUE('{AXIS}'[Month])
        VAR _key = SELECTEDVALUE('{MEASURES}'[{keyfield}])
        VAR _allowed = CONTAINS(VALUES('{REFERENCE}'[SourceRevisionID]), '{REFERENCE}'[SourceRevisionID], _id)
        RETURN IF(_allowed && NOT ISBLANK(_key) && HASONEVALUE('{MEASURES}'[MetricKey]),
            CALCULATE(SUM('{FACTS}'[{column}]), TREATAS({{_id}}, '{FACTS}'[SourceRevisionID]),
                TREATAS({{_month}}, '{FACTS}'[Month]), TREATAS({{_key}}, '{FACTS}'[ComponentKey])))
    """,'0.############',folder)

file_fields={k:quoted(f"COALESCE(SELECTEDVALUE('{FILES}'[{col}]), \"\")") for k,col in {'id':'SourceRevisionID','fullLabel':'FileLabel','filename':'SourceFileName','path':'SourceRelativePath','affiliate':'Country','cycle':'DemandCycle','driver':'GrowthDriver','profile':'SourceProfile','status':'PublicationStatus'}.items()}
for k,c in [('ims','IMSActualsThrough'),('ef','ExFactoryActualsThrough')]:
    file_fields[k]=quoted(f"FORMAT(SELECTEDVALUE('{FILES}'[{c}]), \"yyyy-MM\")")
add('FM UI File',f"""
    VAR _month = SELECTEDVALUE('{AXIS}'[Month])
    VAR _first = MINX(ALL('{AXIS}'), '{AXIS}'[Month])
    RETURN IF(_month = _first, {obj(file_fields)})
""",'',folder)

first=f"""VAR _firstMonth = MINX(ALL('{AXIS}'), '{AXIS}'[Month])
VAR _firstFile = MINX(ALL('{FILES}'), '{FILES}'[SourceRevisionID])
VAR _first = SELECTEDVALUE('{AXIS}'[Month]) = _firstMonth && SELECTEDVALUE('{FILES}'[SourceRevisionID]) = _firstFile
"""
metric_fields={k:quoted(f"'{MEASURES}'[{c}]") for k,c in {'id':'MetricKey','family':'Section','label':'Measure','unit':'Unit','aggregation':'Aggregation','cutoffFamily':'CutoffFamily','numeratorKey':'NumeratorKey','denominatorKey':'DenominatorKey'}.items()}
metric_fields['availabilityIndex']=f"FORMAT(RANKX(ALL('{MEASURES}'), '{MEASURES}'[MetricKey], , ASC, DENSE) - 1, \"0\")"
add('FM UI Catalog',first+f"""
RETURN IF(_first, "[" & CONCATENATEX(ALL('{MEASURES}'), {obj(metric_fields)}, ",", '{MEASURES}'[SortIndex], ASC) & "]")
""",'',folder)
context={k:quoted(f"CALCULATE(SELECTEDVALUE('{t}'[{c}], \"{default}\"), ALLSELECTED('{t}'))") for k,t,c,default in [('affiliate',REFERENCE,'Country',''),('profile',REFERENCE,'SourceProfile',''),('metric',MEASURES,'MetricKey',''),('channel',FACTS,'Channel','all'),('subchannel',FACTS,'SubChannel','all'),('sector',FACTS,'Sector','all')]}
context['schema']='"4"'
# Retain scalar fields for existing R03.2 reports during the model/visual rollout.
# They are blank for a genuine multiple selection; R04 uses the arrays below.
for name,col in [('cycle','DemandCycle'),('driver','GrowthDriver')]:
    context[name]=quoted(f"CALCULATE(SELECTEDVALUE('{REFERENCE}'[{col}], \"\"), ALLSELECTED('{REFERENCE}'))")
for name,col in [('cycles','DemandCycle'),('drivers','GrowthDriver')]:
    context[name]=f'''"[" & CONCATENATEX(SUMMARIZE(ALLSELECTED('{REFERENCE}'), '{REFERENCE}'[{col}]), {quoted(f"'{REFERENCE}'[{col}]")}, ",", '{REFERENCE}'[{col}], ASC) & "]"'''
# ISFILTERED distinguishes All from a cohort that happens to contain one dimension value.
for k,c in [('channel','Channel'),('subchannel','SubChannel'),('sector','Sector')]:
    context[k]=quoted(f"IF(ISFILTERED('{FACTS}'[{c}]), SELECTEDVALUE('{FACTS}'[{c}], \"all\"), \"all\")")
add('FM UI Context',first+f"""
RETURN IF(_first, {obj(context)})
""",'',folder)
dims_fields={k:quoted(f"'{FACTS}'[{c}]") for k,c in [('channel','Channel'),('subchannel','SubChannel'),('sector','Sector')]}
dims_fields['metrics']='"[" & [__metrics] & "]"'
dims=obj(dims_fields)
add('FM UI Dimensions',first+f"""
VAR _ids = DISTINCT(SELECTCOLUMNS(ALLSELECTED('{REFERENCE}'), "ID", '{REFERENCE}'[SourceRevisionID]))
VAR _dimensions = CALCULATETABLE(SUMMARIZE('{FACTS}', '{FACTS}'[Channel], '{FACTS}'[SubChannel], '{FACTS}'[Sector]),
    REMOVEFILTERS('{FACTS}'[Channel], '{FACTS}'[SubChannel], '{FACTS}'[Sector]), TREATAS(_ids, '{FACTS}'[SourceRevisionID]))
VAR _rows = ADDCOLUMNS(_dimensions, "__metrics",
    CONCATENATEX(FILTER(ALL('{MEASURES}'),
        VAR _numKey = '{MEASURES}'[NumeratorKey]
        VAR _denKey = '{MEASURES}'[DenominatorKey]
        VAR _reportedNumerator = CALCULATE(SUM('{FACTS}'[NumericCells]),
            TREATAS(_ids, '{FACTS}'[SourceRevisionID]), TREATAS({{_numKey}}, '{FACTS}'[ComponentKey]))
        VAR _reportedDenominator = CALCULATE(SUM('{FACTS}'[NumericCells]),
            TREATAS(_ids, '{FACTS}'[SourceRevisionID]), TREATAS({{_denKey}}, '{FACTS}'[ComponentKey]))
        RETURN _reportedNumerator > 0 && ('{MEASURES}'[Aggregation] <> "RATIO" || _reportedDenominator > 0)),
        FORMAT(RANKX(ALL('{MEASURES}'), '{MEASURES}'[MetricKey], , ASC, DENSE) - 1, "0"), ","))
RETURN IF(_first, "[" & CONCATENATEX(_rows, {dims}, ",") & "]")
""",'',folder)
bounds = {k:quoted(f"FORMAT({func}X(ALL('{AXIS}'), '{AXIS}'[Month]), \"yyyy-MM\")") for k,func in [('first','MIN'),('last','MAX')]}
add('FM UI Bounds',first+f"RETURN IF(_first, {obj(bounds)})",'',folder)

# A custom visual may filter only fields advertised by its query. These grouping
# columns declare the scope and the aggregate dimension grain. Before an explicit
# cohort/metric is selected, only inventory metadata is returned, never all facts.
_scope=[(REFERENCE,c) for c in ['Country','DemandCycle','GrowthDriver','SourceProfile']]+[(MEASURES,'MetricKey')]
anchor=f"CONTAINS(VALUES('{REFERENCE}'[SourceRevisionID]), '{REFERENCE}'[SourceRevisionID], MINX(ALLSELECTED('{REFERENCE}'), '{REFERENCE}'[SourceRevisionID])) && SELECTEDVALUE('{MEASURES}'[MetricKey]) = MINX(ALLSELECTED('{MEASURES}'), '{MEASURES}'[MetricKey])"
ready=' && '.join(f"CALCULATE(DISTINCTCOUNT('{t}'[{c}]), ALLSELECTED('{t}')) = 1" for t,c in [(REFERENCE,'Country'),(REFERENCE,'SourceProfile'),(MEASURES,'MetricKey')])
for name in list(M):
    if name.startswith('FM UI '):
        expression=M[name]['expression']
        condition=ready if name in ['FM UI Numerator','FM UI Denominator','FM UI Numerator Missing','FM UI Denominator Missing'] else anchor
        M[name]['expression']='VAR _scopeAllowed = '+condition+'\nRETURN IF(_scopeAllowed,\n'+expression+'\n)'
