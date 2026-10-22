"""Structural regression for the actual generated thin report, not UI acceptance."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import prepare_project as p
import model


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.root=Path(cls.temp.name)/'new'
        cls.receipt=p.create(HERE.parent/'report-native-onelake-r17.1/candidate/ForecastMaster Native Review R17.1 TEST.zip',cls.root)
        cls.report=cls.root/(p.NAME+'.Report')
        cls.pages=cls.report/'definition/pages'
        cls.bookmarks={f.stem.replace('.bookmark',''):json.loads(f.read_text()) for f in (cls.report/'definition/bookmarks').glob('*.bookmark.json')}

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def visuals(self,page):
        return {f.parent.name:json.loads(f.read_text()) for f in (self.pages/page/'visuals').glob('*/visual.json')}

    def test_all_native_buttons_have_visible_labels_and_valid_actions(self):
        for page in ('native_demand','native_sop','native_export'):
            for v in self.visuals(page).values():
                if v.get('visual',{}).get('visualType')!='actionButton':continue
                objects=v['visual']['objects'];container=v['visual']['visualContainerObjects']
                self.assertNotIn('visualLink',objects)
                self.assertTrue(any(x.get('properties',{}).get('show')==p.lit(True) for x in objects['text']))
                self.assertTrue(any(x.get('selector',{}).get('id')=='default' and x['properties'].get('text') for x in objects['text']))
                action=container['visualLink'][0]['properties']
                target=action.get('bookmark',action.get('navigationSection'))['expr']['Literal']['Value'][1:-1]
                if 'bookmark' in action:self.assertIn(target,self.bookmarks)
                else:self.assertTrue((self.pages/target/'page.json').is_file())
                self.assertGreaterEqual(v['position']['height'],40)

    def test_bookmark_targets_exist_and_data_display_separate(self):
        for b in self.bookmarks.values():
            key=b['explorationState']['activeSection'];vs=self.visuals(key)
            for target in b['options']['targetVisualNames']:self.assertIn(target,vs)
            if b['name'].endswith(('_clear','_all')):self.assertTrue(b['options']['suppressDisplay'])
            else:self.assertTrue(b['options']['suppressData'])

    def test_matching_header_and_compact_dynamic_scope(self):
        a,b=self.visuals('native_demand'),self.visuals('native_sop')
        for name in ('heading','review_months','source_status','affiliate','cycle','currency','display','drivers','tiers','periods','rates_show'):
            self.assertEqual({k:a[name]['position'][k] for k in ('x','y','width','height')},
                             {k:b[name]['position'][k] for k in ('x','y','width','height')},name)
        for vs in (a,b):
            self.assertEqual(vs['drivers']['visual']['query']['queryState']['Values']['projections'][0]['queryRef'],'fm_native_scope.GrowthDriver')
            self.assertEqual(vs['tiers']['visual']['query']['queryState']['Values']['projections'][0]['queryRef'],'fm_native_scope.SectorLabel')
            self.assertTrue(vs['fx_controls']['isHidden'])
            self.assertFalse(vs['native_chart']['visual']['query']['queryState']['Category']['showAll'])
            self.assertIn("datetime'2026-01-01",json.dumps(vs['review_months']))
            self.assertNotIn('summary_group',vs)

    def test_chart_click_does_not_change_total_matrix(self):
        for page in ('native_demand','native_sop'):
            interactions=json.loads((self.pages/page/'page.json').read_text())['visualInteractions']
            for rule in interactions:
                self.assertEqual(rule['type'],'DataFilter' if rule['target']=='month_readout' else 'NoFilter')

    def test_matrices_open_with_details_and_no_chart_drill_flags(self):
        for page in ('native_demand','native_sop','native_export'):
            for v in self.visuals(page).values():
                kind=v.get('visual',{}).get('visualType')
                if kind not in {'pivotTable','tableEx'}:continue
                for role in v['visual']['query']['queryState'].values():
                    for q in role.get('projections',[]):self.assertNotIn('active',q)
                if kind=='pivotTable':
                    self.assertTrue(v['visual']['expansionStates'])
                    for state in v['visual']['expansionStates']:
                        self.assertTrue(all(not level['isCollapsed'] for level in state['levels']))

    def test_native_fields_exist_in_revision(self):
        # All unchanged helper fields come from the installed R17.1 definition.
        spec=importlib.util.spec_from_file_location('engine',HERE/'tests/engine_fixture.py')
        e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
        db,*_=e.build()
        tables={t['name']:{x['name'] for x in t.get('columns',[])}|{m['name'] for m in t.get('measures',[])} for t in db['model']['tables']}
        def walk(value):
            if isinstance(value,dict):
                for kind in ('Measure','Column'):
                    if kind in value:
                        f=value[kind];entity=f.get('Expression',{}).get('SourceRef',{}).get('Entity')
                        if entity:self.assertIn(f['Property'],tables[entity],entity)
                for v in value.values():walk(v)
            elif isinstance(value,list):
                for v in value:walk(v)
        for page in ('native_demand','native_sop','native_export'):walk(list(self.visuals(page).values()))

    def test_preservation_and_thin_test_only(self):
        self.assertTrue(self.receipt['TESTBindingPreserved'])
        self.assertFalse(self.receipt['CompanyModelIncluded'])
        binding=(self.report/'definition.pbir').read_text()
        self.assertIn('31d00232-ac03-48fe-af39-f2e4bae82443',binding)
        self.assertNotIn('e7af2967-7725-4108-a170-9e490d4e35bb',binding)
        self.assertFalse(list(self.root.rglob('*.bim')))
        self.assertFalse(list(self.root.rglob('*.pbix')))


if __name__=='__main__':unittest.main(verbosity=2)
