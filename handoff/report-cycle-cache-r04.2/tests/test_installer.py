import base64
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_feed import M, candidate
from install_feed import Fabric, install, normalized, prepare, unchanged_except_feed, unpack

EXPECTED = {k: v for k, v in M.items() if k.startswith('FM UI ')}
UPDATES = candidate()


def definition():
    value = {'model': {'tables': [{'name': 'fm_review_measures', 'measures': [{'name': k, 'expression': v['expression'], 'lineageTag': 'keep-' + k} for k, v in EXPECTED.items()], 'partitions': [{'name': 'Keep all data', 'source': {'expression': 'unchanged'}}]}, {'name': 'OtherTable', 'measures': [{'name': 'Keep other measure', 'expression': '1'}]}], 'relationships': [{'name': 'Keep relationship'}]}}
    return {'parts': [{'path': 'model.bim', 'payloadType': 'InlineBase64', 'payload': base64.b64encode(json.dumps(value).encode()).decode()}, {'path': 'definition.pbism', 'payloadType': 'InlineBase64', 'payload': 'preserve exact bytes'}]}


def test_changes_are_only_six_qualified_expressions():
    before = definition()
    after, changed = prepare(before, EXPECTED, UPDATES)
    assert len(changed) == 6
    unchanged_except_feed(before, after, UPDATES)
    assert prepare(after, EXPECTED, UPDATES)[1] == []
    assert definition() == before


@pytest.mark.parametrize('name', UPDATES)
def test_every_source_measure_is_guarded_against_unreviewed_edits(name):
    before = definition()
    part, model = unpack(before)
    next(m for m in model['model']['tables'][0]['measures'] if m['name'] == name)['expression'] += ' + 123'
    part['payload'] = base64.b64encode(json.dumps(model).encode()).decode()
    with pytest.raises(RuntimeError, match='differs from the qualified'):
        prepare(before, EXPECTED, UPDATES)


def test_normalization_preserves_quoted_spaces():
    assert normalized(' SUM ( T[X] ) ') == normalized('SUM(T[X])')
    assert normalized('"a b"') != normalized('"ab"')
    assert normalized("'a b'[X]") != normalized("'ab'[X]")


class FS:
    def __init__(self, truncate=False): self.saved, self.truncate = {}, truncate
    def mkdirs(self, path): pass
    def put(self, path, text, overwrite):
        assert not overwrite
        assert path not in self.saved
        self.saved[path] = text
    def head(self, path, limit): return self.saved[path][:-1] if self.truncate else self.saved[path]


class API:
    def __init__(self): self.current, self.calls, self.reads = definition(), [], 0
    def read(self): self.reads += 1; return copy.deepcopy(self.current)
    def call(self, method, url, body):
        assert method == 'POST' and url.endswith('/updateDefinition')
        assert body['options'] == {'allowPurgeData': False}
        self.calls.append((method, url, body))
        self.current = copy.deepcopy(body['definition'])


def test_install_verifies_backup_then_model_and_is_idempotent():
    api, fs = API(), FS()
    receipt = install(api, fs, EXPECTED, UPDATES)
    assert receipt['Status'] == 'INSTALLED' and receipt['CompanyInteractionSpeed'] == 'NOT_YET_MEASURED'
    assert len(api.calls) == 1 and len(fs.saved) == 2
    assert install(api, fs, EXPECTED, UPDATES)['Status'] == 'ALREADY_INSTALLED'
    assert len(api.calls) == 1


def test_incomplete_backup_prevents_write():
    api = API()
    with pytest.raises(RuntimeError, match='backup'):
        install(api, FS(truncate=True), EXPECTED, UPDATES)
    assert api.calls == []


def test_concurrent_model_edit_prevents_write():
    api, fs = API(), FS()
    original = api.read
    def read():
        result = original()
        if api.reads == 2:
            part, model = unpack(result)
            model['model']['tables'][1]['measures'][0]['expression'] = '2'
            part['payload'] = base64.b64encode(json.dumps(model).encode()).decode()
        return result
    api.read = read
    with pytest.raises(RuntimeError, match='changed during preparation'):
        install(api, fs, EXPECTED, UPDATES)
    assert api.calls == []


@pytest.mark.parametrize('state', ['Failed', 'Canceled'])
def test_failed_long_running_operation_is_not_success(state):
    class Response:
        status_code, content, headers = 202, b'x', {'Location': 'https://api.fabric.microsoft.com/v1/operations/one', 'Retry-After': '1'}
        def raise_for_status(self): pass
        def json(self): return {'status': state}
    class HTTP:
        def request(self, *a, **k): return Response()
        def get(self, *a, **k): return Response()
    with pytest.raises(RuntimeError, match=state):
        Fabric('test', HTTP(), sleep=lambda n: None).call('POST', 'https://example.test')


def test_numeric_body_is_preserved_and_scope_covers_whole_cycle():
    for name in ['FM UI Numerator', 'FM UI Denominator', 'FM UI Numerator Missing', 'FM UI Denominator Missing']:
        assert UPDATES[name]['expression'].split('RETURN IF(_scopeAllowed,', 1)[1] == EXPECTED[name]['expression'].split('RETURN IF(_scopeAllowed,', 1)[1]
        assert '_cycleComplete' in UPDATES[name]['expression']
    assert 'EXCEPT(_expectedIDs, _selectedIDs)' in UPDATES['FM UI Context']['expression']


def test_all_native_metric_components_reconcile_to_independent_synthetic_facts():
    fixture = json.loads((ROOT / 'tests/synthetic-facts.json').read_text())
    result = json.loads((ROOT / 'tests/native-dax-r04.2.json').read_text(encoding='utf-8-sig'))
    assert all(v['Status'] == 'PASS' for v in result['Queries'].values())
    assert result['Queries']['complete-cycle']['Rows'] == result['Queries']['stored-cycle']['Rows']
    catalog = {m['MetricKey']: m for m in fixture['catalog']}
    grouped = {}
    for f in fixture['facts']:
        key = tuple(f[k] for k in ['SourceRevisionID', 'Month', 'ComponentKey', 'Channel', 'SubChannel', 'Sector'])
        grouped[key] = grouped.get(key, 0) + f['Amount']
    checked = 0
    for row in result['Queries']['complete-cycle']['Rows']:
        if row.get('[Numerator]') is None and row.get('[Denominator]') is None:
            continue
        metric = catalog[row['fm_review_measures[MetricKey]']]
        for output, component in [('[Numerator]', 'NumeratorKey'), ('[Denominator]', 'DenominatorKey')]:
            key = (row['fm_review_files[SourceRevisionID]'], row['fm_review_axis[Month]'][:10], metric[component], row['fm_review_facts[Channel]'], row['fm_review_facts[SubChannel]'], row['fm_review_facts[Sector]'])
            expected = grouped.get(key)
            assert row.get(output) == expected
        checked += 1
    assert checked == 1680
    for row in result['Queries']['legacy-scope-incomplete']['Rows']:
        assert row.get('[Numerator]') is None and row.get('[Denominator]') is None
