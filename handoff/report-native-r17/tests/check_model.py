"""Bounded structural and preservation checks; no live model access."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import native_model as m
from installation import render

before={'name':'Synthetic','model':{'culture':'en-GB','tables':[{'name':'fm_review_facts','columns':[{'name':'Amount','dataType':'double'}],
 'partitions':[{'name':'facts','mode':'directLake','source':{'type':'entity','entityName':'fm_review_facts','schemaName':'dbo','expressionSource':'Source'}}]}],
 'roles':[{'name':'Synthetic restricted role','modelPermission':'read','tablePermissions':[{'name':'fm_review_facts','filterExpression':'FALSE()'}]}],
 'expressions':[{'name':'Source','kind':'m','expression':'Sql.Database("synthetic.invalid","synthetic")'}]}}
snapshot=deepcopy(before);after=m.extend_model(before)
assert before==snapshot
assert after['model']['tables'][0]==before['model']['tables'][0]
assert after['model']['roles']==before['model']['roles']
assert after['model']['expressions']==before['model']['expressions']
assert all(t['name'].startswith(m.PREFIX) for t in after['model']['tables'][1:])
assert all(r['fromTable'].startswith(m.PREFIX) and r['toTable'].startswith(m.PREFIX) for r in after['model']['relationships'])
for unsupported in ['import','directQuery']:
    item=deepcopy(before);item['model']['tables'][0]['partitions'][0]['mode']=unsupported
    try:m.extend_model(item)
    except ValueError:pass
    else:raise AssertionError('Unsupported storage mode silently accepted.')
try:m.extend_model(after)
except ValueError:pass
else:raise AssertionError('Existing native objects were silently overwritten.')
state=m.static_tables()['state'];keys=[r['Token'] for r in state]
assert len(keys)==len(set(keys))
assert len(m.catalog_rows())==36
assert {r['RowID'] for r in m.catalog_rows()}==set(m.ORDER)
assert not any(k in m.SQL_VIEWS for k in ['.Amount','MissingCells','DELETE ','DROP ','ALTER TABLE'])
assert m.SQL_VIEWS.count('CREATE VIEW ')==5
for column,sort in [('Channel','ChannelRank'),('SubChannel','SubRank'),('Measure','MeasureRank')]:
    seen={}
    for r in state:
        if r[column] in seen:assert seen[r[column]]==r[sort]
        seen[r[column]]=r[sort]
cell=render('00000000-0000-0000-0000-000000000001','00000000-0000-0000-0000-000000000002','00000000-0000-0000-0000-000000000003')
ast.parse(cell)
assert 'MODE = "PROBE"' in cell and "'allowPurgeData':False" in cell
assert 'lease.acquire()' in cell and 'lease.release()' in cell
assert '/getDefinition?format=TMSL' in cell
assert '.publish' not in cell and '/reports/' not in cell
result={'Status':'PASS','StaticStateTokens':len(keys),'NativeBusinessMeasures':len(m.measures()),'AdditiveTables':len(after['model']['tables'])-1,
        'OldTablesAndSecurityPreserved':True,'UnsupportedModesAndConflictsRefused':True,'PrivateNotebookDefaultsToProbe':True,
        'CompanyExecution':False}
out=Path(__file__).resolve().parent.parent/'VALIDATION-STRUCTURE.json';out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
