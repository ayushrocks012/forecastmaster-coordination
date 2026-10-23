"""Future diagnostic verifier candidate; current R02 operator action is unchanged."""


def verify_installed_r03(client, pbi, fs, evaluate, spark=None):
    result = {'Stage': 'TEST_R178_VERIFICATION_STOPPED', 'Revision': 'R01', 'VerifierRevision': 'R03',
              'TestModelID': TEST, 'ModelWriteRequested': False, 'OriginalModelWriteRequested': False,
              'LakehouseTableWriteRequested': False, 'RefreshRequested': False,
              'CompanyAmountValuesPrintedOrStored': False, 'ReportPublished': False,
              'Checks': {name: {'Status': 'SKIPPED_DEPENDENCY'} for name in CHECK_NAMES},
              'NextStep': 'Send this complete JSON. Keep backups. No install, refresh, reset, publication or blind retry.'}
    active = None

    def check(name, callback):
        nonlocal active
        active = name
        start = time.monotonic()
        result['Checks'][name] = {'Status': 'RUNNING'}
        try:
            value = callback()
        except (Exception, KeyboardInterrupt):
            result['Checks'][name] = {'Status': 'FAILED', 'ElapsedMs': round((time.monotonic() - start) * 1000)}
            raise
        result['Checks'][name] = {'Status': 'PASSED', 'ElapsedMs': round((time.monotonic() - start) * 1000)}
        return value

    try:
        check('Identity', lambda: identity(client, {}))

        def receipts():
            marker = read_private(fs, ATTEMPT)
            folder = marker.get('Backup')
            require(marker.get('Revision') == 'R01' and marker.get('TEST') == TEST
                    and isinstance(folder, str) and folder.startswith(RELEASE_PRIVATE + '/'), 'ATTEMPT_RECEIPT_UNEXPECTED')
            success = read_private(fs, folder + '/success.json')
            require(success.get('Stage') == 'TEST_R178_UPDATED', 'INSTALL_NOT_VERIFIED')
            installed = parsed_time(success.get('InstalledAtUTC'))
            require(installed is not None, 'INSTALL_TIMESTAMP_INVALID')
            result['InstalledAtUTC'] = installed.isoformat()
            return folder, installed
        folder, installed = check('InstallReceipts', receipts)

        def refresh():
            response = http({}, pbi.get('https://api.powerbi.com/v1.0/myorg/groups/' + WORKSPACE
                + '/datasets/' + TEST + '/refreshes?$top=60'), {200})
            payload = response.json()
            rows = payload.get('value') if isinstance(payload, dict) else None
            result['RefreshHistory'] = history_evidence(rows)
            require(rows and rows[0].get('status') == 'Completed', 'TEST_REFRESH_NOT_COMPLETED')
            stamp = parsed_time(rows[0].get('startTime'))
            require(stamp is not None, 'REFRESH_TIMESTAMP_INVALID')
            require(stamp >= installed, 'NEW_ADAPTER_REFRESH_NOT_CONFIRMED')
            require(result['RefreshHistory']['NonTerminalOrUnrecognized'] == 0, 'TEST_PROCESSING_ACTIVE_OR_UNKNOWN')
            return rows
        jobs_before = check('RefreshHistory', refresh)

        def candidate():
            wanted = read_private(fs, folder + '/definition-candidate.json')
            original = read_private(fs, folder + '/definition-before.json')
            expected_db = json.loads(base64.b64decode(next(p for p in wanted['parts'] if p['path'] == 'model.bim')['payload']))
            _, current, _ = read_definition(client, {})
            require(normalized(current) == normalized(expected_db), 'INSTALLED_DEFINITION_DIFFERS')
            return expected_db, original
        expected_db, original = check('CandidateDefinition', candidate)

        def cloud():
            mapping = read_private(fs, folder + '/connections-before.json')
            require(connections(client, {}) == mapping, 'CLOUD_MAPPING_CHANGED')
            return mapping
        mapping = check('CloudMapping', cloud)
        check('QuietProcessing', lambda: require(processing_history(pbi) == jobs_before, 'CONCURRENT_PROCESSING_OR_SOURCE_CHANGE'))

        def physical():
            require(spark is not None, 'SPARK_DATE_METADATA_READER_UNAVAILABLE')
            return physical_dates(spark, fs, {})
        expected_dates = check('PhysicalDates', physical)

        def semantic():
            actual = date_signature(evaluate)
            result['PhysicalSemanticDateGroups'] = compare(expected_dates, actual)
            require(all_match(result['PhysicalSemanticDateGroups']), 'PHYSICAL_SEMANTIC_DATES_DIFFER')
            result['Dates'] = validate_dates(evaluate)
            return actual
        actual_dates = check('SemanticDates', semantic)

        def numeric():
            before_db = json.loads(base64.b64decode(next(p for p in original['parts'] if p['path'] == 'model.bim')['payload']))
            old = {t['name']: t for t in before_db['model']['tables']}['fm_native_measures']['measures']
            return preflight(evaluate, {m['name']: expression_text(m['expression']) for m in old})
        result['NumericalComparisonToPrivateBaseline'] = check('NumericalParity', numeric)

        def labels():
            rows = evaluate(dataset=TEST, dax_string=FILE_COUNT_QUERY, workspace=WORKSPACE,
                            verbose=0, use_readwrite_connection=False).to_dict(orient='records')
            require(len(rows) == 1, 'FILE_LABEL_CHECK_UNAVAILABLE')
            counts = {k.rsplit('[', 1)[-1].rstrip(']'): metadata_integer(v, k.rsplit('[', 1)[-1].rstrip(']')
                       in {'MissingImportedAt', 'HashSuffixes'}) for k, v in rows[0].items()}
            require(set(counts) == {'Files', 'Choices', 'MissingImportedAt', 'HashSuffixes'}, 'FILE_LABEL_COLUMNS_UNEXPECTED')
            require(counts['Files'] > 0 and counts['Files'] == counts['Choices'] and counts['HashSuffixes'] == 0
                    and counts['MissingImportedAt'] == 0,
                    'FILE_CHOICE_LABELS_INVALID')
            return counts
        result['FileLabelCounts'] = check('FileLabels', labels)

        def consistency():
            require(processing_history(pbi) == jobs_before and date_signature(evaluate) == actual_dates,
                    'CONCURRENT_PROCESSING_OR_SOURCE_CHANGE')
            _, final, _ = read_definition(client, {})
            require(normalized(final) == normalized(expected_db) and connections(client, {}) == mapping,
                    'CONCURRENT_DEFINITION_OR_MAPPING_CHANGE')
        check('FinalConsistency', consistency)
        result.update(Stage='TEST_R178_INSTALLED_AND_BOUNDED_CHECKS_VERIFIED',
                      FullCandidateMetadataMatches=True, CloudMappingPreserved=True,
                      NextStep='Return this JSON. Company native workflow, independent reference/export and comparable performance still need separate evidence. Do not publish.')
    except (Exception, KeyboardInterrupt) as exc:
        result['Failure'] = safe_failure(exc)
        result['Failure']['Check'] = active
        result['Failure']['SafeServiceEvidence'] = public_exception(exc)
        first = result.get('RefreshHistory', {}).get('FirstEntry')
        if first and first['Status'] != 'Completed':
            result['NextStep'] = ('Return JSON; exact history category and operation link are included. '
                                  'Inspect that operation if error details remain unclassified. Do not refresh or select an older success.')
    print(json.dumps(result, indent=2), flush=True)
    return result
