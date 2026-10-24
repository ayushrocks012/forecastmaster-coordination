"""Cost decomposition only; intentionally simplified queries are not acceptance."""
import hashlib
import json
from pathlib import Path
import shutil

import prepared

HERE = Path(__file__).resolve().parent


def build(destination, source):
    if destination.exists():
        raise ValueError('Preserve prior diagnostic attempts')
    frozen = json.loads((source / 'FROZEN-INPUTS.json').read_text())
    for name, sha in frozen['Files'].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Changed diagnostic source')
    cases = json.loads((source / 'queries.json').read_text())
    full = next(q['query'] for q in cases if q['name'] == 'market-expanded/full-core/candidate')
    scalar = next(q['query'] for q in cases if q['name'] == 'market/Units/candidate')
    start, end = scalar.index('ROW('), scalar.index(",'fm_review_files'[Country])")
    # Replace only the explicit ROW projection, preserving all scalar filters.
    scalar = scalar.replace('ROW("Monthly",[N Monthly],"Plan",[N Plan],"Benchmark",[N Benchmark],"Pct",[N Variance %])',
        'ROW("Eligible",[P Perf Eligible],"SourceOK",[N Source OK],"FastPlan",[P Fast Plan],"LegacyPlan",[P Legacy Plan])')
    if start < 0 or end < 0:
        raise ValueError('Unknown scalar projection')
    def define(query, declarations):
        if not query.startswith('DEFINE'):
            raise ValueError('Expected native DEFINE')
        return 'DEFINE\n' + declarations + '\n' + query[6:]
    constant = define(full, "MEASURE 'fm_native_measures'[P Perf Eligible]=1")
    dimension = constant
    for field in ('GrowthDriver', 'SectorLabel', 'Sector'):
        dimension = dimension.replace("'fm_native_scope'[" + field + ']', "'fm_perf_sector'[" + field + ']')
    blank_presentation = constant.replace("IGNORE('fm_native_measures'[_N Summary Cell FormatString])", 'BLANK()').replace(
        "IGNORE('fm_native_measures'[N GM Summary Color])", 'BLANK()')
    with open(source / 'candidate.json') as stream:
        db = json.load(stream)
    measures = prepared.adapter.planning.measures(db)
    strict = define(constant, "MEASURE 'fm_native_measures'[N Summary Cell]=" +
        prepared.adapter.selection.OLD.expression_text(measures['N Summary Cell']['expression']).replace('IF.EAGER(', 'IF('))
    queries = [{'model': 'candidate', 'name': n, 'query': q} for n, q in [
        ('admission-and-plan', scalar), ('full-original-dispatch', full),
        ('full-constant-eligible', constant), ('full-constant-physical-dimension', dimension),
        ('full-no-colour-format-diagnostic', blank_presentation), ('full-strict-cell-diagnostic', strict)]]
    destination.mkdir(parents=True)
    shutil.copy2(source / 'candidate.json', destination / 'candidate.json')
    (destination / 'queries.json').write_text(json.dumps(queries))
    runner = (HERE / 'run_profile.ps1').read_text().replace("@('baseline','candidate')", "@('candidate')")
    (destination / 'run_profile.ps1').write_text(runner)
    for path in (Path(__file__), prepared.R02 / 'launch_synthetic_engine.ps1'):
        shutil.copy2(path, destination / path.name)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files,
        'Kind': 'DIAGNOSTIC_NOT_ACCEPTANCE', 'SourceCandidateSHA256': files['candidate.json'],
        'Limits': 'Constant eligibility applies to this observed qualified context only. Removed presentation/strict variants are cost diagnostics, not a report acceptance pass.'}, indent=2))
    print(json.dumps({'Directory': str(destination), 'Queries': len(queries), 'Acceptance': False}))


if __name__ == '__main__':
    import sys
    build(Path(sys.argv[1]), Path(sys.argv[2]))
