"""Validate a PRIVATE generated project, schemas, rollback and rule idempotence."""
from pathlib import Path
import argparse,hashlib,json,runpy,urllib.request,urllib.error
from zipfile import ZipFile
import jsonschema
HERE=Path(__file__).resolve().parent

def verify(source,destination):
    receipt=json.loads((destination/'PRESERVATION.json').read_text())
    assert hashlib.sha256(source.read_bytes()).hexdigest()==receipt['sourceSHA256']
    assert hashlib.sha256((destination/'Original - before GM redesign.pbix').read_bytes()).hexdigest()==receipt['sourceSHA256']
    report=destination/'ForecastMaster GM Review/ForecastMaster GM Review.Report'
    cache={};checked=0;unavailable=[]
    for p in sorted(report.rglob('*.json')):
        if '/CustomVisuals/' in str(p) or '/StaticResources/' in str(p):continue
        obj=json.loads(p.read_text());url=obj.get('$schema')
        if not url:continue
        if url not in cache:
            try:
                with urllib.request.urlopen(url,timeout=30) as r:cache[url]=json.load(r)
            except urllib.error.HTTPError as error:
                if error.code!=404:raise
                cache[url]=None
        if cache[url] is None:
            unavailable.append({'file':str(p.relative_to(report)),'schema':url,'status':'HTTP 404 - preserved source schema version'});continue
        jsonschema.validators.validator_for(cache[url])(cache[url]).validate(obj);checked+=1
    for p in list(report.glob('definition.pbir'))+list(report.parent.glob('*.pbip')):
        obj=json.loads(p.read_text());url=obj['$schema']
        with urllib.request.urlopen(url,timeout=30) as r:schema=json.load(r)
        jsonschema.validators.validator_for(schema)(schema).validate(obj);checked+=1
    with ZipFile(source) as z:
        for n in receipt['refreshDemandFilesBytePreserved']:
            assert z.read(n)==(report/n.removeprefix('Report/')).read_bytes()
        sourceConnection=json.loads(z.read('Connections'))['Connections'][0]['PbiModelDatabaseName']
    assert sourceConnection in json.loads((report/'definition.pbir').read_text())['datasetReference']['byConnection']['connectionString']
    assert not (report/'definition/pages/reviewmeeting').exists()
    pages=json.loads((report/'definition/pages/pages.json').read_text())
    assert pages['pageOrder']==['demandreview','sopreview','refreshdemand']
    for key in ['demandreview','sopreview']:
        page=json.loads((report/f'definition/pages/{key}/page.json').read_text())
        visual=json.loads((report/f'definition/pages/{key}/visuals/{key}workspace/visual.json').read_text())
        assert (page['width'],page['height'],page['displayOption'])==(1440,810,'FitToPage')
        assert (visual['position']['width'],visual['position']['height'])==(1440,810)
    setup=runpy.run_path(str(HERE/'SETUP REPORTING FEED.py'),run_name='test_setup')
    candidate,count=setup['prepare_rules'](None);again,n=setup['prepare_rules'](candidate)
    assert count==19 and n==19 and again==candidate
    bad=candidate.replace('PI Selling units','INVENTED PI')
    try:setup['prepare_rules'](bad)
    except ValueError:pass
    else:raise AssertionError('Conflicting existing rule must be refused')
    result={'schemaFilesValidated':checked,'schemaUnavailable':unavailable,'sourceAndRollbackVerified':True,'refreshDemandBytePreserved':True,'existingSemanticModelConnectionPreserved':True,'newPageGeometry':'1440 x 810, FitToPage, matching visual viewport','newRules':12,'totalRules':count,'setupIdempotent':True,'conflictingSetupRefused':True,'desktopNativeRender':'PENDING','liveCompanyNumbers':'PENDING','publication':'NOT PERFORMED'}
    (HERE/'VALIDATION-PROJECT.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);a=p.parse_args();verify(a.source,a.destination)
