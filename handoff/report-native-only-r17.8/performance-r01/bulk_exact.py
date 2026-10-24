"""Full Plan/Benchmark replacement: one grouped fact set, no legacy branch.

Unlike the earlier limited fast-path experiment, this includes the original
per-sector missing-cell invalidation, per-month currency/FX admission, fixed or
selected channel/subchannel rules, arbitrary catalog rows and aggregate Share.
No prepared data, physical/schema changes or cache-freshness contract is added.
"""
from copy import deepcopy

import prepared
import strictcells


def rate(currency):
    return '''VAR _digits=FILTER(_fx,'fm_native_state'[Currency]='''+currency+''')
RETURN IF('''+currency+'''="USD",1,IF(COUNTROWS(_digits)=7&&COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,
 VAR _exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])
 VAR _half=INT(_exponent/2)
 RETURN SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*
 POWER(10,_half)*POWER(10,_exponent-_half)))'''


def monthly_value(role):
    prefix='N' if role=='N' else 'D'
    component='_numComponent' if role=='N' else '_denComponent'
    return '''VAR _d='fm_review_facts'[Month]
 VAR _rows=FILTER(_byCurrency,'fm_review_facts'[Month]=_d)
 VAR _available=SUMX(_rows,['''+prefix+'''Count])
 VAR _fxBad=SUMX(_rows,['''+prefix+'''FX])
 VAR _localCurrencies=COUNTROWS(FILTER(_rows,['''+prefix+'''Count]>0))
 RETURN IF(LEN('''+component+''')>0&&_available>0&&_fxBad=0&&_currenciesKnown
 &&(NOT _value||_usd||_localCurrencies=1),SUMX(_rows,['''+prefix+'''Raw]))'''


def body(original_plan,original_monthly,benchmark):
    source=original_monthly[:original_monthly.index('VAR _date=')]
    period=original_plan[:original_plan.index('VAR _ratio=')].replace(' VAR _cut=[N Cutoff]','')
    config='''
VAR _row=COALESCE(SELECTEDVALUE('fm_native_catalog'[RowID]),SELECTEDVALUE('fm_native_metric'[RowID]),"market")
VAR _display=[N Display]
VAR _ratio=_row="share"
VAR _definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row&&'fm_native_catalog'[Display]=_display)
VAR _numComponent=IF(_row="ef","ef-ads-"&LOWER(_display),MAXX(_definition,'fm_native_catalog'[Component]))
VAR _denComponent=IF(_ratio,MAXX(_definition,'fm_native_catalog'[Denominator]))
VAR _channel=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[Channel]))
VAR _sub=IF(_row="ef","*",MAXX(_definition,'fm_native_catalog'[SubChannel]))
VAR _value=_display="Value"
VAR _usd=SELECTEDVALUE('fm_native_currency'[Currency],"USD")="USD"
VAR _currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE('fm_native_currency_map'[Currency],
 'fm_native_currency_map'[Country],'fm_native_files'[Country]))
VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1&&COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _singleCC=MAXX(_currencies,[CC])
VAR _currenciesKnown=NOT _value||COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0
VAR _convert=_value&&_usd&&(_row<>"share"||NOT _singleCurrency)
VAR _selectedChannels=VALUES('fm_review_facts'[Channel])
VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])
VAR _fx=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),'fm_native_state'[Kind]="fx")
VAR _singleRate=('''+rate('_singleCC')+''')
VAR _cutoffs=SELECTCOLUMNS(_files,"Cut",IF(_row IN {"share","abbott","market","pi","net"},
 'fm_native_files'[IMSActualsThrough],'fm_native_files'[ExFactoryActualsThrough]))
VAR _datesValid=COUNTROWS(FILTER(_cutoffs,ISBLANK([Cut])||[Cut]<DATE(2000,1,1)||[Cut]>=DATE(2100,1,1)))=0
VAR _cut=IF(_sourceOK&&_datesValid,MINX(_cutoffs,[Cut]))
VAR _fitCut=IF(_sourceOK&&_datesValid&&COUNTROWS(DISTINCT(_cutoffs))=1,MAXX(_cutoffs,[Cut]))
'''
    need='''
VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)
VAR _trainDates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_fitCut,[Value]-_w))
VAR _searchDates='''+('DISTINCT(UNION(_months,_trainDates))' if benchmark else '_months')+'''
VAR _needed=FILTER(ALL('fm_review_axis'[Month]),'fm_review_axis'[Month] IN _searchDates)
VAR _pairs=SELECTCOLUMNS(GENERATE(_files,
 VAR _gd='fm_native_files'[GrowthDriver]
 RETURN SELECTCOLUMNS(FILTER(_scope,'fm_native_scope'[GrowthDriver]=_gd),"__Sector",'fm_native_scope'[Sector])),
 "ID",'fm_native_files'[SourceRevisionID],"Sector",[__Sector])
VAR _groups=CALCULATETABLE(SUMMARIZECOLUMNS(
 'fm_review_facts'[SourceRevisionID],'fm_review_facts'[Sector],'fm_review_facts'[Month],'fm_review_facts'[ComponentKey],
 "Raw",SUM('fm_review_facts'[Amount]),
 "Bad",SUMX('fm_review_facts',INT('fm_review_facts'[MissingCells]<>0||ISBLANK('fm_review_facts'[Amount])))),
 REMOVEFILTERS('fm_review_facts'),
 TREATAS(_pairs,'fm_review_facts'[SourceRevisionID],'fm_review_facts'[Sector]),TREATAS(_needed,'fm_review_facts'[Month]),
 TREATAS({_numComponent,_denComponent},'fm_review_facts'[ComponentKey]),
 FILTER(ALL('fm_review_facts'[Channel]),IF(_channel="*",'fm_review_facts'[Channel] IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),
 FILTER(ALL('fm_review_facts'[SubChannel]),IF(_sub="*",'fm_review_facts'[SubChannel] IN _selectedSubs,COALESCE('fm_review_facts'[SubChannel],"")=_sub)))
VAR _good=FILTER(_groups,[Bad]=0)
VAR _converted=GENERATE(_good,
 VAR _id='fm_review_facts'[SourceRevisionID]
 VAR _cc=IF(NOT _value,"Units",IF(_singleCurrency,_singleCC,
 LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],
 LOOKUPVALUE('fm_native_files'[Country],'fm_native_files'[SourceRevisionID],_id))))
 VAR _rate=IF(_singleCurrency,_singleRate,('''+rate('_cc')+'''))
 RETURN ROW("CC",_cc,
 "A",IF(_convert,IF(NOT ISBLANK([Raw])&&NOT ISBLANK(_rate),IFERROR([Raw]*_rate,BLANK())),[Raw]),
 "FX",INT(_convert&&NOT ISBLANK([Raw])&&(ISBLANK(_rate)||ISERROR([Raw]*_rate)))))
VAR _byCurrency=GROUPBY(_converted,'fm_review_facts'[Month],[CC],
 "NRaw",SUMX(CURRENTGROUP(),IF('fm_review_facts'[ComponentKey]=_numComponent,[A])),
 "DRaw",SUMX(CURRENTGROUP(),IF(_ratio&&'fm_review_facts'[ComponentKey]=_denComponent,[A])),
 "NCount",SUMX(CURRENTGROUP(),INT('fm_review_facts'[ComponentKey]=_numComponent&&NOT ISBLANK([A]))),
 "DCount",SUMX(CURRENTGROUP(),INT(_ratio&&'fm_review_facts'[ComponentKey]=_denComponent&&NOT ISBLANK([A]))),
 "NFX",SUMX(CURRENTGROUP(),IF('fm_review_facts'[ComponentKey]=_numComponent,[FX])),
 "DFX",SUMX(CURRENTGROUP(),IF(_ratio&&'fm_review_facts'[ComponentKey]=_denComponent,[FX])))
VAR _monthly0=ADDCOLUMNS(SUMMARIZE(_byCurrency,'fm_review_facts'[Month]),
 "N",'''+monthly_value('N')+''',
 "D",'''+monthly_value('D')+''')
VAR _monthly=SELECTCOLUMNS(_monthly0,"Date",CONVERT('fm_review_facts'[Month],DATETIME),"N",[N],"D",[D])
VAR _period=NATURALLEFTOUTERJOIN(_months,_monthly)
VAR _denValid=COUNTROWS(FILTER(_period,NOT ISBLANK([D])))=_count
'''
    plan='''
VAR _valid=COUNTROWS(FILTER(_period,NOT ISBLANK([N])))=_count
RETURN IF(_sourceOK&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,
 IF(_ratio,IF(_denValid,DIVIDE(SUMX(_period,[N]),SUMX(_period,[D]))),SUMX(_period,[N])))'''
    bench='''
VAR _train0=FILTER(_monthly,[Date]>=EDATE(_fitCut,1-_w)&&[Date]<=_fitCut)
VAR _train=ADDCOLUMNS(_train0,"X",DATEDIFF(EDATE(_fitCut,1-_w),[Date],MONTH)+1,
 "Y",IF(_ratio,DIVIDE([N],[D]),[N]))
VAR _fitValid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w
VAR _mx=(_w+1)/2
VAR _mean=IF(_fitValid,AVERAGEX(_train,[Y]))
VAR _slope=IF(_fitValid,DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_mean)),SUMX(_train,POWER([X]-_mx,2))))
VAR _values=ADDCOLUMNS(_period,"BN",VAR _m=[Date]
 VAR _forecast=IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),
 _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))
 RETURN IF(_m<=_cut,[N],IF(_ratio,IF(NOT ISBLANK(_forecast)&&NOT ISBLANK([D]),_forecast*[D]),_forecast)))
VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([BN])))=_count
RETURN IF(_sourceOK&&NOT ISBLANK(_fitCut)&&NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,
 IF(_ratio,IF(_denValid,DIVIDE(SUMX(_values,[BN]),SUMX(_period,[D]))),SUMX(_values,[BN])))'''
    return source+config+period+need+(bench if benchmark else plan)


def patch(database):
    fixed=deepcopy(database);old=prepared.adapter.planning.measures(database)
    current=prepared.adapter.planning.measures(fixed)
    expected=prepared.adapter.planning.measures(strictcells.patch(
        prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]))
    text=prepared.adapter.selection.OLD.expression_text
    for name in ('N Plan','N Benchmark','N Monthly Numerator','N Summary Cell','N Headline Cell'):
        if text(old[name]['expression'])!=text(expected[name]['expression']):
            raise ValueError('Unknown R03 expression: '+name)
    for name in ('N Plan','N Benchmark'):
        current[name]['expression']=body(text(old['N Plan']['expression']),text(old['N Monthly Numerator']['expression']),name=='N Benchmark')
    return fixed
