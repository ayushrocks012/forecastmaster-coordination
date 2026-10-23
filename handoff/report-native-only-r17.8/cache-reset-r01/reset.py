"""Processing workflow appended to frozen read-only helpers by build.py."""

PBI_BASE='https://api.powerbi.com/v1.0/myorg/groups/'+WORKSPACE+'/datasets/'+TEST
ITEM='/v1/workspaces/'+WORKSPACE+'/items/'+TEST
PRIVATE=ROOT.replace('/Tables/','/Files/ForecastMasterRefreshState/report-upgrades/Native-R178-Date-Cache-R01')
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


def no_active_refresh(pbi,ctx):
    ctx['Step']='REFRESH_CONCURRENCY_CHECK'
    page=http(ctx,pbi.get(PBI_BASE+'/refreshes?$top=5'),{200}).json()
    require(isinstance(page.get('value'),list),'REFRESH_HISTORY_SHAPE_UNEXPECTED')
    require(all(row.get('status') in {'Completed','Failed','Disabled','Cancelled','Canceled'} for row in page['value']),
            'TEST_REFRESH_ACTIVE_OR_UNKNOWN')


def refresh(pbi,kind,state):
    state['Step']=kind.upper()+'_SUBMIT'
    # Mark before submitting: a lost response must not be reported as no action.
    state[kind+'Requested']=True
    response=pbi.post(PBI_BASE+'/refreshes',json={'type':kind,'commitMode':'transactional',
                      'maxParallelism':1,'retryCount':0,'applyRefreshPolicy':False,'timeout':'00:15:00'})
    http(state,response,{200,202})
    headers={key.lower():value for key,value in response.headers.items()}
    location=headers.get('location','')
    request_id=headers.get('x-ms-request-id')
    if location:
        parsed=urlsplit(location)
        require(parsed.scheme=='https' and parsed.netloc=='api.powerbi.com' and not parsed.query and not parsed.fragment and
                parsed.path.startswith(urlsplit(PBI_BASE).path+'/refreshes/'),'REFRESH_LOCATION_UNEXPECTED')
        suffix=parsed.path[len(urlsplit(PBI_BASE).path+'/refreshes/'):]
    else:suffix=request_id
    try:rid=str(UUID(suffix))
    except (ValueError,TypeError,AttributeError):raise CheckStopped('REFRESH_ID_UNAVAILABLE_OUTCOME_UNKNOWN') from None
    state[kind+'RequestID']=rid
    deadline=time.monotonic()+1200;poll=0
    while time.monotonic()<deadline:
        state['Step']=kind.upper()+'_POLL'
        response=http(state,pbi.get(PBI_BASE+'/refreshes/'+rid),{200,202});detail=response.json()
        status=detail.get('status');extended=detail.get('extendedStatus',status)
        require(status not in {'Failed','Disabled','Cancelled','Canceled'} and extended not in {'Failed','TimedOut','Cancelled','Disabled'},
                'TEST_REFRESH_FAILED')
        if response.status_code==200 and status=='Completed':
            messages=detail.get('messages',[])
            require(isinstance(messages,list),'REFRESH_MESSAGES_SHAPE_UNEXPECTED')
            state[kind+'Completed']=True;state[kind+'MessageCount']=len(messages)
            return
        require(status=='Unknown' and extended in {'Unknown','NotStarted','InProgress'},'REFRESH_STATUS_UNEXPECTED')
        poll+=1
        if poll==1 or poll%6==0:print('TEST '+kind+': processing; waiting for completion.',flush=True)
        time.sleep(5)
    raise CheckStopped('TEST_REFRESH_OUTCOME_UNCONFIRMED')


def run(client,pbi,evaluate,spark,fs):
    state={'Step':'START','clearValuesRequested':False,'clearValuesCompleted':False,'fullRequested':False,'fullCompleted':False}
    result={'Stage':'TEST_R178_DATE_CACHE_RESET_STOPPED','Revision':'R01','TestModelID':TEST,
      'ModelDefinitionWriteRequested':False,'LakehouseTableWriteRequested':False,'OriginalModelWriteRequested':False,
      'CompanyAmountQuerySubmitted':False,'CompanyAmountsPrintedOrStoredByScript':False,'ReportPublished':False,
      'NativeR178AdapterInstalled':False}
    try:
        identity(client,state)
        require(not fs.exists(PRIVATE+'/ATTEMPT.json'),'RESET_ALREADY_ATTEMPTED_SEND_PRIOR_RESULT')
        print('TEST only: checking binding and exact date metadata; amounts stay private.',flush=True)
        before,db,bindings=read_definition(client,state);routing(db,bindings)
        physical_before=physical_dates(spark,fs,state)
        result['DatesBefore']=compare(physical_before,semantic_dates(evaluate,state))
        if all_match(result['DatesBefore']):
            result['Stage']='TEST_R178_DATES_ALREADY_MATCH_NO_RESET'
            result['DateParityVerified']=True
        else:
            no_active_refresh(pbi,state)
            mapping=connections(client,state)
            backup=PRIVATE+'/'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')+'-'+str(uuid4())
            result['Backup']=backup
            state['Step']='PRIVATE_BACKUP';fs.mkdirs(backup)
            require(fs.exists(backup),'PRIVATE_BACKUP_DIRECTORY_FAILED')
            verified_backup(fs,backup+'/definition-before.json',before)
            verified_backup(fs,backup+'/connections-before.json',mapping)
            verified_backup(fs,backup+'/date-counts-before.json',result['DatesBefore'])
            result['BackupVerification']='FULL_FILE_UTF8_SHA256_AND_LENGTH'
            again,_,_=read_definition(client,state)
            require(digest(before)==digest(again) and digest(mapping)==digest(connections(client,state)),
                    'TEST_METADATA_CHANGED_NO_RESET')
            no_active_refresh(pbi,state)
            state['Step']='ATTEMPT_MARKER'
            verified_backup(fs,PRIVATE+'/ATTEMPT.json',{'Revision':'R01','TEST':TEST,'Backup':backup,'Action':'clearValues then full; run once'})
            print('Verified private TEST backup. Clearing TEST loaded values, then full refresh.',flush=True)
            refresh(pbi,'clearValues',state)
            refresh(pbi,'full',state)
            after,_,_=read_definition(client,state)
            result['OtherModelDefinitionPreserved']=digest(before)==digest(after)
            result['CloudConnectionPreserved']=digest(mapping)==digest(connections(client,state))
            physical_after=physical_dates(spark,fs,state)
            result['PhysicalDateMetadataStable']=physical_before==physical_after
            result['DatesAfter']=compare(physical_after,semantic_dates(evaluate,state))
            result['DateParityVerified']=all_match(result['DatesAfter'])
            require(result['OtherModelDefinitionPreserved'] and result['CloudConnectionPreserved'],
                    'TEST_METADATA_READBACK_NEEDS_REVIEW')
            require(result['PhysicalDateMetadataStable'],'PHYSICAL_DATE_METADATA_CHANGED_REVIEW_RESULT')
            require(result['DateParityVerified'],'DATES_STILL_DIFFER_AFTER_RESET')
            require(state.get('clearValuesMessageCount')==state.get('fullMessageCount')==0,'REFRESH_MESSAGES_REQUIRE_REVIEW')
            result['Stage']='TEST_R178_DATE_CACHE_RESET_VERIFIED'
    except Exception as exc:
        code=exc.code if isinstance(exc,CheckStopped) else 'EXCEPTION_WITHHELD'
        result['Failure']={'Reason':code,'ExceptionFamily':type(exc).__name__ if type(exc).__name__ in
                          {'CheckStopped','RuntimeError','KeyError','TypeError','ValueError','FabricAdomdException','TimeoutError'} else 'OTHER_WITHHELD'}
    result['Processing']=state
    result['RawErrorsOrSourceRecordsPrinted']=False
    result['NextStep']='Send this final JSON. Do not rerun, manually refresh or install an updater until reviewed.'
    print(json.dumps(result,indent=2),flush=True);return result


if __name__=='__main__':
    import sempy.fabric as fabric
    import notebookutils
    # Disable SDK submission retries as well as REST retryCount. Service-internal
    # retries remain possible; the script never resubmits an ambiguous POST.
    no_retry={'total':0,'allowed_methods':['GET'],'raise_on_status':False}
    run(fabric.FabricRestClient(retry_config=no_retry),fabric.PowerBIRestClient(retry_config=no_retry),
        fabric.evaluate_dax,spark,notebookutils.fs)
