"""Create a private native-first PBIP beside the untouched R16.6 project."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import shutil
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
SCHEMA='https://developer.microsoft.com/json-schemas/fabric/item/report/definition/'
GUID='ForecastMasterNativeControlsR17'


def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')


def literal(value):
    if isinstance(value,bool):v=str(value).lower()
    elif isinstance(value,(int,float)):v=str(value)
    else:v="'"+str(value).replace("'","''")+"'"
    return {'expr':{'Literal':{'Value':v}}}


def field(table,column,measure=False):
    return {'Measure' if measure else 'Column':{'Expression':{'SourceRef':{'Entity':table}},'Property':column}}


def projection(table,column,measure=False,label=None):
    result={'field':field(table,column,measure),'queryRef':table+'.'+column,'nativeQueryRef':label or column}
    if label is not None:result['displayName']=label
    if not measure:result['active']=True
    return result


def visual(name,kind,x,y,w,h,title='',roles=None):
    v={'$schema':SCHEMA+'visualContainer/2.7.0/schema.json','name':name,
       'position':{'x':x,'y':y,'z':0,'width':w,'height':h,'tabOrder':0},
       'visual':{'visualType':kind,'query':{'queryState':roles or {}},
                 'visualContainerObjects':{'title':[{'properties':{'show':literal(bool(title)),'text':literal(title),'fontSize':literal(12)}}],
                   'background':[{'properties':{'show':literal(True),'color':{'solid':{'color':literal('#FFFFFF')}},'transparency':literal(0)}}],
                   'visualHeader':[{'properties':{'show':literal(True),'showFocusModeButton':literal(True),'showPersonalizeVisualButton':literal(True)}}]}}}
    return v


def category_filter(table,column,values):
    return {'Version':2,'From':[{'Name':'x','Entity':table,'Type':0}],
            'Where':[{'Condition':{'In':{'Expressions':[{'Column':{'Expression':{'SourceRef':{'Source':'x'}},'Property':column}}],
              'Values':[[{'Literal':{'Value':"'"+str(v).replace("'","''")+"'"}}] for v in values]}}}]}


def slicer(name,table,column,x,y,w,title,default=None,sync=True,mode='Dropdown',single=False):
    v=visual(name,'slicer',x,y,w,67,title,{'Values':{'projections':[projection(table,column)]}})
    v['visual']['objects']={'data':[{'properties':{'mode':literal(mode)}}],
      'selection':[{'properties':{'singleSelect':literal(single),'selectAllCheckboxEnabled':literal(not single),'strictSingleSelect':literal(single)}}],
      'header':[{'properties':{'show':literal(False)}}],
      'general':[{'properties':{'selfFilterEnabled':literal(True)}}]}
    if default is not None:
        v['visual']['objects']['general'][0]['properties']['filter']={'filter':category_filter(table,column,default if isinstance(default,list) else [default])}
    if sync:v['visual']['syncGroup']={'groupName':'Native '+table+'.'+column,'fieldChanges':False,'filterChanges':True}
    return v


def measure_filter(v,name,comparison=1):
    f=field('fm_native_measures',name,True)
    v.setdefault('filterConfig',{'filters':[]})['filters'].append({'name':v['name']+'_'+name.replace(' ','_'),'field':f,'type':'Advanced',
      'filter':{'Version':2,'From':[{'Name':'m','Entity':'fm_native_measures','Type':0}],
                'Where':[{'Condition':{'Comparison':{'ComparisonKind':0,'Left':{'Measure':{'Expression':{'SourceRef':{'Source':'m'}},'Property':name}},'Right':{'Literal':{'Value':str(comparison)+'L'}}}}}]}})


def local_filter(v,table,column,value):
    v.setdefault('filterConfig',{'filters':[]})['filters'].append({'name':v['name']+'_'+column,'field':field(table,column),'type':'Categorical','filter':category_filter(table,column,[value])})


def matrix(name,x,y,w,h,rows,values,periods=True,title=''):
    roles={'Rows':{'projections':[projection('fm_review_files','DemandCycle'),projection('fm_native_scenario','Scenario')]+[projection(t,c) for t,c in rows]},
           'Values':{'projections':[projection('fm_native_measures',n,True,label) for n,label in values]}}
    if periods:roles['Columns']={'projections':[projection('fm_review_periods','Label')]}
    v=visual(name,'pivotTable',x,y,w,h,title,roles)
    measure_filter(v,'N Scenario Visible')
    v['visual']['objects']={'grid':[{'properties':{'rowPadding':literal(5),'gridVertical':literal(False),'gridHorizontal':literal(True)}}],
      'rowHeaders':[{'properties':{'stepped':literal(False),'fontSize':literal(11)}}],
      'columnHeaders':[{'properties':{'fontSize':literal(11),'backColor':{'solid':{'color':literal('#EAF3F6')}}}}],
      'values':[{'properties':{'fontSize':literal(11)}}],
      'subTotals':[{'properties':{'rowSubtotals':literal(True),'columnSubtotals':literal(False)}}]}
    return v


def button(name,title,x,y,w,action,target):
    v=visual(name,'actionButton',x,y,w,32)
    v['visual'].pop('query',None)
    v['visual']['objects']={'text':[{'properties':{'text':literal(title),'fontSize':literal(11)}}],
      'visualLink':[{'properties':{'show':literal(True),'type':literal(action),
          'navigationSection' if action=='PageNavigation' else 'bookmark':literal(target)}}]}
    return v


def chart(name,chart_type,x,y,w,h):
    roles={'Category':{'projections':[projection('fm_review_axis','Month')],'showAll':True},
      'Series':{'projections':[projection('fm_native_lines','LineLabel')]},
      'Y':{'projections':[projection('fm_native_measures','N Chart Amount',True,'Amount')]}}
    if chart_type=='sop':roles['Y2']={'projections':[projection('fm_native_measures','N Chart Share',True,'Share %')]}
    v=visual(name,'lineChart',x,y,w,h,'Demand trend' if chart_type=='demand' else 'Selected measures',roles)
    v['visual']['objects']={'categoryAxis':[{'properties':{'axisType':literal('Categorical'),'showAxisTitle':literal(False)}}],
      'valueAxis':[{'properties':{'showAxisTitle':literal(True),'secShow':literal(chart_type=='sop'),'secPosition':literal('Right')}}],
      'legend':[{'properties':{'show':literal(True),'position':literal('Bottom'),'fontSize':literal(10)}}],
      'lineStyles':[{'properties':{'strokeWidth':literal(2),'showMarker':literal(False)}}],
      'zoomSlider':[{'properties':{'show':literal(True)}}]}
    v['visual']['query']['sortDefinition']={'sort':[{'field':field('fm_review_axis','Month'),'direction':'Ascending'}],'isDefaultSort':True}
    local_filter(v,'fm_native_lines','Chart',chart_type)
    return v


def make_page(key,title,sop=False):
    page={'$schema':SCHEMA+'page/2.1.0/schema.json','name':key,'displayName':title,
          'displayOption':'FitToWidth','height':1220,'width':1600}
    vs=[]
    vs.append(button('nav_demand','Demand review',20,12,150,'PageNavigation','native_demand'))
    vs.append(button('nav_sop','Explore in S&OP',178,12,150,'PageNavigation','native_sop'))
    vs.append(button('nav_advanced','Advanced workspace',1315,12,180,'PageNavigation','advancedreview'))
    vs.append(button('nav_export','Export data',1140,12,160,'PageNavigation','native_export'))
    heading=visual('heading','textbox',350,10,770,36,'ForecastMaster · '+title)
    heading['visual'].pop('query',None)
    heading['visual']['visualContainerObjects']['title'][0]['properties']['fontSize']=literal(18)
    vs.append(heading)
    # Identical top geometry and sync groups on both native pages.
    vs.extend([slicer('affiliate','fm_review_files','Country',20,55,240,'Affiliate'),
               slicer('cycle','fm_review_files','DemandCycle',275,55,240,'Demand cycle'),
               slicer('display','fm_native_display','Display',1300,55,280,'Display','Units',True,single=True),
               slicer('review_months','fm_review_months','Month',530,55,500,'Review months',mode='Between'),
               slicer('currency','fm_native_currency','Currency',1045,55,240,'Currency','USD',True,single=True)])
    if not sop:
        vs.extend([slicer('section','fm_native_metric','Section',20,132,200,'Section','IMS / Market',True),
                   slicer('metric','fm_native_metric','MetricLabel',235,132,240,'Measure','Market',True,single=True)])
    drivers=slicer('drivers','fm_native_scope','GrowthDriver',490,132,715,'Growth drivers & forecast tiers')
    drivers['visual']['query']['queryState']['Values']['projections'].append(projection('fm_native_scope','Sector'))
    measure_filter(drivers,'N Scope Available');vs.append(drivers)
    periods=slicer('periods','fm_review_periods','Label',1220,132,360,'Review summary periods');measure_filter(periods,'N Period Available');vs.append(periods)
    ctrl=visual('native_controls',GUID,20,210,430,900,'',{
        n:{'projections':[projection('fm_native_catalog',n)]} for n in ('RowID','Channel','SubChannel','Measure','Display','ChannelRank','SubRank','MeasureRank')})
    ctrl['visual']['syncGroup']={'groupName':'Native review preferences','fieldChanges':False,'filterChanges':True}
    ctrl['visual']['objects']={'general':[{'properties':{'currencies':literal('GBP'),'variant':literal('sop' if sop else 'fx'),
       'filter':{'filter':category_filter('fm_native_state','Token',['none'])}}}]}
    measure_filter(ctrl,'N Catalog Visible')
    measure_filter(ctrl,'N Catalog Available')
    # One compact control stays available for shared FX; SOP additionally uses its selector.
    if not sop:ctrl['position'].update(x=20,y=210,width=320,height=180)
    vs.append(ctrl)
    if not sop:
        vs.append(slicer('chart_trend','fm_native_chart_trend','Label',355,210,300,'Chart / headline trend','12M',False,single=True))
        vs.append(slicer('trend','fm_native_trend','Label',670,210,290,'Trend comparisons',['12M'],False))
        vs.append(slicer('view','fm_native_view','View',975,210,290,'Chart view','Total',False,single=True))
        vs.append(slicer('file_mode','fm_native_file_mode','Mode',1280,210,300,'Plan source','Automatic ADS',True,single=True))
        headline=matrix('headline',355,287,1225,103,[],[('N Plan','Plan'),('N Headline Variance','Overcall / Undercall'),('N Headline Variance %','%')],title='Review summary')
        vs.append(headline);vs.append(chart('native_chart','demand',20,405,1560,300))
        # Native row alternatives via display-only bookmarks, no slicer reset.
        row_views={'drivers':[('fm_native_scope','GrowthDriver')],
                   'sectors':[('fm_native_scope','SectorLabel')],
                   'both':[('fm_native_scope','GrowthDriver'),('fm_native_scope','Sector')]}
        for ix,(mode,rows) in enumerate(row_views.items()):
            t=matrix('summary_'+mode,20,760,1560,300,rows,[('N Summary Cell','Value')],title='Executive summary')
            t['visual']['query']['queryState']['Columns']['projections'].extend([projection('fm_native_columns','Comparison'),projection('fm_native_columns','ValueLabel')])
            if mode!='drivers':t['isHidden']=True
            vs.append(t)
            vs.append(button('rows_'+mode,mode.title(),20+ix*115,717,110,'Bookmark','table_'+mode))
        vs.append(slicer('matching_files','fm_review_files','FileLabel',20,1080,1560,'Matching files · optional override',sync=True))
    else:
        vs.append(slicer('view','fm_native_view','View',465,210,300,'Chart view','Total',False,single=True))
        vs.append(slicer('runrate','fm_native_run_rate','Show',780,210,250,'Monthly run rate','Off',False,single=True))
        vs.append(slicer('growth','fm_native_growth','Show',1045,210,250,'Growth vs PY','Off',False,single=True))
        vs.append(slicer('file_mode','fm_native_file_mode','Mode',1310,210,270,'Plan source','Automatic ADS',True,single=True))
        vs.append(chart('native_chart','sop',465,287,1115,315))
        rows=[('fm_native_rows',n) for n in ('Channel','SubChannel','Measure')]
        summary=matrix('sop_summary',465,660,1115,450,rows,[('N SOP Plan','Plan'),('N SOP Run Rate','Monthly run rate'),('N SOP Growth %','Growth vs PY')],title='S&OP summary')
        vs.append(summary)
        monthly=matrix('sop_monthly',465,660,1115,450,rows,[('N SOP Monthly','Amount'),('N SOP Monthly Growth %','Growth vs PY')],False,'S&OP monthly')
        month=projection('fm_review_axis','Month');month['format']='MMM yyyy'
        monthly['visual']['query']['queryState']['Columns']={'projections':[month]};monthly['isHidden']=True;vs.append(monthly)
        vs.extend([button('period_mode','Periods',465,615,120,'Bookmark','sop_periods'),button('monthly_mode','Monthly',595,615,120,'Bookmark','sop_monthly')])
        vs.append(slicer('matching_files','fm_review_files','FileLabel',465,1130,1115,'Matching files · optional override',sync=True))
    # Native query/render count is intentionally bounded; line/matrix detail is
    # lazy, unlike the old all-rows HTML viewport. Export is enabled report-wide.
    # Native display bookmarks keep all slicer/selection data intact. Native
    # Focus mode is the full-size chart/table alternative to HTML reflow.
    target='native_controls'
    vs.extend([button('selector_hide','Hide selector' if sop else 'Hide rates',20,1120,135,'Bookmark',key+'_selector_hide'),
               button('selector_show','Show selector' if sop else 'Plan rates',20,1120,135,'Bookmark',key+'_selector_show'),
               button('graph_hide','Hide graph',1460,400 if not sop else 280,120,'Bookmark',key+'_graph_hide'),
               button('graph_show','Show graph',1460,400 if not sop else 280,120,'Bookmark',key+'_graph_show')])
    for item in vs:
        if item['name'] in {'selector_show','graph_show'}:item['isHidden']=True
    group={'$schema':SCHEMA+'visualContainer/2.7.0/schema.json','name':'summary_group',
           'position':{'x':0,'y':0,'z':0,'width':1600,'height':1220,'tabOrder':0},
           'visualGroup':{'displayName':'Summary','groupMode':'ScaleMode'}}
    for item in vs:
        if item['name'].startswith('summary_') or item['name'] in {'sop_summary','sop_monthly','period_mode','monthly_mode'}:
            item['parentGroupName']='summary_group'
        if item.get('visual',{}).get('visualType')=='pivotTable' and item['name'].startswith('summary_'):
            item['visual']['objects']['values'][0]['properties']['fontColor']={'solid':{'color':{'expr':field('fm_native_measures','N Variance Color',True)}}}
    vs.append(group)
    vs.extend([button('summary_hide','Hide summary',1460,715 if not sop else 615,120,'Bookmark',key+'_summary_hide'),
               button('summary_show','Show summary',1460,715 if not sop else 615,120,'Bookmark',key+'_summary_show')])
    vs[-1]['isHidden']=True
    for item in vs:
        if item['position']['y']>=210:item['position']['y']+=32
    page['height']+=32
    for control,x,label in [('scope',490,'scope'),('periods',1220,'periods')]:
        vs.append(button(control+'_all','Select all',x,202,105,'Bookmark',key+'_'+control+'_all'))
        vs.append(button(control+'_clear','Clear all',x+115,202,105,'Bookmark',key+'_'+control+'_clear'))
    # Shared source/cutoff row sits in the same place on both native pages.
    for item in vs:
        if item['position']['y']>=132:item['position']['y']+=24
    page['height']+=24
    status=visual('source_status','tableEx',20,124,1560,24,'',{'Values':{'projections':[projection('fm_native_measures','N Source Caption',True,'Saved sources')]}})
    status['visual']['objects']={'columnHeaders':[{'properties':{'show':literal(False)}}],
        'values':[{'properties':{'fontSize':literal(10)}}],'total':[{'properties':{'totals':literal(False)}}]}
    vs.append(status)
    return page,vs


def visibility_bookmark(name,page,visible,hidden):
    return {'$schema':SCHEMA+'bookmark/1.3.0/schema.json','name':name,'displayName':name.replace('_',' ').title(),
       'options':{'applyOnlyToTargetVisuals':True,'targetVisualNames':visible+hidden,'suppressActiveSection':True,'suppressData':True},
       'explorationState':{'version':'1.3','activeSection':page,'sections':{page:{'visualContainers':{
        v:{'singleVisual':({} if v in visible else {'display':{'mode':'hidden'}})} for v in visible+hidden}}}}}


def selection_bookmark(page,key,table,column,clear):
    """Explicit empty choice via native bookmark; eraser remains native Reset.

    The reserved non-member is a filter state, never a fabricated dimension row.
    Receiving UI must verify the empty state and recovery before release.
    """
    target='drivers' if key=='scope' else 'periods'
    if clear:
        objects={'merge':{'general':[{'properties':{'filter':{'filter':category_filter(table,column,['__FM_NO_SELECTION_R17__'])}}}]}}
    else:
        objects={'remove':[{'object':'general','property':'filter','selector':{}}]}
    return {'$schema':SCHEMA+'bookmark/1.3.0/schema.json','name':page+'_'+key+('_clear' if clear else '_all'),
       'displayName':('Clear ' if clear else 'Select all ')+key,
       'options':{'applyOnlyToTargetVisuals':True,'targetVisualNames':[target],'suppressActiveSection':True,'suppressData':False,'suppressDisplay':True},
       'explorationState':{'version':'1.3','activeSection':page,'sections':{page:{'visualContainers':{target:{'singleVisual':{'objects':objects}}}}}}}


def create(source:Path,destination:Path,affiliate=None,cycle=None):
    if destination.exists():raise ValueError('Use a NEW destination. Existing versions remain intact.')
    reports=list(source.glob('*.Report'))
    if len(reports)!=1:raise ValueError('Supply the R16.6 project folder containing one .Report folder.')
    old=reports[0];report=destination/'ForecastMaster Native Review'/'ForecastMaster Native Review.Report'
    before={p.relative_to(source).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in source.rglob('*') if p.is_file()}
    shutil.copytree(old,report)
    definition=report/'definition';pages=definition/'pages'
    advanced=pages/'demandreview';advanced.rename(pages/'advancedreview')
    j=json.loads((pages/'advancedreview/page.json').read_text());j.update(name='advancedreview',displayName='Advanced workspace · R16.6',visibility='HiddenInViewMode');write(pages/'advancedreview/page.json',j)
    bookmarks=[]
    native_visuals={}
    for key,title,sop in [('native_demand','Demand review',False),('native_sop','S&OP review',True)]:
        page,vs=make_page(key,title,sop);write(pages/key/'page.json',page)
        defaults={}
        if affiliate:defaults['affiliate']=('fm_review_files','Country',affiliate)
        if cycle:
            defaults['cycle']=('fm_review_files','DemandCycle',cycle)
            defaults['periods']=('fm_review_periods','Label',cycle[:4]+' FY')
        for v in vs:
            if v['name'] in defaults:
                table,column,value=defaults[v['name']]
                v['visual']['objects']['general'][0]['properties']['filter']={'filter':category_filter(table,column,[value])}
        native_visuals[key]=vs
        for i,v in enumerate(vs):
            v['position']['z']=i;v['position']['tabOrder']=i
            write(pages/key/'visuals'/v['name']/'visual.json',v)
    for mode in ('drivers','sectors','both'):
        bookmarks.append(visibility_bookmark('table_'+mode,'native_demand',['summary_'+mode],['summary_'+m for m in ('drivers','sectors','both') if m!=mode]))
    bookmarks.extend([visibility_bookmark('sop_periods','native_sop',['sop_summary'],['sop_monthly']),visibility_bookmark('sop_monthly','native_sop',['sop_monthly'],['sop_summary'])])
    for key in native_visuals:
        for choice,table,column in [('scope','fm_native_scope','GrowthDriver'),('periods','fm_review_periods','Label')]:
            for clear in (True,False):bookmarks.append(selection_bookmark(key,choice,table,column,clear))
        for group,target in [('selector','native_controls'),('graph','native_chart')]:
            bookmarks.append(visibility_bookmark(key+'_'+group+'_hide',key,[group+'_show'],[target,group+'_hide']))
            bookmarks.append(visibility_bookmark(key+'_'+group+'_show',key,[target,group+'_hide'],[group+'_show']))
        for hidden in (True,False):
            bookmark=visibility_bookmark(key+'_summary_'+('hide' if hidden else 'show'),key,
              ['summary_show' if hidden else 'summary_hide'],['summary_hide' if hidden else 'summary_show'])
            bookmark['options']['targetVisualNames'].append('summary_group')
            bookmark['explorationState']['sections'][key]['visualContainerGroups']={'summary_group':{'isHidden':hidden}}
            bookmarks.append(bookmark)
    # Clean-label native detail exports. Presentation ordering uses hidden rank
    # suffixes in the matrix/legend labels; these tables export raw identities.
    export_page={'$schema':SCHEMA+'page/2.1.0/schema.json','name':'native_export','displayName':'Export data',
                 'displayOption':'FitToWidth','height':1450,'width':1600,'visibility':'HiddenInViewMode'}
    write(pages/'native_export/page.json',export_page)
    exports=[button('back_demand','Demand review',20,12,150,'PageNavigation','native_demand'),button('back_sop','S&OP review',180,12,150,'PageNavigation','native_sop')]
    seen_groups=set()
    for original in native_visuals['native_sop']+native_visuals['native_demand']:
        if original.get('visual',{}).get('syncGroup'):
            group=original['visual']['syncGroup']['groupName']
            if group in seen_groups:continue
            seen_groups.add(group)
            hidden=json.loads(json.dumps(original));hidden['isHidden']=True;exports.append(hidden)
    data_fields=[('fm_review_files','Country'),('fm_review_files','DemandCycle'),('fm_native_scenario','Scenario'),('fm_native_scope','GrowthDriver'),
                 ('fm_native_scope','Sector'),('fm_review_periods','Label')]
    for ident,y,title,extra,values in [('demand_export',60,'Demand data · clean identities',[],[('N Plan','Plan'),('N Variance','Variance'),('N Variance %','Variance %')]),
        ('sop_export',520,'S&OP data · clean identities',[('fm_native_catalog','Channel'),('fm_native_catalog','SubChannel'),('fm_native_catalog','Measure')],
         [('N Export Order','Order'),('N Export Plan','Plan'),('N Export Run Rate','Monthly run rate'),('N Export Growth %','Growth vs PY')])]:
        roles={'Values':{'projections':[projection(t,c) for t,c in data_fields+extra]+[projection('fm_native_measures',m,True,label) for m,label in values]}}
        t=visual(ident,'tableEx',20,y,1560,420,title,roles);measure_filter(t,'N Scenario Visible');exports.append(t)
    monthly_fields=[(t,c) for t,c in data_fields if t!='fm_review_periods']+[('fm_review_axis','Month')]+[("fm_native_catalog",c) for c in ('Channel','SubChannel','Measure')]
    monthly=visual('monthly_export','tableEx',20,980,1560,420,'Monthly data · clean identities',{'Values':{'projections':
      [projection(t,c) for t,c in monthly_fields]+[projection('fm_native_measures','N Export Month Stage',True,'Stage'),projection('fm_native_measures','N Export Monthly',True,'Amount')]}})
    measure_filter(monthly,'N Scenario Visible');exports.append(monthly)
    for i,v in enumerate(exports):v['position']['z']=i;v['position']['tabOrder']=i;write(pages/'native_export/visuals'/v['name']/'visual.json',v)
    for b in bookmarks:write(definition/'bookmarks'/(b['name']+'.bookmark.json'),b)
    write(definition/'bookmarks/bookmarks.json',{'$schema':SCHEMA+'bookmarksMetadata/1.0.0/schema.json','items':[{'name':b['name']} for b in bookmarks]})
    write(pages/'pages.json',{'$schema':SCHEMA+'pagesMetadata/1.0.0/schema.json','pageOrder':['native_demand','native_sop','native_export','advancedreview','refreshdemand'],'activePageName':'native_demand'})
    config=json.loads((definition/'report.json').read_text());config.setdefault('settings',{}).update(exportDataMode='AllowSummarizedAndUnderlying',useEnhancedTooltips=True,allowChangeFilterTypes=True)
    package=next((HERE/'Controls/dist').glob('*.pbiviz'))
    with ZipFile(package) as z:
        for item in z.namelist():
            if item.endswith('/'):continue
            p=report/'CustomVisuals'/GUID/item;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(item))
    config['resourcePackages'].append({'name':GUID,'type':'CustomVisual','items':[{'name':f'resources/{GUID}.pbiviz.json','path':f'{GUID}.pbiviz.json','type':'CustomVisualMetadata'}]})
    write(definition/'report.json',config)
    write(report.parent/'ForecastMaster Native Review.pbip',{'$schema':'https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json','version':'1.0','artifacts':[{'report':{'path':report.name}}],'settings':{'enableAutoRecovery':True}})
    assert all(hashlib.sha256((source/n).read_bytes()).hexdigest()==h for n,h in before.items())
    refresh={p.relative_to(old).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (old/'definition/pages/refreshdemand').rglob('*') if p.is_file()}
    assert all(hashlib.sha256((report/n).read_bytes()).hexdigest()==h for n,h in refresh.items())
    write(destination/'PRESERVATION.json',{'SourceUnchanged':True,'SourceFiles':before,'NativeRefreshDemand':refresh,
      'ConnectionPreserved':(old/'definition.pbir').read_bytes()==(report/'definition.pbir').read_bytes(),
      'R16_6RuntimePreserved':True,'LiveInstallation':False,'DesktopOpen':False,'Release':'CANDIDATE - NOT READY TO REPLACE PRODUCTION'})
    return report.parent


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('destination',type=Path);p.add_argument('--affiliate');p.add_argument('--cycle');a=p.parse_args();print(create(a.source,a.destination,a.affiliate,a.cycle))
