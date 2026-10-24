"""Qualify the exact generated receiving queries on the fabricated native engine."""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import runpy
import shutil
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
R02ROOT = HERE.parents[1] / 'ui-correction-r02'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def build(directory, sample_archive):
    if directory.exists():
        raise ValueError('Preserve prior native attempts')
    directory.mkdir(parents=True)
    cell = HERE / 'INSTALL AND PREPARE PRIVATE TEST R03.py'
    ns = runpy.run_path(str(cell), run_name='r178_native_test')
    fixture = load('r178_receiving_fixture', R02ROOT / 'large_fixture.py')
    oracle = load('r178_receiving_oracle', R02ROOT / 'matrix_cases.py')
    with ZipFile(sample_archive) as archive:
        model = next(n for n in archive.namelist() if n.endswith('/model.bim'))
        raw_model = archive.read(model)
        database = json.loads(raw_model)
        if any(p['source']['type'] != 'calculated' for t in database['model']['tables'] for p in t.get('partitions', [])):
            raise ValueError('Refuse a non-calculated fabricated fixture')
        # The Desktop-only routing hint requests MEngineHelper in the standalone
        # server. The existing synthetic harness removes this same property.
        if database['model'].pop('defaultPowerBIDataSourceVersion', None) not in (None, 'powerBI_V3'):
            raise ValueError('Unexpected Desktop-only data-source version')
        (directory / 'candidate.json').write_text(json.dumps(database))
        (directory / 'HOST-METADATA-ADAPTATION.json').write_text(json.dumps({
            'OriginalDesktopBIMSHA256': hashlib.sha256(raw_model).hexdigest(),
            'RemovedForIsolatedCalculatedEngine': ['model.defaultPowerBIDataSourceVersion'],
            'DAXExpressionsOrFormatsChanged': False}, indent=2))
    label = next(s for s in fixture.defaults() if 'Driver_01_2026-10_' in s)
    scope = {'Country': 'UK', 'Cycle': '2026-10', 'Driver': 'Driver 01', 'Scenario': 'ADS', 'Label': label}
    cases = list(ns['scalar_queries'](scope))
    original = 'DEFINE\n' + '\n'.join("MEASURE 'fm_native_measures'[" + name + '] = ' + ns['expression_text'](ns['EXPECTED_NATIVE'][name]['expression']) for name in ns['EXPRESSION_PATCHES']) + '\n'
    queries, expected = [], {}
    for i, (check, query) in enumerate(cases, 1):
        metric = check['Metric']
        values = oracle.oracle('2026-10', metric, 'Units', 1, 2026, 'FY', 12)
        measure = check['Measure']
        if measure == 'N Trend Monthly':
            cutoff = 44 if metric == 'ef' else 43
            def monthly(month):
                numerator = oracle.total('2026-10', 'abbott' if metric == 'share' else metric, 'Units', 1, month)
                return numerator / oracle.total('2026-10', 'market', 'Units', 1, month) if metric == 'share' else numerator
            train = [monthly(m) for m in range(cutoff - 11, cutoff + 1)]
            mean = sum(train) / 12
            slope = sum((i - 5.5) * (v - mean) for i, v in enumerate(train)) / sum((i - 5.5)**2 for i in range(12))
            want = mean + slope * (59 - cutoff + 5.5)
        elif measure == 'N Benchmark':
            want = values['plan'] - values['variance']
        elif measure == 'N Variance %' or 'pct' in check['Variant']:
            want = values['pct']
        elif 'variance' in check['Variant'] or '12:abs' in check['Variant']:
            want = values['variance']
        else:
            want = values['plan']
        for kind, prefix in [('original', original), ('candidate', '')]:
            name = kind + '/' + str(i) + '/' + metric + '/' + measure
            queries.append({'model': 'candidate', 'name': name, 'query': prefix + query})
            expected[name] = want
    for metric in ('market', 'ef', 'share'):
        query = next(q for check, q in cases if check['Metric'] == metric and check['Measure'] == 'N Plan')
        selected = 'TREATAS({"' + label.replace('"', '""') + """"},'fm_native_files'[FileChoiceLabel])"""
        if query.count(selected) != 1:
            raise ValueError('Generated file filter changed')
        name = 'no-files/' + metric
        queries.append({'model': 'candidate', 'name': name, 'query': query.replace(',' + selected, '')})
        expected[name] = None
    (directory / 'queries.json').write_text(json.dumps(queries))
    (directory / 'expected.json').write_text(json.dumps(expected))
    bound = {}
    for path in (cell, Path(__file__), R02ROOT / 'matrix_cases.py', R02ROOT / 'large_fixture.py', R02ROOT / 'run_large_engine.ps1', R02ROOT / 'launch_synthetic_engine.ps1'):
        target = directory / path.name
        shutil.copy2(path, target)
        bound[path.name] = hashlib.sha256(target.read_bytes()).hexdigest()
    for name in ('candidate.json', 'queries.json', 'expected.json', 'HOST-METADATA-ADAPTATION.json'):
        bound[name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    (directory / 'FROZEN-INPUTS.json').write_text(json.dumps(bound, indent=2))
    return {'Queries': len(queries), 'PairedComparisons': len(cases), 'NoFileBlankCases': 3}


def verify(directory):
    bound = json.loads((directory / 'FROZEN-INPUTS.json').read_text())
    if any(hashlib.sha256((directory / n).read_bytes()).hexdigest() != h for n, h in bound.items()):
        raise AssertionError('Frozen input differs')
    expected = json.loads((directory / 'expected.json').read_text())
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    if len(results) != len(expected) or {r['name'] for r in results} != set(expected):
        raise AssertionError('Native receiving-query population incomplete')
    failures = []
    for result in results:
        rows = result.get('rows', [])
        if 'error' in result or len(rows) != 1 or len(rows[0]) != 1:
            failures.append(result['name'])
            continue
        actual = next(iter(rows[0].values()))
        want = expected[result['name']]
        if not (actual is None and want is None or actual is not None and want is not None and math.isclose(actual, want, rel_tol=1e-9, abs_tol=1e-6)):
            failures.append(result['name'])
    if failures:
        raise AssertionError(failures)
    return {'Stage': 'LOCAL_EXACT_RECEIVING_SCALAR_QUERIES_VERIFIED', 'Queries': len(results),
            'PairedComparisons': 30, 'NoFileBlankCases': 3, 'Mismatches': 0, 'FrozenInputsMatch': True,
            'FabricatedOnly': True, 'CompanyNumericalAcceptance': False,
            'SHA256': dict(bound, **{'results.json': hashlib.sha256((directory / 'results.json').read_bytes()).hexdigest()})}


if __name__ == '__main__':
    import sys
    value = build(Path(sys.argv[2]), Path(sys.argv[3])) if sys.argv[1] == 'build' else verify(Path(sys.argv[2]))
    print(json.dumps(value, indent=2))
