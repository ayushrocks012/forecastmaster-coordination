"""10 drivers x 50 sectors, fabricated facts only. No company scale assertion."""
from datetime import date
import json
from pathlib import Path
import sys
import engine_fixture as e


def build():
    db,queries,_,_,_=e.build()
    files=[]
    for i in range(1,11):
        files.append(dict(SourceRevisionID=f"scale-{i}",SourceFileName=f"scale-{i}_IMS202608_ADS.xlsm",SourceRelativePath=f"Synthetic/scale-{i}",
            Country="UK",DemandCycle="2026-10",GrowthDriver=f"Example Driver {i:02d}",SourceProfile="Ext",PublicationStatus="SAVED",FileLabel=f"scale-{i}",
            IMSActualsThrough=date(2026,8,1),ExFactoryActualsThrough=date(2026,9,1)))
    for index,t in enumerate(db['model']['tables']):
        if t['name']=='fm_review_files':db['model']['tables'][index]=e.old.old.datatable('fm_review_files',files)
        if t['name']=='fm_review_facts':
            t['partitions'][0]['source']['expression']='''
VAR _members=GENERATE(SELECTCOLUMNS(GENERATESERIES(1,10),"D",[Value]),
 SELECTCOLUMNS(GENERATESERIES(1,50),"S",[Value]))
VAR _months=SELECTCOLUMNS(GENERATESERIES(0,47),"M",[Value])
VAR _catalog=FILTER('fm_native_catalog','fm_native_catalog'[RowID]<>"share")
VAR _all=CROSSJOIN(_members,_months,_catalog)
RETURN SELECTCOLUMNS(_all,
 "SourceRevisionID","scale-"&[D],"Channel",[Channel],"SubChannel",[SubChannel],
 "Sector","Example Sector "&FORMAT([S],"00"),"Month",EDATE(DATE(2024,1,1),[M]),"ComponentKey",[Component],
 "Amount",IF([S]=50&&[M]=21,BLANK(),(100+[M]+[S]/100+[D]+IF([M]>=32,10,0))*IF([Display]="Value",2,1)),
 "MissingCells",INT([S]=50&&[M]=21),"NumericCells",INT(NOT([S]=50&&[M]=21)))'''
    return db,[q for q in queries if q['name']=='visual/headline']


def verify(results):
    failures=[]
    rows=results[0].get('rows',[])
    if 'error' in results[0]:failures.append(results[0]['error'])
    if len(rows)!=10:failures.append('Expected 10 numeric headline cells')
    import math
    def monthly(i):
        return sum(100+i+s/100+d+(10 if i>=32 else 0) for d in range(1,11) for s in range(1,51) if not(s==50 and i==21))
    training=[monthly(i) for i in range(20,32)]
    mx=5.5;my=sum(training)/12
    slope=sum((i-mx)*(v-my) for i,v in enumerate(training))/sum((i-mx)**2 for i in range(12))
    ranges={'2026 FY':range(24,36),'2026 YTD':range(24,32),'2026 YTG':range(32,36),'2027 FY':range(36,48)}
    for r in rows:
        label=r['fm_native_headline[Label]'];period=r['fm_native_periods[Label]'];months=ranges[period]
        plan=sum(monthly(i) for i in months)
        benchmark=sum(monthly(i) if i<=31 else my+slope*((i-20)-mx) for i in months)
        expected=plan if label=='Plan' else plan-benchmark if label=='Overcall / Undercall' else (plan-benchmark)/abs(benchmark)
        if not math.isclose(r['[Value]'],expected,rel_tol=1e-9,abs_tol=1e-8):failures.append('Scale aggregate arithmetic mismatch')
    return {'Drivers':10,'SectorsPerDriver':50,'SyntheticFactRows':816000,'HeadlineNumericCells':len(rows),
            'Failures':failures,'CompanyPerformanceOrDirectLake':'PENDING','ElapsedMs':results[0].get('elapsedMs')}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    db,queries=build()
    if a.verify:
        result=verify(json.loads(a.verify.read_text(encoding='utf-8-sig')))
        result['RetainedInputMatches']=json.loads((a.directory/'synthetic-model.json').read_text())==db
        if not result['RetainedInputMatches']:result['Failures'].append('Retained input differs')
        print(json.dumps(result,indent=2));raise SystemExit(bool(result['Failures']))
    a.directory.mkdir(parents=True,exist_ok=True)
    (a.directory/'synthetic-model.json').write_text(json.dumps(db,ensure_ascii=False))
    (a.directory/'queries.json').write_text(json.dumps(queries))
    for name in ('fx-queries','edge-queries'):(a.directory/(name+'.json')).write_text('[]')
