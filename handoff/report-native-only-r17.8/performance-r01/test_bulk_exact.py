"""Bound the complete arithmetic rewrite to two expressions and known R03."""
from copy import deepcopy
import unittest

import bulk_exact
import prepared
import strictcells


class ExactContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.baseline=strictcells.patch(prepared.adapter.patch_database(
            prepared.adapter.selection.original_database())[0])

    def test_only_two_expressions_change_and_input_is_immutable(self):
        before=deepcopy(self.baseline);after=bulk_exact.patch(before)
        old=prepared.adapter.planning.measures(before);now=prepared.adapter.planning.measures(after)
        self.assertEqual({n for n in old if now[n]!=old[n]},{'N Plan','N Benchmark'})
        self.assertEqual(set(now),set(old))
        for n in ('N Plan','N Benchmark'):
            now[n]['expression']=deepcopy(old[n]['expression'])
        self.assertEqual(after,before);self.assertEqual(before,self.baseline)

    def test_unknown_numerical_dependency_refused(self):
        before=deepcopy(self.baseline)
        prepared.adapter.planning.measures(before)['N Monthly Numerator']['expression']='0'
        with self.assertRaises(ValueError):bulk_exact.patch(before)

    def test_service_arrays_and_reapplication_refusal(self):
        before=deepcopy(self.baseline)
        for m in prepared.adapter.planning.measures(before).values():
            if isinstance(m['expression'],str):m['expression']=m['expression'].splitlines()
        candidate=bulk_exact.patch(before)
        with self.assertRaises(ValueError):bulk_exact.patch(candidate)

    def test_no_reference_to_old_monthly_fit_or_fallback_numerical_graph(self):
        measures=prepared.adapter.planning.measures(bulk_exact.patch(self.baseline))
        for name in ('N Plan','N Benchmark'):
            for dependency in ('N Monthly','N Monthly Numerator','N Monthly Denominator','N Fit Mean','N Fit Slope','N Plan','N Benchmark'):
                self.assertNotIn('['+dependency+']',measures[name]['expression'])


if __name__=='__main__':
    unittest.main()
