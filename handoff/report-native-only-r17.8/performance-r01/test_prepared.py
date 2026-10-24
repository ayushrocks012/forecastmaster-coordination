"""Guard exact prototype boundaries; numerical proof is native, not mocked."""
from copy import deepcopy
import unittest

import prepared
import vectorized
import star
import pushdown
import physical
import moments
import cells


class PreparedContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline = prepared.adapter.patch_database(prepared.adapter.selection.original_database())[0]

    def test_restore_preserves_every_baseline_property(self):
        before = deepcopy(self.baseline)
        after = prepared.patch(before)
        self.assertEqual(before, self.baseline)
        restored = deepcopy(after)
        restored['model']['tables'] = [t for t in restored['model']['tables'] if t['name'] != prepared.TABLE]
        original = prepared.adapter.planning.measures(before)
        table = next(t for t in restored['model']['tables'] if t['name'] == 'fm_native_measures')
        table['measures'] = [m for m in table['measures'] if not m['name'].startswith('P R02 ')]
        current = prepared.adapter.planning.measures(restored)
        for name in ('N Monthly Numerator', 'N Monthly Denominator'):
            self.assertEqual(current[name].get('formatString'), original[name].get('formatString'))
            current[name]['expression'] = deepcopy(original[name]['expression'])
        self.assertEqual(restored, before)

    def test_unknown_kernel_and_second_application_refused(self):
        changed = deepcopy(self.baseline)
        prepared.adapter.planning.measures(changed)['N Monthly Numerator']['expression'] = '0'
        with self.assertRaisesRegex(ValueError, 'Unknown R02'):
            prepared.patch(changed)
        with self.assertRaisesRegex(ValueError, 'already installed'):
            prepared.patch(prepared.patch(self.baseline))

    def test_original_fallbacks_preserve_exact_dax(self):
        current = prepared.adapter.planning.measures(prepared.patch(self.baseline))
        original = prepared.adapter.planning.measures(self.baseline)
        for role in ('Numerator', 'Denominator'):
            self.assertEqual(current['P R02 Monthly ' + role]['expression'], original['N Monthly ' + role]['expression'])
            self.assertTrue(current['P R02 Monthly ' + role]['isHidden'])

    def test_batched_period_and_fit_boundaries_preserve_other_measures(self):
        before = deepcopy(self.baseline)
        after = vectorized.patch(before)
        old = prepared.adapter.planning.measures(before)
        current = prepared.adapter.planning.measures(after)
        for name in ('N Plan', 'N Fit Mean', 'N Fit Slope'):
            self.assertEqual(current['P R02 ' + name[2:]]['expression'], old[name]['expression'])
            current[name]['expression'] = deepcopy(old[name]['expression'])
        for name in ('N Monthly Numerator', 'N Monthly Denominator'):
            current[name]['expression'] = deepcopy(old[name]['expression'])
        for name in old:
            self.assertEqual(current[name], old[name])
        self.assertEqual(before, self.baseline)

    def test_star_preserves_baseline_after_declared_changes_restored(self):
        before = deepcopy(self.baseline)
        after = star.patch(before)
        restored = deepcopy(after)
        restored['model']['tables'] = [t for t in restored['model']['tables'] if t['name'] not in {prepared.TABLE, star.DIM}]
        restored['model']['relationships'] = [r for r in restored['model']['relationships'] if not r['name'].startswith('Perf-Sector-')]
        old = prepared.adapter.planning.measures(before)
        current = prepared.adapter.planning.measures(restored)
        for name in star.NAMES:
            current[name]['expression'] = deepcopy(old[name]['expression'])
        for table in restored['model']['tables']:
            table['columns'] = [c for c in table.get('columns', []) if c['name'] != star.KEY]
            if table['name'] == 'fm_native_measures':
                table['measures'] = [m for m in table['measures'] if m['name'] in old]
        self.assertEqual(restored, before)

    def test_fast_and_legacy_graphs_do_not_call_monthly_dispatchers(self):
        current = prepared.adapter.planning.measures(star.patch(self.baseline))
        for name in star.NAMES:
            for lane in (star.fast_name, star.legacy_name):
                text = current[lane(name)]['expression']
                for dispatch in star.NAMES:
                    self.assertNotIn('[' + dispatch + ']', text)
            self.assertIn('[P Perf Eligible]', current[name]['expression'])

    def test_source_filter_patch_preserves_all_other_model_properties(self):
        before = deepcopy(self.baseline)
        after = pushdown.patch(before)
        original = prepared.adapter.planning.measures(before)
        current = prepared.adapter.planning.measures(after)
        changed = {name for name in original if current[name] != original[name]}
        self.assertEqual(changed, {'N Catalog Available', 'N Source OK',
            'N Scope Available', 'N Cutoff', 'N Monthly Numerator',
            'N Monthly Denominator', 'N Fit Cutoff'})
        for name in changed:
            current[name]['expression'] = deepcopy(original[name]['expression'])
        self.assertEqual(after, before)
        self.assertEqual(before, self.baseline)

    def test_unknown_source_policy_and_reapplication_refused(self):
        changed = deepcopy(self.baseline)
        measures = prepared.adapter.planning.measures(changed)
        body = measures['N Monthly Numerator']['expression']
        measures['N Monthly Numerator']['expression'] = body.replace(
            'VAR _custom = "Selected files" = "Selected files"',
            'VAR _custom = SELECTEDVALUE(\'fm_native_file_mode\'[Mode]) = "Selected files"')
        with self.assertRaisesRegex(ValueError, 'Unknown source policy'):
            pushdown.patch(changed)
        with self.assertRaises(ValueError):
            pushdown.patch(pushdown.patch(self.baseline))

    def test_physical_prototype_preserves_original_model_and_fallback_graph(self):
        before = deepcopy(self.baseline)
        after = physical.patch(before)
        original = prepared.adapter.planning.measures(before)
        current = prepared.adapter.planning.measures(after)
        for name in star.NAMES:
            self.assertTrue(current[star.legacy_name(name)]['isHidden'])
            for public in star.NAMES:
                self.assertNotIn('[' + public + ']', current[star.legacy_name(name)]['expression'])
        after['model']['tables'] = [t for t in after['model']['tables'] if t['name'] not in
            {prepared.TABLE, star.DIM, moments.SHARE}]
        after['model']['relationships'] = [r for r in after['model']['relationships'] if not r['name'].startswith('Perf-')]
        for table in after['model']['tables']:
            table['columns'] = [c for c in table.get('columns', []) if c['name'] != star.KEY]
            if table['name'] == 'fm_native_measures':
                table['measures'] = [m for m in table['measures'] if m['name'] in original]
        for name in star.NAMES:
            current[name]['expression'] = deepcopy(original[name]['expression'])
        self.assertEqual(after, before)
        self.assertEqual(before, self.baseline)

    def test_shared_cells_change_only_two_expressions(self):
        before = deepcopy(self.baseline)
        after = cells.patch(before)
        old = prepared.adapter.planning.measures(before)
        current = prepared.adapter.planning.measures(after)
        self.assertEqual({n for n in old if old[n] != current[n]}, {'N Summary Cell', 'N Headline Cell'})
        for name in ('N Summary Cell', 'N Headline Cell'):
            current[name]['expression'] = deepcopy(old[name]['expression'])
        self.assertEqual(after, before)
        self.assertEqual(before, self.baseline)

    def test_shared_cells_accept_service_line_arrays_but_refuse_unknown_formulas(self):
        before = deepcopy(self.baseline)
        old = prepared.adapter.planning.measures(before)
        old['N Summary Cell']['expression'] = old['N Summary Cell']['expression'].splitlines()
        cells.patch(before)
        old['N Headline Cell']['expression'] = '0'
        with self.assertRaisesRegex(ValueError, 'Unknown R02 cell'):
            cells.patch(before)


if __name__ == '__main__':
    unittest.main()
