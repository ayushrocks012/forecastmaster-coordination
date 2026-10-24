"""Diagnostic only: quantify metadata/dispatch guard cost on fixed fake scope.

Constants are valid only for the frozen UK/2026-10 Market/Share sample query.
This cannot qualify a report or be used against company data.
"""
import hashlib
import json
from pathlib import Path
import shutil

import prepared

HERE = Path(__file__).resolve().parent


def build(destination, source):
    if destination.exists():
        raise ValueError('Preserve prior diagnostic attempts')
    bound = json.loads((source / 'FROZEN-INPUTS.json').read_text())
    if bound.get('Prototype') != 'physical':
        raise ValueError('Physical fabricated candidate required')
    for name, sha in bound['Files'].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Changed source')
    population = json.loads((source / 'queries.json').read_text())
    queries = []
    for metric in ('market', 'share'):
        full = next(q['query'] for q in population if q['name'] == metric + '-expanded/full-core/candidate')
        if not full.startswith('DEFINE'):
            raise ValueError('Expected native DEFINE')
        def define(declarations):
            return 'DEFINE\n' + declarations + '\n' + full[6:]
        source_constants = '''MEASURE 'fm_native_measures'[N Source OK]=1
MEASURE 'fm_native_measures'[N Cutoff]=DATE(2026,8,1)
MEASURE 'fm_native_measures'[N Fit Cutoff]=DATE(2026,8,1)'''
        variants = [('original', full), ('constant-source-guards', define(source_constants)),
            ('constant-source-and-dispatch', define(source_constants + "\nMEASURE 'fm_native_measures'[P Perf Eligible]=1"))]
        for label, query in variants:
            queries.append({'name': metric + '/' + label, 'model': 'candidate', 'query': query})
    destination.mkdir(parents=True)
    shutil.copy2(source / 'candidate.json', destination / 'candidate.json')
    (destination / 'queries.json').write_text(json.dumps(queries))
    (destination / 'run_profile.ps1').write_text((HERE / 'run_profile.ps1').read_text().replace("@('baseline','candidate')", "@('candidate')"))
    for path in (Path(__file__), prepared.R02 / 'launch_synthetic_engine.ps1'):
        shutil.copy2(path, destination / path.name)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files,
        'Kind': 'DIAGNOSTIC_NOT_ACCEPTANCE', 'ExpectedScope': 'Fabricated UK/2026-10, all preferred ADS, Market/Share, common IMS cutoff August 2026',
        'Limit': 'Constant guards do not test missing files, collisions, invalid/mixed cutoffs or other contexts. No report readiness claim.'}, indent=2))
    return {'Queries': len(queries), 'Directory': str(destination), 'Acceptance': False}


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2]))))
