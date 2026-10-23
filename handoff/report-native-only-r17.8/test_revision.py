"""Native metadata/selection contracts. No Desktop or company DAX claim."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('r178_prepare_test',HERE/'prepare_project.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
m=p.MODEL

class Tests(unittest.TestCase):
    def setUp(self):
        self.page,vs=p.make_page();self.vs={v['name']:v for v in vs}
    def test_compact_geometry_no_overlap_or_clipped_title_padding(self):
        self.assertEqual(1330,self.page['height'])
        vs=list(self.vs.values())
        for i,v in enumerate(vs):
            a=v['position'];self.assertLessEqual(a['x']+a['width'],self.page['width'])
            self.assertLessEqual(a['y']+a['height'],self.page['height'])
            for u in vs[i+1:]:
                b=u['position']
                self.assertFalse(a['x']<b['x']+b['width'] and b['x']<a['x']+a['width'] and
                                 a['y']<b['y']+b['height'] and b['y']<a['y']+a['height'],(v['name'],u['name']))
            if v['visual']['visualType']=='textbox':
                self.assertTrue(all(x==p.lit(0) for x in v['visual']['visualContainerObjects']['padding'][0]['properties'].values()))
    def test_one_file_control_no_source_mode_apply_or_duplicate_audit_table(self):
        for name in ('source_mode','apply_top','apply_files','apply_note','matching_files','chart_key'):
            self.assertNotIn(name,self.vs)
        self.assertEqual(1,sum(v['name']=='file_picker' for v in self.vs.values()))
        self.assertFalse(any(v['visual']['visualType'] in {'tableEx','actionButton'} for v in self.vs.values()))
        file=self.vs['file_picker']
        self.assertEqual('fm_native_files.FileChoiceLabel',file['visual']['query']['queryState']['Values']['projections'][0]['queryRef'])
        self.assertEqual(p.lit(False),file['visual']['objects']['selection'][0]['properties']['singleSelect'])
        self.assertEqual(p.lit(False),file['visual']['objects']['selection'][0]['properties']['strictSingleSelect'])
        self.assertEqual('N File Available',file['filterConfig']['filters'][0]['field']['Measure']['Property'])
    def test_compact_independent_right_controls_and_dynamic_outside_chart_title(self):
        for name in ('trend','chart_trend','view'):
            self.assertEqual(44,self.vs[name]['position']['height'])
            self.assertEqual(1200,self.vs[name]['position']['x'])
            self.assertEqual(p.lit(False),self.vs[name]['visual']['objects']['header'][0]['properties']['show'])
        self.assertNotEqual(self.vs['trend']['visual']['query']['queryState'],self.vs['chart_trend']['visual']['query']['queryState'])
        chart=self.vs['native_chart']['visual']
        self.assertEqual(p.lit(False),chart['visualContainerObjects']['title'][0]['properties']['show'])
        title=self.vs['dynamic_chart_title']['visual']['query']['queryState']['Data']['projections'][0]
        self.assertEqual('fm_native_measures.N Measure Caption',title['queryRef'])
        self.assertEqual(p.lit(False),chart['objects']['zoom'][0]['properties']['show'])
    def test_draft_adapter_preserves_arithmetic_formats_original_sources_and_metadata(self):
        before=m.original_database();after,changed=m.patch_database(before)
        orig={t['name']:t for t in before['model']['tables']};new={t['name']:t for t in after['model']['tables']}
        for name in orig:
            if name not in {'fm_native_measures','fm_native_files'}:self.assertEqual(orig[name],new[name])
        old={a['name']:a for a in orig['fm_native_measures']['measures']}
        fixed={a['name']:a for a in new['fm_native_measures']['measures']}
        for name in ('N Plan','N Benchmark','N Variance','N Variance %','N Fit Mean','N Fit Slope','N Trend Monthly','N Display'):
            self.assertEqual(old[name],fixed[name])
        for name in old:
            self.assertEqual(old[name].get('formatStringDefinition'),fixed[name].get('formatStringDefinition'))
        self.assertEqual(orig['fm_native_files']['columns'],new['fm_native_files']['columns'])
        self.assertEqual(52,len(fixed));self.assertEqual(before['model']['relationships'],after['model']['relationships'])
        for name in ('N Monthly Numerator','N Monthly Denominator','N Source OK','N Catalog Available','N Scope Available','N Line Visible','N Chart Monthly','N Scenario Visible'):
            self.assertEqual(old[name]['expression'].replace(m.OLD_MODE,m.MODE),fixed[name]['expression'])
    def test_auto_file_detection_ambiguous_version_guards_and_invalid_dates_remain_explicit(self):
        edits=m.replacements()
        self.assertIn(m.PICKED,edits['N Source OK'])
        self.assertIn('COUNTROWS(_files)=COUNTROWS(_cohorts)',edits['N Source OK'])
        self.assertIn('COUNTROWS(_cohorts)=COUNTROWS(_expected)',edits['N Source OK'])
        for name in ('N Cutoff','N Fit Cutoff'):self.assertIn(m.DATE_OK,edits[name])
        self.assertIn('Cutoff metadata unavailable',edits['N Source Caption'])
        self.assertIn('"unavailable"',edits['N Source Caption'])
        self.assertNotIn('Apply filters',edits['N Source Caption'])
        old,new=m.file_expression()
        self.assertIn('&" | "&[SourceRevisionID]',old)
        self.assertNotIn('&" | "&[SourceRevisionID]',new)
        self.assertIn('" · v"&FORMAT(_number,"0")',new)
        self.assertIn("'fm_review_files'[Country]",m.FILE_AVAILABLE)
        self.assertIn("'fm_review_files'[DemandCycle]",m.FILE_AVAILABLE)
    def test_unknown_definition_refused_before_draft_patch(self):
        db=m.original_database();next(t for t in db['model']['tables'] if t['name']=='fm_native_measures')['measures'][0]['expression']='UNKNOWN'
        with self.assertRaises(ValueError):m.patch_database(db)
    def test_sample_is_fabricated_and_test_bound_package_is_explicitly_held(self):
        source=HERE.parent/'report-native-only-r17.7/candidate/ForecastMaster Native Only R17.7 TEST.zip'
        with tempfile.TemporaryDirectory() as temp:
            test=Path(temp)/'test';sample=Path(temp)/'sample'
            p.create(source,test);p.create_sample(test,sample)
            self.assertIn('HOLD:',(test/'OPEN FIRST.txt').read_text())
            with ZipFile(source) as z:
                binding=z.read(next(n for n in z.namelist() if n.endswith('/definition.pbir')))
            self.assertEqual(binding,(test/(p.NAME+'.Report')/'definition.pbir').read_bytes())
            self.assertFalse(json.loads((sample/'PRESERVATION.json').read_text())['FabricConnection'])
            self.assertFalse(any(x.suffix.lower() in {'.pbiviz','.pbix','.pbit'} for x in test.rglob('*')))

if __name__=='__main__':unittest.main()
