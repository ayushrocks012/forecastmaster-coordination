"""Execute the exact generated cell against isolated fake clients and files.

These tests prove control flow/refusals/privacy, not Fabric or company values.
The numerical queries require their separate native-engine qualification.
"""
import base64
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import importlib.util
from io import StringIO, BytesIO
import json
from pathlib import Path
import runpy
import sys
from types import ModuleType
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
json_loads = json.loads


def must(condition):
    if not condition:
        raise AssertionError('Fake-client contract violated')


class Response:
    def __init__(self, value, status=200, headers=None):
        self.value, self.status_code, self.headers = value, status, headers or {}

    def json(self):
        return deepcopy(self.value)


class Frame:
    def __init__(self, rows):
        self.rows = rows

    def to_dict(self, orient):
        must(orient == 'records')
        return deepcopy(self.rows)


class Environment:
    def __init__(self, mode='healthy'):
        loaded = runpy.run_path(str(HERE / 'INSTALL AND PREPARE PRIVATE TEST R02.py'), run_name='r178_test')
        self.ns = loaded['run'].__globals__
        spec = importlib.util.spec_from_file_location('r178_mock_adapter', HERE.parent / 'adapter.py')
        self.adapter = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.adapter)
        self.db = self.adapter.selection.original_database()
        for table in self.db['model']['tables']:
            if table['name'] in self.ns['FIELDS']:
                table['partitions'] = [{'name': table['name'], 'mode': 'directLake', 'source': {'type': 'entity', 'entityName': table['name'], 'expressionSource': 'OneLake'}}]
                for column in table['columns']:
                    column.pop('type', None)
                    column['sourceColumn'] = column['name']
        self.db['model']['expressions'] = [{'name': 'OneLake', 'expression': 'AzureStorage.DataLake("' + self.ns['WORKSPACE'] + '/' + self.ns['LAKEHOUSE'] + '")'}]
        if mode == 'unknown-public-expression':
            self.ns['native_measures'](self.db)['N Plan']['expression'] = '0'
        self.before = self.definition(self.db)
        self.mapping = [{'id': 'fabricated-cloud-connection', 'connectivityType': 'ShareableCloud'}]
        self.folder = self.ns['R01_PRIVATE'] + '/fabricated-r01-backup'
        self.storage = {
            self.ns['R01_PRIVATE'] + '/ATTEMPT.json': json.dumps({'Revision': 'R01', 'TEST': self.ns['TEST'], 'Backup': self.folder, 'CandidateBIM': self.ns['digest'](self.db)}),
            self.folder + '/definition-candidate.json': json.dumps(self.before),
            self.folder + '/connections-before.json': json.dumps(self.mapping),
            self.folder + '/success.json': json.dumps({'Stage': 'TEST_R178_UPDATED'}),
        }
        self.mode, self.writes, self.updated, self.reads, self.amount_reads = mode, [], False, 0, 0
        self.defaults = [{'Country': 'UK', 'Cycle': '2026-10', 'Driver': 'Driver 01', 'Label': "Private O'Brien ADS · 24 Oct 2026 UTC", 'Scenario': 'ADS'}]
        if mode == 'prior-attempt':
            self.storage[self.ns['ATTEMPT']] = '{}'
        if mode == 'current-changed':
            self.db['model']['description'] = 'changed after R01'
        if mode == 'wrong-private-hash':
            self.storage[self.ns['R01_PRIVATE'] + '/ATTEMPT.json'] = self.storage[self.ns['R01_PRIVATE'] + '/ATTEMPT.json'].replace(self.ns['digest'](self.db), '0' * 64)

    @staticmethod
    def definition(db):
        return {'parts': [{'path': 'model.bim', 'payload': base64.b64encode(json.dumps(db).encode()).decode(), 'payloadType': 'InlineBase64'},
                          {'path': 'definition.pbism', 'payload': 'fabricated-unchanged-part', 'payloadType': 'InlineBase64'}]}

    def get(self, path):
        if '/refreshes?' in path:
            return Response({'value': [{'id': 'fabricated-refresh', 'status': 'Failed' if self.mode == 'latest-failed' else 'Completed'}]})
        if path.endswith('/connections'):
            return Response({'value': [] if self.mode == 'cloud-changed' else self.mapping})
        if path == self.ns['ITEM']:
            return Response({'id': 'WRONG' if self.mode == 'identity' else self.ns['TEST'], 'displayName': self.ns['NAME'], 'type': 'SemanticModel'})
        raise AssertionError('Unexpected GET route')

    def post(self, path, json=None):
        if path.endswith('/getDefinition?format=TMSL'):
            self.reads += 1
            db = deepcopy(self.db)
            if self.mode == 'concurrent' and self.reads > 1:
                db['model']['description'] = 'concurrent fabricated edit'
            return Response({'definition': self.definition(db)})
        if path.endswith('/updateDefinition'):
            self.writes.append((path, deepcopy(json)))
            must(json['options'] == {'allowPurgeData': False})
            must(self.ns['ATTEMPT'] in self.storage)
            self.db = json_loads(base64.b64decode(json['definition']['parts'][0]['payload']))
            self.updated = True
            if self.mode == 'lost-update-response':
                raise ConnectionError('private text must not appear')
            if self.mode == 'unknown-operation-header':
                return Response({}, 202, {})
            if self.mode == 'readback-differs':
                self.db['model']['description'] = 'wrong post-write metadata'
            return Response({})
        raise AssertionError('Unexpected POST route')

    def exists(self, path):
        return path in self.storage

    def mkdirs(self, path):
        return True

    def put(self, path, value, overwrite):
        must(overwrite is False and path not in self.storage)
        if self.mode == 'backup-write-fails':
            return False
        self.storage[path] = value
        return True

    def cp(self, source, target, recurse):
        must(recurse is False)
        text = self.storage[source]
        if self.mode == 'backup-corrupt' and source.startswith(self.ns['R02_PRIVATE']):
            text += 'CORRUPTED'
        Path(unquote(urlsplit(target).path)).write_text(text)
        return True

    def evaluate(self, **args):
        must(args['dataset'] == self.ns['TEST'] and args['workspace'] == self.ns['WORKSPACE'])
        must(args['use_readwrite_connection'] is False)
        query = args['dax_string']
        if query == self.ns['DATE_QUERY']:
            return Frame([{'Kind': kind, 'ID': 'fabricated-source' if kind in {'SourceIMS', 'SourceEF', 'NativeIMS', 'NativeEF'} else '', 'D': datetime(2026, 8, 1)} for kind in self.ns['KINDS'] if self.mode != 'missing-date' or kind != 'Axis'])
        if query == self.ns['DEFAULTS_QUERY']:
            return Frame([] if self.mode == 'no-defaults' else self.defaults * (2 if self.mode == 'ambiguous-defaults' else 1))
        if query == self.ns['METADATA_QUERY']:
            return Frame([{k: self.defaults[0][k] for k in ('Country', 'Cycle', 'Driver')}])
        self.amount_reads += 1
        if self.mode == 'cancelled':
            raise RuntimeError('cancelled; private text must not appear')
        if self.mode == 'unknown-category':
            raise ArithmeticError('private text must not appear')
        body = query.rsplit('EVALUATE ROW("V",', 1)[-1]
        absent = "'fm_native_files'[FileChoiceLabel]" not in body
        value = 0 if absent and self.mode == 'no-file-not-blank' else None if absent else 42
        if self.mode == 'zero' and not absent:
            value = 0
        if self.mode == 'preflight-mismatch' and query.startswith('DEFINE'):
            value = 43
        if self.mode == 'installed-mismatch' and self.updated and not absent:
            value = 43
        if self.mode == 'bad-scalar':
            value = 'private text must not appear'
        if self.mode == 'malformed':
            return Frame([{'[V]': value}, {'[V]': value}])
        return Frame([{'[V]': value}])

    def run(self):
        display = ModuleType('IPython.display')
        display.HTML = lambda value: value
        self.links = []
        display.display = self.links.append
        with patch.dict(sys.modules, {'IPython.display': display}), redirect_stdout(StringIO()) as output:
            result = self.ns['run'](self, self, self, self.evaluate)
        self.output = output.getvalue()
        return result


class ReceivingTests(unittest.TestCase):
    def test_healthy_exact_generated_cell_and_private_report(self):
        env = Environment()
        before = deepcopy(env.db)
        result = env.run()
        self.assertEqual(result['Stage'], 'TEST_R178_R02_UPDATED_AND_BOUNDED_READBACK_VERIFIED')
        self.assertEqual(result['Preflight']['PairedScalarComparisons'], 24)
        self.assertEqual(result['Preflight']['NoFileBlankChecks'], 3)
        self.assertEqual(result['InstalledScalarReadbacks'], 24)
        self.assertEqual(len(env.writes), 1)
        self.assertEqual(env.db, env.adapter.patch_database(before)[0])
        self.assertFalse(result['RefreshRequested'] or result['ReportPublished'] or result['OriginalModelWriteRequested'])
        self.assertNotIn(env.defaults[0]['Label'], env.output)
        self.assertNotIn('private text must not appear', env.output)
        package = json.loads(env.storage[result['PrivateBackup'] + '/report-package.json'])
        with ZipFile(BytesIO(base64.b64decode(package['ZipBase64']))) as archive:
            path = env.ns['REPORT_FOLDER'] + '/definition/pages/native_demand/visuals/file_picker/visual.json'
            picker = json.loads(archive.read(path))
            values = picker['visual']['objects']['general'][0]['properties']['filter']['filter']['Where'][0]['Condition']['In']['Values']
            self.assertEqual(values, [[{'Literal': {'Value': "'" + env.defaults[0]['Label'].replace("'", "''") + "'"}}]])
            self.assertFalse(any('.SemanticModel/' in n for n in archive.namelist()))

    def test_prewrite_refusals_do_not_submit_update(self):
        for mode in ('prior-attempt', 'identity', 'current-changed', 'wrong-private-hash', 'latest-failed', 'cloud-changed',
                     'unknown-public-expression', 'no-defaults', 'ambiguous-defaults', 'cancelled', 'bad-scalar',
                     'preflight-mismatch', 'no-file-not-blank', 'concurrent', 'backup-write-fails', 'backup-corrupt',
                     'missing-date', 'malformed', 'unknown-category'):
            with self.subTest(mode=mode):
                env = Environment(mode)
                result = env.run()
                self.assertEqual(result['Stage'], 'TEST_R178_R02_STOPPED')
                self.assertEqual(env.writes, [])
                self.assertFalse(result['ModelWriteRequested'])
                self.assertEqual(env.links, [])
                self.assertNotIn('private text must not appear', env.output)

    def test_zero_is_numeric_and_blank_is_not_zero(self):
        env = Environment('zero')
        result = env.run()
        self.assertEqual(result['Stage'], 'TEST_R178_R02_UPDATED_AND_BOUNDED_READBACK_VERIFIED')
        self.assertEqual(len(env.writes), 1)
        self.assertEqual(result['Preflight']['NoFileBlankChecks'], 3)

    def test_failed_prewrite_state_then_external_recovery(self):
        env = Environment('latest-failed')
        self.assertEqual(env.run()['Stage'], 'TEST_R178_R02_STOPPED')
        self.assertEqual(env.writes, [])
        self.assertNotIn(env.ns['ATTEMPT'], env.storage)
        # An independently observed external change can justify a reviewed retry.
        # The updater itself never submits or retries a refresh.
        env.mode = 'healthy'
        result = env.run()
        self.assertEqual(result['Stage'], 'TEST_R178_R02_UPDATED_AND_BOUNDED_READBACK_VERIFIED')
        self.assertEqual(len(env.writes), 1)
        self.assertFalse(result['RefreshRequested'])

    def test_uncertain_or_failed_readback_is_sticky_without_retry(self):
        for mode in ('lost-update-response', 'unknown-operation-header', 'readback-differs', 'installed-mismatch'):
            with self.subTest(mode=mode):
                env = Environment(mode)
                result = env.run()
                self.assertEqual(result['Stage'], 'TEST_R178_R02_STOPPED')
                self.assertTrue(result['ModelWriteRequested'])
                self.assertEqual(len(env.writes), 1)
                self.assertEqual(env.links, [])
                again = env.run()
                self.assertEqual(again['Failure']['Reason'], 'PRIOR_R02_ATTEMPT_REVIEW_REQUIRED_NO_RETRY')
                self.assertEqual(len(env.writes), 1)


if __name__ == '__main__':
    unittest.main()
