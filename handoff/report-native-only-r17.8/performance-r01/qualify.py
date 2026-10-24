"""Exact generated R03 receiving queries plus corrected native boundary checks."""
import hashlib
import json
import math
from pathlib import Path
import shutil

import prepared
import regression
import edge_cases

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(destination, receiving, benchmark, runner_source):
    if destination.exists():
        raise ValueError('Preserve previous qualification')
    receiving_bound = json.loads((receiving / 'FROZEN-INPUTS.json').read_text())
    for name, sha in receiving_bound.items():
        if digest(receiving / name) != sha:
            raise ValueError('Receiving input changed')
    regression.checked(benchmark)
    regression.checked(runner_source)
    db = json.loads((receiving / 'candidate.json').read_text())
    if db != json.loads((benchmark / 'candidate.json').read_text()):
        raise ValueError('Different qualification and benchmark model')
    queries = json.loads((receiving / 'queries.json').read_text())
    expected = json.loads((receiving / 'expected.json').read_text())
    if len(queries) != 63 or len(expected) != 63:
        raise ValueError('Exact receiving query population changed')
    edges, edge_expected = edge_cases.build(prepared.adapter.planning.measures(db))
    destination.mkdir(parents=True)
    for name in ('candidate.json', 'launch_synthetic_engine.ps1'):
        shutil.copy2(receiving / name, destination / name)
    shutil.copy2(runner_source / 'run_profile.ps1', destination / 'run_profile.ps1')
    for path in (Path(__file__), HERE / 'edge_cases.py'):
        shutil.copy2(path, destination / path.name)
    (destination / 'queries.json').write_text(json.dumps(queries + edges))
    (destination / 'expected.json').write_text(json.dumps({'Receiving': expected, 'Boundaries': edge_expected}))
    files = {p.name: digest(p) for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files,
        'ReceivingInputs': receiving_bound, 'BenchmarkInputsSHA256': digest(benchmark / 'FROZEN-INPUTS.json'),
        'SameParsedModelAsBenchmark': True, 'Queries': 93, 'CompanyAcceptance': False,
        'BoundaryCorrection': 'Exact candidate cell bodies are also defined in query scope; two-query diagnostic proved stored cells did not pick up the virtual fake leaf substitutions.'}, indent=2))
    return {'Directory': str(destination), 'Queries': 93}


def verify(directory):
    binding = regression.checked(directory)
    expected = json.loads((directory / 'expected.json').read_text())
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    requested = json.loads((directory / 'queries.json').read_text())
    if len(results) != 93 or len({r['name'] for r in results}) != 93 or {r['name'] for r in results} != {q['name'] for q in requested}:
        raise AssertionError('Incomplete or duplicated qualification')
    failures = []
    def equal(left, right, boundary):
        if right is None:
            return left is None
        return isinstance(left, (int, float)) and not isinstance(left, bool) and \
            math.isclose(left, right, rel_tol=1e-12 if boundary else 1e-9, abs_tol=1e-12 if boundary else 1e-6)
    for row in results:
        boundary = row['name'] in expected['Boundaries']
        want = expected['Boundaries'][row['name']] if boundary else {'[V]': expected['Receiving'][row['name']]}
        actual = row.get('rows', [])
        if 'error' in row or len(actual) != 1 or set(actual[0]) != set(want) or any(not equal(actual[0][k], v, boundary) for k, v in want.items()):
            failures.append(row['name'])
    if failures:
        raise AssertionError(failures)
    return {'Stage': 'LOCAL_EXACT_RECEIVING_AND_BOUNDARY_QUERIES_VERIFIED',
        'Queries': 93, 'ExactReceivingQueries': 63, 'PairedComparisons': 30, 'NoFileBlankCases': 3,
        'ScalarBoundaryQueries': 30, 'BoundaryCells': 60, 'Mismatches': 0, 'FrozenInputsMatch': True,
        'SameParsedModelAsBenchmark': binding['SameParsedModelAsBenchmark'],
        'SourceHashes': binding['Files'], 'ReceivingInputHashes': binding['ReceivingInputs'],
        'ResultsSHA256': digest(directory / 'results.json'), 'TaskOwnedEngineClosed': True,
        'CompanyNumericalAcceptance': False, 'FabricatedOnly': True}


if __name__ == '__main__':
    import sys
    value = verify(Path(sys.argv[2])) if sys.argv[1] == 'verify' else build(*(Path(s) for s in sys.argv[2:6]))
    print(json.dumps(value, indent=2))
