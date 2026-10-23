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
