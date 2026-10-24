"""Independent full-sector arithmetic, formats, colours and empty-state checks.

Uses the original fabricated amount generator, never the serving preparer.
Preserves all 150 sectors, both cycles, six metrics, both displays, all three
trends and ten mixed periods. This does not qualify Fabric/RLS/freshness.
"""
from functools import lru_cache
import json
import math
from pathlib import Path
import shutil

import cell_fact
import prepared
import probe
import regression
import sector_dim

original=prepared.load('independent_leaf_matrix',prepared.R02/'matrix_cases.py')
fixture=original.fixture


@lru_cache(None)
def oracle(cycle,metric,display,driver,sector,year,kind,window,alternative):
    cut=36+int(cycle[-2:])-(2 if metric=='ef' else 3)
    lo,hi={'FY':(0,12),'YTD':(0,cut%12+1),'YTG':(cut%12+1,12),'H1':(0,6),'H2':(6,12)}[kind]
    months=range((year-2023)*12+lo,(year-2023)*12+hi)
    def raw(m,row):return fixture.amount(cycle,driver,sector,m,row,display,alternative)
    def numerator(m):return raw(m,'abbott' if metric=='share' else metric)
    def value(m):return numerator(m)/raw(m,'market') if metric=='share' else numerator(m)
    plan=sum(numerator(m) for m in months)
    if metric=='share':plan/=sum(raw(m,'market') for m in months)
    if months[-1]<=cut:return plan,None,None
    train=[value(m) for m in range(cut-window+1,cut+1)]
    center=(window-1)/2;mean=sum(train)/window
    slope=sum((i-center)*(v-mean) for i,v in enumerate(train))/sum((i-center)**2 for i in range(window))
    def projected(m):return value(m) if m<=cut else mean+slope*(m-cut+center)
    benchmark=sum(projected(m)*(raw(m,'market') if metric=='share' else 1) for m in months)
    if metric=='share':benchmark/=sum(raw(m,'market') for m in months)
    return plan,plan-benchmark,(plan-benchmark)/abs(benchmark)


def format_code(value,metric,display,key):
    if metric=='share' or key.endswith(':pct'):return '0.0%;−0.0%;0.0%'
    size=abs(value);symbol='£' if display=='Value' else ''
    text=(('−' if value<0 else '')+symbol+(f'{size/1e6:,.2f}m' if size>=1e6 else
        f'{size/1e3:,.1f}k' if size>=1000 else f'{size:,.0f}'))
    literal='"'+text+'"';return ';'.join([literal]*3)


def build(destination,candidate,population):
    if destination.exists():raise ValueError('Preserve independent leaf run')
    bound=regression.checked(candidate);regression.checked(population)
    if bound.get('Prototype')!='prepared-executive-cells':raise ValueError('Unknown leaf candidate')
    periods=[f'{y}:{k}' for y in (2026,2027) for k in ('FY','YTD','YTG','H1','H2')]
    queries=[];expected={};tf=original.tf
    specs=[(cycle,metric,display,False) for cycle in fixture.CYCLES for metric in ('market','abbott','share','pi','net','ef') for display in ('Units','Value')]
    specs.extend([('2026-10',metric,'Value',True) for metric in ('market','share')])
    for cycle,metric,display,alternative in specs:
        name='/'.join([cycle,metric,display,'mixed-alternative' if alternative else 'ADS'])
        defaults=fixture.defaults()
        if alternative:
            defaults=[v.replace('_ADS.xlsm','_REVIEW_001.xlsm') if '_Driver_02_' in v else v for v in defaults]
        filters=[tf('fm_review_files','Country',['UK']),tf('fm_review_files','DemandCycle',[cycle]),
            tf('fm_native_files','FileChoiceLabel',defaults),tf('fm_native_metric','RowID',[metric]),
            tf('fm_native_metric','Section',['Ex-factory' if metric=='ef' else 'IMS / Market']),
            tf('fm_native_display','Display',[display]),tf('fm_native_currency','Currency',['Local']),
            tf('fm_native_trend','Window',[6,12,24]),tf('fm_native_periods','PeriodKey',periods),
            tf('fm_native_start_month','MonthLabel',['Jan 2025']),tf('fm_native_end_month','MonthLabel',['Dec 2027'])]
        query="EVALUATE SUMMARIZECOLUMNS('"+sector_dim.DIM+"'[GrowthDriver],'"+sector_dim.DIM+"'[SectorLabel],"+'''
'fm_native_periods'[PeriodKey],'fm_native_columns'[ColumnKey],'''+','.join(filters)+''',
"V",['''+cell_fact.VALUE+'''],"F",IGNORE(['''+'_'+cell_fact.VALUE+''' FormatString]),
"C",IGNORE(['''+cell_fact.COLOR+''']))'''
        queries.append({'model':'candidate','name':name,'query':query});want={}
        for driver in range(1,6):
            for sector in range(1,31):
                label=f'Sector {driver:02}.{sector:02} – Driver {driver:02}'
                for period in periods:
                    y,k=period.split(':')
                    for w in (6,12,24):
                        plan,var,pct=oracle(cycle,metric,display,driver,sector,int(y),k,w,alternative and driver==2)
                        vals={'plan':plan, str(w)+':abs':var,str(w)+':pct':pct}
                        for key,value in vals.items():
                            if value is None:continue
                            identity='|'.join([f'Driver {driver:02}',label,period,key])
                            want[identity]={'Value':value,'Color':None if key=='plan' else original.color(pct)}
        expected[name]={'Metric':metric,'Display':display,'Cells':want}
    first=queries[0]['query']
    for name,old,new in [('no-files',tf('fm_native_files','FileChoiceLabel',fixture.defaults()),"FILTER(ALL('fm_native_files'[FileChoiceLabel]),FALSE())"),
        ('no-metric',tf('fm_native_metric','RowID',['market']),"FILTER(ALL('fm_native_metric'[RowID]),TRUE())"),
        ('incompatible-section',tf('fm_native_metric','Section',['IMS / Market']),tf('fm_native_metric','Section',['Ex-factory']))]:
        if first.count(old)!=1:raise ValueError('Changed query filter shape')
        queries.append({'model':'candidate','name':name,'query':first.replace(old,new)})
        expected[name]={'Metric':'market','Display':'Units','Cells':{}}
    destination.mkdir(parents=True)
    shutil.copy2(candidate/'candidate.json',destination/'candidate.json')
    for n in ('run_profile.ps1','launch_synthetic_engine.ps1'):shutil.copy2(population/n,destination/n)
    for n,obj in [('queries',queries),('expected',expected)]:
        (destination/(n+'.json')).write_text(json.dumps(obj,ensure_ascii=False))
    shutil.copy2(Path(__file__),destination/Path(__file__).name)
    files={p.name:probe.digest(p) for p in destination.iterdir()}
    (destination/'FROZEN-INPUTS.json').write_text(json.dumps({'Files':files,'Candidate':bound['Files']['candidate.json'],
        'IndependentOracleHashes':{n:probe.digest(prepared.R02/n) for n in ('large_fixture.py','matrix_cases.py')},
        'IndependentCells':sum(len(v['Cells']) for v in expected.values()),'Queries':len(queries),
        'CompanyAcceptance':False,'NoSectorCap':True},indent=2))
    return {'Queries':len(queries),'IndependentCells':sum(len(v['Cells']) for v in expected.values())}


def verify(directory):
    bound=regression.checked(directory)
    for n,h in bound['IndependentOracleHashes'].items():
        if probe.digest(prepared.R02/n)!=h:raise ValueError('Changed independent oracle source')
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    expected=json.loads((directory/'expected.json').read_text());by={r['name']:r for r in results}
    if len(by)!=len(results) or set(by)!=set(expected) or any('error' in r for r in results):raise AssertionError('Incomplete leaf regression')
    count=0
    for name,r in by.items():
        actual={}
        for row in r['rows']:
            identity='|'.join(str(row[k]) for k in (sector_dim.DIM+'[GrowthDriver]',sector_dim.DIM+'[SectorLabel]',
                'fm_native_periods[PeriodKey]','fm_native_columns[ColumnKey]'))
            if identity in actual:raise AssertionError('Duplicate leaf identity')
            actual[identity]=row
        spec=expected[name];want=spec['Cells']
        if set(actual)!=set(want):raise AssertionError('Exact leaf population: '+name)
        for identity,value in want.items():
            row=actual[identity];got=row.get('[V]')
            if not isinstance(got,(int,float)) or not math.isclose(got,value['Value'],rel_tol=1e-9,abs_tol=1e-7):
                raise AssertionError('Independent leaf arithmetic: '+name+'/'+identity)
            if row.get('[C]')!=value['Color']:raise AssertionError('Independent colour: '+name+'/'+identity)
            if row.get('[F]')!=format_code(got,spec['Metric'],spec['Display'],identity.split('|')[-1]):
                raise AssertionError('Independent exact format: '+name+'/'+identity)
            count+=1
    if count!=bound['IndependentCells']:raise AssertionError('Incomplete independent count')
    return {'Stage':'LOCAL_INDEPENDENT_FULL_SECTOR_CELLS','Queries':len(results),'IndependentCells':count,'Mismatches':0,
        'SourceHashes':bound['Files'],'ResultsSHA256':probe.digest(directory/'results.json'),
        'TaskOwnedEngineClosed':True,'CompanyOrDesktopAcceptance':False}


if __name__=='__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1]=='verify' else build(*(Path(s) for s in sys.argv[2:5])),indent=2))
