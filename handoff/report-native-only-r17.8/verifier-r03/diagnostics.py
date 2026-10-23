"""Bounded operational evidence only. Raw API errors and amounts stay private."""
import re
from zoneinfo import ZoneInfo

CHECK_NAMES = ('Identity', 'InstallReceipts', 'RefreshHistory', 'CandidateDefinition',
               'CloudMapping', 'QuietProcessing', 'PhysicalDates', 'SemanticDates',
               'NumericalParity', 'FileLabels', 'FinalConsistency')
TERMINAL_STATES = {'Completed', 'Failed', 'Disabled', 'Cancelled', 'Canceled', 'TimedOut'}
CATEGORIES = {'OnDemand': 'Scheduled', 'Scheduled': 'Scheduled', 'ViaApi': 'Scheduled',
              'ViaEnhancedApi': 'Scheduled', 'ViaXmlaEndpoint': 'Scheduled',
              'DirectLake': 'Direct Lake', 'OneDrive': 'OneDrive',
              'OneLakeIntegration': 'OneLake Integration'}


def parsed_time(value):
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return stamp.astimezone(timezone.utc) if stamp.tzinfo is not None else None
    except ValueError:
        return None


def public_error(value):
    """Return bounded structured codes and fixed useful messages, never raw text.

    Unknown free-form details get an exact operation link instead of another
    diagnostic run. Do not attempt unreliable free-text redaction of amounts.
    """
    raw = value if isinstance(value, str) else ''
    if len(raw) > 100000:
        raw = raw[:100000]
    codes = []
    try:
        payload = json.loads(raw)
    except (ValueError, TypeError):
        payload = None

    def visit(node, depth=0):
        if depth > 4 or not isinstance(node, dict):
            return
        for key, item in list(node.items())[:40]:
            if key in {'errorCode', 'code'} and isinstance(item, str):
                # API error code field, not arbitrary messages/query results.
                if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,95}', item) and item not in codes:
                    codes.append(item)
            elif isinstance(item, dict):
                visit(item, depth + 1)
    visit(payload)
    lower = raw.lower()
    messages = []
    for tokens, label in (
        (('checking the latest version', 'sending the request'), 'Backend request failed while checking a Direct Lake table version.'),
        (('available resources',), 'Query resource limit exceeded.'),
        (('memory limit',), 'Memory limit exceeded.'),
        (('credentials',), 'Credentials-related service error; inspect exact operation details.'),
        (('timed out',), 'Service operation timed out.'),
        (('cancelled',), 'Operation was cancelled.'),
        (('canceled',), 'Operation was cancelled.'),
        (('access denied',), 'Access was denied; inspect exact operation details.')
    ):
        if all(token in lower for token in tokens) and label not in messages:
            messages.append(label)
    return {'ErrorPresent': bool(value), 'Codes': codes[:8], 'Messages': messages,
            'UnclassifiedDetails': bool(value) and not (codes or messages),
            'RawErrorPrintedOrStored': False}


def history_evidence(rows):
    require(isinstance(rows, list) and len(rows) <= 60
            and all(isinstance(row, dict) for row in rows), 'REFRESH_HISTORY_SHAPE_INVALID')
    public = []
    for index, row in enumerate(rows):
        status = row.get('status')
        status = status if isinstance(status, str) and status in TERMINAL_STATES | {'Unknown'} else 'UNRECOGNIZED'
        stamp, end = parsed_time(row.get('startTime')), parsed_time(row.get('endTime'))
        try:
            request = str(UUID(row.get('requestId')))
        except (TypeError, ValueError, AttributeError):
            request = None
        kind = row.get('refreshType')
        category = CATEGORIES.get(kind, 'Unclassified') if isinstance(kind, str) else 'Unclassified'
        public.append({'APIIndex': index, 'Status': status, 'Category': category,
                       'StartUTC': stamp.isoformat() if stamp else None,
                       'StartUK': stamp.astimezone(ZoneInfo('Europe/London')).isoformat() if stamp else None,
                       'EndUTC': end.isoformat() if end else None, 'RequestID': request,
                       'DetailsURL': ('https://app.powerbi.com/groups/' + WORKSPACE + '/datasets/' + TEST
                                      + '/refreshdetails/' + request) if request else None,
                       'Error': public_error(row.get('serviceExceptionJson'))})
    newest_by_category = {}
    for row in public:
        if row['Category'] not in newest_by_category:
            newest_by_category[row['Category']] = row
    return {'RowsReturned': len(public), 'FirstEntry': public[0] if public else None,
            'NewestInReturnedOrderByCategory': newest_by_category,
            'NonTerminalOrUnrecognized': sum(row['Status'] not in TERMINAL_STATES for row in public),
            'Interpretation': 'API order retained. Categories explain UI tabs; they do not exempt a newer failed operation.'}


def metadata_integer(value, empty_means_zero=False):
    # Only metadata COUNTROWS counters may use this helper. Never business values.
    if value is None or isinstance(value, float) and math.isnan(value):
        require(empty_means_zero, 'REQUIRED_METADATA_COUNT_UNAVAILABLE')
        return 0
    require(isinstance(value, Number) and not isinstance(value, bool)
            and math.isfinite(float(value)) and value >= 0 and int(value) == value,
            'METADATA_COUNT_NOT_NONNEGATIVE_INTEGER')
    return int(value)


def public_exception(exc):
    try:
        return public_error(str(exc))
    except Exception:
        return {'ErrorPresent': True, 'Codes': [], 'Messages': [],
                'UnclassifiedDetails': True, 'RawErrorPrintedOrStored': False}
