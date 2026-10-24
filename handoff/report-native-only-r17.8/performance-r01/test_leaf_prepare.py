"""Independent small numerical checks for prepared leaf periods."""
import unittest

import numpy as np

from leaf_prepare import values


class LeafArithmetic(unittest.TestCase):
    def test_linear_future_and_weighted_share(self):
        dates=np.array([0,1,2])
        self.assertEqual(values([5,7,999],None,dates,1,6,2,2,False),(1011.,21.))
        plan,bench=values([10,20,90],[100,200,300],dates,1,.1,.02,2,True)
        self.assertAlmostEqual(plan,.2)
        self.assertAlmostEqual(bench,69/600)
        self.assertNotAlmostEqual(bench,(.1+.1+.13)/3)

    def test_missing_future_plan_does_not_invalidate_additive_benchmark(self):
        dates=np.array([0,1,2])
        plan,bench=values([5,7,np.nan],None,dates,1,6,2,2,False)
        self.assertIsNone(plan);self.assertEqual(bench,21.)
        self.assertEqual(values([np.nan,7,9],None,dates,1,6,2,2,False),(None,None))
        self.assertEqual(values([10,20,30],[100,200,np.nan],dates,1,.1,0,2,True),(None,None))

    def test_known_zero_negative_and_no_fit_for_actual_only(self):
        dates=np.array([0,1])
        self.assertEqual(values([0,0],None,dates,1,None,None,12,False),(0.,0.))
        self.assertEqual(values([-5,-7],None,dates,1,None,None,12,False),(-12.,-12.))
        self.assertEqual(values([0,0],[0,0],dates,1,None,None,12,True),(None,None))
        self.assertEqual(values([1,2],None,dates,0,None,None,12,False),(3.,None))

    def test_empty_period_and_zero_denominator(self):
        self.assertEqual(values([],None,np.array([],dtype=int),0,1,0,6,False),(None,None))
        self.assertEqual(values([1,2],[1,-1],np.array([0,1]),1,1,0,6,True),(None,None))


if __name__=='__main__':unittest.main()
