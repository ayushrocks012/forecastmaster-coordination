"""Read-only TEST/Lakehouse date-boundary check after R01 counts returned.

No amounts, raw file records, identifiers, model writes or table writes.
Uses only the existing known Lakehouse and isolated TEST. Run one NEW cell.
"""
import base64
import json
import time

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


def definition(client):
    path='/v1/workspaces/'+WORKSPACE+'/semanticModels/'+TEST+'/getDefinition?format=TMSL'
    response=client.post(path)
    if response.status_code==202:
        location=response.headers.get('Location','')
        prefix='https://api.fabric.microsoft.com'
        if location.startswith(prefix+'/v1/operations/'):location=location[len(prefix):]
        if not location.startswith('/v1/operations/') or '?' in location:raise RuntimeError('Unsupported read operation')
        for _ in range(30):
            time.sleep(2)
            status=client.get(location)
            if status.status_code!=200:raise RuntimeError('Read operation unavailable')
            state=status.json().get('status')
            if state=='Succeeded':
                response=client.get(location+'/result');break
            if state in {'Failed','Cancelled'}:raise RuntimeError('Read operation failed')
        else:raise RuntimeError('Read operation incomplete')
    if response.status_code!=200:raise RuntimeError('Definition read unavailable')
    parts=response.json()['definition']['parts']
    values=[p for p in parts if p['path']=='model.bim']
    if len(values)!=1:raise RuntimeError('Expected one definition part')
    db=json.loads(base64.b64decode(values[0]['payload']))
    tables={t['name']:t for t in db['model']['tables']}
    result={}
    for table,columns in FIELDS.items():
        t=tables[table];part=t.get('partitions',[])
        c={c['name']:c for c in t['columns']}
        source=part[0].get('source',{}) if len(part)==1 else {}
        result[table]={'PartitionCount':len(part),'Mode':part[0].get('mode','unknown') if len(part)==1 else 'unknown',
            'SourceType':source.get('type','unknown'),
            'EntityNameMatchesExpected':source.get('entityName')==table,
            'Columns':{name:{'ModelDataType':c[name].get('dataType','unknown'),
                             'ColumnKind':c[name].get('type','data'),
                             'SourceColumnMatchesExpected':c[name].get('sourceColumn')==
                              ('['+name+']' if c[name].get('type')=='calculatedTableColumn' else name)} for name in columns}}
    return result


def safe_counts(frame):
    rows=frame.to_dict(orient='records')
    expected={'FactMonthKeys','InvalidFactMonthKeys','AxisMonthKeys','InvalidAxisMonthKeys',
              'ReviewMonthKeys','InvalidReviewMonthKeys','StartMonthKeys','InvalidStartMonthKeys','EndMonthKeys','InvalidEndMonthKeys'}
    if len(rows)!=1:raise RuntimeError('Unexpected metadata row count')
    row={k.rsplit('[',1)[-1].rstrip(']'):v for k,v in rows[0].items()}
    if set(row)!=expected:raise RuntimeError('Unexpected metadata fields')
    result={}
    for key,value in row.items():
        if value is None or isinstance(value,float) and value!=value:value=0
        if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0 or int(value)!=value:raise RuntimeError('Unexpected metadata count')
        result[key]=int(value)
    return result


def physical(spark,fs):
    from pyspark.sql import functions as F
    frames={};results={}
    for table,columns in FIELDS.items():
        paths=[ROOT+table,ROOT+'dbo/'+table]
        found=[path for path in paths if fs.exists(path+'/_delta_log')]
        if len(found)!=1:
            results[table]={'Status':'PATH_MISSING_OR_AMBIGUOUS'};continue
        df=spark.read.format('delta').load(found[0])
        selected=['SourceRevisionID','Country','DemandCycle']+columns if table=='fm_review_files' else (
            ['SourceRevisionID']+columns if table=='fm_review_facts' else columns)
        df=df.select(*selected)
        if table=='fm_review_files':df=df.filter((F.col('Country')=='UK')&(F.col('DemandCycle')=='2026-10'))
        if table=='fm_review_facts':
            if 'fm_review_files' not in frames:
                results[table]={'Status':'FILE_SCOPE_UNAVAILABLE'};continue
            ids=frames['fm_review_files'].select('SourceRevisionID').distinct()
            df=df.join(F.broadcast(ids),'SourceRevisionID','inner').select('Month').distinct()
        frames[table]=df
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
        results[table]={'Status':'READ_COMPLETED','RowsOrDistinctFactMonthKeys':int(row['Rows']), 'Columns':cols}
    return results


def run(client,evaluate,spark,fs):
    identity=client.get('/v1/workspaces/'+WORKSPACE+'/items/'+TEST)
    if identity.status_code!=200:raise RuntimeError('Identity unavailable')
    item=identity.json()
    if item.get('id')!=TEST or item.get('displayName')!=NAME or item.get('type')!='SemanticModel':raise RuntimeError('Wrong TEST')
    print('Read-only date boundary: TEST metadata/month-key counts and physical Lakehouse DATE columns only.',flush=True)
    binding=definition(client)
    semantic=safe_counts(evaluate(dataset=TEST,dax_string=QUERY,workspace=WORKSPACE,verbose=0,use_readwrite_connection=False))
    delta=physical(spark,fs)
    complete=all(row.get('Status')=='READ_COMPLETED' for row in delta.values()) and set(delta)==set(FIELDS)
    result={'Stage':'R178_DATE_BOUNDARY_READS_COMPLETED' if complete else 'R178_DATE_BOUNDARY_PARTIAL',
            'AllPhysicalDateReadsCompleted':complete,'TestModelID':TEST,'TESTDateBindings':binding,
            'SemanticMonthCounts':semantic,'PhysicalDateChecks':delta,
            'CompanyAmountsQueriedOrPrinted':False,'SourceRecordsOrIdentifiersPrinted':False,
            'ModelWriteRequested':False,'LakehouseWriteRequested':False,'RefreshRequested':False,'ReportPublished':False,
            'NextStep':'Send this JSON. No updater/refresh/source rewrite yet; retain the private backup.'}
    print(json.dumps(result,indent=2),flush=True);return result


def safe_run(client,evaluate,spark,fs):
    try:return run(client,evaluate,spark,fs)
    except Exception as exc:
        result={'Stage':'R178_DATE_BOUNDARY_CHECK_STOPPED','ExceptionFamily':type(exc).__name__,'RawErrorPrinted':False,
                'CompanyAmountsQueriedOrPrinted':False,'ModelWriteRequested':False,'LakehouseWriteRequested':False,
                'RefreshRequested':False,'ReportPublished':False,'NextStep':'Send this JSON; no update or refresh retry.'}
        print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__':
    import sempy.fabric as fabric
    import notebookutils
    safe_run(fabric.FabricRestClient(),fabric.evaluate_dax,spark,notebookutils.fs)
