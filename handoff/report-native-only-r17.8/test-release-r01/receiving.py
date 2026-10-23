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
