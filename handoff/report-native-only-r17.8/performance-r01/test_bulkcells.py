"""Cheap model-boundary/refusal checks before executing synthetic native DAX."""
from copy import deepcopy
import unittest

import bulkcells
import prepared
import strictcells


class BulkContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=strictcells.patch(prepared.adapter.patch_database(
            prepared.adapter.selection.original_database())[0])

    def test_exact_two_kernels_and_hidden_fallbacks_only(self):
        before=deepcopy(self.baseline)
        after=bulkcells.patch(before)
        old=prepared.adapter.planning.measures(before)
        now=prepared.adapter.planning.measures(after)
        self.assertEqual({n for n in old if now[n]!=old[n]},{'N Plan','N Benchmark'})
        for name in ('N Plan','N Benchmark'):
            fallback='P R03 '+name[2:]
            self.assertEqual(now[fallback]['expression'],old[name]['expression'])
            self.assertTrue(now[fallback]['isHidden'])
            now[name]['expression']=deepcopy(old[name]['expression'])
        rows=next(t for t in after['model']['tables'] if t['name']=='fm_native_measures')['measures']
        rows[:]=[m for m in rows if m['name'] not in {'P R03 Plan','P R03 Benchmark'}]
        self.assertEqual(after,before)
        self.assertEqual(before,self.baseline)

    def test_unknown_context_and_second_application_refused(self):
        changed=deepcopy(self.baseline)
        prepared.adapter.planning.measures(changed)['N Monthly Numerator']['expression']='0'
        with self.assertRaises(ValueError):
            bulkcells.patch(changed)
        with self.assertRaises(ValueError):
            bulkcells.patch(bulkcells.patch(self.baseline))

    def test_service_line_arrays_are_admitted(self):
        changed=deepcopy(self.baseline)
        for m in prepared.adapter.planning.measures(changed).values():
            if isinstance(m['expression'],str):
                m['expression']=m['expression'].splitlines()
        bulkcells.patch(changed)

    def test_fallback_graph_does_not_reenter_replaced_kernels(self):
        measures=prepared.adapter.planning.measures(bulkcells.patch(self.baseline))
        for name in ('P R03 Plan','P R03 Benchmark'):
            self.assertNotIn('[N Plan]',measures[name]['expression'])
            self.assertNotIn('[N Benchmark]',measures[name]['expression'])


if __name__=='__main__':
    unittest.main()
