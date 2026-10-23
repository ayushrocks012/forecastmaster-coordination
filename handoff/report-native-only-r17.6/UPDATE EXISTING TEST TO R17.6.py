"""Run ONE NEW cell in ForecastMaster_GM_Setup: EXISTING TEST only.
Adds two monthly dictionaries and a flat comparison label; gates display bodies.
Full private backup/readback, no purge, source arithmetic unchanged.
After success, refresh TEST ONCE to process new calculated metadata helpers.
This cell does not request a refresh or publish a report.
"""
import base64
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID, uuid4

WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'
TEST_MODEL = '31d00232-ac03-48fe-af39-f2e4bae82443'
TEST_NAME = 'ForecastMaster Native OneLake R17.1 - TEST'
ORIGINAL_MODEL = 'e7af2967-7725-4108-a170-9e490d4e35bb'
LAKEHOUSE = 'd6e33ebd-67b1-420a-8d84-c3a0d04d8b21'
BASE = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/semanticModels/31d00232-ac03-48fe-af39-f2e4bae82443'
ITEM = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/items/31d00232-ac03-48fe-af39-f2e4bae82443'
EXPECTED_HASHES = {'N Display': {'expression': '83d093218662a8012c7d2c2c5c431506544c084e299eca356fc787c1fe262777'},
 'N Catalog Visible': {'expression': 'a1ed096682f12f94c65b23f7439585517369266b65c07ebe8118b02a6931be11'},
 'N Catalog Available': {'expression': '16c7897c758fc38ae89aac4b979b8fe1756662aa833271d82f603af844302c3f'},
 'N Source Caption': {'expression': 'a45fc9ada06582a0f1be59a66260c420c01cc9847be13ced786ae1d26c04cc96'},
 'N Source OK': {'expression': '91260c4f00240445f7cbf6d047a941dc63c4d8feea7256fe372f03d8e8c4b3aa'},
 'N Scenario Visible': {'expression': '224fb77731eacd9b6bf6eb53f8846dce25a4d3ae26952a9485a6d28073514a83'},
 'N Scope Available': {'expression': '571e278cbf01bb7a332503f94bb9ad9f3a1448b3d7481f54ce88bbcccc15fb8e'},
 'N Period Available': {'expression': '65a319055a3ffce2a10288be6fce3cd3efb15d72b9c539709e1c137c3705188e'},
 'N Cutoff': {'expression': '3e1ee0805af2a98e580d59d819fe6cb4267ea4432f2b7c2cccbd019c6f0e2e5f'},
 'N Monthly Numerator': {'expression': '280044a7b6374af356860a16af45652c77daf032080a6bbd6449c8c9977b8c26',
                         'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Monthly Denominator': {'expression': '6c38394049f9eea1cb152668448f10c1967ade393e7a387a512626c015620754',
                           'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Monthly': {'expression': '3274d7e88c1e1339794ede78bc182696d9fc833f3ae17a07a8edfc936713b656',
               'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Trend Monthly': {'expression': '44438a048456e942a7789c8b87756fff99b90d283842bef729ff0b994365e5b7',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Period Months': {'expression': '91e5fce6fff5b9ada7acdb1c108d038beb1362cf588015b6b1ca730076615a8f'},
 'N Plan': {'expression': '7fbe2abb60b6675e37e75bf449beeef7e06745b5daeee46430b3cfd96bf777f4',
            'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Benchmark': {'expression': '93eb5aaee3809ea25f94c4de76991622306911c3dfcea1d5a968a29cb2623554',
                 'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Variance': {'expression': '64525ee09318aa2b386f7dc6c6bdb57d164d4f7ddef3b93415c7b7b23a7fbe74',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Variance %': {'expression': 'd45e4c988e73543f03aa8f2df86bc31829cd4babaf743d38cb5d86b85631808b'},
 'N Headline Variance': {'expression': '690ac7c392670a846e8acad7b38a097c7de6029723c5006ea10b72f42aa15ebc',
                         'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Headline Variance %': {'expression': '9d36d5afc5d2c34b56bd356ab725370b1fec474a86aa309b44f91e5075be3537'},
 'N Summary Cell': {'expression': '6ab85953924d3605c6f7340664de82f369314523365bd99112fb894bdb0e9b0d',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Run Rate': {'expression': '434e231e9f5e422a95019c31bbe897cdbb0259f6e12f7c5d30d00c65b519631c',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Growth %': {'expression': '4fc1fe94cec78aaf19127186afcb68c073e97062a8d6bcfaf422e50016dbd137'},
 'N SOP Row Selected': {'expression': 'f90686cc5dbbd18e004cf469eeb4552fe40799f1f1915f3423fb5911e1f0fc52'},
 'N SOP Plan': {'expression': '6b3295c53e8165906a1b12f8df8420580a7882bf7ab46edf3ebe7006dd6fa9e7',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Run Rate': {'expression': '5882bd2cc6903f458af102482318d04234a17851745c117cd7a95086c2c0edbc',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Growth %': {'expression': '4f57cc7f5ead4b5690ed9b26357a0767c6ea3725948512477f680d3be9339faf'},
 'N SOP Monthly': {'expression': 'dd57e3585a8e0615f10e9cb1dbfa380fdcd235ba1d077996d92825653addc949',
                   'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Monthly Growth %': {'expression': 'c1e02098ab614686ed5f3d2447fa82e21844e8bf93f2ccedb1baae201137fc2f'},
 'N Export Selected': {'expression': '488d7184e52844c19a0e3463dbcc165860f45b498cad362bb58ce01d344b5960'},
 'N Export Plan': {'expression': '04897f30186fcf00a11eb9fca8f92149ca07d3fa16a01e4f92ff6e25e5d1dd25',
                   'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Run Rate': {'expression': '772eec49fab63a3d29fe40aa7892da5745b3dbbb76805915162d71eebcc4b49f',
                       'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Growth %': {'expression': '2b04daf4beb36283edbebd50f2df3decc8a95924b704f889087edd410ae32584'},
 'N Export Order': {'expression': 'e730be8fa633332b34441ee8d65a764d2b26678ea7dc2af1199236d524929b66'},
 'N Export Monthly': {'expression': '4cf518b0e5d5cf5bfecee35e6f162c8759723d0433cc60b91321563231abaa4e',
                      'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Month Stage': {'expression': '98a443d675dbaac8ed174b7ff51b630063a4d1e54819f7b72efcb595ec67e697'},
 'N Chart Monthly': {'expression': '0cd93fd47ad185374e9d3d28f27581363b498ffa863531f8912b23d374b78671',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Chart Amount': {'expression': 'dec5ddc92c8c2fee36b340718e61be818a0f8ad33c5c985d651bdcfd85dbffa3',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Chart Share': {'expression': 'b59efc20e7accd4b466b347b5ce798fb3cad8c57993ade1ea3906d1682cf2da6'},
 'N Status': {'expression': '5c0bcca0d2c5f657c0be14a01bf7ea0cf9dcf7937270d66748ab4ebf7e3d3d0f'},
 'N Variance Color': {'expression': 'ab31ad7cee52b774325f64076c934bddb3ff6beb849c6e1095d712989787379c'},
 'N Fit Cutoff': {'expression': 'd3dd2b6875c0ef51b5c9c1a9db0a78637e7f6b975b5a59e5f7a3353fb96ce2ed'},
 'N Actual Only': {'expression': '8826b03260473ca437c797d32a933eb7bddf870b3ebd5d5e16d9ce61044371e8'},
 'N Line Visible': {'expression': '6cf95d187c33f0d145a1fc76e43a24fac421b595ad5e475af0c060617c0c26b8'},
 'N Selected Month': {'expression': '98983667084cf6376a0a68140e675dd2a585b6a57c5a478b585a1e0a0f7fe762'},
 'N Selected Monthly': {'expression': '580775cdf730607dfee50efb75ffe6817fe227b3010c67a5cab8eaf393b6b950',
                        'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Headline Cell': {'expression': 'abf3f6a3a083a185d6f85e8353f814bf20bde94a9b4b7e69de6f6ab05d44ed37',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Measure Caption': {'expression': 'c5fa17fb3d90c92d173610329f9025251a93e4704b96a2164cda7b568037c5cb'},
 'N Group Visible': {'expression': '6b975f0b80238fc7341493dd5fcaf4926fde29a4d617fd54526f4966240291bb'}}

EDITS = {'N Chart Monthly': "VAR _kind=SELECTEDVALUE('fm_native_lines'[LineKind])\n"
                    "VAR _gd=SELECTEDVALUE('fm_native_lines'[ScopeDriver]) VAR "
                    "_sec=SELECTEDVALUE('fm_native_lines'[ScopeSector])\n"
                    "VAR _sectorLevel=SELECTEDVALUE('fm_native_lines'[IsSector],0)=1\n"
                    "VAR _cyc=SELECTEDVALUE('fm_native_lines'[DemandCycle]) VAR "
                    "_type=SELECTEDVALUE('fm_native_lines'[Chart])\n"
                    'VAR '
                    '_row=IF(_type="sop",SELECTEDVALUE(\'fm_native_lines\'[RowID]),COALESCE(SELECTEDVALUE(\'fm_native_catalog\'[RowID]),SELECTEDVALUE(\'fm_native_metric\'[RowID]),"market"))\n'
                    "VAR _display=SELECTEDVALUE('fm_native_lines'[Display])\n"
                    'VAR _selected=_type="demand" || ISFILTERED(\'fm_native_state\'[Token]) && COUNTROWS(\n'
                    ' FILTER(ALLSELECTED(\'fm_native_state\'),\'fm_native_state\'[Kind]="row"\n'
                    " &&'fm_native_state'[RowID]=_row&&'fm_native_state'[Display]=_display))>0\n"
                    'VAR '
                    "_scope=FILTER(ALLSELECTED('fm_native_scope'),(LEN(_gd)=0||'fm_native_scope'[GrowthDriver]=_gd)&&(NOT "
                    "_sectorLevel||'fm_native_scope'[Sector]=_sec))\n"
                    "VAR _month=SELECTEDVALUE('fm_review_axis'[Month])\n"
                    'VAR '
                    "_within=_month>=MIN('fm_native_start_month'[Month])&&_month<=MAX('fm_native_end_month'[Month])\n"
                    'VAR '
                    '_mode=SELECTEDVALUE(\'fm_native_lines\'[Mode])=SELECTEDVALUE(\'fm_native_file_mode\'[Mode],"Automatic '
                    'ADS")\n'
                    'VAR _base=CALCULATE([N '
                    "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                    'VAR _cut=CALCULATE([N '
                    "Cutoff],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]))\n"
                    'RETURN '
                    'IF((_type<>"demand"||HASONEVALUE(\'fm_native_metric\'[RowID]))&&MIN(\'fm_native_start_month\'[Month])<=MAX(\'fm_native_end_month\'[Month])&&_mode&&_within&&_selected&&COUNTROWS(_scope)>0&&CONTAINS(VALUES(\'fm_native_lines\'[ViewType]),\'fm_native_lines\'[ViewType],SELECTEDVALUE(\'fm_native_view\'[View],"Total")),\n'
                    ' '
                    'SWITCH(TRUE(),_kind=0&&_month<=_cut,_base,_kind=1&&(_month>_cut||_type="demand"&&_month=_cut),_base,\n'
                    ' _kind IN '
                    "{6,12,24}&&_month>=_cut&&_kind=SELECTEDVALUE('fm_native_chart_trend'[Window],12),\n"
                    ' CALCULATE([N Trend '
                    "Monthly],KEEPFILTERS(_scope),TREATAS({_cyc},'fm_review_files'[DemandCycle]),TREATAS({_row},'fm_native_catalog'[RowID]),REMOVEFILTERS('fm_native_trend'),TREATAS({_kind},'fm_native_trend'[Window]))))",
 'N Period Available': "VAR _start=MIN('fm_native_start_month'[Month]) VAR "
                       "_end=MAX('fm_native_end_month'[Month])\n"
                       "VAR _y=SELECTEDVALUE('fm_native_periods'[Year])\n"
                       'RETURN IF(NOT ISBLANK(_start)&&NOT ISBLANK(_end)&&_start<=_end&&NOT '
                       'ISBLANK(_y)&&_y>=YEAR(_start)&&_y<=YEAR(_end),1)',
 'N Headline Cell': "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1&&[N Period Available]=1,\n"
                    "SWITCH(SELECTEDVALUE('fm_native_headline'[Key]),\n"
                    ' "plan",[N Plan],"variance",[N Headline Variance],"pct",[N Headline Variance %])))',
 'N Summary Cell': "IF(HASONEVALUE('fm_native_metric'[RowID]),IF([N Source OK]=1,\n"
                   "VAR _leaf=HASONEVALUE('fm_native_columns'[ColumnKey])\n"
                   'RETURN IF(NOT _leaf,\n'
                   " IF(NOT ISINSCOPE('fm_native_columns'[ColumnLabel])&&[N Period Available]=1,[N Plan]),\n"
                   "VAR _key=SELECTEDVALUE('fm_native_columns'[ColumnKey])\n"
                   "VAR _w=SELECTEDVALUE('fm_native_columns'[Window])\n"
                   "VAR _allowed=_w=0 || _w IN VALUES('fm_native_trend'[Window])\n"
                   'VAR _actualOnly=[N Actual Only]=1\n'
                   'RETURN IF([N Period Available]=1&&_allowed,SWITCH(TRUE(),_key="plan",[N '
                   'Plan],_actualOnly,BLANK(),\n'
                   ' RIGHT(_key,3)="abs",CALCULATE([N '
                   "Variance],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])),\n"
                   ' CALCULATE([N Variance '
                   "%],REMOVEFILTERS('fm_native_trend'),TREATAS({_w},'fm_native_trend'[Window])))))))",
 'N Measure Caption': "IF(HASONEVALUE('fm_native_metric'[RowID]),\n"
                      'VAR _name=SELECTEDVALUE(\'fm_native_metric\'[MetricLabel],"Selected measures")\n'
                      'RETURN IF(CONTAINSSTRING(_name,"%"),_name,_name & IF([N Display]="Value"," value"," '
                      'units")),"Choose a measure in the selected section")'}

MONTH_TABLES = [{'name': 'fm_native_start_month',
  'description': 'R17.6 independent start month bound; monthly metadata only.',
  'columns': [{'name': 'Month',
               'dataType': 'dateTime',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Month]',
               'summarizeBy': 'none',
               'formatString': 'mmm yyyy'},
              {'name': 'MonthLabel',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[MonthLabel]',
               'summarizeBy': 'none',
               'sortByColumn': 'Month'}],
  'partitions': [{'name': 'fm_native_start_month',
                  'mode': 'import',
                  'source': {'type': 'calculated',
                             'expression': "DISTINCT(SELECTCOLUMNS('fm_review_months',\n"
                                           ' '
                                           '"Month",DATE(YEAR(\'fm_review_months\'[Month]),MONTH(\'fm_review_months\'[Month]),1),\n'
                                           ' "MonthLabel",FORMAT(\'fm_review_months\'[Month],"mmm '
                                           'yyyy","en-GB")))'}}]},
 {'name': 'fm_native_end_month',
  'description': 'R17.6 independent end month bound; monthly metadata only.',
  'columns': [{'name': 'Month',
               'dataType': 'dateTime',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[Month]',
               'summarizeBy': 'none',
               'formatString': 'mmm yyyy'},
              {'name': 'MonthLabel',
               'dataType': 'string',
               'type': 'calculatedTableColumn',
               'sourceColumn': '[MonthLabel]',
               'summarizeBy': 'none',
               'sortByColumn': 'Month'}],
  'partitions': [{'name': 'fm_native_end_month',
                  'mode': 'import',
                  'source': {'type': 'calculated',
                             'expression': "DISTINCT(SELECTCOLUMNS('fm_review_months',\n"
                                           ' '
                                           '"Month",DATE(YEAR(\'fm_review_months\'[Month]),MONTH(\'fm_review_months\'[Month]),1),\n'
                                           ' "MonthLabel",FORMAT(\'fm_review_months\'[Month],"mmm '
                                           'yyyy","en-GB")))'}}]}]

COLUMN_PATCH = ('DATATABLE("ColumnKey",STRING,"Comparison",STRING,"ValueLabel",STRING,"Window",INTEGER,"Sort",INTEGER,{\n'
 '{"plan","Total Plan"," ",0,0},\n'
 '{"6:abs","6M variance","Absolute",6,60},\n'
 '{"6:pct","6M variance","%",6,61},\n'
 '{"12:abs","12M variance","Absolute",12,120},\n'
 '{"12:pct","12M variance","%",12,121},\n'
 '{"24:abs","24M variance","Absolute",24,240},\n'
 '{"24:pct","24M variance","%",24,241}\n'
 '})',
 'ADDCOLUMNS(\n'
 '(DATATABLE("ColumnKey",STRING,"Comparison",STRING,"ValueLabel",STRING,"Window",INTEGER,"Sort",INTEGER,{\n'
 '{"plan","Total Plan"," ",0,0},\n'
 '{"6:abs","6M variance","Absolute",6,60},\n'
 '{"6:pct","6M variance","%",6,61},\n'
 '{"12:abs","12M variance","Absolute",12,120},\n'
 '{"12:pct","12M variance","%",12,121},\n'
 '{"24:abs","24M variance","Absolute",24,240},\n'
 '{"24:pct","24M variance","%",24,241}\n'
 '})),\n'
 ' "ColumnLabel",SWITCH([ColumnKey],"plan","Plan",\n'
 ' "6:abs","6M variance","6:pct","6M variance %",\n'
 ' "12:abs","12M variance","12:pct","12M variance %",\n'
 ' "24:abs","24M variance","24:pct","24M variance %"))',
 {'name': 'ColumnLabel',
  'dataType': 'string',
  'type': 'calculatedTableColumn',
  'sourceColumn': '[ColumnLabel]',
  'summarizeBy': 'none',
  'sortByColumn': 'Sort'})

SAFE_KEYS = ['annotations',
 'columns',
 'compatibilityLevel',
 'culture',
 'cultures',
 'dataSources',
 'dataType',
 'defaultMode',
 'description',
 'displayFolder',
 'entityName',
 'expression',
 'expressionSource',
 'expressions',
 'filterExpression',
 'formatString',
 'formatStringDefinition',
 'fromColumn',
 'fromTable',
 'hierarchies',
 'isHidden',
 'levels',
 'lineageTag',
 'measures',
 'members',
 'mode',
 'model',
 'modelPermission',
 'name',
 'partitions',
 'parts',
 'path',
 'payload',
 'payloadType',
 'perspectives',
 'relationships',
 'roles',
 'schemaName',
 'sortByColumn',
 'source',
 'sourceLineageTag',
 'tablePermissions',
 'tables',
 'toColumn',
 'toTable',
 'type']

DETAIL_LIMIT = 40

RULES = EXPECTED_HASHES
class CheckStopped(RuntimeError):
    pass

def expression_hash(expression):
    text = "\n".join(expression) if isinstance(expression, list) else expression
    return hashlib.sha256(text.strip().replace("\r\n","\n").encode()).hexdigest()


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def complete(client, response, result=False):
    if response.status_code not in {200, 202}:
        raise RuntimeError("Fabric HTTP " + str(response.status_code)
                           + "; inspect Fabric. No automatic retry.")
    if response.status_code == 200:
        if not result:
            return {}
        return response.json()
    operation_id = str(UUID(response.headers["x-ms-operation-id"]))
    print("Operation: " + operation_id, flush=True)
    operation = "/v1/operations/" + operation_id
    deadline = time.monotonic() + 360
    while time.monotonic() < deadline:
        time.sleep(min(30, max(1, int(response.headers.get("Retry-After", "5")))))
        response = client.get(operation)
        if response.status_code != 200:
            raise RuntimeError("Operation status unavailable; inspect it before any retry.")
        state = response.json().get("status")
        if state == "Succeeded":
            if not result:
                return {}
            received = client.get(operation + "/result")
            if received.status_code != 200:
                raise RuntimeError("Operation result unavailable; inspect Fabric before retrying.")
            return received.json()
        if state in {"Failed", "Cancelled", "Canceled"}:
            raise RuntimeError("Operation " + state + "; inspect the private backup. No retry.")
    raise TimeoutError("Outcome unconfirmed; inspect this operation before any retry.")


def read_definition(client):
    return complete(client, client.post(BASE + "/getDefinition?format=TMSL"), True)["definition"]


def database_part(definition):
    parts = [p for p in definition["parts"] if p["path"] == "model.bim"]
    if len(parts) != 1:
        raise ValueError("Expected one TMSL model.bim; no write.")
    return json.loads(base64.b64decode(parts[0]["payload"], validate=True))


def connection_state(client):
    values, token = [], None
    for _ in range(100):
        path = ITEM + "/connections"
        if token:
            path += "?continuationToken=" + quote(token, safe="")
        response = client.get(path)
        if response.status_code != 200:
            raise RuntimeError("Cannot verify TEST cloud mapping; no further write attempted.")
        page = response.json()
        values.extend(page.get("value", []))
        token = page.get("continuationToken")
        if not token:
            return sorted(values, key=lambda value: json.dumps(value, sort_keys=True))
    raise RuntimeError("Connection inventory incomplete; no further write attempted.")


def verified_backup(fs, path, value):
    """Full UTF-8 byte verification; never use a preview read as backup evidence."""
    raw = json.dumps(value, ensure_ascii=False)
    expected = raw.encode("utf-8")
    expected_hash = hashlib.sha256(expected).digest()
    if not fs.put(path, raw, False):
        raise RuntimeError("Private backup write failed; no model write. Retained path: " + path)
    observed_size, reason = None, "copy not completed"
    with TemporaryDirectory(prefix="forecastmaster-test-backup-") as directory:
        for attempt in range(3):
            if attempt:
                time.sleep(0.5)
            local = Path(directory) / (str(attempt) + ".json")
            try:
                if not fs.cp(path, local.as_uri(), False):
                    reason = "copy returned false"
                    continue
                observed_hash, observed_size = hashlib.sha256(), 0
                with local.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(65536), b""):
                        observed_size += len(chunk)
                        observed_hash.update(chunk)
                if observed_size == len(expected) and observed_hash.digest() == expected_hash:
                    return
                reason = "full-file hash/length mismatch"
            except Exception as error:
                reason = type(error).__name__
    raise RuntimeError(
        "Private backup verification failed: " + reason
        + "; expected bytes=" + str(len(expected)) + ", observed bytes=" + str(observed_size)
        + ". No model write. Retained backup: " + path)


def require(condition, code):
    if not condition:
        raise CheckStopped(code)


def parse_json(raw):
    def unique(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "DUPLICATE_JSON_KEY")
            result[key] = value
        return result

    def invalid_constant(_):
        raise CheckStopped("INVALID_JSON_CONSTANT")

    return json.loads(raw, object_pairs_hook=unique, parse_constant=invalid_constant)


def expression_text(value):
    if isinstance(value, str):
        return value
    if isinstance(value, list) and all(isinstance(line, str) for line in value):
        return "\n".join(value)
    raise CheckStopped("INVALID_EXPRESSION_SHAPE")


def unpack(value):
    require(isinstance(value, dict) and isinstance(value.get("parts"), list), "DEFINITION_INVALID")
    paths = [part.get("path") for part in value["parts"]]
    require(all(isinstance(path, str) for path in paths) and len(paths) == len(set(paths)),
            "DEFINITION_PARTS_NOT_UNIQUE")
    require(paths.count("model.bim") == 1, "MODEL_PART_NOT_UNIQUE")
    part = next(part for part in value["parts"] if part["path"] == "model.bim")
    require(part.get("payloadType") == "InlineBase64", "MODEL_PAYLOAD_TYPE_UNEXPECTED")
    database = parse_json(base64.b64decode(part["payload"], validate=True).decode("utf-8-sig"))
    require(isinstance(database, dict) and isinstance(database.get("model"), dict), "MODEL_JSON_INVALID")
    decoded = deepcopy(value)
    next(part for part in decoded["parts"] if part["path"] == "model.bim")["payload"] = database
    return decoded, database


def safe_token(value):
    if isinstance(value, int):
        return "[" + str(value) + "]"
    if value in SAFE_KEYS or value in RULES or value in {"model.bim", "fm_native_measures"}:
        return value
    return "id:" + hashlib.sha256(value.encode()).hexdigest()[:12]


def compare(expected, observed):
    """Full traversal; emit only safe paths/kinds, never private differing values.

    Named arrays align objects for readable diagnostics, but reordering still
    counts as an unexplained difference. No metadata property is ignored.
    Only measure DAX string/list representations with identical joined text are
    eligible for representation-only verification. CRLF/whitespace are NOT erased.
    """
    counts, details, representation_details = Counter(), [], []

    def note(path, kind, left=None, right=None):
        counts[kind] += 1
        selected = representation_details if kind == "IDENTICAL_DAX_LINE_REPRESENTATION" else details
        if len(selected) < DETAIL_LIMIT:
            detail = {"Path": ".".join(safe_token(p) for p in path), "Kind": kind}
            if kind == "TYPE_CHANGED":
                detail.update(ExpectedType=type(left).__name__, ObservedType=type(right).__name__)
            selected.append(detail)

    def walk(left, right, path):
        dax = ((len(path) >= 3 and path[-1] == "expression" and path[-3] == "measures")
               or (len(path) >= 4 and path[-2:] == ("formatStringDefinition", "expression")
                   and path[-4] == "measures"))
        if dax and type(left) is not type(right):
            try:
                if expression_text(left) == expression_text(right):
                    note(path, "IDENTICAL_DAX_LINE_REPRESENTATION")
                    return
            except CheckStopped:
                pass
        if type(left) is not type(right):
            note(path, "TYPE_CHANGED", left, right)
        elif isinstance(left, dict):
            for key in sorted(set(left) | set(right)):
                if key not in left:
                    note(path + (key,), "PROPERTY_ADDED")
                elif key not in right:
                    note(path + (key,), "PROPERTY_REMOVED")
                else:
                    walk(left[key], right[key], path + (key,))
        elif isinstance(left, list):
            identity = "path" if path and path[-1] == "parts" else "name"
            named = bool(left or right) and all(isinstance(item, dict) and isinstance(item.get(identity), str)
                                               for item in left + right)
            if named:
                a, b = {item[identity]: item for item in left}, {item[identity]: item for item in right}
                if len(a) != len(left) or len(b) != len(right):
                    note(path, "DUPLICATE_OBJECT_IDENTITY")
                    return
                if set(a) == set(b) and list(a) != list(b):
                    note(path, "OBJECT_ORDER_CHANGED")
                for key in sorted(set(a) | set(b)):
                    if key not in a:
                        note(path + (key,), "OBJECT_ADDED")
                    elif key not in b:
                        note(path + (key,), "OBJECT_REMOVED")
                    else:
                        walk(a[key], b[key], path + (key,))
            else:
                for index in range(max(len(left), len(right))):
                    if index >= len(left):
                        note(path + (index,), "ITEM_ADDED")
                    elif index >= len(right):
                        note(path + (index,), "ITEM_REMOVED")
                    else:
                        walk(left[index], right[index], path + (index,))
        elif left != right:
            note(path, "VALUE_CHANGED")

    walk(expected, observed, ())
    # Unexpected changes must not disappear behind many harmless DAX-line
    # details when the public output reaches its bounded size.
    details = (details + representation_details)[:DETAIL_LIMIT]
    return {"Counts": dict(counts), "Total": sum(counts.values()), "Details": details,
            "DetailsTruncated": sum(counts.values()) > len(details),
            "Unexplained": sum(n for kind, n in counts.items() if kind != "IDENTICAL_DAX_LINE_REPRESENTATION")}


def compare_with_calculated(expected, observed):
    """Only the three allowlisted calculated helpers gain line-array tolerance."""
    right = deepcopy(observed)
    left_db = next(p for p in expected["parts"] if p["path"] == "model.bim")["payload"]
    right_db = next(p for p in right["parts"] if p["path"] == "model.bim")["payload"]
    target_tables = {t["name"]: t for t in right_db["model"]["tables"]}
    representation_count = 0
    for table in left_db["model"]["tables"]:
        if table["name"] not in {"fm_native_columns", "fm_native_start_month", "fm_native_end_month"}:
            continue
        other = target_tables.get(table["name"], {})
        if len(table.get("partitions", [])) != 1 or len(other.get("partitions", [])) != 1:
            continue
        source = table["partitions"][0].get("source", {})
        received = other["partitions"][0].get("source", {})
        if source.get("type") != "calculated" or received.get("type") != "calculated":
            continue
        a, b = source.get("expression"), received.get("expression")
        if type(a) is not type(b):
            try:
                if expression_text(a) == expression_text(b):
                    received["expression"] = deepcopy(a)
                    representation_count += 1
            except CheckStopped:
                pass
    result = compare(expected, right)
    if representation_count:
        key = "IDENTICAL_CALCULATED_HELPER_LINE_REPRESENTATION"
        result["Counts"][key] = representation_count
        result["Total"] += representation_count
    return result


def patch_database(database):
    fixed = deepcopy(database)
    tables = {t["name"]: t for t in fixed["model"]["tables"]}
    expected, edits = EXPECTED_HASHES, EDITS
    measures = tables.get("fm_native_measures", {}).get("measures", [])
    current = {m["name"]: m for m in measures}
    if set(current) != set(expected) or len(current) != len(measures):
        raise ValueError("Unexpected native measure inventory; no write.")
    changed = []
    for name, hashes in expected.items():
        allowed = {hashes["expression"]}
        if name in edits:
            allowed.add(expression_hash(edits[name]))
        if expression_hash(current[name]["expression"]) not in allowed:
            raise ValueError("Unknown native expression; require verified R17.5 first.")
        fmt = current[name].get("formatStringDefinition")
        if bool(fmt) != ("formatStringDefinition" in hashes) or (
                fmt and expression_hash(fmt["expression"]) != hashes["formatStringDefinition"]):
            raise ValueError("Unexpected native format; no write.")
        if name in edits and expression_hash(current[name]["expression"]) != expression_hash(edits[name]):
            current[name]["expression"] = edits[name]
            changed.append(name)
    for helper in MONTH_TABLES:
        if helper["name"] in tables:
            actual = deepcopy(tables[helper["name"]])
            raw = actual["partitions"][0]["source"]["expression"]
            if isinstance(raw, list):
                actual["partitions"][0]["source"]["expression"] = "\n".join(raw)
            if actual != helper:
                raise ValueError("Unknown month helper; no write.")
        else:
            fixed["model"]["tables"].append(deepcopy(helper))
            changed.append(helper["name"])
    old_source, new_source, new_column = COLUMN_PATCH
    columns = tables.get("fm_native_columns")
    if not columns or len(columns.get("partitions", [])) != 1:
        raise ValueError("Unexpected comparison helper; no write.")
    partition = columns["partitions"][0]
    source = partition.get("source", {})
    if source.get("type") != "calculated" or expression_hash(source.get("expression", "")) not in {
            expression_hash(old_source), expression_hash(new_source)}:
        raise ValueError("Unknown comparison helper expression; no write.")
    label = [c for c in columns.get("columns", []) if c["name"] == "ColumnLabel"]
    if label and (len(label) != 1 or label[0] != new_column):
        raise ValueError("Unknown comparison label; no write.")
    if expression_hash(source["expression"]) != expression_hash(new_source):
        source["expression"] = new_source
        changed.append("fm_native_columns.expression")
    if not label:
        columns["columns"].append(deepcopy(new_column))
        changed.append("fm_native_columns.ColumnLabel")
    # Prove every non-allowlisted object stays byte-for-byte equivalent as JSON.
    restored = deepcopy(fixed)
    original = {t["name"]: t for t in database["model"]["tables"]}
    allowed_tables = {"fm_native_measures", "fm_native_columns"} | {t["name"] for t in MONTH_TABLES}
    restored["model"]["tables"] = [deepcopy(original[t["name"]]) if t["name"] in allowed_tables else t
        for t in restored["model"]["tables"] if t["name"] in original]
    if restored != database:
        raise AssertionError("Unrelated model change; no write.")
    return fixed, changed


def run(client, fs):
    if TEST_MODEL == ORIGINAL_MODEL or not BASE.endswith("/" + TEST_MODEL):
        raise ValueError("Invalid TEST target; no write.")
    identity_response = client.get(ITEM)
    if identity_response.status_code != 200:
        raise RuntimeError("TEST identity unavailable; no write.")
    identity = identity_response.json()
    if any(identity.get(key) != value for key,value in {
            "id":TEST_MODEL,"displayName":TEST_NAME,"type":"SemanticModel"}.items()):
        raise ValueError("TEST identity mismatch; no write.")
    before = read_definition(client)
    database = database_part(before)
    if sum(t["name"].startswith("fm_native_") for t in database["model"]["tables"]) not in (22,24):
        raise ValueError("Unexpected helper inventory; no write.")
    fixed, changed = patch_database(database)
    connections = connection_state(client)
    if not any(c.get("connectivityType") == "ShareableCloud" for c in connections):
        raise ValueError("Explicit TEST cloud mapping missing; no write.")
    if not changed:
        result = {"Stage":"TEST_R176_ALREADY_INSTALLED","TestModelID":TEST_MODEL,
                  "ModelWriteRequested":False,"KnownDisplayExpressionsAndHelpersConfirmed":True,"TESTRefreshRequiredForNewHelpers":True,
                  "RefreshRequested":False,"ReportPublished":False,
                  "NextStep":"Refresh this TEST model once to process new helpers, then open R17.6 TEST PBIP. If already processed, do not repeat refresh."}
        print(json.dumps(result,indent=2),flush=True)
        return result
    after = deepcopy(before)
    part = next(p for p in after["parts"] if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(fixed,ensure_ascii=False).encode()).decode()
    folder = (f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}/Files/"
              "ForecastMasterRefreshState/report-upgrades/Native-R176-Months-Summaries/"
              + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(uuid4()))
    fs.mkdirs(folder)
    for name, value in (("definition-before.json",before),("definition-candidate.json",after),
                        ("connections-before.json",connections)):
        verified_backup(fs,folder+"/"+name,value)
    print("Verified private TEST backup: "+folder,flush=True)
    if digest(read_definition(client)) != digest(before) or connection_state(client) != connections:
        raise RuntimeError("TEST changed concurrently; no write.")
    complete(client,client.post(BASE+"/updateDefinition",json={"definition":after,"options":{"allowPurgeData":False}}))
    received = read_definition(client)
    diff = compare_with_calculated(unpack(after)[0],unpack(received)[0])
    mapping_ok = connection_state(client) == connections
    ok = diff["Unexplained"] == 0 and mapping_ok
    result = {"Stage":"TEST_R176_UPDATED" if ok else "TEST_R176_READBACK_NEEDS_REVIEW",
              "TestModelID":TEST_MODEL,"MetadataChanged":changed,"TESTRefreshRequiredForNewHelpers":True,
              "FullDefinitionMatchesApartFromIdenticalDaxLineRepresentation":diff["Unexplained"] == 0,
              "DifferenceSummary":diff,"CloudConnectionPreserved":mapping_ok,
              "PrivateBackup":folder,"ModelWriteRequested":True,
              "SourceAmountsQueried":False,"OriginalModelWriteRequested":False,
              "RefreshRequested":False,"ReportPublished":False,
              "NextStep":("Refresh this TEST model once to process new helpers, then open R17.6 TEST PBIP. If already processed, do not repeat refresh." if ok else
                          "Keep backup and send this result. Do not retry, refresh or publish.")}
    if ok:
        fs.put(folder+"/success.json",json.dumps(result,indent=2),False)
    print(json.dumps(result,indent=2),flush=True)
    return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(),notebookutils.fs)
