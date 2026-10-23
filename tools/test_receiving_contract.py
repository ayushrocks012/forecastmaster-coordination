"""Fabricated files exercise the actual admission rules; no company data."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('contract', HERE / 'receiving_contract.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
SHA = 'a' * 64


def timing():
    return {'EvidenceKind': 'COMPANY_OPERATOR_REVIEWED', 'ArtifactSHA256': SHA,
            'Context': {'EnvironmentFingerprint': SHA, 'SelectionFingerprint': SHA,
                        'SourceSnapshotFingerprint': SHA, 'CacheState': 'warm', 'View': 'Total'},
            'Runs': [{name: {'DAX': 100, 'Total': 150} for name in c.VISUALS}], 'ResourceErrorsObserved': False}


def slice_receipt(report_sha):
    return {'EvidenceKind': 'COMPANY_OPERATOR_REVIEWED', 'ArtifactSHA256': report_sha,
            'Context': timing()['Context'], 'IndependentReferenceMatch': True, 'ReferenceFingerprint': SHA,
            'Checks': {name: {'Passed': True, 'EvidenceSHA256': SHA} for name in c.SLICE_CHECKS}}


def verified_receipt():
    return {'Stage': 'TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED', 'TestModelID': 'SYNTHETIC_TEST',
            'VerifierRevision': 'R02', 'FullCandidateMetadataMatches': True, 'CloudMappingPreserved': True,
            **{name: False for name in ('ModelWriteRequested', 'OriginalModelWriteRequested', 'LakehouseTableWriteRequested',
                                       'RefreshRequested', 'CompanyAmountValuesPrintedOrStored', 'ReportPublished')},
            'Dates': {'Groups': 9, 'InvalidDates': 0, 'MatchingSourceNativeAndMonthSets': True},
            'PhysicalSemanticDateGroups': {name: {'PhysicalExpectedRows': 3, 'SemanticRows': 3,
                'InvalidSemanticDates': 0, 'ExactRowsMatch': True} for name in ('Axis', 'End', 'Facts', 'NativeEF',
                'NativeIMS', 'Review', 'SourceEF', 'SourceIMS', 'Start')},
            'NumericalComparisonToPrivateBaseline': {'PairedScalarComparisons': 12, 'Mismatches': 0, 'ValuesPrintedOrStored': False},
            'FileLabelCounts': {'Files': 8, 'Choices': 8, 'MissingImportedAt': 0, 'HashSuffixes': 0}}


class Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = {'Files': {}, 'ReceivingQualification': {
            'SchemaVersion': 1, 'TestModelID': 'SYNTHETIC_TEST', 'Facts': {
                'known': {'Classification': 'VERIFIED', 'EvidenceKind': 'LOCAL_SYNTHETIC', 'Scope': 'fabricated metadata',
                          'Evidence': {'Path': 'feedback/logs/known.json', 'Pointer': '/Observed', 'Equals': True}},
                'unknown': {'Classification': 'UNKNOWN', 'Scope': 'root cause unknown', 'Evidence': None}},
            'CurrentReport': 'report.zip', 'Handoffs': {},
            'Gates': {name: {'Evidence': None, 'EvidenceKind': 'COMPANY_OPERATOR_REVIEWED'}
                      for name in ('installed_verification', 'representative_flow', 'performance')}}}
        self.write('feedback/logs/known.json', {'Observed': True})
        self.write('report.zip', 'FABRICATED REPORT BYTES')
        self.report_sha = self.manifest['Files']['report.zip']['SHA256']

    def write(self, name, value):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value))
        raw = path.read_bytes()
        self.manifest['Files'][name] = {'Bytes': len(raw), 'SHA256': hashlib.sha256(raw).hexdigest()}
        return path

    def test_maintenance_reports_pending_without_promoting_company_acceptance(self):
        result = c.admit(self.root, self.manifest, 'maintenance')
        self.assertEqual({'PENDING'}, set(result['Gates'].values()))
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'expand-report')
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'claim-performance')

    def test_fact_contradiction_unknown_promotion_and_unqualified_inference_refused(self):
        original = deepcopy(self.manifest)
        for change in (lambda f: f['known']['Evidence'].update(Equals=False),
                       lambda f: f['unknown'].update(Classification='VERIFIED'),
                       lambda f: f['known'].update(Classification='INFERRED'),
                       lambda f: f['known'].update(Classification='ASSUMED')):
            self.manifest = deepcopy(original)
            change(self.manifest['ReceivingQualification']['Facts'])
            with self.assertRaises(c.Refused):
                c.check_contract(self.root, self.manifest)

    def test_inference_with_bound_support_and_explicit_caveat_is_labelled(self):
        fact = self.manifest['ReceivingQualification']['Facts']['known']
        fact.update(Classification='INFERRED', Caveat='Fixture inference, no company proof')
        self.assertEqual('RECEIVING_CONTRACT_VALID', c.check_contract(self.root, self.manifest)['Stage'])

    def test_changed_missing_or_outside_artifact_and_boolean_type_mismatch_refused(self):
        for path in ('../escape.json', str(self.root / 'report.zip'), 'missing.json'):
            with self.assertRaises(c.Refused):
                c.bound_file(self.root, self.manifest, path)
        (self.root / 'report.zip').write_bytes(b'CHANGED')
        with self.assertRaises(c.Refused):
            c.check_contract(self.root, self.manifest)
        self.write('report.zip', 'FABRICATED REPORT BYTES')
        self.write('feedback/logs/known.json', {'Observed': 1})
        with self.assertRaises(c.Refused):
            c.check_contract(self.root, self.manifest)

    def test_handoff_requires_exact_cell_qualification_cases_and_complete_instructions(self):
        self.write('cell.py', 'FABRICATED CELL')
        proof = {'Stage': 'LOCAL_CHECKER_QUALIFIED', 'ArtifactSHA256': self.manifest['Files']['cell.py']['SHA256'],
                 'Failures': 0, 'Cases': ['healthy', 'blank_zero', 'missing_date', 'malformed', 'cancelled',
                                         'concurrent', 'failed_then_recovered', 'safe_errors', 'unknown_category']}
        self.write('proof.json', proof)
        handoff = {'Artifact': 'cell.py', 'LocalQualification': 'proof.json', 'OperatorEnabled': False,
                   **{name: 'Declared fixture instruction' for name in ('Where', 'ReadWriteScope', 'ExpectedMarker',
                                                                      'StopCondition', 'NextAction', 'RetryBasis')}}
        self.manifest['ReceivingQualification']['Handoffs']['candidate'] = handoff
        c.check_contract(self.root, self.manifest)
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'operator-handoff', 'candidate')
        handoff['OperatorEnabled'] = True
        c.admit(self.root, self.manifest, 'operator-handoff', 'candidate')
        del handoff['StopCondition']
        with self.assertRaises(c.Refused):
            c.check_contract(self.root, self.manifest)
        handoff['StopCondition'] = 'STOPPED'
        proof['Cases'].remove('malformed')
        self.write('proof.json', proof)
        with self.assertRaises(c.Refused):
            c.check_contract(self.root, self.manifest)

    def test_local_pass_cannot_satisfy_company_gate(self):
        gate = self.manifest['ReceivingQualification']['Gates']['installed_verification']
        self.write('feedback/logs/verified.json', verified_receipt())
        gate.update(Evidence='feedback/logs/verified.json', ResultPointer='', EvidenceKind='LOCAL')
        with self.assertRaises(c.Refused):
            c.check_contract(self.root, self.manifest)

    def test_complete_bound_representative_flow_required_before_expansion(self):
        gates = self.manifest['ReceivingQualification']['Gates']
        self.write('feedback/logs/verified.json', verified_receipt())
        gates['installed_verification'].update(Evidence='feedback/logs/verified.json', ResultPointer='')
        evidence = slice_receipt(self.report_sha)
        self.write('feedback/logs/slice.json', evidence)
        gates['representative_flow']['Evidence'] = 'feedback/logs/slice.json'
        c.admit(self.root, self.manifest, 'expand-report')
        for key in ('file_selection', 'monthly_chart', 'native_layout'):
            broken = deepcopy(evidence)
            broken['Checks'][key]['Passed'] = False
            self.write('feedback/logs/slice.json', broken)
            with self.assertRaises(c.Refused):
                c.admit(self.root, self.manifest, 'expand-report')
        broken = deepcopy(evidence)
        broken['IndependentReferenceMatch'] = None
        self.write('feedback/logs/slice.json', broken)
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'expand-report')

    def test_fabricated_rendering_or_different_artifact_cannot_pass_slice(self):
        for change in ({'EvidenceKind': 'LOCAL_SYNTHETIC'}, {'ArtifactSHA256': 'b' * 64}):
            with self.assertRaises(c.Refused):
                c.representative_slice({**slice_receipt(self.report_sha), **change}, self.report_sha)

    def test_old_automatic_fallback_cannot_satisfy_new_empty_file_rule(self):
        evidence = slice_receipt(self.report_sha)
        evidence['Checks']['empty_file_selection']['Passed'] = False
        with self.assertRaises(c.Refused):
            c.representative_slice(evidence, self.report_sha)
        evidence['Checks']['clear_to_automatic'] = evidence['Checks'].pop('empty_file_selection')
        evidence['Checks']['clear_to_automatic']['Passed'] = True
        with self.assertRaises(c.Refused):
            c.representative_slice(evidence, self.report_sha)
        self.assertEqual('PASSED_WITHIN_REVIEWED_SLICE',
                         c.representative_slice(slice_receipt(self.report_sha), self.report_sha))

    def test_success_word_alone_cannot_promote_missing_or_failed_receiving_evidence(self):
        for change in (lambda row: row.pop('Dates'),
                       lambda row: row.update(FullCandidateMetadataMatches=False),
                       lambda row: row['NumericalComparisonToPrivateBaseline'].update(Mismatches=1),
                       lambda row: row['PhysicalSemanticDateGroups']['Axis'].update(ExactRowsMatch=False),
                       lambda row: row['FileLabelCounts'].update(HashSuffixes=1),
                       lambda row: row['Dates'].update(InvalidDates=False),
                       lambda row: row['NumericalComparisonToPrivateBaseline'].update(Mismatches=False),
                       lambda row: row.update(TestModelID='DIFFERENT')):
            row = verified_receipt()
            change(row)
            with self.assertRaises(c.Refused):
                c.installed_verification(row, 'SYNTHETIC_TEST')

    def test_comparable_timings_report_medians_and_signed_change(self):
        before, after = timing(), timing()
        after['ArtifactSHA256'] = 'b' * 64
        after['Runs'][0]['MonthlyGraph'] = {'DAX': 80, 'Total': 120}
        result = c.compare_performance(before, after)
        self.assertEqual(-20, result['Visuals']['MonthlyGraph']['DAX']['ChangeMs'])
        self.assertEqual(20, result['Visuals']['MonthlyGraph']['DAX']['ImprovementPercent'])

    def test_unknown_or_different_selection_data_cache_environment_and_view_refuse_speed_claim(self):
        for key, value in (('SelectionFingerprint', 'b' * 64), ('SourceSnapshotFingerprint', 'b' * 64),
                           ('EnvironmentFingerprint', 'b' * 64), ('CacheState', 'cold'), ('View', 'Sectors'),
                           ('CacheState', 'UNKNOWN')):
            before, after = timing(), timing()
            after['Context'][key] = value
            with self.assertRaises(c.Refused):
                c.compare_performance(before, after)

    def test_invalid_missing_synthetic_or_resource_error_timings_refused(self):
        for change in (lambda value: value.update(EvidenceKind='LOCAL_SYNTHETIC'),
                       lambda value: value.update(ResourceErrorsObserved=True),
                       lambda value: value.update(Runs=[]),
                       lambda value: value['Runs'][0].pop('ReviewSummary'),
                       lambda value: value['Runs'][0]['MonthlyGraph'].update(DAX=None),
                       lambda value: value['Runs'][0]['MonthlyGraph'].update(DAX=float('nan')),
                       lambda value: value['Runs'][0]['MonthlyGraph'].update(DAX=True),
                       lambda value: value['Runs'][0]['MonthlyGraph'].update(DAX=-1),
                       lambda value: value['Runs'][0]['MonthlyGraph'].update(DAX=160)):
            before, after = timing(), timing()
            change(after)
            with self.assertRaises(c.Refused):
                c.compare_performance(before, after)

    def test_zero_timing_is_preserved_without_inventing_percentage(self):
        before, after = timing(), timing()
        before['Runs'][0]['MonthlyGraph'] = {'DAX': 0, 'Total': 0}
        result = c.compare_performance(before, after)
        self.assertIsNone(result['Visuals']['MonthlyGraph']['DAX']['ImprovementPercent'])
        self.assertEqual(100, result['Visuals']['MonthlyGraph']['DAX']['ChangeMs'])

    def test_blank_templates_are_not_acceptance_evidence(self):
        with self.assertRaises(c.Refused):
            c.representative_slice(c.evidence_template('slice'), self.report_sha)
        with self.assertRaises(c.Refused):
            c.performance_sample(c.evidence_template('performance'))

    def test_comparison_stage_cannot_hide_different_raw_context_or_report(self):
        before, after = timing(), timing()
        after['ArtifactSHA256'] = self.report_sha
        result = c.compare_performance(before, after)
        self.write('feedback/logs/comparison.json', result)
        self.write('feedback/logs/before.json', before)
        self.write('feedback/logs/after.json', after)
        self.manifest['ReceivingQualification']['Gates']['performance'].update(
            Evidence='feedback/logs/comparison.json', Baseline='feedback/logs/before.json', Candidate='feedback/logs/after.json')
        c.admit(self.root, self.manifest, 'claim-performance')
        after['ArtifactSHA256'] = 'b' * 64
        self.write('feedback/logs/after.json', after)
        self.write('feedback/logs/comparison.json', c.compare_performance(before, after))
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'claim-performance')
        after['ArtifactSHA256'] = self.report_sha
        after['Context']['CacheState'] = 'cold'
        self.write('feedback/logs/after.json', after)
        with self.assertRaises(c.Refused):
            c.admit(self.root, self.manifest, 'claim-performance')


if __name__ == '__main__':
    unittest.main()
