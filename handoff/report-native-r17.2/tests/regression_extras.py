"""Run the frozen independent FX/export oracles against revised native DAX."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import engine_fixture as e

sys.path.insert(0,str(e.HERE.parent/'report-native-r17/tests'))
import fx_cases
import edge_cases


def inputs():
    db,*_=e.build()
    fx=json.loads(json.dumps(fx_cases.cases()).replace('fm_review_periods','fm_native_periods'))
    edges=edge_cases.queries()
    for q in edges:
        q['query']=q['query'].replace('fm_review_periods','fm_native_periods')
        if q['name'].startswith('blank-tier-'):
            # Real line-chart queries group by cycle-bearing LineLabel. The
            # frozen scalar edge query instead needs this explicit cycle scope.
            q['query']=q['query'].replace(',"Amount",',',TREATAS({"2026-10"},\'fm_native_lines\'[DemandCycle]),"Amount",')
    return {'synthetic-model':db,'queries':[],'fx-queries':fx,'edge-queries':edges}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args()
    values=inputs();a.directory.mkdir(exist_ok=True,parents=True)
    if not a.verify:
        for name,value in values.items():(a.directory/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False))
    else:
        for name,value in values.items():
            if json.loads((a.directory/(name+'.json')).read_text())!=value:raise SystemExit('Retained input differs: '+name)
        receipts=[]
        for stem,script,receipt in (('fx-queries','fx_cases.py','VALIDATION-NATIVE-FX.json'),('edge-queries','edge_cases.py','VALIDATION-NATIVE-EDGES.json')):
            results=json.loads((a.verify/(stem+'-results.json')).read_text(encoding='utf-8-sig'))
            # Adapt field names only; preserve all engine numbers and blank cells.
            adapted=a.directory/(stem+'-oracle-adapted.json')
            adapted.write_text(json.dumps(results).replace('fm_native_periods[','fm_review_periods['))
            subprocess.run([sys.executable,str(e.HERE.parent/'report-native-r17/tests'/script),str(a.directory),str(adapted)],check=True)
            receipts.append(json.loads((a.directory/receipt).read_text()))
        print(json.dumps({'Checks':sum(r['Checks'] for r in receipts),'Failures':[f for r in receipts for f in r['Failures']],
                          'RetainedInputMatches':True},indent=2))
