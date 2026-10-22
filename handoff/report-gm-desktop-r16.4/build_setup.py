"""Create a self-contained, user-run additive reporting-rule setup cell."""
from pathlib import Path
import csv,io,json,sys
HERE=Path(__file__).resolve().parent
sys.dont_write_bytecode=True
sys.path.insert(0,str(HERE.parent/'report-cycle-cache-r04.2/baseline'))
from contract import rules,RULE_FIELDS
bridge=json.loads((HERE.parents[1]/'design/currency-plan-review-r15/bridge-catalog.json').read_text())
additions=[]
for name in ['abbott','market','pi','net','community','ads']:
    b=next(b for b in bridge['bindings'] if b['id']==name)
    for display in ['units','value']:
        identity='leaf' if name=='wholesaler' else name
        component='gm-'+identity+'-'+display
        row=dict(zip(RULE_FIELDS,[component,'GM S&OP',b[display]['role'],'Units' if display=='units' else '£','SUM',b['basis'],component,b[display]['section'],b[display]['measure'],'*','false','','','','','false',str(1000+len(additions)*10)],strict=True))
        additions.append(row)
worker=(HERE.parent/'notebook-r05.4/Refresh/source/request_worker.py').read_text()
store=worker[worker.index('class OneLakeQueueStore:'):worker.index('\n\nclass RequestWorker:')]
text='''# Run in a separate, unscheduled Fabric Python notebook attached to ForecastMaster.
# This updates only reporting definitions. It does not start a worker or publish a report.
import csv, io, json, hashlib, requests, re
from typing import Any, Callable
from datetime import datetime, UTC
from email.utils import format_datetime
from urllib.parse import quote
from uuid import UUID, uuid4
WORKSPACE = "__WORKSPACE__"
LAKEHOUSE = "__LAKEHOUSE__"
'''+store+'''
FIELDS = '''+repr(RULE_FIELDS)+'''
BASE = '''+repr(rules())+'''
ADDITIONS = '''+repr(additions)+'''

def prepare_rules(existing):
    rows=list(csv.DictReader(io.StringIO(existing))) if existing is not None else list(BASE)
    if not rows or any(set(r)!=set(FIELDS) for r in rows):
        raise ValueError('Existing report rules have an unknown schema; no file changed.')
    keys=[r['MetricKey'] for r in rows]
    if len(keys)!=len(set(keys)):raise ValueError('Duplicate metric identities; no file changed.')
    for row in ADDITIONS:
        old=next((r for r in rows if r['MetricKey']==row['MetricKey']),None)
        if old is not None and old!=row:raise ValueError('Existing GM rule differs: '+row['MetricKey'])
        if old is None:rows.append(row)
    definitions={}
    for row in rows:
        for part in ['Numerator','Denominator']:
            key=row[part+'Key']
            if not key:continue
            spec=tuple(row[part+k] for k in ['Section','Measure','Manufacturer','RequireProduct'])
            if key in definitions and definitions[key]!=spec:raise ValueError('Conflicting component '+key)
            definitions[key]=spec
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=FIELDS,lineterminator='\\n');w.writeheader();w.writerows(rows)
    return out.getvalue(),len(rows)

def main():
    if WORKSPACE.startswith('__') or LAKEHOUSE.startswith('__'):raise ValueError('Use the company-bound setup file in the private delivery ZIP.')
    root=f'abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}'
    path=root+'/Files/ForecastMasterControls/ReportMeasureRules.csv'
    store=OneLakeQueueStore(WORKSPACE,LAKEHOUSE,notebookutils.credentials.getToken)
    if not store.acquire():raise RuntimeError('Refresh worker is busy. Wait for it to finish and run this setup cell again.')
    try:
        existing=notebookutils.fs.head(path,1048576) if notebookutils.fs.exists(path) else None
        if existing is not None and len(existing.encode('utf-8'))>=1048576:raise ValueError('Rules exceed safe read limit; no file changed.')
        candidate,count=prepare_rules(existing)
        if candidate==existing:
            print('READY: GM reporting rules already present. No file changed.')
            return
        stamp=datetime.now(UTC).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())
        backup=root+'/Files/ForecastMasterRefreshState/report-upgrades/GM-R16/'+stamp
        notebookutils.fs.mkdirs(backup)
        before=existing if existing is not None else ''
        notebookutils.fs.put(backup+'/rules-before.csv',before,False)
        notebookutils.fs.put(backup+'/receipt.json',json.dumps({'BeforeExisted':existing is not None,'BeforeSHA256':hashlib.sha256(before.encode()).hexdigest(),'AfterSHA256':hashlib.sha256(candidate.encode()).hexdigest(),'Rows':count}),False)
        if notebookutils.fs.head(backup+'/rules-before.csv',1048576)!=before:raise RuntimeError('Backup readback failed; live rules unchanged.')
        current=notebookutils.fs.head(path,1048576) if notebookutils.fs.exists(path) else None
        if current!=existing:raise RuntimeError('Rules changed concurrently; no overwrite performed.')
        notebookutils.fs.put(path,candidate,True)
        if notebookutils.fs.head(path,1048576)!=candidate:raise RuntimeError('Rule write outcome requires inspection; do not rerun blindly.')
        print('READY: added GM reporting measures; existing rules retained. Backup: '+backup)
        print('NEXT: click the existing native Refresh Demand button ONCE. Wait for SUCCESS and ModelRefresh COMPLETED before reviewing or publishing.')
    finally:store.release()

if __name__=='__main__':main()
'''
(HERE/'SETUP REPORTING FEED.py').write_text(text)
(HERE/'GM-RULES.json').write_text(json.dumps(additions,indent=2)+'\n')
print('Prepared',len(additions),'additional exact-identity reporting rules.')
