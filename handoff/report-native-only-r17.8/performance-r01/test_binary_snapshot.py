"""Independent rational proof of DOUBLE transport without numeric tolerance."""
from fractions import Fraction
import math
import unittest

from binary_snapshot import parts


class BinaryTransport(unittest.TestCase):
    def test_exact_rational_identity(self):
        for value in (0.,-0.,1.,-7.,12371.739999999998,1e200,-1e200,1e-200,math.ulp(0.)):
            with self.subTest(value=value):
                mantissa,exponent=parts(value)
                power=Fraction(2**exponent) if exponent>=0 else Fraction(1,2**(-exponent))
                self.assertEqual(Fraction(mantissa)*power,Fraction.from_float(value))
                self.assertLess(abs(mantissa),2**53)

    def test_missing_and_nonfinite(self):
        self.assertEqual(parts(None),(None,0))
        for value in (math.inf,-math.inf,math.nan):
            with self.assertRaises(ValueError):parts(value)


if __name__=='__main__':unittest.main()
