"""Consolidated recovery and diagnostics appended by build.py.

One writer, no other TEST activity during this receiving run. All amount
observations are transient locals. Public output contains fixed labels/counts.
"""
BACKUP = PRIVATE + '/20261023T204254-cf53fe3f-50cf-4285-b947-49022c814164'
ANCHOR = '2026-10-23T20:42:54Z'
RESUME_MARKER = BACKUP + '/full-resume-r02.json'
TERMINAL = {'Completed', 'Failed', 'Disabled', 'Cancelled', 'Canceled', 'TimedOut'}
RUNNING = {'Unknown', 'NotStarted', 'InProgress'}
GUARD_FIELDS = {'SourceOK', 'CutoffValid', 'FitCutoffValid', 'PeriodAvailable',
                'MetricChoices', 'ScenarioChoices', 'AvailableScopeRows'}
FILE_FIELDS = {'SourceRows', 'NativeRows', 'AutomaticADSSources', 'SourceInvalidIMS',
 'SourceInvalidEF', 'NativeInvalidIMS', 'NativeInvalidEF', 'AutoInvalidIMS', 'AutoInvalidEF',
 'SourceIdsMissingNative', 'NativeIdsMissingSource', 'IMSMetadataMismatch', 'EFMetadataMismatch'}
PROBE_FIELDS = {'P': 'N Plan', 'B': 'N Benchmark', 'A': 'N Variance',
                'V': 'N Variance %', 'T': 'N Trend Monthly'}


def safe_failure(exc):
    # Inspect privately; output fixed allowlisted categories only, never messages.
    family = type(exc).__name__
    if family not in {'CheckStopped', 'RuntimeError', 'ValueError', 'TypeError', 'KeyError',
                      'TimeoutError', 'FabricAdomdException', 'ConnectionError', 'KeyboardInterrupt'}:
        family = 'OTHER_WITHHELD'
    signals = []
    try:
        raw = str(exc).lower()[:100000]
        for name, tokens in (
            ('MEMORY_LIMIT', ('memory limit', 'available resources', 'rsquerymemorylimitexceeded')),
            ('CANCELLED', ('cancelled', 'canceled', 'cancelation')),
            ('TIMEOUT', ('timeout', 'timed out')),
            ('ACCESS_OR_AUTHENTICATION', ('forbidden', 'unauthorized', 'permission')),
            ('QUERY_SYNTAX_OR_DEFINITION', ('syntax', 'semanticquerydefinition', 'cannot find', 'not found')),
            ('PROCESSING_REQUIRED', ('not processed', 'needs to be processed'))):
            if any(token in raw for token in tokens): signals.append(name)
    except Exception:
        pass
    return {'Reason': exc.code if isinstance(exc, CheckStopped) else 'EXCEPTION_WITHHELD',
            'ExceptionFamily': family, 'KnownSignals': signals, 'RawErrorPrintedOrStored': False}


def capture(report, name, action, summary=None):
    """Keep independent results and per-check context; never serialize private returns."""
    ctx = {}; started = time.monotonic()
    print('TEST batch: ' + name + '.', flush=True)
    try:
        value = action(ctx)
        record = {'Status': 'READ_COMPLETED'}
        if summary is not None: record['Data'] = summary(value)
        ok = True
    except Exception as exc:
        value = None; ok = False
        record = {'Status': 'FAILED', 'Failure': safe_failure(exc)}
    record['ElapsedMs'] = round((time.monotonic() - started) * 1000)
    # Each ctx is local, so a getDefinition status can never masquerade as refresh status.
    record['Context'] = {k: v for k, v in ctx.items() if k in
                        {'Step', 'Table', 'HTTPStatus', 'PollCount', 'OperationState',
                         'RefreshHistory', 'RefreshDetails'}}
    report['Checks'][name] = record
    return ok, value


def skip(report, name, reason):
    report['Checks'][name] = {'Status': 'SKIPPED', 'Reason': reason}


def read_private(fs, path):
    require(path in {PRIVATE + '/ATTEMPT.json', BACKUP + '/definition-before.json',
                    BACKUP + '/connections-before.json', BACKUP + '/date-counts-before.json', RESUME_MARKER},
            'PRIVATE_READ_PATH_NOT_PINNED')
    require(fs.exists(path), 'PINNED_PRIVATE_BACKUP_MISSING')
    with TemporaryDirectory(prefix='fm-recovery-read-') as temp:
        local = Path(temp) / 'private.json'
        require(fs.cp(path, local.as_uri(), False), 'PRIVATE_COPY_FAILED')
        require(0 < local.stat().st_size <= 64 * 1024 * 1024, 'PRIVATE_FILE_SIZE_UNEXPECTED')
        return json.loads(local.read_bytes().decode('utf-8'))


def load_backup(fs):
    marker = read_private(fs, PRIVATE + '/ATTEMPT.json')
    require(marker == {'Revision': 'R01', 'TEST': TEST, 'Backup': BACKUP,
                       'Action': 'clearValues then full; run once'}, 'R01_ATTEMPT_MARKER_MISMATCH')
    definition = read_private(fs, BACKUP + '/definition-before.json')
    mapping = read_private(fs, BACKUP + '/connections-before.json')
    counts_before = read_private(fs, BACKUP + '/date-counts-before.json')
    require(isinstance(definition, dict) and isinstance(definition.get('parts'), list) and
            isinstance(mapping, list) and set(counts_before) == KINDS, 'PINNED_BACKUP_SHAPE_UNEXPECTED')
    for row in counts_before.values():
        require(isinstance(row, dict) and set(row) == {'PhysicalExpectedRows', 'SemanticRows',
                'InvalidSemanticDates', 'ExactRowsMatch'} and type(row['ExactRowsMatch']) is bool and
                all(type(row[k]) is int and 0 <= row[k] <= 10000 for k in
                    ('PhysicalExpectedRows', 'SemanticRows', 'InvalidSemanticDates')),
                'BACKUP_DATE_COUNTS_INVALID')
    return definition, mapping, counts_before


def utc(value):
    require(isinstance(value, str) and bool(value), 'REFRESH_TIME_UNAVAILABLE')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return (parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed).astimezone(timezone.utc)
    except (ValueError, TypeError):
        raise CheckStopped('REFRESH_TIME_INVALID') from None


def uuid_or_none(value):
    try: return str(UUID(value))
    except (ValueError, TypeError, AttributeError): return None


def history(pbi, ctx):
    ctx['Step'] = 'TEST_REFRESH_HISTORY'
    rows = http(ctx, pbi.get(PBI_BASE + '/refreshes?$top=60'), {200}).json().get('value')
    require(isinstance(rows, list) and len(rows) <= 60, 'REFRESH_HISTORY_SHAPE_UNEXPECTED')
    items = []; seen = set()
    for row in rows:
        require(isinstance(row, dict), 'REFRESH_HISTORY_ROW_INVALID')
        started = utc(row.get('startTime')); rid = uuid_or_none(row.get('requestId'))
        require(rid is not None and rid not in seen, 'REFRESH_HISTORY_ID_AMBIGUOUS'); seen.add(rid)
        status = row.get('status')
        require(status in TERMINAL | RUNNING, 'REFRESH_HISTORY_STATUS_UNKNOWN')
        # Even a preceding operation still in progress blocks a submission.
        require(started >= utc(ANCHOR) or status in TERMINAL, 'OLDER_REFRESH_STILL_ACTIVE')
        if started >= utc(ANCHOR):
            items.append({'ID': rid, 'Start': started, 'Status': status})
    require(len(rows) < 60 or min(utc(row['startTime']) for row in rows) < utc(ANCHOR),
            'REFRESH_HISTORY_COVERAGE_INCOMPLETE')
    return sorted(items, key=lambda row: (row['Start'], row['ID']))


def detail(pbi, rid, ctx):
    require(uuid_or_none(rid) == rid, 'REFRESH_ID_INVALID')
    ctx['Step'] = 'TEST_REFRESH_DETAIL'
    response = http(ctx, pbi.get(PBI_BASE + '/refreshes/' + rid), {200, 202})
    data = response.json()
    require(isinstance(data, dict), 'REFRESH_DETAIL_SHAPE_UNEXPECTED')
    kind = data.get('type')
    require(kind in {'ClearValues', 'Full'}, 'REFRESH_TYPE_UNEXPECTED')
    status = data.get('status'); extended = data.get('extendedStatus', status)
    require(status in TERMINAL | RUNNING and extended in TERMINAL | RUNNING,
            'REFRESH_DETAIL_STATUS_UNKNOWN')
    messages = data.get('messages', [])
    require(isinstance(messages, list), 'REFRESH_MESSAGES_SHAPE_UNEXPECTED')
    start = utc(data.get('startTime'))
    end = utc(data['endTime']) if data.get('endTime') else None
    if status == 'Completed':
        require(response.status_code == 200 and extended == 'Completed' and end is not None and end >= start,
                'REFRESH_COMPLETION_INCONSISTENT')
    return {'ID': rid, 'Kind': kind, 'Status': status, 'Extended': extended,
            'Start': start, 'End': end, 'MessageCount': len(messages),
            'HTTPStatus': response.status_code}


def read_jobs(pbi, ctx):
    jobs = []
    rows = history(pbi, ctx)
    ctx['RefreshHistory'] = [{'ID': row['ID'], 'Status': row['Status'], 'StartUTC': row['Start'].isoformat()}
                             for row in rows]
    ctx['RefreshDetails'] = []
    for row in rows:
        item = detail(pbi, row['ID'], ctx)
        ctx['RefreshDetails'].append(job_summary(item))
        require(item['Start'] >= utc(ANCHOR) and item['Start'] == row['Start'],
                'REFRESH_HISTORY_DETAIL_TIME_MISMATCH')
        jobs.append(item)
    require(len(jobs) in {1, 2}, 'EXPECTED_SINGLE_CLEAR_AND_OPTIONAL_FULL')
    require(jobs[0]['Kind'] == 'ClearValues' and sum(j['Kind'] == 'ClearValues' for j in jobs) == 1,
            'ACCEPTED_CLEAR_NOT_UNIQUELY_IDENTIFIED')
    if len(jobs) == 2:
        require(jobs[1]['Kind'] == 'Full' and jobs[0]['End'] is not None and
                jobs[1]['Start'] >= jobs[0]['End'], 'FULL_NOT_AFTER_COMPLETED_CLEAR')
    return jobs


def job_summary(job):
    return {k: job[k] for k in ('ID', 'Kind', 'Status', 'Extended', 'MessageCount', 'HTTPStatus')}


def wait_job(pbi, job, state, ctx):
    deadline = time.monotonic() + 1200; polls = 0
    while True:
        state[job['Kind']] = job_summary(job)
        require(job['Status'] not in TERMINAL - {'Completed'} and
                job['Extended'] not in TERMINAL - {'Completed'}, 'TEST_PROCESSING_FAILED')
        if job['Status'] == 'Completed': return job
        require(job['Status'] in RUNNING and job['Extended'] in RUNNING, 'TEST_PROCESSING_STATE_UNEXPECTED')
        require(time.monotonic() < deadline, 'TEST_PROCESSING_OUTCOME_UNCONFIRMED')
        if polls % 6 == 0: print('TEST batch: waiting for known ' + job['Kind'] + ' request.', flush=True)
        time.sleep(5); polls += 1; ctx['PollCount'] = polls
        new = detail(pbi, job['ID'], ctx)
        require(new['Kind'] == job['Kind'] and new['Start'] == job['Start'], 'REFRESH_JOB_CHANGED')
        job = new


def header_ids(headers):
    """Extract IDs only; no URL from a response is ever followed."""
    h = {str(k).lower(): v for k, v in headers.items()}; ids = set()
    rid = uuid_or_none(h.get('x-ms-request-id'))
    if rid: ids.add(rid)
    location = h.get('location')
    if isinstance(location, str):
        try:
            path = urlsplit(location).path.rstrip('/')
            # Relative/regional/queried locations carry only an optional UUID hint.
            if '/refreshes/' in path:
                rid = uuid_or_none(path.rsplit('/refreshes/', 1)[1])
                if rid: ids.add(rid)
        except ValueError:
            pass
    return ids


def submit_missing_full(pbi, fs, state, ctx, expected_jobs):
    # Durable marker is written BEFORE the sole POST. It is never deleted/replaced.
    require(not fs.exists(RESUME_MARKER), 'FULL_RESUME_ALREADY_ATTEMPTED_NO_RESUBMIT')
    require(read_jobs(pbi, ctx) == expected_jobs, 'REFRESH_HISTORY_CHANGED_BEFORE_SUBMIT')
    submitted = datetime.now(timezone.utc)
    verified_backup(fs, RESUME_MARKER, {'Revision': 'R02', 'TEST': TEST, 'Backup': BACKUP,
                    'ClearRequestID': expected_jobs[0]['ID'], 'FullSubmitAfterUTC': submitted.isoformat(),
                    'Action': 'full only; never repeat clear or an ambiguous full'})
    state['FullSubmissionAttemptedHere'] = True
    # Lost response is an unknown outcome. No POST retry, even after a transport exception.
    try:
        response = pbi.post(PBI_BASE + '/refreshes', json={'type': 'full', 'commitMode': 'transactional',
                'maxParallelism': 1, 'retryCount': 0, 'applyRefreshPolicy': False, 'timeout': '00:15:00'})
    except Exception:
        state['FullResponseReceived'] = False
        state['FullSubmissionOutcomeInitiallyUnknown'] = True
        hints = set()
    else:
        http(ctx, response, {200, 202}); state['FullResponseReceived'] = True
        state['FullAcceptedHTTPStatus'] = response.status_code
        hints = header_ids(response.headers)
    state['FullHeaderIDCount'] = len(hints)
    # History pins the target, temporal order and request. Headers are hints only.
    for attempt in range(12):
        jobs = read_jobs(pbi, ctx)
        full = [j for j in jobs if j['Kind'] == 'Full']
        if full:
            # Exact before/after TEST history is authoritative. A header may be
            # a correlation ID; laptop/server clock skew must not lose a job.
            require(len(full) == 1 and full[0]['ID'] not in {j['ID'] for j in expected_jobs},
                    'NEW_FULL_IDENTITY_AMBIGUOUS')
            state['FullHeaderMatchedHistory'] = full[0]['ID'] in hints
            return full[0]
        if attempt < 11: time.sleep(5)
    raise CheckStopped('FULL_ACCEPTED_HISTORY_NOT_VISIBLE_NO_RESUBMIT')


def frame_rows(evaluate, dax):
    frame = evaluate(dataset=TEST, dax_string=dax, workspace=WORKSPACE, verbose=0,
                     use_readwrite_connection=False)
    return [{key.rsplit('[', 1)[-1].rstrip(']'): value for key, value in row.items()}
            for row in frame.to_dict(orient='records')]


def metadata_counts(evaluate, dax, fields):
    rows = frame_rows(evaluate, dax)
    require(len(rows) == 1 and set(rows[0]) == fields, 'METADATA_COUNT_SHAPE_UNEXPECTED')
    result = {}
    for key, value in rows[0].items():
        # COUNTROWS(empty) returns BLANK; only known cardinalities use zero.
        if value is None or isinstance(value, Number) and math.isnan(float(value)): value = 0
        require(not isinstance(value, bool) and isinstance(value, Number) and math.isfinite(float(value))
                and value >= 0 and int(value) == value, 'METADATA_COUNT_INVALID')
        result[key] = int(value)
    return result


def files_valid(counts):
    return counts['SourceRows'] > 0 and counts['SourceRows'] == counts['NativeRows'] and \
        counts['AutomaticADSSources'] > 0 and all(counts[k] == 0 for k in FILE_FIELDS -
                                  {'SourceRows', 'NativeRows', 'AutomaticADSSources'})


def guards_valid(counts):
    return counts['AvailableScopeRows'] > 0 and all(counts[k] == 1 for k in GUARD_FIELDS - {'AvailableScopeRows'})


def inventory(db):
    tables = db['model']['tables']; measures = [m for t in tables for m in t.get('measures', [])]
    modes = {k: sum(p.get('mode') == k for t in tables for p in t.get('partitions', []))
             for k in ('directLake', 'import', 'directQuery', 'default')}
    return {'TableCount': len(tables), 'MeasureCount': len(measures), 'PartitionModes': modes,
            'RelationshipCount': len(db['model'].get('relationships', [])),
            'RequiredProbeMeasuresPresent': all(any(m.get('name') == name for m in measures)
                                                for name in PROBE_FIELDS.values()),
            'DateBindings': 'CHECKED_SEPARATELY', 'RawDefinitionPrinted': False}


def engine_date_boundary(evaluate, expected):
    # Date text/YEAR are evaluated inside DAX, independently of SemPy's typed
    # datetime conversion. All dates/IDs stay private; output is aggregate flags.
    dax = 'EVALUATE\nVAR _dateRows=(\n' + DATE_QUERY.split('EVALUATE', 1)[1] + ''')
RETURN ADDCOLUMNS(_dateRows,
 "EngineDay",IF(ISBLANK([D]),BLANK(),FORMAT([D],"yyyy-MM-dd")),
 "EngineYear",IF(ISBLANK([D]),BLANK(),YEAR([D])),
 "EngineBlank",IF(ISBLANK([D]),1,0))'''
    rows = frame_rows(evaluate, dax)
    require(0 < len(rows) <= 10000, 'ENGINE_DATE_ROW_COUNT_UNEXPECTED')
    grouped = {kind: [] for kind in KINDS}
    for row in rows:
        require(set(row) == {'Kind', 'ID', 'D', 'EngineDay', 'EngineYear', 'EngineBlank'} and
                row['Kind'] in KINDS and isinstance(row['ID'], str), 'ENGINE_DATE_SHAPE_UNEXPECTED')
        require(row['EngineBlank'] in (0, 1), 'ENGINE_BLANK_FLAG_INVALID')
        grouped[row['Kind']].append(row)
    result = {}
    for kind, values in grouped.items():
        text_rows = []; invalid = 0; disagree = 0; blank = 0
        for row in values:
            blank += int(row['EngineBlank'])
            day = row['EngineDay'] if isinstance(row['EngineDay'], str) and row['EngineDay'] else None
            year = row['EngineYear']
            if row['EngineBlank'] or not isinstance(year, Number) or not 2000 <= year < 2100: invalid += 1
            if as_date(row['D']) != day: disagree += 1
            text_rows.append((row['ID'], day))
        result[kind] = {'Rows': len(values), 'EngineBlankDates': blank, 'EngineOutOfRangeOrBlankDates': invalid,
                        'ClientTypedDayDisagreesWithEngineText': disagree,
                        'EngineDaysMatchPhysical': expected is not None and len(text_rows) == len(expected[kind]) and
                                                   set(text_rows) == set(expected[kind])}
    return result


def source_scope(evaluate):
    # One available ADS driver in the exact reported UK/October scope; identities stay private.
    dax = '''EVALUATE SELECTCOLUMNS(TOPN(1,
FILTER(ALL('fm_native_files'),'fm_native_files'[Country]="UK"&&'fm_native_files'[DemandCycle]="2026-10"
&&'fm_native_files'[ADSPriority]>0&&'fm_native_files'[PreferenceRank]=1&&'fm_native_files'[PreferenceTies]=1),
'fm_native_files'[SourceRevisionID],ASC),"Country",'fm_native_files'[Country],
"Cycle",'fm_native_files'[DemandCycle],"Driver",'fm_native_files'[GrowthDriver])'''
    rows = frame_rows(evaluate, dax)
    require(len(rows) == 1 and set(rows[0]) == {'Country', 'Cycle', 'Driver'}, 'NUMERIC_SCOPE_UNAVAILABLE')
    scope = rows[0]
    require(scope['Country'] == 'UK' and scope['Cycle'] == '2026-10' and
            isinstance(scope['Driver'], str) and bool(scope['Driver'].strip()), 'NUMERIC_SCOPE_INVALID')
    return scope


def source_signature(evaluate):
    # The selected revision cohort is a dependency of every numeric comparison.
    dax = '''EVALUATE SELECTCOLUMNS(FILTER(ALL('fm_native_files'),
'fm_native_files'[Country]="UK"&&'fm_native_files'[DemandCycle]="2026-10"),
"Revision",'fm_native_files'[SourceRevisionID],"Priority",'fm_native_files'[ADSPriority],
"Rank",'fm_native_files'[PreferenceRank],"Ties",'fm_native_files'[PreferenceTies])'''
    rows = frame_rows(evaluate, dax)
    require(0 < len(rows) <= 1000 and all(set(row) == {'Revision', 'Priority', 'Rank', 'Ties'}
            and isinstance(row['Revision'], str) and bool(row['Revision']) for row in rows),
            'SOURCE_COHORT_METADATA_UNAVAILABLE')
    # No hash/ID is output. allow_nan=False refuses unavailable selection metadata.
    return hashlib.sha256(json.dumps(sorted(json.dumps(r, sort_keys=True, allow_nan=False)
                   for r in rows), ensure_ascii=False).encode()).hexdigest()


def text_filter(table, column, value):
    return 'TREATAS({"' + value.replace('"', '""') + '"},\'' + table + '\'[' + column + '])'


def scalar_query(scope, metric, window, year, field):
    require(metric in {'market', 'ef', 'share'} and window in {6, 12, 24} and field in PROBE_FIELDS,
            'UNKNOWN_SCALAR_CASE')
    f = [text_filter('fm_review_files', 'Country', scope['Country']),
         text_filter('fm_review_files', 'DemandCycle', scope['Cycle']),
         text_filter('fm_native_scope', 'GrowthDriver', scope['Driver']),
         text_filter('fm_native_file_mode', 'Mode', 'Automatic ADS'),
         text_filter('fm_native_scenario', 'Mode', 'Automatic ADS'),
         text_filter('fm_native_currency', 'Currency', 'Local'),
         text_filter('fm_native_display', 'Display', 'Units'),
         text_filter('fm_native_metric', 'RowID', metric),
         'TREATAS({' + str(window) + '},\'fm_native_trend\'[Window])',
         text_filter('fm_native_periods', 'PeriodKey', str(year) + ':FY')]
    if field == 'T': f.append('TREATAS({DATE(' + str(year) + ',12,1)},\'fm_review_axis\'[Month])')
    return 'EVALUATE ROW("Value",CALCULATE([' + PROBE_FIELDS[field] + '],' + ','.join(f) + '))'


def read_scalar(evaluate, dax):
    rows = frame_rows(evaluate, dax)
    require(len(rows) == 1 and set(rows[0]) == {'Value'}, 'SCALAR_RESULT_SHAPE_UNEXPECTED')
    value = rows[0]['Value']
    if value is None: return None
    require(not isinstance(value, bool) and isinstance(value, Number), 'SCALAR_NOT_NUMERIC')
    number = float(value)
    if math.isnan(number): return None
    require(math.isfinite(number), 'SCALAR_NOT_FINITE')
    return number


def equal_number(a, b):
    return a is None and b is None or a is not None and b is not None and math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-6)


def numeric_probes(evaluate, report, scope):
    started = time.monotonic(); groups = []; aborted = False; reads = 0
    progress = {'RequestedPopulation': 90, 'ScalarQueriesSubmitted': 0, 'Groups': groups}
    report['PrivateScalarProgress'] = progress
    for metric in ('market', 'ef', 'share'):
        for window in (6, 12, 24):
            for offset in (0, 1):
                row = {'Metric': metric, 'Window': window, 'YearOffset': offset, 'Scalars': {}}
                groups.append(row); values = {}; complete = True
                print('TEST batch: private scalar probes ' + metric + '/' + str(window) + 'M/year+' + str(offset) + '.', flush=True)
                for field in PROBE_FIELDS:
                    if aborted or time.monotonic() - started > 900:
                        row['Scalars'][field] = {'Status': 'SKIPPED', 'Reason': 'BATCH_BUDGET_OR_SERVICE_FAILURE'}
                        complete = False; aborted = True; continue
                    begin = time.monotonic()
                    report['CompanyAmountQuerySubmitted'] = True; reads += 1
                    progress['ScalarQueriesSubmitted'] = reads
                    try:
                        value = read_scalar(evaluate, scalar_query(scope, metric, window, 2026 + offset, field))
                        values[field] = value
                        row['Scalars'][field] = {'Status': 'READ_COMPLETED', 'ValueState': 'BLANK' if value is None else 'NUMERIC'}
                    except Exception as exc:
                        failure = safe_failure(exc); complete = False
                        row['Scalars'][field] = {'Status': 'FAILED', 'Failure': failure}
                        # A known cancellation/resource/auth problem is not an invitation to hammer the service.
                        if set(failure['KnownSignals']) & {'MEMORY_LIMIT', 'CANCELLED', 'TIMEOUT', 'ACCESS_OR_AUTHENTICATION'}:
                            aborted = True
                    row['Scalars'][field]['ElapsedMs'] = round((time.monotonic() - begin) * 1000)
                if complete:
                    p, b = values['P'], values['B']
                    expected_a = p - b if p is not None and b is not None else None
                    expected_v = expected_a / abs(b) if expected_a is not None and b != 0 else None
                    informative = all(values[k] is not None for k in ('P', 'B', 'T')) and b != 0
                    row['InternalVarianceIdentityMatches'] = equal_number(values['A'], expected_a)
                    row['InternalPercentIdentityMatches'] = equal_number(values['V'], expected_v)
                    row['Informative'] = informative
                    row['Status'] = 'PASSED' if informative and row['InternalVarianceIdentityMatches'] and row['InternalPercentIdentityMatches'] else 'NEEDS_REVIEW'
                else: row['Status'] = 'INCOMPLETE'
    report.pop('PrivateScalarProgress', None)
    return {'Status': 'PASSED' if all(g['Status'] == 'PASSED' for g in groups) else 'NEEDS_REVIEW',
            'Scope': 'ONE_AVAILABLE_UK_OCTOBER_ADS_DRIVER', 'RequestedPopulation': 90,
            'ScalarQueriesSubmitted': reads, 'Groups': groups,
            'IndependentBusinessParityVerified': False, 'ReportPerformanceVerified': False,
            'Interpretation': 'Execution and internal variance identities only; not Excel/R16.6 or full report parity.'}


def recover(client, pbi, fs, report, backup, current, mapping, physical_ok):
    state = report['Processing']
    ok, jobs = capture(report, 'AcceptedRefreshHistory', lambda ctx: read_jobs(pbi, ctx),
                       lambda value: [job_summary(j) for j in value])
    if not ok: return False
    ok, clear = capture(report, 'WaitAcceptedClear', lambda ctx: wait_job(pbi, jobs[0], state, ctx), job_summary)
    if not ok: return False
    if len(jobs) == 2:
        state['ExistingFullReused'] = True
        ok, full = capture(report, 'WaitExistingFull', lambda ctx: wait_job(pbi, jobs[1], state, ctx), job_summary)
        return ok
    ready = backup is not None and current is not None and mapping is not None and physical_ok
    if ready:
        ready = digest(backup[0]) == digest(current[0]) and digest(backup[1]) == digest(mapping)
    if not ready:
        skip(report, 'MissingFullRecovery', 'BACKUP_ROUTING_PHYSICAL_OR_PRESERVATION_CHECK_FAILED')
        return False
    def resume(ctx):
        again, _, bindings = read_definition(client, ctx)
        require(digest(again) == digest(backup[0]) and digest(connections(client, ctx)) == digest(backup[1]),
                'METADATA_CHANGED_BEFORE_FULL')
        routing(current[1], bindings)
        latest = read_jobs(pbi, ctx)
        require(len(latest) == 1 and latest[0]['ID'] == clear['ID'] and latest[0]['Status'] == 'Completed',
                'REFRESH_HISTORY_CHANGED_NO_SUBMISSION')
        full = submit_missing_full(pbi, fs, state, ctx, latest)
        return wait_job(pbi, full, state, ctx)
    ok, _ = capture(report, 'MissingFullRecovery', resume, job_summary)
    return ok


def run(client, pbi, evaluate, spark, fs):
    report = {'Stage': 'TEST_R178_DEEP_DIAGNOSTICS_NEEDS_REVIEW', 'Revision': 'R02', 'TestModelID': TEST,
      'Checks': {}, 'Processing': {'ClearValuesSubmissionRequestedHere': False,
        'FullSubmissionAttemptedHere': False, 'ExistingFullReused': False},
      'ModelDefinitionWriteRequested': False, 'LakehouseTableWriteRequested': False,
      'OriginalModelWriteRequested': False, 'CompanyAmountQuerySubmitted': False,
      'CompanyAmountsPrintedOrStoredByScript': False, 'RawErrorsOrSourceRecordsPrinted': False,
      'ReportPublished': False, 'NativeR178AdapterInstalled': False,
      'DesktopRenderingVerified': False, 'IndependentBusinessParityVerified': False}
    try:
        batch(client, pbi, evaluate, spark, fs, report)
    except KeyboardInterrupt:
        report['Interrupted'] = True
        report['Stage'] = 'TEST_R178_DEEP_DIAGNOSTICS_INTERRUPTED'
    except Exception as exc:
        report['UnexpectedFailure'] = safe_failure(exc)
    report['NextStep'] = 'Send the entire final JSON. Keep backups and attempt markers. No rerun, reset, manual refresh, updater or publication until reviewed.'
    print(json.dumps(report, indent=2, allow_nan=False), flush=True)
    return report


def batch(client, pbi, evaluate, spark, fs, report):
    ok, _ = capture(report, 'ExactTESTIdentity', lambda ctx: identity(client, ctx), lambda _: {'ExactTESTConfirmed': True})
    if not ok: return
    backup_ok, backup = capture(report, 'PinnedR01Backup', lambda ctx: load_backup(fs),
                lambda v: {'ExactAttemptMarker': True, 'FullPrivateFilesRead': True, 'DatesBefore': v[2]})
    current_ok, current = capture(report, 'DefinitionAndRouting', lambda ctx: read_definition(client, ctx),
                lambda v: inventory(v[1]))
    route_ok = False
    if current_ok:
        route_ok, _ = capture(report, 'KnownLakehouseRouting', lambda ctx: routing(current[1], current[2]), lambda _: {'KnownRouting': True})
    map_ok, mapping = capture(report, 'CloudMappingBefore', lambda ctx: connections(client, ctx),
                             lambda v: {'ConnectionCount': len(v)})
    physical_ok, physical = capture(report, 'PhysicalDatesBefore', lambda ctx: physical_dates(spark, fs, ctx),
                        lambda v: {kind: {'Rows': len(rows)} for kind, rows in v.items()})
    preserved = backup_ok and current_ok and map_ok and digest(backup[0]) == digest(current[0]) and digest(backup[1]) == digest(mapping)
    report['BeforeDefinitionAndCloudMatchBackup'] = bool(preserved)
    # History/status reads remain useful even when an independent precondition failed.
    processing_ok = recover(client, pbi, fs, report, backup if backup_ok else None,
                            current if current_ok and route_ok else None, mapping if map_ok else None, physical_ok)
    report['KnownFullCompleted'] = processing_ok
    after_ok, after = capture(report, 'DefinitionAfter', lambda ctx: read_definition(client, ctx),
                              lambda v: inventory(v[1]))
    map_after_ok, map_after = capture(report, 'CloudMappingAfter', lambda ctx: connections(client, ctx),
                                      lambda v: {'ConnectionCount': len(v)})
    report['OtherModelDefinitionPreserved'] = bool(backup_ok and after_ok and digest(backup[0]) == digest(after[0]))
    report['CloudConnectionPreserved'] = bool(backup_ok and map_after_ok and digest(backup[1]) == digest(map_after))
    physical_after_ok, physical_after = capture(report, 'PhysicalDatesAfter', lambda ctx: physical_dates(spark, fs, ctx),
                               lambda v: {kind: {'Rows': len(rows)} for kind, rows in v.items()})
    report['PhysicalDateMetadataStable'] = bool(physical_ok and physical_after_ok and physical == physical_after)
    # A missing/pending/failed processing operation does not allow loading measures or more DAX queries.
    if not processing_ok:
        for name in ('ExactSemanticDates', 'EngineClientDateBoundary', 'FilesMetadata', 'SelectionGuards', 'AvailableProbeScope', 'PrivateScalarChecks'):
            skip(report, name, 'FULL_COMPLETION_NOT_CONFIRMED')
        return
    date_ok, dates = capture(report, 'ExactSemanticDates', lambda ctx: semantic_dates(evaluate, ctx),
                lambda v: compare(physical_after, v) if physical_after_ok else {'ExactParityUnavailable': True})
    report['ExactDateParityVerified'] = bool(date_ok and physical_after_ok and all_match(compare(physical_after, dates)))
    engine_ok, engine = capture(report, 'EngineClientDateBoundary',
             lambda ctx: engine_date_boundary(evaluate, physical_after if physical_after_ok else None), lambda v: v)
    report['EngineDateBoundaryValid'] = bool(engine_ok and all(row['EngineDaysMatchPhysical'] and
                  row['ClientTypedDayDisagreesWithEngineText'] == row['EngineOutOfRangeOrBlankDates'] == 0
                  for row in engine.values()))
    file_ok, files = capture(report, 'FilesMetadata', lambda ctx: metadata_counts(evaluate, FILES_QUERY, FILE_FIELDS), lambda v: v)
    guard_ok, guards = capture(report, 'SelectionGuards', lambda ctx: metadata_counts(evaluate, GUARDS_QUERY, GUARD_FIELDS), lambda v: v)
    report['FilesMetadataValid'] = bool(file_ok and files_valid(files))
    report['SelectionGuardsValid'] = bool(guard_ok and guards_valid(guards))
    safe_numeric = all(report.get(k) for k in ('ExactDateParityVerified', 'EngineDateBoundaryValid', 'FilesMetadataValid', 'SelectionGuardsValid',
                    'BeforeDefinitionAndCloudMatchBackup', 'OtherModelDefinitionPreserved',
                    'CloudConnectionPreserved', 'PhysicalDateMetadataStable'))
    if safe_numeric:
        signature_ok, signature = capture(report, 'SourceCohortBefore', lambda ctx: source_signature(evaluate),
                                         lambda _: {'PrivateSignatureHeld': True})
        scope_ok, scope = capture(report, 'AvailableProbeScope', lambda ctx: source_scope(evaluate),
                                 lambda _: {'AvailableScopesSelected': 1, 'IdentifiersPrinted': False})
        if scope_ok and signature_ok:
            ok, numeric = capture(report, 'PrivateScalarChecks', lambda ctx: numeric_probes(evaluate, report, scope), lambda v: v)
            report['BoundedInternalCalculationChecksPassed'] = bool(ok and numeric['Status'] == 'PASSED')
        else: skip(report, 'PrivateScalarChecks', 'PROBE_SCOPE_UNAVAILABLE')
        signature_after_ok, signature_after = capture(report, 'SourceCohortAfter', lambda ctx: source_signature(evaluate),
                                                       lambda _: {'PrivateSignatureHeld': True})
        report['NumericSourceCohortStable'] = bool(signature_ok and signature_after_ok and signature == signature_after)
        def final_metadata(ctx):
            definition, _, _ = read_definition(client, ctx)
            require(digest(definition) == digest(backup[0]) and
                    digest(connections(client, ctx)) == digest(backup[1]), 'METADATA_CHANGED_DURING_PROBES')
            return True
        final_ok, _ = capture(report, 'MetadataAfterProbes', final_metadata, lambda _: {'DefinitionAndCloudStable': True})
        report['NumericMetadataStable'] = final_ok
        final_physical_ok, final_physical = capture(report, 'PhysicalDatesAfterProbes', lambda ctx: physical_dates(spark, fs, ctx),
                              lambda v: {kind: {'Rows': len(rows)} for kind, rows in v.items()})
        report['NumericPhysicalDateMetadataStable'] = bool(final_physical_ok and physical_after == final_physical)
        def final_history(ctx):
            jobs = read_jobs(pbi, ctx)
            require(len(jobs) == 2 and all(j['Status'] == 'Completed' for j in jobs) and
                    jobs[0]['ID'] == report['Processing']['ClearValues']['ID'] and
                    jobs[1]['ID'] == report['Processing']['Full']['ID'], 'PROCESSING_CHANGED_DURING_PROBES')
            return jobs
        history_ok, _ = capture(report, 'RefreshHistoryAfterProbes', final_history,
                               lambda value: [job_summary(j) for j in value])
        report['NumericProcessingStable'] = history_ok
    else:
        skip(report, 'AvailableProbeScope', 'DATE_GUARD_OR_PRESERVATION_FAILURE')
        skip(report, 'PrivateScalarChecks', 'DATE_GUARD_OR_PRESERVATION_FAILURE')
    messages_ok = all(report['Processing'].get(kind, {}).get('MessageCount') == 0 for kind in ('ClearValues', 'Full'))
    report['ProcessingMessagesRequireReview'] = not messages_ok
    all_reads = all(c['Status'] == 'READ_COMPLETED' for c in report['Checks'].values())
    if safe_numeric and messages_ok and all_reads and all(report.get(k) for k in
       ('BoundedInternalCalculationChecksPassed', 'NumericSourceCohortStable', 'NumericMetadataStable',
        'NumericPhysicalDateMetadataStable', 'NumericProcessingStable')):
        report['Stage'] = 'TEST_R178_RECOVERY_AND_BOUNDED_CHECKS_VERIFIED'


if __name__ == '__main__':
    import sempy.fabric as fabric
    import notebookutils
    # Suppress SDK POST retries; service-internal retries can still occur.
    no_retry = {'total': 0, 'allowed_methods': ['GET'], 'raise_on_status': False}
    run(fabric.FabricRestClient(retry_config=no_retry), fabric.PowerBIRestClient(retry_config=no_retry),
        fabric.evaluate_dax, spark, notebookutils.fs)
