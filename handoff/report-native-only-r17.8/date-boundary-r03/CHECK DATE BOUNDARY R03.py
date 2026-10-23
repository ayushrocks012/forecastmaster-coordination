"""Read-only R03: keep per-step diagnostics and independent date evidence.

One NEW ForecastMaster_GM_Setup PySpark cell. No values/records/raw errors,
source/model writes, refresh, credentials or publication. R02 stays preserved.
"""
import base64
import json
import time
from urllib.parse import urlsplit
from uuid import UUID

WORKSPACE='f5cb5742-9a7c-4337-a4c0-952706dddf0b'
LAKEHOUSE='d6e33ebd-67b1-420a-8d84-c3a0d04d8b21'
TEST='31d00232-ac03-48fe-af39-f2e4bae82443'
NAME='ForecastMaster Native OneLake R17.1 - TEST'
ROOT='abfss://'+WORKSPACE+'@onelake.dfs.fabric.microsoft.com/'+LAKEHOUSE+'/Tables/'
FIELDS={'fm_review_files':['IMSActualsThrough','ExFactoryActualsThrough'],
        'fm_review_months':['Month'],'fm_review_axis':['Month'],'fm_review_facts':['Month']}
QUERY='''EVALUATE
VAR _files=FILTER(ALL('fm_review_files'),'fm_review_files'[Country]="UK"&&'fm_review_files'[DemandCycle]="2026-10")
VAR _ids=SELECTCOLUMNS(_files,"ID",'fm_review_files'[SourceRevisionID])
VAR _facts=CALCULATETABLE(VALUES('fm_review_facts'[Month]),TREATAS(_ids,'fm_review_facts'[SourceRevisionID]))
VAR _axis=VALUES('fm_review_axis'[Month])
VAR _months=VALUES('fm_review_months'[Month])
VAR _start=VALUES('fm_native_start_month'[Month])
VAR _end=VALUES('fm_native_end_month'[Month])
RETURN ROW("FactMonthKeys",COUNTROWS(_facts),
 "InvalidFactMonthKeys",COUNTROWS(FILTER(_facts,ISBLANK('fm_review_facts'[Month])||'fm_review_facts'[Month]<DATE(2000,1,1)||'fm_review_facts'[Month]>=DATE(2100,1,1))),
 "AxisMonthKeys",COUNTROWS(_axis),"InvalidAxisMonthKeys",COUNTROWS(FILTER(_axis,ISBLANK('fm_review_axis'[Month])||'fm_review_axis'[Month]<DATE(2000,1,1)||'fm_review_axis'[Month]>=DATE(2100,1,1))),
 "ReviewMonthKeys",COUNTROWS(_months),"InvalidReviewMonthKeys",COUNTROWS(FILTER(_months,ISBLANK('fm_review_months'[Month])||'fm_review_months'[Month]<DATE(2000,1,1)||'fm_review_months'[Month]>=DATE(2100,1,1))),
 "StartMonthKeys",COUNTROWS(_start),"InvalidStartMonthKeys",COUNTROWS(FILTER(_start,ISBLANK('fm_native_start_month'[Month])||'fm_native_start_month'[Month]<DATE(2000,1,1)||'fm_native_start_month'[Month]>=DATE(2100,1,1))),
 "EndMonthKeys",COUNTROWS(_end),"InvalidEndMonthKeys",COUNTROWS(FILTER(_end,ISBLANK('fm_native_end_month'[Month])||'fm_native_end_month'[Month]<DATE(2000,1,1)||'fm_native_end_month'[Month]>=DATE(2100,1,1))))'''


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


def attempt(step,action):
    ctx={'Step':step};start=time.monotonic()
    print('Read-only R03: '+step+' (metadata/counts only).',flush=True)
    try:
        data=action(ctx)
        return {'Status':'READ_COMPLETED','ElapsedMs':round((time.monotonic()-start)*1000),'Data':data}
    except Exception as exc:
        # All CheckStopped codes are fixed source literals, never API text.
        reason=exc.code if isinstance(exc,CheckStopped) else 'EXCEPTION_WITHHELD'
        family=type(exc).__name__
        allowed={'RuntimeError','ValueError','KeyError','TypeError','TimeoutError','FabricAdomdException',
                 'AnalysisException','Py4JJavaError','ModuleNotFoundError','JSONDecodeError','CheckStopped'}
        return {'Status':'READ_FAILED','ElapsedMs':round((time.monotonic()-start)*1000),
                'Failure':dict(ctx,Reason=reason,ExceptionFamily=family if family in allowed else 'OTHER_WITHHELD')}


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
    return result


def safe_counts(frame):
    rows=frame.to_dict(orient='records')
    expected={prefix+name for prefix in ('','Invalid') for name in
              ('FactMonthKeys','AxisMonthKeys','ReviewMonthKeys','StartMonthKeys','EndMonthKeys')}
    require(len(rows)==1,'METADATA_ROW_COUNT_INVALID')
    row={k.rsplit('[',1)[-1].rstrip(']'):v for k,v in rows[0].items()}
    require(set(row)==expected,'METADATA_FIELDS_UNEXPECTED')
    result={}
    for key,value in row.items():
        # Only known COUNTROWS cardinalities: empty-table BLANK is count zero.
        if value is None or isinstance(value,float) and value!=value:value=0
        require(not isinstance(value,bool) and isinstance(value,(int,float)) and
                value>=0 and value!=float('inf') and int(value)==value,'METADATA_COUNT_TYPE_INVALID')
        result[key]=int(value)
    return result


def month_counts(evaluate,ctx):
    ctx['Step']='SEMANTIC_MONTH_QUERY'
    frame=evaluate(dataset=TEST,dax_string=QUERY,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False)
    ctx['Step']='SEMANTIC_COUNT_VALIDATION'
    return safe_counts(frame)


def physical(spark,fs):
    from pyspark.sql import functions as F
    frames={};results={}
    for table,columns in FIELDS.items():
        def read(ctx):
            ctx['Step']='PHYSICAL_PATH_CHECK'
            paths=[ROOT+table,ROOT+'dbo/'+table]
            found=[path for path in paths if fs.exists(path+'/_delta_log')]
            require(len(found)==1,'PHYSICAL_PATH_MISSING_OR_AMBIGUOUS')
            ctx['Step']='PHYSICAL_METADATA_PROJECTION'
            if table=='fm_review_facts':require('fm_review_files' in frames,'PHYSICAL_FILE_SCOPE_UNAVAILABLE')
            selected=['SourceRevisionID','Country','DemandCycle']+columns if table=='fm_review_files' else (
                ['SourceRevisionID']+columns if table=='fm_review_facts' else columns)
            df=spark.read.format('delta').load(found[0]).select(*selected)
            if table=='fm_review_files':df=df.filter((F.col('Country')=='UK')&(F.col('DemandCycle')=='2026-10'))
            if table=='fm_review_facts':
                ids=frames['fm_review_files'].select('SourceRevisionID').distinct()
                df=df.join(F.broadcast(ids),'SourceRevisionID','inner').select('Month').distinct()
            ctx['Step']='PHYSICAL_DATE_AGGREGATES'
            cols={};aggregates=[F.count(F.lit(1)).alias('Rows')]
            for name in columns:
                kind=df.schema[name].dataType.simpleString()
                if kind not in {'date','timestamp','timestamp_ntz','string','int','bigint','double'}:kind='OTHER_WITHHELD'
                cols[name]={'PhysicalDataType':kind}
                if kind in {'date','timestamp','timestamp_ntz'}:
                    bad=F.col(name).isNull()|(F.year(F.col(name))<2000)|(F.year(F.col(name))>=2100)
                    aggregates.append(F.sum(F.when(bad,1).otherwise(0)).alias(name))
                else:cols[name]['Validity']='NOT_CAST; NON_DATE_TYPE'
            row=df.agg(*aggregates).collect()[0].asDict()
            for name in columns:
                if name in row:cols[name]['InvalidDateCount']=int(row[name] or 0)
            frames[table]=df
            return {'RowsOrDistinctFactMonthKeys':int(row['Rows']),'Columns':cols}
        results[table]=attempt(table,read)
    return results


def run(client,evaluate,spark,fs):
    def identity(ctx):
        ctx['Step']='TEST_IDENTITY'
        item=http(ctx,client.get('/v1/workspaces/'+WORKSPACE+'/items/'+TEST),{200}).json()
        require(item.get('id')==TEST and item.get('displayName')==NAME and item.get('type')=='SemanticModel','TEST_IDENTITY_MISMATCH')
        return {'ExactTESTConfirmed':True}
    checks={'Identity':attempt('Identity',identity)}
    if checks['Identity']['Status']=='READ_COMPLETED':
        checks['Definition']=attempt('Definition',lambda ctx:read_definition(client,ctx))
        checks['SemanticMonths']=attempt('SemanticMonths',lambda ctx:month_counts(evaluate,ctx))
        checks['PhysicalDates']=attempt('PhysicalDates',lambda ctx:physical(spark,fs))
    complete=len(checks)==4 and all(row['Status']=='READ_COMPLETED' for row in checks.values())
    if complete:
        data=checks['PhysicalDates']['Data']
        complete=set(data)==set(FIELDS) and all(row['Status']=='READ_COMPLETED' for row in data.values())
    stage='COMPLETED' if complete else ('STOPPED' if len(checks)==1 else 'PARTIAL')
    result={'Stage':'R178_DATE_BOUNDARY_R03_'+stage,'ProbeVersion':'R03','TestModelID':TEST,
      'AllRequestedReadsCompleted':complete,'Checks':checks,'RawErrorsOrHeadersPrinted':False,
      'CompanyAmountsQueriedOrPrinted':False,'SourceRecordsOrIdentifiersPrinted':False,
      'ModelWriteRequested':False,'LakehouseWriteRequested':False,'RefreshRequested':False,'ReportPublished':False,
      'NextStep':'Send this final JSON, including PARTIAL/STOPPED. No updater, refresh retry or source rewrite.'}
    print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__':
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(),fabric.evaluate_dax,spark,notebookutils.fs)
