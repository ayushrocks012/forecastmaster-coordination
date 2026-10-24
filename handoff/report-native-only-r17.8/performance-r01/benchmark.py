"""Alternated, same-process native full-matrix benchmark with exact parity.

Repeated identical selections, no cache clearing or cold-cache claim. Three
pairs per metric are descriptive observations, not a p95 acceptance result.
"""
import hashlib
import json
from pathlib import Path
import shutil
import statistics

import prepared
import probe
import regression
import edge_cases

HERE = Path(__file__).resolve().parent


def build(destination, source, native_query_source):
    if destination.exists():
        raise ValueError('Preserve previous benchmark')
    binding = regression.checked(source)
    if binding.get('Prototype') not in ('cells', 'strictcells'):
        raise ValueError('Require source-bound shared-cell candidate')
    source_queries = json.loads((source / 'queries.json').read_text())
    if probe.digest(native_query_source) != binding['NativeQuerySourceSHA256']:
        raise ValueError('Changed native query capture')
    events = json.loads(native_query_source.read_text(encoding='utf-8-sig'))['events']
    executive = [e['metrics']['QueryText'] for e in events if e.get('name') == 'Execute DAX Query'
        and '[N Summary Cell]' in e.get('metrics', {}).get('QueryText', '')]
    headline = [e['metrics']['QueryText'] for e in events if e.get('name') == 'Execute DAX Query'
        and '[N Headline Cell]' in e.get('metrics', {}).get('QueryText', '')]
    if len(executive) != 5 or not headline:
        raise ValueError('Unknown native query population')
    queries = []
    for metric in ('market', 'share', 'drivers', 'review'):
        for repeat, order in enumerate((('baseline', 'candidate'), ('candidate', 'baseline'), ('baseline', 'candidate')), 1):
            for model in order:
                query = executive[0] if metric == 'drivers' else headline[0] if metric == 'review' else \
                    next(q['query'] for q in source_queries if q['name'] == metric + '-expanded/full-core/' + model)
                queries.append({'name': f'{metric}/{repeat}/{model}', 'model': model, 'query': query})
    measures = prepared.adapter.planning.measures(json.loads((source / 'candidate.json').read_text()))
    edges, edge_expected = edge_cases.build(measures)
    queries.extend(edges)
    destination.mkdir(parents=True)
    for name in ('baseline.json', 'candidate.json'):
        shutil.copy2(source / name, destination / name)
    (destination / 'queries.json').write_text(json.dumps(queries))
    (destination / 'edge-expected.json').write_text(json.dumps(edge_expected))
    runner = (HERE / 'run_profile.ps1').read_text().replace("@('QueryEnd','VertiPaqSEQueryEnd','DAXQueryPlan','ExecutionMetrics')", "@('QueryEnd')")
    (destination / 'run_profile.ps1').write_text(runner)
    for path in (Path(__file__), HERE / 'edge_cases.py', prepared.R02 / 'launch_synthetic_engine.ps1'):
        shutil.copy2(path, destination / path.name)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files,
        'Prototype': binding['Prototype'], 'SourceProbeSHA256': hashlib.sha256((source / 'FROZEN-INPUTS.json').read_bytes()).hexdigest(),
        'ExpectedQueries': len(queries), 'BenchmarkQueries': 24, 'ScalarBoundaryQueries': len(edges),
        'NativeQuerySourceSHA256': probe.digest(native_query_source),
        'CacheState': 'repeated_same_selection', 'CacheCleared': False,
        'Order': 'AB then BA then AB for each metric, one isolated process, serial',
        'Population': 'same 504000 facts / 20 files / 2 cycles / 5 drivers / all 150 sectors',
        'Limit': 'Three pairs per metric; not a p95 result or company/Desktop timing acceptance'}, indent=2))
    return {'Directory': str(destination), 'Queries': len(queries)}


def verify(directory, *, timing_only=False):
    binding = regression.checked(directory)
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    requested = json.loads((directory / 'queries.json').read_text())
    if len(results) != binding['ExpectedQueries'] or {r['name'] for r in results} != {q['name'] for q in requested} or any('error' in r for r in results):
        raise AssertionError('Incomplete or failed benchmark')
    by = {r['name']: r for r in results}
    trace = json.loads((directory / 'trace.json').read_text(encoding='utf-8-sig'))
    server_ends = {r['SessionID']: r for r in trace if r['EventClass'] == 'QueryEnd'}
    summary = {}
    for metric in ('market', 'share', 'drivers', 'review'):
        values = {'baseline': [], 'candidate': []}
        for repeat in range(1, 4):
            left, right = (by[f'{metric}/{repeat}/{model}'] for model in ('baseline', 'candidate'))
            lsets, rsets = left['resultSets'], right['resultSets']
            if metric in ('market', 'share'):
                lsets, rsets = probe.full_core_sets(lsets), probe.full_core_sets(rsets)
            if not probe.equal(lsets, rsets):
                raise AssertionError('Changed full value/format/colour population')
            sectors = {r.get('fm_native_scope[SectorLabel]') for r in left['rows'] if r.get('fm_native_scope[SectorLabel]') is not None}
            if metric in ('market', 'share') and len(sectors) != 150:
                raise AssertionError('Not all sectors')
            if metric in ('drivers', 'review') and not all(s['rows'] for s in lsets):
                raise AssertionError('Empty management query')
            for row in (left, right):
                server = server_ends.get(row['sessionID'])
                if server is None:
                    raise AssertionError('Missing server QueryEnd')
                values[row['model']].append({'ServerMs': server['Duration'], 'ReaderMs': row['elapsedMs'], 'ServerCPUMs': server['CpuTime']})
        old, new = (statistics.median(v['ServerMs'] for v in values[model]) for model in ('baseline', 'candidate'))
        summary[metric] = {'Runs': values, 'MedianBaselineServerMs': old, 'MedianCandidateServerMs': new,
            'MedianReductionPercent': round((1-new/old)*100, 1)}
    edge_expected = json.loads((directory / 'edge-expected.json').read_text())
    boundary_failures = [name for name, value in edge_expected.items() if by[name]['rows'] != [value]]
    if boundary_failures and not timing_only:
        raise AssertionError('Scalar boundaries failed: ' + str(boundary_failures))
    return {'Stage': 'LOCAL_ALTERNATED_SHARED_CELL_TIMING_COMPONENT' if timing_only else 'LOCAL_ALTERNATED_SHARED_CELL_BENCHMARK', 'Prototype': binding['Prototype'],
        'Queries': len(results), 'ExactFullMatrixPairs': 6, 'ExactCommonManagementPairs': 6,
        'TimingQueries': 24, 'ScalarBoundaryQueries': len(edge_expected), 'Sectors': 150, 'TimingMismatches': 0,
        'InitialScalarBoundaryFailures': boundary_failures,
        'BoundaryGatePassed': not boundary_failures, 'Mismatches': len(boundary_failures),
        'InitialQueryCacheState': 'Unmeasured; no explicit cache clearing or warmup. Three pairs include each model first observed query execution.',
        'Context': {k: binding[k] for k in ('CacheState', 'CacheCleared', 'Order', 'Population', 'Limit')},
        'Metrics': summary, 'SourceHashes': binding['Files'],
        'ResultsSHA256': probe.digest(directory / 'results.json'), 'TraceSHA256': probe.digest(directory / 'trace.json'),
        'CompanyPerformanceAcceptance': False, 'P95TargetVerified': False, 'TaskOwnedEngineClosed': True}


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2]), timing_only=sys.argv[1] == 'verify-timing') if sys.argv[1].startswith('verify') else build(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])), indent=2))
