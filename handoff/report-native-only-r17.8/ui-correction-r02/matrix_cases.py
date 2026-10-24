"""Independent generated-data oracle for complete mixed-period native matrices."""
from functools import lru_cache
import hashlib
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location('matrix_' + name, HERE / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


fixture, planning, gm, cases = [load(n) for n in ('large_fixture', 'matrix_planning', 'gm_presentation', 'chart_cases')]
tf = cases.tf


@lru_cache(None)
def total(cycle, metric, display, driver, month):
    drivers = [driver] if driver else range(1, 6)
    return sum(fixture.amount(cycle, d, sector, month, metric, display)
               for d in drivers for sector in range(1, 31))


def oracle(cycle, metric, display, driver, year, kind, window):
    cut = 36 + int(cycle[-2:]) - (2 if metric == 'ef' else 3)
    cut_month = cut % 12
    start, end = {'FY': (0, 12), 'YTD': (0, cut_month + 1), 'YTG': (cut_month + 1, 12),
                  'H1': (0, 6), 'H2': (6, 12)}[kind]
    months = list(range((year - 2023) * 12 + start, (year - 2023) * 12 + end))
    def num(month):
        return total(cycle, 'abbott' if metric == 'share' else metric, display, driver, month)
    def den(month):
        return total(cycle, 'market', display, driver, month)
    def value(month):
        return num(month) / den(month) if metric == 'share' else num(month)
    plan = sum(num(m) for m in months)
    if metric == 'share':
        plan /= sum(den(m) for m in months)
    if months[-1] <= cut:
        return {'plan': plan, 'variance': None, 'pct': None}
    train = [value(m) for m in range(cut - window + 1, cut + 1)]
    mean, center = sum(train) / window, (window - 1) / 2
    slope = sum((i - center) * (v - mean) for i, v in enumerate(train)) / sum((i - center)**2 for i in range(window))
    def trend(month):
        return value(month) if month <= cut else mean + slope * (month - cut + center)
    if metric == 'share':
        benchmark = sum(trend(m) * den(m) for m in months) / sum(den(m) for m in months)
    else:
        benchmark = sum(trend(m) for m in months)
    return {'plan': plan, 'variance': plan - benchmark, 'pct': (plan - benchmark) / abs(benchmark)}


def color(value):
    if value is None:
        return None
    return '#E5F2E6' if abs(value) <= .05 else '#FFF3CD' if abs(value) <= .10 else '#F9E1E3'


def build(directory, candidate):
    if directory.exists():
        raise ValueError('Preserve earlier attempts')
    directory.mkdir(parents=True)
    db, edits = planning.patch_database(json.loads(candidate.read_text()))
    (directory / 'candidate.json').write_text(json.dumps(db))
    definitions = 'DEFINE ' + '\n'.join("MEASURE 'fm_native_measures'[" + n + '] = ' + v for n, v in gm.MEASURES.items()) + '\n'
    periods = [f'{y}:{k}' for y in (2026, 2027) for k in ('FY', 'YTD', 'YTG', 'H1', 'H2')]
    queries, expected = [], {}
    for cycle in fixture.CYCLES:
        for metric in ('market', 'abbott', 'share', 'pi', 'net', 'ef'):
            for display in ('Units', 'Value'):
                for window in (6, 12, 24):
                    name = f'{cycle}/{metric}/{display}/{window}'
                    filters = [tf('fm_review_files', 'Country', ['UK']), tf('fm_review_files', 'DemandCycle', [cycle]),
                        tf('fm_native_files', 'FileChoiceLabel', fixture.defaults()), tf('fm_native_metric', 'RowID', [metric]),
                        tf('fm_native_metric', 'Section', ['Ex-factory' if metric == 'ef' else 'IMS / Market']),
                        tf('fm_native_display', 'Display', [display]), tf('fm_native_currency', 'Currency', ['Local']),
                        tf('fm_native_chart_trend', 'Window', [window]), tf('fm_native_trend', 'Window', [window]),
                        tf('fm_native_periods', 'PeriodKey', periods),
                        tf('fm_native_start_month', 'MonthLabel', ['Jan 2025']), tf('fm_native_end_month', 'MonthLabel', ['Dec 2027'])]
                    filt = ','.join(filters)
                    query = definitions + '''VAR _h=SUMMARIZECOLUMNS('fm_native_headline'[Key],'fm_native_periods'[PeriodKey],'''+filt+''',
 "V",[N Headline Cell],"C",IGNORE([N GM Review Color]))
VAR _s=SUMMARIZECOLUMNS('fm_native_scope'[GrowthDriver],'fm_native_columns'[ColumnKey],'fm_native_periods'[PeriodKey],'''+filt+''',
 "V",[N Summary Cell],"C",IGNORE([N GM Summary Color]))
EVALUATE UNION(SELECTCOLUMNS(_h,"Type","H","Driver","Total","Period",'fm_native_periods'[PeriodKey],
 "Key",'fm_native_headline'[Key],"Value",[V],"Color",[C]),
 SELECTCOLUMNS(_s,"Type","S","Driver",'fm_native_scope'[GrowthDriver],"Period",'fm_native_periods'[PeriodKey],
 "Key",'fm_native_columns'[ColumnKey],"Value",[V],"Color",[C]))'''
                    queries.append({'model': 'candidate', 'name': name, 'query': query})
                    want = {}
                    for period in periods:
                        year, kind = period.split(':')
                        for driver in range(6):
                            values = oracle(cycle, metric, display, driver, int(year), kind, window)
                            for key in ('plan', 'variance', 'pct'):
                                if values[key] is None:
                                    continue
                                rowkey = '|'.join(('S' if driver else 'H', f'Driver {driver:02}' if driver else 'Total', period,
                                                 ('plan' if key == 'plan' else f'{window}:' + ('abs' if key == 'variance' else 'pct')) if driver else key))
                                want[rowkey] = {'Value': values[key], 'Color': None if key == 'plan' else color(values['pct'])}
                    expected[name] = want
    first = queries[0]['query']
    for name, old, new in [('no-files', tf('fm_native_files', 'FileChoiceLabel', fixture.defaults()), "FILTER(ALL('fm_native_files'[FileChoiceLabel]),FALSE())"),
            ('no-metric', tf('fm_native_metric', 'RowID', ['market']), "FILTER(ALL('fm_native_metric'[RowID]),TRUE())"),
            ('incompatible-section', tf('fm_native_metric', 'Section', ['IMS / Market']), tf('fm_native_metric', 'Section', ['Ex-factory']))]:
        if first.count(old) != 2:
            raise ValueError('Unknown combined query shape')
        queries.append({'model': 'candidate', 'name': name, 'query': first.replace(old, new)})
        expected[name] = {}
    (directory / 'queries.json').write_text(json.dumps(queries))
    (directory / 'expected.json').write_text(json.dumps(expected))
    return {'Contexts': 72, 'AdmissionEdges': 3, 'CellEvaluationEdits': edits,
            'ExpectedValueAndColorCells': sum(len(v) for v in expected.values())}


def verify(directory):
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    expected = json.loads((directory / 'expected.json').read_text())
    failures, compared = [], 0
    if len(results) != len(expected) or {r['name'] for r in results} != set(expected):
        failures.append('Requested context population')
    for result in results:
        name = result['name']
        if 'error' in result:
            failures.append(name + ': native query failed'); continue
        actual = {}
        for row in result['rows']:
            key = '|'.join(str(row['[' + k + ']']) for k in ('Type', 'Driver', 'Period', 'Key'))
            if key in actual:
                failures.append(name + ': duplicate cell')
            actual[key] = {'Value': row.get('[Value]'), 'Color': row.get('[Color]')}
        if set(actual) != set(expected[name]):
            failures.append(name + ': exact cell/blank population'); continue
        for key, value in expected[name].items():
            got = actual[key]
            if not isinstance(got['Value'], (float, int)) or not math.isclose(got['Value'], value['Value'], rel_tol=1e-9, abs_tol=1e-7):
                failures.append(name + '/' + key + ': arithmetic')
            if got['Color'] != value['Color']:
                failures.append(name + '/' + key + ': alert')
            compared += 1
    receipt = {'Stage': 'LOCAL_MIXED_PERIOD_MATRICES', 'Contexts': 72, 'AdmissionEdges': 3,
        'IndependentValueAndColorCells': compared, 'Failures': failures, 'CompanyAcceptance': False,
        'SHA256': {f: hashlib.sha256((directory / f).read_bytes()).hexdigest()
                   for f in ('candidate.json', 'queries.json', 'expected.json', 'results.json')}}
    if failures:
        raise AssertionError(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1])) if '--verify' in sys.argv else
                     build(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
