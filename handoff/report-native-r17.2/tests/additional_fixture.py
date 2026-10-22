"""Bounded synthetic signed/mixed-cutoff and visual-query comparisons."""
from copy import deepcopy
import json
from pathlib import Path
import re
import sys
import engine_fixture as e


def build(variant):
    db,queries,lookup,_,_=e.build()
    if variant=="before":
        db,_,_,_=e.old.create_fixture()
        # Same 4-period request and source population as the revised headline.
        query='''EVALUATE SUMMARIZECOLUMNS('fm_review_files'[DemandCycle],'fm_native_scenario'[Scenario],'fm_review_periods'[Label],
 TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"Automatic ADS"},'fm_native_scenario'[Mode]),TREATAS({"2026 FY","2026 YTD","2026 YTG","2027 FY"},'fm_review_periods'[Label]),
 TREATAS({"Local"},'fm_native_currency'[Currency]),"P",[N Plan],"V",[N Headline Variance],"Pct",[N Headline Variance %])'''
        return db,[{"name":"headline-before","query":query}],{}
    if variant=="after":
        return db,[q for q in queries if q["name"]=="visual/headline"],{}
    if variant=="signed":
        facts=next(t for t in db['model']['tables'] if t['name']=='fm_review_facts')
        expression=facts['partitions'][0]['source']['expression']
        def edit(match):
            row=match.group(0)
            if '"Internal Account"' in row and re.search('"2027-[0-9]{2}-01"',row):
                parts=row.split(',');parts[-3]=str(float(parts[-3])*1.2);return ','.join(parts)
            return row
        facts['partitions'][0]['source']['expression']=re.sub(r'\{[^{}]+\}',edit,expression)
        return db,[q for q in queries if q['name']=='negative-denominator'],{'percentage':-0.2}
    if variant=="mixed":
        files=next(t for t in db['model']['tables'] if t['name']=='fm_review_files')
        expr=files['partitions'][0]['source']['expression']
        def edit(match):
            row=match.group(0)
            return row.replace('"2026-08-01"','"2026-07-01"') if row.startswith('{"UK-b",') else row
        new=re.sub(r'\{[^{}]+\}',edit,expr)
        assert new!=expr
        files['partitions'][0]['source']['expression']=new
        query='''EVALUATE CALCULATETABLE(ROW("Cut",FORMAT([N Cutoff],"yyyy-MM"),"Fit",[N Fit Cutoff],
 "Plan",[N Plan],"Variance",[N Variance]),TREATAS({"UK"},'fm_review_files'[Country]),
 TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),TREATAS({"2026:YTD"},'fm_native_periods'[PeriodKey]))'''
        expected=sum(e.old.old.available([lookup[("UK",s,"market","Units",i)] for s in e.old.old.ALL_SECTORS]) for i in range(24,31))
        return db,[{'name':'mixed-cutoffs','query':query}],{'cut':'2026-07','plan':expected}
    if variant=="overlays":
        query='''EVALUATE SUMMARIZECOLUMNS('fm_native_lines'[LineKind],
 TREATAS({"UK"},'fm_review_files'[Country]),TREATAS({"2026-10"},'fm_review_files'[DemandCycle]),
 TREATAS({"2026-10"},'fm_native_lines'[DemandCycle]),TREATAS({"Total"},'fm_native_view'[View]),
 TREATAS({"demand"},'fm_native_lines'[Chart]),TREATAS({"Units"},'fm_native_display'[Display]),
 TREATAS({6,12,24},'fm_native_lines'[LineKind]),
 TREATAS({"Automatic ADS"},'fm_native_file_mode'[Mode]),TREATAS({12,24},'fm_native_trend'[Window]),
 TREATAS({DATE(2026,12,1)},'fm_review_axis'[Month]),"V",[N Chart Monthly])'''
        expected={}
        for window in (12,24):
            values=[e.old.old.available([lookup[("UK",s,"market","Units",i)] for s in e.old.old.ALL_SECTORS]) for i in range(32-window,32)]
            mx=(window-1)/2;my=sum(values)/window
            slope=sum((i-mx)*(v-my) for i,v in enumerate(values))/sum((i-mx)**2 for i in range(window))
            expected[window]=my+slope*(window+3-mx)
        return db,[{'name':'multi-trend-overlay','query':query}],expected
    if variant=="sectors":
        query=next(q['query'] for q in queries if q['name']=='visual/sop-groups').replace('{"Drivers"}','{"Sectors"}')
        expected={(s or 'No forecast tier')+' – '+('Example Paed' if s=='Example C' else 'Example Oral'):
            sum(lookup[("UK",s,"market","Units",i)] for i in range(24,36)) for s in e.old.old.ALL_SECTORS}
        return db,[{'name':'sop-sector-groups','query':query}],expected
    raise ValueError(variant)


def verify(variant,results,expected):
    failures=[]
    for r in results:
        if 'error' in r:failures.append(r['error'])
    row=results[0].get('rows',[{}])[0]
    if variant=='signed':
        import math
        if not isinstance(row.get('[V]'),(int,float)) or not math.isclose(row['[V]'],expected['percentage'],abs_tol=1e-9):failures.append('Signed variance must be -20%')
    elif variant=='mixed':
        if row.get('[Cut]')!=expected['cut'] or row.get('[Plan]')!=expected['plan']:failures.append('Mixed cutoff plan window mismatch')
        if row.get('[Fit]') is not None or row.get('[Variance]') is not None:failures.append('Mixed cutoff trend must remain unavailable')
    elif variant in {'overlays','sectors'}:
        import math
        key='fm_native_lines[LineKind]' if variant=='overlays' else 'fm_native_groups[ScopeLabel]'
        actual={r[key]:r['[V]'] for r in results[0].get('rows',[])}
        if set(actual)!=set(expected):failures.append('Unexpected overlay/sector population')
        for k,value in expected.items():
            if k not in actual or not math.isclose(actual[k],value,rel_tol=1e-9):failures.append('Overlay/sector arithmetic mismatch')
    return {'Variant':variant,'Failures':failures,'Rows':sum(len(q.get('rows',[])) for q in results),
            'SyntheticOnly':True,'ReceivingPerformanceOrUI':'PENDING'}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('variant',choices=['before','after','signed','mixed','overlays','sectors']);p.add_argument('directory',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    db,queries,expected=build(a.variant)
    if a.verify:
        result=verify(a.variant,json.loads(a.verify.read_text(encoding='utf-8-sig')),expected)
        result['RetainedInputMatches']=json.loads((a.directory/'synthetic-model.json').read_text())==db
        if not result['RetainedInputMatches']:result['Failures'].append('Engine input differs')
        print(json.dumps(result,indent=2));raise SystemExit(bool(result['Failures']))
    a.directory.mkdir(parents=True,exist_ok=True)
    (a.directory/'synthetic-model.json').write_text(json.dumps(db,ensure_ascii=False))
    (a.directory/'queries.json').write_text(json.dumps(queries))
    for name in ('fx-queries','edge-queries'):(a.directory/(name+'.json')).write_text('[]')
