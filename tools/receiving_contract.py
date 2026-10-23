"""Local admission checks for the existing handoff manifest; no cloud access."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import statistics


class Refused(ValueError):
    """An unsupported claim, changed artifact or incomplete gate."""


def require(ok, reason):
    if not ok:
        raise Refused(reason)


def fingerprint(value):
    return isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def bound_file(root, manifest, name):
    require(isinstance(name, str) and not Path(name).is_absolute() and '..' not in Path(name).parts,
            'Evidence path must stay within the handoff')
    root = root.resolve()
    path = (root / name).resolve()
    require(path.is_relative_to(root) and path.is_file(), 'Evidence file unavailable: ' + name)
    expected = manifest['Files'].get(name)
    raw = path.read_bytes()
    require(isinstance(expected, dict) and expected.get('Bytes') == len(raw)
            and expected.get('SHA256') == hashlib.sha256(raw).hexdigest(), 'Unbound or changed file: ' + name)
    return path


def pointer(value, path):
    require(isinstance(path, str) and (not path or path.startswith('/')), 'Invalid JSON pointer')
    for part in path.split('/')[1:]:
        part = part.replace('~1', '/').replace('~0', '~')
        try:
            value = value[int(part)] if isinstance(value, list) else value[part]
        except (KeyError, IndexError, ValueError, TypeError):
            raise Refused('Evidence does not contain declared pointer: ' + path) from None
    return value


def observation(root, manifest, binding):
    require(isinstance(binding, dict) and set(binding) == {'Path', 'Pointer', 'Equals'}, 'Invalid evidence binding')
    value = json.loads(bound_file(root, manifest, binding['Path']).read_text())
    actual = pointer(value, binding['Pointer'])
    require(type(actual) is type(binding['Equals']) and actual == binding['Equals'],
            'Evidence contradicts declared fact: ' + binding['Path'] + binding['Pointer'])
    return value


SLICE_CHECKS = {'file_selection', 'source_cutoff', 'review_summary', 'monthly_chart',
                'executive_variance', 'drill_expand', 'clear_to_automatic', 'native_layout'}
VISUALS = {'MonthlyGraph', 'ReviewSummary', 'ExecutiveSummary'}
CONTEXT_KEYS = {'EnvironmentFingerprint', 'SelectionFingerprint', 'SourceSnapshotFingerprint', 'CacheState', 'View'}


def context(value):
    require(isinstance(value, dict) and set(value) == CONTEXT_KEYS, 'Incomplete receiving/performance context')
    require(all(fingerprint(value[k]) for k in CONTEXT_KEYS if k.endswith('Fingerprint')), 'Unknown context fingerprint')
    require(value['CacheState'] in {'cold', 'warm', 'first_observed_load', 'repeated_same_selection'}
            and value['View'] in {'Total', 'Drivers', 'Sectors'},
            'Cache state and view must be observed')


def representative_slice(value, report_sha):
    require(value.get('EvidenceKind') == 'COMPANY_OPERATOR_REVIEWED', 'Local evidence cannot pass the company slice')
    require(value.get('ArtifactSHA256') == report_sha and fingerprint(report_sha), 'Slice belongs to another report')
    context(value.get('Context'))
    require(value.get('IndependentReferenceMatch') is True and fingerprint(value.get('ReferenceFingerprint')),
            'Independent reviewed reference comparison missing')
    checks = value.get('Checks')
    require(isinstance(checks, dict) and set(checks) == SLICE_CHECKS, 'Incomplete representative workflow population')
    for name, check in checks.items():
        require(isinstance(check, dict) and check.get('Passed') is True
                and fingerprint(check.get('EvidenceSHA256')), 'Unreviewed slice step: ' + name)
    return 'PASSED_WITHIN_REVIEWED_SLICE'


def installed_verification(value, test_id):
    require(value.get('Stage') == 'TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED'
            and value.get('TestModelID') == test_id and value.get('VerifierRevision') in {'R02', 'R03'},
            'Installed verification is incomplete or targets another version/model')
    require(all(value.get(key) is False for key in ('ModelWriteRequested', 'OriginalModelWriteRequested',
            'LakehouseTableWriteRequested', 'RefreshRequested', 'CompanyAmountValuesPrintedOrStored', 'ReportPublished')),
            'Receiving verifier action declarations are incomplete')
    require(value.get('FullCandidateMetadataMatches') is True and value.get('CloudMappingPreserved') is True,
            'Metadata/cloud mapping evidence incomplete')
    dates = value.get('Dates', {})
    require(type(dates.get('Groups')) is int and dates['Groups'] == 9
            and type(dates.get('InvalidDates')) is int and dates['InvalidDates'] == 0
            and dates.get('MatchingSourceNativeAndMonthSets') is True, 'Date summary is incomplete')
    groups = value.get('PhysicalSemanticDateGroups')
    require(isinstance(groups, dict) and set(groups) == {'Axis', 'End', 'Facts', 'NativeEF', 'NativeIMS',
                                                       'Review', 'SourceEF', 'SourceIMS', 'Start'}, 'Nine exact date groups required')
    for group in groups.values():
        require(isinstance(group, dict) and type(group.get('PhysicalExpectedRows')) is int
                and group['PhysicalExpectedRows'] > 0 and type(group.get('SemanticRows')) is int
                and group['SemanticRows'] == group['PhysicalExpectedRows']
                and type(group.get('InvalidSemanticDates')) is int and group['InvalidSemanticDates'] == 0
                and group.get('ExactRowsMatch') is True,
                'Date-group parity failed or unavailable')
    numbers = value.get('NumericalComparisonToPrivateBaseline', {})
    require(type(numbers.get('PairedScalarComparisons')) is int and numbers['PairedScalarComparisons'] == 12
            and type(numbers.get('Mismatches')) is int and numbers['Mismatches'] == 0
            and numbers.get('ValuesPrintedOrStored') is False, 'Bounded numerical proof incomplete')
    labels = value.get('FileLabelCounts', {})
    require(type(labels.get('Files')) is int and labels['Files'] > 0
            and type(labels.get('Choices')) is int and labels['Choices'] == labels['Files']
            and type(labels.get('HashSuffixes')) is int and labels['HashSuffixes'] == 0
            and type(labels.get('MissingImportedAt')) is int and labels['MissingImportedAt'] == 0,
            'Readable unique file-choice/import evidence incomplete')
    return 'PASSED_WITHIN_BOUNDED_VERIFIER_SCOPE'


def performance_sample(value):
    require(value.get('EvidenceKind') == 'COMPANY_OPERATOR_REVIEWED', 'Synthetic timing is not company performance')
    require(fingerprint(value.get('ArtifactSHA256')), 'Performance artifact not identified')
    context(value.get('Context'))
    runs = value.get('Runs')
    require(isinstance(runs, list) and runs, 'No measured runs')
    for run in runs:
        require(isinstance(run, dict) and set(run) == VISUALS, 'Incomplete visual timing population')
        for metrics in run.values():
            require(isinstance(metrics, dict) and set(metrics) == {'DAX', 'Total'}, 'Incomplete timing metrics')
            require(all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        and math.isfinite(v) and v >= 0 for v in metrics.values()), 'Invalid or missing timing')
            require(metrics['Total'] >= metrics['DAX'], 'Total time cannot precede its DAX duration')
    require(value.get('ResourceErrorsObserved') is False, 'Unresolved resource errors prevent a speed claim')


def compare_performance(before, after):
    performance_sample(before)
    performance_sample(after)
    require(before['Context'] == after['Context'], 'Different selection, data, environment, view or cache state')
    rows = {}
    for visual in sorted(VISUALS):
        rows[visual] = {}
        for metric in ('DAX', 'Total'):
            old = statistics.median(run[visual][metric] for run in before['Runs'])
            new = statistics.median(run[visual][metric] for run in after['Runs'])
            rows[visual][metric] = {'BeforeMs': old, 'AfterMs': new, 'ChangeMs': new - old,
                                   'ImprovementPercent': (old - new) / old * 100 if old else None}
    return {'Stage': 'COMPARABLE_COMPANY_TIMINGS', 'Scope': before['Context'],
            'BeforeRuns': len(before['Runs']), 'AfterRuns': len(after['Runs']), 'Visuals': rows,
            'Interpretation': 'Measured context only; no broader speed or production-readiness claim'}


def check_contract(root, manifest):
    contract = manifest.get('ReceivingQualification')
    require(isinstance(contract, dict) and contract.get('SchemaVersion') == 1, 'Receiving contract missing or unsupported')
    facts = contract.get('Facts')
    require(isinstance(facts, dict) and facts, 'No classified evidence facts')
    for name, fact in facts.items():
        require(fact.get('Classification') in {'VERIFIED', 'INFERRED', 'UNKNOWN'} and fact.get('Scope'), 'Unclassified fact: ' + name)
        if fact['Classification'] == 'UNKNOWN':
            require(fact.get('Evidence') is None, 'Unknown fact cannot carry a passed assertion')
        else:
            require(fact.get('EvidenceKind') in {'LOCAL_SYNTHETIC', 'COMPANY_OPERATOR_REVIEWED'}, 'Evidence provenance missing: ' + name)
            require(fact['EvidenceKind'] != 'COMPANY_OPERATOR_REVIEWED'
                    or fact['Evidence']['Path'].startswith('feedback/logs/'), 'Company fact must bind a reviewed company receipt')
            observation(root, manifest, fact.get('Evidence'))
        if fact['Classification'] == 'INFERRED':
            require(fact.get('Caveat'), 'Inference needs its uncertainty: ' + name)
    artifact = contract['CurrentReport']
    report = bound_file(root, manifest, artifact)
    report_sha = hashlib.sha256(report.read_bytes()).hexdigest()
    for name, candidate in contract.get('Handoffs', {}).items():
        require(type(candidate.get('OperatorEnabled')) is bool, 'Handoff enabled state missing: ' + name)
        for key in ('Where', 'ReadWriteScope', 'ExpectedMarker', 'StopCondition', 'NextAction', 'RetryBasis'):
            require(isinstance(candidate.get(key), str) and candidate[key].strip(), 'Incomplete operator instructions: ' + name + '/' + key)
        bound_file(root, manifest, candidate['Artifact'])
        proof = json.loads(bound_file(root, manifest, candidate['LocalQualification']).read_text())
        require(proof.get('ArtifactSHA256') == manifest['Files'][candidate['Artifact']]['SHA256'], 'Qualification targets different cell')
        require(proof.get('Stage') == 'LOCAL_CHECKER_QUALIFIED' and type(proof.get('Failures')) is int
                and proof['Failures'] == 0,
                'Checker qualification not passed')
        require(set(proof.get('Cases', [])) >= {'healthy', 'blank_zero', 'missing_date', 'malformed',
                'cancelled', 'concurrent', 'failed_then_recovered', 'safe_errors', 'unknown_category'}, 'Missing checker regression classes')
    gates = {}
    for name, gate in contract.get('Gates', {}).items():
        source = gate.get('Evidence')
        if source is None:
            gates[name] = 'PENDING'
            continue
        require(gate.get('EvidenceKind') == 'COMPANY_OPERATOR_REVIEWED'
                and isinstance(source, str) and source.startswith('feedback/logs/'), 'Company gate requires reviewed company evidence')
        value = json.loads(bound_file(root, manifest, source).read_text())
        if name == 'representative_flow':
            gates[name] = representative_slice(value, report_sha)
        elif name == 'installed_verification':
            gates[name] = installed_verification(pointer(value, gate['ResultPointer']), contract['TestModelID'])
        elif name == 'performance':
            require(value.get('Stage') == 'COMPARABLE_COMPANY_TIMINGS', 'Unqualified speed claim')
            # Recompute from bound raw timing receipts; never trust a self-declared comparison stage.
            baseline = json.loads(bound_file(root, manifest, gate['Baseline']).read_text())
            candidate = json.loads(bound_file(root, manifest, gate['Candidate']).read_text())
            require(candidate.get('ArtifactSHA256') == report_sha, 'Timing candidate belongs to another report')
            require(value == compare_performance(baseline, candidate), 'Timing comparison does not reproduce')
            gates[name] = 'COMPARABLE_WITHIN_CONTEXT'
        else:
            raise Refused('Unsupported gate kind: ' + name)
    require(set(gates) == {'installed_verification', 'representative_flow', 'performance'}, 'Receiving gates incomplete')
    return {'Stage': 'RECEIVING_CONTRACT_VALID', 'Gates': gates, 'CompanyAcceptance': 'SEPARATE; never implied by file hashes'}


def admit(root, manifest, purpose, handoff=None):
    result = check_contract(root, manifest)
    if purpose == 'expand-report':
        require(result['Gates']['installed_verification'].startswith('PASSED')
                and result['Gates']['representative_flow'].startswith('PASSED'), 'Representative company flow still pending; broad report expansion refused')
    elif purpose == 'claim-performance':
        require(result['Gates']['performance'] == 'COMPARABLE_WITHIN_CONTEXT', 'Comparable company performance evidence pending')
    elif purpose == 'operator-handoff':
        candidate = manifest['ReceivingQualification']['Handoffs'].get(handoff)
        require(candidate is not None and candidate['OperatorEnabled'] is True, 'Candidate not selected for the operator; current main-chat handoff is unchanged')
    else:
        require(purpose == 'maintenance', 'Unknown admission purpose')
    result['Purpose'] = purpose
    return result


def evidence_template(kind):
    # Nulls are deliberately incomplete and cannot be admitted as a pass.
    shared = {'EvidenceKind': 'COMPANY_OPERATOR_REVIEWED', 'ArtifactSHA256': None,
              'Context': {key: None for key in sorted(CONTEXT_KEYS)}}
    if kind == 'slice':
        return {**shared, 'IndependentReferenceMatch': None, 'ReferenceFingerprint': None,
                'Checks': {name: {'Passed': None, 'EvidenceSHA256': None} for name in sorted(SLICE_CHECKS)}}
    require(kind == 'performance', 'Unsupported evidence template')
    return {**shared, 'Runs': [{name: {'DAX': None, 'Total': None} for name in sorted(VISUALS)}],
            'ResourceErrorsObserved': None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--purpose', choices=['maintenance', 'expand-report', 'claim-performance', 'operator-handoff'], default='maintenance')
    parser.add_argument('--handoff')
    parser.add_argument('--emit-template', choices=['slice', 'performance'])
    parser.add_argument('--fingerprint-json', type=Path)
    parser.add_argument('--compare-performance', nargs=2, type=Path, metavar=('BASELINE_JSON', 'CANDIDATE_JSON'))
    args = parser.parse_args()
    try:
        require(sum(bool(value) for value in (args.compare_performance, args.emit_template, args.fingerprint_json)) <= 1,
                'Choose only one evidence operation')
        if args.emit_template:
            result = evidence_template(args.emit_template)
        elif args.fingerprint_json:
            canonical = json.dumps(json.loads(args.fingerprint_json.read_text()), sort_keys=True, separators=(',', ':'), ensure_ascii=False)
            result = {'SHA256': hashlib.sha256(canonical.encode()).hexdigest(), 'SourceContentsPrinted': False}
        elif args.compare_performance:
            result = compare_performance(*(json.loads(p.read_text()) for p in args.compare_performance))
        else:
            root = Path(__file__).resolve().parents[1]
            result = admit(root, json.loads((root / 'HANDOFF-MANIFEST.json').read_text()), args.purpose, args.handoff)
        print(json.dumps(result, indent=2))
    except (Refused, KeyError, TypeError, ValueError, OSError) as exc:
        # Local public contract files only; never a raw company API error.
        raise SystemExit('REFUSED: ' + str(exc)) from None


if __name__ == '__main__':
    main()
