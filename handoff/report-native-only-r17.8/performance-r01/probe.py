"""Freeze and compare a prepared-component prototype against SAMPLE05."""
import hashlib
import json
import math
from pathlib import Path
import shutil
from zipfile import ZipFile

import prepared

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(destination, sample, variant='prepared'):
    if destination.exists():
        raise ValueError('Preserve earlier attempts')
    destination.mkdir(parents=True)
    archive = sample / 'schema-candidate.zip'
    with ZipFile(archive) as source:
        name = next(n for n in source.namelist() if n.endswith('/model.bim'))
        baseline = json.loads(source.read(name))
    if baseline['model'].pop('defaultPowerBIDataSourceVersion', None) != 'powerBI_V3':
        raise ValueError('Unknown Desktop host routing hint')
    if variant not in ('prepared', 'vectorized', 'star', 'moments', 'pushdown', 'physical', 'cells', 'strictcells'):
        raise ValueError('Unknown isolated prototype variant')
    vector = prepared.load('perf_' + variant, HERE / (variant + '.py')) if variant != 'prepared' else None
    candidate = (vector.patch if vector else prepared.patch)(baseline)
    for db in (baseline, candidate):
        if any(p['source']['type'] != 'calculated' for t in db['model']['tables'] for p in t.get('partitions', [])):
            raise ValueError('Calculated fabricated models only')
    fixture = prepared.load('perf_fixture', prepared.R02 / 'large_fixture.py')
    cases = prepared.load('perf_cases', prepared.R02 / 'chart_cases.py')
    oracle = prepared.load('perf_oracle', prepared.R02 / 'matrix_cases.py')
    queries, expected = [], {}
    for row in ('market', 'share', 'ef'):
        for display in ('Units', 'Value'):
            filters = [cases.tf('fm_review_files', 'Country', ['UK']), cases.tf('fm_review_files', 'DemandCycle', ['2026-10']),
                cases.tf('fm_native_files', 'FileChoiceLabel', fixture.defaults()), cases.tf('fm_native_metric', 'RowID', [row]),
                cases.tf('fm_native_display', 'Display', [display]), cases.tf('fm_native_currency', 'Currency', ['Local']),
                cases.tf('fm_native_periods', 'PeriodKey', ['2026:FY']), cases.tf('fm_native_trend', 'Window', [12]),
                "TREATAS({DATE(2026,8,1)},'fm_review_axis'[Month])"]
            query = 'EVALUATE CALCULATETABLE(ROW("Monthly",[N Monthly],"Plan",[N Plan],"Benchmark",[N Benchmark],"Pct",[N Variance %]),' + ','.join(filters) + ')'
            for model in ('baseline', 'candidate'):
                queries.append({'name': row + '/' + display + '/' + model, 'model': model, 'query': query})
            values = oracle.oracle('2026-10', row, display, 0, 2026, 'FY', 12)
            monthly = oracle.total('2026-10', 'abbott' if row == 'share' else row, display, 0, 43)
            if row == 'share':
                monthly /= oracle.total('2026-10', 'market', display, 0, 43)
            expected[row + '/' + display] = {'[Monthly]': monthly, '[Plan]': values['plan'],
                '[Benchmark]': values['plan'] - values['variance'], '[Pct]': values['pct']}
    pa = sample / 'ez.json'
    events = json.loads(pa.read_text(encoding='utf-8-sig'))['events']
    executive = [e for e in events if e.get('name') == 'Execute DAX Query' and
                 '[N Summary Cell]' in e.get('metrics', {}).get('QueryText', '')]
    if len(executive) != 5:
        raise ValueError('Native query source population differs')
    for index, name in [(1, 'market-expanded'), (2, 'share-expanded')]:
        query = executive[index]['metrics']['QueryText']
        for portion, text in [('native-window', query), ('full-core', query[:query.index('\nEVALUATE')] + '\nEVALUATE __DS0Core')]:
            for model in ('baseline', 'candidate'):
                actual = text
                if variant in ('moments', 'physical') and model == 'candidate':
                    for field in ('GrowthDriver', 'SectorLabel', 'Sector'):
                        actual = actual.replace("'fm_native_scope'[" + field + ']', "'fm_perf_sector'[" + field + ']')
                queries.append({'name': name + '/' + portion + '/' + model, 'model': model, 'query': actual})
    queries.append({'name': 'prepared-population', 'model': 'candidate',
        'query': 'EVALUATE ROW("Facts",COUNTROWS(\'fm_review_facts\'),"Prepared",COUNTROWS(\'fm_perf_monthly\'))'})
    if variant in ('moments', 'physical'):
        queries[-1]['query'] = queries[-1]['query'][:-1] + ',"Share",COUNTROWS(\'fm_perf_share\'),"Sectors",COUNTROWS(\'fm_perf_sector\'))'
    if variant in ('pushdown', 'cells', 'strictcells'):
        queries[-1]['query'] = 'EVALUATE ROW("Facts",COUNTROWS(\'fm_review_facts\'),"Files",COUNTROWS(\'fm_native_files\'),"Scope",COUNTROWS(\'fm_native_scope\'),"Sectors",DISTINCTCOUNT(\'fm_native_scope\'[SectorLabel]))'
    for name, value in [('baseline', baseline), ('candidate', candidate), ('queries', queries), ('expected', expected)]:
        (destination / (name + '.json')).write_text(json.dumps(value, ensure_ascii=False))
    files = [Path(__file__), HERE / 'prepared.py', HERE / 'run_profile.ps1', prepared.R02 / 'launch_synthetic_engine.ps1']
    if vector:
        files.append(HERE / (variant + '.py'))
    if variant in ('moments', 'physical'):
        files.append(HERE / 'star.py')
    if variant == 'physical':
        files.append(HERE / 'moments.py')
    if variant == 'strictcells':
        files.append(HERE / 'cells.py')
    for path in files:
        shutil.copy2(path, destination / path.name)
    bound = {p.name: digest(p) for p in destination.iterdir() if p.is_file()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': bound,
        'SampleArchiveSHA256': digest(archive), 'NativeQuerySourceSHA256': digest(pa),
        'ExpectedPopulation': {'Files': 20, 'Cycles': 2, 'Drivers': 5, 'SectorsPerFile': 30,
                               'Sectors': 150, 'Months': 84, 'Facts': 504000},
        'Prototype': variant,
        'Semantics': 'Prepared monthly source/sector validity; unchanged period/trend/variance meaning; exact R02 fallback'}, indent=2))
    return {'Queries': len(queries), 'Directory': str(destination)}


def equal(left, right):
    if isinstance(left, (int, float)) and not isinstance(left, bool):
        return isinstance(right, (int, float)) and math.isclose(left, right, rel_tol=1e-9, abs_tol=1e-6)
    if isinstance(left, dict):
        return isinstance(right, dict) and set(left) == set(right) and all(equal(v, right[k]) for k, v in left.items())
    if isinstance(left, list):
        return isinstance(right, list) and len(left) == len(right) and all(equal(a, b) for a, b in zip(left, right))
    return type(left) is type(right) and left == right


def full_core_sets(sets):
    """Core query has no ORDER BY; compare complete, uniquely keyed cells."""
    dimensions = ['fm_native_scope[GrowthDriver]', 'fm_native_scope[SectorLabel]',
        'fm_native_periods[Label]', 'fm_native_periods[SortIndex]',
        'fm_native_columns[ColumnLabel]', 'fm_native_columns[Sort]',
        '[IsGrandTotalRowTotal]', '[IsDM1Total]']
    result = []
    for value in sets:
        rows = value['rows']
        def key(row):
            return tuple(json.dumps(row.get(k), ensure_ascii=True) for k in dimensions)
        keys = [key(row) for row in rows]
        if len(set(keys)) != len(keys):
            raise AssertionError('Duplicate complete matrix cell identity')
        result.append(dict(value, rows=sorted(rows, key=key)))
    return result


def sector_aliases(sets):
    """The moments prototype binds the equivalent physical sector dimension."""
    alias = lambda name: name.replace('fm_perf_sector[', 'fm_native_scope[')
    return [dict(s, columns=[alias(c) for c in s['columns']],
                 rows=[{alias(k): v for k, v in row.items()} for row in s['rows']]) for s in sets]


def verify(directory):
    frozen = json.loads((directory / 'FROZEN-INPUTS.json').read_text())
    if any(digest(directory / n) != h for n, h in frozen['Files'].items()):
        raise AssertionError('Frozen input changed')
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    requested = json.loads((directory / 'queries.json').read_text())
    expected = json.loads((directory / 'expected.json').read_text())
    by = {r['name']: r for r in results}
    if len(by) != len(results) or set(by) != {q['name'] for q in requested} or any('error' in r for r in results):
        raise AssertionError({'IncompleteOrFailed': [r for r in results if 'error' in r]})
    pairs = []
    for name, left in by.items():
        if not name.endswith('/baseline'):
            continue
        right = by[name[:-8] + 'candidate']
        left_sets, right_sets = left['resultSets'], right['resultSets']
        if frozen.get('Prototype') in ('moments', 'physical'):
            right_sets = sector_aliases(right_sets)
        if '/full-core/' in name:
            left_sets, right_sets = full_core_sets(left_sets), full_core_sets(right_sets)
        if not equal(left_sets, right_sets):
            raise AssertionError('Result/format/colour/row population mismatch: ' + name)
        key = name[:-9]
        if key in expected:
            if len(left['rows']) != 1 or not equal(expected[key], left['rows'][0]):
                raise AssertionError('Independent scalar oracle or nonblank admission: ' + key)
        elif not all(s['rows'] for s in left['resultSets']):
            raise AssertionError('Empty native matrix is not a performance pass: ' + key)
        if '/full-core/' in name:
            rows = left['rows']
            sectors = {r.get('fm_native_scope[SectorLabel]') for r in rows if r.get('fm_native_scope[SectorLabel]') is not None}
            if len(sectors) != 150:
                raise AssertionError('Expected all 150 sectors: ' + str(len(sectors)))
        pairs.append({'Query': name[:-9], 'BaselineMs': left['elapsedMs'], 'CandidateMs': right['elapsedMs'],
                      'ResultSetRows': [len(s['rows']) for s in left['resultSets']]})
    population = {'[Facts]': 504000, '[Prepared]': 504000}
    if frozen.get('Prototype') in ('moments', 'physical'):
        population.update({'[Share]': 100800, '[Sectors]': 150})
    if frozen.get('Prototype') in ('pushdown', 'cells', 'strictcells'):
        population = {'[Facts]': 504000, '[Files]': 20, '[Scope]': 600, '[Sectors]': 150}
    if by['prepared-population']['rows'] != [population]:
        raise AssertionError('Fact/prepared population changed')
    return {'Stage': 'LOCAL_PREPARED_COMPONENT_PROBE', 'Queries': len(results), 'ExactResultSetPairs': len(pairs),
            'Mismatches': 0, 'Pairs': pairs, 'Population': by['prepared-population']['rows'],
            'FrozenInputsMatch': True, 'CompanyPerformanceAcceptance': False,
            'ResultsSHA256': digest(directory / 'results.json')}


if __name__ == '__main__':
    import sys
    value = build(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4] if len(sys.argv) > 4 else 'prepared') if sys.argv[1] == 'build' else verify(Path(sys.argv[2]))
    print(json.dumps(value, indent=2))
