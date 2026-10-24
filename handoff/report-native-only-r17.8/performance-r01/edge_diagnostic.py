"""Small native diagnostic of virtual scalar substitutions; not acceptance."""
import hashlib
import json
from pathlib import Path
import shutil

import prepared
import regression

HERE = Path(__file__).resolve().parent


def build(destination, source, runner_source):
    if destination.exists():
        raise ValueError('Preserve prior diagnostic')
    regression.checked(source)
    regression.checked(runner_source)
    query = next(q['query'] for q in json.loads((source / 'queries.json').read_text()) if q['name'] == 'scalar-edge/positive/plan')
    row = 'ROW("H",[N Headline Cell],"S",[N Summary Cell])'
    projection = '''ROW("H",[N Headline Cell],"S",[N Summary Cell],"Plan",[N Plan],"Benchmark",[N Benchmark],
 "SourceOK",[N Source OK],"PeriodOK",[N Period Available],"Actual",[N Actual Only],
 "MetricCount",COUNTROWS(VALUES('fm_native_metric'[RowID])),"Column",SELECTEDVALUE('fm_native_columns'[ColumnKey]))'''
    if query.count(row) != 1:
        raise ValueError('Unknown edge projection')
    first = query.replace(row, projection)
    db = json.loads((source / 'candidate.json').read_text())
    measures = prepared.adapter.planning.measures(db)
    define = '\n'.join("MEASURE 'fm_native_measures'[" + n + '] = ' + measures[n]['expression'] for n in ('N Headline Cell', 'N Summary Cell'))
    second = first.replace('DEFINE ', 'DEFINE ' + define + '\n', 1)
    queries = [{'name': 'stored-cell-overrides', 'model': 'candidate', 'query': first},
               {'name': 'query-cell-overrides', 'model': 'candidate', 'query': second}]
    destination.mkdir(parents=True)
    for name in ('candidate.json', 'launch_synthetic_engine.ps1'):
        shutil.copy2(source / name, destination / name)
    shutil.copy2(runner_source / 'run_profile.ps1', destination / 'run_profile.ps1')
    shutil.copy2(Path(__file__), destination / Path(__file__).name)
    (destination / 'queries.json').write_text(json.dumps(queries))
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files, 'Kind': 'DIAGNOSTIC_NOT_ACCEPTANCE'}, indent=2))
    return {'Directory': str(destination), 'Queries': len(queries)}


if __name__ == '__main__':
    import sys
    print(json.dumps(build(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))))
