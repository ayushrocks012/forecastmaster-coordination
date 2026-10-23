"""Compact R17.8 R01 built-in report; requires matching TEST adapter.

No Fabric API in this builder. Production binding is never used.
"""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
from tempfile import TemporaryDirectory
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
OLD=load('r178_old_report',HERE.parents[1]/'report-native-only-r17.7/prepare_project.py')
MODEL=load('r178_model',HERE/'model.py')
BASE=OLD.BASE
lit,projection,write=OLD.lit,OLD.projection,OLD.write
NAME='ForecastMaster Compact Native R17.8 TEST'
SAMPLE_NAME='ForecastMaster Compact Native R17.8 SAMPLE'
SOURCE_SHA256='5ab837ba37bebf6f00dfb343cd7031959bc0f66bb989631ca65daa169daabfbf'


def padding(v,n=0):
    v['visual']['visualContainerObjects']['padding']=[{'properties':{k:lit(n) for k in ('top','bottom','left','right')}}]
    return v


def compact_picker(v,x,y,w):
    v['position'].update(x=x,y=y,width=w,height=44)
    v['visual']['objects']['header'][0]['properties']['show']=lit(False)
    padding(v,2)
    return v


def make_page():
    page,before=OLD.make_page()
    removed={'source_mode','apply_top','apply_files','apply_note','chart_key','matching_files','chart_title','file_picker'}
    vs={v['name']:deepcopy(v) for v in before if v['name'] not in removed}
    layout={
      'heading':(20,8,948,32),'source_status':(20,46,948,28),
      'start_month':(980,8,210,64),'end_month':(1202,8,218,64),
      'affiliate':(20,86,160,64),'cycle':(192,86,176,64),'section':(380,86,240,64),
      'metric':(632,86,472,64),'display':(1116,86,304,64),
      'drivers':(20,158,340,64),'tiers':(372,158,450,64),'periods':(834,158,586,64),
      'headline_title':(20,234,1000,24),'headline':(20,280,1400,108),
      'native_chart':(20,448,1400,284),
      'executive_title':(20,748,900,24),'executive_summary':(20,794,1400,288),
      'files_heading':(20,1098,1400,24)}
    for name,rect in layout.items():vs[name]['position'].update(zip(('x','y','width','height'),rect))
    for v in vs.values():
        if v['visual']['visualType']=='textbox':padding(v,0)
        elif v['visual']['visualType']=='slicer':padding(v,2)
    vs['heading']['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value']='ForecastMaster · Demand review · R17.8 TEST'
    for name,label,x,y,w,lx,lw in (
        ('chart_trend','Review trend',1200,228,220,1086,106),
        ('view','View',1200,396,220,1138,54),
        ('trend','Table trends',1200,742,220,1078,114)):
        compact_picker(vs[name],x,y,w)
        vs[name+'_label']=padding(BASE.text(name+'_label',label,lx,y+8,lw,20,10,False),0)
    # The measure/currency title occupies the existing heading band, not plot
    # area. Keep source-provided numeric formatting and native line styles.
    title=deepcopy(vs['source_status']);title['name']='dynamic_chart_title'
    title['position'].update(x=20,y=398,width=1090,height=28)
    p=projection('fm_native_measures','N Measure Caption',True,'Monthly demand')
    title['visual']['query']['queryState']['Data']['projections']=[p]
    vs['dynamic_chart_title']=title
    for name in ('source_status','dynamic_chart_title'):
        card=vs[name]['visual']
        card['objects']['padding'][0]['properties']['paddingUniform']=lit(0)
        padding(vs[name],0)
        card['visualContainerObjects']['border'][0]['properties']['show']=lit(False)
    chart=vs['native_chart']['visual']
    chart['visualContainerObjects']['title'][0]['properties']['show']=lit(False)
    chart['visualContainerObjects']['subTitle'][0]['properties']['show']=lit(False)
    chart['objects']['zoom']=[{'properties':{'show':lit(False),'showOnValueAxis':lit(False)}}]
    chart['objects']['legend'][0]['properties'].update(position=lit('Right'),fontSize=lit(9))
    padding(vs['native_chart'],4)
    # The headline returns Plan/variance rows directly. Source alternatives
    # remain separated in Executive Summary; no cross-version sum is invented.
    headline=vs['headline']['visual']
    headline['query']['queryState']['Rows']['projections']=[p for p in headline['query']['queryState']['Rows']['projections']
                                                          if p['queryRef']!='fm_native_scenario.Scenario']
    headline['expansionStates']=[s for s in headline.get('expansionStates',[]) if s['roles']!=['Rows']]
    picker=BASE.slicer('file_picker','fm_native_files','FileChoiceLabel',20,1134,1400,'',single=False,mode='Basic')
    picker['position']['height']=184
    picker['visual']['objects']['header'][0]['properties']['show']=lit(False)
    picker['visual']['objects']['searchBox']=[{'properties':{'show':lit(True)}}]
    picker['visual']['objects']['selection'][0]['properties'].update(singleSelect=lit(False),strictSingleSelect=lit(False))
    picker['visual']['objects']['items'][0]['properties'].update(textSize=lit(10))
    padding(picker,4)
    BASE.PP.measure_filter(picker,'N File Available')
    picker['visual']['query']['sortDefinition']={'sort':[{'field':BASE.PP.field('fm_native_files','FileChoiceLabel'),
                                                       'direction':'Descending'}],'isDefaultSort':True}
    vs['file_picker']=picker
    vs['files_heading']['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value']='Saved files · filename and import time · clear selection for Automatic ADS'
    # File mode is inferred by the R17.8 adapter from an actual file filter.
    # Currency stays fixed at the existing source-currency basis.
    page['filterConfig']['filters']=[f for f in page['filterConfig']['filters']
        if f['field'].get('Column',{}).get('Expression',{}).get('SourceRef',{}).get('Entity') not in {'fm_native_file_mode','fm_native_scenario'}]
    page['height']=1330
    page['visualInteractions']=[{'source':source,'target':name,'type':'NoFilter'}
        for source in ('headline','native_chart','executive_summary') for name in vs if name!=source]
    page['visualInteractions'].append({'source':'metric','target':'section','type':'NoFilter'})
    page['visualInteractions'].extend({'source':source,'target':target,'type':'NoFilter'}
        for source,targets in (('chart_trend',('executive_summary',)),('trend',('headline','native_chart')),
                               ('file_picker',('affiliate','cycle','section','metric','drivers','tiers','periods','start_month','end_month')))
        for target in targets)
    for i,v in enumerate(vs.values()):v['position'].update(z=i,tabOrder=i)
    return page,list(vs.values())


def create(source_zip,destination):
    if destination.exists():raise ValueError('Use a new destination')
    if hashlib.sha256(source_zip.read_bytes()).hexdigest()!=SOURCE_SHA256:raise ValueError('Require frozen R17.7 TEST ZIP')
    with TemporaryDirectory() as temp:
        with ZipFile(source_zip) as z:z.extractall(temp)
        source=next(Path(temp).glob('*.Report'));report=destination/(NAME+'.Report')
        shutil.copytree(source,report);definition=report/'definition';shutil.rmtree(definition/'pages')
        page,visuals=make_page()
        write(definition/'pages/native_demand/page.json',page)
        write(definition/'pages/pages.json',{'$schema':BASE.PP.SCHEMA+'pagesMetadata/1.0.0/schema.json',
                                            'pageOrder':['native_demand'],'activePageName':'native_demand'})
        for v in visuals:write(definition/'pages/native_demand/visuals'/v['name']/'visual.json',v)
        write(destination/(NAME+'.pbip'),{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json',
            'version':'1.0','artifacts':[{'report':{'path':report.name}}],'settings':{'enableAutoRecovery':True}})
        assert (source/'definition.pbir').read_bytes()==(report/'definition.pbir').read_bytes()
    write(destination/'OPEN FIRST.txt','TEST ONLY: first install the matching R17.8 R01 adapter and complete its single TEST refresh. Then open this PBIP. See the release OPEN FIRST instructions.\n')
    write(destination/'PRESERVATION.json',{'Stage':'R178_R01_COMPACT_TEST','CustomVisuals':0,
        'TESTBindingPreserved':True,'RequiresR178Adapter':True,'CompanyDateRecovery':'VERIFIED in preceding R02 receipt; rechecked after adapter processing',
        'CompanyNumericalUIAndSpeedAcceptance':'PENDING'})


def create_sample(test_project,destination):
    if destination.exists():raise ValueError('Use a new destination')
    shutil.copytree(test_project,destination)
    report=destination/(SAMPLE_NAME+'.Report');(destination/(NAME+'.Report')).rename(report)
    semantic=destination/(SAMPLE_NAME+'.SemanticModel')
    with ZipFile(HERE.parents[1]/'report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 SAMPLE.zip') as z:
        for name in z.namelist():
            if '.SemanticModel/' in name:
                rel=name.split('.SemanticModel/',1)[1]
                if rel:
                    target=semantic/rel;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
    db,_=MODEL.patch_database(json.loads((semantic/'model.bim').read_text()));write(semantic/'model.bim',db)
    write(report/'definition.pbir',{'version':'4.0','datasetReference':{'byPath':{'path':'../'+semantic.name}}})
    project=json.loads((destination/(NAME+'.pbip')).read_text());(destination/(NAME+'.pbip')).unlink()
    project['artifacts'][0]['report']['path']=report.name;write(destination/(SAMPLE_NAME+'.pbip'),project)
    path=report/'definition/pages/native_demand/visuals/heading/visual.json';v=json.loads(path.read_text())
    v['visual']['objects']['general'][0]['properties']['paragraphs'][0]['textRuns'][0]['value']='ForecastMaster · R17.8 SAMPLE · FABRICATED DATA'
    write(path,v)
    write(destination/'OPEN FIRST.txt','SAMPLE ONLY: fabricated data. Review native layout; not company numerical or performance evidence.\n')
    write(destination/'PRESERVATION.json',{'Stage':'R178_NATIVE_SAMPLE','FabricatedDataOnly':True,'FabricConnection':False,
         'CustomVisuals':0,'NativeRendering':'NOT_EXECUTED_HERE'})


zip_project=OLD.zip_project
