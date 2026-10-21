"""Read a supplied thin PBIX, emit a NEW PBIP. Never write or re-zip a PBIX.

The resulting company-bound report is PRIVATE and must not be committed here.
"""
from pathlib import Path
from zipfile import ZipFile
import argparse,hashlib,json,shutil

HERE=Path(__file__).resolve().parent
GUID='ForecastMasterGMReviewR16'

def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def create(source,destination):
    if not source.is_file():raise FileNotFoundError(source)
    if destination.exists():raise ValueError('Use a new output folder; existing projects are preserved.')
    destination.mkdir(parents=True)
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    backup=destination/'Original - before GM redesign.pbix';shutil.copy2(source,backup)
    project=destination/'ForecastMaster GM Review';project.mkdir()
    report=project/'ForecastMaster GM Review.Report';report.mkdir()
    with ZipFile(source) as z:
        def read(name):return json.loads(z.read(name).decode('utf-8-sig'))
        connections=read('Connections');connection=connections['Connections'][0]
        for n in z.namelist():
            if not n.startswith('Report/'):continue
            rel=n.removeprefix('Report/')
            if rel.startswith('CustomVisuals/') or rel.startswith('definition/pages/reviewmeeting/'):continue
            p=report/rel
            if n.endswith('/'):p.mkdir(parents=True,exist_ok=True)
            else:p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
        layout=read('Report/definition/pages/reviewmeeting/visuals/reviewworkspace/visual.json')
        oldExtensions=read('Report/definition/reportExtensions.json')
        old=next(e for e in oldExtensions['entities'] if e['name']=='fm_review_measures')['measures']
        oldByName={m['name']:m for m in old}
        fileExpression=oldByName['FM R04 File']['expression']
        fileExpression=fileExpression[fileExpression.index('VAR _month'):].rsplit('\n)',1)[0]
        fileExpression=fileExpression.replace("VAR _first = MINX(ALL('fm_review_axis'), 'fm_review_axis'[Month])", "VAR _id = SELECTEDVALUE('fm_review_files'[SourceRevisionID])\nVAR _first = CALCULATE(MIN('fm_review_facts'[Month]), REMOVEFILTERS('fm_review_facts'), TREATAS({_id}, 'fm_review_facts'[SourceRevisionID]))")
        fileExpression=fileExpression.replace('IF(_month = _first,','IF(_month = _first && NOT ISBLANK([FM GM Missing]),')
        components=[r['NumeratorKey'] for r in json.loads((HERE/'GM-RULES.json').read_text())]+['ef-ads-units','ef-ads-value']
        admitted='{'+', '.join('"'+key+'"' for key in components)+'}'
        base="""VAR _id = SELECTEDVALUE('fm_review_files'[SourceRevisionID])
VAR _month = SELECTEDVALUE('fm_review_axis'[Month])
VAR _component = SELECTEDVALUE('fm_review_facts'[ComponentKey])
RETURN IF(NOT ISBLANK(_id) && NOT ISBLANK(_month) && _component IN __ADMITTED__,
 CALCULATE(SUM('fm_review_facts'[%s]),
  TREATAS({_id},'fm_review_facts'[SourceRevisionID]),
  TREATAS({_month},'fm_review_facts'[Month])))""".replace('__ADMITTED__',admitted)
        expressions={'FM GM Amount':('Double',base%'Amount'),'FM GM Missing':('Double',base%'MissingCells'),'FM GM File':('Text',fileExpression)}
        bounds=oldByName['FM R04 Bounds']['expression']
        bounds=bounds[bounds.index('VAR _firstMonth'):].rsplit('\n)',1)[0]
        bounds=bounds.replace("VAR _first = SELECTEDVALUE('fm_review_axis'[Month]) = _firstMonth && SELECTEDVALUE('fm_review_files'[SourceRevisionID]) = _firstFile",'VAR _first = NOT ISBLANK([FM GM File])')
        expressions['FM GM Bounds']=('Text',bounds)
        for name,(kind,expression) in expressions.items():
            old.append({'name':name,'dataType':kind,'expression':expression,'description':'R16 report-local complete monthly feed; existing semantic model definition is unchanged.','displayFolder':'Forecast review\\GM report feed'})
        write(report/'definition/reportExtensions.json',oldExtensions)
        query={}
        mappings={'FileID':('fm_review_files','SourceRevisionID'),'Month':('fm_review_axis','Month'),'MetricKey':('fm_review_facts','ComponentKey'),'Channel':('fm_review_facts','Channel'),'SubChannel':('fm_review_facts','SubChannel'),'Sector':('fm_review_facts','Sector')}
        measures={'Numerator':'FM GM Amount','NumeratorMissing':'FM GM Missing','FileMetadata':'FM GM File','Bounds':'FM GM Bounds'}
        for role,(table,column) in mappings.items():
            query[role]={'projections':[{'field':{'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':column}},'queryRef':table+'.'+column,'nativeQueryRef':column,'active':True}]}
        for role,name in measures.items():
            table='fm_review_measures';query[role]={'projections':[{'field':{'Measure':{'Expression':{'SourceRef':{'Schema':'extension','Entity':table}},'Property':name}},'queryRef':table+'.'+name,'nativeQueryRef':name,'active':True}]}
        for key,title,mode in [('demandreview','GM Review','demand')]:
            page=read('Report/definition/pages/reviewmeeting/page.json');page.update(name=key,displayName=title,width=1440,height=810,displayOption='FitToPage')
            write(report/f'definition/pages/{key}/page.json',page)
            visual=json.loads(json.dumps(layout));visual['name']=key+'workspace';visual['position'].update(height=810,width=1440)
            visual['visual']['visualType']=GUID;visual['visual']['query']={'queryState':query}
            visual['visual']['objects']={'general':[{'properties':{'page':{'expr':{'Literal':{'Value':"'"+mode+"'"}}}}}]}
            visual.pop('filterConfig',None)
            write(report/f'definition/pages/{key}/visuals/{key}workspace/visual.json',visual)
        pages=read('Report/definition/pages/pages.json');pages.update(pageOrder=['demandreview','refreshdemand'],activePageName='demandreview');write(report/'definition/pages/pages.json',pages)
        config=read('Report/definition/report.json');config['resourcePackages']=[p for p in config['resourcePackages'] if p['type'] not in ['CustomVisual','RegisteredResources']]
        config['themeCollection'].pop('customTheme',None)
        config['resourcePackages'].append({'name':GUID,'type':'CustomVisual','items':[{'name':f'resources/{GUID}.pbiviz.json','path':f'{GUID}.pbiviz.json','type':'CustomVisualMetadata'}]})
        write(report/'definition/report.json',config)
        package=next((HERE/'Visual/dist').glob('*.pbiviz'))
        with ZipFile(package) as pv:
            for n in pv.namelist():
                if n.endswith('/'):continue
                p=report/'CustomVisuals'/GUID/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(pv.read(n))
        cs=connection['ConnectionString'].rstrip(';')+';semanticModelId='+connection['PbiModelDatabaseName']
        write(report/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json','version':'4.0','datasetReference':{'byConnection':{'connectionString':cs}}})
        write(project/'ForecastMaster GM Review.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':report.name}}],'settings':{'enableAutoRecovery':True}})
        kept={n:hashlib.sha256(z.read(n)).hexdigest() for n in z.namelist() if n.startswith('Report/definition/pages/refreshdemand/')}
        for n,h in kept.items():assert hashlib.sha256((report/n.removeprefix('Report/')).read_bytes()).hexdigest()==h
    assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
    assert hashlib.sha256(backup.read_bytes()).hexdigest()==digest
    write(destination/'PRESERVATION.json',{'sourceSHA256':digest,'sourceUnchanged':True,'backupSHA256':digest,'refreshDemandFilesBytePreserved':kept,'pages':['GM Review','Refresh Demand'],'oldReviewMeetingRemoved':True,'desktopOpenVerified':False,'companyModelConnected':False,'publicationPerformed':False})
    setup=(HERE/'SETUP REPORTING FEED.py').read_text().replace('__WORKSPACE__',connections['OriginalWorkspaceObjectId']).replace('__LAKEHOUSE__','d6e33ebd-67b1-420a-8d84-c3a0d04d8b21')
    (destination/'SETUP REPORTING FEED.py').write_text(setup)
    shutil.copy2(HERE/'OPEN FIRST.txt',destination/'OPEN FIRST.txt')
    return project

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();print(create(a.source,a.destination))
