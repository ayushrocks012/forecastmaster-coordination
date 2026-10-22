"""Exercise the pasteable read-only probe with a mocked Fabric metadata API."""
import ast
import base64
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
SOURCE = (ROOT / 'PROBE ONLY - READABLE.py').read_text(encoding='utf-8')
OP_ID = '00000000-0000-0000-0000-000000000099'
OP = '/v1/operations/' + OP_ID


def definition(mode='directLake', route='Sql.Database("example.invalid","sample")'):
    model = {'tables': [{'name': 'fm_review_facts', 'partitions': [
        {'mode': mode, 'source': {'type': 'entity', 'expressionSource': 'Source'}}]}],
        'expressions': [{'name': 'Source', 'expression': route}],
        'roles': [{'name': 'Synthetic restricted role'}]}
    return {'parts': [{'path': 'model.bim', 'payload': base64.b64encode(
        json.dumps({'model': model}).encode()).decode()}]}


class Response:
    def __init__(self, code, payload=None, headers=None):
        self.status_code = code
        self.payload = payload
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError('Synthetic HTTP ' + str(self.status_code))

    def json(self):
        return self.payload


class Client:
    def __init__(self, responses, running=False):
        self.responses = list(responses)
        self.calls = []
        self.running = running

    def post(self, path):
        assert path.endswith('/getDefinition?format=TMSL')
        self.calls.append(('POST', path))
        return self.responses.pop(0)

    def get(self, path):
        assert path in {OP, OP + '/result'}
        self.calls.append(('GET', path))
        if self.running:
            return Response(200, {'status': 'Running'})
        return self.responses.pop(0)


def execute(client):
    package = types.ModuleType('sempy')
    module = types.ModuleType('sempy.fabric')
    package.fabric = module
    module.FabricRestClient = lambda: client
    clock = [0]
    def sleep(seconds):
        clock[0] += seconds
    output = io.StringIO()
    namespace = {}
    with patch.dict(sys.modules, {'sempy': package, 'sempy.fabric': module}), \
         patch('time.sleep', sleep), patch('time.monotonic', lambda: clock[0]), \
         contextlib.redirect_stdout(output):
        exec(compile(SOURCE, 'readable-probe', 'exec'), namespace)
    text = output.getvalue()
    result = json.loads(text[text.index('{'):])
    return result, client.calls, text


class ReadableProbeTests(unittest.TestCase):
    def test_sync_sql_metadata(self):
        result, calls, text = execute(Client([Response(200, {'definition': definition()})]))
        self.assertTrue(result['CompatibleWithCurrentAdapter'])
        self.assertFalse(result['SourceAmountsRead'])
        self.assertFalse(result['ModelUpdated'])
        self.assertEqual(result['ExistingSecurityRoleCount'], 1)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('example.invalid', text)

    def test_async_metadata(self):
        result, calls, _ = execute(Client([
            Response(202, headers={'x-ms-operation-id': OP_ID, 'Retry-After': '1'}),
            Response(200, {'status': 'Running'}), Response(200, {'status': 'Succeeded'}),
            Response(200, {'definition': definition()})]))
        self.assertTrue(result['CompatibleWithCurrentAdapter'])
        self.assertEqual([method for method, _ in calls], ['POST', 'GET', 'GET', 'GET'])

    def test_import_and_direct_query_are_reported_without_conversion(self):
        for mode in ('import', 'directQuery'):
            with self.subTest(mode=mode):
                result, _, _ = execute(Client([Response(200, {'definition': definition(mode)})]))
                self.assertFalse(result['CompatibleWithCurrentAdapter'])
                self.assertEqual(result['SourceStorageModes'], [mode])

    def test_other_source_and_unknown_expression(self):
        for route in ('AzureStorage.DataLake("example.invalid")', ''):
            with self.subTest(route=route):
                result, _, _ = execute(Client([Response(200, {'definition': definition(route=route)})]))
                self.assertFalse(result['CompatibleWithCurrentAdapter'])

    def test_sql_expression_as_lines(self):
        result, _, _ = execute(Client([Response(200, {'definition': definition(
            route=['let', 'Source = OneLake.SqlAnalytics("example.invalid")', 'in Source'])})]))
        self.assertTrue(result['CompatibleWithCurrentAdapter'])

    def test_existing_native_objects(self):
        data = definition()
        model = json.loads(base64.b64decode(data['parts'][0]['payload']))
        model['model']['tables'].append({'name': 'fm_native_example'})
        data['parts'][0]['payload'] = base64.b64encode(json.dumps(model).encode()).decode()
        result, _, _ = execute(Client([Response(200, {'definition': data})]))
        self.assertEqual(result['NativeTablesAlreadyPresent'], 1)
        self.assertFalse(result['CompatibleWithCurrentAdapter'])

    def test_fact_missing_or_multiple_partitions(self):
        for variant in ('missing', 'multiple'):
            data = definition()
            model = json.loads(base64.b64decode(data['parts'][0]['payload']))
            fact = model['model']['tables'][0]
            if variant == 'missing':
                model['model']['tables'] = []
            else:
                fact['partitions'].append(copy.deepcopy(fact['partitions'][0]))
            data['parts'][0]['payload'] = base64.b64encode(json.dumps(model).encode()).decode()
            result, _, _ = execute(Client([Response(200, {'definition': data})]))
            self.assertFalse(result['CompatibleWithCurrentAdapter'])

    def test_missing_tmsl_part(self):
        with self.assertRaisesRegex(ValueError, 'model.bim'):
            execute(Client([Response(200, {'definition': {'parts': []}})]))

    def test_async_failure_and_timeout(self):
        with self.assertRaisesRegex(RuntimeError, 'Failed'):
            execute(Client([Response(202, headers={'x-ms-operation-id': OP_ID}),
                            Response(200, {'status': 'Failed'})]))
        with self.assertRaises(TimeoutError):
            execute(Client([Response(202, headers={'x-ms-operation-id': OP_ID})], running=True))

    def test_unsafe_operation_id_or_http_error(self):
        with self.assertRaises(ValueError):
            execute(Client([Response(202, headers={'x-ms-operation-id': 'https://example.invalid'})]))
        with self.assertRaisesRegex(RuntimeError, '403'):
            execute(Client([Response(403)]))

    def test_source_is_small_and_contains_no_installation(self):
        ast.parse(SOURCE)
        self.assertLess(len(SOURCE.encode()), 6000)
        self.assertLessEqual(max(map(len, SOURCE.splitlines())), 110)
        for forbidden in ('SPEC=', 'b64decode("', 'zlib', 'updateDefinition', 'saveAsTable',
                          'notebookutils', 'lease.acquire', 'spark.sql'):
            self.assertNotIn(forbidden, SOURCE)
        calls = [node for node in ast.walk(ast.parse(SOURCE)) if isinstance(node, ast.Call)]
        self.assertEqual(sum(isinstance(c.func, ast.Attribute) and c.func.attr == 'post' for c in calls), 1)
        notebook = json.loads((ROOT / 'ForecastMaster Native Probe - READ ONLY.ipynb').read_text())
        self.assertEqual(len(notebook['cells']), 1)
        self.assertEqual(''.join(notebook['cells'][0]['source']), SOURCE)
        self.assertEqual(notebook['cells'][0]['outputs'], [])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(ReadableProbeTests)
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    receipt = {'Tests': result.testsRun, 'Passed': result.wasSuccessful(),
               'SourceBytes': len(SOURCE.encode()),
               'MaximumSourceLineLength': max(map(len, SOURCE.splitlines())),
               'Evidence': 'Mock Fabric metadata API only; no live company execution.',
               'OriginalInstallerZIPUnchanged': True}
    (ROOT / 'VALIDATION-READABLE-PROBE.json').write_text(json.dumps(receipt, indent=2) + '\n')
    raise SystemExit(not result.wasSuccessful())
