"""ONE NEW ForecastMaster_GM_Setup cell; existing TEST only, run ONCE.
12 sequential paired scalar comparisons (values never printed/stored), verified
private backup, pinned inventory and concurrency guards, scoped update/readback.
No refresh, source/production write or publication. Return final JSON.
"""
import base64
from copy import deepcopy
from datetime import date,datetime,timezone
import hashlib
import json
import math
from numbers import Number
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote,urlsplit
from uuid import UUID,uuid4

WORKSPACE='f5cb5742-9a7c-4337-a4c0-952706dddf0b'

LAKEHOUSE='d6e33ebd-67b1-420a-8d84-c3a0d04d8b21'

TEST='31d00232-ac03-48fe-af39-f2e4bae82443'

NAME='ForecastMaster Native OneLake R17.1 - TEST'

ROOT='abfss://'+WORKSPACE+'@onelake.dfs.fabric.microsoft.com/'+LAKEHOUSE+'/Tables/'

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

def physical_dates(spark,fs,ctx):
    # Only date metadata and the IDs needed to match cutoffs; never Amount.
    from pyspark.sql import functions as F
    data={};files=None
    for table,columns in FIELDS.items():
        ctx['Step']='PHYSICAL_DATE_READ';ctx['Table']=table
        found=[path for path in (ROOT+table,ROOT+'dbo/'+table) if fs.exists(path+'/_delta_log')]
        require(len(found)==1,'PHYSICAL_PATH_MISSING_OR_AMBIGUOUS')
        selected=['SourceRevisionID','Country','DemandCycle']+columns if table=='fm_review_files' else (
            ['SourceRevisionID']+columns if table=='fm_review_facts' else columns)
        df=spark.read.format('delta').load(found[0]).select(*selected)
        require(all(df.schema[name].dataType.simpleString() in {'date','timestamp','timestamp_ntz'} for name in columns),
                'PHYSICAL_DATE_TYPE_UNEXPECTED')
        if table=='fm_review_files':
            df=df.filter((F.col('Country')=='UK')&(F.col('DemandCycle')=='2026-10'));files=df
            rows=[row.asDict() for row in df.limit(1001).collect()]
            require(0<len(rows)<=1000,'PHYSICAL_FILE_SCOPE_SIZE_UNEXPECTED')
            require(len({str(row['SourceRevisionID']) for row in rows})==len(rows),'PHYSICAL_FILE_IDS_AMBIGUOUS')
            for kind,col in (('SourceIMS','IMSActualsThrough'),('SourceEF','ExFactoryActualsThrough')):
                data[kind]=[(str(row['SourceRevisionID']),as_date(row[col])) for row in rows]
            data['NativeIMS']=list(data['SourceIMS']);data['NativeEF']=list(data['SourceEF'])
        else:
            if table=='fm_review_facts':
                require(files is not None,'PHYSICAL_FILE_SCOPE_UNAVAILABLE')
                df=df.join(F.broadcast(files.select('SourceRevisionID').distinct()),'SourceRevisionID','inner')
            rows=df.select('Month').distinct().limit(1201).collect()
            require(0<len(rows)<=1200,'PHYSICAL_MONTH_SCOPE_SIZE_UNEXPECTED')
            kind={'fm_review_axis':'Axis','fm_review_months':'Review','fm_review_facts':'Facts'}[table]
            data[kind]=[('',as_date(row['Month'])) for row in rows]
    data['Start']=list(data['Review']);data['End']=list(data['Review'])
    require(all(day is not None and '2000-01-01'<=day<'2100-01-01' for rows in data.values() for _,day in rows),
            'PHYSICAL_DATES_INVALID_NO_RESET')
    require(set(data['Axis'])==set(data['Review'])==set(data['Facts']),'PHYSICAL_MONTH_SETS_DIFFER_NO_RESET')
    return {kind:sorted(rows) for kind,rows in data.items()}

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

def compare(expected,actual):
    counts={}
    for kind in sorted(KINDS):
        wanted=expected[kind];got=actual[kind]
        counts[kind]={'PhysicalExpectedRows':len(wanted),'SemanticRows':len(got),
          'InvalidSemanticDates':sum(day is None or not '2000-01-01'<=day<'2100-01-01' for _,day in got),
          'ExactRowsMatch':len(got)==len(wanted) and set(got)==set(wanted)}
    return counts

def all_match(counts):return all(row['ExactRowsMatch'] for row in counts.values())

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

BASELINE = {'name': 'ForecastMasterNativeSyntheticR174',
 'id': 'ForecastMasterNativeSyntheticR174',
 'compatibilityLevel': 1604,
 'model': {'culture': 'en-GB',
           'defaultPowerBIDataSourceVersion': 'powerBI_V3',
           'tables': [{'name': 'fm_native_measures',
                       'columns': [{'name': 'ID',
                                    'dataType': 'int64',
                                    'sourceColumn': '[ID]',
                                    'summarizeBy': 'none',
                                    'isHidden': True,
                                    'type': 'calculatedTableColumn'}],
                       'partitions': [{'name': 'fm_native_measures',
                                       'mode': 'import',
                                       'source': {'type': 'calculated',
                                                  'expression': 'DATATABLE("ID",INTEGER,{\n{1}\n})'}}],
                       'description': 'OneLake R17.1 TEST metadata. Direct Lake calculated-table preview '
                                      'gate.',
                       'measures': [{'name': 'N Display',
                                     'expression': 'SELECTEDVALUE(\'fm_native_display\'[Display],"Units")',
                                     'formatString': '',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Catalog Visible',
                                     'expression': "IF(SELECTEDVALUE('fm_native_catalog'[Display])=[N "
                                                   'Display],1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Catalog Available',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR '
                                                   "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                                   'VAR '
                                                   '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                                   'VAR '
                                                   "_component=SELECTEDVALUE('fm_native_catalog'[Component])\n"
                                                   'VAR '
                                                   "_channel=SELECTEDVALUE('fm_native_catalog'[Channel])\n"
                                                   "VAR _sub=SELECTEDVALUE('fm_native_catalog'[SubChannel])\n"
                                                   'RETURN '
                                                   "IF(CALCULATE(COUNTROWS('fm_review_facts'),REMOVEFILTERS('fm_review_facts'),\n"
                                                   ' '
                                                   "TREATAS(_candidateIds,'fm_review_facts'[SourceRevisionID]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                                   " TREATAS({_channel},'fm_review_facts'[Channel]),\n"
                                                   ' '
                                                   'FILTER(ALL(\'fm_review_facts\'[SubChannel]),COALESCE(\'fm_review_facts\'[SubChannel],"")=_sub))>0,1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Source Caption',
                                     'expression': 'IF(SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS")="Selected files",\n'
                                                   " IF(ISFILTERED('fm_native_files'[FileChoiceLabel]),\n"
                                                   ' "Selected files · '
                                                   '"&FORMAT(COUNTROWS(INTERSECT(VALUES(\'fm_review_files\'[SourceRevisionID]),\n'
                                                   ' VALUES(\'fm_native_files\'[SourceRevisionID]))),"0")&" '
                                                   'file(s) · comparisons separated by saved scenario",\n'
                                                   ' "Choose saved files below, then Apply filters"),\n'
                                                   "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR '
                                                   "_ims=SUMMARIZE(_files,'fm_native_files'[IMSActualsThrough])\n"
                                                   'VAR '
                                                   "_ef=SUMMARIZE(_files,'fm_native_files'[ExFactoryActualsThrough])\n"
                                                   'RETURN IF(NOT _sourceOK,"Choose an available source for '
                                                   'every selected driver.",\n'
                                                   ' IF(_custom,"Selected versions","ADS automatic")&" · '
                                                   '"&FORMAT(COUNTROWS(_files),"0")&" source(s) · IMS '
                                                   'through "&\n'
                                                   ' '
                                                   'IF(COUNTROWS(_ims)=1,FORMAT(MAXX(_ims,\'fm_native_files\'[IMSActualsThrough]),"mmm '
                                                   'yy"),"mixed cutoffs")&\n'
                                                   ' " · Ex-factory through '
                                                   '"&IF(COUNTROWS(_ef)=1,FORMAT(MAXX(_ef,\'fm_native_files\'[ExFactoryActualsThrough]),"mmm '
                                                   'yy"),"mixed cutoffs")))',
                                     'formatString': '',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Source OK',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'RETURN INT(_sourceOK)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Scenario Visible',
                                     'expression': 'IF(SELECTEDVALUE(\'fm_native_scenario\'[Mode])=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS")&&[N Source OK]=1,1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Scope Available',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR '
                                                   "_admitted=FILTER(_pool,_custom||'fm_native_files'[PreferenceRank]=1)\n"
                                                   'VAR '
                                                   '_candidateIds=SELECTCOLUMNS(_admitted,"ID",\'fm_native_files\'[SourceRevisionID])\n'
                                                   'RETURN '
                                                   "IF(COUNTROWS(FILTER('fm_native_scope','fm_native_scope'[SourceRevisionID] "
                                                   'IN _candidateIds))>0,1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Period Available',
                                     'expression': "VAR _start=MIN('fm_native_start_month'[Month]) VAR "
                                                   "_end=MAX('fm_native_end_month'[Month])\n"
                                                   "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   'RETURN IF(NOT ISBLANK(_start)&&NOT '
                                                   'ISBLANK(_end)&&_start<=_end&&NOT '
                                                   'ISBLANK(_y)&&_y>=YEAR(_start)&&_y<=YEAR(_end),1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Cutoff',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR '
                                                   '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                   'VAR _ef=IF(_row IN '
                                                   '{"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                                                   'VAR '
                                                   '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                                                   'RETURN IF(_sourceOK && '
                                                   'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])))=0,MINX(_dates,[Cutoff]))',
                                     'formatString': 'mmm yyyy',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Monthly Numerator',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 '
                                                   '&& COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                                   'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                                   '_singleCurrency)\n'
                                                   'VAR '
                                                   "_selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                                   "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                                   'VAR '
                                                   '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                                   'VAR _members=GENERATE(_files,\n'
                                                   " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                                   " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                                   " VAR _cc='fm_native_files'[Country]\n"
                                                   ' VAR '
                                                   "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                                   ' VAR '
                                                   "_digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                                   ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 '
                                                   '&& '
                                                   "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                                   '  VAR '
                                                   "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                                   '  VAR _half=INT(_exponent/2)\n'
                                                   '  RETURN '
                                                   "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                                   '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                                   ' VAR '
                                                   '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                                   ' VAR '
                                                   "_memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                                                   '  '
                                                   '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                                                   '  '
                                                   "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                                   '  '
                                                   "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                                   '  '
                                                   'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                                   'IN '
                                                   "_selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
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
                                                   '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) '
                                                   '&& '
                                                   '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                                   'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                                   'VAR '
                                                   '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                                   'RETURN IF(_sourceOK && NOT ISBLANK(_date) && '
                                                   'LEN(_component)>0 && COUNTROWS(_available)>0\n'
                                                   ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                                   'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                                   ' && (NOT _value || _usd || '
                                                   'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Monthly Denominator',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR _singleCurrency=COUNTROWS(DISTINCT(_currencies))=1 '
                                                   '&& COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0\n'
                                                   'VAR _convert=_value && _usd && (_row<>"share" || NOT '
                                                   '_singleCurrency)\n'
                                                   'VAR '
                                                   "_selectedChannels=VALUES('fm_review_facts'[Channel])\n"
                                                   "VAR _selectedSubs=VALUES('fm_review_facts'[SubChannel])\n"
                                                   'VAR '
                                                   '_fx=FILTER(CALCULATETABLE(\'fm_native_state\',ALLEXCEPT(\'fm_native_state\',\'fm_native_state\'[Token])),\'fm_native_state\'[Kind]="fx")\n'
                                                   'VAR _members=GENERATE(_files,\n'
                                                   " VAR _id='fm_native_files'[SourceRevisionID]\n"
                                                   " VAR _gd='fm_native_files'[GrowthDriver]\n"
                                                   " VAR _cc='fm_native_files'[Country]\n"
                                                   ' VAR '
                                                   "_currency=LOOKUPVALUE('fm_native_currency_map'[Currency],'fm_native_currency_map'[Country],_cc)\n"
                                                   ' VAR '
                                                   "_digits=FILTER(_fx,'fm_native_state'[Currency]=_currency)\n"
                                                   ' VAR _rate=IF(_currency="USD",1,IF(COUNTROWS(_digits)=7 '
                                                   '&& '
                                                   "COUNTROWS(SUMMARIZE(_digits,'fm_native_state'[Position]))=7,\n"
                                                   '  VAR '
                                                   "_exponent=MAXX(FILTER(_digits,'fm_native_state'[Position]=6),'fm_native_state'[Digit])\n"
                                                   '  VAR _half=INT(_exponent/2)\n'
                                                   '  RETURN '
                                                   "SUMX(FILTER(_digits,'fm_native_state'[Position]<6),'fm_native_state'[Digit]*POWER(1000,5-'fm_native_state'[Position]))*\n"
                                                   '  POWER(10,_half)*POWER(10,_exponent-_half)))\n'
                                                   ' VAR '
                                                   '_sectors=SELECTCOLUMNS(FILTER(_scope,\'fm_native_scope\'[GrowthDriver]=_gd),"Sector",\'fm_native_scope\'[Sector])\n'
                                                   ' VAR '
                                                   "_memberFacts=CALCULATETABLE(SELECTCOLUMNS('fm_review_facts',\n"
                                                   '  '
                                                   '"Sector",\'fm_review_facts\'[Sector],"Amount",\'fm_review_facts\'[Amount],"MissingCells",\'fm_review_facts\'[MissingCells]),REMOVEFILTERS(\'fm_review_facts\'),\n'
                                                   '  '
                                                   "TREATAS({_id},'fm_review_facts'[SourceRevisionID]),TREATAS({_date},'fm_review_facts'[Month]),\n"
                                                   '  '
                                                   "TREATAS(_sectors,'fm_review_facts'[Sector]),TREATAS({_component},'fm_review_facts'[ComponentKey]),\n"
                                                   '  '
                                                   'FILTER(ALL(\'fm_review_facts\'[Channel]),IF(_channel="*",\'fm_review_facts\'[Channel] '
                                                   'IN '
                                                   "_selectedChannels,'fm_review_facts'[Channel]=_channel)),\n"
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
                                                   '  "FXMissing",INT(_convert && NOT ISBLANK([RawAmount]) '
                                                   '&& '
                                                   '(ISBLANK(_rate)||ISERROR([RawAmount]*_rate))),"SourceCurrency",_currency))\n'
                                                   'VAR _available=FILTER(_members,NOT ISBLANK([Amount]))\n'
                                                   'VAR '
                                                   '_localCurrencies=DISTINCT(SELECTCOLUMNS(_members,"Currency",[SourceCurrency]))\n'
                                                   'RETURN IF(_sourceOK && NOT ISBLANK(_date) && '
                                                   'LEN(_component)>0 && COUNTROWS(_available)>0\n'
                                                   ' && SUMX(_members,[FXMissing])=0 && (NOT _value || '
                                                   'COUNTROWS(FILTER(_currencies,ISBLANK([CC])))=0)\n'
                                                   ' && (NOT _value || _usd || '
                                                   'COUNTROWS(_localCurrencies)=1),SUMX(_available,[Amount]))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Monthly',
                                     'expression': 'VAR _n=[N Monthly Numerator] VAR _d=[N Monthly '
                                                   'Denominator]\n'
                                                   'RETURN '
                                                   'IF(COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share",DIVIDE(_n,_d),_n)',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Trend Monthly',
                                     'expression': 'VAR _cut=[N Fit Cutoff] VAR '
                                                   "_w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                                   "VAR _m=SELECTEDVALUE('fm_review_axis'[Month])\n"
                                                   'RETURN IF(NOT ISBLANK(_m)&&NOT '
                                                   'ISBLANK(_cut),IF(_m<=_cut,[N Monthly],\n'
                                                   ' VAR _mean=CALCULATE([N Fit '
                                                   "Mean],REMOVEFILTERS('fm_review_axis'))\n"
                                                   ' VAR _slope=CALCULATE([N Fit '
                                                   "Slope],REMOVEFILTERS('fm_review_axis'))\n"
                                                   ' RETURN IF(NOT ISBLANK(_mean)&&NOT ISBLANK(_slope),\n'
                                                   ' _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Period Months',
                                     'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) "
                                                   'VAR _cut=[N Cutoff]\n'
                                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                                   'VAR '
                                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                                   'VAR '
                                                   '_end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                                   'RETURN IF(NOT ISBLANK(_y)&&NOT '
                                                   'ISBLANK(_cut)&&_end>=_start,DATEDIFF(_start,_end,MONTH)+1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Plan',
                                     'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) "
                                                   'VAR _cut=[N Cutoff]\n'
                                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                                   'VAR '
                                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                                   'VAR '
                                                   '_end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                                   'VAR '
                                                   '_count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                                                   'VAR '
                                                   '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                                                   'VAR '
                                                   '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                                                   'VAR _values=ADDCOLUMNS(_months,"N",VAR _m=[Date] RETURN\n'
                                                   ' CALCULATE([N Monthly '
                                                   "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])),\n"
                                                   ' "D",VAR _m=[Date] RETURN IF(_ratio,CALCULATE([N Monthly '
                                                   "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                                                   'VAR _valid=COUNTROWS(FILTER(_values,NOT '
                                                   'ISBLANK([N])))=_count\n'
                                                   '\n'
                                                   'RETURN IF(NOT ISBLANK(_y)&&NOT '
                                                   'ISBLANK(_cut)&&_count>0&&_valid,\n'
                                                   ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT '
                                                   'ISBLANK([D])))=_count,DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N Benchmark',
                                     'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) "
                                                   'VAR _cut=[N Cutoff]\n'
                                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                                   'VAR '
                                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                                   'VAR '
                                                   '_end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                                   'VAR '
                                                   '_count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                                                   'VAR '
                                                   '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]))\n'
                                                   'VAR '
                                                   '_ratio=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")="share"\n'
                                                   "VAR _w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                                   'VAR _mean=IF(_end>_cut,CALCULATE([N Fit '
                                                   "Mean],REMOVEFILTERS('fm_review_axis')))\n"
                                                   'VAR _slope=IF(_end>_cut,CALCULATE([N Fit '
                                                   "Slope],REMOVEFILTERS('fm_review_axis')))\n"
                                                   'VAR _base=ADDCOLUMNS(_months,"D",VAR _m=[Date] RETURN '
                                                   'IF(_ratio,\n'
                                                   ' CALCULATE([N Monthly '
                                                   "Denominator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                                                   'VAR _values=ADDCOLUMNS(_base,"N",VAR _m=[Date]\n'
                                                   ' VAR _forecast=IF(NOT ISBLANK(_mean)&&NOT '
                                                   'ISBLANK(_slope),\n'
                                                   ' _mean+_slope*(DATEDIFF(_cut,_m,MONTH)+_w-(_w+1)/2))\n'
                                                   ' RETURN IF(_m>_cut,IF(_ratio,IF(NOT '
                                                   'ISBLANK(_forecast)&&NOT '
                                                   'ISBLANK([D]),_forecast*[D]),_forecast),\n'
                                                   ' CALCULATE([N Monthly '
                                                   "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month]))))\n"
                                                   'VAR _valid=COUNTROWS(FILTER(_values,NOT '
                                                   'ISBLANK([N])))=_count\n'
                                                   'RETURN IF(NOT ISBLANK([N Fit Cutoff])&&NOT '
                                                   'ISBLANK(_y)&&NOT ISBLANK(_cut)&&_count>0&&_valid,\n'
                                                   ' IF(_ratio,IF(COUNTROWS(FILTER(_values,NOT '
                                                   'ISBLANK([D])))=_count,\n'
                                                   ' '
                                                   'DIVIDE(SUMX(_values,[N]),SUMX(_values,[D]))),SUMX(_values,[N])))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Variance',
                                     'expression': 'VAR _p=[N Plan] VAR _t=[N Benchmark] RETURN IF(NOT '
                                                   'ISBLANK(_p)&&NOT ISBLANK(_t),_p-_t)',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N Variance %',
                                     'expression': 'VAR _p=[N Plan] VAR _b=[N Benchmark]\n'
                                                   'RETURN IF(NOT ISBLANK(_p)&&NOT '
                                                   'ISBLANK(_b),DIVIDE(_p-_b,ABS(_b)))',
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': False},
                                    {'name': 'N Headline Variance',
                                     'expression': 'VAR '
                                                   "_w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                                   'VAR _actual=[N Actual Only]=1\n'
                                                   'RETURN IF(NOT _actual,CALCULATE([N '
                                                   "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Headline Variance %',
                                     'expression': 'VAR '
                                                   "_w=SELECTEDVALUE('fm_native_chart_trend'[Window],12)\n"
                                                   'VAR _actual=[N Actual Only]=1\n'
                                                   'RETURN IF(NOT _actual,CALCULATE([N Variance '
                                                   "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))",
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Summary Cell',
                                     'expression': "IF(HASONEVALUE('fm_native_scenario'[Scenario]),\n"
                                                   "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source "
                                                   'OK]=1,\n'
                                                   "VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])\n"
                                                   'RETURN IF(NOT _leaf,\n'
                                                   " IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N "
                                                   'Period Available]=1,[N Plan]),\n'
                                                   "VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])\n"
                                                   "VAR _w=SELECTEDVALUE('fm_native_columns'[Window])\n"
                                                   'VAR _allowed=_w=0 || _w IN '
                                                   "VALUES('fm_native_trend'[Window])\n"
                                                   'VAR _actualOnly=[N Actual Only]=1\n'
                                                   'RETURN IF([N Period '
                                                   'Available]=1&&_allowed,SWITCH(TRUE(),_key="plan",[N '
                                                   'Plan],_actualOnly,BLANK(),\n'
                                                   ' RIGHT(_key,3)="abs",CALCULATE([N '
                                                   "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),\n"
                                                   ' CALCULATE([N Variance '
                                                   "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window]))))))))",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Run Rate',
                                     'expression': 'IF(SELECTEDVALUE(\'fm_native_run_rate\'[Show],"Off")="On" '
                                                   "&& SELECTEDVALUE('fm_native_catalog'[RunRate],0)=1,\n"
                                                   ' DIVIDE([N Plan],[N Period Months]))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Growth %',
                                     'expression': "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) "
                                                   'VAR _cut=[N Cutoff]\n'
                                                   'VAR _first=DATE(_y,1,1) VAR _last=DATE(_y,12,1)\n'
                                                   'VAR _namedCut=DATE(_y,MONTH(_cut),1)\n'
                                                   'VAR '
                                                   '_start=SWITCH(_kind,"YTG",EDATE(_namedCut,1),"H2",DATE(_y,7,1),_first)\n'
                                                   'VAR '
                                                   '_end=SWITCH(_kind,"YTD",_namedCut,"H1",DATE(_y,6,1),_last)\n'
                                                   'VAR '
                                                   '_count=IF(_end>=_start,DATEDIFF(_start,_end,MONTH)+1,0)\n'
                                                   'VAR '
                                                   '_months=SELECTCOLUMNS(GENERATESERIES(0,MAX(0,_count-1)),"Date",EDATE(_start,[Value]-12))\n'
                                                   'VAR _values=ADDCOLUMNS(_months,"PY",VAR _m=[Date] RETURN '
                                                   'CALCULATE([N Monthly '
                                                   "Numerator],REMOVEFILTERS('fm_review_axis'),TREATAS({_m},'fm_review_axis'[Month])))\n"
                                                   'VAR _py=IF(_count>0 && COUNTROWS(FILTER(_values,NOT '
                                                   'ISBLANK([PY])))=_count,SUMX(_values,[PY]))\n'
                                                   'RETURN '
                                                   'IF(SELECTEDVALUE(\'fm_native_growth\'[Show],"Off")="On"&&SELECTEDVALUE(\'fm_native_catalog\'[Growth],0)=1,\n'
                                                   ' IF(NOT ISBLANK([N Plan])&&NOT ISBLANK(_py),DIVIDE([N '
                                                   'Plan]-_py,_py)))',
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N SOP Row Selected',
                                     'expression': "VAR _token=SELECTEDVALUE('fm_native_rows'[Token])\n"
                                                   "RETURN IF(ISFILTERED('fm_native_state'[Token]) && "
                                                   'SELECTEDVALUE(\'fm_native_rows\'[Kind])="row"\n'
                                                   " && SELECTEDVALUE('fm_native_rows'[Display])=[N "
                                                   'Display],1)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N SOP Plan',
                                     'expression': 'VAR '
                                                   "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                                   'VAR '
                                                   "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                                   ' '
                                                   "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                                   ' &&(NOT '
                                                   "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                                   'VAR '
                                                   "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                                   ' NOT '
                                                   "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                                   "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                                   'Group Visible]<>1,BLANK(),CALCULATE(\n'
                                                   "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                                   'RETURN IF([N SOP Row Selected]=1,CALCULATE([N '
                                                   "Plan],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                                   "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N SOP Run Rate',
                                     'expression': 'VAR '
                                                   "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                                   'VAR '
                                                   "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                                   ' '
                                                   "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                                   ' &&(NOT '
                                                   "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                                   'VAR '
                                                   "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                                   ' NOT '
                                                   "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                                   "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                                   'Group Visible]<>1,BLANK(),CALCULATE(\n'
                                                   "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                                   'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Run '
                                                   "Rate],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                                   "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N SOP Growth %',
                                     'expression': 'VAR '
                                                   "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                                   'VAR '
                                                   "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                                   ' '
                                                   "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                                   ' &&(NOT '
                                                   "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                                   'VAR '
                                                   "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                                   ' NOT '
                                                   "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                                   "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                                   'Group Visible]<>1,BLANK(),CALCULATE(\n'
                                                   "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                                   'RETURN IF([N SOP Row Selected]=1,CALCULATE([N Growth '
                                                   "%],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                                   "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': False},
                                    {'name': 'N SOP Monthly',
                                     'expression': 'VAR '
                                                   "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                                   'VAR '
                                                   "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                                   ' '
                                                   "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                                   ' &&(NOT '
                                                   "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                                   'VAR '
                                                   "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                                   ' NOT '
                                                   "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                                   "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                                   'Group Visible]<>1,BLANK(),CALCULATE(\n'
                                                   "VAR _row=SELECTEDVALUE('fm_native_rows'[RowID])\n"
                                                   'RETURN IF([N SOP Row Selected]=1 && '
                                                   "SELECTEDVALUE('fm_review_axis'[Month])>=MIN('fm_review_months'[Month]) "
                                                   '&& '
                                                   "SELECTEDVALUE('fm_review_axis'[Month])<=MAX('fm_review_months'[Month]),CALCULATE([N "
                                                   "Monthly],TREATAS({_row},'fm_native_catalog'[RowID]),TREATAS({[N "
                                                   "Display]},'fm_native_catalog'[Display]))),KEEPFILTERS(_groupScope),KEEPFILTERS(_groupCycles)))",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N SOP Monthly Growth %',
                                     'expression': 'VAR '
                                                   "_groupDriver=SELECTEDVALUE('fm_native_groups'[ScopeDriver])\n"
                                                   'VAR '
                                                   "_groupSector=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_groupIsSector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_groupCycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _groupScope=FILTER(ALLSELECTED('fm_native_scope'),\n"
                                                   ' '
                                                   "(LEN(_groupDriver)=0||'fm_native_scope'[GrowthDriver]=_groupDriver)\n"
                                                   ' &&(NOT '
                                                   "_groupIsSector||'fm_native_scope'[Sector]=_groupSector))\n"
                                                   'VAR '
                                                   "_groupCycles=FILTER(VALUES('fm_review_files'[DemandCycle]),\n"
                                                   ' NOT '
                                                   "HASONEVALUE('fm_native_groups'[DemandCycle])||'fm_review_files'[DemandCycle]=_groupCycle)\n"
                                                   "RETURN IF(ISINSCOPE('fm_native_groups'[ScopeLabel])&&[N "
                                                   'Group Visible]<>1,BLANK(),CALCULATE(\n'
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
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': False},
                                    {'name': 'N Export Selected',
                                     'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                                   'VAR _display=[N Display]\n'
                                                   'VAR '
                                                   "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                                   ' '
                                                   '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                                   'RETURN '
                                                   "IF(ISFILTERED('fm_native_state'[Token])&&COUNTROWS(_chosen)=1,1)",
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Export Plan',
                                     'expression': 'IF([N Export Selected]=1,[N Plan])',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Export Run Rate',
                                     'expression': 'IF([N Export Selected]=1,[N Run Rate])',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Export Growth %',
                                     'expression': 'IF([N Export Selected]=1,[N Growth %])',
                                     'formatString': '+0.0%;−0.0%;0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Export Order',
                                     'expression': "VAR _row=SELECTEDVALUE('fm_native_catalog'[RowID])\n"
                                                   'VAR _display=[N Display]\n'
                                                   'VAR '
                                                   "_chosen=FILTER(CALCULATETABLE('fm_native_state',ALLEXCEPT('fm_native_state','fm_native_state'[Token])),\n"
                                                   ' '
                                                   '\'fm_native_state\'[Kind]="row"&&\'fm_native_state\'[RowID]=_row&&\'fm_native_state\'[Display]=_display)\n'
                                                   'RETURN IF([N Export '
                                                   "Selected]=1,MINX(_chosen,'fm_native_state'[RowRank]))",
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Export Monthly',
                                     'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) RETURN "
                                                   'IF([N Export Selected]=1\n'
                                                   ' '
                                                   "&&_m>=MIN('fm_review_months'[Month])&&_m<=MAX('fm_review_months'[Month]),[N "
                                                   'Monthly])',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Export Month Stage',
                                     'expression': "VAR _m=SELECTEDVALUE('fm_review_axis'[Month]) VAR "
                                                   '_cut=[N Cutoff]\n'
                                                   'RETURN IF([N Export Selected]=1&&NOT ISBLANK(_m)&&NOT '
                                                   'ISBLANK(_cut),IF(_m<=_cut,"Actual","Forecast"))',
                                     'formatString': '',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Chart Monthly',
                                     'expression': 'IF([N Line Visible]=1,\n'
                                                   "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                                   "VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) "
                                                   "VAR _sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])\n"
                                                   'VAR '
                                                   "_sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1\n"
                                                   "VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) "
                                                   "VAR _type=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                                   'VAR '
                                                   '_row=IF(_type="sop",SELECTEDVALUE(\'fm_native_lines\'[RowID]),COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market"))\n'
                                                   "VAR _display=SELECTEDVALUE('fm_native_lines'[Display])\n"
                                                   'VAR _selected=_type="demand" || '
                                                   "ISFILTERED('fm_native_state'[Token]) && COUNTROWS(\n"
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
                                                   '_mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS")\n'
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
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Chart Amount',
                                     'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])<>"share",[N '
                                                   'Chart Monthly])',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Chart Share',
                                     'expression': 'IF(SELECTEDVALUE(\'fm_native_lines\'[RowID])="share",[N '
                                                   'Chart Monthly])',
                                     'formatString': '0.0%',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Status',
                                     'expression': 'SWITCH(TRUE(),[N Source OK]<>1,"Select a valid ADS '
                                                   'source for each selected cohort. Check Matching '
                                                   'files.",\n'
                                                   ' ISBLANK([N Cutoff]),"Selected sources have different '
                                                   'cutoffs; compare them separately.",\n'
                                                   ' "Saved ADS · IMS / EF calendars retained · Native R17 '
                                                   'candidate")',
                                     'formatString': '',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Variance Color',
                                     'expression': 'VAR _value=[N Summary Cell] RETURN '
                                                   'IF(SELECTEDVALUE(\'fm_native_columns\'[ColumnKey])="plan"||ISBLANK(_value)||_value=0,"#17384D",IF(_value>0,"#087D88","#AC640C"))',
                                     'formatString': '',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Fit Cutoff',
                                     'expression': "VAR _country = VALUES('fm_review_files'[Country])\n"
                                                   "VAR _cycles = VALUES('fm_review_files'[DemandCycle])\n"
                                                   'VAR _selectedDrivers = '
                                                   "VALUES('fm_native_scope'[GrowthDriver])\n"
                                                   'VAR _custom = '
                                                   'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS") = "Selected files"\n'
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
                                                   'VAR _pool = '
                                                   "FILTER(_poolAvailable,'fm_native_files'[GrowthDriver] IN "
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
                                                   'VAR '
                                                   '_row=COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market")\n'
                                                   'VAR _ef=IF(_row IN '
                                                   '{"share","abbott","market","pi","net"},FALSE(),TRUE())\n'
                                                   'VAR '
                                                   '_dates=SELECTCOLUMNS(_files,"Cutoff",IF(_ef,\'fm_native_files\'[ExFactoryActualsThrough],\'fm_native_files\'[IMSActualsThrough]))\n'
                                                   'RETURN IF(_sourceOK && '
                                                   'COUNTROWS(DISTINCT(_dates))=1,MAXX(_dates,[Cutoff]))',
                                     'formatString': 'mmm yyyy',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
                                     'isHidden': True},
                                    {'name': 'N Actual Only',
                                     'expression': "VAR _year=SELECTEDVALUE('fm_native_periods'[Year])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_periods'[PeriodType]) "
                                                   'VAR _cut=[N Cutoff]\n'
                                                   'VAR '
                                                   '_end=SWITCH(_kind,"YTD",DATE(_year,MONTH(_cut),1),"H1",DATE(_year,6,1),DATE(_year,12,1))\n'
                                                   'VAR _actualOnly=NOT ISBLANK(_cut)&&NOT '
                                                   'ISBLANK(_year)&&_end<=_cut\n'
                                                   'RETURN INT(_actualOnly)',
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'isHidden': True},
                                    {'name': 'N Line Visible',
                                     'expression': "VAR _view=SELECTEDVALUE('fm_native_lines'[ViewType])\n"
                                                   "VAR _mode=SELECTEDVALUE('fm_native_lines'[Mode])\n"
                                                   "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                                                   'VAR '
                                                   "_cycle=SELECTEDVALUE('fm_native_lines'[DemandCycle])\n"
                                                   "VAR _chart=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                                                   'RETURN '
                                                   'IF(CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total"))\n'
                                                   ' && '
                                                   '_mode=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                                                   'ADS")\n'
                                                   " && _cycle IN VALUES('fm_review_files'[DemandCycle])\n"
                                                   ' && (_chart="sop" || _kind IN {0,1} || '
                                                   "_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12)),1)",
                                     'formatString': '0',
                                     'displayFolder': 'Native review',
                                     'isHidden': True},
                                    {'name': 'N Selected Month',
                                     'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),\n"
                                                   ' FORMAT(SELECTEDVALUE(\'fm_review_axis\'[Month]),"mmm '
                                                   'yyyy"))',
                                     'displayFolder': 'Native review',
                                     'isHidden': True},
                                    {'name': 'N Selected Monthly',
                                     'expression': "IF(HASONEVALUE('fm_review_axis'[Month]),[N Monthly])",
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': True},
                                    {'name': 'N Headline Cell',
                                     'expression': "IF(HASONEVALUE('fm_native_scenario'[Scenario]),\n"
                                                   "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source "
                                                   'OK]=1&&[N Period Available]=1,\n'
                                                   "SWITCH(SELECTEDVALUE('fm_native_headline'[Key]),\n"
                                                   ' "plan",[N Plan],"variance",[N Headline '
                                                   'Variance],"pct",[N Headline Variance %]))))',
                                     'displayFolder': 'Native review',
                                     'description': 'R17 candidate; receiving DAX qualification required.',
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
                                                                              'VAR '
                                                                              '_value=ABS(SELECTEDMEASURE())\n'
                                                                              'VAR '
                                                                              '_number=SWITCH(TRUE(),_value>=1000000,"#,0,,.00" '
                                                                              '& '
                                                                              'UNICHAR(34)&"m"&UNICHAR(34),\n'
                                                                              ' _value>=1000,"#,0,.0" & '
                                                                              'UNICHAR(34)&"k"&UNICHAR(34),"#,0")\n'
                                                                              'RETURN '
                                                                              'IF(_pct||_row="share","0.0%;−0.0%;0.0%",_symbol&_number&";−"&_symbol&_number&";"&_symbol&"0")'},
                                     'isHidden': False},
                                    {'name': 'N Measure Caption',
                                     'expression': "IF(HASONEVALUE('fm_native_metric'[RowID]),\n"
                                                   'VAR '
                                                   '_name=SELECTEDVALUE(\'fm_native_metric\'[MetricLabel],"Selected '
                                                   'measures")\n'
                                                   'RETURN IF(CONTAINSSTRING(_name,"%"),_name,_name & IF([N '
                                                   'Display]="Value"," value"," units")),"Choose a measure '
                                                   'in the selected section")',
                                     'displayFolder': 'Native review',
                                     'isHidden': True},
                                    {'name': 'N Group Visible',
                                     'expression': 'VAR '
                                                   "_cycle=SELECTEDVALUE('fm_native_groups'[DemandCycle])\n"
                                                   "VAR _gd=SELECTEDVALUE('fm_native_groups'[ScopeDriver]) "
                                                   "VAR _sec=SELECTEDVALUE('fm_native_groups'[ScopeSector])\n"
                                                   'VAR '
                                                   "_sector=SELECTEDVALUE('fm_native_groups'[IsSector],0)=1\n"
                                                   'VAR '
                                                   "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)\n"
                                                   " &&(NOT _sector||'fm_native_scope'[Sector]=_sec))\n"
                                                   'RETURN IF(_cycle IN '
                                                   "VALUES('fm_review_files'[DemandCycle])&&COUNTROWS(_scope)>0,1)",
                                     'displayFolder': 'Native review',
                                     'formatString': '0',
                                     'isHidden': True},
                                    {'name': 'N Fit Mean',
                                     'expression': 'VAR _cut=[N Fit Cutoff] VAR '
                                                   "_w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                                   'VAR '
                                                   '_dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])\n'
                                                   'VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN\n'
                                                   ' CALCULATE([N '
                                                   "Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))\n"
                                                   'VAR _valid=COUNTROWS(FILTER(_train,NOT '
                                                   'ISBLANK([Y])))=_w\n'
                                                   'VAR _mx=AVERAGEX(_train,[X]) VAR '
                                                   '_my=AVERAGEX(_train,[Y])\n'
                                                   'RETURN IF(NOT ISBLANK(_cut)&&_valid,_my)',
                                     'displayFolder': 'Native performance',
                                     'isHidden': True},
                                    {'name': 'N Fit Slope',
                                     'expression': 'VAR _cut=[N Fit Cutoff] VAR '
                                                   "_w=SELECTEDVALUE('fm_native_trend'[Window],12)\n"
                                                   'VAR '
                                                   '_dates=SELECTCOLUMNS(GENERATESERIES(1,_w),"Date",EDATE(_cut,[Value]-_w),"X",[Value])\n'
                                                   'VAR _train=ADDCOLUMNS(_dates,"Y",VAR _d=[Date] RETURN\n'
                                                   ' CALCULATE([N '
                                                   "Monthly],REMOVEFILTERS('fm_review_axis'),TREATAS({_d},'fm_review_axis'[Month])))\n"
                                                   'VAR _valid=COUNTROWS(FILTER(_train,NOT '
                                                   'ISBLANK([Y])))=_w\n'
                                                   'VAR _mx=AVERAGEX(_train,[X]) VAR '
                                                   '_my=AVERAGEX(_train,[Y])\n'
                                                   'RETURN IF(NOT ISBLANK(_cut)&&_valid,\n'
                                                   ' '
                                                   'DIVIDE(SUMX(_train,([X]-_mx)*([Y]-_my)),SUMX(_train,POWER([X]-_mx,2))))',
                                     'displayFolder': 'Native performance',
                                     'isHidden': True}]},
                      {'name': 'fm_native_files',
                       'columns': [{'name': 'SourceRevisionID',
                                    'dataType': 'string',
                                    'sourceColumn': '[SourceRevisionID]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'SourceFileName',
                                    'dataType': 'string',
                                    'sourceColumn': '[SourceFileName]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'SourceRelativePath',
                                    'dataType': 'string',
                                    'sourceColumn': '[SourceRelativePath]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'Country',
                                    'dataType': 'string',
                                    'sourceColumn': '[Country]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'DemandCycle',
                                    'dataType': 'string',
                                    'sourceColumn': '[DemandCycle]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'GrowthDriver',
                                    'dataType': 'string',
                                    'sourceColumn': '[GrowthDriver]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'PublicationStatus',
                                    'dataType': 'string',
                                    'sourceColumn': '[PublicationStatus]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'FileLabel',
                                    'dataType': 'string',
                                    'sourceColumn': '[FileLabel]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'Scenario',
                                    'dataType': 'string',
                                    'sourceColumn': '[Scenario]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'IMSActualsThrough',
                                    'dataType': 'dateTime',
                                    'sourceColumn': '[IMSActualsThrough]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'ExFactoryActualsThrough',
                                    'dataType': 'dateTime',
                                    'sourceColumn': '[ExFactoryActualsThrough]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'ADSPriority',
                                    'dataType': 'int64',
                                    'sourceColumn': '[ADSPriority]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'ADSRevision',
                                    'dataType': 'int64',
                                    'sourceColumn': '[ADSRevision]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'PreferenceRank',
                                    'dataType': 'int64',
                                    'sourceColumn': '[PreferenceRank]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'PreferenceTies',
                                    'dataType': 'int64',
                                    'sourceColumn': '[PreferenceTies]',
                                    'summarizeBy': 'none',
                                    'type': 'calculatedTableColumn'},
                                   {'name': 'ImportedAtUTC',
                                    'dataType': 'dateTime',
                                    'type': 'calculatedTableColumn',
                                    'sourceColumn': '[ImportedAtUTC]',
                                    'summarizeBy': 'none',
                                    'formatString': 'dd mmm yyyy hh:mm:ss'},
                                   {'name': 'FileChoiceLabel',
                                    'dataType': 'string',
                                    'type': 'calculatedTableColumn',
                                    'sourceColumn': '[FileChoiceLabel]',
                                    'summarizeBy': 'none',
                                    'sortByColumn': 'ImportedAtUTC'}],
                       'partitions': [{'name': 'fm_native_files',
                                       'mode': 'import',
                                       'source': {'type': 'calculated',
                                                  'expression': '\n'
                                                                'VAR _base = '
                                                                "SELECTCOLUMNS('fm_review_files',\n"
                                                                ' "SourceRevisionID", [SourceRevisionID], '
                                                                '"SourceFileName", [SourceFileName],\n'
                                                                ' "SourceRelativePath", '
                                                                '[SourceRelativePath], "Country", '
                                                                '[Country],\n'
                                                                ' "DemandCycle", [DemandCycle], '
                                                                '"GrowthDriver", [GrowthDriver],\n'
                                                                ' "IMSActualsThrough", [IMSActualsThrough], '
                                                                '"ExFactoryActualsThrough", '
                                                                '[ExFactoryActualsThrough],\n'
                                                                ' "PublicationStatus", [PublicationStatus], '
                                                                '"FileLabel", [FileLabel])\n'
                                                                'VAR _stem = ADDCOLUMNS(_base, "_Stem",\n'
                                                                ' '
                                                                'SUBSTITUTE(SUBSTITUTE(UPPER([SourceFileName]), '
                                                                '".XLSM", ""), ".XLSX", ""))\n'
                                                                'VAR _parsed = ADDCOLUMNS(_stem,\n'
                                                                ' "_Revision", VAR _s = [_Stem] VAR _p = '
                                                                'SEARCH("_ADS_", _s, 1, 0)\n'
                                                                '  VAR _tail = TRIM(IF(_p > 0, MID(_s, _p + '
                                                                '5, LEN(_s))))\n'
                                                                '  VAR _digits = IF(LEFT(_tail, 1) IN {"+", '
                                                                '"-"}, MID(_tail, 2, LEN(_tail)), _tail)\n'
                                                                '  VAR _valid = LEN(_digits) > 0 && '
                                                                'COUNTROWS(FILTER(GENERATESERIES(1, MAX(1, '
                                                                'LEN(_digits))),\n'
                                                                '   NOT (MID(_digits, [Value], 1) IN {"0", '
                                                                '"1", "2", "3", "4", "5", "6", "7", "8", '
                                                                '"9"}))) = 0\n'
                                                                '  RETURN IF(_p > 0 && _valid, '
                                                                'IFERROR(CONVERT(_tail, INTEGER), '
                                                                'BLANK())),\n'
                                                                ' "_Imported", VAR _label = [FileLabel] VAR '
                                                                '_p = SEARCH(" · Imported ", _label, 1, 0)\n'
                                                                '  VAR _tail = IF(_p > 0, MID(_label, _p + '
                                                                '12, LEN(_label)))\n'
                                                                '  VAR _end = SEARCH(" · ", _tail, 1, 0)\n'
                                                                '  VAR _iso = IF(_end > 0, LEFT(_tail, _end '
                                                                '- 1), _tail)\n'
                                                                '  VAR _date = IFERROR(DATE(VALUE(LEFT(_iso, '
                                                                '4)), VALUE(MID(_iso, 6, 2)),\n'
                                                                '   VALUE(MID(_iso, 9, 2))), BLANK())\n'
                                                                '  VAR _time = IFERROR(TIME(VALUE(MID(_iso, '
                                                                '12, 2)), VALUE(MID(_iso, 15, 2)),\n'
                                                                '   VALUE(MID(_iso, 18, 2))), BLANK())\n'
                                                                '  VAR _zone = MAX(SEARCH("+", _iso, 20, 0), '
                                                                'SEARCH("-", _iso, 20, 0))\n'
                                                                '  VAR _offset = IF(_zone > 0,\n'
                                                                '   IFERROR((VALUE(MID(_iso, _zone + 1, 2)) '
                                                                '* 60 + VALUE(MID(_iso, _zone + 4, 2))) / '
                                                                '1440, 0), 0)\n'
                                                                '  VAR _fraction = IF(MID(_iso, 20, 1) = '
                                                                '".",\n'
                                                                '   IFERROR(VALUE("0" & MID(_iso, 20, '
                                                                'IF(_zone > 0, _zone - 20,\n'
                                                                '    LEN(SUBSTITUTE(_iso, "Z", "")) - 19))) '
                                                                '/ 86400, 0), 0)\n'
                                                                '  RETURN IF(_p > 0 && NOT ISBLANK(_date) && '
                                                                'NOT ISBLANK(_time),\n'
                                                                '   _date + _time + _fraction - IF(_zone > 0 '
                                                                '&& MID(_iso, MAX(1, _zone), 1) = "-", '
                                                                '-_offset, _offset)))\n'
                                                                'VAR _versions = ADDCOLUMNS(_parsed,\n'
                                                                ' "ADSPriority", SWITCH(TRUE(),\n'
                                                                '  RIGHT([_Stem], 9) IN {"_PLAN_ADS", '
                                                                '"_PLAN-ADS", "_PLAN ADS"}\n'
                                                                '   || RIGHT([_Stem], 8) = "_PLANADS", 3,\n'
                                                                '  RIGHT([_Stem], 4) = "_ADS", 2,\n'
                                                                '  NOT ISBLANK([_Revision]) && [_Revision] = '
                                                                'INT([_Revision]), 1, 0),\n'
                                                                ' "ADSRevision", COALESCE([_Revision], 0),\n'
                                                                ' "Scenario", VAR _s = [_Stem] VAR _ims = '
                                                                'SEARCH("_IMS", _s, 1, 0)\n'
                                                                '  VAR _start = IF(_ims > 0, SEARCH("_", _s, '
                                                                '_ims + 4, 0), 0)\n'
                                                                '  RETURN IF(_start > 0, MID(_s, _start + 1, '
                                                                '200), _s))\n'
                                                                'VAR _ranked = ADDCOLUMNS(_versions,\n'
                                                                ' "PreferenceRank", VAR _c = [Country] VAR '
                                                                '_cycle = [DemandCycle] VAR _driver = '
                                                                '[GrowthDriver]\n'
                                                                '  VAR _p = [ADSPriority] VAR _r = '
                                                                '[ADSRevision] VAR _i = [_Imported]\n'
                                                                '  RETURN 1 + '
                                                                'COUNTROWS(DISTINCT(SELECTCOLUMNS(FILTER(_versions,\n'
                                                                '   [Country] = _c && [DemandCycle] = _cycle '
                                                                '&& [GrowthDriver] = _driver\n'
                                                                '   && ([ADSPriority] > _p || ([ADSPriority] '
                                                                '= _p && [ADSRevision] > _r)\n'
                                                                '    || ([ADSPriority] = _p && [ADSRevision] '
                                                                '= _r && [_Imported] > _i))),\n'
                                                                '   "P", [ADSPriority], "R", [ADSRevision], '
                                                                '"I", [_Imported]))),\n'
                                                                ' "PreferenceTies", VAR _c = [Country] VAR '
                                                                '_cycle = [DemandCycle] VAR _driver = '
                                                                '[GrowthDriver]\n'
                                                                '  VAR _p = [ADSPriority] VAR _r = '
                                                                '[ADSRevision] VAR _i = [_Imported]\n'
                                                                '  RETURN COUNTROWS(FILTER(_versions, '
                                                                '[Country] = _c && [DemandCycle] = _cycle\n'
                                                                '   && [GrowthDriver] = _driver && '
                                                                '[ADSPriority] = _p && [ADSRevision] = _r\n'
                                                                '   && [_Imported] == _i)))\n'
                                                                'RETURN SELECTCOLUMNS(_ranked,\n'
                                                                ' "ImportedAtUTC",[_Imported],\n'
                                                                ' "FileChoiceLabel",[SourceFileName]&" | '
                                                                '"&IF(ISBLANK([_Imported]),"Import time '
                                                                'unavailable",\n'
                                                                ' FORMAT([_Imported],"dd MMM yyyy '
                                                                'HH:mm:ss","en-GB")&" UTC")&" | '
                                                                '"&[SourceRevisionID],\n'
                                                                ' "SourceRevisionID", [SourceRevisionID], '
                                                                '"SourceFileName", [SourceFileName],\n'
                                                                ' "SourceRelativePath", '
                                                                '[SourceRelativePath], "Country", '
                                                                '[Country],\n'
                                                                ' "DemandCycle", [DemandCycle], '
                                                                '"GrowthDriver", [GrowthDriver],\n'
                                                                ' "IMSActualsThrough", [IMSActualsThrough], '
                                                                '"ExFactoryActualsThrough", '
                                                                '[ExFactoryActualsThrough],\n'
                                                                ' "PublicationStatus", [PublicationStatus], '
                                                                '"FileLabel", [FileLabel],\n'
                                                                ' "ADSPriority", [ADSPriority], '
                                                                '"ADSRevision", [ADSRevision],\n'
                                                                ' "PreferenceRank", [PreferenceRank], '
                                                                '"PreferenceTies", [PreferenceTies], '
                                                                '"Scenario", [Scenario])\n'}}],
                       'description': 'OneLake R17.1 TEST metadata. Direct Lake calculated-table preview '
                                      'gate.'}],
           'relationships': [{'name': 'NativeR17-Rows-State',
                              'fromTable': 'fm_native_rows',
                              'fromColumn': 'Token',
                              'toTable': 'fm_native_state',
                              'toColumn': 'Token'},
                             {'name': 'NativeR17-Lines-Display',
                              'fromTable': 'fm_native_lines',
                              'fromColumn': 'Display',
                              'toTable': 'fm_native_display',
                              'toColumn': 'Display'},
                             {'name': 'NativeR17-Catalog-Display',
                              'fromTable': 'fm_native_catalog',
                              'fromColumn': 'Display',
                              'toTable': 'fm_native_display',
                              'toColumn': 'Display'},
                             {'name': 'NativeR17-Lines-View',
                              'fromTable': 'fm_native_lines',
                              'fromColumn': 'ViewType',
                              'toTable': 'fm_native_view',
                              'toColumn': 'View'},
                             {'name': 'NativeR17-Lines-Mode',
                              'fromTable': 'fm_native_lines',
                              'fromColumn': 'Mode',
                              'toTable': 'fm_native_file_mode',
                              'toColumn': 'Mode'},
                             {'name': 'NativeR17-Scenario-Mode',
                              'fromTable': 'fm_native_scenario',
                              'fromColumn': 'Mode',
                              'toTable': 'fm_native_file_mode',
                              'toColumn': 'Mode'},
                             {'name': 'NativeR172-Groups-View',
                              'fromTable': 'fm_native_groups',
                              'fromColumn': 'ViewType',
                              'toTable': 'fm_native_view',
                              'toColumn': 'View'}]}}

def original_database():
    return deepcopy(BASELINE)

def expression_hash(value):
    return hashlib.sha256(expression_text(value).strip().replace("\r\n","\n").encode()).hexdigest()

PICKED = "(ISFILTERED('fm_native_files'[FileChoiceLabel])||ISFILTERED('fm_review_files'[FileLabel]))"

MODE = ('IF((ISFILTERED(\'fm_native_files\'[FileChoiceLabel])||ISFILTERED(\'fm_review_files\'[FileLabel])),"Selected '
 'files","Automatic ADS")')

OLD_MODE = 'SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic ADS")'

DATE_OK = 'COUNTROWS(FILTER(_dates,ISBLANK([Cutoff])||[Cutoff]<DATE(2000,1,1)||[Cutoff]>=DATE(2100,1,1)))=0'

FILE_AVAILABLE = ("VAR _countries=VALUES('fm_review_files'[Country])\n"
 "VAR _cycles=VALUES('fm_review_files'[DemandCycle])\n"
 "VAR _drivers=VALUES('fm_native_scope'[GrowthDriver])\n"
 "RETURN IF(COUNTROWS(FILTER('fm_native_files','fm_native_files'[Country] IN _countries\n"
 " &&'fm_native_files'[DemandCycle] IN _cycles&&'fm_native_files'[GrowthDriver] IN _drivers))>0,1)")

def replacements():
    measures={m['name']:m for t in original_database()['model']['tables'] for m in t.get('measures',[])}
    result={name:m['expression'].replace(OLD_MODE,MODE) for name,m in measures.items() if OLD_MODE in m['expression']}
    for name in ('N Cutoff','N Fit Cutoff'):
        body=result[name]
        assert body.count('RETURN IF(_sourceOK &&')==1
        result[name]=body.replace('RETURN IF(_sourceOK &&','RETURN IF(_sourceOK && '+DATE_OK+' &&')
    caption=result['N Source Caption'].replace('Choose saved files below, then Apply filters','Choose saved files below')
    for table,column in (('_ims','IMSActualsThrough'),('_ef','ExFactoryActualsThrough')):
        old='FORMAT(MAXX('+table+",'fm_native_files'["+column+']),"mmm yy")'
        new='IF(MAXX('+table+",'fm_native_files'["+column+'])>=DATE(2000,1,1)&&MAXX('+table+",'fm_native_files'["+column+'])<DATE(2100,1,1),'+old+',"unavailable")'
        assert caption.count(old)==1
        caption=caption.replace(old,new)
    result['N Source Caption']='''VAR _c=[N Cutoff]
RETURN IF([N Source OK]=1&&(ISBLANK(_c)||_c<DATE(2000,1,1)||_c>=DATE(2100,1,1)),
 "Cutoff metadata unavailable · investigate source/native dates",
'''+caption+')'
    # Headline has no source-version row. Its existing complete/unique source
    # admission guard already refuses ambiguous alternative versions.
    prefix="IF(HASONEVALUE('fm_native_scenario'[Scenario]),\n"
    assert measures['N Headline Cell']['expression'].startswith(prefix)
    result['N Headline Cell']=measures['N Headline Cell']['expression'][len(prefix):-1]
    body=measures['N Summary Cell']['expression']
    assert body.startswith(prefix)
    result['N Summary Cell']=body.replace(prefix,
        "IF(HASONEVALUE('fm_native_scenario'[Scenario])&&SELECTEDVALUE('fm_native_scenario'[Mode])="+MODE+",\n",1)
    return result


def file_expression():
    table=next(t for t in original_database()['model']['tables'] if t['name']=='fm_native_files')
    before=table['partitions'][0]['source']['expression']
    old='''"FileChoiceLabel",[SourceFileName]&" | "&IF(ISBLANK([_Imported]),"Import time unavailable",
 FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")&" | "&[SourceRevisionID],'''
    new='''"FileChoiceLabel",VAR _name=[SourceFileName] VAR _id=[SourceRevisionID]
 VAR _stamp=IF(ISBLANK([_Imported]),"Import time unavailable",FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")
 VAR _same=FILTER(_ranked,[SourceFileName]=_name&&
  IF(ISBLANK([_Imported]),"Import time unavailable",FORMAT([_Imported],"dd MMM yyyy HH:mm:ss","en-GB")&" UTC")=_stamp)
 VAR _number=1+COUNTROWS(FILTER(_same,[SourceRevisionID]<_id))
 RETURN _name&" · "&_stamp&IF(COUNTROWS(_same)>1," · v"&FORMAT(_number,"0"),""),'''
    assert before.count(old)==1
    return before,before.replace(old,new)


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


def patch_database(database):
    baseline=original_database()
    expected={m['name']:m for t in baseline['model']['tables'] if t['name']=='fm_native_measures' for m in t['measures']}
    fixed=deepcopy(database)
    tables={t['name']:t for t in fixed['model']['tables']}
    if len(tables)!=len(fixed['model']['tables']):raise ValueError('Duplicate tables')
    measure_list=tables['fm_native_measures']['measures']
    actual={m['name']:m for m in measure_list}
    if len(actual)!=len(measure_list) or set(actual)!=set(expected):raise ValueError('Require known R17.7 native inventory')
    for name,old in expected.items():
        if expression_hash(actual[name]['expression'])!=expression_hash(old['expression']):raise ValueError('Unknown R17.7 expression')
        if normalized(actual[name].get('formatStringDefinition'))!=normalized(old.get('formatStringDefinition')):raise ValueError('Unknown dynamic format')
        # Actual server omits only five known empty static formats; keep its representation.
        if actual[name].get('formatString','')!=old.get('formatString',''):raise ValueError('Unknown static format')
    edits=replacements()
    for name,body in edits.items():actual[name]['expression']=body
    measure_list.append({'name':'N File Available','expression':FILE_AVAILABLE,
        'displayFolder':'Native metadata','isHidden':True,'formatString':'0'})
    old,new=file_expression()
    partitions=tables['fm_native_files']['partitions']
    if len(partitions)!=1:raise ValueError('Unknown file partition count')
    source=partitions[0]['source']
    if source.get('type')!='calculated' or expression_hash(source['expression'])!=expression_hash(old):raise ValueError('Unknown file helper')
    source['expression']=new
    restored=deepcopy(fixed)
    original={t['name']:t for t in database['model']['tables']}
    for table in restored['model']['tables']:
        if table['name']=='fm_native_measures':table['measures']=deepcopy(original[table['name']]['measures'])
        if table['name']=='fm_native_files':table['partitions']=deepcopy(original[table['name']]['partitions'])
    if restored!=database:raise AssertionError('Unrelated metadata changed')
    return fixed,sorted(edits)+['N File Available','fm_native_files.FileChoiceLabel expression']


EDITS = replacements()

METADATA_QUERY = 'EVALUATE SELECTCOLUMNS(TOPN(1,\n FILTER(ALL(\'fm_native_files\'),\'fm_native_files\'[ADSPriority]>0\n &&\'fm_native_files\'[PreferenceRank]=1&&\'fm_native_files\'[PreferenceTies]=1),\n \'fm_native_files\'[DemandCycle],DESC,\'fm_native_files\'[SourceRevisionID],ASC),\n "Country",\'fm_native_files\'[Country],"Cycle",\'fm_native_files\'[DemandCycle],\n "Driver",\'fm_native_files\'[GrowthDriver])'

"""Receiving workflow body; build_cell embeds reviewed constants and pure helpers.

Only TEST updateDefinition can mutate remote state. Refresh is a separate action.
Unknown outcome is sticky: the attempt marker forbids blind resubmission.
"""
EXPECTED_TEST_BIM='36870b56fffd9b1d0338472befe9dd530ade0cd959a4f67925f2a35a229f2b66'
RELEASE_PRIVATE='abfss://'+WORKSPACE+'@onelake.dfs.fabric.microsoft.com/'+LAKEHOUSE+'/Files/ForecastMasterRefreshState/report-upgrades/Native-R178-Compact-R01'
ATTEMPT=RELEASE_PRIVATE+'/ATTEMPT.json'


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


def scalar(evaluate,query):
    frame=evaluate(dataset=TEST,dax_string=query,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False)
    rows=frame.to_dict(orient='records')
    require(len(rows)==1 and len(rows[0])==1,'EXPECTED_ONE_SCALAR')
    return next(iter(rows[0].values()))


def preflight(evaluate,edits):
    # One scalar per sequential query. No SUMMARIZECOLUMNS/value-filter explosion.
    frame=evaluate(dataset=TEST,dax_string=METADATA_QUERY,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False)
    rows=[{k.rsplit('[',1)[-1].rstrip(']'):v for k,v in row.items()} for row in frame.to_dict(orient='records')]
    require(len(rows)==1 and set(rows[0])=={'Country','Cycle','Driver'},'NO_UNIQUE_ADS_SCOPE')
    scope=rows[0];year=int(str(scope['Cycle'])[:4]);count=0
    define='DEFINE\n'+'\n'.join("MEASURE 'fm_native_measures'["+name+"]=\n"+body for name,body in edits.items())+'\n'
    def f(table,column,value):return "TREATAS({"+('"'+str(value).replace('"','""')+'"')+"},'"+table+"'["+column+"])"
    shared=[f('fm_review_files','Country',scope['Country']),f('fm_review_files','DemandCycle',scope['Cycle']),
      f('fm_native_scope','GrowthDriver',scope['Driver']),f('fm_native_currency','Currency','Local'),
      f('fm_native_display','Display','Units'),f('fm_native_scenario','Mode','Automatic ADS'),
      f('fm_native_file_mode','Mode','Automatic ADS'),f('fm_native_periods','PeriodKey',str(year)+':FY'),
      "TREATAS({12},'fm_native_trend'[Window])"]
    for metric in ('market','ef','share'):
        for measure in ('N Plan','N Benchmark','N Variance %','N Trend Monthly'):
            print('R17.8 preflight '+str(count+1)+'/12: '+metric+' / '+measure+' (values private).',flush=True)
            filters=shared+[f('fm_native_metric','RowID',metric)]
            if measure=='N Trend Monthly':filters+=["TREATAS({DATE("+str(year+1)+",12,1)},'fm_review_axis'[Month])"]
            query='EVALUATE ROW("V",CALCULATE(['+measure+'],'+','.join(filters)+'))'
            left=scalar(evaluate,query);right=scalar(evaluate,define+query)
            require(isinstance(left,Number) and isinstance(right,Number) and not isinstance(left,bool) and not isinstance(right,bool)
              and math.isfinite(float(left)) and math.isfinite(float(right)) and math.isclose(float(left),float(right),rel_tol=1e-9,abs_tol=1e-6),
              'NUMERICAL_PREFLIGHT_UNAVAILABLE_OR_MISMATCH')
            count+=1
    return {'PairedScalarComparisons':count,'Mismatches':0,'ValuesPrintedOrStored':False,
            'Scope':'One available ADS driver; market/ef/share; 12M; FY and future month',
            'IndependentExcelParity':False}


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


def install(client,pbi,fs,evaluate,report):
    ctx={};identity(client,ctx)
    jobs_before=processing_history(pbi)
    before,database,bindings=read_definition(client,ctx);routing(database,bindings)
    require(digest(database)==EXPECTED_TEST_BIM,'TEST_CHANGED_SINCE_VERIFIED_INVENTORY')
    fixed,changed=patch_database(database)
    require(len(database['model']['tables'])==39 and sum(len(t.get('measures',[])) for t in database['model']['tables'])==98
      and len(database['model']['relationships'])==12,'TEST_INVENTORY_COUNTS_CHANGED')
    mapping=connections(client,ctx)
    require(any(c.get('connectivityType')=='ShareableCloud' for c in mapping),'CLOUD_MAPPING_NOT_CONFIRMED')
    require(not fs.exists(ATTEMPT),'PRIOR_R178_ATTEMPT_REVIEW_REQUIRED')
    report['DatePreflight']=validate_dates(evaluate)
    report['NumericalPreflight']=preflight(evaluate,EDITS)
    # Prevent a refresh/ingestion/model edit from invalidating privately checked inputs.
    dates_before=date_signature(evaluate)
    after=deepcopy(before)
    part=next(p for p in after['parts'] if p['path']=='model.bim')
    part['payload']=base64.b64encode(json.dumps(fixed,ensure_ascii=False).encode()).decode()
    folder=RELEASE_PRIVATE+'/'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())
    fs.mkdirs(folder)
    for name,value in [('definition-before.json',before),('definition-candidate.json',after),
                       ('connections-before.json',mapping),('preflight-counts.json',report)]:
        verified_backup(fs,folder+'/'+name,value)
    report['PrivateBackup']=folder
    latest,latest_db,_=read_definition(client,{})
    require(normalized(latest_db)==normalized(database) and latest==before and connections(client,{})==mapping
      and date_signature(evaluate)==dates_before and processing_history(pbi)==jobs_before,'CONCURRENT_TEST_CHANGE_NO_WRITE')
    # A durable write-once intent precedes submission. Any crash/unknown outcome stops reruns.
    verified_backup(fs,ATTEMPT,{'Revision':'R01','TEST':TEST,'Backup':folder,'BeforeBIM':digest(database),'CandidateBIM':digest(fixed)})
    report['ModelWriteRequested']=True
    response=client.post('/v1/workspaces/'+WORKSPACE+'/semanticModels/'+TEST+'/updateDefinition',
      json={'definition':after,'options':{'allowPurgeData':False}})
    complete_update(client,response,ctx,lambda value:verified_backup(fs,folder+'/operation.json',value))
    received,got,_=read_definition(client,{})
    # All non-BIM parts and the whole semantic document must agree; only DAX line arrays are normalized.
    expected_other=[p for p in after['parts'] if p['path']!='model.bim']
    got_other=[p for p in received['parts'] if p['path']!='model.bim']
    require(normalized(got)==normalized(fixed) and expected_other==got_other,'READBACK_DIFFERS_NO_REFRESH')
    require(connections(client,{})==mapping,'CLOUD_MAPPING_CHANGED_NO_REFRESH')
    report.update(Stage='TEST_R178_UPDATED',InstalledAtUTC=datetime.now(timezone.utc).isoformat(),MetadataChanged=changed,FullDefinitionPreservedExceptDeclaredChanges=True,
      CloudConnectionPreserved=True,RefreshRequiredOnce=True,
      NextStep='Refresh ONLY this existing TEST semantic model ONCE. Wait for Completed without warnings. Then open the R17.8 TEST PBIP and run VERIFY INSTALLED TEST R01.py. Never refresh production.')
    verified_backup(fs,folder+'/success.json',report)


def run(client,fs,evaluate,pbi):
    report={'Stage':'TEST_R178_INSTALL_STOPPED','Revision':'R01','TestModelID':TEST,'ModelWriteRequested':False,
      'OriginalModelWriteRequested':False,'LakehouseTableWriteRequested':False,'CompanyAmountValuesPrintedOrStored':False,
      'RefreshRequested':False,'ReportPublished':False,
      'NextStep':'Send this JSON. Do not retry, refresh or open the R17.8 TEST report until reviewed.'}
    try:install(client,pbi,fs,evaluate,report)
    except (Exception,KeyboardInterrupt) as exc:
        report.update(Stage='TEST_R178_INSTALL_STOPPED',RefreshRequiredOnce=False,Failure=safe_failure(exc),
          NextStep='Send this JSON. Do not retry, refresh or open R17.8 TEST until reviewed.')
    print(json.dumps(report,indent=2),flush=True)
    return report


"""Read-only post-refresh qualification appended to shared pure/read helpers."""

def read_private(fs,path):
    require(path==ATTEMPT or (path.startswith(RELEASE_PRIVATE+'/') and path.endswith(('/definition-candidate.json','/definition-before.json','/connections-before.json','/success.json'))),'PRIVATE_PATH_NOT_PINNED')
    require(fs.exists(path),'PRIVATE_RECEIPT_MISSING')
    with TemporaryDirectory(prefix='fm-r178-check-') as temp:
        local=Path(temp)/'private.json';require(fs.cp(path,local.as_uri(),False),'PRIVATE_READ_FAILED')
        require(0<local.stat().st_size<64*1024*1024,'PRIVATE_READ_SIZE_UNEXPECTED')
        return json.loads(local.read_bytes().decode('utf-8'))


def verify_installed(client,pbi,fs,evaluate,spark=None):
    result={'Stage':'TEST_R178_VERIFICATION_STOPPED','Revision':'R01','VerifierRevision':'R02','TestModelID':TEST,
      'ModelWriteRequested':False,'OriginalModelWriteRequested':False,'LakehouseTableWriteRequested':False,
      'RefreshRequested':False,'CompanyAmountValuesPrintedOrStored':False,'ReportPublished':False,
      'NextStep':'Send this JSON. Keep the backup. Do not rerun the installer or refresh again.'}
    try:
        identity(client,{})
        marker=read_private(fs,ATTEMPT);folder=marker['Backup']
        require(marker.get('Revision')=='R01' and marker.get('TEST')==TEST and folder.startswith(RELEASE_PRIVATE+'/'),'ATTEMPT_RECEIPT_UNEXPECTED')
        success=read_private(fs,folder+'/success.json')
        require(success.get('Stage')=='TEST_R178_UPDATED','INSTALL_NOT_VERIFIED')
        jobs=http({},pbi.get('https://api.powerbi.com/v1.0/myorg/groups/'+WORKSPACE+'/datasets/'+TEST+'/refreshes?$top=5'),{200}).json().get('value')
        require(isinstance(jobs,list) and jobs and jobs[0].get('status')=='Completed','TEST_REFRESH_NOT_COMPLETED')
        installed=datetime.fromisoformat(success['InstalledAtUTC'])
        started=datetime.fromisoformat(jobs[0]['startTime'].replace('Z','+00:00'))
        require(started>=installed,'NEW_ADAPTER_REFRESH_NOT_CONFIRMED')
        wanted=read_private(fs,folder+'/definition-candidate.json')
        original=read_private(fs,folder+'/definition-before.json')
        expected_db=json.loads(base64.b64decode(next(p for p in wanted['parts'] if p['path']=='model.bim')['payload']))
        _,current,_=read_definition(client,{})
        require(normalized(current)==normalized(expected_db),'INSTALLED_DEFINITION_DIFFERS')
        require(connections(client,{})==read_private(fs,folder+'/connections-before.json'),'CLOUD_MAPPING_CHANGED')
        jobs_before=processing_history(pbi)
        require(spark is not None,'SPARK_DATE_METADATA_READER_UNAVAILABLE')
        expected_dates=physical_dates(spark,fs,{})
        actual_dates=date_signature(evaluate)
        result['PhysicalSemanticDateGroups']=compare(expected_dates,actual_dates)
        require(all_match(result['PhysicalSemanticDateGroups']),'PHYSICAL_SEMANTIC_DATES_DIFFER')
        result['Dates']=validate_dates(evaluate)
        before_db=json.loads(base64.b64decode(next(p for p in original['parts'] if p['path']=='model.bim')['payload']))
        old={t['name']:t for t in before_db['model']['tables']}['fm_native_measures']['measures']
        result['NumericalComparisonToPrivateBaseline']=preflight(evaluate,{m['name']:expression_text(m['expression']) for m in old})
        # Empty metadata counts mean zero; business-amount blanks stay untouched.
        query='''EVALUATE ROW("Files",COUNTROWS('fm_native_files'),
 "Choices",DISTINCTCOUNT('fm_native_files'[FileChoiceLabel]),
 "MissingImportedAt",COALESCE(COUNTROWS(FILTER('fm_native_files',ISBLANK('fm_native_files'[ImportedAtUTC]))),0),
 "HashSuffixes",COALESCE(COUNTROWS(FILTER('fm_native_files',RIGHT('fm_native_files'[FileChoiceLabel],LEN('fm_native_files'[SourceRevisionID]))='fm_native_files'[SourceRevisionID])),0))'''
        rows=evaluate(dataset=TEST,dax_string=query,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False).to_dict(orient='records')
        require(len(rows)==1,'FILE_LABEL_CHECK_UNAVAILABLE')
        counts={k.rsplit('[',1)[-1].rstrip(']'):int(v) for k,v in rows[0].items()}
        require(counts['Files']>0 and counts['Files']==counts['Choices'] and counts['HashSuffixes']==0,'FILE_CHOICE_LABELS_INVALID')
        require(processing_history(pbi)==jobs_before and date_signature(evaluate)==actual_dates,'CONCURRENT_PROCESSING_OR_SOURCE_CHANGE')
        result.update(Stage='TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED',FileLabelCounts=counts,
          FullCandidateMetadataMatches=True,CloudMappingPreserved=True,
          NextStep='Open R17.8 TEST. Check Total and Sectors, two table trends, driver drill/expand and file selection/clear. Send screenshots plus Performance Analyzer DAX/total timings for graph and both summaries. Do not publish or change production.')
    except (Exception,KeyboardInterrupt) as exc:result['Failure']=safe_failure(exc)
    print(json.dumps(result,indent=2),flush=True)
    return result

if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    verify_installed(fabric.FabricRestClient(retry_config={"total":0}),fabric.PowerBIRestClient(retry_config={"total":0}),notebookutils.fs,fabric.evaluate_dax,globals().get("spark"))
