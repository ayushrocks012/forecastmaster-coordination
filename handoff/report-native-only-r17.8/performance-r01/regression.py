"""Reuse the closed, independently calculated R02 mixed-matrix population."""
import hashlib
import json
from pathlib import Path
import shutil

import prepared

HERE = Path(__file__).resolve().parent


def checked(directory):
    bound = json.loads((directory / 'FROZEN-INPUTS.json').read_text())
    for name, sha in bound['Files'].items():
        if hashlib.sha256((directory / name).read_bytes()).hexdigest() != sha:
            raise ValueError('Changed source: ' + name)
    return bound


def build(destination, candidate, population):
    if destination.exists():
        raise ValueError('Preserve earlier attempts')
    candidate_binding, population_binding = checked(candidate), checked(population)
    if candidate_binding.get('Prototype') not in ('cells', 'strictcells') or population_binding.get('ExpectedValueColorCells') != 11592:
        raise ValueError('Require exact candidate and closed independent population')
    queries = json.loads((population / 'queries.json').read_text())
    expected = json.loads((population / 'expected.json').read_text())
    if len(queries) != 75 or sum(len(v) for v in expected.values()) != 11592:
        raise ValueError('Changed query/oracle population')
    destination.mkdir(parents=True)
    shutil.copy2(candidate / 'candidate.json', destination / 'candidate.json')
    for name in ('queries.json', 'expected.json'):
        shutil.copy2(population / name, destination / name)
    runner = (HERE / 'run_profile.ps1').read_text()
    start, end = runner.index(' $traceSource=@"'), runner.index(' foreach($case in ')
    runner = runner[:start] + " Write-Output 'Independent regression; tracing disabled.'\n" + runner[end:]
    start, end = runner.index(' $traceDeadline='), runner.index(" Write-Output ('Synthetic query executions:")
    runner = runner[:start] + runner[end:]
    runner = runner.replace("@('baseline','candidate')", "@('candidate')")
    (destination / 'run_profile.ps1').write_text(runner)
    for path in (Path(__file__), prepared.R02 / 'launch_synthetic_engine.ps1', prepared.R02 / 'matrix_cases.py'):
        shutil.copy2(path, destination / path.name)
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files,
        'Prototype': candidate_binding['Prototype'], 'CandidateSource': str(candidate), 'PopulationSource': str(population),
        'ExpectedQueries': 75, 'IndependentValueColorCells': 11592,
        'CompanyAcceptance': False}, indent=2))
    return {'Queries': 75, 'IndependentValueColorCells': 11592, 'Directory': str(destination)}


def verify(directory):
    checked(directory)
    oracle = prepared.load('perf_matrix_verify', prepared.R02 / 'matrix_cases.py')
    if hashlib.sha256((prepared.R02 / 'matrix_cases.py').read_bytes()).hexdigest() != hashlib.sha256((directory / 'matrix_cases.py').read_bytes()).hexdigest():
        raise ValueError('Oracle source changed')
    receipt = oracle.verify(directory)
    receipt.update(FrozenInputsMatch=True, TaskOwnedEngineClosed=True, NewServingTables=False)
    return receipt


if __name__ == '__main__':
    import sys
    result = verify(Path(sys.argv[2])) if sys.argv[1] == 'verify' else build(Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4]))
    print(json.dumps(result, indent=2))
