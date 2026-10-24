"""Independent small arithmetic/blank boundaries for serving preparation."""
import csv
import math
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import cache_prepare


def write(path,rows):
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def inputs(directory,change=None):
    files=[{'SourceID':'S1','Country':'UK','Driver':'Driver test','IMS':24,'EF':25,'Currency':'GBP'}]
    catalog=[]
    for metric in ('market','abbott','pi','net','share'):
        for display in ('Units','Value'):
            catalog.append({'Metric':metric,'Display':display,
                'Component':('abbott' if metric=='share' else metric)+'-'+display,
                'Denominator':'market-'+display if metric=='share' else '',
                'Channel':'IMS','SubChannel':''})
    facts=[]
    for sector in ('A','B'):
        for month in range(36):
            for metric in cache_prepare.METRICS:
                for display in cache_prepare.DISPLAYS:
                    market=100+2*month
                    amount={'market':market,'abbott':market*.2+(1 if sector=='B' else 0),
                        'pi':4.0,'net':market*.2-4,'ef':50+3*month}[metric]
                    facts.append({'SourceID':'S1','Sector':sector,'Month':month,
                        'Component':'ef-ads-'+display.lower() if metric=='ef' else metric+'-'+display,
                        'Channel':'EF' if metric=='ef' else 'IMS','SubChannel':'',
                        'Amount':amount*(2 if display=='Value' else 1),'MissingCells':0})
    if change:
        change(facts)
    for name,rows in [('facts',facts),('files',files),('catalog',catalog)]:
        write(directory/(name+'.csv'),rows)


class PreparationContracts(unittest.TestCase):
    def prepare(self,change=None):
        with TemporaryDirectory() as temp:
            directory=Path(temp);inputs(directory,change)
            with patch('cache_prepare.export_sample.verify',return_value={'SmallIndependentTest':True}):
                return cache_prepare.prepare(directory)

    def test_linear_history_and_zero_slope(self):
        data=self.prepare()
        key=next(k for k,s,sector in data['dimension'] if sector=='A')
        rows={(k,m,d,w):(mean,slope,ready) for k,m,d,w,mean,slope,ready in data['statistics']}
        mean,slope,ready=rows[key,'market','Units',12]
        self.assertEqual(ready,1);self.assertAlmostEqual(mean,137);self.assertAlmostEqual(slope,2)
        mean,slope,ready=rows[key,'pi','Units',24]
        self.assertEqual((mean,slope,ready),(4.0,0.0,1))

    def test_zero_negative_and_blank_missing_flag_are_numeric(self):
        def change(rows):
            for row in rows:
                if row['Sector']=='A' and row['Component']=='market-Units':
                    if row['Month']==24:row['Amount']=0
                    if row['Month']==23:row['Amount']=-7
                    if row['Month']==22:row['MissingCells']=''
        data=self.prepare(change)
        values={(r[0],r[1]):r[2] for r in data['monthly']}
        key=next(k for k,s,sector in data['dimension'] if sector=='A')
        self.assertEqual(values[key,24],0);self.assertEqual(values[key,23],-7)
        self.assertEqual(values[key,22],144)

    def test_one_bad_duplicate_invalidates_entire_sector_month(self):
        def change(rows):
            duplicate=next(r for r in rows if r['Sector']=='A' and r['Month']==20 and r['Component']=='market-Units').copy()
            duplicate.update(Amount=1,MissingCells=1);rows.append(duplicate)
        data=self.prepare(change)
        key=next(k for k,s,sector in data['dimension'] if sector=='A')
        value=next(r[2] for r in data['monthly'] if r[:2]==(key,20))
        self.assertTrue(math.isnan(value))
        stats=next(r for r in data['statistics'] if r[:4]==(key,'market','Units',6))
        self.assertEqual(stats[-1],0)

    def test_share_is_fitted_per_month_not_ratio_of_annual_sums(self):
        data=self.prepare();key=next(k for k,s,sector in data['dimension'] if sector=='B')
        mean,slope,ready=next(r[4:] for r in data['statistics'] if r[:4]==(key,'share','Units',12))
        values=[(.2*(100+2*m)+1)/(100+2*m) for m in range(13,25)]
        expected=sum(values)/12
        expected_slope=sum((i-5.5)*(v-expected) for i,v in enumerate(values))/sum((i-5.5)**2 for i in range(12))
        self.assertEqual(ready,1);self.assertAlmostEqual(mean,expected);self.assertAlmostEqual(slope,expected_slope)


if __name__=='__main__':
    unittest.main()
