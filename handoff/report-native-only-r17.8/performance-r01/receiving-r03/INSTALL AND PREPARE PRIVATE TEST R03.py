"""ONE NEW company ForecastMaster_GM_Setup cell, existing TEST only, ONCE.
30 sequential paired scalars plus three no-file blanks; values never printed/stored.
Full private backup, exact installed R01 guard, one update/readback, private report
download with actual ADS defaults. No refresh/source/production write or publish.
STOPPED or uncertain: return JSON; do not retry, delete markers or refresh.
"""
import base64
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
from io import BytesIO
import json
import math
from numbers import Number
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote, urlsplit
from uuid import UUID, uuid4
from zipfile import ZipFile, ZIP_DEFLATED

WORKSPACE='f5cb5742-9a7c-4337-a4c0-952706dddf0b'

LAKEHOUSE='d6e33ebd-67b1-420a-8d84-c3a0d04d8b21'

TEST='31d00232-ac03-48fe-af39-f2e4bae82443'

NAME='ForecastMaster Native OneLake R17.1 - TEST'

FIELDS={'fm_review_files':['IMSActualsThrough','ExFactoryActualsThrough'],
        'fm_review_months':['Month'],'fm_review_axis':['Month'],'fm_review_facts':['Month']}

class CheckStopped(RuntimeError):
    def __init__(self,code):self.code=code

def require(ok,code):
    if not ok:raise CheckStopped(code)

def http(ctx,response,expected):
    code=response.status_code
    require(type(code) is int and 100<=code<=599,'HTTP_STATUS_INVALID')
    ctx['HTTPStatus']=code
    require(code in expected,'HTTP_NOT_EXPECTED')
    return response

def operation_path(headers):
    # The successful earlier company readers used x-ms-operation-id.
    # Never follow an arbitrary response URL or include header values in output.
    lowered={k.lower():v for k,v in headers.items()}
    token=lowered.get('x-ms-operation-id')
    if token is not None:
        try:return '/v1/operations/'+str(UUID(token))
        except (ValueError,TypeError,AttributeError):raise CheckStopped('OPERATION_ID_INVALID') from None
    location=lowered.get('location','')
    require(isinstance(location,str),'OPERATION_LOCATION_INVALID')
    parsed=urlsplit(location)
    require(not parsed.query and not parsed.fragment and not parsed.username and not parsed.password,
            'OPERATION_LOCATION_INVALID')
    require((parsed.scheme=='https' and parsed.netloc=='api.fabric.microsoft.com') or
            (not parsed.scheme and not parsed.netloc),'OPERATION_LOCATION_INVALID')
    suffix=None
    for prefix in ('/v1/operations/','/operations/'):
        if parsed.path.startswith(prefix):suffix=parsed.path[len(prefix):];break
    require(suffix is not None,'OPERATION_HEADER_MISSING_OR_UNSUPPORTED')
    try:return '/v1/operations/'+str(UUID(suffix))
    except (ValueError,TypeError,AttributeError):raise CheckStopped('OPERATION_LOCATION_INVALID') from None

def read_definition(client,ctx):
    ctx['Step']='DEFINITION_REQUEST'
    response=http(ctx,client.post('/v1/workspaces/'+WORKSPACE+'/semanticModels/'+TEST+'/getDefinition?format=TMSL'),{200,202})
    if response.status_code==202:
        ctx['Step']='DEFINITION_OPERATION_HEADER'
        operation=operation_path(response.headers)
        deadline=time.monotonic()+360
        poll=0
        while time.monotonic()<deadline:
            # Honor bounded Retry-After, as in the previously successful reader.
            try:delay=int(response.headers.get('Retry-After','5'))
            except (ValueError,TypeError):delay=5
            time.sleep(min(30,max(1,delay)))
            poll+=1
            ctx.update(Step='DEFINITION_OPERATION_POLL',PollCount=poll)
            response=http(ctx,client.get(operation),{200})
            state=response.json().get('status')
            ctx['OperationState']=state if state in {'NotStarted','Running','Succeeded','Failed','Cancelled','Canceled','Undefined'} else 'OTHER_WITHHELD'
            require(state not in {'Failed','Cancelled','Canceled'},'DEFINITION_OPERATION_FAILED')
            if state=='Succeeded':
                ctx['Step']='DEFINITION_RESULT'
                response=http(ctx,client.get(operation+'/result'),{200});break
            require(state in {'NotStarted','Running','Undefined'},'DEFINITION_OPERATION_STATE_UNKNOWN')
            if poll==1 or poll%6==0:
                print('Read-only R03: definition operation pending (poll '+str(poll)+').',flush=True)
        else:raise CheckStopped('DEFINITION_OPERATION_TIMEOUT')
    ctx['Step']='DEFINITION_DECODE'
    parts=response.json()['definition']['parts']
    values=[p for p in parts if p['path']=='model.bim']
    require(len(values)==1,'EXPECTED_ONE_MODEL_BIM')
    db=json.loads(base64.b64decode(values[0]['payload'],validate=True))
    tables={t['name']:t for t in db['model']['tables']}
    result={}
    def enum(value,allowed):return value if value in allowed else 'OTHER_WITHHELD'
    for table,columns in FIELDS.items():
        ctx['Step']='DEFINITION_DATE_BINDINGS'
        ctx['Table']=table
        require(table in tables,'EXPECTED_TABLE_MISSING')
        t=tables[table];part=t.get('partitions',[]);c={c['name']:c for c in t['columns']}
        require(set(columns)<=set(c),'EXPECTED_DATE_COLUMN_MISSING')
        source=part[0].get('source',{}) if len(part)==1 else {}
        result[table]={'PartitionCount':len(part),
          'Mode':enum(part[0].get('mode') if len(part)==1 else None,{'directLake','directQuery','import','default'}),
          'SourceType':enum(source.get('type'),{'entity','calculated','m','query','none'}),
          'EntityNameMatchesExpected':source.get('entityName')==table,
          'Columns':{name:{'ModelDataType':enum(c[name].get('dataType'),{'dateTime','string','int64','double','decimal','boolean'}),
            'ColumnKind':enum(c[name].get('type','data'),{'data','calculated','calculatedTableColumn'}),
            'SourceColumnMatchesExpected':c[name].get('sourceColumn')==
              ('['+name+']' if c[name].get('type')=='calculatedTableColumn' else name)} for name in columns}}
    return response.json()['definition'],db,result

ITEM='/v1/workspaces/'+WORKSPACE+'/items/'+TEST

KINDS={'SourceIMS','SourceEF','NativeIMS','NativeEF','Axis','Review','Start','End','Facts'}

DATE_QUERY='''EVALUATE
VAR _files=FILTER(ALL('fm_review_files'),'fm_review_files'[Country]="UK"&&'fm_review_files'[DemandCycle]="2026-10")
VAR _native=FILTER(ALL('fm_native_files'),'fm_native_files'[Country]="UK"&&'fm_native_files'[DemandCycle]="2026-10")
VAR _ids=SELECTCOLUMNS(_files,"ID",'fm_review_files'[SourceRevisionID])
VAR _facts=CALCULATETABLE(VALUES('fm_review_facts'[Month]),TREATAS(_ids,'fm_review_facts'[SourceRevisionID]))
RETURN UNION(
 SELECTCOLUMNS(_files,"Kind","SourceIMS","ID",'fm_review_files'[SourceRevisionID]&"","D",'fm_review_files'[IMSActualsThrough]),
 SELECTCOLUMNS(_files,"Kind","SourceEF","ID",'fm_review_files'[SourceRevisionID]&"","D",'fm_review_files'[ExFactoryActualsThrough]),
 SELECTCOLUMNS(_native,"Kind","NativeIMS","ID",'fm_native_files'[SourceRevisionID]&"","D",'fm_native_files'[IMSActualsThrough]),
 SELECTCOLUMNS(_native,"Kind","NativeEF","ID",'fm_native_files'[SourceRevisionID]&"","D",'fm_native_files'[ExFactoryActualsThrough]),
 SELECTCOLUMNS(VALUES('fm_review_axis'[Month]),"Kind","Axis","ID","","D",'fm_review_axis'[Month]),
 SELECTCOLUMNS(VALUES('fm_review_months'[Month]),"Kind","Review","ID","","D",'fm_review_months'[Month]),
 SELECTCOLUMNS(VALUES('fm_native_start_month'[Month]),"Kind","Start","ID","","D",'fm_native_start_month'[Month]),
 SELECTCOLUMNS(VALUES('fm_native_end_month'[Month]),"Kind","End","ID","","D",'fm_native_end_month'[Month]),
 SELECTCOLUMNS(_facts,"Kind","Facts","ID","","D",'fm_review_facts'[Month]))'''

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()

def identity(client,ctx):
    ctx['Step']='TEST_IDENTITY'
    item=http(ctx,client.get(ITEM),{200}).json()
    require(item.get('id')==TEST and item.get('displayName')==NAME and item.get('type')=='SemanticModel','TEST_IDENTITY_MISMATCH')

def routing(db,bindings):
    tables={t['name']:t for t in db['model']['tables']}
    expressions={e['name']:e.get('expression','') for e in db['model'].get('expressions',[])}
    for table,columns in FIELDS.items():
        b=bindings[table]
        require(b['PartitionCount']==1 and b['Mode']=='directLake' and b['SourceType']=='entity' and
                b['EntityNameMatchesExpected'],'SOURCE_BINDING_UNEXPECTED')
        require(all(b['Columns'][name]['ModelDataType']=='dateTime' and
                    b['Columns'][name]['SourceColumnMatchesExpected'] for name in columns),'DATE_BINDING_UNEXPECTED')
        source=tables[table]['partitions'][0]['source']
        expr=expressions.get(source.get('expressionSource'),'')
        if isinstance(expr,list):expr='\n'.join(expr)
        require(isinstance(expr,str) and 'azurestorage.datalake' in expr.lower() and
                WORKSPACE in expr.lower() and LAKEHOUSE in expr.lower(),'KNOWN_LAKEHOUSE_ROUTE_UNPROVEN')
    require('fm_native_files' in tables and 'fm_native_measures' in tables,'NATIVE_TEST_TABLES_MISSING')

def connections(client,ctx):
    ctx['Step']='CLOUD_MAPPING_READ';values=[];token=None;seen=set()
    for _ in range(100):
        path=ITEM+'/connections'+('?continuationToken='+quote(token,safe='') if token else '')
        page=http(ctx,client.get(path),{200}).json()
        require(isinstance(page.get('value'),list),'CLOUD_MAPPING_SHAPE_UNEXPECTED')
        values.extend(page['value']);token=page.get('continuationToken')
        if not token:return sorted(values,key=digest)
        require(isinstance(token,str) and token not in seen,'CLOUD_MAPPING_PAGINATION_UNEXPECTED');seen.add(token)
    raise CheckStopped('CLOUD_MAPPING_INCOMPLETE')

def as_date(value):
    if isinstance(value,datetime):
        if (value.hour,value.minute,value.second,value.microsecond)!=(0,0,0,0):return None
        try:return value.date().isoformat()
        except (ValueError,TypeError):return None
    if isinstance(value,date):return value.isoformat()
    return None

def semantic_dates(evaluate,ctx):
    ctx['Step']='SEMANTIC_DATE_READ'
    frame=evaluate(dataset=TEST,dax_string=DATE_QUERY,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False)
    records=frame.to_dict(orient='records');require(0<len(records)<=10000,'SEMANTIC_METADATA_SIZE_UNEXPECTED')
    result={kind:[] for kind in KINDS}
    for record in records:
        row={name.rsplit('[',1)[-1].rstrip(']'):value for name,value in record.items()}
        require(set(row)=={'Kind','ID','D'} and row['Kind'] in KINDS,'SEMANTIC_METADATA_FIELDS_UNEXPECTED')
        require(isinstance(row['ID'],str),'SEMANTIC_ID_TYPE_UNEXPECTED')
        result[row['Kind']].append((row['ID'],as_date(row['D'])))
    return result

def verified_backup(fs,path,value):
    raw=json.dumps(value,ensure_ascii=False);expected=raw.encode()
    require(fs.put(path,raw,False),'PRIVATE_BACKUP_WRITE_FAILED')
    with TemporaryDirectory(prefix='fm-date-reset-') as temp:
        local=Path(temp)/'backup.json'
        require(fs.cp(path,local.as_uri(),False),'PRIVATE_BACKUP_COPY_FAILED')
        observed=local.read_bytes()
        require(len(observed)==len(expected) and hashlib.sha256(observed).digest()==hashlib.sha256(expected).digest(),
                'PRIVATE_BACKUP_FULL_UTF8_VERIFICATION_FAILED')

def safe_failure(exc):
    # Inspect privately; output fixed allowlisted categories only, never messages.
    family = type(exc).__name__
    if family not in {'CheckStopped', 'RuntimeError', 'ValueError', 'TypeError', 'KeyError',
                      'TimeoutError', 'FabricAdomdException', 'ConnectionError', 'KeyboardInterrupt'}:
        family = 'OTHER_WITHHELD'
    signals = []
    try:
        raw = str(exc).lower()[:100000]
        for name, tokens in (
            ('MEMORY_LIMIT', ('memory limit', 'available resources', 'rsquerymemorylimitexceeded')),
            ('CANCELLED', ('cancelled', 'canceled', 'cancelation')),
            ('TIMEOUT', ('timeout', 'timed out')),
            ('ACCESS_OR_AUTHENTICATION', ('forbidden', 'unauthorized', 'permission')),
            ('QUERY_SYNTAX_OR_DEFINITION', ('syntax', 'semanticquerydefinition', 'cannot find', 'not found')),
            ('PROCESSING_REQUIRED', ('not processed', 'needs to be processed'))):
            if any(token in raw for token in tokens): signals.append(name)
    except Exception:
        signals=[]  # Error rendering must not expose private details.
    return {'Reason': exc.code if isinstance(exc, CheckStopped) else 'EXCEPTION_WITHHELD',
            'ExceptionFamily': family, 'KnownSignals': signals, 'RawErrorPrintedOrStored': False}

def expression_text(value):
    if isinstance(value,str):return value
    if isinstance(value,list) and all(isinstance(line,str) for line in value):return "\n".join(value)
    raise ValueError("Invalid expression representation")

def normalized(database):
    """Only identical DAX/M line-array representation is equivalent.

    Never remove unrelated metadata/defaults or sort arrays to make a match.
    """
    result=deepcopy(database)
    def walk(value):
        if isinstance(value,dict):
            for key,item in value.items():
                if key=="expression" and isinstance(item,(str,list)):
                    value[key]=expression_text(item)
                else:walk(item)
        elif isinstance(value,list):
            for item in value:walk(item)
    walk(result)
    return result

def processing_history(pbi):
    rows=http({},pbi.get('https://api.powerbi.com/v1.0/myorg/groups/'+WORKSPACE+'/datasets/'+TEST+'/refreshes?$top=60'),{200}).json().get('value')
    require(isinstance(rows,list) and rows,'TEST_PROCESSING_HISTORY_UNAVAILABLE')
    require(all(row.get('status') in {'Completed','Failed','Disabled','Cancelled','Canceled','TimedOut'} for row in rows),
      'TEST_PROCESSING_ACTIVE_OR_UNKNOWN')
    return rows

def complete_update(client,response,ctx,save_operation):
    http(ctx,response,{200,202})
    if response.status_code==200:return
    operation=operation_path(response.headers)
    save_operation({'Operation':operation})
    deadline=time.monotonic()+600
    while time.monotonic()<deadline:
        try:delay=int(response.headers.get('Retry-After','5'))
        except (TypeError,ValueError):delay=5
        time.sleep(min(30,max(1,delay)))
        response=http(ctx,client.get(operation),{200})
        status=response.json().get('status')
        require(status in {'NotStarted','Running','Undefined','Succeeded','Failed','Cancelled','Canceled'},'UPDATE_OPERATION_STATE_UNKNOWN')
        if status=='Succeeded':return
        require(status not in {'Failed','Cancelled','Canceled'},'UPDATE_OPERATION_FAILED')
    raise CheckStopped('UPDATE_OPERATION_TIMEOUT_NO_RETRY')

def date_signature(evaluate):
    # DAX rowset order is not an identity or a concurrency signal.
    return {kind:sorted(values) for kind,values in semantic_dates(evaluate,{}).items()}

def validate_dates(evaluate):
    rows=semantic_dates(evaluate,{})
    counts={kind:len(values) for kind,values in rows.items()}
    require(set(rows)==KINDS and all(counts.values()),'DATE_GROUP_MISSING')
    require(all(day is not None and '2000-01-01'<=day<'2100-01-01' and day.endswith('-01')
      for values in rows.values() for _,day in values),'SEMANTIC_DATES_INVALID')
    require(set(rows['SourceIMS'])==set(rows['NativeIMS']) and set(rows['SourceEF'])==set(rows['NativeEF']),
      'SOURCE_NATIVE_DATES_DIFFER')
    require(all(set(rows[k])==set(rows['Axis']) for k in ('Review','Start','End','Facts')),'MONTH_SETS_DIFFER')
    return {'Groups':len(counts),'InvalidDates':0,'MatchingSourceNativeAndMonthSets':True}

EXPECTED_NATIVE = {'N Display': {'expression': 'SELECTEDVALUE(\'fm_native_display\'[Display],"Units")', 'formatString': ''},
 'N Catalog Visible': {'expression': "IF(SELECTEDVALUE('fm_native_catalog'[Display])=[N Display],1)",
                       'formatString': '0'},
 'N Catalog Available': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                       "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                       "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                       'VAR _custom = '
                                       'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                       'files","Automatic ADS") = "Selected files"\n'
                                       'VAR _scenario = '
                                       "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                       'VAR _chosen = '
                                       "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                       "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                       "'fm_native_files'[Country] IN _country\n"
                                       " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                       " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                       "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                       'VAR _driver = '
                                       'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                       "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                       '_driver)\n'
                                       'VAR _files = FILTER(_pool, IF(_custom, '
                                       "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                       "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                       " 'fm_native_files'[PreferenceRank]=1 && "
                                       "'fm_native_files'[PreferenceTies]=1))\n"
                                       'VAR _ids = '
                                       'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       'VAR _scope = '
                                       "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                       "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                       'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                       'VAR _cohorts = '
                                       "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                       'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                       'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                       ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                       ' && (NOT _custom || '
                                       "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                       'VAR '
                                       "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                       'VAR '
                                       '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       "VAR _component=SELECTEDVALUE('fm_native_catalog'[Component])\n"
                                       "VAR _channel=SELECTEDVALUE('fm_native_catalog'[Channel])\n"
                                       "VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])\n"
                                       'RETURN '
                                       "IF(CALCULATE(COUNTROWS('fm_review_facts'),REMOVEFILTERS('fm_review_facts'),\n"
                                       ' '
                                       "TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                       " TREATAS({_channel},'fm_review_facts'[Channel]),\n"
                                       ' '
                                       'FILTER(ALL(\'fm_review_facts\'[SubChannel]),COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub))>0,1)',
                         'formatString': '0'},
 'N Source Caption': {'expression': 'VAR _c=[N Cutoff]\n'
                                    'RETURN IF([N Source '
                                    'OK]=1&&(ISBLANK(_c)||_c<DATE(2000,1,1)||_c>=DATE(2100,1,1)),\n'
                                    ' "Cutoff metadata unavailable · investigate source/native dates",\n'
                                    'IF(IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                    'files","Automatic ADS")="Selected files",\n'
                                    " IF(ISFILTERED('fm_native_files'[FileChoiceLabel]),\n"
                                    ' "Selected files · '
                                    '"&FORMAT(COUNTROWS(INTERSECT(VALUES(\'fm_review_files\'[SourceRevisionID]),\n'
                                    ' VALUES(\'fm_native_files\'[SourceRevisionID]))),"0")&" file(s) · '
                                    'comparisons separated by saved scenario",\n'
                                    ' "Choose saved files below"),\n'
                                    "VAR _country = VALUES('fm_review_files'[Country])\n"
                                    "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                    "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                    'VAR _custom = '
                                    'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                    'files","Automatic ADS") = "Selected files"\n'
                                    'VAR _scenario = '
                                    "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                    'VAR _chosen = '
                                    "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                    "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                    "'fm_native_files'[Country] IN _country\n"
                                    " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                    " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                    "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                    'VAR _driver = '
                                    'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                    "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                    '_driver)\n'
                                    'VAR _files = FILTER(_pool, IF(_custom, '
                                    "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                    "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                    " 'fm_native_files'[PreferenceRank]=1 && "
                                    "'fm_native_files'[PreferenceTies]=1))\n"
                                    'VAR _ids = '
                                    'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                    'VAR _scope = '
                                    "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                    "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                    'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                    'VAR _cohorts = '
                                    "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                    'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                    'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                    ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                    ' && (NOT _custom || '
                                    "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                    "VAR _ims=SUMMARIZE(_files,'fm_native_files'[IMSActualsThrough])\n"
                                    "VAR _ef=SUMMARIZE(_files,'fm_native_files'[ExFactoryActualsThrough])\n"
                                    'RETURN IF(NOT _sourceOK,"Choose an available source for every selected '
                                    'driver.",\n'
                                    ' IF(_custom,"Selected versions","ADS automatic")&" · '
                                    '"&FORMAT(COUNTROWS(_files),"0")&" source(s) · IMS through "&\n'
                                    ' '
                                    'IF(COUNTROWS(_ims)=1,IF(MAXX(_ims,\'fm_native_files\'[IMSActualsThrough])>=DATE(2000,1,1)&&MAXX(_ims,\'fm_native_files\'[IMSActualsThrough])<DATE(2100,1,1),FORMAT(MAXX(_ims,\'fm_native_files\'[IMSActualsThrough]),"mmm '
                                    'yy"),"unavailable"),"mixed cutoffs")&\n'
                                    ' " · Ex-factory through '
                                    '"&IF(COUNTROWS(_ef)=1,IF(MAXX(_ef,\'fm_native_files\'[ExFactoryActualsThrough])>=DATE(2000,1,1)&&MAXX(_ef,\'fm_native_files\'[ExFactoryActualsThrough])<DATE(2100,1,1),FORMAT(MAXX(_ef,\'fm_native_files\'[ExFactoryActualsThrough]),"mmm '
                                    'yy"),"unavailable"),"mixed cutoffs"))))',
                      'formatString': ''},
 'N Source OK': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                               "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                               "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                               'VAR _custom = '
                               'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                               'files","Automatic ADS") = "Selected files"\n'
                               'VAR _scenario = '
                               "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                               'VAR _chosen = '
                               "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                               "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                               "'fm_native_files'[Country] IN _country\n"
                               " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                               " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                               "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                               'VAR _driver = '
                               'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                               "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                               '_driver)\n'
                               "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] "
                               "IN _chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                               " 'fm_native_files'[PreferenceRank]=1 && "
                               "'fm_native_files'[PreferenceTies]=1))\n"
                               'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                               'VAR _scope = '
                               "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                               "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                               'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                               'VAR _cohorts = '
                               "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                               'VAR _sourceOK = COUNTROWS(_files)>0 && '
                               'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                               ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                               ' && (NOT _custom || '
                               "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                               'RETURN INT(_sourceOK)',
                 'formatString': '0'},
 'N Scenario Visible': {'expression': 'IF(SELECTEDVALUE(\'fm_native_scenario\'[Mode])=IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                      'files","Automatic ADS")&&[N Source OK]=1,1)',
                        'formatString': '0'},
 'N Scope Available': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                     "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                     "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                     'VAR _custom = '
                                     'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                     'files","Automatic ADS") = "Selected files"\n'
                                     'VAR _scenario = '
                                     "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                     'VAR _chosen = '
                                     "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                     "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                     "'fm_native_files'[Country] IN _country\n"
                                     " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                     " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                     "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                     'VAR _driver = '
                                     'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                     "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                     '_driver)\n'
                                     'VAR _files = FILTER(_pool, IF(_custom, '
                                     "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                     "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                     " 'fm_native_files'[PreferenceRank]=1 && "
                                     "'fm_native_files'[PreferenceTies]=1))\n"
                                     'VAR _ids = '
                                     'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                     'VAR _scope = '
                                     "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                     "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                     'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                     'VAR _cohorts = '
                                     "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                     'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                     'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                     ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                     ' && (NOT _custom || '
                                     "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                     'VAR '
                                     "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                     'VAR '
                                     '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                     'RETURN '
                                     "IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                     'IN _candidateIds))>0,1)',
                       'formatString': '0'},
 'N Period Available': {'expression': "VAR _start=MIN('fm_native_start_month'[Month]) VAR "
                                      "_end=MAX('fm_native_end_month'[Month])\n"
                                      "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                      'RETURN IF(NOT ISBLANK(_start)&&NOT ISBLANK(_end)&&_start<=_end&&NOT '
                                      'ISBLANK(_y)&&_y>=YEAR(_start)&&_y<=YEAR(_end),1)',
                        'formatString': '0'},
 'N Cutoff': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                            "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                            "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                            'VAR _custom = '
                            'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                            'files","Automatic ADS") = "Selected files"\n'
                            'VAR _scenario = '
                            "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                            'VAR _chosen = '
                            "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                            "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] "
                            'IN _country\n'
                            " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                            " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                            "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                            'VAR _driver = '
                            'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                            "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                            "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN "
                            "_chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                            " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                            'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                            'VAR _scope = '
                            "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                            "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                            'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                            'VAR _cohorts = '
                            "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                            'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                            ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                            ' && (NOT _custom || '
                            "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                            'VAR '
                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                            'VAR _ef=IF(_row IN {"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                            'VAR '
                            '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                            'RETURN IF(_sourceOK && '
                            'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0 '
                            '&& COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])))=0,MINX(_dates,[Cutoff]))',
              'formatString': 'mmm yyyy'},
 'N Monthly Numerator': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                       "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                       "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                       'VAR _custom = '
                                       'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                       'files","Automatic ADS") = "Selected files"\n'
                                       'VAR _scenario = '
                                       "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                       'VAR _chosen = '
                                       "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                       "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                       "'fm_native_files'[Country] IN _country\n"
                                       " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                       " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                       "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                       'VAR _driver = '
                                       'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                       "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                       '_driver)\n'
                                       'VAR _files = FILTER(_pool, IF(_custom, '
                                       "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                       "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                       " 'fm_native_files'[PreferenceRank]=1 && "
                                       "'fm_native_files'[PreferenceTies]=1))\n"
                                       'VAR _ids = '
                                       'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                       'VAR _scope = '
                                       "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                       "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                       'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                       'VAR _cohorts = '
                                       "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                       'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                       'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                       ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                       ' && (NOT _custom || '
                                       "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                       "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                       'VAR '
                                       '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                       'VAR _display=[N Display]\n'
                                       'VAR '
                                       "_definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row "
                                       "&& 'fm_native_catalog'[Display]=_display)\n"
                                       'VAR _component=IF(_row="ef","ef-ads-" & '
                                       "LOWER(_display),MAXX(_definition,'fm_native_catalog'[Component]))\n"
                                       'VAR '
                                       '_channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                                       'VAR '
                                       '_sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                                       'VAR _value=_display="Value"\n'
                                       'VAR '
                                       '_usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                                       'VAR '
                                       '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                                       'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && '
                                       'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                       'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                       '_singleCurrency)\n'
                                       "VAR _selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                       "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                       'VAR '
                                       '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                       'VAR _members=GENERATE(_files,\n'
                                       " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                       " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                       " VAR _cc='fm_native_files'[Country]\n"
                                       ' VAR '
                                       "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                       " VAR _digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                       ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && '
                                       "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                       '  VAR '
                                       "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                       '  VAR _half=INT(_exponent/2)\n'
                                       '  RETURN '
                                       "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                       '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                       ' VAR '
                                       '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                       " VAR _memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                                       '  '
                                       '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                                       '  '
                                       "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                       '  '
                                       "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                       '  '
                                       'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                       "IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                                       '  '
                                       'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                                       'IN '
                                       '_selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                                       ' VAR _bySector=GROUPBY(_memberFacts,[Sector],\n'
                                       '  "RawAmount",SUMX(CURRENTGROUP(),[Amount]),\n'
                                       '  '
                                       '"BadCells",SUMX(CURRENTGROUP(),INT([MissingCells]<>0||ISBLANK([Amount]))))\n'
                                       ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                                       '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                                       'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                                       '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && '
                                       '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                       'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                       'VAR '
                                       '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                       'RETURN IF(_sourceOK && NOT ISBLANK(_date) && LEN(_component)>0 && '
                                       'COUNTROWS(_available)>0\n'
                                       ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                       'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                       ' && (NOT _value || _usd || '
                                       'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                         'formatStringDefinition': {'expression': 'VAR '
                                                                  '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                  'VAR '
                                                                  '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                  ' || '
                                                                  'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                  'VAR '
                                                                  "_countries=VALUES('fm_review_files'[Country])\n"
                                                                  'VAR '
                                                                  "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                  'IN '
                                                                  "_countries),'fm_native_currency_map'[Currency])\n"
                                                                  'VAR _symbol=IF([N '
                                                                  'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                  ' '
                                                                  'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                  'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                                  'VAR '
                                                                  '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                  '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                  ' _value>=1000,"#,0,.0" & '
                                                                  'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                  'RETURN '
                                                                  'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Monthly Denominator': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                         "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                         "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                         'VAR _custom = '
                                         'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                         'files","Automatic ADS") = "Selected files"\n'
                                         'VAR _scenario = '
                                         "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                         'VAR _chosen = '
                                         "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                         "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                         "'fm_native_files'[Country] IN _country\n"
                                         " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                         " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                         "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                         'VAR _driver = '
                                         'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                         "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] "
                                         'IN _driver)\n'
                                         'VAR _files = FILTER(_pool, IF(_custom, '
                                         "'fm_native_files'[SourceRevisionID] IN _chosen && "
                                         "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                         " 'fm_native_files'[PreferenceRank]=1 && "
                                         "'fm_native_files'[PreferenceTies]=1))\n"
                                         'VAR _ids = '
                                         'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                         'VAR _scope = '
                                         "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                         'IN '
                                         "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                         'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                         'VAR _cohorts = '
                                         "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                         'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                         'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                         ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                         ' && (NOT _custom || '
                                         "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                         "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                         'VAR '
                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                         'VAR _display=[N Display]\n'
                                         'VAR '
                                         "_definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row "
                                         "&& 'fm_native_catalog'[Display]=_display)\n"
                                         'VAR '
                                         '_component=IF(_row="ef","",MAXX(_definition,\'fm_native_catalog\'[Denominator]))\n'
                                         'VAR '
                                         '_channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                                         'VAR '
                                         '_sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                                         'VAR _value=_display="Value"\n'
                                         'VAR '
                                         '_usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                                         'VAR '
                                         '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                                         'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && '
                                         'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                         'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                         '_singleCurrency)\n'
                                         "VAR _selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                         "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                         'VAR '
                                         '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                         'VAR _members=GENERATE(_files,\n'
                                         " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                         " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                         " VAR _cc='fm_native_files'[Country]\n"
                                         ' VAR '
                                         "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                         " VAR _digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                         ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && '
                                         "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                         '  VAR '
                                         "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                         '  VAR _half=INT(_exponent/2)\n'
                                         '  RETURN '
                                         "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                         '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                         ' VAR '
                                         '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                         " VAR _memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                                         '  '
                                         '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                                         '  '
                                         "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                         '  '
                                         "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                         '  '
                                         'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                         "IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                                         '  '
                                         'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                                         'IN '
                                         '_selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                                         ' VAR _bySector=GROUPBY(_memberFacts,[Sector],\n'
                                         '  "RawAmount",SUMX(CURRENTGROUP(),[Amount]),\n'
                                         '  '
                                         '"BadCells",SUMX(CURRENTGROUP(),INT([MissingCells]<>0||ISBLANK([Amount]))))\n'
                                         ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                                         '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                                         'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                                         '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && '
                                         '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                         'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                         'VAR '
                                         '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                         'RETURN IF(_sourceOK && NOT ISBLANK(_date) && LEN(_component)>0 && '
                                         'COUNTROWS(_available)>0\n'
                                         ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                         'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                         ' && (NOT _value || _usd || '
                                         'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                           'formatStringDefinition': {'expression': 'VAR '
                                                                    '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                    'VAR '
                                                                    '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                    ' || '
                                                                    'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                    'VAR '
                                                                    "_countries=VALUES('fm_review_files'[Country])\n"
                                                                    'VAR '
                                                                    "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                    'IN '
                                                                    "_countries),'fm_native_currency_map'[Currency])\n"
                                                                    'VAR _symbol=IF([N '
                                                                    'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                    ' '
                                                                    'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                    'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                                    'VAR '
                                                                    '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                    '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                    ' _value>=1000,"#,0,.0" & '
                                                                    'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                    'RETURN '
                                                                    'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Monthly': {'expression': 'VAR _n=[N Monthly Numerator] VAR _d=[N Monthly Denominator]\n'
                             'RETURN '
                             'IF(COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share",DIVIDE(_n,_d),_n)',
               'formatStringDefinition': {'expression': 'VAR '
                                                        '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                        'VAR '
                                                        '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                        ' || '
                                                        'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                        "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                                        'VAR '
                                                        "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                        "IN _countries),'fm_native_currency_map'[Currency])\n"
                                                        'VAR _symbol=IF([N '
                                                        'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                        ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                        'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                        'VAR '
                                                        '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & '
                                                        'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                        ' _value>=1000,"#,0,.0" & '
                                                        'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                        'RETURN '
                                                        'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Trend Monthly': {'expression': 'VAR _cut=[N Fit Cutoff] VAR '
                                   "_w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                   "VAR _m=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                   'RETURN IF(NOT ISBLANK(_m)&&NOT ISBLANK(_cut),IF(_m<=_cut,[N Monthly],\n'
                                   " VAR _mean=CALCULATE([N Fit Mean],REMOVEFILTERS('fm_review_axis'))\n"
                                   " VAR _slope=CALCULATE([N Fit Slope],REMOVEFILTERS('fm_review_axis'))\n"
                                   ' RETURN IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),\n'
                                   ' _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))))',
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0,.0" & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Period Months': {'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N "
                                   'Cutoff]\n'
                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                   'VAR '
                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                   'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                   'RETURN IF(NOT ISBLANK(_y)&&NOT '
                                   'ISBLANK(_cut)&&_end>=_start,DATEDIFF(_start,_end,MONTH)+1)',
                     'formatString': '0'},
 'N Plan': {'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                          "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N Cutoff]\n"
                          'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                          'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                          'VAR _start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                          'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                          'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                          'VAR '
                          '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                          'VAR '
                          '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                          'VAR _values=ADDCOLUMNS(_months,"N",VAR _m=[Date] RETURN\n'
                          ' CALCULATE([N Monthly '
                          "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])),\n"
                          ' "D",VAR _m=[Date] RETURN IF(_ratio,CALCULATE([N Monthly '
                          "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                          'VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count\n'
                          '\n'
                          'RETURN IF(NOT ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,\n'
                          ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT '
                          'ISBLANK([D])))=_count,DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
            'formatStringDefinition': {'expression': 'VAR '
                                                     '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                     'VAR '
                                                     '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                     ' || SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                     "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                                     'VAR '
                                                     "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                     "IN _countries),'fm_native_currency_map'[Currency])\n"
                                                     'VAR _symbol=IF([N '
                                                     'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                     ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                     'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                     'VAR _number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & '
                                                     'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                     ' _value>=1000,"#,0,.0" & '
                                                     'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                     'RETURN '
                                                     'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Benchmark': {'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                               "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N "
                               'Cutoff]\n'
                               'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                               'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                               'VAR _start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                               'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                               'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                               'VAR '
                               '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                               'VAR '
                               '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                               "VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                               'VAR _mean=IF(_end>_cut,CALCULATE([N Fit '
                               "Mean],REMOVEFILTERS('fm_review_axis')))\n"
                               'VAR _slope=IF(_end>_cut,CALCULATE([N Fit '
                               "Slope],REMOVEFILTERS('fm_review_axis')))\n"
                               'VAR _base=ADDCOLUMNS(_months,"D",VAR _m=[Date] RETURN IF(_ratio,\n'
                               ' CALCULATE([N Monthly '
                               "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                               'VAR _values=ADDCOLUMNS(_base,"N",VAR _m=[Date]\n'
                               ' VAR _forecast=IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),\n'
                               ' _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))\n'
                               ' RETURN IF(_m>_cut,IF(_ratio,IF(NOT ISBLANK(_forecast)&&NOT '
                               'ISBLANK([D]),_forecast*[D]),_forecast),\n'
                               ' CALCULATE([N Monthly '
                               "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                               'VAR _valid=COUNTROWS(FILTER(_values,NOT ISBLANK([N])))=_count\n'
                               'RETURN IF(NOT ISBLANK([N Fit Cutoff])&&NOT ISBLANK(_y)&&NOT '
                               'ISBLANK(_cut)&&_count>0&&_valid,\n'
                               ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT ISBLANK([D])))=_count,\n'
                               ' DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
                 'formatStringDefinition': {'expression': 'VAR '
                                                          '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                          'VAR '
                                                          '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                          ' || '
                                                          'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                          'VAR '
                                                          "_countries=VALUES('fm_review_files'[Country])\n"
                                                          'VAR '
                                                          "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                          'IN '
                                                          "_countries),'fm_native_currency_map'[Currency])\n"
                                                          'VAR _symbol=IF([N '
                                                          'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                          ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                          'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                          'VAR '
                                                          '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                          '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                          ' _value>=1000,"#,0,.0" & '
                                                          'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                          'RETURN '
                                                          'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Variance': {'expression': 'VAR _p=[N Plan] VAR _t=[N Benchmark] RETURN IF(NOT ISBLANK(_p)&&NOT '
                              'ISBLANK(_t),_p-_t)',
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & '
                                                         'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0,.0" & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Variance %': {'expression': 'VAR _p=[N Plan] VAR _b=[N Benchmark]\n'
                                'RETURN IF(NOT ISBLANK(_p)&&NOT ISBLANK(_b),DIVIDE(_p-_b,ABS(_b)))',
                  'formatString': '+0.0%;−0.0%;0.0%'},
 'N Headline Variance': {'expression': "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                       'VAR _actual=[N Actual Only]=1\n'
                                       'RETURN IF(NOT _actual,CALCULATE([N '
                                       "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                         'formatStringDefinition': {'expression': 'VAR '
                                                                  '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                  'VAR '
                                                                  '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                  ' || '
                                                                  'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                  'VAR '
                                                                  "_countries=VALUES('fm_review_files'[Country])\n"
                                                                  'VAR '
                                                                  "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                  'IN '
                                                                  "_countries),'fm_native_currency_map'[Currency])\n"
                                                                  'VAR _symbol=IF([N '
                                                                  'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                  ' '
                                                                  'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                  'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                                  'VAR '
                                                                  '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                  '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                  ' _value>=1000,"#,0,.0" & '
                                                                  'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                  'RETURN '
                                                                  'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Headline Variance %': {'expression': "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                         'VAR _actual=[N Actual Only]=1\n'
                                         'RETURN IF(NOT _actual,CALCULATE([N Variance '
                                         "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                           'formatString': '+0.0%;−0.0%;0.0%'},
 'N Summary Cell': {'expression': 'IF(HASONEVALUE(\'fm_native_scenario\'[Scenario])&&SELECTEDVALUE(\'fm_native_scenario\'[Mode])=IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                  'files","Automatic ADS"),\n'
                                  "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1,\n"
                                  "VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])\n"
                                  'RETURN IF(NOT _leaf,\n'
                                  " IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N Period "
                                  'Available]=1,[N Plan]),\n'
                                  "VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])\n"
                                  "VAR _w=SELECTEDVALUE('fm_native_columns'[Window])\n"
                                  "VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])\n"
                                  'VAR _actualOnly=[N Actual Only]=1\n'
                                  'RETURN IF([N Period Available]=1&&_allowed,SWITCH(TRUE(),_key="plan",[N '
                                  'Plan],_actualOnly,BLANK(),\n'
                                  ' RIGHT(_key,3)="abs",CALCULATE([N '
                                  "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),\n"
                                  ' CALCULATE([N Variance '
                                  "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))))))))",
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0,.0" & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Run Rate': {'expression': 'IF(SELECTEDVALUE(\'fm_native_run_rate\'[Show],"Off")="On" && '
                              "SELECTEDVALUE('fm_native_catalog'[RunRate],0)=1,\n"
                              ' DIVIDE([N Plan],[N Period Months]))',
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & '
                                                         'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0,.0" & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Growth %': {'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                              "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N Cutoff]\n"
                              'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                              'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                              'VAR _start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                              'VAR _end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                              'VAR _count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                              'VAR '
                              '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]-12))\n'
                              'VAR _values=ADDCOLUMNS(_months,"PY",VAR _m=[Date] RETURN CALCULATE([N Monthly '
                              "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))\n"
                              'VAR _py=IF(_count>0 && COUNTROWS(FILTER(_values,NOT '
                              'ISBLANK([PY])))=_count,SUMX(_values,[PY]))\n'
                              'RETURN '
                              'IF(SELECTEDVALUE(\'fm_native_growth\'[Show],"Off")="On"&&SELECTEDVALUE(\'fm_native_catalog\'[Growth],0)=1,\n'
                              ' IF(NOT ISBLANK([N Plan])&&NOT ISBLANK(_py),DIVIDE([N Plan]-_py,_py)))',
                'formatString': '+0.0%;−0.0%;0.0%'},
 'N SOP Row Selected': {'expression': "VAR _token=SELECTEDVALUE('fm_native_rows'[Token])\n"
                                      "RETURN IF(ISFILTERED('fm_native_state'[Token]) && "
                                      'SELECTEDVALUE(\'fm_native_rows\'[Kind])="row"\n'
                                      " && SELECTEDVALUE('fm_native_rows'[Display])=[N Display],1)",
                        'formatString': '0'},
 'N SOP Plan': {'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                              "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                              "VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                              "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                              "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                              " (LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                              " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                              "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                              ' NOT '
                              "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                              "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                              'Visible]<>1,BLANK(),CALCULATE(\n'
                              "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                              'RETURN IF([N SOP Row Selected]=1,CALCULATE([N '
                              "Plan],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                              "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                'formatStringDefinition': {'expression': 'VAR '
                                                         '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                         'VAR '
                                                         '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                         ' || '
                                                         'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                         "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                                         'VAR '
                                                         "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                         'IN '
                                                         "_countries),'fm_native_currency_map'[Currency])\n"
                                                         'VAR _symbol=IF([N '
                                                         'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                         ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                         'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                         'VAR '
                                                         '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" & '
                                                         'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                         ' _value>=1000,"#,0,.0" & '
                                                         'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                         'RETURN '
                                                         'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N SOP Run Rate': {'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                  "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                  "VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                  "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                  "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                  " (LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                  " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                  "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                  ' NOT '
                                  "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                  "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                  'Visible]<>1,BLANK(),CALCULATE(\n'
                                  "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                  'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Run '
                                  "Rate],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                  "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0,.0" & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N SOP Growth %': {'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                  "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                  "VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                  "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                  "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                  " (LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                  " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                  "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                  ' NOT '
                                  "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                  "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                  'Visible]<>1,BLANK(),CALCULATE(\n'
                                  "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                  'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Growth '
                                  "%],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                  "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                    'formatString': '+0.0%;−0.0%;0.0%'},
 'N SOP Monthly': {'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                 "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                 "VAR _groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                 "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                 "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                 " (LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                 " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                 "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                 ' NOT '
                                 "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                 "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                 'Visible]<>1,BLANK(),CALCULATE(\n'
                                 "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                 'RETURN IF([N SOP Row Selected]=1 && '
                                 "SELECTEDVALUE('fm_review_axis'[Month])>=MIN('fm_review_months'[Month]) && "
                                 "SELECTEDVALUE('fm_review_axis'[Month])<=MAX('fm_review_months'[Month]),CALCULATE([N "
                                 "Monthly],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                 "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                   'formatStringDefinition': {'expression': 'VAR '
                                                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                            'VAR '
                                                            '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                            ' || '
                                                            'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                            'VAR '
                                                            "_countries=VALUES('fm_review_files'[Country])\n"
                                                            'VAR '
                                                            "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                            'IN '
                                                            "_countries),'fm_native_currency_map'[Currency])\n"
                                                            'VAR _symbol=IF([N '
                                                            'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                            ' '
                                                            'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                            'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                            'VAR '
                                                            '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                            '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                            ' _value>=1000,"#,0,.0" & '
                                                            'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                            'RETURN '
                                                            'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N SOP Monthly Growth %': {'expression': "VAR _groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                          "VAR _groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                          'VAR '
                                          "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                          "VAR _groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                          "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                          ' '
                                          "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                          " &&(NOT _groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                          "VAR _groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                          ' NOT '
                                          "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                          "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N Group "
                                          'Visible]<>1,BLANK(),CALCULATE(\n'
                                          "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                          "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                          'VAR '
                                          "_allowed=MAXX(FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row),'fm_native_catalog'[Growth])=1\n"
                                          'VAR _current=CALCULATE([N Monthly '
                                          "Numerator],TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                          'VAR _prior=CALCULATE([N Monthly '
                                          "Numerator],TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_review_axis'),TREATAS({EDATE(_month,-12)},'fm_review_axis'[Month]))\n"
                                          'RETURN IF([N SOP Row '
                                          'Selected]=1&&_allowed&&SELECTEDVALUE(\'fm_native_growth\'[Show],"Off")="On"\n'
                                          ' '
                                          "&&_month>=MIN('fm_review_months'[Month])&&_month<=MAX('fm_review_months'[Month])\n"
                                          ' &&NOT ISBLANK(_current)&&NOT '
                                          'ISBLANK(_prior),DIVIDE(_current-_prior,_prior)),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))',
                            'formatString': '+0.0%;−0.0%;0.0%'},
 'N Export Selected': {'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                     'VAR _display=[N Display]\n'
                                     'VAR '
                                     "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                     ' '
                                     '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                     'RETURN '
                                     "IF(ISFILTERED('fm_native_state'[Token])&&COUNTROWS(_chosen)=1,1)",
                       'formatString': '0'},
 'N Export Plan': {'expression': 'IF([N Export Selected]=1,[N Plan])',
                   'formatStringDefinition': {'expression': 'VAR '
                                                            '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                            'VAR '
                                                            '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                            ' || '
                                                            'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                            'VAR '
                                                            "_countries=VALUES('fm_review_files'[Country])\n"
                                                            'VAR '
                                                            "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                            'IN '
                                                            "_countries),'fm_native_currency_map'[Currency])\n"
                                                            'VAR _symbol=IF([N '
                                                            'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                            ' '
                                                            'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                            'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                            'VAR '
                                                            '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                            '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                            ' _value>=1000,"#,0,.0" & '
                                                            'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                            'RETURN '
                                                            'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Export Run Rate': {'expression': 'IF([N Export Selected]=1,[N Run Rate])',
                       'formatStringDefinition': {'expression': 'VAR '
                                                                '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                'VAR '
                                                                '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                ' || '
                                                                'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                'VAR '
                                                                "_countries=VALUES('fm_review_files'[Country])\n"
                                                                'VAR '
                                                                "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                'IN '
                                                                "_countries),'fm_native_currency_map'[Currency])\n"
                                                                'VAR _symbol=IF([N '
                                                                'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                ' '
                                                                'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                                'VAR '
                                                                '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                ' _value>=1000,"#,0,.0" & '
                                                                'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                'RETURN '
                                                                'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Export Growth %': {'expression': 'IF([N Export Selected]=1,[N Growth %])',
                       'formatString': '+0.0%;−0.0%;0.0%'},
 'N Export Order': {'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                  'VAR _display=[N Display]\n'
                                  'VAR '
                                  "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                  ' '
                                  '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                  "RETURN IF([N Export Selected]=1,MINX(_chosen,'fm_native_state'[RowRank]))",
                    'formatString': '0'},
 'N Export Monthly': {'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) RETURN IF([N Export "
                                    'Selected]=1\n'
                                    ' '
                                    "&&_m>=MIN('fm_review_months'[Month])&&_m<=MAX('fm_review_months'[Month]),[N "
                                    'Monthly])',
                      'formatStringDefinition': {'expression': 'VAR '
                                                               '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                               'VAR '
                                                               '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                               ' || '
                                                               'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                               'VAR '
                                                               "_countries=VALUES('fm_review_files'[Country])\n"
                                                               'VAR '
                                                               "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                               'IN '
                                                               "_countries),'fm_native_currency_map'[Currency])\n"
                                                               'VAR _symbol=IF([N '
                                                               'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                               ' '
                                                               'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                               'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                               'VAR '
                                                               '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                               '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                               ' _value>=1000,"#,0,.0" & '
                                                               'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                               'RETURN '
                                                               'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Export Month Stage': {'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) VAR _cut=[N Cutoff]\n"
                                        'RETURN IF([N Export Selected]=1&&NOT ISBLANK(_m)&&NOT '
                                        'ISBLANK(_cut),IF(_m<=_cut,"Actual","Forecast"))',
                          'formatString': ''},
 'N Chart Monthly': {'expression': 'IF([N Line Visible]=1,\n'
                                   "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                   "VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) VAR "
                                   "_sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])\n"
                                   "VAR _sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1\n"
                                   "VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) VAR "
                                   "_type=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                   'VAR '
                                   '_row=IF(_type="sop",SELECTEDVALUE(\'fm_native_lines\'[RowID]),COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market"))\n'
                                   "VAR _display=SELECTEDVALUE('fm_native_lines'[Display])\n"
                                   'VAR _selected=_type="demand" || ISFILTERED(\'fm_native_state\'[Token]) '
                                   '&& COUNTROWS(\n'
                                   ' '
                                   'FILTER(ALLSELECTED(\'fm_native_state\'),\'fm_native_state\'[Kind]="row"\n'
                                   ' '
                                   "&&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0\n"
                                   'VAR '
                                   "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)&&(NOT "
                                   "_sectorLevel||'fm_native_scope'[Sector]=_sec))\n"
                                   "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                   'VAR '
                                   "_within=_month>=MIN('fm_native_start_month'[Month])&&_month<=MAX('fm_native_end_month'[Month])\n"
                                   'VAR '
                                   '_mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                   'files","Automatic ADS")\n'
                                   'VAR _base=CALCULATE([N '
                                   "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                   'VAR _cut=CALCULATE([N '
                                   "Cutoff],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                                   'RETURN '
                                   'IF((_type<>"demand"||HASONEVALUE(\'fm_native_metric\'[RowID]))&&MIN(\'fm_native_start_month\'[Month])<=MAX(\'fm_native_end_month\'[Month])&&_mode&&_within&&_selected&&COUNTROWS(_scope)>0&&CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total")),\n'
                                   ' '
                                   'SWITCH(TRUE(),_kind=0&&_month<=_cut,_base,_kind=1&&(_month>_cut||_type="demand"&&_month=_cut),_base,\n'
                                   ' _kind IN '
                                   "{6,12,24}&&_month>=_cut&&_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12),\n"
                                   ' CALCULATE([N Trend '
                                   "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_native_trend'),TREATAS({_kind},'fm_native_trend'[Window])))))",
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0,.0" & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Chart Amount': {'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])<>"share",[N Chart Monthly])',
                    'formatStringDefinition': {'expression': 'VAR '
                                                             '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                             'VAR '
                                                             '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                             ' || '
                                                             'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                             'VAR '
                                                             "_countries=VALUES('fm_review_files'[Country])\n"
                                                             'VAR '
                                                             "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                             'IN '
                                                             "_countries),'fm_native_currency_map'[Currency])\n"
                                                             'VAR _symbol=IF([N '
                                                             'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                             ' '
                                                             'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                             'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                             'VAR '
                                                             '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                             '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                             ' _value>=1000,"#,0,.0" & '
                                                             'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                             'RETURN '
                                                             'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Chart Share': {'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])="share",[N Chart Monthly])',
                   'formatString': '0.0%'},
 'N Status': {'expression': 'SWITCH(TRUE(),[N Source OK]<>1,"Select a valid ADS source for each selected '
                            'cohort. Check Matching files.",\n'
                            ' ISBLANK([N Cutoff]),"Selected sources have different cutoffs; compare them '
                            'separately.",\n'
                            ' "Saved ADS · IMS / EF calendars retained · Native R17 candidate")',
              'formatString': ''},
 'N Variance Color': {'expression': 'VAR _value=[N Summary Cell] RETURN '
                                    'IF(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey])="plan"||ISBLANK(_value)||_value=0,"#17384D",IF(_value>0,"#087D88","#AC640C"))',
                      'formatString': ''},
 'N Fit Cutoff': {'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                                'VAR _custom = '
                                'IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                'files","Automatic ADS") = "Selected files"\n'
                                'VAR _scenario = '
                                "COALESCE(SELECTEDVALUE('fm_native_lines'[Scenario]),SELECTEDVALUE('fm_native_scenario'[Scenario]))\n"
                                'VAR _chosen = '
                                "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                                "VAR _poolAvailable = FILTER(ALL('fm_native_files'), "
                                "'fm_native_files'[Country] IN _country\n"
                                " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                                " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                                "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                                'VAR _driver = '
                                'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                                "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
                                '_driver)\n'
                                "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] "
                                "IN _chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                                " 'fm_native_files'[PreferenceRank]=1 && "
                                "'fm_native_files'[PreferenceTies]=1))\n"
                                'VAR _ids = '
                                'SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                'VAR _scope = '
                                "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                                "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                                'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                                'VAR _cohorts = '
                                "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                                'VAR _sourceOK = COUNTROWS(_files)>0 && '
                                'COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                                ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                                ' && (NOT _custom || '
                                "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                                'VAR '
                                '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                'VAR _ef=IF(_row IN {"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                                'VAR '
                                '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                                'RETURN IF(_sourceOK && '
                                'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0 '
                                '&& COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff]))',
                  'formatString': 'mmm yyyy'},
 'N Actual Only': {'expression': "VAR _year=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                 "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) VAR _cut=[N "
                                 'Cutoff]\n'
                                 'VAR '
                                 '_end=SWITCH(_kind,"YTD",DATE(_year,MONTH(_cut),1),"H1",DATE(_year,6,1),DATE(_year,12,1))\n'
                                 'VAR _actualOnly=NOT ISBLANK(_cut)&&NOT ISBLANK(_year)&&_end<=_cut\n'
                                 'RETURN INT(_actualOnly)',
                   'formatString': '0'},
 'N Line Visible': {'expression': "VAR _view=SELECTEDVALUE('fm_native_lines'[ViewType])\n"
                                  "VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])\n"
                                  "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                  "VAR _cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])\n"
                                  "VAR _chart=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                  'RETURN '
                                  'IF(CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total"))\n'
                                  ' && '
                                  '_mode=IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
                                  'files","Automatic ADS")\n'
                                  " && _cycle IN VALUES('fm_review_files'[DemandCycle])\n"
                                  ' && (_chart="sop" || _kind IN {0,1} || '
                                  "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)),1)",
                    'formatString': '0'},
 'N Selected Month': {'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),\n"
                                    ' FORMAT(SELECTEDVALUE(\'fm_review_axis\'[Month]),"mmm yyyy"))'},
 'N Selected Monthly': {'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),[N Monthly])",
                        'formatStringDefinition': {'expression': 'VAR '
                                                                 '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                                 'VAR '
                                                                 '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                                 ' || '
                                                                 'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                                 'VAR '
                                                                 "_countries=VALUES('fm_review_files'[Country])\n"
                                                                 'VAR '
                                                                 "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                                 'IN '
                                                                 "_countries),'fm_native_currency_map'[Currency])\n"
                                                                 'VAR _symbol=IF([N '
                                                                 'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                                 ' '
                                                                 'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                                 'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                                 'VAR '
                                                                 '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                 '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                 ' _value>=1000,"#,0,.0" & '
                                                                 'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                 'RETURN '
                                                                 'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Headline Cell': {'expression': "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1&&[N Period "
                                   'Available]=1,\n'
                                   "SWITCH(SELECTEDVALUE('fm_native_headline'[Key]),\n"
                                   ' "plan",[N Plan],"variance",[N Headline Variance],"pct",[N Headline '
                                   'Variance %])))',
                     'formatStringDefinition': {'expression': 'VAR '
                                                              '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                              'VAR '
                                                              '_pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                                                              ' || '
                                                              'SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                                                              'VAR '
                                                              "_countries=VALUES('fm_review_files'[Country])\n"
                                                              'VAR '
                                                              "_ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] "
                                                              'IN '
                                                              "_countries),'fm_native_currency_map'[Currency])\n"
                                                              'VAR _symbol=IF([N '
                                                              'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                                                              ' '
                                                              'SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                                                              'VAR _value=ABS(SELECTEDMEASURE())\n'
                                                              'VAR '
                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                              '& UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                              ' _value>=1000,"#,0,.0" & '
                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                              'RETURN '
                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'}},
 'N Measure Caption': {'expression': "IF(HASONEVALUE('fm_native_metric'[RowID]),\n"
                                     'VAR _name=SELECTEDVALUE(\'fm_native_metric\'[MetricLabel],"Selected '
                                     'measures")\n'
                                     'RETURN IF(CONTAINSSTRING(_name,"%"),_name,_name & IF([N '
                                     'Display]="Value"," value"," units")),"Choose a measure in the selected '
                                     'section")'},
 'N Group Visible': {'expression': "VAR _cycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                   "VAR _gd=SELECTEDVALUE('fm_native_groups'[ScopeDriver]) VAR "
                                   "_sec=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                   "VAR _sector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                   'VAR '
                                   "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)\n"
                                   " &&(NOT _sector||'fm_native_scope'[Sector]=_sec))\n"
                                   'RETURN IF(_cycle IN '
                                   "VALUES('fm_review_files'[DemandCycle])&&COUNTROWS(_scope)>0,1)",
                     'formatString': '0'},
 'N Fit Mean': {'expression': "VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                              'VAR '
                              '_dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])\n'
                              'VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN\n'
                              ' CALCULATE([N '
                              "Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))\n"
                              'VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w\n'
                              'VAR _mx=AVERAGEX(_train,[X]) VAR _my=AVERAGEX(_train,[Y])\n'
                              'RETURN IF(NOT ISBLANK(_cut)&&_valid,_my)'},
 'N Fit Slope': {'expression': "VAR _cut=[N Fit Cutoff] VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                               'VAR '
                               '_dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])\n'
                               'VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN\n'
                               ' CALCULATE([N '
                               "Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))\n"
                               'VAR _valid=COUNTROWS(FILTER(_train,NOT ISBLANK([Y])))=_w\n'
                               'VAR _mx=AVERAGEX(_train,[X]) VAR _my=AVERAGEX(_train,[Y])\n'
                               'RETURN IF(NOT ISBLANK(_cut)&&_valid,\n'
                               ' DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2))))'},
 'N File Available': {'expression': "VAR _countries=VALUES('fm_review_files'[Country])\n"
                                    "VAR _cycles=VALUES('fm_review_files'[DemandCycle])\n"
                                    "VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\n"
                                    "RETURN IF(COUNTROWS(FILTER('fm_native_files','fm_native_files'[Country] "
                                    'IN _countries\n'
                                    " &&'fm_native_files'[DemandCycle] IN "
                                    "_cycles&&'fm_native_files'[GrowthDriver] IN _drivers))>0,1)",
                      'formatString': '0'}}

EXPRESSION_PATCHES = {'N Catalog Available': "VAR _country = VALUES('fm_review_files'[Country])\n"
                        "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                        "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                        'VAR _custom = "Selected files" = "Selected files"\n'
                        'VAR _scenario = '
                        'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                        'VAR _chosen = '
                        "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                        "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN "
                        '_country\n'
                        " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                        " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                        "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                        'VAR _driver = '
                        'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                        "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                        "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN "
                        "_chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                        " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                        'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                        "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                        "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                        'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                        'VAR _cohorts = '
                        "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                        'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                        ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                        ' && (NOT _custom || '
                        "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                        "VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                        'VAR '
                        '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                        "VAR _component=SELECTEDVALUE('fm_native_catalog'[Component])\n"
                        "VAR _channel=SELECTEDVALUE('fm_native_catalog'[Channel])\n"
                        "VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])\n"
                        "RETURN IF(CALCULATE(COUNTROWS('fm_review_facts'),REMOVEFILTERS('fm_review_facts'),\n"
                        ' '
                        "TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                        " TREATAS({_channel},'fm_review_facts'[Channel]),\n"
                        ' '
                        'FILTER(ALL(\'fm_review_facts\'[SubChannel]),COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub))>0,1)',
 'N Chart Monthly': 'IF([N Line Visible]=1,\n'
                    "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                    "VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) VAR "
                    "_sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])\n"
                    "VAR _sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1\n"
                    "VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) VAR "
                    "_type=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                    'VAR '
                    '_row=IF(_type="sop",SELECTEDVALUE(\'fm_native_lines\'[RowID]),COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market"))\n'
                    "VAR _display=SELECTEDVALUE('fm_native_lines'[Display])\n"
                    'VAR _selected=_type="demand" || ISFILTERED(\'fm_native_state\'[Token]) && COUNTROWS(\n'
                    ' FILTER(ALLSELECTED(\'fm_native_state\'),\'fm_native_state\'[Kind]="row"\n'
                    " &&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0\n"
                    'VAR '
                    "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)&&(NOT "
                    "_sectorLevel||'fm_native_scope'[Sector]=_sec))\n"
                    "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                    'VAR '
                    "_within=_month>=MIN('fm_native_start_month'[Month])&&_month<=MAX('fm_native_end_month'[Month])\n"
                    'VAR _mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=IF(_type="demand","Automatic '
                    'ADS","Selected files")\n'
                    'VAR _base=CALCULATE([N '
                    "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                    'VAR _cut=CALCULATE([N '
                    "Cutoff],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                    'RETURN '
                    'IF((_type<>"demand"||HASONEVALUE(\'fm_native_metric\'[RowID]))&&MIN(\'fm_native_start_month\'[Month])<=MAX(\'fm_native_end_month\'[Month])&&_mode&&_within&&_selected&&COUNTROWS(_scope)>0&&CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total")),\n'
                    ' '
                    'SWITCH(TRUE(),_kind=0&&_month<=_cut,_base,_kind=1&&(_month>_cut||_type="demand"&&_month=_cut),_base,\n'
                    ' _kind IN '
                    "{6,12,24}&&_month>=_cut&&_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12),\n"
                    ' CALCULATE([N Trend '
                    "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_native_trend'),TREATAS({_kind},'fm_native_trend'[Window])))))",
 'N Cutoff': "VAR _country = VALUES('fm_review_files'[Country])\n"
             "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
             "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
             'VAR _custom = "Selected files" = "Selected files"\n'
             'VAR _scenario = '
             'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
             'VAR _chosen = '
             "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
             "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN _country\n"
             " && 'fm_native_files'[DemandCycle] IN _cycles\n"
             " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
             "_chosen,'fm_native_files'[ADSPriority]>0))\n"
             'VAR _driver = '
             'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
             "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
             "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN _chosen && "
             "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
             " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
             'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
             "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
             "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
             'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
             'VAR _cohorts = '
             "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
             'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
             ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
             ' && (NOT _custom || '
             "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
             'VAR '
             '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
             'VAR _ef=IF(_row IN {"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
             'VAR '
             '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
             'RETURN IF(_sourceOK && '
             'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0 '
             '&& COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])))=0,MINX(_dates,[Cutoff]))',
 'N Fit Cutoff': "VAR _country = VALUES('fm_review_files'[Country])\n"
                 "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                 "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                 'VAR _custom = "Selected files" = "Selected files"\n'
                 'VAR _scenario = '
                 'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                 'VAR _chosen = '
                 "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                 "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN "
                 '_country\n'
                 " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                 " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                 "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                 'VAR _driver = '
                 'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                 "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                 "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN _chosen && "
                 "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                 " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                 'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                 "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                 "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                 'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                 'VAR _cohorts = '
                 "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                 'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                 ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                 ' && (NOT _custom || '
                 "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                 'VAR '
                 '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                 'VAR _ef=IF(_row IN {"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                 'VAR '
                 '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                 'RETURN IF(_sourceOK && '
                 'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0 '
                 '&& COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff]))',
 'N Headline Cell': "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1&&[N Period Available]=1,\n"
                    "VAR _key=SELECTEDVALUE('fm_native_headline'[Key])\n"
                    "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                    'VAR _actualOnly=[N Actual Only]=1\n'
                    'VAR _plan=[N Plan]\n'
                    'VAR _benchmark=CALCULATE([N '
                    "Benchmark],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))\n"
                    'VAR _pair=NOT ISBLANK(_plan)&&NOT ISBLANK(_benchmark)\n'
                    'VAR _variance=IF(_pair,_plan-_benchmark)\n'
                    'VAR _percent=IF(_pair,DIVIDE(_plan-_benchmark,ABS(_benchmark)))\n'
                    'RETURN IF(_key="plan",_plan,IF(_key="variance",IF(NOT _actualOnly,_variance),\n'
                    ' IF(_key="pct",IF(NOT _actualOnly,_percent),BLANK())))))',
 'N Headline Variance': "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                        'VAR _actual=[N Actual Only]=1\n'
                        'RETURN IF.EAGER(NOT _actual,CALCULATE([N '
                        "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
 'N Headline Variance %': "VAR _w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                          'VAR _actual=[N Actual Only]=1\n'
                          'RETURN IF.EAGER(NOT _actual,CALCULATE([N Variance '
                          "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
 'N Line Visible': "VAR _view=SELECTEDVALUE('fm_native_lines'[ViewType])\n"
                   "VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])\n"
                   "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                   "VAR _cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])\n"
                   "VAR _chart=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                   'RETURN '
                   'IF(CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total"))\n'
                   ' && _mode=IF(_chart="demand","Automatic ADS","Selected files")\n'
                   " && _cycle IN VALUES('fm_review_files'[DemandCycle])\n"
                   ' && (_chart="sop" || _kind IN {0,1} || '
                   "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)),1)",
 'N Monthly Denominator': "VAR _country = VALUES('fm_review_files'[Country])\n"
                          "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                          "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                          'VAR _custom = "Selected files" = "Selected files"\n'
                          'VAR _scenario = '
                          'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                          'VAR _chosen = '
                          "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                          "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN "
                          '_country\n'
                          " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                          " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                          "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                          'VAR _driver = '
                          'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                          "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                          "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN "
                          "_chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                          " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                          'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                          'VAR _scope = '
                          "SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                          "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                          'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                          'VAR _cohorts = '
                          "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                          'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                          ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                          ' && (NOT _custom || '
                          "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                          "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                          'VAR '
                          '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                          'VAR _display=[N Display]\n'
                          "VAR _definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row "
                          "&& 'fm_native_catalog'[Display]=_display)\n"
                          'VAR '
                          '_component=IF(_row="ef","",MAXX(_definition,\'fm_native_catalog\'[Denominator]))\n'
                          'VAR _channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                          'VAR _sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                          'VAR _value=_display="Value"\n'
                          'VAR _usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                          'VAR '
                          '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                          'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && '
                          'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                          'VAR _convert=_value && _usd && (_row<>"share" || NOT _singleCurrency)\n'
                          "VAR _selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                          "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                          'VAR '
                          '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                          'VAR _members=GENERATE(_files,\n'
                          " VAR _id='fm_native_files'[SourceRevisionID]\n"
                          " VAR _gd='fm_native_files'[GrowthDriver]\n"
                          " VAR _cc='fm_native_files'[Country]\n"
                          ' VAR '
                          "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                          " VAR _digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                          ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && '
                          "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                          '  VAR '
                          "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                          '  VAR _half=INT(_exponent/2)\n'
                          '  RETURN '
                          "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                          '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                          ' VAR '
                          '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                          " VAR _memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                          '  '
                          '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                          '  '
                          "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                          '  '
                          "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                          '  '
                          'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                          "IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                          '  '
                          'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                          'IN _selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                          ' VAR _bySector=GROUPBY(_memberFacts,[Sector],\n'
                          '  "RawAmount",SUMX(CURRENTGROUP(),[Amount]),\n'
                          '  "BadCells",SUMX(CURRENTGROUP(),INT([MissingCells]<>0||ISBLANK([Amount]))))\n'
                          ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                          '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                          'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                          '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && '
                          '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                          'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                          'VAR '
                          '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                          'RETURN IF(_sourceOK && NOT ISBLANK(_date) && LEN(_component)>0 && '
                          'COUNTROWS(_available)>0\n'
                          ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                          'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                          ' && (NOT _value || _usd || '
                          'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
 'N Monthly Numerator': "VAR _country = VALUES('fm_review_files'[Country])\n"
                        "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                        "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                        'VAR _custom = "Selected files" = "Selected files"\n'
                        'VAR _scenario = '
                        'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                        'VAR _chosen = '
                        "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                        "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN "
                        '_country\n'
                        " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                        " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                        "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                        'VAR _driver = '
                        'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                        "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                        "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN "
                        "_chosen && (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                        " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                        'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                        "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                        "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                        'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                        'VAR _cohorts = '
                        "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                        'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                        ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                        ' && (NOT _custom || '
                        "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                        "VAR _date=SELECTEDVALUE('fm_review_axis'[Month])\n"
                        'VAR '
                        '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                        'VAR _display=[N Display]\n'
                        "VAR _definition=FILTER(ALL('fm_native_catalog'),'fm_native_catalog'[RowID]=_row && "
                        "'fm_native_catalog'[Display]=_display)\n"
                        'VAR _component=IF(_row="ef","ef-ads-" & '
                        "LOWER(_display),MAXX(_definition,'fm_native_catalog'[Component]))\n"
                        'VAR _channel=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[Channel]))\n'
                        'VAR _sub=IF(_row="ef","*",MAXX(_definition,\'fm_native_catalog\'[SubChannel]))\n'
                        'VAR _value=_display="Value"\n'
                        'VAR _usd=SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD"\n'
                        'VAR '
                        '_currencies=SELECTCOLUMNS(_files,"CC",LOOKUPVALUE(\'fm_native_currency_map\'[Currency],\'fm_native_currency_map\'[Country],\'fm_native_files\'[Country]))\n'
                        'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 && '
                        'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                        'VAR _convert=_value && _usd && (_row<>"share" || NOT _singleCurrency)\n'
                        "VAR _selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                        "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                        'VAR '
                        '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                        'VAR _members=GENERATE(_files,\n'
                        " VAR _id='fm_native_files'[SourceRevisionID]\n"
                        " VAR _gd='fm_native_files'[GrowthDriver]\n"
                        " VAR _cc='fm_native_files'[Country]\n"
                        ' VAR '
                        "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                        " VAR _digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                        ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 && '
                        "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                        '  VAR '
                        "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                        '  VAR _half=INT(_exponent/2)\n'
                        '  RETURN '
                        "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                        '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                        ' VAR '
                        '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                        " VAR _memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                        '  '
                        '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                        '  '
                        "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                        '  '
                        "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                        '  '
                        'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                        "IN _selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
                        '  '
                        'FILTER(ALL(\'fm_review_facts\'[SubChannel]),IF(_sub="*",\'fm_review_facts\'[SubChannel] '
                        'IN _selectedSubs,COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub)))\n'
                        ' VAR _bySector=GROUPBY(_memberFacts,[Sector],\n'
                        '  "RawAmount",SUMX(CURRENTGROUP(),[Amount]),\n'
                        '  "BadCells",SUMX(CURRENTGROUP(),INT([MissingCells]<>0||ISBLANK([Amount]))))\n'
                        ' RETURN ADDCOLUMNS(FILTER(_bySector,[BadCells]=0),\n'
                        '  "Amount",IF(_convert,IF(NOT ISBLANK([RawAmount])&&NOT '
                        'ISBLANK(_rate),IFERROR([RawAmount]*_rate,BLANK())),[RawAmount]),\n'
                        '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) && '
                        '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                        'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                        'VAR _localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                        'RETURN IF(_sourceOK && NOT ISBLANK(_date) && LEN(_component)>0 && '
                        'COUNTROWS(_available)>0\n'
                        ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                        'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                        ' && (NOT _value || _usd || '
                        'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
 'N Scenario Visible': 'IF(SELECTEDVALUE(\'fm_native_scenario\'[Mode])="Selected files"&&[N Source OK]=1,1)',
 'N Scope Available': "VAR _country = VALUES('fm_review_files'[Country])\n"
                      "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                      "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                      'VAR _custom = "Selected files" = "Selected files"\n'
                      'VAR _scenario = '
                      'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                      'VAR _chosen = '
                      "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                      "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN "
                      '_country\n'
                      " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                      " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                      "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                      'VAR _driver = '
                      'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                      "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                      "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN _chosen "
                      "&& (ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                      " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                      'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                      "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                      "IN _ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                      'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                      'VAR _cohorts = '
                      "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                      'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                      ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                      ' && (NOT _custom || '
                      "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                      "VAR _admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                      'VAR '
                      '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                      "RETURN IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                      '_candidateIds))>0,1)',
 'N Source Caption': 'VAR '
                     "_picked=ISFILTERED('fm_native_files'[FileChoiceLabel])||ISFILTERED('fm_review_files'[FileLabel])\n"
                     "VAR _countries=VALUES('fm_review_files'[Country])\n"
                     "VAR _cycles=VALUES('fm_review_files'[DemandCycle])\n"
                     "VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\n"
                     'VAR '
                     "_chosen=INTERSECT(VALUES('fm_native_files'[SourceRevisionID]),VALUES('fm_review_files'[SourceRevisionID]))\n"
                     "VAR _files=FILTER(ALL('fm_native_files'),'fm_native_files'[SourceRevisionID] IN "
                     '_chosen\n'
                     " &&'fm_native_files'[Country] IN _countries&&'fm_native_files'[DemandCycle] IN "
                     '_cycles\n'
                     " &&'fm_native_files'[GrowthDriver] IN _drivers)\n"
                     "VAR _ims=MAXX(_files,'fm_native_files'[IMSActualsThrough])\n"
                     "VAR _ef=MAXX(_files,'fm_native_files'[ExFactoryActualsThrough])\n"
                     'RETURN SWITCH(TRUE(),NOT _picked,"Select saved files below",\n'
                     ' [N Source OK]<>1,"Select one saved version for each required growth driver",\n'
                     ' ISBLANK(_ims)||ISBLANK(_ef)||_ims<DATE(2000,1,1)||_ef<DATE(2000,1,1)\n'
                     ' ||_ims>=DATE(2100,1,1)||_ef>=DATE(2100,1,1),"Actuals cutoff metadata unavailable",\n'
                     ' FORMAT(COUNTROWS(_files),"0")&" selected file(s) · IMS through "&FORMAT(_ims,"mmm '
                     'yy")\n'
                     ' &" · Ex-factory through "&FORMAT(_ef,"mmm yy"))',
 'N Source OK': "VAR _country = VALUES('fm_review_files'[Country])\n"
                "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                "VAR _selectedDrivers = VALUES('fm_native_scope'[GrowthDriver])\n"
                'VAR _custom = "Selected files" = "Selected files"\n'
                'VAR _scenario = '
                'IF(SELECTEDVALUE(\'fm_native_lines\'[Chart])="demand",BLANK(),COALESCE(SELECTEDVALUE(\'fm_native_lines\'[Scenario]),SELECTEDVALUE(\'fm_native_scenario\'[Scenario])))\n'
                'VAR _chosen = '
                "INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))\n"
                "VAR _poolAvailable = FILTER(ALL('fm_native_files'), 'fm_native_files'[Country] IN _country\n"
                " && 'fm_native_files'[DemandCycle] IN _cycles\n"
                " && IF(_custom,'fm_native_files'[SourceRevisionID] IN "
                "_chosen,'fm_native_files'[ADSPriority]>0))\n"
                'VAR _driver = '
                'INTERSECT(_selectedDrivers,DISTINCT(SELECTCOLUMNS(_poolAvailable,"Driver",\'fm_native_files\'[GrowthDriver])))\n'
                "VAR _pool = FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN _driver)\n"
                "VAR _files = FILTER(_pool, IF(_custom, 'fm_native_files'[SourceRevisionID] IN _chosen && "
                "(ISBLANK(_scenario)||'fm_native_files'[Scenario]=_scenario),\n"
                " 'fm_native_files'[PreferenceRank]=1 && 'fm_native_files'[PreferenceTies]=1))\n"
                'VAR _ids = SELECTCOLUMNS(_files,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                "VAR _scope = SUMMARIZE(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] IN "
                "_ids),'fm_native_scope'[GrowthDriver],'fm_native_scope'[Sector])\n"
                'VAR _expected = CROSSJOIN(_country,_cycles,_driver)\n'
                'VAR _cohorts = '
                "SUMMARIZE(_files,'fm_native_files'[Country],'fm_native_files'[DemandCycle],'fm_native_files'[GrowthDriver])\n"
                'VAR _sourceOK = COUNTROWS(_files)>0 && COUNTROWS(_files)=COUNTROWS(_cohorts)\n'
                ' && COUNTROWS(_cohorts)=COUNTROWS(_expected)\n'
                ' && (NOT _custom || '
                "(ISFILTERED('fm_review_files'[FileLabel])||ISFILTERED('fm_native_files'[FileChoiceLabel])))\n"
                'RETURN INT(_sourceOK)',
 'N Summary Cell': "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1,\n"
                   "VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])\n"
                   'RETURN IF(NOT _leaf,\n'
                   " IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N Period Available]=1,[N Plan]),\n"
                   "VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])\n"
                   "VAR _w=SELECTEDVALUE('fm_native_columns'[Window])\n"
                   "VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])\n"
                   'VAR _actualOnly=[N Actual Only]=1\n'
                   'VAR _plan=[N Plan]\n'
                   'VAR _benchmark=CALCULATE([N '
                   "Benchmark],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))\n"
                   'VAR _pair=NOT ISBLANK(_plan)&&NOT ISBLANK(_benchmark)\n'
                   'VAR _variance=IF(_pair,_plan-_benchmark)\n'
                   'VAR _percent=IF(_pair,DIVIDE(_plan-_benchmark,ABS(_benchmark)))\n'
                   'RETURN IF([N Period Available]=1&&_allowed,\n'
                   ' IF(_key="plan",_plan,IF(_actualOnly,BLANK(),\n'
                   ' IF(RIGHT(_key,3)="abs",_variance,_percent)))))))'}

FORMAT_PATCHES = {'N Headline Cell': 'VAR '
                    '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                    'VAR _pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                    ' || SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                    "VAR _countries=VALUES('fm_review_files'[Country])\n"
                    "VAR _ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] IN "
                    "_countries),'fm_native_currency_map'[Currency])\n"
                    'VAR _symbol=IF([N '
                    'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                    ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                    'VAR _value=SELECTEDMEASURE()\n'
                    'VAR _abs=ABS(_value)\n'
                    'VAR _display=IF(_value<0,"−","")&_symbol&SWITCH(TRUE(),\n'
                    ' _abs>=1000000,FORMAT(_abs/1000000,"#,0.00","en-GB")&"m",\n'
                    ' _abs>=1000,FORMAT(_abs/1000,"#,0.0","en-GB")&"k",FORMAT(_abs,"#,0","en-GB"))\n'
                    'VAR _literal=UNICHAR(34)&_display&UNICHAR(34)\n'
                    'RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",_literal&";"&_literal&";"&_literal)',
 'N Summary Cell': 'VAR '
                   '_row=COALESCE(SELECTEDVALUE(\'fm_native_rows\'[RowID]),SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                   'VAR _pct=RIGHT(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey],""),3)="pct"\n'
                   ' || SELECTEDVALUE(\'fm_native_headline\'[Key])="pct"\n'
                   "VAR _countries=VALUES('fm_review_files'[Country])\n"
                   "VAR _ccy=MAXX(FILTER('fm_native_currency_map','fm_native_currency_map'[Country] IN "
                   "_countries),'fm_native_currency_map'[Currency])\n"
                   'VAR _symbol=IF([N '
                   'Display]="Units","",IF(SELECTEDVALUE(\'fm_native_currency\'[Currency],"USD")="USD","$",\n'
                   ' SWITCH(_ccy,"GBP","£","EUR","€","USD","$","")))\n'
                   'VAR _value=SELECTEDMEASURE()\n'
                   'VAR _abs=ABS(_value)\n'
                   'VAR _display=IF(_value<0,"−","")&_symbol&SWITCH(TRUE(),\n'
                   ' _abs>=1000000,FORMAT(_abs/1000000,"#,0.00","en-GB")&"m",\n'
                   ' _abs>=1000,FORMAT(_abs/1000,"#,0.0","en-GB")&"k",FORMAT(_abs,"#,0","en-GB"))\n'
                   'VAR _literal=UNICHAR(34)&_display&UNICHAR(34)\n'
                   'RETURN IF(_pct||_row="share","0.0%;−0.0%;0.0%",_literal&";"&_literal&";"&_literal)'}

REPORT_FOLDER = 'ForecastMaster R17.8 R03 TEST.Report'

TEMPLATE_SHA256 = 'ea43ee9b4e3e7dab5f20cddd36359ca05b008bab299943ed6a5bf51a45a73cd0'

TEMPLATE = base64.b64decode('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b3JlY2FzdE1hc3Rlck92ZXJsYXlSMTc4L3BhY2thZ2UuanNvblBLAQIUAxQAAAAIAAAAWF0K46+/0R0AAD5EAAB8AAAAAAAAAAAAAACAAdwBAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvQ3VzdG9tVmlzdWFscy9Gb3JlY2FzdE1hc3Rlck92ZXJsYXlSMTc4L3Jlc291cmNlcy9Gb3JlY2FzdE1hc3Rlck92ZXJsYXlSMTc4LnBiaXZpei5qc29uUEsBAhQDFAAAAAgAAABYXbxfMDbnAAAAzwEAAGcAAAAAAAAAAAAAAIABRyAAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9TdGF0aWNSZXNvdXJjZXMvUmVnaXN0ZXJlZFJlc291cmNlcy9mbS1uYXRpdmUtb25seS1yMTczLXRoZW1lLmpzb25QSwECFAMUAAAACAAAAFhdo5EWB80aAAB7MwIAZQAAAAAAAAAAAAAAgAGzIQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L1N0YXRpY1Jlc291cmNlcy9TaGFyZWRSZXNvdXJjZXMvQmFzZVRoZW1lcy9GbHVlbnQyLUNZMjZTVTA4Lmpzb25QSwECFAMUAAAACAAAAFhd4T2sy0gBAADLAQAANAAAAAAAAAAAAAAAgAEDPQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24ucGJpclBLAQIUAxQAAAAIAAAAWF0BsErblwAAAOQAAABIAAAAAAAAAAAAAACAAZ0+AABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9ib29rbWFya3MvYm9va21hcmtzLmpzb25QSwECFAMUAAAACAAAAFhdltt7qX8CAACOEgAAUgAAAAAAAAAAAAAAgAGaPwAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vYm9va21hcmtzL3NlY3Rpb25fZWYuYm9va21hcmsuanNvblBLAQIUAxQAAAAIAAAAWF22WYeEfQIAAIsSAABTAAAAAAAAAAAAAACAAYlCAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9ib29rbWFya3Mvc2VjdGlvbl9pbXMuYm9va21hcmsuanNvblBLAQIUAxQAAAAIAAAAWF2gmmd6bgQAAFszAABNAAAAAAAAAAAAAACAAXdFAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3BhZ2UuanNvblBLAQIUAxQAAAAIAAAAWF37QpU2/gMAAN4gAABhAAAAAAAAAAAAAACAAVBKAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvYWZmaWxpYXRlL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXUVyDb0TBAAAByEAAGMAAAAAAAAAAAAAAIABzU4AAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9jaGFydF90cmVuZC92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF0J/ZujlgIAAFoRAABpAAAAAAAAAAAAAACAAWFTAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvY2hhcnRfdHJlbmRfbGFiZWwvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhdi+EpnQgEAAD3IAAAXQAAAAAAAAAAAAAAgAF+VgAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL2N5Y2xlL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXQ0Tf+D5AwAA5yAAAF8AAAAAAAAAAAAAAIABAVsAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9kaXNwbGF5L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXdd9zd0YBAAAjyAAAF8AAAAAAAAAAAAAAIABd18AAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9kcml2ZXJzL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXfZ/T8ENAwAAchcAAGsAAAAAAAAAAAAAAIABDGQAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9keW5hbWljX2NoYXJ0X3RpdGxlL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXWJyN3QCBAAABSEAAGEAAAAAAAAAAAAAAIABomcAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9lbmRfbW9udGgvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhd3Ab6cqoFAACJNwAAaQAAAAAAAAAAAAAAgAEjbAAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL2V4ZWN1dGl2ZV9zdW1tYXJ5L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXXh74jqaAgAAWhEAAGcAAAAAAAAAAAAAAIABVHIAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9leGVjdXRpdmVfdGl0bGUvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhdL+1t1xQFAAAMJAAAYwAAAAAAAAAAAAAAgAFzdQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL2ZpbGVfcGlja2VyL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXX83jfe+AgAAjhEAAGUAAAAAAAAAAAAAAIABCHsAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9maWxlc19oZWFkaW5nL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXW0zEvKwAgAAbREAAF8AAAAAAAAAAAAAAIABSX4AAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9oZWFkaW5nL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXdzZSRNgBAAANiYAAGAAAAAAAAAAAAAAAIABdoEAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9oZWFkbGluZS92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF1BzlHIqAIAAGcRAABmAAAAAAAAAAAAAACAAVSGAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvaGVhZGxpbmVfdGl0bGUvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhdmTrbddcDAACJIAAAXgAAAAAAAAAAAAAAgAGAiQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL21ldHJpYy92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF3MQar1cAQAAGEgAABkAAAAAAAAAAAAAACAAdONAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvbmF0aXZlX2NoYXJ0L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXaf80iruBAAAuCgAAF8AAAAAAAAAAAAAAIABxZIAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9wZXJpb2RzL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXWr43tjWAgAAVxQAAGsAAAAAAAAAAAAAAIABMJgAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9yZXZpZXdfdmFyaWFuY2Vfa2V5L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXVNPSikHBAAA/yAAAF8AAAAAAAAAAAAAAIABj5sAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9zZWN0aW9uL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXfEgfGOyAgAAOhkAAGIAAAAAAAAAAAAAAIABE6AAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9zZWN0aW9uX2VmL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXYEXMeW4AgAAPhkAAGMAAAAAAAAAAAAAAIABRaMAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy9zZWN0aW9uX2ltcy92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF3vFHgxjQIAAE8RAABlAAAAAAAAAAAAAACAAX6mAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvc2VjdGlvbl9sYWJlbC92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF39RiHfBQMAAGQXAABlAAAAAAAAAAAAAACAAY6pAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvc291cmNlX3N0YXR1cy92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF0ymfOKBwQAABAhAABjAAAAAAAAAAAAAACAARatAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvc3RhcnRfbW9udGgvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhdIR5z09kCAABYFAAAbAAAAAAAAAAAAAAAgAGesQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL3N1bW1hcnlfdmFyaWFuY2Vfa2V5L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXax12bpHBAAA9SAAAF0AAAAAAAAAAAAAAIABAbUAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy90aWVycy92aXN1YWwuanNvblBLAQIUAxQAAAAIAAAAWF321Zd1DwQAAOcgAABdAAAAAAAAAAAAAACAAcO5AABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5SZXBvcnQvZGVmaW5pdGlvbi9wYWdlcy9uYXRpdmVfZGVtYW5kL3Zpc3VhbHMvdHJlbmQvdmlzdWFsLmpzb25QSwECFAMUAAAACAAAAFhd4Mozt5QCAABUEQAAYwAAAAAAAAAAAAAAgAFNvgAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcGFnZXMvbmF0aXZlX2RlbWFuZC92aXN1YWxzL3RyZW5kX2xhYmVsL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXX3AVIf5AwAA0iAAAFwAAAAAAAAAAAAAAIABYsEAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy92aWV3L3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXUL/GKSQAgAAShEAAGIAAAAAAAAAAAAAAIAB1cUAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL25hdGl2ZV9kZW1hbmQvdmlzdWFscy92aWV3X2xhYmVsL3Zpc3VhbC5qc29uUEsBAhQDFAAAAAgAAABYXVXnhjOSAAAAzQAAAEAAAAAAAAAAAAAAAIAB5cgAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3BhZ2VzL3BhZ2VzLmpzb25QSwECFAMUAAAACAAAAFhdpa0JYaMCAACHCAAAOwAAAAAAAAAAAAAAgAHVyQAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcmVwb3J0Lmpzb25QSwECFAMUAAAACAAAAFhd0ItuHPMFAAAbEgAARQAAAAAAAAAAAAAAgAHRzAAARm9yZWNhc3RNYXN0ZXIgUjE3LjggUjAzIFRFU1QuUmVwb3J0L2RlZmluaXRpb24vcmVwb3J0RXh0ZW5zaW9ucy5qc29uUEsBAhQDFAAAAAgAAABYXU48gMduAAAAjAAAADwAAAAAAAAAAAAAAIABJ9MAAEZvcmVjYXN0TWFzdGVyIFIxNy44IFIwMyBURVNULlJlcG9ydC9kZWZpbml0aW9uL3ZlcnNpb24uanNvblBLAQIUAxQAAAAIAAAAWF2J06aUyQAAACcBAAAiAAAAAAAAAAAAAACAAe/TAABGb3JlY2FzdE1hc3RlciBSMTcuOCBSMDMgVEVTVC5wYmlwUEsBAhQDFAAAAAgAAABYXefQz8/uAAAASgEAAA4AAAAAAAAAAAAAAIAB+NQAAE9QRU4gRklSU1QudHh0UEsFBgAAAAAuAC4AdBgAABLWAAAAAA==', validate=True)

METADATA_QUERY = 'EVALUATE SELECTCOLUMNS(TOPN(1,\n FILTER(ALL(\'fm_native_files\'),\'fm_native_files\'[ADSPriority]>0\n &&\'fm_native_files\'[PreferenceRank]=1&&\'fm_native_files\'[PreferenceTies]=1),\n \'fm_native_files\'[DemandCycle],DESC,\'fm_native_files\'[SourceRevisionID],ASC),\n "Country",\'fm_native_files\'[Country],"Cycle",\'fm_native_files\'[DemandCycle],\n "Driver",\'fm_native_files\'[GrowthDriver])'

DEFAULTS_QUERY = 'EVALUATE SELECTCOLUMNS(FILTER(ALL(\'fm_native_files\'),\n \'fm_native_files\'[ADSPriority]>0&&\'fm_native_files\'[PreferenceRank]=1&&\'fm_native_files\'[PreferenceTies]=1),\n "Country",\'fm_native_files\'[Country],"Cycle",\'fm_native_files\'[DemandCycle],"Driver",\'fm_native_files\'[GrowthDriver],\n "Label",\'fm_native_files\'[FileChoiceLabel],"Scenario",\'fm_native_files\'[Scenario])'

"""Receiving body embedded by build_cell.py. Existing R01 TEST only.

No refresh, processing, source/production update or publication. The durable
R03 intent precedes the single updateDefinition submission. Unknown outcomes
refuse reruns. Report defaults are read privately from actual model metadata.
"""
R01_PRIVATE = 'abfss://' + WORKSPACE + '@onelake.dfs.fabric.microsoft.com/' + LAKEHOUSE + '/Files/ForecastMasterRefreshState/report-upgrades/Native-R178-Compact-R01'
R03_PRIVATE = R01_PRIVATE.rsplit('/', 1)[0] + '/Native-R178-UI-R03'
ATTEMPT = R03_PRIVATE + '/ATTEMPT.json'


def native_measures(database):
    tables = [t for t in database['model']['tables'] if t['name'] == 'fm_native_measures']
    require(len(tables) == 1, 'EXPECTED_ONE_NATIVE_MEASURE_TABLE')
    rows = tables[0]['measures']
    result = {m['name']: m for m in rows}
    require(len(result) == len(rows), 'DUPLICATE_NATIVE_MEASURE')
    return result


def patch_database(database):
    fixed = deepcopy(database)
    actual = native_measures(fixed)
    require(set(actual) == set(EXPECTED_NATIVE), 'INSTALLED_R01_MEASURE_INVENTORY_DIFFERS')
    for name, expected in EXPECTED_NATIVE.items():
        require(expression_text(actual[name]['expression']).strip() == expression_text(expected['expression']).strip(), 'INSTALLED_R01_EXPRESSION_DIFFERS')
        require(normalized(actual[name].get('formatStringDefinition')) == normalized(expected.get('formatStringDefinition'))
                and actual[name].get('formatString', '') == expected.get('formatString', ''), 'INSTALLED_R01_FORMAT_DIFFERS')
    for name, expression in EXPRESSION_PATCHES.items():
        actual[name]['expression'] = expression
    for name, expression in FORMAT_PATCHES.items():
        actual[name]['formatStringDefinition']['expression'] = expression
    restored = deepcopy(fixed)
    before, restore = native_measures(database), native_measures(restored)
    for name in EXPRESSION_PATCHES:
        restore[name]['expression'] = deepcopy(before[name]['expression'])
    for name in FORMAT_PATCHES:
        restore[name]['formatStringDefinition'] = deepcopy(before[name]['formatStringDefinition'])
    require(restored == database, 'UNDECLARED_MODEL_DIFFERENCE')
    return fixed


def read_private(fs, path):
    allowed = path == R01_PRIVATE + '/ATTEMPT.json' or (
        path.startswith(R01_PRIVATE + '/') and path.endswith(('/definition-candidate.json', '/connections-before.json', '/success.json')))
    require(allowed, 'PRIVATE_R01_PATH_NOT_PINNED')
    require(fs.exists(path), 'PRIVATE_R01_RECEIPT_MISSING')
    with TemporaryDirectory(prefix='fm-r178-ui-r02-') as temp:
        local = Path(temp) / 'private.json'
        require(fs.cp(path, local.as_uri(), False), 'PRIVATE_R01_READ_FAILED')
        require(0 < local.stat().st_size < 64 * 1024 * 1024, 'PRIVATE_R01_SIZE_UNEXPECTED')
        return json.loads(local.read_bytes().decode('utf-8'))


def records(evaluate, query):
    frame = evaluate(dataset=TEST, dax_string=query, workspace=WORKSPACE, verbose=0, use_readwrite_connection=False)
    return [{k.rsplit('[', 1)[-1].rstrip(']'): v for k, v in row.items()} for row in frame.to_dict(orient='records')]


def preferred_files(evaluate):
    rows = records(evaluate, DEFAULTS_QUERY)
    require(bool(rows), 'NO_UNIQUE_PREFERRED_ADS_DEFAULTS')
    expected = {'Country', 'Cycle', 'Driver', 'Label', 'Scenario'}
    require(all(set(row) == expected and all(isinstance(v, str) and v for v in row.values()) for row in rows), 'PREFERRED_FILE_METADATA_INVALID')
    require(len({(r['Country'], r['Cycle'], r['Driver']) for r in rows}) == len(rows)
            and len({r['Label'] for r in rows}) == len(rows), 'PREFERRED_FILE_CHOICES_AMBIGUOUS')
    return sorted(rows, key=lambda row: tuple(row[k] for k in sorted(row)))


def scalar(evaluate, query):
    rows = records(evaluate, query)
    require(len(rows) == 1 and set(rows[0]) == {'V'}, 'EXPECTED_ONE_PRIVATE_SCALAR')
    value = rows[0]['V']
    if value is None or isinstance(value, Number) and not isinstance(value, bool) and math.isnan(float(value)):
        return None
    require(isinstance(value, Number) and not isinstance(value, bool) and math.isfinite(float(value)), 'SCALAR_NOT_FINITE_NUMERIC')
    return float(value)


def scalar_queries(scope):
    def filt(table, column, value):
        return 'TREATAS({' + '"' + str(value).replace('"', '""') + '"' + '},\'' + table + '\'[' + column + '])'
    year = int(scope['Cycle'][:4])
    shared = [filt('fm_review_files', 'Country', scope['Country']), filt('fm_review_files', 'DemandCycle', scope['Cycle']),
        filt('fm_native_scope', 'GrowthDriver', scope['Driver']), filt('fm_native_files', 'FileChoiceLabel', scope['Label']),
        filt('fm_native_currency', 'Currency', 'Local'), filt('fm_native_display', 'Display', 'Units'),
        filt('fm_native_scenario', 'Scenario', scope['Scenario']), filt('fm_native_scenario', 'Mode', 'Selected files'),
        filt('fm_native_file_mode', 'Mode', 'Selected files'), filt('fm_native_periods', 'PeriodKey', str(year) + ':FY'),
        "TREATAS({12},'fm_native_trend'[Window])", "TREATAS({12},'fm_native_chart_trend'[Window])"]
    for metric in ('market', 'ef', 'share'):
        filters = shared + [filt('fm_native_metric', 'RowID', metric), filt('fm_native_metric', 'Section', 'Ex-factory' if metric == 'ef' else 'IMS / Market')]
        for measure, extra in [
            ('N Plan', []), ('N Benchmark', []), ('N Variance %', []),
            ('N Trend Monthly', ["TREATAS({DATE(" + str(year + 1) + ",12,1)},'fm_review_axis'[Month])"]),
            ('N Headline Cell', [filt('fm_native_headline', 'Key', 'plan')]),
            ('N Headline Cell', [filt('fm_native_headline', 'Key', 'variance')]),
            ('N Headline Cell', [filt('fm_native_headline', 'Key', 'pct')]),
            ('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', 'plan')]),
            ('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', '12:abs')]),
            ('N Summary Cell', [filt('fm_native_columns', 'ColumnKey', '12:pct')])]:
            yield {'Metric': metric, 'Measure': measure, 'Variant': len(extra) and extra[0] or 'FY'}, 'EVALUATE ROW("V",CALCULATE([' + measure + '],' + ','.join(filters + extra) + '))'


def compare_number(left, right):
    return left is None and right is None or left is not None and right is not None and math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-6)


def qualified_report(labels):
    require(hashlib.sha256(TEMPLATE).hexdigest() == TEMPLATE_SHA256, 'REPORT_TEMPLATE_HASH_DIFFERS')
    with ZipFile(BytesIO(TEMPLATE)) as source:
        files = {n: source.read(n) for n in source.namelist()}
    require(not any('.SemanticModel/' in n or n.endswith('model.bim') for n in files), 'REPORT_TEMPLATE_NOT_THIN')
    path = REPORT_FOLDER + '/definition/pages/native_demand/visuals/file_picker/visual.json'
    picker = json.loads(files[path])
    node = picker['visual']['objects']['general'][0]['properties']['filter']['filter']['Where'][0]['Condition']['In']
    require(node['Values'] == [[{'Literal': {'Value': "'__PRIVATE_ADS_DEFAULTS__'"}}]], 'REPORT_DEFAULT_PLACEHOLDER_DIFFERS')
    node['Values'] = [[{'Literal': {'Value': "'" + label.replace("'", "''") + "'"}}] for label in sorted(labels)]
    files[path] = json.dumps(picker, ensure_ascii=False, indent=2).encode()
    payload = BytesIO()
    with ZipFile(payload, 'w', compression=ZIP_DEFLATED) as archive:
        for name, data in sorted(files.items()):
            archive.writestr(name, data)
    return payload.getvalue()


def install(client, pbi, fs, evaluate, result, context):
    context['Step'] = 'IDENTITY_AND_PRIOR_R01'
    identity(client, context)
    require(not fs.exists(ATTEMPT), 'PRIOR_R03_ATTEMPT_REVIEW_REQUIRED_NO_RETRY')
    marker = read_private(fs, R01_PRIVATE + '/ATTEMPT.json')
    folder = marker.get('Backup', '')
    require(marker.get('Revision') == 'R01' and marker.get('TEST') == TEST and folder.startswith(R01_PRIVATE + '/'), 'PRIVATE_R01_MARKER_UNEXPECTED')
    require(read_private(fs, folder + '/success.json').get('Stage') == 'TEST_R178_UPDATED', 'PRIVATE_R01_INSTALL_NOT_VERIFIED')
    wanted = read_private(fs, folder + '/definition-candidate.json')
    expected = json.loads(base64.b64decode(next(p for p in wanted['parts'] if p['path'] == 'model.bim')['payload'], validate=True))
    require(digest(expected) == marker.get('CandidateBIM'), 'PRIVATE_R01_CANDIDATE_HASH_DIFFERS')
    jobs = processing_history(pbi)
    require(jobs[0].get('status') == 'Completed', 'LATEST_TEST_REFRESH_NOT_COMPLETED')
    before, database, bindings = read_definition(client, context)
    routing(database, bindings)
    require(normalized(database) == normalized(expected), 'CURRENT_TEST_DIFFERS_FROM_PRIVATE_R01_NO_WRITE')
    require([p for p in before['parts'] if p['path'] != 'model.bim'] == [p for p in wanted['parts'] if p['path'] != 'model.bim'], 'NON_BIM_PARTS_CHANGED_NO_WRITE')
    mapping = connections(client, context)
    require(mapping == read_private(fs, folder + '/connections-before.json'), 'CLOUD_MAPPING_DIFFERS_NO_WRITE')
    dates = date_signature(evaluate)
    result['Dates'] = validate_dates(evaluate)
    defaults = preferred_files(evaluate)
    scope_rows = records(evaluate, METADATA_QUERY)
    require(len(scope_rows) == 1, 'NO_UNIQUE_COMPARISON_SCOPE')
    scope = [r for r in defaults if all(r[k] == scope_rows[0][k] for k in ('Country', 'Cycle', 'Driver'))]
    require(len(scope) == 1, 'COMPARISON_DEFAULT_NOT_UNIQUE')
    fixed = patch_database(database)
    report_bytes = qualified_report([row['Label'] for row in defaults])
    define = 'DEFINE\n' + '\n'.join("MEASURE 'fm_native_measures'[" + n + ']=\n' + v for n, v in EXPRESSION_PATCHES.items()) + '\n'
    checks, candidate_values = list(scalar_queries(scope[0])), []
    context.clear()
    for i, (check, query) in enumerate(checks, 1):
        context.update(Step='PAIRED_SCALAR_PREFLIGHT', CheckIndex=i, Metric=check['Metric'], Measure=check['Measure'])
        print('R17.8 R03 private paired check ' + str(i) + '/' + str(len(checks)) + ': ' + check['Metric'] + ' / ' + check['Measure'] + '.', flush=True)
        left, right = scalar(evaluate, query), scalar(evaluate, define + query)
        require(left is not None and right is not None and compare_number(left, right), 'PAIRED_SCALAR_MISMATCH_OR_UNAVAILABLE_NO_WRITE')
        candidate_values.append(right)
    # Clearing the explicit file choice must never restore Automatic ADS.
    empty_queries = []
    for metric in ('market', 'ef', 'share'):
        source = next(query for (check, query) in checks if check['Metric'] == metric and check['Measure'] == 'N Plan')
        literal = '"' + scope[0]['Label'].replace('"', '""') + '"'
        selected = 'TREATAS({' + literal + "},'fm_native_files'[FileChoiceLabel])"
        require(source.count(selected) == 1, 'PREFLIGHT_FILE_FILTER_SHAPE_CHANGED')
        empty_queries.append(source.replace(',' + selected, ''))
    for i, query in enumerate(empty_queries, 1):
        context.update(Step='NO_FILE_BLANK_PREFLIGHT', CheckIndex=i)
        require(scalar(evaluate, define + query) is None, 'NO_FILE_DID_NOT_BLANK_NO_WRITE')
    result['Preflight'] = {'PairedScalarComparisons': len(checks), 'NoFileBlankChecks': len(empty_queries), 'Mismatches': 0, 'ValuesPrintedOrStored': False,
                          'Scope': 'One preferred ADS driver; market/ef/share; 12M; FY/future; kernels and matrix cells'}
    context.clear()
    context['Step'] = 'BACKUP_AND_CONCURRENCY'
    latest, latest_database, _ = read_definition(client, context)
    require(latest == before and normalized(latest_database) == normalized(database) and connections(client, context) == mapping
            and processing_history(pbi) == jobs and date_signature(evaluate) == dates and preferred_files(evaluate) == defaults, 'CONCURRENT_CHANGE_NO_WRITE')
    after = deepcopy(before)
    next(p for p in after['parts'] if p['path'] == 'model.bim')['payload'] = base64.b64encode(json.dumps(fixed, ensure_ascii=False).encode()).decode()
    backup = R03_PRIVATE + '/' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S') + '-' + str(uuid4())
    fs.mkdirs(backup)
    for name, value in [('definition-before.json', before), ('definition-candidate.json', after), ('connections-before.json', mapping), ('preflight-counts.json', result)]:
        verified_backup(fs, backup + '/' + name, value)
    verified_backup(fs, backup + '/report-package.json', {'SHA256': hashlib.sha256(report_bytes).hexdigest(), 'ZipBase64': base64.b64encode(report_bytes).decode()})
    # Backup I/O can take time. Recheck immediately before durable write intent.
    latest, latest_database, _ = read_definition(client, context)
    require(latest == before and normalized(latest_database) == normalized(database) and connections(client, context) == mapping
            and processing_history(pbi) == jobs and date_signature(evaluate) == dates and preferred_files(evaluate) == defaults, 'CHANGE_DURING_BACKUP_NO_WRITE')
    verified_backup(fs, ATTEMPT, {'Revision': 'R03', 'TEST': TEST, 'Backup': backup, 'BeforeBIM': digest(database), 'CandidateBIM': digest(fixed)})
    context.clear()
    context['Step'] = 'UPDATE_DEFINITION_ONCE'
    result.update(ModelWriteRequested=True, PrivateBackup=backup)
    response = client.post('/v1/workspaces/' + WORKSPACE + '/semanticModels/' + TEST + '/updateDefinition', json={'definition': after, 'options': {'allowPurgeData': False}})
    complete_update(client, response, context, lambda value: verified_backup(fs, backup + '/operation.json', value))
    result['UpdateOperationCompleted'] = True
    context['Step'] = 'FULL_READBACK'
    got, got_database, _ = read_definition(client, context)
    require(normalized(got_database) == normalized(fixed) and [p for p in got['parts'] if p['path'] != 'model.bim'] == [p for p in after['parts'] if p['path'] != 'model.bim'], 'UPDATED_DEFINITION_READBACK_DIFFERS_NO_REFRESH')
    require(connections(client, context) == mapping and date_signature(evaluate) == dates and preferred_files(evaluate) == defaults, 'UPDATED_MAPPING_OR_SOURCE_DIFFERS_NO_REFRESH')
    installed_jobs = processing_history(pbi)
    require(installed_jobs[0].get('status') == 'Completed', 'INSTALLED_LATEST_REFRESH_NOT_COMPLETED_NO_RETRY')
    for i, ((check, query), wanted_value) in enumerate(zip(checks, candidate_values), 1):
        context.clear()
        context.update(Step='INSTALLED_SCALAR_READBACK', CheckIndex=i, Metric=check['Metric'], Measure=check['Measure'])
        require(compare_number(scalar(evaluate, query), wanted_value), 'INSTALLED_SCALAR_READBACK_DIFFERS_NO_REFRESH')
        if i == 1 or i % 4 == 0:
            print('Installed private scalar readback ' + str(i) + '/' + str(len(checks)) + ' completed.', flush=True)
    for i, query in enumerate(empty_queries, 1):
        context.update(Step='INSTALLED_NO_FILE_BLANK_READBACK', CheckIndex=i)
        require(scalar(evaluate, query) is None, 'INSTALLED_NO_FILE_DID_NOT_BLANK_NO_REFRESH')
    context.clear()
    context['Step'] = 'FINAL_STABILITY_READBACK'
    stable, stable_database, _ = read_definition(client, context)
    require(stable == got and normalized(stable_database) == normalized(fixed) and connections(client, context) == mapping
            and processing_history(pbi) == installed_jobs and date_signature(evaluate) == dates and preferred_files(evaluate) == defaults, 'INSTALLED_STATE_CHANGED_DURING_READBACK_NO_RETRY')
    result.update(Stage='TEST_R178_R03_UPDATED_AND_BOUNDED_READBACK_VERIFIED', FullMetadataReadbackMatches=True,
        CloudMappingPreserved=True, DefaultADSChoices=len(defaults), InstalledScalarReadbacks=len(checks),
        RefreshRequired=False, PrivateReportStored=True, ReportDownloadSHA256=hashlib.sha256(report_bytes).hexdigest(),
        NextStep='Download the private TEST ZIP shown below. Extract to a NEW folder; open PBIP in company Desktop. No refresh or publish. Send final JSON and screenshots/timings; keep filenames and report ZIP private.')
    verified_backup(fs, backup + '/success.json', result)
    return report_bytes


def run(client, pbi, fs, evaluate):
    result = {'Stage': 'TEST_R178_R03_STOPPED', 'Revision': 'R03', 'TestModelID': TEST, 'ModelWriteRequested': False,
        'UpdateOperationCompleted': False, 'RefreshRequested': False, 'LakehouseTableWriteRequested': False,
        'OriginalModelWriteRequested': False, 'ReportPublished': False, 'CompanyAmountsPrintedOrStored': False,
        'NextStep': 'Send this JSON. Do not rerun, refresh, delete markers or use an old installer.'}
    context, report_bytes = {}, None
    try:
        report_bytes = install(client, pbi, fs, evaluate, result, context)
    except (Exception, KeyboardInterrupt) as exc:
        result['Failure'] = safe_failure(exc)
        result['Checkpoint'] = {k: context[k] for k in ('Step', 'CheckIndex', 'Metric', 'Measure', 'HTTPStatus') if k in context}
    if report_bytes is not None:
        try:
            from IPython.display import HTML, display
            display(HTML('<a download="ForecastMaster-R178-R03-TEST-PRIVATE.zip" href="data:application/zip;base64,' + base64.b64encode(report_bytes).decode() + '">Download private R17.8 R03 TEST report</a>'))
            result['DownloadLinkOffered'] = True
        except Exception:
            result.update(DownloadLinkOffered=False, NextStep='Send this JSON. The private report is backed up; do not rerun or refresh to recover its download.')
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(retry_config={"total": 0}), fabric.PowerBIRestClient(retry_config={"total": 0}), notebookutils.fs, fabric.evaluate_dax)
