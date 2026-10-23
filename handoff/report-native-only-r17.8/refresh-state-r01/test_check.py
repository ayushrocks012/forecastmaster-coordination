"""Synthetic operational metadata only; no Fabric session or amount queries."""
import ast
from contextlib import redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_history_probe', HERE / 'CHECK TEST REFRESH STATE R01.py')
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class Response:
    def __init__(self, value, status=200):
        self.value, self.status_code = value, status

    def json(self):
        return deepcopy(self.value)


class FS:
    def __init__(self):
        self.reads = []
        self.folder = probe.ROOT + '/20261023T220000-11111111-1111-4111-8111-111111111111'
        self.files = {
            probe.ATTEMPT: {'Revision': 'R01', 'TEST': probe.TEST, 'Backup': self.folder},
            self.folder + '/success.json': {'Stage': 'TEST_R178_UPDATED',
                                           'InstalledAtUTC': '2026-10-23T22:00:00+00:00'}
        }

    def exists(self, path):
        return path in self.files

    def cp(self, path, destination, recurse):
        assert not recurse and path in self.files and destination.startswith('file://')
        self.reads.append(path)
        Path(destination.removeprefix('file://')).write_text(json.dumps(self.files[path]))
        return True


class Client:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.status = 200
        self.identity = {'id': probe.TEST, 'displayName': probe.NAME, 'type': 'SemanticModel'}

    def get(self, path):
        self.calls.append(path)
        if path == '/v1/workspaces/' + probe.WORKSPACE + '/items/' + probe.TEST:
            return Response(self.identity)
        assert path == probe.HISTORY, 'Unexpected read route'
        return Response({'value': self.rows}, self.status)


def job(status='Completed', start='2026-10-23T22:01:00Z', **kwargs):
    return {'status': status, 'startTime': start,
            'requestId': '11111111-1111-4111-8111-111111111111',
            'refreshType': 'OnDemand', **kwargs}


class Tests(unittest.TestCase):
    def run_probe(self, rows, change=None):
        client, fs = Client(rows), FS()
        if change:
            change(client, fs)
        with redirect_stdout(io.StringIO()) as output:
            result = probe.run(client, client, fs)
        self.assertNotIn('PRIVATE_SENTINEL', output.getvalue())
        for field in ('ModelWriteRequested', 'OriginalModelWriteRequested',
                      'LakehouseTableWriteRequested', 'RefreshRequested',
                      'CompanyAmountQuerySubmitted', 'CompanyAmountValuesPrintedOrStored', 'ReportPublished'):
            self.assertIs(False, result[field])
        return result, client, fs

    def test_completed_new_vs_old_refresh_and_no_amount_or_definition_calls(self):
        for start, expected in [('2026-10-23T22:01:00Z', 1), ('2026-10-23T21:59:00Z', 0)]:
            result, client, fs = self.run_probe([job(start=start)])
            self.assertEqual('R178_REFRESH_STATE_READ_COMPLETED', result['Stage'])
            self.assertEqual(expected, result['Summary']['CompletedAtOrAfterInstall'])
            self.assertEqual(2, len(client.calls))
            self.assertEqual([probe.ATTEMPT, fs.folder + '/success.json'], fs.reads)

    def test_unknown_failed_disabled_and_unrecognized_are_reported_without_authorizing_retry(self):
        for status, reported, active in [('Unknown', 'Unknown', 1), ('Failed', 'Failed', 0),
                                        ('Disabled', 'Disabled', 0), ('PRIVATE_SENTINEL', 'UNRECOGNIZED', 1)]:
            result, _, _ = self.run_probe([job(status)])
            self.assertEqual(reported, result['Summary']['FirstEntryStatusUsedByVerifier'])
            self.assertEqual(active, result['Summary']['NonTerminalOrUnrecognized'])
            self.assertIn('until reviewed', result['NextStep'])

    def test_empty_history_and_missing_dates_stay_explicit(self):
        result, _, _ = self.run_probe([])
        self.assertEqual('NO_ROWS', result['Summary']['FirstEntryStatusUsedByVerifier'])
        for start in (None, '', 'PRIVATE_SENTINEL', '2026-10-23T22:01:00'):
            result, _, _ = self.run_probe([job(start=start)])
            self.assertIsNone(result['History'][0]['StartedAtOrAfterInstall'])
            self.assertEqual(1, result['Summary']['MissingOrInvalidStartTimes'])

    def test_api_order_kept_and_old_failed_plus_new_completed_not_silently_passed(self):
        result, _, _ = self.run_probe([job('Failed', '2026-10-23T20:00:00Z'), job()])
        self.assertEqual('Failed', result['Summary']['FirstEntryStatusUsedByVerifier'])
        self.assertEqual(1, result['Summary']['CompletedAtOrAfterInstall'])
        self.assertNotIn('VERIFIED', result['Stage'])

    def test_error_messages_and_arbitrary_labels_never_printed(self):
        result, _, _ = self.run_probe([job('Failed', serviceExceptionJson='PRIVATE_SENTINEL memory capacity',
                                         refreshType='PRIVATE_SENTINEL', requestId='PRIVATE_SENTINEL')])
        row = result['History'][0]
        self.assertEqual(['MEMORY', 'CAPACITY'], row['KnownErrorSignals'])
        self.assertTrue(row['ServiceErrorPresent'])
        self.assertIsNone(row['RequestID'])
        self.assertEqual('UNRECOGNIZED', row['RefreshType'])

    def test_wrong_identity_marker_receipt_or_http_stops_before_dependent_reads(self):
        cases = [
            lambda client, fs: client.identity.update(id='PRIVATE_SENTINEL'),
            lambda client, fs: fs.files[probe.ATTEMPT].update(Backup=probe.ROOT + '/../other'),
            lambda client, fs: fs.files[probe.ATTEMPT].update(Backup=probe.ROOT + '/%2E%2E'),
            lambda client, fs: fs.files[fs.folder + '/success.json'].update(Stage='STOPPED'),
            lambda client, fs: fs.files[fs.folder + '/success.json'].update(InstalledAtUTC='INVALID'),
            lambda client, fs: setattr(client, 'status', 403)
        ]
        for change in cases:
            result, _, _ = self.run_probe([job()], change)
            self.assertEqual('R178_REFRESH_STATE_CHECK_STOPPED', result['Stage'])
            self.assertIn('Failure', result)

    def test_malformed_history_and_raw_exception_withheld(self):
        for rows in (None, {}, ['PRIVATE_SENTINEL'], [job()] * 61):
            result, _, _ = self.run_probe(rows)
            self.assertEqual('HISTORY_SHAPE_UNEXPECTED', result['Failure']['Reason'])

        def change(client, fs):
            def fail(_):
                raise RuntimeError('PRIVATE_SENTINEL')
            client.get = fail
        result, _, _ = self.run_probe([], change)
        self.assertEqual('EXCEPTION_WITHHELD', result['Failure']['Reason'])

    def test_python310_and_no_remote_mutation_or_evaluate_entrypoint(self):
        source = (HERE / 'CHECK TEST REFRESH STATE R01.py').read_text()
        tree = ast.parse(source, feature_version=(3, 10))
        calls = {node.func.attr for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)}
        self.assertTrue(calls.isdisjoint({'post', 'put', 'patch', 'delete', 'mkdirs', 'evaluate_dax', 'sql'}))
        self.assertIn("retry_config={'total': 0}", source)


if __name__ == '__main__':
    unittest.main()
