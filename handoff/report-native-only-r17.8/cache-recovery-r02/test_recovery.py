"""Synthetic state/route/privacy and numerical-sanity tests, not company acceptance."""
import ast
from contextlib import redirect_stdout
from datetime import date, datetime, timezone
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.parse import unquote, urlsplit

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r178_recovery', HERE / 'RECOVER AND DIAGNOSE TEST R02.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
OLD = HERE.parent / 'cache-reset-r01/RESET TEST DATE CACHE R01.py'
RID = ['20000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000002',
       '20000000-0000-4000-8000-000000000003']
START = '2026-10-23T20:43:00Z'; END = '2026-10-23T20:44:00Z'
FULL_START = '2026-10-23T20:44:01Z'; FULL_END = '2026-10-23T20:45:00Z'


class Response:
    def __init__(self, data, status=200, headers=None):
        self.data = data; self.status_code = status; self.headers = headers or {}
    def json(self): return self.data


class Frame:
    def __init__(self, data): self.data = data
    def to_dict(self, orient): return self.data


def snapshot():
    expr = 'AzureStorage.DataLake("https://onelake.dfs.fabric.microsoft.com/' + p.WORKSPACE + '/' + p.LAKEHOUSE + '")'
    tables = [{'name': t, 'partitions': [{'mode': 'directLake', 'source': {'expressionSource': 'DL'}}]}
              for t in p.FIELDS]
    tables.extend([{'name': 'fm_native_files'}, {'name': 'fm_native_measures',
                   'measures': [{'name': v} for v in p.PROBE_FIELDS.values()]}])
    db = {'model': {'tables': tables, 'expressions': [{'name': 'DL', 'expression': expr}]}}
    bindings = {t: {'PartitionCount': 1, 'Mode': 'directLake', 'SourceType': 'entity',
       'EntityNameMatchesExpected': True, 'Columns': {c: {'ModelDataType': 'dateTime',
       'SourceColumnMatchesExpected': True} for c in cs}} for t, cs in p.FIELDS.items()}
    return {'parts': [{'path': 'model.bim', 'payload': 'PRIVATE_DEFINITION'}]}, db, bindings


def dates():
    return {k: [('PRIVATE_SOURCE' if k.endswith(('IMS', 'EF')) else '', '2026-01-01')] for k in p.KINDS}


class FS:
    def __init__(self):
        self.files = {}; self.writes = []; self.corrupt = False
        self.seed(p.PRIVATE + '/ATTEMPT.json', {'Revision': 'R01', 'TEST': p.TEST, 'Backup': p.BACKUP,
                    'Action': 'clearValues then full; run once'})
        self.seed(p.BACKUP + '/definition-before.json', snapshot()[0])
        self.seed(p.BACKUP + '/connections-before.json', [{'id': 'PRIVATE_CONNECTION'}])
        self.seed(p.BACKUP + '/date-counts-before.json', p.compare(dates(), dates()))
    def seed(self, path, value): self.files[path] = json.dumps(value, ensure_ascii=False).encode()
    def exists(self, path): return path in self.files
    def put(self, path, text, overwrite):
        self.writes.append(path)
        assert overwrite is False
        if path in self.files: return False
        self.files[path] = text.encode(); return True
    def cp(self, src, dst, recurse):
        Path(unquote(urlsplit(dst).path)).write_bytes(self.files[src] + (b'INVALID' if self.corrupt else b'')); return True


class Fabric:
    def __init__(self): self.calls = []; self.wrong = False; self.mapping = [{'id': 'PRIVATE_CONNECTION'}]
    def get(self, path):
        self.calls.append(path)
        if path == p.ITEM: return Response({'id': 'WRONG' if self.wrong else p.TEST, 'displayName': p.NAME, 'type': 'SemanticModel'})
        if path == p.ITEM + '/connections': return Response({'value': self.mapping})
        raise AssertionError('Unexpected Fabric route')


class PBI:
    def __init__(self):
        self.jobs = {RID[0]: {'type': 'ClearValues', 'startTime': START, 'endTime': END,
                    'status': 'Completed', 'extendedStatus': 'Completed'}}
        self.calls = []; self.posts = []; self.lost = False; self.header = 'regional'
        self.pending = 0; self.no_history = False
    def add_full(self, status='Completed'):
        self.jobs[RID[1]] = {'type': 'Full', 'startTime': FULL_START, 'endTime': FULL_END,
                            'status': status, 'extendedStatus': status}
    def get(self, url):
        self.calls.append(url)
        assert url.startswith(p.PBI_BASE + '/refreshes')
        if url == p.PBI_BASE + '/refreshes?$top=60':
            return Response({'value': [{'requestId': rid, 'startTime': j['startTime'], 'status': j['status']}
                          for rid, j in self.jobs.items() if not self.no_history or rid != RID[1]]})
        rid = url.rsplit('/', 1)[-1]; j = dict(self.jobs[rid])
        if self.pending:
            self.pending -= 1
            j.update(status='Unknown', extendedStatus='InProgress'); j.pop('endTime', None)
            return Response(j, 202)
        return Response(j)
    def post(self, url, json):
        assert url == p.PBI_BASE + '/refreshes'; assert json['type'] == 'full'
        self.posts.append(json); self.add_full()
        if self.lost: raise RuntimeError('PRIVATE_LOST_RESPONSE')
        headers = {
            'regional': {'Location': 'https://regional.example/v1.0/myorg/groups/' + p.WORKSPACE + '/datasets/' + p.TEST + '/refreshes/' + RID[1] + '?ct=PRIVATE_QUERY'},
            'relative': {'Location': '/refreshes/' + RID[1] + '/'},
            'canonical': {'Location': p.PBI_BASE + '/refreshes/' + RID[1]},
            'missing': {}, 'request': {'x-ms-request-id': RID[1]},
            'correlation': {'x-ms-request-id': RID[2]},
            'conflicting': {'x-ms-request-id': RID[2], 'Location': '/refreshes/' + RID[1]},
        }[self.header]
        return Response({}, 202, headers)


class Tests(unittest.TestCase):
    def run_case(self, pbi=None, fs=None, client=None, bad_dates=False, bad_physical=False,
                 changed=False, bad_guard=False, numeric=None, interrupted=False):
        pbi = pbi or PBI(); fs = fs or FS(); client = client or Fabric(); output = io.StringIO(); definitions = [0]
        def definition(*args):
            definitions[0] += 1
            value = snapshot()
            if changed and (changed == 'before' or definitions[0] >= (4 if changed == 'numeric' else 3)):
                value[0]['changed'] = 'PRIVATE_CHANGE'
            return value
        def physical(*args):
            if bad_physical: raise p.CheckStopped('PHYSICAL_DATES_INVALID_NO_RESET')
            return dates()
        def semantic(*args):
            value = dates()
            if bad_dates: value['Axis'] = [('', '1899-12-30')]
            return value
        def counts(evaluate, dax, fields):
            if fields == p.FILE_FIELDS:
                return {k: (3 if k in {'SourceRows', 'NativeRows'} else 2 if k == 'AutomaticADSSources' else 0) for k in fields}
            return {k: (100 if k == 'AvailableScopeRows' else 0 if bad_guard and k == 'CutoffValid' else 1) for k in fields}
        def read_numeric(**kwargs):
            self.assertFalse(kwargs['use_readwrite_connection'])
            if interrupted: raise KeyboardInterrupt()
            dax = kwargs['dax_string']
            vals = {'N Plan': 10., 'N Benchmark': 8., 'N Variance': 2., 'N Variance %': .25, 'N Trend Monthly': 8.5}
            if numeric: return numeric(kwargs)
            name = next(name for name in vals if '[' + name + ']' in dax)
            return Frame([{'[Value]': vals[name]}])
        with redirect_stdout(output), patch.object(p, 'read_definition', side_effect=definition), \
             patch.object(p, 'physical_dates', side_effect=physical), patch.object(p, 'semantic_dates', side_effect=semantic), \
             patch.object(p, 'metadata_counts', side_effect=counts), patch.object(p, 'source_scope',
             return_value={'Country': 'UK', 'Cycle': '2026-10', 'Driver': 'PRIVATE_DRIVER'}), \
             patch.object(p, 'engine_date_boundary', return_value={kind: {'Rows': 1, 'EngineBlankDates': 0,
                'EngineOutOfRangeOrBlankDates': 0, 'ClientTypedDayDisagreesWithEngineText': 0,
                'EngineDaysMatchPhysical': True} for kind in p.KINDS}), \
             patch.object(p, 'source_signature', return_value='PRIVATE_SIGNATURE'), patch.object(p.time, 'sleep'):
            result = p.run(client, pbi, read_numeric, None, fs)
        for token in ('PRIVATE_DEFINITION', 'PRIVATE_CONNECTION', 'PRIVATE_DRIVER', 'PRIVATE_SOURCE',
                      'PRIVATE_SIGNATURE', 'PRIVATE_QUERY', 'PRIVATE_CHANGE', 'PRIVATE_LOST_RESPONSE'):
            self.assertNotIn(token, output.getvalue())
        json.dumps(result, allow_nan=False)
        return result, pbi, fs

    def test_missing_full_recovered_once_and_all_ninety_scalars_pass(self):
        r, api, fs = self.run_case()
        self.assertEqual('TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED', r['Stage'])
        self.assertEqual(1, len(api.posts)); self.assertEqual([p.RESUME_MARKER], fs.writes)
        self.assertEqual({'type': 'full', 'commitMode': 'transactional', 'maxParallelism': 1,
                          'retryCount': 0, 'applyRefreshPolicy': False, 'timeout': '00:15:00'}, api.posts[0])
        data = r['Checks']['PrivateScalarChecks']['Data']
        self.assertEqual(90, data['ScalarQueriesSubmitted']); self.assertEqual(18, len(data['Groups']))
        self.assertTrue(r['CompanyAmountQuerySubmitted']); self.assertFalse(r['IndependentBusinessParityVerified'])
        for field in ('ModelDefinitionWriteRequested', 'LakehouseTableWriteRequested', 'OriginalModelWriteRequested',
             'CompanyAmountsPrintedOrStoredByScript', 'RawErrorsOrSourceRecordsPrinted', 'ReportPublished',
             'NativeR178AdapterInstalled', 'DesktopRenderingVerified'):
            self.assertIs(False, r[field])

    def test_header_variants_never_supply_network_endpoints(self):
        for header in ('regional', 'relative', 'canonical', 'missing', 'request', 'correlation', 'conflicting'):
            with self.subTest(header=header):
                api = PBI(); api.header = header
                r, api, _ = self.run_case(pbi=api)
                self.assertEqual('TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED', r['Stage'])
                self.assertTrue(all(url.startswith(p.PBI_BASE) for url in api.calls))

    def test_existing_full_reused_even_when_resume_marker_exists(self):
        api = PBI(); api.add_full(); fs = FS(); fs.seed(p.RESUME_MARKER, {'private': 'PRIOR'})
        r, api, fs = self.run_case(pbi=api, fs=fs)
        self.assertEqual('TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED', r['Stage'])
        self.assertTrue(r['Processing']['ExistingFullReused']); self.assertFalse(api.posts); self.assertFalse(fs.writes)

    def test_existing_failed_full_is_never_retried(self):
        api = PBI(); api.add_full('Failed')
        r, api, fs = self.run_case(pbi=api)
        self.assertFalse(r['KnownFullCompleted']); self.assertFalse(api.posts)
        self.assertEqual('FAILED', r['Checks']['WaitExistingFull']['Status'])
        self.assertEqual('SKIPPED', r['Checks']['PrivateScalarChecks']['Status'])

    def test_unknown_prior_submission_marker_without_history_refuses_post(self):
        fs = FS(); fs.seed(p.RESUME_MARKER, {'private': 'PRIOR'})
        r, api, _ = self.run_case(fs=fs)
        self.assertEqual('FULL_RESUME_ALREADY_ATTEMPTED_NO_RESUBMIT', r['Checks']['MissingFullRecovery']['Failure']['Reason'])
        self.assertFalse(api.posts)

    def test_lost_response_retains_possible_write_and_never_retries(self):
        api = PBI(); api.lost = True
        r, api, fs = self.run_case(pbi=api)
        self.assertEqual(1, len(api.posts)); self.assertTrue(r['Processing']['FullSubmissionAttemptedHere'])
        self.assertFalse(r['Processing']['FullResponseReceived']); self.assertIn(p.RESUME_MARKER, fs.files)
        self.assertTrue(r['Processing']['FullSubmissionOutcomeInitiallyUnknown'])
        self.assertTrue(r['KnownFullCompleted'])
        self.assertEqual('TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED', r['Stage'])

    def test_lost_response_without_history_holds_and_never_retries(self):
        api = PBI(); api.lost = True; api.no_history = True
        r, api, _ = self.run_case(pbi=api)
        self.assertEqual(1, len(api.posts)); self.assertFalse(r['KnownFullCompleted'])
        self.assertTrue(r['Processing']['FullSubmissionOutcomeInitiallyUnknown'])

    def test_accepted_but_no_history_never_resubmits(self):
        api = PBI(); api.no_history = True
        r, api, _ = self.run_case(pbi=api)
        self.assertEqual(1, len(api.posts))
        self.assertEqual('FULL_ACCEPTED_HISTORY_NOT_VISIBLE_NO_RESUBMIT', r['Checks']['MissingFullRecovery']['Failure']['Reason'])

    def test_wrong_identity_has_no_other_reads_or_processing(self):
        client = Fabric(); client.wrong = True
        r, api, fs = self.run_case(client=client)
        self.assertEqual(['ExactTESTIdentity'], list(r['Checks'])); self.assertFalse(api.calls); self.assertFalse(fs.writes)

    def test_missing_backup_or_wrong_marker_still_keeps_safe_independent_reads(self):
        for mode in ('missing', 'mismatch'):
            fs = FS()
            if mode == 'missing': del fs.files[p.BACKUP + '/definition-before.json']
            else: fs.seed(p.PRIVATE + '/ATTEMPT.json', {'WRONG': True})
            r, api, _ = self.run_case(fs=fs)
            self.assertEqual('FAILED', r['Checks']['PinnedR01Backup']['Status'])
            self.assertEqual('READ_COMPLETED', r['Checks']['PhysicalDatesAfter']['Status'])
            self.assertEqual('READ_COMPLETED', r['Checks']['AcceptedRefreshHistory']['Status']); self.assertFalse(api.posts)

    def test_changed_definition_or_mapping_prevents_full(self):
        r, api, _ = self.run_case(changed='before')
        self.assertFalse(r['BeforeDefinitionAndCloudMatchBackup']); self.assertFalse(api.posts)
        client = Fabric(); client.mapping = [{'id': 'OTHER'}]
        r, api, _ = self.run_case(client=client)
        self.assertFalse(r['CloudConnectionPreserved']); self.assertFalse(api.posts)

    def test_failed_physical_check_does_not_erase_other_diagnostics(self):
        r, api, _ = self.run_case(bad_physical=True)
        self.assertFalse(api.posts); self.assertEqual('READ_COMPLETED', r['Checks']['DefinitionAfter']['Status'])
        self.assertEqual('FAILED', r['Checks']['PhysicalDatesAfter']['Status'])

    def test_full_completed_does_not_override_bad_dates_or_guards(self):
        for kwargs in ({'bad_dates': True}, {'bad_guard': True}):
            r, api, _ = self.run_case(**kwargs)
            self.assertTrue(r['KnownFullCompleted']); self.assertFalse(r['CompanyAmountQuerySubmitted'])
            self.assertEqual('TEST_R178_DEEP_DIAGNOSTICS_NEEDS_REVIEW', r['Stage'])
            self.assertEqual('READ_COMPLETED', r['Checks']['FilesMetadata']['Status'])
            self.assertEqual('READ_COMPLETED', r['Checks']['SelectionGuards']['Status'])

    def test_refresh_warnings_need_review(self):
        api = PBI(); api.add_full(); api.jobs[RID[1]]['messages'] = [{'message': 'PRIVATE_CONNECTION'}]
        r, _, _ = self.run_case(pbi=api)
        self.assertTrue(r['ProcessingMessagesRequireReview']); self.assertEqual('TEST_R178_DEEP_DIAGNOSTICS_NEEDS_REVIEW', r['Stage'])

    def test_failed_or_ambiguous_clear_never_submits(self):
        for mode in ('failed', 'missing', 'duplicate', 'wrong_type', 'unknown_status'):
            api = PBI()
            if mode == 'failed': api.jobs[RID[0]].update(status='Failed', extendedStatus='Failed')
            if mode == 'missing': api.jobs.clear()
            if mode == 'duplicate': api.jobs[RID[2]] = dict(api.jobs[RID[0]])
            if mode == 'wrong_type': api.jobs[RID[0]]['type'] = 'Calculate'
            if mode == 'unknown_status': api.jobs[RID[0]]['status'] = 'OTHER'
            r, api, _ = self.run_case(pbi=api)
            self.assertFalse(api.posts); self.assertFalse(r['KnownFullCompleted'])

    def test_running_202_clear_is_confirmed_before_full(self):
        api = PBI(); api.pending = 2
        r, api, _ = self.run_case(pbi=api)
        self.assertEqual('TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED', r['Stage'])
        self.assertEqual('Completed', r['Processing']['ClearValues']['Status'])

    def test_history_coverage_and_time_fail_closed(self):
        class History(PBI):
            def __init__(self, rows): super().__init__(); self.rows = rows
            def get(self, url):
                if '?$top=60' in url: return Response({'value': self.rows})
                return super().get(url)
        for rows in ([{'requestId': RID[0], 'status': 'Completed'}],
                     [{'requestId': str(__import__('uuid').UUID(int=i+1)), 'status': 'Completed', 'startTime': START} for i in range(60)]):
            with self.assertRaises(p.CheckStopped): p.history(History(rows), {})
        self.assertEqual(p.utc('2026-10-23T20:43:00'), p.utc(START))

    def test_pending_timeout_keeps_correct_refresh_status_and_never_posts(self):
        api = PBI(); api.pending = 99999
        out = io.StringIO(); ticks = iter((0, 1300)); job = p.detail(api, RID[0], {})
        with redirect_stdout(out), patch.object(p.time, 'monotonic', side_effect=lambda: next(ticks)):
            state = {}
            with self.assertRaises(p.CheckStopped) as caught: p.wait_job(api, job, state, {})
        self.assertEqual('TEST_PROCESSING_OUTCOME_UNCONFIRMED', caught.exception.code)
        self.assertEqual('Unknown', state['ClearValues']['Status']); self.assertFalse(api.posts)

    def test_history_changes_after_preflight_prevent_post(self):
        api = PBI(); fs = FS(); expected = p.read_jobs(api, {})
        api.add_full()
        with self.assertRaises(p.CheckStopped) as caught: p.submit_missing_full(api, fs, {}, {}, expected)
        self.assertEqual('REFRESH_HISTORY_CHANGED_BEFORE_SUBMIT', caught.exception.code)
        self.assertFalse(api.posts); self.assertFalse(fs.writes)

    def test_failed_detail_retains_prior_history_in_safe_context(self):
        api = PBI(); api.jobs[RID[0]]['type'] = 'Calculate'
        r, _, _ = self.run_case(pbi=api)
        self.assertEqual(RID[0], r['Checks']['AcceptedRefreshHistory']['Context']['RefreshHistory'][0]['ID'])

    def test_complete_full_before_clear_finishes_refused(self):
        api = PBI(); api.add_full(); api.jobs[RID[1]]['startTime'] = START
        r, api, _ = self.run_case(pbi=api)
        self.assertFalse(api.posts); self.assertFalse(r['KnownFullCompleted'])

    def test_numeric_mismatch_is_retained_and_not_passed(self):
        r, _, _ = self.run_case(numeric=lambda _: Frame([{'Value': 10.}]))
        data = r['Checks']['PrivateScalarChecks']['Data']
        self.assertEqual(90, data['ScalarQueriesSubmitted']); self.assertEqual('NEEDS_REVIEW', data['Status'])
        self.assertFalse(r['BoundedInternalCalculationChecksPassed'])

    def test_numeric_blank_and_nonfinite_do_not_become_zero_or_pass(self):
        for value in (None, float('nan'), float('inf'), True, 'PRIVATE_VALUE'):
            r, _, _ = self.run_case(numeric=lambda _, v=value: Frame([{'Value': v}]))
            self.assertFalse(r['BoundedInternalCalculationChecksPassed']); self.assertNotIn('PRIVATE_VALUE', json.dumps(r))

    def test_known_service_failure_aborts_remaining_amount_reads_but_keeps_metadata(self):
        def memory(_): raise RuntimeError('PRIVATE_CONNECTION query memory limit exceeded')
        r, _, _ = self.run_case(numeric=memory)
        data = r['Checks']['PrivateScalarChecks']['Data']
        self.assertEqual(1, data['ScalarQueriesSubmitted']); self.assertEqual(18, len(data['Groups']))
        self.assertEqual('READ_COMPLETED', r['Checks']['MetadataAfterProbes']['Status'])
        self.assertEqual('READ_COMPLETED', r['Checks']['PhysicalDatesAfterProbes']['Status'])

    def test_interrupt_keeps_partial_safe_progress_and_never_continues(self):
        r, api, _ = self.run_case(interrupted=True)
        self.assertEqual('TEST_R178_DEEP_DIAGNOSTICS_INTERRUPTED', r['Stage'])
        self.assertEqual(1, r['PrivateScalarProgress']['ScalarQueriesSubmitted'])
        self.assertNotIn('MetadataAfterProbes', r['Checks']); self.assertEqual(1, len(api.posts))

    def test_numeric_dependency_change_prevents_success(self):
        r, _, _ = self.run_case(changed='numeric')
        self.assertFalse(r['NumericMetadataStable']); self.assertEqual('TEST_R178_DEEP_DIAGNOSTICS_NEEDS_REVIEW', r['Stage'])

    def test_another_processing_job_during_numeric_reads_cannot_qualify(self):
        api = PBI()
        def change(_):
            api.jobs[RID[2]] = dict(api.jobs[RID[1]])
            return Frame([{'Value': 10.}])
        r, _, _ = self.run_case(pbi=api, numeric=change)
        self.assertFalse(r['NumericProcessingStable'])
        self.assertEqual('FAILED', r['Checks']['RefreshHistoryAfterProbes']['Status'])

    def test_exact_dates_check_ids_and_values_not_just_count_or_range(self):
        a = dates(); b = dates(); b['Axis'] = [('', '2026-02-01')]; b['SourceIMS'] = [('OTHER', '2026-01-01')]
        result = p.compare(a, b)
        self.assertFalse(result['Axis']['ExactRowsMatch']); self.assertEqual(0, result['Axis']['InvalidSemanticDates'])
        self.assertFalse(result['SourceIMS']['ExactRowsMatch'])
        self.assertIsNone(p.as_date(datetime(2026, 1, 1, 2)))

    def test_engine_text_and_client_typed_dates_compared_without_outputting_dates(self):
        def frame(**kw):
            self.assertIn('FORMAT([D],"yyyy-MM-dd")', kw['dax_string'])
            self.assertIn('YEAR([D])', kw['dax_string']); self.assertNotIn('[Amount]', kw['dax_string'])
            return Frame([{'Kind': kind, 'ID': ident, 'D': date(2026, 1, 1), 'EngineDay': day,
                           'EngineYear': 2026, 'EngineBlank': 0} for kind, pairs in dates().items() for ident, day in pairs])
        result = p.engine_date_boundary(frame, dates())
        self.assertTrue(all(row['EngineDaysMatchPhysical'] for row in result.values()))
        self.assertNotIn('2026-01-01', json.dumps(result)); self.assertNotIn('PRIVATE_SOURCE', json.dumps(result))

    def test_engine_vs_client_disagreement_is_classified(self):
        def frame(**kw):
            return Frame([{'Kind': 'Axis', 'ID': '', 'D': date(1899, 12, 30), 'EngineDay': '2026-01-01',
                           'EngineYear': 2026, 'EngineBlank': 0}])
        result = p.engine_date_boundary(frame, dates())['Axis']
        self.assertTrue(result['EngineDaysMatchPhysical']); self.assertEqual(1, result['ClientTypedDayDisagreesWithEngineText'])

    def test_engine_wrong_dates_are_separate_from_client_conversion(self):
        def frame(**kw):
            return Frame([{'Kind': 'Axis', 'ID': '', 'D': date(1899, 12, 30), 'EngineDay': '1899-12-30',
                           'EngineYear': 1899, 'EngineBlank': 0}])
        result = p.engine_date_boundary(frame, dates())['Axis']
        self.assertFalse(result['EngineDaysMatchPhysical']); self.assertEqual(1, result['EngineOutOfRangeOrBlankDates'])
        self.assertEqual(0, result['ClientTypedDayDisagreesWithEngineText'])

    def test_engine_date_fields_fail_closed(self):
        with self.assertRaises(p.CheckStopped): p.engine_date_boundary(lambda **_: Frame([{'Secret': 'PRIVATE_SOURCE'}]), dates())

    def test_scalar_filters_private_escaping_and_single_cell_shape(self):
        scope = {'Country': 'UK', 'Cycle': '2026-10', 'Driver': 'A"B'}
        dax = p.scalar_query(scope, 'ef', 6, 2027, 'T')
        self.assertIn('A""B', dax); self.assertIn('DATE(2027,12,1)', dax)
        self.assertIn('"2027:FY"', dax); self.assertIn('[N Trend Monthly]', dax)
        self.assertEqual(1, dax.count('EVALUATE')); self.assertNotIn('DEFINE', dax)
        self.assertIn('[N Variance]', p.scalar_query(scope, 'share', 24, 2026, 'A'))
        with self.assertRaises(p.CheckStopped): p.scalar_query(scope, 'unknown', 24, 2026, 'P')

    def test_safe_error_categories_never_output_raw_error(self):
        result = p.safe_failure(RuntimeError('PRIVATE_AMOUNT memory limit exceeded; cancelled; permission denied'))
        self.assertEqual(['MEMORY_LIMIT', 'CANCELLED', 'ACCESS_OR_AUTHENTICATION'], result['KnownSignals'])
        self.assertNotIn('PRIVATE_AMOUNT', json.dumps(result))

    def test_metadata_frames_count_shapes_guard_semantics_and_source_cohort(self):
        def counts(**kwargs): return Frame([{'[SourceOK]': 1, '[Empty]': None}])
        self.assertEqual({'SourceOK': 1, 'Empty': 0}, p.metadata_counts(counts, 'EVALUATE ROW()', {'SourceOK', 'Empty'}))
        self.assertFalse(p.guards_valid({k: 0 for k in p.GUARD_FIELDS}))
        with self.assertRaises(p.CheckStopped): p.metadata_counts(counts, 'test', {'OTHER'})
        seen = []
        def cohort(**kw):
            seen.append(kw['dax_string'])
            return Frame([{'[Revision]': 'PRIVATE_SOURCE', '[Priority]': 1, '[Rank]': 1, '[Ties]': 1}])
        signature = p.source_signature(cohort)
        self.assertEqual(64, len(signature)); self.assertNotIn('[Amount]', seen[0])

    def test_scalar_negative_denominator_zero_and_blank_semantics(self):
        # The % contract uses ABS(benchmark); financial zero is not BLANK.
        values = {'N Plan': -10., 'N Benchmark': -8., 'N Variance': -2., 'N Variance %': -.25, 'N Trend Monthly': -8.5}
        def negative(kwargs):
            name = next(k for k in values if '[' + k + ']' in kwargs['dax_string'])
            return Frame([{'Value': values[name]}])
        r, _, _ = self.run_case(numeric=negative)
        self.assertTrue(r['BoundedInternalCalculationChecksPassed'])
        values.update({'N Plan': 0., 'N Benchmark': 0., 'N Variance': 0., 'N Variance %': None, 'N Trend Monthly': 0.})
        r, _, _ = self.run_case(numeric=negative)
        data = r['Checks']['PrivateScalarChecks']['Data']['Groups'][0]
        self.assertTrue(data['InternalVarianceIdentityMatches']); self.assertTrue(data['InternalPercentIdentityMatches'])
        self.assertFalse(data['Informative']); self.assertEqual('NUMERIC', data['Scalars']['P']['ValueState'])

    def test_unsafe_backup_count_fields_cannot_leak(self):
        fs = FS(); fs.seed(p.BACKUP + '/date-counts-before.json', {kind: {'Secret': 'PRIVATE_AMOUNT'} for kind in p.KINDS})
        with self.assertRaises(p.CheckStopped): p.load_backup(fs)
        with self.assertRaises(p.CheckStopped): p.read_private(fs, 'https://unrelated.example/secret')

    def test_utf8_full_marker_verification_corruption_refuses_post(self):
        fs = FS(); p.verified_backup(fs, p.RESUME_MARKER, {'text': 'SYNTHETIC café £'})
        self.assertIn('café'.encode(), fs.files[p.RESUME_MARKER])
        fs = FS()
        original = fs.cp
        def copy(src, dst, recurse):
            if src == p.RESUME_MARKER: fs.corrupt = True
            return original(src, dst, recurse)
        fs.cp = copy
        r, api, _ = self.run_case(fs=fs)
        self.assertFalse(api.posts); self.assertIn(p.RESUME_MARKER, fs.files)
        self.assertEqual('PRIVATE_BACKUP_FULL_UTF8_VERIFICATION_FAILED', r['Checks']['MissingFullRecovery']['Failure']['Reason'])

    def test_python310_static_write_routes_and_old_cell_frozen(self):
        source = (HERE / 'RECOVER AND DIAGNOSE TEST R02.py').read_text()
        tree = ast.parse(source, feature_version=(3, 10))
        posts = [ast.unparse(n) for n in ast.walk(tree) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute) and n.func.attr == 'post']
        self.assertEqual(2, len(posts)); self.assertTrue(any('/getDefinition?format=TMSL' in x for x in posts))
        self.assertTrue(any("PBI_BASE + '/refreshes'" in x and "'type': 'full'" in x for x in posts))
        for token in ('updateDefinition', 'saveAsTable', 'client.delete', "'type': 'clearValues'", 'fs.head('):
            self.assertNotIn(token, source)
        self.assertIn("'total': 0", source)
        self.assertEqual('a5135045e61623126cd3cc0ddb4e07da9beb25e82e1386f97bf1e44cc9fb12ff', hashlib.sha256(OLD.read_bytes()).hexdigest())


if __name__ == '__main__': unittest.main()
