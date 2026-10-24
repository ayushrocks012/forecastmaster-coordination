"""Source precision and missing-versus-zero regression at the CSV boundary."""
from pathlib import Path
import tempfile
import unittest

import pandas as pd

from precise_snapshot import read_round_trip


class PrecisionBoundary(unittest.TestCase):
    def test_exported_double_missing_zero_and_blank_sector(self):
        text='12371.739999999998'
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'facts.csv'
            path.write_text('"[SourceID]","[Sector]","[Amount]","[MissingCells]"\n'
                '"a","","'+text+'","0"\n"b","S","","1"\n"c","S","0","0"\n')
            frame=read_round_trip(path)
        self.assertEqual(frame.loc[0,'Amount'],float(text))
        self.assertEqual(frame.loc[0,'Sector'],'')
        self.assertTrue(pd.isna(frame.loc[1,'Amount']))
        self.assertEqual(frame.loc[2,'Amount'],0)
        self.assertFalse(pd.isna(frame.loc[2,'Amount']))
        self.assertEqual(frame.loc[1,'MissingCells'],1)


if __name__=='__main__':unittest.main()
