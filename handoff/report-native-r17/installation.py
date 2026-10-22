"""Render a private, default-read-only Fabric notebook cell.

This module never contacts Fabric. The generated cell requires the receiving
operator's existing authenticated notebook context. PREPARE/APPLY are separate
explicit operator actions; no credentials or tenant-admin setup is introduced.
"""
from __future__ import annotations
import ast
import base64
import json
from pathlib import Path
import re
import zlib
from native_model import static_tables, measures, SQL_VIEWS, extend_model

HERE=Path(__file__).resolve().parent

RUNTIME=r'''
import base64,copy,hashlib,json,re,time,zlib
from datetime import datetime,timezone
from uuid import uuid4
import sempy.fabric as fabric
import notebookutils
import requests
from typing import Any,Callable
from datetime import UTC
from email.utils import format_datetime
from urllib.parse import quote
from uuid import UUID
__LEASE_CLASS__

# PROBE reads model metadata only. It does not create tables or change the model.
# PREPARE creates NEW native metadata tables only, then stops for the SQL step.
# APPLY adds the native definitions only after the SQL views exist and are tested.
MODE = "PROBE"
WORKSPACE = __WORKSPACE__
MODEL = __MODEL__
LAKEHOUSE = __LAKEHOUSE__
SPEC=json.loads(zlib.decompress(base64.b64decode(__SPEC__)))
ROOT=f'abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}'
BASE=f'/v1/workspaces/{WORKSPACE}/semanticModels/{MODEL}'

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()

def complete(client,response,result=False):
    response.raise_for_status()
    if response.status_code!=202:return response.json() if response.content else {}
    location=response.headers.get('Location','')
    if not re.fullmatch(r'https://api\.fabric\.microsoft\.com/v1/operations/[0-9a-fA-F-]+',location):
        raise RuntimeError('Unexpected operation URL. Outcome must be inspected; do not retry blindly.')
    operation=location.removeprefix('https://api.fabric.microsoft.com')
    deadline=time.monotonic()+360
    while time.monotonic()<deadline:
        time.sleep(min(30,max(1,int(response.headers.get('Retry-After','5')))))
        response=client.get(operation);response.raise_for_status();state=response.json()
        if state.get('status')=='Succeeded':
            if not result:return state
            received=client.get(operation+'/result');received.raise_for_status();return received.json()
        if state.get('status') in {'Failed','Cancelled','Canceled'}:
            raise RuntimeError('Native model operation failed. Inspect the retained backup and operation in Fabric.')
    raise TimeoutError('Operation not confirmed. Inspect Fabric before retrying.')

def definition(client):
    return complete(client,client.post(BASE+'/getDefinition?format=TMSL'),True)['definition']

def database(parts):
    part=next((p for p in parts if p['path']=='model.bim'),None)
    if not part:raise ValueError('No TMSL model.bim returned; live model is unchanged.')
    return json.loads(base64.b64decode(part['payload']))

def extend(before):
    after=copy.deepcopy(before);model=after['model'];tables=model['tables']
    if any(t['name'].startswith('fm_native_') for t in tables):
        raise ValueError('Native objects already exist. Inspect receiving receipt; no blind overwrite.')
    fact=next(t for t in tables if t['name']=='fm_review_facts')
    if len(fact['partitions'])!=1:raise ValueError('Unexpected fact partition count.')
    partition=fact['partitions'][0]
    if partition.get('mode')!='directLake' or partition.get('source',{}).get('type')!='entity':
        raise ValueError('This candidate requires the existing Direct Lake SQL source. No storage-mode conversion performed.')
    source_expression=partition['source'].get('expressionSource')
    expressions=model.get('expressions',[])
    expression=next((e.get('expression','') for e in expressions if e['name']==source_expression),'')
    expression='\n'.join(expression) if isinstance(expression,list) else expression
    if not any(c in expression for c in ('Sql.Database','OneLake.SqlAnalytics')):
        raise ValueError('Direct Lake on SQL not confirmed. OneLake/other source requires a different native metadata route.')
    for item in SPEC['additions']:
        t=copy.deepcopy(item);p=copy.deepcopy(partition);p['name']=t['name'];p.pop('annotations',None)
        p['source']['entityName']=t['name'];p['source']['schemaName']='dbo';t['partitions']=[p];tables.append(t)
    model.setdefault('relationships',[]).extend(copy.deepcopy(SPEC['relationships']))
    # Explicit preservation check: old tables, roles and all other model properties.
    trimmed=copy.deepcopy(after);trimmed['model']['tables']=trimmed['model']['tables'][:-len(SPEC['additions'])]
    trimmed['model']['relationships']=trimmed['model']['relationships'][:-len(SPEC['relationships'])]
    if 'relationships' not in before['model']:trimmed['model'].pop('relationships')
    if trimmed!=before:raise AssertionError('Existing model mutation detected. No request sent.')
    return after

def run():
    if MODE not in {'PROBE','PREPARE','APPLY'}:raise ValueError('Unknown mode.')
    client=fabric.FabricRestClient();before=definition(client);db=database(before['parts'])
    facts=next(t for t in db['model']['tables'] if t['name']=='fm_review_facts')
    print(json.dumps({'Mode':MODE,'SourceStorageMode':facts['partitions'][0].get('mode'),
        'ExistingTablesPreserved':len(db['model']['tables']),'ExistingSecurityRolesRetained':len(db['model'].get('roles',[])),
        'AdditiveTables':len(SPEC['additions']),'ModelDefinitionSHA256':digest(before),
        'SourceAmountsRead':False,'ModelUpdated':False}))
    try:candidate=extend(db)
    except ValueError as error:
        if MODE!='PROBE':raise
        print(json.dumps({'CompatibleWithCurrentAdapter':False,'Reason':str(error),'ModelUpdated':False}))
        return
    if MODE=='PROBE':
        print('PROBE PASSED. Native Desktop/Service rendering, export, performance and company reconciliation remain unverified.');return
    if MODE=='PREPARE':
        location=spark.sql('DESCRIBE DETAIL fm_review_facts').select('location').first()['location']
        if not location.lower().startswith((ROOT+'/Tables/').lower()):
            raise ValueError('Attach this notebook to the EXISTING ForecastMaster lakehouse before preparing metadata.')
        for name,rows in SPEC['static'].items():
            full='fm_native_'+name
            if spark.catalog.tableExists(full):
                raise ValueError('A native table already exists: '+full+'. Inspect it rather than overwriting.')
        for name,rows in SPEC['static'].items():
            full='fm_native_'+name
            schema=', '.join(k+(' long' if isinstance(v,int) else ' string') for k,v in rows[0].items())
            spark.createDataFrame([tuple(r[k] for k in rows[0]) for r in rows],schema).write.format('delta').mode('errorifexists').saveAsTable(full)
        print('PREPARED native metadata only. Run NATIVE VIEWS.sql in the EXISTING lakehouse SQL endpoint. Verify all five views. Then use APPLY.');return
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())
    backup=ROOT+'/Files/ForecastMasterRefreshState/report-upgrades/Native-R17/'+stamp
    notebookutils.fs.mkdirs(backup)
    serialized=json.dumps(before,ensure_ascii=False)
    notebookutils.fs.put(backup+'/model-before.json',serialized,False)
    if notebookutils.fs.head(backup+'/model-before.json',len(serialized.encode())+1)!=serialized:
        raise RuntimeError('Backup readback failed. Model remains unchanged.')
    after=copy.deepcopy(before)
    model_part=next(p for p in after['parts'] if p['path']=='model.bim')
    model_part['payload']=base64.b64encode(json.dumps(candidate,ensure_ascii=False).encode()).decode()
    notebookutils.fs.put(backup+'/model-candidate.json',json.dumps(after,ensure_ascii=False),False)
    if digest(definition(client))!=digest(before):raise RuntimeError('Model changed concurrently. No overwrite performed.')
    result=complete(client,client.post(BASE+'/updateDefinition',json={'definition':after,'options':{'allowPurgeData':False}}))
    received=database(definition(client)['parts'])
    old_by_name={t['name']:t for t in db['model']['tables']}
    new_by_name={t['name']:t for t in received['model']['tables']}
    if any(new_by_name.get(k)!=v for k,v in old_by_name.items()) or received['model'].get('roles',[])!=db['model'].get('roles',[]):
        raise RuntimeError('Readback differs. Inspect private backup; do not publish the candidate.')
    print('APPLIED additive native definitions. Backup: '+backup)
    print('Keep production R16.6. Refresh/qualify the separate native candidate before any report replacement.')

if MODE=='PROBE':run()
else:
    lease=OneLakeQueueStore(WORKSPACE,LAKEHOUSE,notebookutils.credentials.getToken)
    if not lease.acquire():raise RuntimeError('Refresh worker is busy. Wait for it to finish; no native changes started.')
    try:run()
    finally:lease.release()
'''


def render(workspace,model,lakehouse):
    # Build model additions with a neutral template; runtime reuses the actual
    # existing source partition and explicitly preserves every existing object.
    template={'model':{'tables':[{'name':'fm_review_facts','partitions':[{'name':'facts','mode':'directLake','source':{'type':'entity','entityName':'fm_review_facts','schemaName':'dbo','expressionSource':'EXISTING'}}]}]}}
    extended=extend_model(template)
    additions=[{k:v for k,v in t.items() if k!='partitions'} for t in extended['model']['tables'][1:]]
    spec={'additions':additions,'static':static_tables(),'relationships':extended['model']['relationships']}
    payload=base64.b64encode(zlib.compress(json.dumps(spec,ensure_ascii=False).encode(),9)).decode()
    # Reuse the already qualified exclusive writer implementation verbatim.
    owner=HERE.parent/'report-gm-desktop-r16.6/SETUP REPORTING FEED.py'
    source=owner.read_text();tree=ast.parse(source)
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='OneLakeQueueStore')
    lease='\n'.join(source.splitlines()[cls.lineno-1:cls.end_lineno])
    return (RUNTIME.replace('__WORKSPACE__',repr(workspace)).replace('__MODEL__',repr(model))
            .replace('__LAKEHOUSE__',repr(lakehouse)).replace('__SPEC__',repr(payload)).replace('__LEASE_CLASS__',lease))


if __name__=='__main__':
    raise SystemExit('Use build_delivery.py with the private R16.6 project. No network access occurs here.')
