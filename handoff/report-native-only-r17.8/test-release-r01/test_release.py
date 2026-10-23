"""Receiving failure paths, metadata preservation and native PBIR contracts."""
import ast
import base64
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

p=load('release_report',HERE/'prepare_project.py');m=p.MODEL
c=load('release_cell',HERE/'INSTALL COMPACT TEST R01.py')
builder=load('release_builder',HERE/'build_cell.py')


def database():
    db=m.original_database();tables={t['name']:t for t in db['model']['tables']}
    db['model']['expressions']=[{'name':'KeepSource','expression':'AzureStorage.DataLake("'+c.WORKSPACE+'/'+c.LAKEHOUSE+'")'}]
    for name,columns in c.FIELDS.items():
        tables[name]['partitions']=[{'name':name,'mode':'directLake','source':{'type':'entity','entityName':name,'expressionSource':'KeepSource'}}]
        for col in tables[name]['columns']:col['type']='data';col['sourceColumn']=col['name']
    tables['fm_review_facts']['measures']=[{'name':'Inherited '+str(i),'expression':'0','description':'PRESERVE_PRIVATE_METADATA'} for i in range(47)]
    db['model']['tables'] += [{'name':'base_stub_'+str(i),'columns':[]} for i in range(10)]
    db['model']['relationships'] += [{'name':'base_relationship_'+str(i),'fromTable':'base_stub_0','toTable':'base_stub_1'} for i in range(5)]
    # Company export returns DAX and dynamic formats as line arrays.
    for measure in tables['fm_native_measures']['measures']:
        measure['expression']=measure['expression'].split('\n')
        if 'formatStringDefinition' in measure:measure['formatStringDefinition']['expression']=measure['formatStringDefinition']['expression'].split('\n')
        if measure.get('formatString')=='':measure.pop('formatString')
    return db


class Response:
    def __init__(self,value=None,status=200,headers=None):self.value=value;self.status_code=status;self.headers=headers or {}
    def json(self):return deepcopy(self.value)


class Client:
    def __init__(self,db):self.db=deepcopy(db);self.updates=0;self.mode='ok';self.mapping=[{'id':'SYNTHETIC','connectivityType':'ShareableCloud'}]
    def get(self,path):
        if path.endswith('/refreshes?$top=60'):return Response({'value':[{'status':'Completed','startTime':'2026-10-23T21:00:00Z'}]})
        if path==c.ITEM:return Response({'id':c.TEST,'displayName':c.NAME,'type':'SemanticModel'})
        if path==c.ITEM+'/connections':return Response({'value':self.mapping})
        if path.startswith('/v1/operations/'):
            if self.mode=='cancelled':return Response({'status':'Cancelled'})
            return Response({'status':'Succeeded'})
        raise AssertionError('Unexpected API GET')
    def post(self,path,json=None):
        if path.endswith('/getDefinition?format=TMSL'):
            return Response({'definition':{'parts':[{'path':'model.bim','payloadType':'InlineBase64','payload':base64.b64encode(__import__('json').dumps(self.db).encode()).decode()},
              {'path':'definition.pbism','payload':'SYNTHETIC_UNCHANGED','payloadType':'InlineBase64'}]}})
        if path.endswith('/updateDefinition'):
            self.updates+=1
            if self.mode=='lost':raise ConnectionError('PRIVATE MUST NOT PRINT')
            assert json['options']=={'allowPurgeData':False}
            self.db=__import__('json').loads(base64.b64decode(json['definition']['parts'][0]['payload']))
            if self.mode=='arrays':
                for t in self.db['model']['tables']:
                    for measure in t.get('measures',[]):
                        if isinstance(measure['expression'],str):measure['expression']=measure['expression'].split('\n')
            if self.mode=='drift':self.db['model']['tables'][-1]['description']='UNKNOWN CHANGE'
            if self.mode=='mapping':self.mapping[0]['id']='DRIFT'
            if self.mode in {'async','cancelled'}:return Response(status=202,headers={'x-ms-operation-id':'11111111-1111-4111-8111-111111111111'})
            return Response()
        raise AssertionError('Unexpected API POST')


class FS:
    def __init__(self,root):self.root=root;self.corrupt=False
    def path(self,path):return self.root/str(path).replace('://','/').lstrip('/')
    def exists(self,path):return self.path(path).exists()
    def mkdirs(self,path):self.path(path).mkdir(parents=True,exist_ok=True);return True
    def put(self,path,text,overwrite):
        p=self.path(path);p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('w' if overwrite else 'x') as stream:stream.write(text)
        return True
    def cp(self,source,destination,recurse):
        shutil.copyfile(self.path(source),destination.removeprefix('file://'))
        if self.corrupt:Path(destination.removeprefix('file://')).write_bytes(b'CORRUPTED')
        return True


class Frame:
    def __init__(self,rows):self.rows=rows
    def to_dict(self,orient='records'):return deepcopy(self.rows)


class Tests(unittest.TestCase):
    def setUp(self):self.page,visuals=p.make_page();self.vs={v['name']:v for v in visuals}
    def run_receiving(self,mode='ok',mutate=None,preflight_failure=False,corrupt=False):
        db=database();client=Client(db);client.mode=mode
        if mutate:mutate(client.db)
        with tempfile.TemporaryDirectory() as temp:
            fs=FS(Path(temp));fs.corrupt=corrupt
            dates={kind:[('example','2026-01-01')] for kind in c.KINDS}
            for kind in ('Axis','Review','Start','End','Facts'):dates[kind]=[('','2026-01-01')]
            with patch.object(c,'EXPECTED_TEST_BIM',c.digest(db)),patch.object(c,'semantic_dates',return_value=dates),\
              patch.object(c,'preflight',side_effect=c.CheckStopped('PREFLIGHT_TEST_FAILED') if preflight_failure else None,return_value={'PairedScalarComparisons':12}),\
              patch.object(c.time,'sleep',lambda _:None),redirect_stdout(io.StringIO()) as output:
                result=c.run(client,fs,None,client)
                if mode=='lost':
                    # Same exact baseline but the persistent intent prevents second submission.
                    second=c.run(client,fs,None,client);self.assertFalse(second['ModelWriteRequested'])
                    self.assertEqual('PRIOR_R178_ATTEMPT_REVIEW_REQUIRED',second['Failure']['Reason'])
                self.assertNotIn('PRIVATE MUST NOT PRINT',output.getvalue())
                self.assertNotIn('PRESERVE_PRIVATE_METADATA',output.getvalue())
                marker=fs.exists(c.ATTEMPT)
            return result,client,marker
    def test_live_line_formats_and_all_unrelated_metadata_preserved(self):
        db=database();after,changed=m.patch_database(db)
        for t in db['model']['tables']:
            got=next(v for v in after['model']['tables'] if v['name']==t['name'])
            if t['name'] not in {'fm_native_measures','fm_native_files'}:self.assertEqual(t,got)
        measures=lambda d:{v['name']:v for t in d['model']['tables'] if t['name']=='fm_native_measures' for v in t['measures']}
        before,fixed=measures(db),measures(after)
        for name in ('N Plan','N Benchmark','N Variance','N Variance %','N Fit Mean','N Fit Slope','N Trend Monthly'):
            self.assertEqual(before[name],fixed[name])
        for name in before:
            self.assertEqual(before[name].get('formatStringDefinition'),fixed[name].get('formatStringDefinition'))
        self.assertEqual(52,len(fixed));self.assertEqual(db['model']['relationships'],after['model']['relationships'])
    def test_unknown_expression_format_partition_and_duplicate_inventory_refused(self):
        for mutate in (lambda d:next(t for t in d['model']['tables'] if t['name']=='fm_native_measures')['measures'][0].update(expression='UNKNOWN'),
                       lambda d:next(t for t in d['model']['tables'] if t['name']=='fm_native_measures')['measures'][0].update(formatString='UNKNOWN'),
                       lambda d:next(t for t in d['model']['tables'] if t['name']=='fm_native_files')['partitions'][0]['source'].update(expression='UNKNOWN'),
                       lambda d:d['model']['tables'].append(deepcopy(d['model']['tables'][0]))):
            db=database();mutate(db)
            with self.assertRaises(ValueError):m.patch_database(db)
    def test_success_and_exact_dax_array_readback(self):
        for mode in ('ok','arrays','async'):
            result,client,marker=self.run_receiving(mode)
            self.assertEqual('TEST_R178_UPDATED',result['Stage'],result)
            self.assertEqual(1,client.updates);self.assertTrue(marker)
            self.assertFalse(result['RefreshRequested']);self.assertFalse(result['OriginalModelWriteRequested'])
    def test_unknown_write_outcome_sticky_no_second_post(self):
        result,client,marker=self.run_receiving('lost')
        self.assertEqual('TEST_R178_INSTALL_STOPPED',result['Stage']);self.assertTrue(result['ModelWriteRequested'])
        self.assertEqual(1,client.updates);self.assertTrue(marker)
    def test_readback_mapping_or_cancelled_operation_never_requests_refresh(self):
        for mode in ('drift','mapping','cancelled'):
            result,client,marker=self.run_receiving(mode)
            self.assertEqual('TEST_R178_INSTALL_STOPPED',result['Stage']);self.assertFalse(result.get('RefreshRequiredOnce',False))
            self.assertEqual(1,client.updates);self.assertTrue(marker)
    def test_preflight_failure_corrupt_backup_or_concurrent_definition_blocks_write(self):
        for kwargs in ({'preflight_failure':True},{'corrupt':True},{'mutate':lambda d:d.update(name='UNKNOWN')}):
            result,client,marker=self.run_receiving(**kwargs)
            self.assertFalse(result['ModelWriteRequested']);self.assertEqual(0,client.updates);self.assertFalse(marker)
    def test_scalar_preflight_exactly_24_reads_and_private_zero_is_numeric(self):
        calls=[]
        def evaluate(**kwargs):
            calls.append(kwargs);self.assertFalse(kwargs['use_readwrite_connection'])
            return Frame([{'Country':'UK','Cycle':'2026-10','Driver':'Example'}]) if len(calls)==1 else Frame([{'[V]':0.}])
        with redirect_stdout(io.StringIO()):result=c.preflight(evaluate,c.EDITS)
        self.assertEqual(25,len(calls));self.assertEqual(12,result['PairedScalarComparisons'])
        def bad(**kwargs):return Frame([{'Country':'UK','Cycle':'2026-10','Driver':'Example'}]) if kwargs['dax_string']==c.METADATA_QUERY else Frame([{'[V]':None}])
        with redirect_stdout(io.StringIO()),self.assertRaises(c.CheckStopped):c.preflight(bad,c.EDITS)
    def test_no_geometry_overlap_and_native_visual_inventory(self):
        self.assertEqual(1330,self.page['height']);visuals=list(self.vs.values())
        for i,v in enumerate(visuals):
            self.assertIn(v['visual']['visualType'],{'slicer','lineChart','pivotTable','cardVisual','textbox'})
            projections=[item.get('nativeQueryRef') for role in v['visual'].get('query',{}).get('queryState',{}).values() for item in role.get('projections',[])]
            self.assertEqual(len(projections),len(set(projections)),v['name']+' duplicate native query alias')
            a=v['position'];self.assertGreaterEqual(a['x'],0);self.assertGreaterEqual(a['y'],0)
            self.assertLessEqual(a['x']+a['width'],self.page['width']);self.assertLessEqual(a['y']+a['height'],self.page['height'])
            for other in visuals[i+1:]:
                b=other['position'];self.assertFalse(a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and a['y']<b['y']+b['height'] and b['y']<a['y']+a['height'],(v['name'],other['name']))
        for forbidden in ('apply_top','apply_files','source_mode','matching_files','chart_key','chart_title'):self.assertNotIn(forbidden,self.vs)
    def test_native_months_short_external_labels_dynamic_title_and_no_zoom(self):
        for name in ('start_month','end_month'):
            self.assertIn('MonthLabel',str(self.vs[name]['visual']['query']))
        for name in ('trend','chart_trend','view'):
            v=self.vs[name];self.assertEqual(44,v['position']['height'])
            self.assertEqual(p.lit(False),v['visual']['objects']['header'][0]['properties']['show'])
            self.assertIn(name+'_label',self.vs)
        chart=self.vs['native_chart']['visual'];self.assertEqual(p.lit(False),chart['visualContainerObjects']['title'][0]['properties']['show'])
        self.assertEqual(p.lit(False),chart['objects']['zoom'][0]['properties']['showOnValueAxis'])
        self.assertIn('N Measure Caption',str(self.vs['dynamic_chart_title']['visual']['query']))
        self.assertEqual(p.lit(True),chart['objects']['seriesLabels'][0]['properties']['show'])
    def test_independent_trends_and_one_searchable_checkbox_file_control(self):
        for source,target in [('chart_trend','executive_summary'),('trend','headline'),('trend','native_chart')]:
            self.assertIn({'source':source,'target':target,'type':'NoFilter'},self.page['visualInteractions'])
        for target in ('affiliate','cycle','section','metric','drivers','tiers','periods','start_month','end_month'):
            self.assertIn({'source':'file_picker','target':target,'type':'NoFilter'},self.page['visualInteractions'])
        picker=self.vs['file_picker']['visual'];self.assertEqual(p.lit(False),picker['objects']['selection'][0]['properties']['strictSingleSelect'])
        self.assertEqual(p.lit(True),picker['objects']['searchBox'][0]['properties']['show'])
        self.assertIn('FileChoiceLabel',str(picker['query']))
        for name in ('headline','executive_summary','native_chart'):
            for value in self.vs[name].get('filterConfig',{}).get('filters',[]):self.assertNotIn('Measure',value.get('field',{}))
    def test_whole_cell_rebuild_python310_and_post_retries_disabled(self):
        before={name:(HERE/name).read_bytes() for name in ('INSTALL COMPACT TEST R01.py','VERIFY INSTALLED TEST R01.py')}
        builder.build()
        for name,raw in before.items():
            self.assertEqual(raw,(HERE/name).read_bytes())
            ast.parse(raw.decode(),feature_version=(3,10));self.assertIn('retry_config={"total":0}',raw.decode())
    def test_post_refresh_check_is_read_only_and_refuses_old_refresh(self):
        with patch.object(c,'semantic_dates',side_effect=[{'Axis':[('','2026-01-01'),('','2026-02-01')]},{'Axis':[('','2026-02-01'),('','2026-01-01')]}]):
            self.assertEqual(c.date_signature(None),c.date_signature(None))
        verify=load('release_post_check',HERE/'VERIFY INSTALLED TEST R01.py')
        db=database();fixed,_=m.patch_database(db)
        def definition(value):return {'parts':[{'path':'model.bim','payload':base64.b64encode(json.dumps(value).encode()).decode()}]}
        folder=c.RELEASE_PRIVATE+'/synthetic'
        marker={'Backup':folder,'Revision':'R01','TEST':c.TEST}
        files={c.ATTEMPT:marker,folder+'/success.json':{'Stage':'TEST_R178_UPDATED','InstalledAtUTC':'2026-10-23T22:00:00+00:00'},
          folder+'/definition-before.json':definition(db),folder+'/definition-candidate.json':definition(fixed),
          folder+'/connections-before.json':[{'id':'keep'}]}
        class PBI:
            started='2026-10-23T22:01:00Z'
            def get(self,path):return Response({'value':[{'status':'Completed','startTime':self.started}]})
        pbi=PBI()
        metadata={'Files':17,'Choices':17,'MissingImportedAt':6,'HashSuffixes':0}
        def evaluate(**kwargs):return Frame([metadata])
        with patch.object(verify,'read_private',side_effect=lambda fs,path:deepcopy(files[path])),patch.object(verify,'identity'),\
          patch.object(verify,'read_definition',return_value=({},fixed,{})),patch.object(verify,'connections',return_value=[{'id':'keep'}]),\
          patch.object(verify,'physical_dates',return_value={kind:[('','2026-01-01')] for kind in c.KINDS}),\
          patch.object(verify,'semantic_dates',return_value={kind:[('','2026-01-01')] for kind in c.KINDS}),\
          patch.object(verify,'validate_dates',return_value={'Groups':9,'InvalidDates':0}),patch.object(verify,'preflight',return_value={'PairedScalarComparisons':12}),redirect_stdout(io.StringIO()):
            for missing_imported in (6,0):
                metadata['MissingImportedAt']=missing_imported
                result=verify.verify_installed(None,pbi,None,evaluate,object())
                self.assertEqual('TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED',result['Stage'],result)
                self.assertEqual('R02',result['VerifierRevision'])
                self.assertEqual(missing_imported,result['FileLabelCounts']['MissingImportedAt'])
                self.assertEqual(0,result['FileLabelCounts']['HashSuffixes'])
                self.assertFalse(result['ModelWriteRequested']);self.assertFalse(result['RefreshRequested'])
            metadata['HashSuffixes']=1
            result=verify.verify_installed(None,pbi,None,evaluate,object())
            self.assertEqual('FILE_CHOICE_LABELS_INVALID',result['Failure']['Reason'])
            metadata['HashSuffixes']=0
            pbi.started='2026-10-23T21:00:00Z'
            result=verify.verify_installed(None,pbi,None,evaluate,object())
            self.assertEqual('NEW_ADAPTER_REFRESH_NOT_CONFIRMED',result['Failure']['Reason'])
    def test_active_processing_blocks_install_before_any_mutation(self):
        db=database();client=Client(db)
        original_get=client.get
        def get(path):return Response({'value':[{'status':'Unknown'}]}) if path.endswith('refreshes?$top=60') else original_get(path)
        client.get=get
        with tempfile.TemporaryDirectory() as temp,redirect_stdout(io.StringIO()):
            result=c.run(client,FS(Path(temp)),None,client)
        self.assertEqual('TEST_PROCESSING_ACTIVE_OR_UNKNOWN',result['Failure']['Reason'])
        self.assertEqual(0,client.updates);self.assertFalse(result['ModelWriteRequested'])
    def test_pinned_test_binding_and_no_cached_company_model(self):
        source=HERE.parents[1]/'report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 TEST.zip'
        with ZipFile(source) as old,ZipFile(HERE/'candidate'/f'{p.NAME}.zip') as new:
            binding=next(n for n in old.namelist() if n.endswith('/definition.pbir'))
            actual=next(n for n in new.namelist() if n.endswith('/definition.pbir'))
            self.assertEqual(old.read(binding),new.read(actual))
            self.assertIn(c.TEST,new.read(actual).decode())
            self.assertFalse(any(n.endswith(('.bim','.pbix','.pbit','.pbiviz')) for n in new.namelist()))

if __name__=='__main__':unittest.main()
