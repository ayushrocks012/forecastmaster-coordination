"""Synthetic-only model and independent arithmetic oracle for the native engine.

No original workbook/report data is read. Dates in DATATABLE are constant text
literals coerced to DATETIME; DATE() is not a legal DATATABLE cell constant.
"""
from __future__ import annotations
import argparse
from datetime import date
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(HERE))
import native_model as nm

FACTORS={'market':100.,'abbott':30.,'pi':3.,'net':27.,'community':28.,'wholesaler':25.,'ni':3.,
         'homecare':5.,'hospital':2.,'hcl':1.,'competitor':1.,'nursing':1.,'private':.5,'internal':-.2,
         'retail':1.,'unassigned':.1,'ads':40.}
PERIODS=['2024:FY','2025:FY','2026:FY','2026:YTD','2026:YTG','2027:FY']
ALL_SECTORS=('Example A','Example B','Example C','')


def datatable(name,rows):
    columns=[];types=[]
    for key in rows[0]:
        value=next((r[key] for r in rows if r[key] is not None),'')
        typ='dateTime' if isinstance(value,date) else 'int64' if isinstance(value,int) else 'double' if isinstance(value,float) else 'string'
        columns.append(dict(name=key,dataType=typ,type='calculatedTableColumn',sourceColumn='['+key+']',summarizeBy='none'))
        types.extend([json.dumps(key),{'dateTime':'DATETIME','int64':'INTEGER','double':'DOUBLE','string':'STRING'}[typ]])
    def cell(value):
        if value is None:return 'BLANK()'
        if isinstance(value,(str,date)):
            text=value.isoformat() if isinstance(value,date) else value
            return '"'+text.replace('"','""')+'"'
        return json.dumps(value)
    expression='DATATABLE('+','.join(types)+',{'+','.join('{'+','.join(cell(r[c['name']]) for c in columns)+'}' for r in rows)+'})'
    return dict(name=name,columns=columns,partitions=[dict(name=name,mode='import',source=dict(type='calculated',expression=expression))])


def fixture():
    files=[];facts=[];scope=[];lookup={}
    configs=[('UK','GBP',1.),('Example EUR','EUR',1.3),('Example USD','USD',.9)]
    for country,currency,scale in configs:
        for driver,sectors,short in [('Example Oral',['Example A','Example B',''],'a'),('Example Paed',['Example C'],'b')]:
            source=country+'-'+short
            f=dict(SourceRevisionID=source,SourceFileName=source+'_IMS-Aug_26_ADS.xlsm',SourceRelativePath='Synthetic/'+source,
                   Country=country,DemandCycle='2026-10',GrowthDriver=driver,SourceProfile='Ext',PublicationStatus='SAVED',
                   FileLabel=source,IMSActualsThrough=date(2026,8,1),ExFactoryActualsThrough=date(2026,9,1))
            files.append(f)
            for sector in sectors:
                scope.append(dict(SourceRevisionID=source,Country=country,DemandCycle='2026-10',GrowthDriver=driver,Sector=sector,SectorLabel=sector+' – '+driver))
                for i in range(48):
                    month=date(2024+i//12,1+i%12,1)
                    amounts={key:(-0.2-i*.1 if key=='internal' else factor+i)*scale for key,factor in FACTORS.items()}
                    if i>=32:amounts['market']+=10.*scale
                    if sector=='Example B' and i==21:amounts['market']=None
                    if i==1:amounts['market']=None
                    if i==14:amounts['market']=0.
                    if sector=='Example B' and i==0:amounts['abbott']=None
                    if sector=='Example A' and i>=36:amounts['abbott']=0.
                    amounts['net']=None if amounts['abbott'] is None else amounts['abbott']-amounts['pi']
                    amounts['community']=amounts['wholesaler']+amounts['ni']
                    leaves=['wholesaler','ni','homecare','hospital','hcl','competitor','nursing','retail','private','internal','unassigned']
                    amounts['ads']=sum(amounts[key] for key in leaves)
                    sector_price={'Example A':2.,'Example B':3.,'Example C':5.,'':2.7}[sector]
                    values={key:None if value is None else value*sector_price for key,value in amounts.items()}
                    values['abbott']=None if amounts['abbott'] is None else amounts['abbott']*(sector_price+1.3)
                    values['pi']=amounts['pi']*(sector_price+.2)
                    values['net']=None if values['abbott'] is None else values['abbott']-values['pi']
                    for r in nm.catalog_rows():
                        if r['RowID']=='share':continue
                        amount=(amounts if r['Display']=='Units' else values)[r['RowID']]
                        record=dict(SourceRevisionID=source,Channel=r['Channel'],SubChannel=r['SubChannel'],Sector=sector,Month=month,
                                    ComponentKey=r['Component'],Amount=amount,MissingCells=int(amount is None),NumericCells=int(amount is not None))
                        facts.append(record);lookup[(country,sector,r['RowID'],r['Display'],i)]=amount
    native_files=[dict(**f,ADSPriority=2,ADSRevision=0,PreferenceRank=1,PreferenceTies=1,Scenario='ADS') for f in files]
    # A second saved plan for the same cohort is a comparison, never additive.
    original=next(f for f in files if f['SourceRevisionID']=='UK-a')
    review=dict(original);review.update(SourceRevisionID='UK-a-review',SourceFileName='Synthetic_IMS-Aug_26_REVIEW_001.xlsm',FileLabel='UK-a-review')
    files.append(review);native_files.append(dict(**review,ADSPriority=0,ADSRevision=0,PreferenceRank=2,PreferenceTies=1,Scenario='REVIEW_001'))
    for f in list(facts):
        if f['SourceRevisionID']=='UK-a':
            copied=dict(f);copied['SourceRevisionID']='UK-a-review';copied['Amount']=None if f['Amount'] is None else f['Amount']*1.1;facts.append(copied)
    for row in list(scope):
        if row['SourceRevisionID']=='UK-a':copied=dict(row);copied['SourceRevisionID']='UK-a-review';scope.append(copied)
    # A driver from another cycle must never make the current-cycle total unavailable.
    old=dict(files[0]);old.update(SourceRevisionID='inactive',FileLabel='inactive',GrowthDriver='Example Inactive',DemandCycle='2025-10')
    files.append(old);native_files.append(dict(**old,ADSPriority=2,ADSRevision=0,PreferenceRank=1,PreferenceTies=1,Scenario='ADS'))
    scope.append(dict(SourceRevisionID='inactive',Country='UK',DemandCycle='2025-10',GrowthDriver='Example Inactive',Sector='Inactive tier',SectorLabel='Inactive tier – Example Inactive'))
    static=nm.static_tables(('GBP','EUR','USD'))
    static['currency_map']=[dict(Country=c, Currency=fx) for c,fx,_ in configs]
    tables=[datatable('fm_native_'+k,v) for k,v in static.items()]
    next(t for t in tables if t['name']=='fm_native_measures')['measures']=nm.measures()
    tables.extend([datatable('fm_review_files',files),datatable('fm_review_facts',facts),datatable('fm_native_files',native_files),datatable('fm_native_scope',scope)])
    months=[dict(Month=date(2024+i//12,1+i%12,1)) for i in range(48)]
    tables.extend(datatable(n,months) for n in ('fm_review_axis','fm_review_months'))
    periods=[dict(Year=y,PeriodType=k,PeriodKey=f'{y}:{k}',Label=f'{y} {k}',SortIndex=y*3+j) for y in range(2024,2028) for j,k in enumerate(('FY','YTD','YTG'))]
    tables.append(datatable('fm_review_periods',periods))
    tables.append(datatable('fm_native_scenario',[dict(Mode='Automatic ADS',Scenario='Automatic ADS'),dict(Mode='Selected files',Scenario='ADS'),dict(Mode='Selected files',Scenario='REVIEW_001')]))
    lines=[]
    for display in ('Units','Value'):
        for mode,scenario in [('Automatic ADS','Automatic ADS'),('Selected files','ADS'),('Selected files','REVIEW_001')]:
            for kind in (0,1,6,12,24):
                lines.append(dict(DemandCycle='2026-10',ViewType='Total',ScopeDriver='',ScopeSector='',ScopeLabel='Selected total',
                                  Mode=mode,Scenario=scenario,Chart='demand',Token='none',RowID='',Display=display,
                                  IsSector=0,LineKind=kind,LineLabel=scenario+' Total '+str(kind),LineSort=kind))
    tables.append(datatable('fm_native_lines',lines))
    # The offline native preview needs all graph modes and reorder tokens, not
    # just the small Total-chart rows used by the arithmetic queries.
    groups=[dict(DemandCycle='2026-10',ViewType='Total',ScopeDriver='',ScopeSector='',ScopeLabel='Selected total',IsSector=0)]
    for driver,sectors in [('Example Oral',['Example A','Example B','']),('Example Paed',['Example C'])]:
        for view in ('Drivers','Both'):groups.append(dict(DemandCycle='2026-10',ViewType=view,ScopeDriver=driver,ScopeSector='',ScopeLabel=driver,IsSector=0))
        for sector in sectors:
            for view in ('Sectors','Both'):groups.append(dict(DemandCycle='2026-10',ViewType=view,ScopeDriver=driver,ScopeSector=sector,ScopeLabel=(sector or 'No forecast tier')+' – '+driver,IsSector=1))
    tables.append(datatable('fm_native_groups',groups))
    line_table=next(t for t in tables if t['name']=='fm_native_lines')
    line_table['partitions'][0]['source']['expression']='''
VAR _groups=CROSSJOIN('fm_native_groups','fm_native_scenario')
VAR _demand=CROSSJOIN(_groups,'fm_native_display',DATATABLE("K",INTEGER,{{0},{1},{6},{12},{24}}))
VAR _sop=CROSSJOIN(_groups,FILTER('fm_native_state','fm_native_state'[Kind]="row"),DATATABLE("K",INTEGER,{{0},{1}}))
RETURN UNION(
 SELECTCOLUMNS(_demand,"DemandCycle",[DemandCycle],"ViewType",[ViewType],"ScopeDriver",[ScopeDriver],"ScopeSector",[ScopeSector],"ScopeLabel",[ScopeLabel],
 "Mode",[Mode],"Scenario",[Scenario],"Chart","demand","Token","none","RowID","","Display",[Display],
 "IsSector",[IsSector],"LineKind",[K],"LineLabel",[Scenario]&" · "&[ScopeLabel]&" · "&SWITCH([K],0,"Actuals",1,"Forecast",[K]&"M trend"),"LineSort",[K]),
 SELECTCOLUMNS(_sop,"DemandCycle",[DemandCycle],"ViewType",[ViewType],"ScopeDriver",[ScopeDriver],"ScopeSector",[ScopeSector],"ScopeLabel",[ScopeLabel],
 "Mode",[Mode],"Scenario",[Scenario],"Chart","sop","Token",[Token],"RowID",[RowID],"Display",[Display],
 "IsSector",[IsSector],"LineKind",[K],"LineLabel",[Scenario]&" · "&[ScopeLabel]&" · "&[Channel]&" · "&[SubChannel]&" · "&[Measure]&" · "&IF([K]=0,"Actuals","Forecast"),"LineSort",[RowRank]*100+[K]))'''
    template={'model':{'tables':[dict(name='fm_review_facts',partitions=[dict(name='facts',mode='directLake',source=dict(type='entity',entityName='fm_review_facts',expressionSource='Source'))])]}}
    extended=nm.extend_model(template);relationships=extended['model']['relationships']
    definitions={t['name']:t for t in extended['model']['tables']}
    for table in tables:
        if table['name'] not in definitions:continue
        cols={c['name']:c for c in definitions[table['name']].get('columns',[])}
        for col in table['columns']:
            for prop in ('sortByColumn','isHidden'):
                if prop in cols.get(col['name'],{}):col[prop]=cols[col['name']][prop]
    database=dict(name='ForecastMasterNativeSyntheticR6',id='ForecastMasterNativeSyntheticR6',compatibilityLevel=1604,
                  model=dict(culture='en-GB',defaultPowerBIDataSourceVersion='powerBI_V3',tables=tables,relationships=relationships))
    return database,lookup


def period_months(row,period):
    year,kind=period.split(':');first=(int(year)-2024)*12;last=first+11;cut=31 if row in ('share','abbott','market','pi','net') else 32
    if kind=='YTD':last=min(last,cut)
    if kind=='YTG':first=max(first,cut+1)
    return list(range(first,last+1))


def available(values):
    present=[v for v in values if v is not None]
    return sum(present) if present else None


def oracle(lookup,row,display,period,window=0,sectors=ALL_SECTORS,countries=('UK',),rates=None,usd=False):
    rates=rates or {};cut=31 if row in ('share','abbott','market','pi','net') else 32
    def parts(i):
        out=[]
        for component in (('abbott','market') if row=='share' else (row,)):
            values=[]
            for country in countries:
                currency={'UK':'GBP','Example EUR':'EUR','Example USD':'USD'}[country]
                rate=1. if currency=='USD' else rates.get(currency)
                convert=display=='Value' and usd and (row!='share' or len(countries)>1)
                for sector in sectors:
                    value=lookup.get((country,sector,component,display,i))
                    if value is not None and convert:
                        if rate is None:return (None,None)
                        value*=rate
                    values.append(value)
            out.append(available(values))
        return out[0],out[1] if row=='share' else None
    months=period_months(row,period)
    if not months:return None
    slope=intercept=None
    if window and max(months)>cut:
        points=[]
        for x,i in enumerate(range(cut-window+1,cut+1),1):
            n,d=parts(i);y=(n/d if n is not None and d not in (None,0) else None) if row=='share' else n
            if y is None:return None
            points.append((x,y))
        mx=sum(p[0] for p in points)/window;my=sum(p[1] for p in points)/window
        slope=sum((x-mx)*(y-my) for x,y in points)/sum((x-mx)**2 for x,y in points);intercept=my-slope*mx
    nums=[];dens=[]
    for i in months:
        n,d=parts(i)
        if window and i>cut:
            value=intercept+slope*(window+i-cut)
            n=value*d if row=='share' and d is not None else value if row!='share' else None
        if n is None or row=='share' and d is None:return None
        nums.append(n)
        if row=='share':dens.append(d)
    if row=='share':return sum(nums)/sum(dens) if sum(dens)!=0 else None
    return sum(nums)


def queries():
    contexts=[('aggregate',None),('leaf', 'Example B')]
    q=[]
    for name,sector in contexts:
        filters=['TREATAS({"UK"},\'fm_review_files\'[Country])','TREATAS({"2026-10"},\'fm_review_files\'[DemandCycle])',
                 'TREATAS({"Local"},\'fm_native_currency\'[Currency])','TREATAS({'+','.join(json.dumps(x) for x in PERIODS)+'},\'fm_review_periods\'[PeriodKey])',
                 'TREATAS({"On"},\'fm_native_run_rate\'[Show])','TREATAS({"On"},\'fm_native_growth\'[Show])']
        if sector:filters.append('TREATAS({"'+sector+'"},\'fm_native_scope\'[Sector])')
        query="EVALUATE SUMMARIZECOLUMNS('fm_native_catalog'[RowID],'fm_native_display'[Display],'fm_review_periods'[PeriodKey],"+','.join(filters)+',"Plan",[N Plan],"6M",CALCULATE([N Benchmark],TREATAS({6},\'fm_native_trend\'[Window])),"12M",CALCULATE([N Benchmark],TREATAS({12},\'fm_native_trend\'[Window])),"24M",CALCULATE([N Benchmark],TREATAS({24},\'fm_native_trend\'[Window])),"Run rate",[N Run Rate],"Growth",[N Growth %])'
        q.append(dict(name=name,query=query))
    q.append(dict(name='availability',query="EVALUATE SUMMARIZECOLUMNS('fm_native_scope'[GrowthDriver],TREATAS({\"UK\"},'fm_review_files'[Country]),TREATAS({\"2026-10\"},'fm_review_files'[DemandCycle]),\"Available\",[N Scope Available])"))
    return q


def verify(results,lookup):
    count=0;failures=[]
    definitions={r['RowID']:r for r in nm.catalog_rows()}
    names=[r['name'] for r in results]
    if len(names)!=len(set(names)) or set(names)!={r['name'] for r in queries()}:failures.append('Missing or duplicate native query groups.')
    for group in results:
        if 'error' in group:failures.append(group['name']+': '+group['error']);continue
        if group['name']=='availability':
            names={r['fm_native_scope[GrowthDriver]'] for r in group['rows']}
            if names!={'Example Oral','Example Paed'}:failures.append('Availability did not hide inactive-cycle driver.')
            count+=1;continue
        sectors=('Example B',) if group['name']=='leaf' else ALL_SECTORS
        actual_rows={(r['fm_native_catalog[RowID]'],r['fm_native_display[Display]'],r['fm_review_periods[PeriodKey]']):r for r in group['rows']}
        expected_keys={(k,display,period) for k in nm.ORDER for display in ('Units','Value') for period in PERIODS}
        if set(actual_rows)-expected_keys:failures.append('Unexpected native row identities.')
        for key,display,period in sorted(expected_keys):
            r=actual_rows.get((key,display,period),{'fm_native_catalog[RowID]':key,'fm_native_display[Display]':display,'fm_review_periods[PeriodKey]':period})
            row=r['fm_native_catalog[RowID]'];display=r['fm_native_display[Display]'];period=r['fm_review_periods[PeriodKey]']
            expected={"Plan":oracle(lookup,row,display,period,sectors=sectors)}
            for w in (6,12,24):expected[f'{w}M']=oracle(lookup,row,display,period,w,sectors)
            months=period_months(row,period);p=expected['Plan']
            expected['Run rate']=p/len(months) if p is not None and months and definitions[row]['RunRate'] else None
            year,kind=period.split(':');py=oracle(lookup,row,display,str(int(year)-1)+':'+kind,sectors=sectors) if kind=='FY' else None
            # YTD/YTG PY must shift exactly the CURRENT window, not recompute the
            # prior year's YTD/YTG cutoff. Use an explicit synthetic month sum.
            if kind!='FY' and definitions[row]['Growth'] and months:
                vals=[available([lookup.get(('UK',s,row,display,i-12)) for s in sectors]) for i in months]
                py=sum(vals) if vals and all(x is not None for x in vals) else None
            expected['Growth']=(p/py-1) if definitions[row]['Growth'] and p is not None and py not in (None,0) else None
            for col,value in expected.items():
                actual=r.get('['+col+']');count+=1
                if value is None:
                    if actual is not None:failures.append(f'{group["name"]} {row} {display} {period} {col}: expected missing, got {actual}')
                elif not isinstance(actual,(int,float)) or not math.isclose(actual,value,rel_tol=1e-9,abs_tol=1e-8):
                    failures.append(f'{group["name"]} {row} {display} {period} {col}: {actual} != {value}')
    return {'Checks':count,'Failures':failures,'Evidence':'Actual local Power BI Analysis Services engine; synthetic only. No receiving UI/export/Service gate claimed.'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);parser.add_argument('--verify',type=Path);args=parser.parse_args()
    db,lookup=fixture();args.output.mkdir(parents=True,exist_ok=True)
    if args.verify:
        result=verify(json.loads(args.verify.read_text(encoding='utf-8-sig')),lookup);(args.output/'VALIDATION-NATIVE-DAX.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(bool(result['Failures']))
    (args.output/'synthetic-model.json').write_text(json.dumps(db,ensure_ascii=False));(args.output/'queries.json').write_text(json.dumps(queries()));print('Prepared synthetic native-engine model and independent oracle cases.')
