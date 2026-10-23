"""Metadata/API guards and independent regression algebra. No company amounts."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
import math
from pathlib import Path
import random
import re
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


p = load("r177_project", HERE / "prepare_project.py")
model = p.MODEL
builder = load("r177_builder", HERE / "build_cell.py")
cell = load("r177_cell", HERE / "UPDATE EXISTING TEST TO R17.7.py")
check = load("r177_check", HERE / "numeric_check.py")
mock = load("r177_mock", HERE.parent / "report-native-onelake-r17.1/measure-repair-r02/tests/check_repair.py")
mock.repair = cell


def database():
    return {"name": "Synthetic", "compatibilityLevel": 1604, "model": {
        "culture": "en-GB", "roles": [{"name": "KeepRole", "modelPermission": "read"}],
        "expressions": [{"name": "KeepSource", "expression": "SYNTHETIC_PRIVATE"}],
        "relationships": [{"name": "KeepRelationship", "fromTable": "A", "toTable": "B"},deepcopy(model.RELATIONSHIP)],
        "tables": [{"name": "fm_native_measures", "measures": list(model.baseline().values())},
                   model.original_helper("fm_native_files"), model.original_helper("fm_native_lines")]
                  + [{"name": "fm_native_stub"+str(i)} for i in range(21)]
                  + [{"name": "fm_review_facts", "partitions": [{"mode": "directLake", "source": {
                      "type": "entity", "expressionSource": "KeepSource", "entityName": "KeepFact"}}]}]}}


class Frame:
    def __init__(self, rows): self.rows = rows
    def to_dict(self, orient):
        assert orient == 'records'
        return deepcopy(self.rows)


class Evaluate:
    def __init__(self): self.calls, self.mode = [], "ok"
    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        assert not kwargs['use_readwrite_connection']
        if self.mode == 'unavailable': raise RuntimeError('PRIVATE MUST NOT PRINT')
        if len(self.calls) == 1:
            return Frame([{'[Country]':'ZZ','[Cycle]':'2026-10','[Driver]':'Example'}])
        rows = [{'[CheckKey]': metric+'/'+str(w)+'/'+str(y), '[P]': 1000., '[B]': -20., '[V]': 51., '[T]': 0.}
                for metric in ('market','ef','share') for w in (6,12,24) for y in (2026,2027)]
        if self.mode == 'blank':
            for row in rows:
                for field in ('P','B','V','T'): row['['+field+']'] = float('nan')
        if self.mode == 'plans_only':
            for row in rows:
                for field in ('B','V','T'): row['['+field+']'] = None
        if len(self.calls) == 3:
            if self.mode == 'mismatch': rows[0]['[B]'] = None
            if self.mode == 'incomplete': rows.pop()
            if self.mode == 'blank_to_zero': rows[0]['[T]'] = None
        return Frame(rows)


class Client(mock.Client):
    def __init__(self):
        with patch.object(mock, 'database', database): super().__init__()
        self.arrays, self.mapping_after_write = False, False
    def post(self, path, json=None):
        result = super().post(path, json=json)
        if path.endswith('/updateDefinition'):
            if self.arrays:
                for table in self.db['model']['tables']:
                    for m in table.get('measures', []):
                        m['expression'] = m['expression'].split('\n')
                        if 'formatStringDefinition' in m:
                            m['formatStringDefinition']['expression'] = m['formatStringDefinition']['expression'].split('\n')
                    for partition in table.get('partitions', []):
                        source = partition.get('source', {})
                        if 'expression' in source: source['expression'] = source['expression'].split('\n')
            if self.mapping_after_write: self.connections[0]['id'] = 'CHANGED'
        return result


class Tests(unittest.TestCase):
    def setUp(self):
        self.page, visuals = p.make_page(); self.vs = {v['name']:v for v in visuals}
    def run_cell(self, client=None, fs=None, evaluate=None):
        client, fs, evaluate = client or Client(), fs or mock.FileSystem(), evaluate or Evaluate()
        with redirect_stdout(io.StringIO()), patch.object(cell.time, 'sleep', lambda _: None):
            result = cell.run(client, fs, evaluate)
        return result, client, fs, evaluate

    def test_compact_labelled_controls_native_only_and_nonoverlap(self):
        visuals = list(self.vs.values())
        for i, visual in enumerate(visuals):
            a = visual['position']
            self.assertLessEqual(a['x']+a['width'], self.page['width'])
            self.assertLessEqual(a['y']+a['height'], self.page['height'])
            for b in [v['position'] for v in visuals[i+1:]]:
                self.assertFalse(a['x'] < b['x']+b['width'] and b['x'] < a['x']+a['width']
                                 and a['y'] < b['y']+b['height'] and b['y'] < a['y']+a['height'])
            if visual['visual']['visualType']=='slicer':
                self.assertEqual(visual['visual']['objects']['header'][0]['properties']['show'],p.lit(True))
        self.assertNotIn('scope_heading',self.vs)
        self.assertEqual(self.vs['chart_trend']['position']['height'],64)
        self.assertEqual(self.vs['metric']['position']['height'],64)

    def test_native_series_names_first_end_labels_axis_and_style_retained(self):
        chart = self.vs['native_chart']['visual']
        self.assertEqual(chart['query']['queryState']['Series']['projections'][0]['queryRef'],'fm_native_lines.SeriesLabel')
        self.assertEqual(chart['objects']['seriesLabels'][0]['properties']['show'],p.lit(True))
        self.assertEqual(chart['objects']['legend'][0]['properties']['position'],p.lit('Right'))
        self.assertEqual(chart['objects']['valueAxis'][0]['properties']['labelDisplayUnits'],p.lit(0))
        expression = model.helper_patches()['fm_native_lines'][1]
        self.assertIn('[ScopeLabel]&" · "&SWITCH([LineKind]',expression)
        self.assertIn('&[DemandCycle]',expression)
        _, old = p.OLD.make_page(); prior = next(v for v in old if v['name']=='native_chart')['visual']
        for name in ('lineStyles','dataPoint','zoom'): self.assertEqual(chart['objects'][name],prior['objects'][name])

    def test_checkbox_file_picker_import_times_search_order_and_no_ctrl(self):
        visual = self.vs['file_picker']['visual']
        self.assertEqual(visual['visualType'],'slicer')
        self.assertEqual(visual['objects']['data'][0]['properties']['mode'],p.lit('Basic'))
        for key in ('singleSelect','strictSingleSelect'):
            self.assertEqual(visual['objects']['selection'][0]['properties'][key],p.lit(False))
        self.assertEqual(visual['objects']['searchBox'][0]['properties']['show'],p.lit(True))
        self.assertEqual(visual['query']['sortDefinition']['sort'][0]['direction'],'Descending')
        old, new, columns = model.helper_patches()['fm_native_files']
        self.assertIn('"ImportedAtUTC",[_Imported]',new)
        self.assertIn('Import time unavailable',new)
        self.assertNotIn('NOW()',new)
        self.assertEqual(columns[1]['sortByColumn'],'ImportedAtUTC')
        formats = [f.get('format') for f in self.vs['matching_files']['visual']['query']['queryState']['Values']['projections']]
        self.assertIn('dd MMM yyyy HH:mm:ss',formats)

    def test_apply_all_native_buttons_and_pending_header_contract(self):
        for name in ('apply_top','apply_files'):
            v = self.vs[name]['visual']
            self.assertEqual(v['visualType'],'actionButton')
            self.assertEqual(v['visualContainerObjects']['visualLink'][0]['properties']['type'],p.lit('ApplyAllSlicers'))
            self.assertNotIn('query',v)
        self.assertEqual(len([v for v in self.vs.values() if v['visual']['visualType']=='actionButton']),2)

    def test_file_selection_adapter_preserves_original_tables_and_no_version_sum(self):
        before = database(); after, changed = model.patch_database(before)
        self.assertEqual(len(after['model']['tables'][0]['measures']),51)
        self.assertEqual(sum(t['name'].startswith('fm_native_') for t in after['model']['tables']),24)
        self.assertEqual(before['model']['tables'][-1],after['model']['tables'][-1])
        for field in ('roles','expressions','culture'): self.assertEqual(before['model'][field],after['model'][field])
        for name in ('N Monthly Numerator','N Monthly Denominator','N Source OK','N Source Caption','N Fit Cutoff','N Cutoff'):
            self.assertIn("INTERSECT(VALUES('fm_review_files'[SourceRevisionID]),VALUES('fm_native_files'[SourceRevisionID]))",model.replacements()[name])
        for name in ('N Headline Cell','N Summary Cell'):
            self.assertTrue(model.replacements()[name].startswith("IF(HASONEVALUE('fm_native_scenario'[Scenario])"))
            rows = self.vs['headline' if name=='N Headline Cell' else 'executive_summary']['visual']['query']['queryState']['Rows']['projections']
            self.assertEqual(rows[0]['queryRef'],'fm_native_scenario.Scenario')
        self.assertIn(model.RELATIONSHIP,after['model']['relationships'])
        self.assertEqual(model.patch_database(after),(after,[]))
        self.assertEqual(before,database())

    def test_performance_shape_does_not_retrain_inside_future_month_loop(self):
        edits = model.performance_edits()
        benchmark = edits['N Benchmark']
        self.assertNotIn('[N Trend Monthly]',benchmark)
        self.assertLess(benchmark.index('VAR _mean='),benchmark.index('VAR _values='))
        self.assertEqual(benchmark.count('[N Fit Mean]'),1)
        self.assertEqual(benchmark.count('[N Fit Slope]'),1)
        self.assertIn('IF(_ratio',edits['N Plan'])
        for name in ('N Monthly Numerator','N Monthly Denominator'):
            projected = edits[name]
            self.assertIn("CALCULATETABLE(SELECTCOLUMNS('fm_review_facts'",projected)
            self.assertIn('GROUPBY(_memberFacts,[Sector]',projected)
            self.assertNotIn('DISTINCT(_memberFacts)',projected)
            self.assertIn('"BadCells",SUMX(CURRENTGROUP(),INT([MissingCells]<>0||ISBLANK([Amount])))',projected)
        self.assertIn('ABS(_b)',edits['N Variance %'])
        self.assertTrue(model.replacements()['N Chart Monthly'].startswith('IF([N Line Visible]=1,'))
        self.assertIn(model.baseline()['N Chart Monthly']['expression'],model.replacements()['N Chart Monthly'])
        self.assertFalse(any('Measure' in f.get('field',{}) for f in self.vs['native_chart']['filterConfig']['filters']))

    def test_regression_algebra_missing_zero_negative_ratio_and_all_windows(self):
        rng = random.Random(177)
        checks = 0
        # Independent old per-point fitting vs one fit reused for each period.
        # Includes zero/negative histories, missing training, variable weights,
        # all-actual, all-future, mixed and a missing future denominator.
        def fit(train):
            if any(v is None for v in train): return None
            w=len(train); xs=list(range(1,w+1)); mx=sum(xs)/w; my=sum(train)/w
            slope=sum((x-mx)*(v-my) for x,v in zip(xs,train))/sum((x-mx)**2 for x in xs)
            return my,slope,mx
        for w in (6,12,24):
            for case in range(150):
                training = [rng.uniform(-200,200) for _ in range(w)] if case%7 else [0.]*w
                if case%13==0: training[-1]=None
                for ratio in (False,True):
                    for points in (range(-11,1),range(-7,5),range(1,13),range(13,25)):
                        den=[rng.uniform(1,100) for _ in points]
                        if case%17==0 and ratio: den[-1]=None
                        def old_value(offset):
                            if offset<=0:return 3.+offset
                            trained=fit(training)
                            return None if trained is None else trained[0]+trained[1]*(offset+w-trained[2])
                        before=[old_value(i) for i in points]
                        trained=fit(training)
                        after=[3.+i if i<=0 else None if trained is None else trained[0]+trained[1]*(i+w-(w+1)/2) for i in points]
                        def total(vals):
                            if any(v is None for v in vals):return None
                            if ratio:
                                if any(v is None for v in den):return None
                                return sum(v*d for v,d in zip(vals,den))/sum(den)
                            return sum(vals)
                        a,b=total(before),total(after)
                        if a is None:self.assertIsNone(b)
                        else:self.assertTrue(math.isclose(a,b,rel_tol=1e-12,abs_tol=1e-10))
                        checks+=1
        self.assertEqual(checks,3600)

    def test_numeric_preflight_virtual_override_read_only_no_values_exposed(self):
        ev=Evaluate()
        with redirect_stdout(io.StringIO()) as stream:
            result=cell.verify_numeric(ev,'WORKSPACE','TEST',cell.NUMERIC_OVERRIDES)
        self.assertEqual(result['Checks'],72)
        self.assertEqual(result['Mismatches'],0)
        self.assertIn('DEFINE',ev.calls[2]['dax_string'])
        self.assertNotIn('DEFINE',ev.calls[1]['dax_string'])
        self.assertTrue(all(c['dataset']=='TEST' and not c['use_readwrite_connection'] for c in ev.calls))
        self.assertNotIn('1000',stream.getvalue())
        for mode in ('unavailable','blank','plans_only','incomplete','mismatch','blank_to_zero'):
            ev=Evaluate();ev.mode=mode
            with self.assertRaises(RuntimeError),redirect_stdout(io.StringIO()):
                cell.verify_numeric(ev,'W','TEST',cell.NUMERIC_OVERRIDES)

    def test_cell_build_python310_backup_preservation_and_one_scoped_write(self):
        source=(HERE/'UPDATE EXISTING TEST TO R17.7.py').read_text()
        self.assertEqual(source,builder.build());ast.parse(source,feature_version=(3,10))
        result,client,fs,ev=self.run_cell()
        self.assertEqual(result['Stage'],'TEST_R177_UPDATED')
        self.assertEqual(len(mock.writes(client)),1)
        self.assertEqual(mock.writes(client)[0][1]['options'],{'allowPurgeData':False})
        self.assertEqual(len(ev.calls),3)
        self.assertTrue(result['CloudConnectionPreserved'])
        self.assertFalse(result['CompanyAmountValuesPrintedOrStored'] or result['RefreshRequested'] or result['ReportPublished'])
        self.assertTrue(any(k.endswith('numerical-check-summary.json') for k in fs.files))
        self.assertFalse(any(cell.ORIGINAL_MODEL in path for _,path,_ in client.calls))

    def test_no_write_on_numeric_or_metadata_or_backup_failures(self):
        for mode in ('mismatch','incomplete','blank','unavailable','identity','unknown_expression','unknown_format',
                     'unknown_helper','missing_cloud','concurrent','connection_change','truncated','put_false','copy_false'):
            with self.subTest(mode=mode):
                client,fs,ev=Client(),mock.FileSystem(),Evaluate()
                if mode in ('mismatch','incomplete','blank','unavailable'):ev.mode=mode
                elif mode=='identity':client.identity['id']=cell.ORIGINAL_MODEL
                elif mode=='unknown_expression':client.db['model']['tables'][0]['measures'][0]['expression']='UNKNOWN'
                elif mode=='unknown_format':
                    m=next(m for m in client.db['model']['tables'][0]['measures'] if 'formatStringDefinition' in m)
                    m['formatStringDefinition']['expression']='UNKNOWN'
                elif mode=='unknown_helper':client.db['model']['tables'][1]['partitions'][0]['source']['expression']='UNKNOWN'
                elif mode=='missing_cloud':client.connections=[]
                elif mode in ('concurrent','connection_change'):setattr(client,mode,True)
                else:
                    setattr(fs,mode,True)
                    if mode=='truncated':client.db['model']['expressions'][0]['expression']='SYNTHETIC é'*20000
                with self.assertRaises((RuntimeError,ValueError)):self.run_cell(client,fs,ev)
                self.assertFalse(mock.writes(client))

    def test_readback_arrays_and_failures_no_retry_or_false_success(self):
        client=Client();client.arrays=True
        result,_,_,_=self.run_cell(client)
        self.assertEqual(result['Stage'],'TEST_R177_UPDATED')
        for mode in ('bad_readback','mapping_after_write'):
            client=Client();setattr(client,mode,True)
            result,client,fs,_=self.run_cell(client)
            self.assertEqual(result['Stage'],'TEST_R177_READBACK_NEEDS_REVIEW')
            self.assertEqual(len(mock.writes(client)),1)
            self.assertFalse(any(k.endswith('success.json') for k in fs.files))
        client=Client();client.reject=True
        with self.assertRaises(RuntimeError):self.run_cell(client)
        self.assertEqual(len(mock.writes(client)),1)
        client=Client();client.db,_=cell.patch_database(client.db)
        result,client,_,ev=self.run_cell(client)
        self.assertEqual(result['Stage'],'TEST_R177_ALREADY_INSTALLED')
        self.assertFalse(mock.writes(client) or ev.calls)

    def test_original_static_files_and_chart_helpers_preserved_inside_wrappers(self):
        before=database();after,_=model.patch_database(before)
        after_by={t['name']:t for t in after['model']['tables']}
        for name,(old,new,_) in model.helper_patches().items():
            if name=='fm_native_files':
                marker='RETURN SELECTCOLUMNS(_ranked,\n '
                self.assertEqual(old.split(marker)[0],new.split(marker)[0])
                self.assertTrue(new.endswith(old.split(marker)[1]))
            else:self.assertIn(old,new)
            self.assertEqual(model.expression_hash(after_by[name]['partitions'][0]['source']['expression']),model.expression_hash(new))
        self.assertEqual(after_by['fm_review_facts'],before['model']['tables'][-1])
        old_measures=model.baseline();new_measures={m['name']:m for m in after_by['fm_native_measures']['measures']}
        for name in old_measures:
            self.assertEqual(old_measures[name].get('formatStringDefinition'),new_measures[name].get('formatStringDefinition'))

    def test_project_binding_fabricated_sample_and_no_custom_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            test,sample=Path(tmp)/'TEST',Path(tmp)/'SAMPLE'
            p.create(HERE.parent/'report-native-only-r17.6/candidate/ForecastMaster Native Only R17.6 TEST.zip',test)
            p.sample_from_frozen(test,sample)
            self.assertFalse(list(test.rglob('model.bim')))
            self.assertFalse(list(test.rglob('*.pbiviz'))+list(test.rglob('*.js')))
            for path in test.rglob('visual.json'):
                self.assertIn(json.loads(path.read_text())['visual']['visualType'],
                              {'textbox','slicer','cardVisual','tableEx','pivotTable','lineChart','actionButton'})
            observed=json.loads(next(sample.glob('*.SemanticModel/model.bim')).read_text())
            with ZipFile(HERE.parent/'report-native-only-r17.6/candidate/ForecastMaster Native Only R17.6 SAMPLE.zip') as archive:
                original=json.loads(archive.read(next(n for n in archive.namelist() if n.endswith('/model.bim'))))
            self.assertEqual(observed,model.patch_database(original)[0])


if __name__=='__main__': unittest.main(verbosity=2)
