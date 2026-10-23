"""ONE NEW ForecastMaster_GM_Setup Python cell. Read metadata only; no refresh.

Reads the existing TEST installation receipts and up to 60 refresh-history rows.
No DAX, Spark, definition read/update, remote file write or publication.
Returns only allowlisted operational metadata, never raw errors or company data.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory
from uuid import UUID

WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
LAKEHOUSE = 'd6e33ebd-67b1-420a-8d84-c3a0d04d8b21'
TEST = '31d00232-ac03-48fe-af39-f2e4bae82443'
NAME = 'ForecastMaster Native OneLake R17.1 - TEST'
ROOT = ('abfss://' + WORKSPACE + '@onelake.dfs.fabric.microsoft.com/' + LAKEHOUSE
        + '/Files/ForecastMasterRefreshState/report-upgrades/Native-R178-Compact-R01')
ATTEMPT = ROOT + '/ATTEMPT.json'
HISTORY = ('https://api.powerbi.com/v1.0/myorg/groups/' + WORKSPACE
           + '/datasets/' + TEST + '/refreshes?$top=60')
STATUSES = {'Completed', 'Failed', 'Disabled', 'Unknown', 'Cancelled', 'Canceled', 'TimedOut'}
TERMINAL = STATUSES - {'Unknown'}
TYPES = {'Scheduled', 'OnDemand', 'ViaApi', 'ViaXmlaEndpoint', 'ViaEnhancedApi', 'OnDemandTraining'}
SIGNALS = ('CREDENTIAL', 'MEMORY', 'TIMEOUT', 'CANCEL', 'CAPACITY', 'PERMISSION', 'THROTTL', 'DIRECTLAKE')


class CheckStopped(Exception):
    pass


def require(condition, reason):
    if not condition:
        raise CheckStopped(reason)


def timestamp(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.astimezone(timezone.utc) if parsed.tzinfo is not None else None
    except ValueError:
        return None


def read_receipt(fs, path):
    require(fs.exists(path), 'PRIVATE_RECEIPT_MISSING')
    with TemporaryDirectory(prefix='fm-r178-history-') as temp:
        local = Path(temp) / 'receipt.json'
        require(fs.cp(path, local.as_uri(), False), 'PRIVATE_RECEIPT_READ_FAILED')
        require(0 < local.stat().st_size <= 1024 * 1024, 'PRIVATE_RECEIPT_SIZE_UNEXPECTED')
        value = json.loads(local.read_text(encoding='utf-8'))
        require(isinstance(value, dict), 'PRIVATE_RECEIPT_SHAPE_UNEXPECTED')
        return value


def run(client, pbi, fs):
    result = {
        'Stage': 'R178_REFRESH_STATE_CHECK_STOPPED', 'ProbeRevision': 'R01', 'TestModelID': TEST,
        'ModelWriteRequested': False, 'OriginalModelWriteRequested': False,
        'LakehouseTableWriteRequested': False, 'RefreshRequested': False,
        'CompanyAmountQuerySubmitted': False, 'CompanyAmountValuesPrintedOrStored': False,
        'ReportPublished': False, 'RawErrorsPrintedOrStored': False,
        'NextStep': 'Send this complete JSON. No installer, verifier, refresh, reset or publication retry until reviewed.'
    }
    step = 'Identity'
    try:
        print('Read-only TEST: installation receipt and refresh history only. No amounts or refresh.', flush=True)
        response = client.get('/v1/workspaces/' + WORKSPACE + '/items/' + TEST)
        require(response.status_code == 200, 'IDENTITY_HTTP_NOT_OK')
        item = response.json()
        require(isinstance(item, dict) and item.get('id') == TEST
                and item.get('displayName') == NAME and item.get('type') == 'SemanticModel',
                'EXACT_TEST_IDENTITY_NOT_CONFIRMED')
        result['ExactTESTConfirmed'] = True
        step = 'InstallationReceipt'
        marker = read_receipt(fs, ATTEMPT)
        folder = marker.get('Backup')
        require(marker.get('Revision') == 'R01' and marker.get('TEST') == TEST
                and isinstance(folder, str) and folder.startswith(ROOT + '/')
                and re.fullmatch(r'[0-9]{8}T[0-9]{6}-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
                                 folder[len(ROOT) + 1:]) is not None, 'INSTALL_MARKER_UNEXPECTED')
        success = read_receipt(fs, folder + '/success.json')
        require(success.get('Stage') == 'TEST_R178_UPDATED', 'INSTALL_SUCCESS_NOT_CONFIRMED')
        installed = timestamp(success.get('InstalledAtUTC'))
        require(installed is not None, 'INSTALL_TIMESTAMP_INVALID')
        result['InstalledAtUTC'] = installed.isoformat()
        step = 'RefreshHistory'
        response = pbi.get(HISTORY)
        result['HistoryHTTPStatus'] = int(response.status_code)
        require(response.status_code == 200, 'HISTORY_HTTP_NOT_OK')
        payload = response.json()
        jobs = payload.get('value') if isinstance(payload, dict) else None
        require(isinstance(jobs, list) and len(jobs) <= 60
                and all(isinstance(job, dict) for job in jobs), 'HISTORY_SHAPE_UNEXPECTED')
        rows = []
        for index, job in enumerate(jobs):
            start, end = timestamp(job.get('startTime')), timestamp(job.get('endTime'))
            status = job.get('status') if job.get('status') in STATUSES else 'UNRECOGNIZED'
            raw_error = job.get('serviceExceptionJson')
            error_text = raw_error.upper() if isinstance(raw_error, str) else ''
            try:
                request_id = str(UUID(job.get('requestId')))
            except (ValueError, TypeError, AttributeError):
                request_id = None
            rows.append({
                'APIIndex': index, 'Status': status,
                'RefreshType': job.get('refreshType') if job.get('refreshType') in TYPES else 'UNRECOGNIZED',
                'RequestID': request_id, 'StartTimeUTC': start.isoformat() if start else None,
                'EndTimeUTC': end.isoformat() if end else None,
                'StartedAtOrAfterInstall': start >= installed if start else None,
                'ServiceErrorPresent': bool(raw_error),
                'KnownErrorSignals': [signal for signal in SIGNALS if signal in error_text]
            })
        result['History'] = rows
        result['Summary'] = {
            'RowsReturned': len(rows),
            'FirstEntryStatusUsedByVerifier': rows[0]['Status'] if rows else 'NO_ROWS',
            'FirstEntryStartedAtOrAfterInstall': rows[0]['StartedAtOrAfterInstall'] if rows else None,
            'CompletedAtOrAfterInstall': sum(row['Status'] == 'Completed'
                and row['StartedAtOrAfterInstall'] is True for row in rows),
            'NonTerminalOrUnrecognized': sum(row['Status'] not in TERMINAL for row in rows),
            'MissingOrInvalidStartTimes': sum(row['StartTimeUTC'] is None for row in rows)
        }
        result['Stage'] = 'R178_REFRESH_STATE_READ_COMPLETED'
        result['Interpretation'] = ('History snapshot only. Unknown can mean running or unknown completion. '
                                    'No date, numerical, definition or final-verification pass is claimed.')
    except (Exception, KeyboardInterrupt) as exc:
        result['Failure'] = {'Step': step,
            'Reason': str(exc) if isinstance(exc, CheckStopped) else 'EXCEPTION_WITHHELD',
            'ExceptionFamily': type(exc).__name__ if type(exc).__name__ in {
                'CheckStopped', 'TypeError', 'ValueError', 'KeyError', 'JSONDecodeError',
                'KeyboardInterrupt', 'ConnectionError', 'TimeoutError', 'RuntimeError'} else 'OTHER'}
    print(json.dumps(result, indent=2), flush=True)
    return result


if __name__ == '__main__':
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(retry_config={'total': 0}),
        fabric.PowerBIRestClient(retry_config={'total': 0}), notebookutils.fs)
