"""Exact selected-file regression contexts plus preserved independent arithmetic."""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('r178_ui_cases_model', HERE / 'model.py')
old = load('r178_ui_old_cases', HERE.parent / 'test-release-r01/native_cases.py')
def tf(table, column, values):
    # DAX {} is a zero-column table, so TREATAS({}, one_column) cannot compile.
    if not values:
        return "FILTER(ALL('" + table + "'[" + column + ']),FALSE())'
    return old.tf(table, column, values)
DEFAULTS = '''TREATAS(SELECTCOLUMNS(FILTER(ALL('fm_native_files'),
 'fm_native_files'[ADSPriority]>0&&'fm_native_files'[PreferenceRank]=1
 &&'fm_native_files'[PreferenceTies]=1),"Label",'fm_native_files'[FileChoiceLabel]),
 'fm_native_files'[FileChoiceLabel])'''


def build(directory):
    if directory.exists():
        raise ValueError('Use a new directory; freeze each engine input population')
    with TemporaryDirectory() as temp:
        d = Path(temp)
        old.build(d)
        cases = [v for v in json.loads((d / 'queries.json').read_text()) if v['name'].startswith('numeric/')]
        expected = json.loads((d / 'expected.json').read_text())
    # Same complete numeric population and independent oracle; current R01
    # automatic baseline versus R02 explicitly selected preferred ADS files.
    for case in cases:
        if case['model'] == 'candidate':
            anchor = tf('fm_review_files', 'Country', ['UK'])
            if case['query'].count(anchor) != 1:
                raise ValueError('Numeric query structure drift')
            case['query'] = case['query'].replace(anchor, DEFAULTS + ',' + anchor)
    baseline = m.original_database()
    candidate, _ = m.patch_database(baseline)
    for db in (baseline, candidate):
        db['name'] = db['id'] = 'ForecastMasterNativeSyntheticR178R02'
        db['model'].pop('defaultPowerBIDataSourceVersion', None)
    filters = old.SHARED + [tf('fm_native_metric', 'RowID', ['market']),
        tf('fm_native_display', 'Display', ['Units']), tf('fm_native_periods', 'PeriodKey', ['2026:FY'])]

    def add(name, query):
        cases.append({'name': name, 'model': 'candidate', 'query': query})

    for picked, extra in (('default', [DEFAULTS]), ('clear', []), ('empty', [tf('fm_native_files', 'FileChoiceLabel', [])])):
        f = filters + extra
        add('selection/' + picked, 'EVALUATE CALCULATETABLE(ROW("Plan",[N Plan],"OK",[N Source OK],'
            '"Headline",CALCULATE([N Headline Cell],' + tf('fm_native_headline', 'Key', ['plan']) + ')), ' + ','.join(f) + ')')
        add('summary/' + picked, "EVALUATE SUMMARIZECOLUMNS('fm_native_scope'[GrowthDriver],"
            "'fm_native_scope'[SectorLabel],'fm_native_periods'[Label],'fm_native_columns'[ColumnLabel],"
            + ','.join(f + [tf('fm_native_trend', 'Window', [6, 12])]) + ',"V",[N Summary Cell])')
    # Real selector binding: both file picker and driver now use native_files.
    for driver in ('Example Oral', 'Example Paed'):
        add('files/' + driver, "EVALUATE SUMMARIZECOLUMNS('fm_native_files'[GrowthDriver],"
            "'fm_native_files'[FileChoiceLabel]," + ','.join(old.SHARED + [tf('fm_native_files', 'GrowthDriver', [driver])])
            + ',"Available",[N File Available])')
        add('driver/' + driver, 'EVALUATE CALCULATETABLE(ROW("V",[N Plan]),' + ','.join(filters + [DEFAULTS,
            tf('fm_native_files', 'GrowthDriver', [driver])]) + ')')
    for section, metric, key in [('Ex-factory', 'Market', 'invalid'), ('Ex-factory', 'Ex-factory ADS', 'valid-ef')]:
        f = old.SHARED + [DEFAULTS, tf('fm_native_metric', 'Section', [section]),
            tf('fm_native_metric', 'MetricLabel', [metric]), tf('fm_native_periods', 'PeriodKey', ['2026:FY'])]
        add('metric/' + key, 'EVALUATE CALCULATETABLE(ROW("Headline",CALCULATE([N Headline Cell],'
            + tf('fm_native_headline', 'Key', ['plan']) + ')), ' + ','.join(f) + ')')
    for view in ('Total', 'Drivers', 'Sectors'):
        for picked, extra in (('default', [DEFAULTS]), ('clear', [])):
            f = old.SHARED + extra + [tf('fm_native_metric', 'RowID', ['market']),
                tf('fm_native_display', 'Display', ['Units']), tf('fm_native_view', 'View', [view]),
                tf('fm_native_chart_trend', 'Window', [12]), tf('fm_native_lines', 'Chart', ['demand']),
                "TREATAS({DATE(2026,8,1),DATE(2026,9,1),DATE(2026,12,1)},'fm_review_axis'[Month])"]
            add('chart/' + view + '/' + picked, "EVALUATE SUMMARIZECOLUMNS('fm_native_lines'[SeriesLabel],"
                "'fm_native_lines'[LineKind],'fm_review_axis'[Month]," + ','.join(f) + ',"V",[N Chart Monthly])')
    labels = "SELECTCOLUMNS(FILTER(ALL('fm_native_files'),'fm_native_files'[SourceRevisionID] IN {\"UK-a\",\"UK-a-review\"}),\"L\",[FileChoiceLabel])"
    add('ambiguous', 'EVALUATE CALCULATETABLE(ROW("V",[N Plan],"OK",[N Source OK]),' + ','.join(filters + [
        "TREATAS(" + labels + ",'fm_native_files'[FileChoiceLabel])"]) + ')')
    add('default-labels', "EVALUATE SELECTCOLUMNS(FILTER(ALL('fm_native_files'),[ADSPriority]>0&&"
        '[PreferenceRank]=1&&[PreferenceTies]=1),"L",[FileChoiceLabel])')
    directory.mkdir(parents=True)
    for name, value in [('baseline', baseline), ('candidate', candidate), ('queries', cases), ('expected', expected)]:
        (directory / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False))
    return {'Queries': len(cases), 'IndependentOracleCases': len(expected)}


def verify(directory, corrected_empty=None):
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    cases = json.loads((directory / 'queries.json').read_text())
    expected = json.loads((directory / 'expected.json').read_text())
    correction_binding = None
    if corrected_empty is not None:
        # Reuse only the unchanged successful contexts, keeping the failed
        # checker queries/results intact in their original evidence directory.
        if (directory / 'candidate.json').read_bytes() != (corrected_empty / 'candidate.json').read_bytes():
            raise ValueError('Empty-filter correction uses a different candidate')
        corrected_queries = json.loads((corrected_empty / 'queries.json').read_text())
        corrected_results = json.loads((corrected_empty / 'results.json').read_text(encoding='utf-8-sig'))
        names = {'selection/empty', 'summary/empty'}
        if {c['name'] for c in corrected_queries} != names or len(corrected_queries) != 2:
            raise ValueError('Only the two malformed empty-filter checker contexts may be repaired')
        by_query = {c['name']: c for c in cases}
        for c in corrected_queries:
            prior = by_query[c['name']]
            before = "TREATAS({},'fm_native_files'[FileChoiceLabel])"
            if prior['query'].count(before) != 1 or c != dict(prior, query=prior['query'].replace(before, tf('fm_native_files', 'FileChoiceLabel', []))):
                raise ValueError('Correction changed more than the typed empty filter')
        replacement = {(r['name'], r['model']): r for r in corrected_results}
        if len(replacement) != 2 or {r['name'] for r in corrected_results} != names:
            raise ValueError('Correction results incomplete')
        for r in results:
            if r['name'] in names and 'number of columns in the input table (0)' not in r.get('error', ''):
                raise ValueError('Expected original checker compilation failure is absent')
        results = [replacement.get((r['name'], r['model']), r) for r in results]
        correction_binding = {'OriginalCheckerCompilationFailures': sorted(names),
            'AdditionalExecutedQueries': 2, 'OnlyChange': 'Typed one-column empty filter',
            'SHA256': {f: hashlib.sha256((corrected_empty / f).read_bytes()).hexdigest()
                       for f in ('candidate.json', 'queries.json', 'results.json')}}
    by = {(r['name'], r['model']): r for r in results}
    failures, checks = [], []

    def check(ok, label):
        checks.append(label)
        if not ok:
            failures.append(label)

    def rows(name, model='candidate'):
        return by.get((name, model), {}).get('rows', [])

    def close(a, b):
        return a is None and b is None or isinstance(a, (int, float)) and isinstance(b, (int, float)) and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)

    check(len(by) == len(cases) == len(results), 'Exact query population')
    for key, result in by.items():
        check('error' not in result, str(key) + ': ' + result.get('error', ''))
    for name, values in expected.items():
        for model in ('baseline', 'candidate'):
            got = rows(name, model)
            check(len(got) == 1, name + '/' + model + ' cardinality')
            for column, want in values.items():
                check(bool(got) and close(got[0].get(column), want), name + '/' + model + '/' + column)
        check(rows(name, 'baseline') == rows(name), name + ' explicit ADS/baseline exact parity')
    for key in ('clear', 'empty'):
        got = rows('selection/' + key)
        check(len(got) == 1 and got[0].get('[Plan]') is None and got[0].get('[Headline]') is None
              and got[0].get('[OK]') == 0, key + ' means unavailable, not automatic')
        check(not rows('summary/' + key), key + ' Executive blank')
    got = rows('selection/default')
    check(bool(got) and got[0].get('[Plan]') is not None and got[0].get('[OK]') == 1, 'Visible ADS defaults admitted')
    summary = rows('summary/default')
    check(bool(summary) and {r['fm_native_columns[ColumnLabel]'] for r in summary} ==
          {'Plan', '6M variance', '6M variance %', '12M variance', '12M variance %'}, 'Two Executive trends without Scenario row')
    check({r['fm_native_scope[GrowthDriver]'] for r in summary} == {'Example Oral', 'Example Paed'}, 'Both driver levels populated')
    for driver in ('Example Oral', 'Example Paed'):
        got = rows('files/' + driver)
        check(bool(got) and all(r['fm_native_files[GrowthDriver]'] == driver for r in got), driver + ' file scope')
        check(bool(rows('driver/' + driver)) and rows('driver/' + driver)[0].get('[V]') is not None, driver + ' amount context')
    check(rows('metric/invalid') == [{'[Headline]': None}], 'Invalid Section/Measure stays unavailable')
    check(bool(rows('metric/valid-ef')) and rows('metric/valid-ef')[0].get('[Headline]') is not None, 'Valid Ex-factory context is numeric')
    for view in ('Total', 'Drivers', 'Sectors'):
        got = rows('chart/' + view + '/default')
        check(bool(got) and {r['fm_native_lines[LineKind]'] for r in got} == {0, 1, 12}, view + ' chart actual/forecast/trend')
        check(not rows('chart/' + view + '/clear'), view + ' chart clear blank')
    got = rows('ambiguous')
    check(bool(got) and got[0].get('[V]') is None and got[0].get('[OK]') == 0, 'Alternative versions never summed')
    inputs = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in directory.glob('*.json') if p.name != 'results.json'}
    receipt = {'Stage': 'LOCAL_R178_R02_NATIVE_CHECKS', 'Queries': len(cases), 'Assertions': len(checks),
               'Failures': failures, 'InputSHA256': inputs, 'FabricatedOnly': True,
               'CompanyNumericalUIAndSpeedAcceptance': False}
    if correction_binding:
        receipt['CheckerCorrection'] = correction_binding
    if failures:
        raise AssertionError(json.dumps(receipt, indent=2))
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('directory', type=Path)
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--corrected-empty', type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(args.directory, args.corrected_empty) if args.verify else build(args.directory), indent=2))
