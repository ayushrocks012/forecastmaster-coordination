"""Independent fabricated custom-chart values/context checks; no live access."""
from datetime import date
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


f = load('r178_chart_fixture', 'large_fixture.py')
c = load('r178_chart_context', 'chart_context.py')


def tf(table, column, values):
    # DAX strings use doubled quotes, not JSON backslash or Unicode escapes.
    def literal(value):
        return '"' + value.replace('"', '""') + '"' if isinstance(value, str) else str(value)
    return 'TREATAS({' + ','.join(literal(v) for v in values) + '},\'' + table + '\'[' + column + '])'


def build(directory, candidate):
    if directory.exists():
        raise ValueError('Preserve earlier attempts')
    directory.mkdir(parents=True)
    (directory / 'candidate.json').write_bytes(candidate.read_bytes())
    cases, expected = [], {}
    periods = [str(y) + ':' + kind for y in (2026, 2027) for kind in ('FY', 'YTD', 'YTG', 'H1', 'H2')]
    define = "DEFINE MEASURE 'fm_native_measures'[N Overlay Context] = " + c.EXPRESSION + '\n'
    for cycle in f.CYCLES:
        for metric in ('market', 'abbott', 'share', 'pi', 'net', 'ef'):
            for display in ('Units', 'Value'):
                cut = 36 + int(cycle[-2:]) - (2 if metric == 'ef' else 3)
                def total(mi, row):
                    return sum(f.amount(cycle, d, s, mi, row, display) for d in range(1, 6) for s in range(1, 31))
                def monthly(mi):
                    return total(mi, 'abbott') / total(mi, 'market') if metric == 'share' else total(mi, metric)
                for window in (6, 12, 24):
                    filters = [tf('fm_review_files', 'Country', ['UK']), tf('fm_review_files', 'DemandCycle', [cycle]),
                        tf('fm_native_files', 'FileChoiceLabel', f.defaults()), tf('fm_native_metric', 'RowID', [metric]),
                        tf('fm_native_metric', 'Section', ['Ex-factory' if metric == 'ef' else 'IMS / Market']),
                        tf('fm_native_display', 'Display', [display]), tf('fm_native_currency', 'Currency', ['Local']),
                        tf('fm_native_chart_trend', 'Window', [window]), tf('fm_native_lines', 'LineKind', [window]),
                        tf('fm_native_lines', 'ScopeLabel', ['Selected total']), tf('fm_native_lines', 'Chart', ['demand']),
                        tf('fm_native_lines', 'Mode', ['Automatic ADS']), tf('fm_native_view', 'View', ['Total']),
                        tf('fm_native_periods', 'PeriodKey', periods),
                        "TREATAS({DATE(2026,11,1)},'fm_review_axis'[Month])"]
                    query = define + "EVALUATE SUMMARIZECOLUMNS('fm_native_lines'[SeriesLabel]," + ','.join(filters) + ',"V",[N Chart Monthly],"C",[N Overlay Context])'
                    name = '/'.join((cycle, metric, display, str(window)))
                    ys = [monthly(mi) for mi in range(cut - window + 1, cut + 1)]
                    mean, center = sum(ys) / window, (window - 1) / 2
                    slope = sum((i - center) * (v - mean) for i, v in enumerate(ys)) / sum((i - center)**2 for i in range(window))
                    # November 2026 is zero-based month 46 from January 2023.
                    expected[name] = {'Value': mean + slope * (46 - cut + center),
                        'Cutoff': date(2023 + cut // 12, cut % 12 + 1, 1).strftime('%Y-%m'),
                        'Metric': metric, 'Display': display, 'Unit': '%' if metric == 'share' else 'Units' if display == 'Units' else 'GBP',
                        'Periods': periods}
                    cases.append({'model': 'candidate', 'name': name, 'query': query})
    # Do not group a disconnected metric/display column into the visual query:
    # that would manufacture HASONEVALUE when the user's selection is absent.
    first = cases[0]['query']
    remove = tf('fm_native_metric', 'RowID', ['market']) + ','
    cases.append({'model': 'candidate', 'name': 'no-metric-selection', 'query': first.replace(remove, '')})
    remove = tf('fm_native_files', 'FileChoiceLabel', f.defaults()) + ','
    cases.append({'model': 'candidate', 'name': 'no-file-selection', 'query': first.replace(remove, '')})
    cases.append({'model': 'candidate', 'name': 'incompatible-section', 'query': first.replace(
        tf('fm_native_metric', 'Section', ['IMS / Market']), tf('fm_native_metric', 'Section', ['Ex-factory']))})
    for name, data in [('queries', cases), ('expected', expected)]:
        (directory / (name + '.json')).write_text(json.dumps(data))
    return {'Contexts': len(expected), 'AdmissionEdges': 3}


def verify(directory, oracle_directory=None):
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    oracle_directory = oracle_directory or directory
    for filename in ('candidate.json', 'queries.json'):
        if (directory / filename).read_bytes() != (oracle_directory / filename).read_bytes():
            raise ValueError('Oracle correction cannot reuse changed native inputs')
    expected = json.loads((oracle_directory / 'expected.json').read_text())
    failures = []
    if len(results) != len(expected) + 3 or len({r['name'] for r in results}) != len(results):
        failures.append('Requested population')
    for result in results:
        name = result['name']
        if 'error' in result:
            failures.append(name + ': native query failed'); continue
        rows = result['rows']
        if name not in expected:
            if rows:
                failures.append(name + ': expected blank data, not manufactured selection')
            continue
        want = expected[name]
        if len(rows) != 1 or not isinstance(rows[0].get('[C]'), str):
            failures.append(name + ': one complete value/context required'); continue
        got = rows[0]
        if not math.isclose(got['[V]'], want['Value'], rel_tol=1e-9, abs_tol=1e-7):
            failures.append(name + ': independent trend/weighted-share mismatch')
        ctx = json.loads(got['[C]'])
        for key in ('cutoff', 'metric', 'display', 'unit'):
            if ctx.get(key) != want[key.title()]:
                failures.append(name + '/' + key)
        bounds = {p['id']: p for p in ctx['periods']}
        if set(bounds) != set(want['Periods']):
            failures.append(name + ': selected period population')
        cut_month = int(want['Cutoff'][-2:])
        for key, p in bounds.items():
            year, kind = key.split(':'); y = int(year)
            start = cut_month + 1 if kind == 'YTG' else 7 if kind == 'H2' else 1
            end = cut_month if kind == 'YTD' else 6 if kind == 'H1' else 12
            if p['start'] != f'{y}-{start:02}' or p['end'] != f'{y}-{end:02}':
                failures.append(name + '/' + key + ': named-year shading boundary')
    receipt = {'Stage': 'LOCAL_CUSTOM_CHART_VALUES_AND_CONTEXT', 'FabricatedOnly': True,
        'Contexts': len(expected), 'AdmissionEdges': 3, 'Failures': failures,
        'CompanyAcceptance': False}
    if failures:
        raise AssertionError(json.dumps(receipt))
    return receipt


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[1]), Path(sys.argv[sys.argv.index('--oracle') + 1]) if '--oracle' in sys.argv else None) if '--verify' in sys.argv else
                     build(Path(sys.argv[1]), Path(sys.argv[2])), indent=2))
