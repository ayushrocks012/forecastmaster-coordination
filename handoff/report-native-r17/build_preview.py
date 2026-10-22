"""Create an offline native PBIP with fabricated values and no company connection."""
from pathlib import Path
import json
import shutil
import sys
from prepare_project import write,literal
sys.path.insert(0,str(Path(__file__).resolve().parent/'tests'))
from native_fixture import fixture


def preview(candidate,destination):
    if destination.exists():raise ValueError('Use a new synthetic preview folder.')
    source=next((candidate/'ForecastMaster Native Review').glob('*.Report'))
    report=destination/'ForecastMaster Native Preview.Report'
    shutil.copytree(source,report)
    definitions=report/'definition';pages=definitions/'pages'
    for page in ('advancedreview','refreshdemand'):
        # These are task-created copies, never the source report. The synthetic
        # preview must not retain a real company refresh action or connection.
        shutil.rmtree(pages/page)
    for path in list(definitions.glob('reportExtensions.json')):path.unlink()
    for name in ('advancedreview','refreshdemand'):
        assert not (pages/name).exists()
    write(pages/'pages.json',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json',
          'pageOrder':['native_demand','native_sop','native_export'],'activePageName':'native_demand'})
    for path in pages.rglob('visual.json'):
        j=json.loads(path.read_text())
        if j['name']=='nav_advanced':path.unlink();path.parent.rmdir();continue
        if j['name']=='heading':j['visual']['visualContainerObjects']['title'][0]['properties']['text']=literal('SYNTHETIC SAMPLE DATA · Native review')
        if j.get('visual',{}).get('visualType')=='ForecastMasterNativeControlsR17':
            j['visual']['objects']['general'][0]['properties']['currencies']=literal('GBP,EUR')
        write(path,j)
    config=json.loads((definitions/'report.json').read_text())
    config['resourcePackages']=[p for p in config['resourcePackages'] if p['type']!='CustomVisual' or p['name']=='ForecastMasterNativeControlsR17']
    write(definitions/'report.json',config)
    for path in list((report/'CustomVisuals').iterdir()):
        if path.name!='ForecastMasterNativeControlsR17':shutil.rmtree(path)
    platform=report/'.platform'
    if platform.exists():platform.unlink()
    write(report/'definition.pbir',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json',
       'version':'4.0','datasetReference':{'byPath':{'path':'../ForecastMaster Native Preview.SemanticModel'}}})
    model=destination/'ForecastMaster Native Preview.SemanticModel';model.mkdir()
    write(model/'definition.pbism',{'version':'4.0','settings':{}})
    db,_=fixture();db['name']=db['id']='ForecastMasterNativePreviewSynthetic'
    write(model/'model.bim',db)
    write(destination/'ForecastMaster Native Preview - SYNTHETIC.pbip',{'version':'1.0','artifacts':[{'report':{'path':report.name}}],'settings':{'enableAutoRecovery':True}})
    (destination/'READ ME - SAMPLE DATA ONLY.txt').write_text('Offline native Power BI preview. Every figure and source identity is fabricated.\nNo company connection, refresh action or publication is included.\nDesktop rendering still requires receiving confirmation; native-engine arithmetic checks are separate.\nDo not publish this preview as the company report.\n')
    assert all(p['source']['type']=='calculated' for t in db['model']['tables'] for p in t.get('partitions',[]))
    return destination


if __name__=='__main__':print(preview(Path(sys.argv[1]),Path(sys.argv[2])))
