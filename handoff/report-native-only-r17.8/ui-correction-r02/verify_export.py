"""Check a fabricated SAMPLE05 native sector CSV against the Python oracle.

This is not a company-data reader or independent Excel parity check. Refuse
unrecognised labels/populations. Compare every exported formatted leaf value,
including actual-only omission, rather than checking a few visible cells.
"""
import csv
from decimal import Decimal, ROUND_HALF_UP
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_export_fixture', HERE / 'large_fixture.py')
fixture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fixture)


def values(driver, sector, year, kind, metric='market', display='Units', cycle='2026-10', window=12):
    cutoff = 36 + int(cycle[-2:]) - (2 if metric == 'ef' else 3)
    cut_month = cutoff % 12
    start, end = {'FY': (0, 12), 'YTD': (0, cut_month + 1), 'YTG': (cut_month + 1, 12)}[kind]
    months = range((year - 2023) * 12 + start, (year - 2023) * 12 + end)

    def numerator(month):
        return fixture.amount(cycle, driver, sector, month, 'abbott' if metric == 'share' else metric, display)

    def denominator(month):
        return fixture.amount(cycle, driver, sector, month, 'market', display)

    def monthly(month):
        return numerator(month) / denominator(month) if metric == 'share' else numerator(month)

    plan = sum(numerator(month) for month in months)
    if metric == 'share':
        plan /= sum(denominator(month) for month in months)
    if months[-1] <= cutoff:
        return {'Plan': plan}
    train = [monthly(month) for month in range(cutoff - window + 1, cutoff + 1)]
    mean, center = sum(train) / window, (window - 1) / 2
    slope = sum((i - center) * (v - mean) for i, v in enumerate(train)) / sum((i - center)**2 for i in range(window))

    def trend(month):
        return monthly(month) if month <= cutoff else mean + slope * (month - cutoff + center)

    benchmark = sum(trend(month) * denominator(month) for month in months) / sum(denominator(month) for month in months) if metric == 'share' else sum(trend(month) for month in months)
    variance = plan - benchmark
    return {'Plan': plan, f'{window}M variance': variance, f'{window}M variance %': variance / abs(benchmark)}


def formatted(value, percent=False, symbol=''):
    sign, magnitude = ('−' if value < 0 else ''), Decimal(str(abs(value)))
    def rounded(number, places):
        return number.quantize(Decimal(10) ** -places, rounding=ROUND_HALF_UP)
    if percent:
        return sign + f'{rounded(magnitude * 100, 1):.1f}%'
    number = f'{rounded(magnitude / 1000000, 2):,.2f}m' if magnitude >= 1000000 else f'{rounded(magnitude / 1000, 1):,.1f}k' if magnitude >= 1000 else f'{rounded(magnitude, 0):,.0f}'
    return sign + symbol + number


def verify(path, metric='market', display='Units'):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    expected = {}
    for driver in range(1, 6):
        for sector in range(1, 31):
            for year, kind in ((2026, 'FY'), (2026, 'YTD'), (2026, 'YTG'), (2027, 'FY')):
                for comparison, value in values(driver, sector, year, kind, metric, display).items():
                    key = (f'Driver {driver:02}', f'Sector {driver:02}.{sector:02} – Driver {driver:02}', f'{year} {kind}', comparison)
                    expected[key] = formatted(value, metric == 'share' or comparison.endswith('%'), '£' if display == 'Value' else '')
    actual = {}
    for row in rows:
        key = tuple(row[k] for k in ('Growth driver', 'Sector – growth driver', 'Review period', 'Comparison'))
        if key in actual:
            raise AssertionError('Duplicate fabricated export key')
        actual[key] = row['Value']
    if actual != expected:
        missing, extra = len(expected.keys() - actual.keys()), len(actual.keys() - expected.keys())
        mismatches = sum(actual[k] != expected[k] for k in expected.keys() & actual.keys())
        raise AssertionError({'Missing': missing, 'Extra': extra, 'Mismatches': mismatches})
    return {'Stage': 'LOCAL_FABRICATED_NATIVE_SECTOR_EXPORT_VERIFIED', 'Metric': metric, 'Display': display,
            'Drivers': 5, 'Sectors': 150, 'FormattedCells': len(expected), 'Mismatches': 0,
            'Scope': '2026-10; 12M; 2026 FY/YTD/YTG and 2027 FY', 'IndependentExcelParity': False}


if __name__ == '__main__':
    import json
    import sys
    print(json.dumps(verify(Path(sys.argv[1]), *(sys.argv[2:])), indent=2))
