"""Report-local colour reuse pilot; numerical model stays the qualified R03."""
from pathlib import Path
import hashlib
import json
import shutil

import prepared
import regression
import probe

HERE = Path(__file__).resolve().parent

PALETTE = '''RETURN IF(NOT ISBLANK(_value),
 VAR _size=ABS(_value)
 RETURN SWITCH(TRUE(),_size<=0.05,"#E5F2E6",_size<=0.10,"#FFF3CD","#F9E1E3"))'''

SUMMARY = '''VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])
VAR _window=SELECTEDVALUE('fm_native_columns'[Window])
RETURN IF(HASONEVALUE('fm_native_columns'[ColumnKey])&&_key<>"plan",
 VAR _value=CALCULATE([N Summary Cell],REMOVEFILTERS('fm_native_columns'),
 TREATAS({FORMAT(_window,"0")&":pct"},'fm_native_columns'[ColumnKey]))
 ''' + PALETTE + ')'

REVIEW = '''VAR _key=SELECTEDVALUE('fm_native_headline'[Key])
RETURN IF(HASONEVALUE('fm_native_headline'[Key])&&_key<>"plan",
 VAR _value=CALCULATE([N Headline Cell],REMOVEFILTERS('fm_native_headline'),
 TREATAS({"pct"},'fm_native_headline'[Key]))
 ''' + PALETTE + ')'


def rewrite(query, name, expression):
    old = prepared.load('perf_gm', prepared.R02 / 'gm_presentation.py').MEASURES[name]
    if query.count(old) != 1:
        raise ValueError('Unknown qualified colour body')
    return query.replace(old, expression)


def build(destination, source, runner_source):
    if destination.exists():
        raise ValueError('Preserve previous pilot')
    regression.checked(source)
    regression.checked(runner_source)
    population = json.loads((source / 'queries.json').read_text())
    queries = []
    for metric in ('market', 'share', 'review'):
        original = next(q['query'] for q in population if q['name'] == metric + '/1/candidate')
        name, expression = ('N GM Review Color', REVIEW) if metric == 'review' else ('N GM Summary Color', SUMMARY)
        changed = rewrite(original, name, expression)
        for label, query in [('old', original), ('reuse', changed)]:
            queries.append({'name': metric + '/' + label, 'model': 'candidate', 'query': query})
    destination.mkdir(parents=True)
    for name in ('candidate.json', 'launch_synthetic_engine.ps1'):
        shutil.copy2(source / name, destination / name)
    shutil.copy2(runner_source / 'run_profile.ps1', destination / 'run_profile.ps1')
    shutil.copy2(Path(__file__), destination / Path(__file__).name)
    (destination / 'queries.json').write_text(json.dumps(queries))
    files = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}
    (destination / 'FROZEN-INPUTS.json').write_text(json.dumps({'Files': files, 'Kind': 'COLOUR_REUSE_PILOT_NOT_RELEASE'}, indent=2))
    return {'Directory': str(destination), 'Queries': len(queries)}


def verify(directory):
    binding = regression.checked(directory)
    results = json.loads((directory / 'results.json').read_text(encoding='utf-8-sig'))
    if len(results) != 6 or any('error' in r for r in results):
        raise AssertionError('Incomplete or failed pilot')
    by = {r['name']: r for r in results}
    pairs = []
    for metric in ('market', 'share', 'review'):
        left, right = (by[metric + '/' + label] for label in ('old', 'reuse'))
        a, b = left['resultSets'], right['resultSets']
        if metric != 'review':
            a, b = probe.full_core_sets(a), probe.full_core_sets(b)
        if not all(s['rows'] for s in a) or not probe.equal(a, b):
            raise AssertionError('Changed values/colours/formats/population: ' + metric)
        pairs.append({'Context': metric, 'OldMs': left['elapsedMs'], 'ReuseMs': right['elapsedMs']})
    return {'Stage': 'LOCAL_COLOUR_REUSE_PILOT', 'Pairs': pairs, 'Mismatches': 0,
        'SourceHashes': binding['Files'], 'CompanyAcceptance': False, 'TaskOwnedEngineClosed': True}


if __name__ == '__main__':
    import sys
    print(json.dumps(verify(Path(sys.argv[2])) if sys.argv[1] == 'verify' else build(*(Path(s) for s in sys.argv[2:5])), indent=2))
