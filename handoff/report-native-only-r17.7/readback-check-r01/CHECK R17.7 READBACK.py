"""ONE NEW cell in ForecastMaster_GM_Setup. Already-updated TEST metadata only.
Read exact R03 backup and verify three inferred-name flags plus the WHOLE model.
No model/backup write, amount query, refresh, rollback, publishing or retries.
"""
import base64
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import time
from urllib.parse import quote
from uuid import UUID

WORKSPACE = 'f5cb5742-9a7c-4337-a4c0-952706dddf0b'

TEST_MODEL = '31d00232-ac03-48fe-af39-f2e4bae82443'

TEST_NAME = 'ForecastMaster Native OneLake R17.1 - TEST'

BASE = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/semanticModels/31d00232-ac03-48fe-af39-f2e4bae82443'

ITEM = '/v1/workspaces/f5cb5742-9a7c-4337-a4c0-952706dddf0b/items/31d00232-ac03-48fe-af39-f2e4bae82443'

BACKUP = 'abfss://f5cb5742-9a7c-4337-a4c0-952706dddf0b@onelake.dfs.fabric.microsoft.com/d6e33ebd-67b1-420a-8d84-c3a0d04d8b21/Files/ForecastMasterRefreshState/report-upgrades/Native-R177-Performance-Files-R03/20261023T185452-34a80b74-e9c7-4749-af9f-d5a835b23e5e'

BACKUP_FILES = ('definition-before.json',
 'definition-candidate.json',
 'connections-before.json',
 'numerical-check-summary.json')

MAX_BACKUP_BYTES = 67108864

DETAIL_LIMIT = 40

INPUT_HASHES = {'N Actual Only': {'expression': '8826b03260473ca437c797d32a933eb7bddf870b3ebd5d5e16d9ce61044371e8'},
 'N Benchmark': {'expression': '93eb5aaee3809ea25f94c4de76991622306911c3dfcea1d5a968a29cb2623554',
                 'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Catalog Available': {'expression': '16c7897c758fc38ae89aac4b979b8fe1756662aa833271d82f603af844302c3f'},
 'N Catalog Visible': {'expression': 'a1ed096682f12f94c65b23f7439585517369266b65c07ebe8118b02a6931be11'},
 'N Chart Amount': {'expression': 'dec5ddc92c8c2fee36b340718e61be818a0f8ad33c5c985d651bdcfd85dbffa3',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Chart Monthly': {'expression': '4fcd764501395fa2d41cc4dfdd4df0dd886dde2020995ba145f418c9900e034f',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Chart Share': {'expression': 'b59efc20e7accd4b466b347b5ce798fb3cad8c57993ade1ea3906d1682cf2da6'},
 'N Cutoff': {'expression': '3e1ee0805af2a98e580d59d819fe6cb4267ea4432f2b7c2cccbd019c6f0e2e5f'},
 'N Display': {'expression': '83d093218662a8012c7d2c2c5c431506544c084e299eca356fc787c1fe262777'},
 'N Export Growth %': {'expression': '2b04daf4beb36283edbebd50f2df3decc8a95924b704f889087edd410ae32584'},
 'N Export Month Stage': {'expression': '98a443d675dbaac8ed174b7ff51b630063a4d1e54819f7b72efcb595ec67e697'},
 'N Export Monthly': {'expression': '4cf518b0e5d5cf5bfecee35e6f162c8759723d0433cc60b91321563231abaa4e',
                      'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Order': {'expression': 'e730be8fa633332b34441ee8d65a764d2b26678ea7dc2af1199236d524929b66'},
 'N Export Plan': {'expression': '04897f30186fcf00a11eb9fca8f92149ca07d3fa16a01e4f92ff6e25e5d1dd25',
                   'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Run Rate': {'expression': '772eec49fab63a3d29fe40aa7892da5745b3dbbb76805915162d71eebcc4b49f',
                       'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Export Selected': {'expression': '488d7184e52844c19a0e3463dbcc165860f45b498cad362bb58ce01d344b5960'},
 'N Fit Cutoff': {'expression': 'd3dd2b6875c0ef51b5c9c1a9db0a78637e7f6b975b5a59e5f7a3353fb96ce2ed'},
 'N Group Visible': {'expression': '6b975f0b80238fc7341493dd5fcaf4926fde29a4d617fd54526f4966240291bb'},
 'N Growth %': {'expression': '4fc1fe94cec78aaf19127186afcb68c073e97062a8d6bcfaf422e50016dbd137'},
 'N Headline Cell': {'expression': '0a3c29ae6844b5cc7fc7ac3f2a03fc63bd9af068dd0d1fc33679ab75c713789e',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Headline Variance': {'expression': '690ac7c392670a846e8acad7b38a097c7de6029723c5006ea10b72f42aa15ebc',
                         'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Headline Variance %': {'expression': '9d36d5afc5d2c34b56bd356ab725370b1fec474a86aa309b44f91e5075be3537'},
 'N Line Visible': {'expression': '6cf95d187c33f0d145a1fc76e43a24fac421b595ad5e475af0c060617c0c26b8'},
 'N Measure Caption': {'expression': 'd67f9b7b48d7cdfc28e8331225572d09532ff2bbef3c04d68706c7c82e575198'},
 'N Monthly': {'expression': '3274d7e88c1e1339794ede78bc182696d9fc833f3ae17a07a8edfc936713b656',
               'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Monthly Denominator': {'expression': '6c38394049f9eea1cb152668448f10c1967ade393e7a387a512626c015620754',
                           'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Monthly Numerator': {'expression': '280044a7b6374af356860a16af45652c77daf032080a6bbd6449c8c9977b8c26',
                         'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Period Available': {'expression': 'e4be688b118e0d2a5ef26f02eda77d2e12c0e19675af13b010bbcd6bf0d741f2'},
 'N Period Months': {'expression': '91e5fce6fff5b9ada7acdb1c108d038beb1362cf588015b6b1ca730076615a8f'},
 'N Plan': {'expression': '7fbe2abb60b6675e37e75bf449beeef7e06745b5daeee46430b3cfd96bf777f4',
            'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Run Rate': {'expression': '434e231e9f5e422a95019c31bbe897cdbb0259f6e12f7c5d30d00c65b519631c',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Growth %': {'expression': '4f57cc7f5ead4b5690ed9b26357a0767c6ea3725948512477f680d3be9339faf'},
 'N SOP Monthly': {'expression': 'dd57e3585a8e0615f10e9cb1dbfa380fdcd235ba1d077996d92825653addc949',
                   'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Monthly Growth %': {'expression': 'c1e02098ab614686ed5f3d2447fa82e21844e8bf93f2ccedb1baae201137fc2f'},
 'N SOP Plan': {'expression': '6b3295c53e8165906a1b12f8df8420580a7882bf7ab46edf3ebe7006dd6fa9e7',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N SOP Row Selected': {'expression': 'f90686cc5dbbd18e004cf469eeb4552fe40799f1f1915f3423fb5911e1f0fc52'},
 'N SOP Run Rate': {'expression': '5882bd2cc6903f458af102482318d04234a17851745c117cd7a95086c2c0edbc',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Scenario Visible': {'expression': '224fb77731eacd9b6bf6eb53f8846dce25a4d3ae26952a9485a6d28073514a83'},
 'N Scope Available': {'expression': '571e278cbf01bb7a332503f94bb9ad9f3a1448b3d7481f54ce88bbcccc15fb8e'},
 'N Selected Month': {'expression': '98983667084cf6376a0a68140e675dd2a585b6a57c5a478b585a1e0a0f7fe762'},
 'N Selected Monthly': {'expression': '580775cdf730607dfee50efb75ffe6817fe227b3010c67a5cab8eaf393b6b950',
                        'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Source Caption': {'expression': 'a45fc9ada06582a0f1be59a66260c420c01cc9847be13ced786ae1d26c04cc96'},
 'N Source OK': {'expression': '91260c4f00240445f7cbf6d047a941dc63c4d8feea7256fe372f03d8e8c4b3aa'},
 'N Status': {'expression': '5c0bcca0d2c5f657c0be14a01bf7ea0cf9dcf7937270d66748ab4ebf7e3d3d0f'},
 'N Summary Cell': {'expression': '13a56278497e537e857839007a722248aecfbd7db9b3d2441eeac01938b54f37',
                    'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Trend Monthly': {'expression': '44438a048456e942a7789c8b87756fff99b90d283842bef729ff0b994365e5b7',
                     'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Variance': {'expression': '64525ee09318aa2b386f7dc6c6bdb57d164d4f7ddef3b93415c7b7b23a7fbe74',
                'formatStringDefinition': '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60'},
 'N Variance %': {'expression': 'd45e4c988e73543f03aa8f2df86bc31829cd4babaf743d38cb5d86b85631808b'},
 'N Variance Color': {'expression': 'ab31ad7cee52b774325f64076c934bddb3ff6beb849c6e1095d712989787379c'}}

EDIT_HASHES = {'N Benchmark': '364df3afb10cb30e6845696326b7553cc0eb04305d4435c14c4ee8f8b75c7182',
 'N Catalog Available': '7580bf6ef8064976e1e343fff330388a44e0891148494082523a7dea012f07e5',
 'N Chart Monthly': '84890255cbc43db5d69b57effe4de43269dca599ff9c9c4f995d3ec4484e8176',
 'N Cutoff': '250140a34c7c06575151670c9de697abddc305c247274001dbcaa03fbe74ce7d',
 'N Fit Cutoff': '5406e8c96756aa7f81619a577585ca0076f636fef787b80344bd2a014632973b',
 'N Headline Cell': '53ab234ec68ecbf4ad843752a3cd442b0f32984730b1e5cb5e9343d446dfa62d',
 'N Monthly Denominator': '90c5c00aea4d38076f7f0b1f828d6fe0fc7cfc032426176eb05482c3325f3883',
 'N Monthly Numerator': 'ce3b0829fadfb13fe403f297b09f5ec9e5f7d78f173a5e72de582dfc42411901',
 'N Plan': 'c36f63bb84207f273dc92443e81e6b76bd76cf3d88d73c6349a32cd800f84773',
 'N Scope Available': '822e3a2da9b17dc814002b6b0375402911b972712d84d8a73ec21037dbef2cca',
 'N Source Caption': 'ee656f37a0dd0550c4270f79b131e2f8e2954df5f6c1f6dd85f7ce242e655039',
 'N Source OK': '9c9e7bff36a3dd46896700986d15a534a060de3d0ec6fbf2ff9a2a419063e76e',
 'N Summary Cell': 'ffdd85db4c887fc2daa871cfdb61d9263b7378f33de5db36cba9564d8b0d0b48',
 'N Trend Monthly': '8357b2389f680dbe5401184c199f9d4b9e050c06bafb1194f77f359fc0e82ca8',
 'N Variance %': '669e3d8bcdcd104906221f29aa7e8f47caa4bc769c7b0b4329e441bb733a44a5'}

FIT_OBJECT_HASHES = {'N Fit Mean': '5ee226496d47339719a1ebb5702aa3ed00f7fbcac9df06fb43626b2048dff1aa',
 'N Fit Slope': '9fce2f12ac4c4b062fd8059ff25ed3b44832df1d0f2bd96abee0c6fac5fbcc65'}

HELPER_SPECS = {'fm_native_files': {'Columns': [{'dataType': 'dateTime',
                                  'formatString': 'dd mmm yyyy hh:mm:ss',
                                  'name': 'ImportedAtUTC',
                                  'sourceColumn': '[ImportedAtUTC]',
                                  'summarizeBy': 'none',
                                  'type': 'calculatedTableColumn'},
                                 {'dataType': 'string',
                                  'name': 'FileChoiceLabel',
                                  'sortByColumn': 'ImportedAtUTC',
                                  'sourceColumn': '[FileChoiceLabel]',
                                  'summarizeBy': 'none',
                                  'type': 'calculatedTableColumn'}],
                     'InputHash': 'fcf54481d737f3aeac4d5a6d76caf2fb1e3270a78b46778a2fe54cce6f633d0b',
                     'OutputHash': 'e9e7084c7b19c6bfd8b60324d1d10db029b9c4188bf2d768bb3d8df6c713a666'},
 'fm_native_lines': {'Columns': [{'dataType': 'string',
                                  'name': 'SeriesLabel',
                                  'sourceColumn': '[SeriesLabel]',
                                  'summarizeBy': 'none',
                                  'type': 'calculatedTableColumn'}],
                     'InputHash': 'cd45b14feb340adcff92d1cbad92257787161e373fd8beb4ae1d7adb3f7291d9',
                     'OutputHash': '98e4d4678e6af583c25d57bce0d8a2f94258f99915f3c802dad9ec33de751e0c'}}

RULES = {'N Actual Only': {},
 'N Benchmark': {},
 'N Catalog Available': {},
 'N Catalog Visible': {},
 'N Chart Amount': {},
 'N Chart Monthly': {},
 'N Chart Share': {},
 'N Cutoff': {},
 'N Display': {},
 'N Export Growth %': {},
 'N Export Month Stage': {},
 'N Export Monthly': {},
 'N Export Order': {},
 'N Export Plan': {},
 'N Export Run Rate': {},
 'N Export Selected': {},
 'N Fit Cutoff': {},
 'N Fit Mean': {},
 'N Fit Slope': {},
 'N Group Visible': {},
 'N Growth %': {},
 'N Headline Cell': {},
 'N Headline Variance': {},
 'N Headline Variance %': {},
 'N Line Visible': {},
 'N Measure Caption': {},
 'N Monthly': {},
 'N Monthly Denominator': {},
 'N Monthly Numerator': {},
 'N Period Available': {},
 'N Period Months': {},
 'N Plan': {},
 'N Run Rate': {},
 'N SOP Growth %': {},
 'N SOP Monthly': {},
 'N SOP Monthly Growth %': {},
 'N SOP Plan': {},
 'N SOP Row Selected': {},
 'N SOP Run Rate': {},
 'N Scenario Visible': {},
 'N Scope Available': {},
 'N Selected Month': {},
 'N Selected Monthly': {},
 'N Source Caption': {},
 'N Source OK': {},
 'N Status': {},
 'N Summary Cell': {},
 'N Trend Monthly': {},
 'N Variance': {},
 'N Variance %': {},
 'N Variance Color': {}}

SAFE_KEYS = ['FileChoiceLabel',
 'ImportedAtUTC',
 'SeriesLabel',
 'annotations',
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
 'fm_native_files',
 'fm_native_lines',
 'formatString',
 'formatStringDefinition',
 'fromColumn',
 'fromTable',
 'hierarchies',
 'isHidden',
 'isNameInferred',
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

class CheckStopped(RuntimeError):
    pass

def require(condition, code):
    if not condition:
        raise CheckStopped(code)


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


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


def known_expression_hash(value):
    # Same fingerprint convention as the frozen updater, ONLY for identifying
    # known repair fields. Full-definition comparison below does NOT strip text.
    return hashlib.sha256(expression_text(value).strip().replace("\r\n", "\n").encode()).hexdigest()


class MetadataReader:
    """Restrict even helper calls to this TEST and read-only operation routes."""
    def __init__(self, client):
        self.client = client

    def get(self, path):
        allowed = path == ITEM or path == ITEM + "/connections"
        allowed = allowed or path.startswith(ITEM + "/connections?continuationToken=")
        if path.startswith("/v1/operations/"):
            suffix = path.removeprefix("/v1/operations/")
            operation = suffix.removesuffix("/result")
            allowed = str(UUID(operation)) == operation and suffix in {operation, operation + "/result"}
        require(allowed, "API_ROUTE_NOT_READ_ONLY")
        return self.client.get(path)

    def post(self, path):
        require(path == BASE + "/getDefinition?format=TMSL", "API_ROUTE_NOT_READ_ONLY")
        return self.client.post(path)


def definition(reader):
    response = reader.post(BASE + "/getDefinition?format=TMSL")
    require(response.status_code in {200, 202}, "METADATA_RETRIEVAL_FAILED")
    if response.status_code == 202:
        operation = "/v1/operations/" + str(UUID(response.headers["x-ms-operation-id"]))
        deadline = time.monotonic() + 360
        while time.monotonic() < deadline:
            time.sleep(min(30, max(1, int(response.headers.get("Retry-After", "5")))))
            response = reader.get(operation)
            require(response.status_code == 200, "METADATA_OPERATION_STATUS_UNAVAILABLE")
            status = response.json().get("status")
            require(status not in {"Failed", "Cancelled", "Canceled"}, "METADATA_OPERATION_FAILED")
            if status == "Succeeded":
                response = reader.get(operation + "/result")
                require(response.status_code == 200, "METADATA_OPERATION_RESULT_UNAVAILABLE")
                break
        else:
            raise CheckStopped("METADATA_OPERATION_TIMEOUT")
    value = response.json()["definition"]
    unpack(value)
    return value


def connections(reader):
    values, token, seen = [], None, set()
    for _ in range(100):
        path = ITEM + "/connections"
        if token:
            path += "?continuationToken=" + quote(token, safe="")
        response = reader.get(path)
        require(response.status_code == 200, "CONNECTION_INVENTORY_UNAVAILABLE")
        page = response.json()
        require(isinstance(page.get("value"), list), "CONNECTION_INVENTORY_INVALID")
        values.extend(page["value"])
        token = page.get("continuationToken")
        if not token:
            return sorted(values, key=digest)
        require(isinstance(token, str) and token not in seen, "CONNECTION_PAGINATION_INVALID")
        seen.add(token)
    raise CheckStopped("CONNECTION_INVENTORY_INCOMPLETE")


def read_backups(fs):
    entries = fs.ls(BACKUP)
    values = {}
    with TemporaryDirectory(prefix="fm-r177-readback-") as directory:
        for name in BACKUP_FILES:
            found = [entry for entry in entries if entry.name == name]
            require(len(found) == 1, "BACKUP_FILE_NOT_UNIQUE")
            size = found[0].size
            require(type(size) is int and 0 < size <= MAX_BACKUP_BYTES, "BACKUP_SIZE_INVALID")
            copies = []
            for index in range(2):
                local = Path(directory) / (str(index) + "-" + name)
                require(fs.cp(BACKUP + "/" + name, local.as_uri(), False), "BACKUP_READ_COPY_FAILED")
                raw = local.read_bytes()
                require(len(raw) == size, "BACKUP_READ_LENGTH_MISMATCH")
                copies.append(raw)
            require(copies[0] == copies[1], "BACKUP_READ_CHANGED")
            values[name] = parse_json(copies[0].decode("utf-8-sig"))
    return values


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
        if table["name"] not in {"fm_native_columns", "fm_native_start_month", "fm_native_end_month", "fm_native_files", "fm_native_lines"}:
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


def named(items, code):
    require(isinstance(items, list) and all(isinstance(item, dict) and isinstance(item.get("name"), str)
                                          for item in items), code)
    result = {item["name"]: item for item in items}
    require(len(result) == len(items), code)
    return result


def exact_expression_hash(value):
    return hashlib.sha256(expression_text(value).encode("utf-8")).hexdigest()


def verify_backup_pair(before, candidate):
    old_decoded, old_db = unpack(before)
    new_decoded, new_db = unpack(candidate)
    old_tables = named(old_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    new_tables = named(new_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    require(sum(n.startswith("fm_native_") for n in old_tables) == 24, "BACKUP_NATIVE_TABLE_COUNT_UNEXPECTED")
    require(set(old_tables) == set(new_tables), "BACKUP_TABLE_INVENTORY_CHANGED")
    old_measures = named(old_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    new_measures = named(new_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    require(set(old_measures) == set(INPUT_HASHES), "BACKUP_NOT_KNOWN_R176_INPUT")
    require(set(new_measures) == set(INPUT_HASHES) | set(FIT_OBJECT_HASHES), "BACKUP_NOT_KNOWN_R177_OUTPUT")
    restored = deepcopy(new_decoded)
    restore_db = next(p for p in restored["parts"] if p["path"] == "model.bim")["payload"]
    restore_tables = named(restore_db["model"]["tables"], "BACKUP_TABLE_INVENTORY_INVALID")
    restore_measures = named(restore_tables["fm_native_measures"]["measures"], "BACKUP_MEASURE_INVENTORY_INVALID")
    for name, fields in INPUT_HASHES.items():
        old = old_measures[name]
        require(known_expression_hash(old["expression"]) == fields["expression"], "BACKUP_UNKNOWN_INPUT_EXPRESSION")
        require(("formatStringDefinition" in old) == ("formatStringDefinition" in fields), "BACKUP_INPUT_FORMAT_INVENTORY_CHANGED")
        if "formatStringDefinition" in fields:
            require(known_expression_hash(old["formatStringDefinition"]["expression"]) == fields["formatStringDefinition"],
                    "BACKUP_UNKNOWN_INPUT_FORMAT")
        if name in EDIT_HASHES:
            require(exact_expression_hash(new_measures[name]["expression"]) == EDIT_HASHES[name],
                    "BACKUP_UNKNOWN_CANDIDATE_EXPRESSION")
            restore_measures[name]["expression"] = deepcopy(old["expression"])
    for name, expected in FIT_OBJECT_HASHES.items():
        require(digest(new_measures[name]) == expected, "BACKUP_UNKNOWN_FIT_MEASURE")
    restore_tables["fm_native_measures"]["measures"] = [m for m in restore_tables["fm_native_measures"]["measures"]
                                                        if m["name"] not in FIT_OBJECT_HASHES]
    for name, spec in HELPER_SPECS.items():
        old_table, new_table, restored_table = old_tables[name], new_tables[name], restore_tables[name]
        require(len(old_table.get("partitions", [])) == len(new_table.get("partitions", [])) == 1,
                "BACKUP_HELPER_PARTITIONS_CHANGED")
        old_source, new_source = old_table["partitions"][0]["source"], new_table["partitions"][0]["source"]
        require(old_source.get("type") == new_source.get("type") == "calculated", "BACKUP_HELPER_TYPE_CHANGED")
        require(known_expression_hash(old_source["expression"]) == spec["InputHash"], "BACKUP_UNKNOWN_INPUT_HELPER")
        require(exact_expression_hash(new_source["expression"]) == spec["OutputHash"], "BACKUP_UNKNOWN_OUTPUT_HELPER")
        restored_table["partitions"][0]["source"]["expression"] = deepcopy(old_source["expression"])
        old_columns = named(old_table["columns"], "BACKUP_COLUMN_INVENTORY_INVALID")
        new_columns = named(new_table["columns"], "BACKUP_COLUMN_INVENTORY_INVALID")
        additions = {column["name"]: column for column in spec["Columns"]}
        require(not set(old_columns) & set(additions), "BACKUP_NEW_COLUMN_ALREADY_PRESENT")
        require(set(new_columns) == set(old_columns) | set(additions), "BACKUP_COLUMN_INVENTORY_CHANGED")
        for column, expected in additions.items():
            require(digest(new_columns[column]) == digest(expected), "BACKUP_UNKNOWN_NEW_COLUMN")
        restored_table["columns"] = [column for column in restored_table["columns"] if column["name"] not in additions]
    require(digest(restored) == digest(old_decoded), "BACKUP_UNDECLARED_MODEL_OR_PART_CHANGE")
    return new_decoded, new_db


def verify_preflight(value):
    expected = {"Revision": "R03", "Checks": 72, "NumericComparisons": 72, "BlankComparisons": 0,
                "Mismatches": 0, "DirectOriginalScalarReads": 54, "DerivedOriginalVarianceComparisons": 18,
                "ActualCandidateScalarReads": 72, "OriginalVarianceFormulaVerified": True,
                "OriginalVariancePercentMeasureExecuted": False, "NumericBenchmarks": 18,
                "NumericFutureTrends": 9, "ScalarQueries": 126, "MetadataQueries": 3,
                "SourceSelectionMetadataStable": True, "CompanyAmountValuesPrintedOrStored": False,
                "ValidationMethod": "54_DIRECT_BASELINE_AND_18_VERIFIED_FORMULA_EXPECTATIONS_VS_72_ACTUAL_CANDIDATES",
                "ComparisonCountsByMetric": {m: {"Numeric": 24, "Blank": 0} for m in ("market", "ef", "share")}}
    require(isinstance(value, dict), "PREFLIGHT_RECEIPT_INVALID")
    require(all(key in value and digest(value[key]) == digest(want) for key, want in expected.items()),
            "PREFLIGHT_RECEIPT_NOT_EXPECTED_SUCCESS")
    return {key: value[key] for key in ("Revision", "Checks", "NumericComparisons", "BlankComparisons", "Mismatches",
                                       "DirectOriginalScalarReads", "DerivedOriginalVarianceComparisons", "ActualCandidateScalarReads")}


def inferred_name_normalization(expected, observed):
    right = deepcopy(observed)
    expected_db = next(p for p in expected["parts"] if p["path"] == "model.bim")["payload"]
    right_db = next(p for p in right["parts"] if p["path"] == "model.bim")["payload"]
    left_tables = named(expected_db["model"]["tables"], "CANDIDATE_TABLE_INVENTORY_INVALID")
    right_tables = named(right_db["model"]["tables"], "CURRENT_TABLE_INVENTORY_INVALID")
    details = []
    for table, spec in HELPER_SPECS.items():
        left_columns = named(left_tables[table]["columns"], "CANDIDATE_COLUMN_INVENTORY_INVALID")
        right_columns = named(right_tables.get(table, {}).get("columns", []), "CURRENT_COLUMN_INVENTORY_INVALID")
        for col in spec["Columns"]:
            name = col["name"]
            a, b = left_columns[name], right_columns.get(name, {})
            if "isNameInferred" not in b:
                continue
            value = b["isNameInferred"]
            accepted = ("isNameInferred" not in a and type(value) is bool and value is True
                        and a.get("type") == b.get("type") == "calculatedTableColumn"
                        and a.get("sourceColumn") == b.get("sourceColumn") == "[" + name + "]")
            details.append({"Table": table, "Column": name, "Property": "isNameInferred",
                            "ObservedBoolean": value if type(value) is bool else "NONBOOLEAN_VALUE_WITHHELD",
                            "Accepted": accepted})
            if accepted:
                del b["isNameInferred"]
    return right, details


def run(client, fs):
    reader = MetadataReader(client)
    response = reader.get(ITEM)
    require(response.status_code == 200, "TEST_IDENTITY_UNAVAILABLE")
    identity = response.json()
    require(identity.get("id") == TEST_MODEL and identity.get("displayName") == TEST_NAME
            and identity.get("type") == "SemanticModel", "TEST_IDENTITY_MISMATCH")
    print("Read-only: exact R03 private backup, preflight receipt and two TEST metadata snapshots. No amount query, update or refresh.", flush=True)
    backups = read_backups(fs)
    expected, expected_db = verify_backup_pair(backups["definition-before.json"], backups["definition-candidate.json"])
    numeric = verify_preflight(backups["numerical-check-summary.json"])
    saved_connections = backups["connections-before.json"]
    require(isinstance(saved_connections, list) and any(c.get("connectivityType") == "ShareableCloud" for c in saved_connections),
            "BACKUP_EXPLICIT_CLOUD_MAPPING_MISSING")
    first, first_mapping = definition(reader), connections(reader)
    second, second_mapping = definition(reader), connections(reader)
    observed, _ = unpack(second)
    raw_diff = compare_with_calculated(expected, observed)
    normalized, additions = inferred_name_normalization(expected, observed)
    diff = compare_with_calculated(expected, normalized)
    stable = digest(unpack(first)[0]) == digest(observed) and digest(first_mapping) == digest(second_mapping)
    mapping_ok = digest(sorted(saved_connections, key=digest)) == digest(second_mapping)
    flags_ok = all(detail["Accepted"] for detail in additions)
    verified = stable and mapping_ok and flags_ok and diff["Unexplained"] == 0
    result = {"Stage": "TEST_R177_READBACK_VERIFIED" if verified else "TEST_R177_READBACK_NEEDS_REVIEW",
              "CheckVersion": "R01", "UpdaterRevision": "R03", "TestModelID": TEST_MODEL,
              "ExactPrivateBackupRead": True, "BackupPairVerifiedAgainstFrozenR177": True,
              "NumericalPreflightReceiptVerified": True, "NumericalPreflight": numeric,
              "TwoMetadataSnapshotsStable": stable, "CloudConnectionMatchesBackup": mapping_ok,
              "WholeDefinitionMatchesWithOnlyDocumentedNormalizations": diff["Unexplained"] == 0,
              "InferredNameMetadata": additions,
              "RawUnexplainedDifferenceCount": raw_diff["Unexplained"], "DifferenceSummaryAfterStrictCheck": diff,
              "ModelWriteRequested": False, "OriginalModelWriteRequested": False,
              "CompanyAmountsQueried": False, "RefreshRequested": False, "ReportPublished": False,
              "NextStep": ("Refresh ONLY existing R17.1 TEST once; require warning-free Completed, then open unchanged R17.7 TEST PBIP. Send this JSON and refresh result."
                           if verified else "Send this JSON; keep backup. Do not rerun updater, refresh, open R17.7 or publish.")}
    print(json.dumps(result, indent=2), flush=True)
    return result


def safe_run(client, fs):
    try:
        return run(client, fs)
    except Exception as exc:
        result = {"Stage": "TEST_R177_READBACK_CHECK_STOPPED", "CheckVersion": "R01",
                  "ReasonCode": str(exc) if isinstance(exc, CheckStopped) else "METADATA_OR_BACKUP_READ_FAILED",
                  "ModelWriteRequested": False, "CompanyAmountsQueried": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "Send this JSON. Do not retry the updater, refresh or publish; preserve the private backup."}
        print(json.dumps(result, indent=2), flush=True)
        return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    safe_run(fabric.FabricRestClient(), notebookutils.fs)
