"""Focused public-fixture and native-report contracts; no company connection."""
from collections import Counter
from copy import deepcopy
import importlib.util
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('test_r02_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


large = load('large_fixture')
report = load('prepare_project')
model = load('model')


class CorrectionContracts(unittest.TestCase):
    def test_twenty_files_and_exact_sector_population(self):
        rows = large.files()
        self.assertEqual(len(rows), 20)
        self.assertEqual(len({r['SourceRevisionID'] for r in rows}), 20)
        self.assertEqual(set(Counter(r['DemandCycle'] for r in rows).values()), {10})
        self.assertEqual(set(Counter((r['DemandCycle'], r['GrowthDriver']) for r in rows).values()), {2})
        self.assertEqual(20 * large.SECTORS, 500)
        self.assertEqual(20 * large.SECTORS * 84 * 10, 420000)

    def test_explicit_defaults_and_import_times(self):
        labels = large.defaults()
        self.assertEqual(len(labels), 10)
        self.assertEqual(len(set(labels)), 10)
        self.assertTrue(all('_ADS.xlsm · 23 Oct 2026 ' in s and s.endswith(' UTC') for s in labels))

    def test_every_sample_partition_is_calculated(self):
        database = large.database()
        self.assertTrue(all(p['source']['type'] == 'calculated'
                            for t in database['model']['tables'] for p in t.get('partitions', [])))
        facts = next(t for t in database['model']['tables'] if t['name'] == 'fm_review_facts')
        self.assertIn('ef-ads-units', facts['partitions'][0]['source']['expression'])
        self.assertNotIn('gm-ads-units', facts['partitions'][0]['source']['expression'])

    def test_model_changes_only_the_twelve_declared_expressions(self):
        before = model.original_database()
        snapshot = deepcopy(before)
        after, edits = model.patch_database(before)
        self.assertEqual(before, snapshot)
        self.assertEqual(len(edits), 12)
        old = next(t for t in before['model']['tables'] if t['name'] == 'fm_native_measures')['measures']
        new = next(t for t in after['model']['tables'] if t['name'] == 'fm_native_measures')['measures']
        for a, b in zip(old, new):
            self.assertEqual(a.get('formatString'), b.get('formatString'))
            self.assertEqual(a.get('formatStringDefinition'), b.get('formatStringDefinition'))
            if a['name'] not in edits:
                self.assertEqual(a, b)
        next(t for t in after['model']['tables'] if t['name'] == 'fm_native_measures')['measures'] = old
        self.assertEqual(after, before)

    def test_unknown_baseline_is_refused(self):
        database = model.original_database()
        table = next(t for t in database['model']['tables'] if t['name'] == 'fm_native_measures')
        table['measures'][0]['expression'] = '0'
        with self.assertRaises(ValueError):
            model.patch_database(database)

    def test_matching_adapter_preserves_service_metadata_and_line_arrays(self):
        adapter = load('adapter')
        before = model.original_database()
        measures = adapter.planning.measures(before)
        for name in adapter.planning.replacements():
            measures[name]['expression'] = model.OLD.expression_text(measures[name]['expression']).splitlines()
            measures[name]['annotations'] = [{'name': 'FabricatedMetadata', 'value': 'preserve'}]
        snapshot = deepcopy(before)
        after, edits = adapter.patch_database(before)
        self.assertEqual(before, snapshot)
        self.assertEqual(len(edits), 15)
        restore = adapter.planning.measures(after)
        for name in edits:
            self.assertEqual(restore[name].get('annotations'), measures[name].get('annotations'))
            restore[name]['expression'] = deepcopy(measures[name]['expression'])
        for name in adapter.formats.NAMES:
            restore[name]['formatStringDefinition'] = deepcopy(measures[name]['formatStringDefinition'])
        self.assertEqual(after, before)

    def test_display_definitions_preserve_numeric_model_and_currency_logic(self):
        formats = load('display_formats')
        before = model.original_database()
        snapshot = deepcopy(before)
        after, names = formats.patch_database(before)
        self.assertEqual(before, snapshot)
        self.assertEqual(set(names), set(formats.NAMES))
        old, new = formats.measures(before), formats.measures(after)
        for name in names:
            expression = model.OLD.expression_text(new[name]['formatStringDefinition']['expression'])
            original = model.OLD.expression_text(old[name]['formatStringDefinition']['expression'])
            self.assertEqual(original.split('VAR _value=')[0], expression.split('VAR _value=')[0])
            self.assertEqual(new[name]['expression'], old[name]['expression'])
            self.assertIn('_literal&";"&_literal&";"&_literal', expression)
            new[name]['formatStringDefinition'] = deepcopy(old[name]['formatStringDefinition'])
        self.assertEqual(after, before)

    def test_matching_adapter_rejects_unknown_cell_or_numeric_format(self):
        adapter = load('adapter')
        for field in ('expression', 'formatString'):
            before = model.original_database()
            adapter.planning.measures(before)['N Summary Cell'][field] = 'UNKNOWN'
            with self.assertRaises(ValueError):
                adapter.patch_database(before)

    def test_export_oracle_preserves_scale_sign_and_actual_only_omission(self):
        export = load('verify_export')
        self.assertEqual(export.formatted(-585900), '−585.9k')
        self.assertEqual(export.formatted(371250, symbol='£'), '£371.3k')
        self.assertEqual(export.formatted(.215, True), '21.5%')
        self.assertEqual(export.values(1, 1, 2026, 'YTD').keys(), {'Plan'})
        self.assertAlmostEqual(export.values(1, 1, 2026, 'FY')['12M variance'], 6000)

    def test_native_controls_and_geometry(self):
        page, visuals = report.make_page(large.defaults())
        by = {v['name']: v for v in visuals}
        self.assertEqual(by['file_picker']['visual']['visualType'], 'listSlicer')
        self.assertEqual(by['headline']['position']['height'], 144)
        rows = by['executive_summary']['visual']['query']['queryState']['Rows']['projections']
        self.assertEqual([p['queryRef'] for p in rows], ['fm_native_scope.GrowthDriver', 'fm_native_scope.SectorLabel'])
        self.assertEqual([p['active'] for p in rows], [True, False])
        states = by['executive_summary']['visual']['expansionStates']
        row_state = next(s for s in states if s['roles'] == ['Rows'])
        self.assertEqual([level['queryRefs'] for level in row_state['levels']],
                         [[p['queryRef']] for p in rows])
        self.assertTrue(all(level['isCollapsed'] and level['isPinned'] for level in row_state['levels']))
        chart = by['native_chart']['visual']
        self.assertEqual(chart['objects']['valueAxis'][0]['properties']['labelDisplayUnits'], report.lit(1))
        self.assertEqual(chart['objects']['seriesLabels'][0]['properties']['show'], report.lit(False))
        self.assertFalse(any('apply' in name.lower() for name in by))
        rectangles = sorted((v['position']['y'], v['position']['y'] + v['position']['height'], v['name'])
                            for v in visuals if v['name'] in {'headline', 'native_chart', 'executive_summary', 'file_picker'})
        self.assertTrue(all(a[1] <= b[0] for a, b in zip(rectangles, rectangles[1:])))
        self.assertLessEqual(rectangles[-1][1], page['height'])

    def test_section_bookmarks_preserve_all_other_choices(self):
        bookmark = report.selection_bookmark('section_ef', 'Ex-factory', 'Ex-factory ADS')
        self.assertEqual(bookmark['options']['targetVisualNames'], ['section', 'metric'])
        self.assertTrue(bookmark['options']['suppressDisplay'])
        self.assertFalse(bookmark['options']['suppressData'])
        self.assertEqual(set(bookmark['explorationState']['sections']['native_demand']['visualContainers']), {'section', 'metric'})

    def test_missing_defaults_refused(self):
        for labels in ([], None, ['']):
            with self.assertRaises(ValueError):
                report.make_page(labels)

    def test_dax_file_labels_preserve_unicode_and_quotes(self):
        cases = load('chart_cases')
        actual = cases.tf('Files', 'Label', ['A · B "quoted"'])
        self.assertIn('A · B ""quoted""', actual)
        self.assertNotIn('\\u00b7', actual)
        self.assertNotIn('\\"', actual)

    def test_no_bookmark_reset_can_remove_file_availability(self):
        _, visuals = report.make_page(large.defaults())
        by = {v['name']: v for v in visuals}
        self.assertNotIn('files_defaults', by)
        self.assertIn('filter', by['file_picker']['filterConfig']['filters'][0])
        self.assertGreaterEqual(by['file_picker']['position']['y'] - (
            by['files_heading']['position']['y'] + by['files_heading']['position']['height']), 30)


if __name__ == '__main__':
    unittest.main()
