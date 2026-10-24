"""Report-local presentation metadata for the single custom overlay.

Reuses N Cutoff with the exact N Chart Monthly scope. Named period boundaries
match N Plan / N Period Months; no amounts, ratios or regressions are computed.
"""

NAME = 'N Overlay Context'
EXPRESSION = '''IF(NOT ISBLANK([N Chart Monthly]),
VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver])
VAR _sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])
VAR _sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1
VAR _cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])
VAR _scope=FILTER(ALLSELECTED('fm_native_scope'),
 (LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)
 &&(NOT _sectorLevel||'fm_native_scope'[Sector]=_sec))
VAR _cut=CALCULATE([N Cutoff],KEEPFILTERS(_scope),
 TREATAS({_cycle},'fm_review_files'[DemandCycle]))
VAR _metric=SELECTEDVALUE('fm_native_metric'[RowID])
VAR _display=[N Display]
VAR _countries=VALUES('fm_review_files'[Country])
VAR _currencies=DISTINCT(SELECTCOLUMNS(FILTER('fm_native_currency_map',
 'fm_native_currency_map'[Country] IN _countries),"Code",'fm_native_currency_map'[Currency]))
VAR _unit=IF(_metric="share","%",IF(_display="Units","Units",
 IF(SELECTEDVALUE('fm_native_currency'[Currency],"USD")="USD","USD",
 IF(COUNTROWS(_currencies)=1,MAXX(_currencies,[Code]),"Value"))))
VAR _q=UNICHAR(34)
VAR _periods=CONCATENATEX(ALLSELECTED('fm_native_periods'),
 VAR _y='fm_native_periods'[Year]
 VAR _kind='fm_native_periods'[PeriodType]
 VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)
 VAR _namedCut=DATE(_y,MONTH(_cut),1)
 VAR _start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)
 VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)
 RETURN "{"&_q&"id"&_q&":"&_q&'fm_native_periods'[PeriodKey]&_q&","&
 _q&"start"&_q&":"&_q&FORMAT(_start,"yyyy-MM")&_q&","&
 _q&"end"&_q&":"&_q&FORMAT(_end,"yyyy-MM")&_q&"}",
 ",",'fm_native_periods'[SortIndex],ASC)
RETURN IF(NOT ISBLANK(_cut),"{"&_q&"cutoff"&_q&":"&_q&FORMAT(_cut,"yyyy-MM")&_q&","&
 _q&"cycle"&_q&":"&_q&_cycle&_q&","&
 _q&"metric"&_q&":"&_q&_metric&_q&","&
 _q&"display"&_q&":"&_q&_display&_q&","&
 _q&"unit"&_q&":"&_q&_unit&_q&","&
 _q&"periods"&_q&":["&_periods&"]}"))'''
