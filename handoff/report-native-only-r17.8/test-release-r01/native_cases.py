"""Fabricated native-engine execution, independent numeric oracle and context checks."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

m=load('r178m_cases',HERE/'model.py')
fixture_path=HERE.parents[1]/'report-native-r17/tests/native_fixture.py'
sys.path.insert(0,str(fixture_path.parent))
f=load('r178_oracle_source',fixture_path)


def tf(table,column,values):
    return 'TREATAS({'+','.join(json.dumps(v,ensure_ascii=False) if isinstance(v,str) else str(v) for v in values)+"},'"+table+"'["+column+'])'


SHARED=[tf('fm_review_files','Country',['UK']),tf('fm_review_files','DemandCycle',['2026-10']),
 tf('fm_native_currency','Currency',['Local'])]


def oracle(lookup,row,display,year,kind,window=0):
    """Named-year calendar masks; regression fit uses actual cutoff year only.

    Independent Python source components and complete calendar months. Missing
    cells stay unavailable; weighted share never averages sector percentages.
    """
    row='ads' if row=='ef' else row
    cut=31 if row in {'market','abbott','share','pi','net'} else 32
    cut_month=cut%12
    begin,end={'FY':(0,12),'YTD':(0,cut_month+1),'YTG':(cut_month+1,12),'H1':(0,6),'H2':(6,12)}[kind]
    months=range((year-2024)*12+begin,(year-2024)*12+end)
    def parts(i):
        components=('abbott','market') if row=='share' else (row,)
        totals=[]
        for comp in components:
            cells=[lookup.get(('UK',sector,comp,display,i)) for sector in f.ALL_SECTORS]
            # Original reviewed native semantics permit a present sector subtotal;
            # a completely absent calendar month remains unavailable.
            totals.append(f.available(cells))
        return totals[0],totals[1] if row=='share' else None
    fit=None
    if window and max(months)>cut:
        ys=[]
        for i in range(cut-window+1,cut+1):
            n,d=parts(i);y=n/d if row=='share' and n is not None and d not in (None,0) else n if row!='share' else None
            if y is None:return None
            ys.append(y)
        mean=sum(ys)/window;center=(window-1)/2
        slope=sum((i-center)*(y-mean) for i,y in enumerate(ys))/sum((i-center)**2 for i in range(window))
        fit=mean,slope,center
    nums=[];dens=[]
    for i in months:
        n,d=parts(i)
        if window and i>cut:
            mean,slope,center=fit;y=mean+slope*(window+i-cut-1-center)
            n=y*d if row=='share' and d is not None else y if row!='share' else None
        if n is None or row=='share' and d is None:return None
        nums.append(n)
        if row=='share':dens.append(d)
    return sum(nums)/sum(dens) if row=='share' and sum(dens)!=0 else None if row=='share' else sum(nums)


def build(directory):
    baseline=m.original_database();baseline['name']=baseline['id']='ForecastMasterNativeSyntheticR178'
    candidate,_=m.patch_database(baseline)
    # Generic isolated Tabular instance has no Desktop Mashup host. All source
    # partitions are DAX calculated; this host-only property is irrelevant to DAX.
    for db in (baseline,candidate):db['model'].pop('defaultPowerBIDataSourceVersion',None)
    _,lookup=f.fixture();cases=[];expected={}
    def add(name,query,models=('candidate',),expect=None):
        for model in models:cases.append(dict(name=name,model=model,query=query))
        if expect is not None:expected[name]=expect
    for row in ('market','abbott','share','pi','net','ef'):
        for display in ('Units','Value'):
            for year,kind in [(2026,k) for k in ('FY','YTD','YTG','H1','H2')]+[(2027,k) for k in ('FY','YTD','YTG')]:
                name=f'numeric/{row}/{display}/{year}/{kind}'
                filters=SHARED+[tf('fm_native_metric','RowID',[row]),tf('fm_native_display','Display',[display]),tf('fm_native_periods','PeriodKey',[str(year)+':'+kind])]
                members=['"P",[N Plan]']
                ex={'[P]':oracle(lookup,row,display,year,kind)}
                for window in (6,12,24):
                    members+=['"B'+str(window)+'",CALCULATE([N Benchmark],'+tf('fm_native_trend','Window',[window])+')',
                              '"V'+str(window)+'",CALCULATE([N Variance %],'+tf('fm_native_trend','Window',[window])+')']
                    b=oracle(lookup,row,display,year,kind,window);p=ex['[P]']
                    ex['[B'+str(window)+']']=b
                    ex['[V'+str(window)+']']=(p-b)/abs(b) if p is not None and b not in (None,0) else None
                add(name,'EVALUATE CALCULATETABLE(ROW('+','.join(members)+'),'+','.join(filters)+')',('baseline','candidate'),ex)
    filters=SHARED+[tf('fm_native_metric','RowID',['market']),tf('fm_native_display','Display',['Units']),tf('fm_native_periods','PeriodKey',['2026:FY','2026:YTD','2026:YTG','2027:FY'])]
    add('headline/no-source-row',"EVALUATE SUMMARIZECOLUMNS('fm_native_headline'[Label],'fm_native_periods'[Label],"+','.join(filters)+',"V",[N Headline Cell])')
    add('executive/auto-drill',"EVALUATE SUMMARIZECOLUMNS('fm_native_scenario'[Scenario],'fm_native_scope'[GrowthDriver],'fm_native_scope'[SectorLabel],'fm_native_periods'[Label],'fm_native_columns'[ColumnLabel],"+','.join(filters+[tf('fm_native_trend','Window',[6,12])])+',"V",[N Summary Cell])')
    for ids,name in [(['UK-a-review'],'manual/review'),(['UK-a','UK-b'],'manual/ads-pair'),(['UK-a','UK-a-review'],'manual/alternatives')]:
        selected="VAR _labels=SELECTCOLUMNS(FILTER(ALL('fm_native_files'),'fm_native_files'[SourceRevisionID] IN {"+','.join(json.dumps(i) for i in ids)+"}),\"L\",'fm_native_files'[FileChoiceLabel])\n"
        extra=SHARED+[tf('fm_native_metric','RowID',['market']),tf('fm_native_display','Display',['Units']),tf('fm_native_periods','PeriodKey',['2026:FY']),"TREATAS(_labels,'fm_native_files'[FileChoiceLabel])"]
        add(name,'EVALUATE\n'+selected+"RETURN SUMMARIZECOLUMNS('fm_native_scenario'[Scenario],"+','.join(extra)+',"V",[N Summary Cell])')
        add(name+'/headline','EVALUATE\n'+selected+'RETURN CALCULATETABLE(ROW("P",[N Plan],"Headline",CALCULATE([N Headline Cell],'+tf('fm_native_headline','Key',['plan'])+')),'+','.join(extra)+')')
    for view in ('Total','Drivers','Sectors'):
        extra=SHARED+[tf('fm_native_metric','RowID',['market']),tf('fm_native_display','Display',['Units']),tf('fm_native_view','View',[view]),tf('fm_native_chart_trend','Window',[12]),tf('fm_native_lines','Chart',['demand']),tf('fm_review_axis','Month',[]) ]
        extra=extra[:-1]+["TREATAS({DATE(2026,8,1),DATE(2026,9,1),DATE(2026,12,1)},'fm_review_axis'[Month])"]
        add('chart/'+view,"EVALUATE SUMMARIZECOLUMNS('fm_native_lines'[SeriesLabel],'fm_native_lines'[LineKind],'fm_review_axis'[Month],"+','.join(extra)+',"V",[N Chart Monthly])')
    add('files/labels',"EVALUATE SELECTCOLUMNS('fm_native_files',\"ID\",[SourceRevisionID],\"Label\",[FileChoiceLabel],\"Imported\",FORMAT([ImportedAtUTC],\"yyyy-MM-dd HH:mm:ss\"))")
    add('files/scope-available',"EVALUATE SUMMARIZECOLUMNS('fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[SourceRevisionID],"+','.join(SHARED)+',"V",[N File Available])')
    add('missing-ads', 'EVALUATE CALCULATETABLE(ROW("V",[N Plan],"OK",[N Source OK]),'+','.join([tf('fm_review_files','Country',['Parser']),tf('fm_review_files','DemandCycle',['2026-10']),tf('fm_native_metric','RowID',['market']),tf('fm_native_periods','PeriodKey',['2026:FY'])])+')')
    add('reversed-months','EVALUATE CALCULATETABLE(ROW("V",[N Headline Cell]),'+','.join(SHARED+[tf('fm_native_metric','RowID',['market']),tf('fm_native_headline','Key',['plan']),tf('fm_native_periods','PeriodKey',['2026:FY']),"TREATAS({DATE(2027,1,1)},'fm_native_start_month'[Month])","TREATAS({DATE(2026,1,1)},'fm_native_end_month'[Month])"])+')')
    directory.mkdir(parents=True,exist_ok=True)
    for name,value in [('baseline',baseline),('candidate',candidate),('queries',cases),('expected',expected)]:
        (directory/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    return {'Queries':len(cases),'OracleNumericCells':sum(len(r) for r in expected.values())}


def verify(directory):
    results=json.loads((directory/'results.json').read_text(encoding='utf-8-sig'))
    cases=json.loads((directory/'queries.json').read_text());expected=json.loads((directory/'expected.json').read_text())
    failures=[];checks=0
    by={(r['name'],r['model']):r for r in results}
    def check(ok,label):
        nonlocal checks
        checks+=1
        if not ok:failures.append(label)
    check(len(by)==len(cases)==len(results),'Exact query population')
    for key,r in by.items():check('error' not in r,str(key)+': '+r.get('error',''))
    def rows(name,model='candidate'):return by.get((name,model),{}).get('rows',[])
    def close(a,b):return a is None and b is None or isinstance(a,(int,float)) and isinstance(b,(int,float)) and math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-6)
    for name,values in expected.items():
        for model in ('baseline','candidate'):
            got=rows(name,model)
            check(len(got)==1,name+'/'+model+' cardinality')
            for col,val in values.items():check(bool(got) and close(got[0].get(col),val),name+'/'+model+'/'+col)
        check(rows(name,'baseline')==rows(name),name+' baseline/candidate exact parity')
    check(len(rows('headline/no-source-row'))==10,'Headline produces all 10 nonblank cells without source row')
    auto=rows('executive/auto-drill');check(bool(auto) and {r['fm_native_scenario[Scenario]'] for r in auto}=={'Automatic ADS'},'Automatic Executive shows one scenario only')
    check({r['fm_native_columns[ColumnLabel]'] for r in auto}=={'Plan','6M variance','6M variance %','12M variance','12M variance %'},'Executive admits exactly two selected trend windows')
    for name,want in [('manual/review',{'REVIEW_001'}),('manual/ads-pair',{'ADS'}),('manual/alternatives',{'ADS','REVIEW_001'})]:
        got=rows(name);check(bool(got) and {r['fm_native_scenario[Scenario]'] for r in got}==want,name+' separates scenarios')
    _,lookup=f.fixture()
    oral=f.oracle(lookup,'market','Units','2026:FY',sectors=('Example A','Example B',''))
    manual_values={r['fm_native_scenario[Scenario]']:r['[V]'] for r in rows('manual/alternatives')}
    check(close(manual_values.get('ADS'),oral) and close(manual_values.get('REVIEW_001'),oral*1.1),'Alternate scenarios retain independent plan values')
    review=rows('manual/review/headline');check(bool(review) and close(review[0].get('[P]'),oral*1.1) and close(review[0].get('[Headline]'),oral*1.1),'Single manual version headline equals selected plan')
    alt=rows('manual/alternatives/headline');check(bool(alt) and alt[0].get('[P]') is None and alt[0].get('[Headline]') is None,'Ambiguous alternatives not added in total/headline')
    for view in ('Total','Drivers','Sectors'):
        got=rows('chart/'+view)
        check(bool(got) and {r['fm_native_lines[LineKind]'] for r in got}=={0,1,12},'Chart '+view+' admits actual/forecast/one trend')
        check(all(not r['fm_native_lines[SeriesLabel]'].startswith('2026-10') for r in got),'Scope-first chart labels '+view)
        actual={(r['fm_native_lines[SeriesLabel]'].split(' · ')[0],r['fm_review_axis[Month]']):r['[V]'] for r in got if r['fm_native_lines[LineKind]']==0}
        forecast={(r['fm_native_lines[SeriesLabel]'].split(' · ')[0],r['fm_review_axis[Month]']):r['[V]'] for r in got if r['fm_native_lines[LineKind]']==1}
        check(bool(actual) and all(k in forecast and close(value,forecast[k]) for k,value in actual.items()),'Actual/forecast share matching cutoff endpoint '+view)
    files=rows('files/labels');check(len(files)==17,'File metadata population')
    labels=[r['[Label]'] for r in files];check(len(labels)==len(set(labels)),'Collision labels unique')
    check(all(' | ' not in label and not any(r['[ID]'] in label for r in files if len(r['[ID]'])>30) for label in labels),'No raw hash suffix')
    check(any(' UTC' in label for label in labels),'Import UTC visible')
    file_map={r['[ID]']:r for r in files}
    check(file_map['p1']['[Imported]']==file_map['p2']['[Imported]']=='2026-10-22 08:00:00','Fraction/timezone import parsing retained')
    check(file_map['p1']['[Label]'].endswith(' · v1') and file_map['p2']['[Label]'].endswith(' · v2'),'Same-second file collision uses short unique versions')
    check('Import time unavailable' in file_map['UK-a']['[Label]'],'Missing timestamp never invented')
    scope=rows('files/scope-available');check(bool(scope) and all(r['fm_native_files[Country]']=='UK' and r['fm_native_files[DemandCycle]']=='2026-10' for r in scope),'File picker current scope only')
    check(rows('missing-ads')[0].get('[V]') is None,'Unavailable source stays blank')
    check(rows('reversed-months')[0].get('[V]') is None,'Invalid month bounds stay blank')
    timings={r['name']:r.get('elapsedMs') for r in results if r['name'].startswith(('chart/','headline/','executive/'))}
    return {'Stage':'R178_NATIVE_SYNTHETIC_VERIFIED' if not failures else 'R178_NATIVE_SYNTHETIC_FAILED',
      'QueriesExecuted':len(results),'Assertions':checks,'Failures':failures,'SyntheticVisualQueryMs':timings,
      'InputSHA256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.json') if p.name!='results.json'},
      'CompanyDataUsed':False,'CompanySpeedOrDesktopRenderingVerified':False}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=verify(args.directory) if args.verify else build(args.directory)
    print(json.dumps(result,indent=2));sys.exit(bool(result.get('Failures')))
