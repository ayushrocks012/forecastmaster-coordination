"""Run the exact generated candidate against fabricated receiving responses."""
import ast
import base64
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RELEASE = ROOT / 'handoff/report-native-only-r17.8/test-release-r01'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


b = load('r03_build', HERE / 'build_verifier.py')
b.build(HERE, RELEASE / 'VERIFY INSTALLED TEST R01.py')
v = load('r03_exact', HERE / 'VERIFY INSTALLED TEST R03.py')
fixtures = load('r02_fixture_helpers', RELEASE / 'test_release.py')


def job(status='Completed', start='2026-10-23T22:57:24Z', kind='DirectLake', **other):
    return {'status': status, 'startTime': start, 'refreshType': kind,
            'requestId': '11111111-1111-4111-8111-111111111111', **other}


class PBI:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def get(self, path):
        self.calls.append(path)
        if not path.endswith('/' + v.TEST + '/refreshes?$top=60'):
            raise AssertionError('Unpinned route')
        return fixtures.Response({'value': self.rows})


class Tests(unittest.TestCase):
    def run_case(self, rows=None, metadata=None, override=None):
        db = fixtures.database()
        fixed, _ = fixtures.m.patch_database(db)
        definition = lambda value: {'parts': [{'path': 'model.bim', 'payload': base64.b64encode(json.dumps(value).encode()).decode()}]}
        folder = v.RELEASE_PRIVATE + '/synthetic'
        receipts = {v.ATTEMPT: {'Revision': 'R01', 'TEST': v.TEST, 'Backup': folder},
                    folder + '/success.json': {'Stage': 'TEST_R178_UPDATED', 'InstalledAtUTC': '2026-10-23T22:22:35+00:00'},
                    folder + '/definition-before.json': definition(db), folder + '/definition-candidate.json': definition(fixed),
                    folder + '/connections-before.json': [{'id': 'SYNTHETIC'}]}
        rows = [job()] if rows is None else rows
        pbi = PBI(rows)
        dates = {kind: [('', '2026-01-01')] for kind in v.KINDS}
        values = {'Files': 8, 'Choices': 8, 'MissingImportedAt': 0, 'HashSuffixes': 0} if metadata is None else metadata
        settings = {
            'identity': {'return_value': None},
            'read_private': {'side_effect': lambda fs, path: deepcopy(receipts[path])},
            'read_definition': {'return_value': ({}, fixed, {})},
            'connections': {'return_value': [{'id': 'SYNTHETIC'}]},
            'physical_dates': {'return_value': dates}, 'semantic_dates': {'return_value': dates},
            'preflight': {'return_value': {'PairedScalarComparisons': 12, 'Mismatches': 0}}
        }
        if override:
            override(settings, receipts, dates, rows, fixed)
        with ExitStack() as stack, redirect_stdout(io.StringIO()) as output:
            mocks = {name: stack.enter_context(patch.object(v, name, **options)) for name, options in settings.items()}
            evaluate = stack.enter_context(patch.object(v, '_synthetic_evaluate', create=True,
                                                        return_value=fixtures.Frame([values])))
            result = v.verify_installed_r03(None, pbi, None, evaluate, object())
        self.assertNotIn('PRIVATE_SENTINEL', output.getvalue())
        for key in ('ModelWriteRequested', 'OriginalModelWriteRequested', 'LakehouseTableWriteRequested',
                    'RefreshRequested', 'CompanyAmountValuesPrintedOrStored', 'ReportPublished'):
            self.assertIs(False, result[key])
        return result, mocks, evaluate

    def test_healthy_exact_cell_all_checks_and_r03_marker(self):
        result, _, _ = self.run_case()
        self.assertEqual('TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED', result['Stage'], result)
        self.assertEqual('R03', result['VerifierRevision'])
        self.assertTrue(all(c['Status'] == 'PASSED' for c in result['Checks'].values()))

    def test_blank_nan_zero_metadata_is_distinct_from_missing_required_count(self):
        for blank in (None, float('nan'), 0):
            result, _, _ = self.run_case(metadata={'Files': 8, 'Choices': 8, 'MissingImportedAt': blank, 'HashSuffixes': blank})
            self.assertEqual(0, result['FileLabelCounts']['HashSuffixes'])
            self.assertEqual('TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED', result['Stage'])
        for invalid in (None, float('nan'), -1, 1.2, True, '8'):
            result, _, _ = self.run_case(metadata={'Files': invalid, 'Choices': 8, 'MissingImportedAt': 0, 'HashSuffixes': 0})
            self.assertEqual('FAILED', result['Checks']['FileLabels']['Status'])

    def test_hash_suffix_missing_import_or_duplicate_choices_refused(self):
        for patch_values in ({'HashSuffixes': 1}, {'MissingImportedAt': 1}, {'Choices': 7}):
            values = {'Files': 8, 'Choices': 8, 'MissingImportedAt': 0, 'HashSuffixes': 0, **patch_values}
            result, _, _ = self.run_case(metadata=values)
            self.assertEqual('FILE_CHOICE_LABELS_INVALID', result['Failure']['Reason'])

    def test_newer_failure_blocks_old_success_with_category_and_error_no_amount_queries(self):
        error = json.dumps({'errorCode': 'ModelRefreshFailed_BackendRequest', 'errorDescription':
                           'PRIVATE_SENTINEL 123456 while checking the latest version; An error occurred while sending the request'})
        result, mocks, evaluate = self.run_case([job('Failed', serviceExceptionJson=error), job(start='2026-10-23T22:24:13Z', kind='OnDemand')])
        self.assertEqual('TEST_REFRESH_NOT_COMPLETED', result['Failure']['Reason'])
        first = result['RefreshHistory']['FirstEntry']
        self.assertEqual('Direct Lake', first['Category'])
        self.assertEqual('2026-10-23T23:57:24+01:00', first['StartUK'])
        self.assertEqual(['ModelRefreshFailed_BackendRequest'], first['Error']['Codes'])
        self.assertTrue(first['Error']['Messages'])
        self.assertTrue(first['DetailsURL'].endswith(first['RequestID']))
        mocks['preflight'].assert_not_called()
        evaluate.assert_not_called()
        self.assertEqual('SKIPPED_DEPENDENCY', result['Checks']['PhysicalDates']['Status'])

    def test_failed_then_later_recovered_admitted_without_ignoring_failure(self):
        result, _, _ = self.run_case([job(), job('Failed', start='2026-10-23T22:27:57Z')])
        self.assertEqual('TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED', result['Stage'])
        result, _, _ = self.run_case([job('Failed'), job(start='2026-10-23T22:24:13Z')])
        self.assertEqual('TEST_REFRESH_NOT_COMPLETED', result['Failure']['Reason'])

    def test_unknown_active_cancelled_disabled_empty_history_and_category(self):
        for rows in ([job('Unknown')], [job('Cancelled')], [job('Disabled')], [], [job('Failed', kind='PRIVATE_SENTINEL')]):
            result, mocks, _ = self.run_case(rows)
            self.assertEqual('TEST_R178_VERIFICATION_STOPPED', result['Stage'])
            mocks['preflight'].assert_not_called()
        summary = v.history_evidence([job('Failed', kind='NewUnmappedType')])
        self.assertEqual('Unclassified', summary['FirstEntry']['Category'])
        self.assertIsNotNone(summary['FirstEntry']['DetailsURL'])

    def test_malformed_history_and_old_or_naive_dates_refused(self):
        for rows in ({}, ['PRIVATE_SENTINEL'], [job()] * 61, [job(start='2026-10-23T22:57:24')], [job(start='2026-10-23T20:00:00Z')]):
            result, mocks, _ = self.run_case(rows)
            self.assertEqual('FAILED', result['Checks']['RefreshHistory']['Status'])
            mocks['preflight'].assert_not_called()

    def test_invalid_semantic_date_stops_before_amount_queries(self):
        def invalid(settings, receipts, dates, rows, fixed):
            settings['semantic_dates'] = {'return_value': {**dates, 'Axis': [('', '1899-12-01')]}}
        result, mocks, _ = self.run_case(override=invalid)
        self.assertEqual('FAILED', result['Checks']['SemanticDates']['Status'])
        mocks['preflight'].assert_not_called()

    def test_identity_install_receipt_candidate_and_mapping_guards_retained(self):
        def no_identity(settings, *_):
            settings['identity'] = {'side_effect': v.CheckStopped('TEST_IDENTITY_MISMATCH')}
        def no_install(settings, receipts, *_):
            next(value for name, value in receipts.items() if name.endswith('/success.json'))['Stage'] = 'STOPPED'
        def no_candidate(settings, receipts, dates, rows, fixed):
            changed = deepcopy(fixed)
            changed['name'] = 'UNEXPECTED'
            settings['read_definition'] = {'return_value': ({}, changed, {})}
        def no_mapping(settings, *_):
            settings['connections'] = {'return_value': [{'id': 'DRIFT'}]}
        for change in (no_identity, no_install, no_candidate, no_mapping):
            result, mocks, _ = self.run_case(override=change)
            self.assertEqual('TEST_R178_VERIFICATION_STOPPED', result['Stage'])
            mocks['preflight'].assert_not_called()

    def test_concurrent_history_definition_or_mapping_blocks_final_pass(self):
        def history(settings, receipts, dates, rows, fixed):
            settings['processing_history'] = {'side_effect': [rows, [job(start='2026-10-23T23:00:00Z')]]}
        def definition(settings, receipts, dates, rows, fixed):
            changed = deepcopy(fixed)
            changed['model']['description'] = 'DRIFT'
            settings['read_definition'] = {'side_effect': [({}, fixed, {}), ({}, changed, {})]}
        def mapping(settings, *_):
            settings['connections'] = {'side_effect': [[{'id': 'SYNTHETIC'}], [{'id': 'DRIFT'}]]}
        for change in (history, definition, mapping):
            result, _, _ = self.run_case(override=change)
            self.assertEqual('FAILED', result['Checks']['FinalConsistency']['Status'])

    def test_cancelled_numeric_read_and_unknown_private_error_do_not_print_values(self):
        def cancelled(settings, *_):
            settings['preflight'] = {'side_effect': RuntimeError('PRIVATE_SENTINEL 123456 cancelled')}
        result, _, evaluate = self.run_case(override=cancelled)
        self.assertEqual('FAILED', result['Checks']['NumericalParity']['Status'])
        self.assertIn('CANCELLED', result['Failure']['KnownSignals'])
        self.assertEqual('SKIPPED_DEPENDENCY', result['Checks']['FileLabels']['Status'])
        evaluate.assert_not_called()
        self.assertTrue(v.public_error('PRIVATE_SENTINEL 123456')['UnclassifiedDetails'])

    def test_exception_with_broken_stringification_still_returns_safe_partial_receipt(self):
        class BadException(Exception):
            def __str__(self):
                raise RuntimeError('PRIVATE_SENTINEL')
        def broken(settings, *_):
            settings['identity'] = {'side_effect': BadException()}
        result, _, _ = self.run_case(override=broken)
        self.assertEqual('FAILED', result['Checks']['Identity']['Status'])
        self.assertTrue(result['Failure']['SafeServiceEvidence']['UnclassifiedDetails'])

    def test_exact_build_dax_query_and_unchanged_business_helpers(self):
        before = (HERE / 'VERIFY INSTALLED TEST R03.py').read_bytes()
        b.build(HERE, RELEASE / 'VERIFY INSTALLED TEST R01.py')
        self.assertEqual(before, (HERE / 'VERIFY INSTALLED TEST R03.py').read_bytes())
        count_cases = load('r02_engine_counter_contract', RELEASE / 'metadata_count_cases.py')
        self.assertEqual(count_cases.current_query(), v.FILE_COUNT_QUERY)
        old_tree = ast.parse((RELEASE / 'VERIFY INSTALLED TEST R01.py').read_text())
        new_tree = ast.parse(before.decode(), feature_version=(3, 10))
        funcs = lambda tree: {node.name: ast.dump(node, include_attributes=False) for node in tree.body if isinstance(node, ast.FunctionDef)}
        old, new = funcs(old_tree), funcs(new_tree)
        for name in ('preflight', 'scalar', 'semantic_dates', 'validate_dates', 'physical_dates', 'normalized', 'read_private'):
            self.assertEqual(old[name], new[name], name)
        functions = {node.name: node for node in ast.walk(new_tree) if isinstance(node, ast.FunctionDef)}
        todo, seen = ['verify_installed_r03'], set()
        while todo:
            name = todo.pop()
            if name in seen or name not in functions:
                continue
            seen.add(name)
            for node in ast.walk(functions[name]):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                    todo.append(node.func.id)
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {'post', 'put', 'delete', 'patch', 'mkdirs'}:
                    self.assertEqual('post', node.func.attr)
                    self.assertIn('getDefinition', ast.unparse(node.args[0]))
        self.assertNotIn('install', seen)
        self.assertNotIn('verified_backup', seen)


if __name__ == '__main__':
    unittest.main()
