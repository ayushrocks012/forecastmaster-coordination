"""Read-only forensic check of the already-attempted R17.4 TEST update.

The standalone copy is CHECK R17.4 READBACK.py. Only metadata retrieval and
copies FROM the exact private backup TO temporary local files are permitted.
No model write, backup write, amount query, refresh, publish or rollback.
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

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
TEST_MODEL = "31d00232-ac03-48fe-af39-f2e4bae82443"
TEST_NAME = "ForecastMaster Native OneLake R17.1 - TEST"
BASE = f"/v1/workspaces/{WORKSPACE}/semanticModels/{TEST_MODEL}"
ITEM = f"/v1/workspaces/{WORKSPACE}/items/{TEST_MODEL}"
BACKUP = (
    "abfss://f5cb5742-9a7c-4337-a4c0-952706dddf0b@onelake.dfs.fabric.microsoft.com/"
    "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21/Files/ForecastMasterRefreshState/"
    "report-upgrades/Native-R174-Format-Display/"
    "20261023T141622-17478716-8578-4b93-846c-4a506bab98eb"
)
BACKUP_FILES = ("definition-before.json", "definition-candidate.json", "connections-before.json")
MAX_BACKUP_BYTES = 64 * 1024 * 1024
DETAIL_LIMIT = 40
RULES = {'N Display': {'expression': ['83d093218662a8012c7d2c2c5c431506544c084e299eca356fc787c1fe262777']},
 'N Catalog Visible': {'expression': ['a1ed096682f12f94c65b23f7439585517369266b65c07ebe8118b02a6931be11']},
 'N Catalog Available': {'expression': ['16c7897c758fc38ae89aac4b979b8fe1756662aa833271d82f603af844302c3f']},
 'N Source Caption': {'expression': ['a45fc9ada06582a0f1be59a66260c420c01cc9847be13ced786ae1d26c04cc96']},
 'N Source OK': {'expression': ['91260c4f00240445f7cbf6d047a941dc63c4d8feea7256fe372f03d8e8c4b3aa']},
 'N Scenario Visible': {'expression': ['224fb77731eacd9b6bf6eb53f8846dce25a4d3ae26952a9485a6d28073514a83']},
 'N Scope Available': {'expression': ['571e278cbf01bb7a332503f94bb9ad9f3a1448b3d7481f54ce88bbcccc15fb8e']},
 'N Period Available': {'expression': ['65a319055a3ffce2a10288be6fce3cd3efb15d72b9c539709e1c137c3705188e']},
 'N Cutoff': {'expression': ['3e1ee0805af2a98e580d59d819fe6cb4267ea4432f2b7c2cccbd019c6f0e2e5f']},
 'N Monthly Numerator': {'expression': ['280044a7b6374af356860a16af45652c77daf032080a6bbd6449c8c9977b8c26'],
                         'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                    '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Monthly Denominator': {'expression': ['6c38394049f9eea1cb152668448f10c1967ade393e7a387a512626c015620754'],
                           'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                      '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Monthly': {'expression': ['3274d7e88c1e1339794ede78bc182696d9fc833f3ae17a07a8edfc936713b656'],
               'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                          '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Trend Monthly': {'expression': ['44438a048456e942a7789c8b87756fff99b90d283842bef729ff0b994365e5b7'],
                     'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Period Months': {'expression': ['91e5fce6fff5b9ada7acdb1c108d038beb1362cf588015b6b1ca730076615a8f']},
 'N Plan': {'expression': ['7fbe2abb60b6675e37e75bf449beeef7e06745b5daeee46430b3cfd96bf777f4'],
            'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                       '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Benchmark': {'expression': ['93eb5aaee3809ea25f94c4de76991622306911c3dfcea1d5a968a29cb2623554'],
                 'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                            '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Variance': {'expression': ['64525ee09318aa2b386f7dc6c6bdb57d164d4f7ddef3b93415c7b7b23a7fbe74'],
                'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                           '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Variance %': {'expression': ['d45e4c988e73543f03aa8f2df86bc31829cd4babaf743d38cb5d86b85631808b']},
 'N Headline Variance': {'expression': ['690ac7c392670a846e8acad7b38a097c7de6029723c5006ea10b72f42aa15ebc'],
                         'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                    '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Headline Variance %': {'expression': ['9d36d5afc5d2c34b56bd356ab725370b1fec474a86aa309b44f91e5075be3537']},
 'N Summary Cell': {'expression': ['e67d6e7699eeeb91a655da724364741034850a061df7546d518c0f2b4a39c1c9',
                                   '6ab85953924d3605c6f7340664de82f369314523365bd99112fb894bdb0e9b0d'],
                    'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                               '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Run Rate': {'expression': ['434e231e9f5e422a95019c31bbe897cdbb0259f6e12f7c5d30d00c65b519631c'],
                'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                           '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Growth %': {'expression': ['4fc1fe94cec78aaf19127186afcb68c073e97062a8d6bcfaf422e50016dbd137']},
 'N SOP Row Selected': {'expression': ['f90686cc5dbbd18e004cf469eeb4552fe40799f1f1915f3423fb5911e1f0fc52']},
 'N SOP Plan': {'expression': ['6b3295c53e8165906a1b12f8df8420580a7882bf7ab46edf3ebe7006dd6fa9e7'],
                'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                           '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N SOP Run Rate': {'expression': ['5882bd2cc6903f458af102482318d04234a17851745c117cd7a95086c2c0edbc'],
                    'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                               '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N SOP Growth %': {'expression': ['4f57cc7f5ead4b5690ed9b26357a0767c6ea3725948512477f680d3be9339faf']},
 'N SOP Monthly': {'expression': ['dd57e3585a8e0615f10e9cb1dbfa380fdcd235ba1d077996d92825653addc949'],
                   'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                              '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N SOP Monthly Growth %': {'expression': ['c1e02098ab614686ed5f3d2447fa82e21844e8bf93f2ccedb1baae201137fc2f']},
 'N Export Selected': {'expression': ['488d7184e52844c19a0e3463dbcc165860f45b498cad362bb58ce01d344b5960']},
 'N Export Plan': {'expression': ['04897f30186fcf00a11eb9fca8f92149ca07d3fa16a01e4f92ff6e25e5d1dd25'],
                   'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                              '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Export Run Rate': {'expression': ['772eec49fab63a3d29fe40aa7892da5745b3dbbb76805915162d71eebcc4b49f'],
                       'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                  '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Export Growth %': {'expression': ['2b04daf4beb36283edbebd50f2df3decc8a95924b704f889087edd410ae32584']},
 'N Export Order': {'expression': ['e730be8fa633332b34441ee8d65a764d2b26678ea7dc2af1199236d524929b66']},
 'N Export Monthly': {'expression': ['4cf518b0e5d5cf5bfecee35e6f162c8759723d0433cc60b91321563231abaa4e'],
                      'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                 '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Export Month Stage': {'expression': ['98a443d675dbaac8ed174b7ff51b630063a4d1e54819f7b72efcb595ec67e697']},
 'N Chart Monthly': {'expression': ['fa422123daccd6959ae03e1e38079d7c5149a860a78736f51710e943dc224bc4'],
                     'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Chart Amount': {'expression': ['dec5ddc92c8c2fee36b340718e61be818a0f8ad33c5c985d651bdcfd85dbffa3'],
                    'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                               '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Chart Share': {'expression': ['b59efc20e7accd4b466b347b5ce798fb3cad8c57993ade1ea3906d1682cf2da6']},
 'N Status': {'expression': ['5c0bcca0d2c5f657c0be14a01bf7ea0cf9dcf7937270d66748ab4ebf7e3d3d0f']},
 'N Variance Color': {'expression': ['ab31ad7cee52b774325f64076c934bddb3ff6beb849c6e1095d712989787379c']},
 'N Fit Cutoff': {'expression': ['d3dd2b6875c0ef51b5c9c1a9db0a78637e7f6b975b5a59e5f7a3353fb96ce2ed']},
 'N Actual Only': {'expression': ['8826b03260473ca437c797d32a933eb7bddf870b3ebd5d5e16d9ce61044371e8']},
 'N Line Visible': {'expression': ['3acf9f5430aa96a01e094d01719a3a1954156b8f065fbf106dc6e759a021e669']},
 'N Selected Month': {'expression': ['98983667084cf6376a0a68140e675dd2a585b6a57c5a478b585a1e0a0f7fe762']},
 'N Selected Monthly': {'expression': ['580775cdf730607dfee50efb75ffe6817fe227b3010c67a5cab8eaf393b6b950'],
                        'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                   '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Headline Cell': {'expression': ['abf3f6a3a083a185d6f85e8353f814bf20bde94a9b4b7e69de6f6ab05d44ed37'],
                     'formatStringDefinition': ['db9441c63a6527e0891cc07c308ea09280392beec0faa5043886dcc2ffbd2b1f',
                                                '92f1f7f494fa62f9fd4a728ff9f3f409e1fcbf18def64ddf1310354c7c4b8a60']},
 'N Measure Caption': {'expression': ['c5fa17fb3d90c92d173610329f9025251a93e4704b96a2164cda7b568037c5cb']},
 'N Group Visible': {'expression': ['6b975f0b80238fc7341493dd5fcaf4926fde29a4d617fd54526f4966240291bb']}}


class CheckStopped(RuntimeError):
    """A controlled reason code, containing no private response or value."""


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
    with TemporaryDirectory(prefix="fm-r174-readonly-") as directory:
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


def native_measures(database):
    tables = database["model"]["tables"]
    require(isinstance(tables, list), "TABLE_INVENTORY_INVALID")
    names = [table["name"] for table in tables]
    require(len(names) == len(set(names)), "TABLE_INVENTORY_NOT_UNIQUE")
    require(sum(name.startswith("fm_native_") for name in names) == 22, "NATIVE_TABLE_INVENTORY_UNEXPECTED")
    table = next(table for table in tables if table["name"] == "fm_native_measures")
    measures = table["measures"]
    by_name = {measure["name"]: measure for measure in measures}
    require(len(by_name) == len(measures) and set(by_name) == set(RULES), "NATIVE_MEASURE_INVENTORY_UNEXPECTED")
    return by_name


def field_value(measure, key):
    return measure["expression"] if key == "expression" else measure[key]["expression"]


def verify_backup_pair(before, candidate):
    before_decoded, old_database = unpack(before)
    candidate_decoded, new_database = unpack(candidate)
    old, new = native_measures(old_database), native_measures(new_database)
    restored = deepcopy(candidate_decoded)
    restore_db = next(part for part in restored["parts"] if part["path"] == "model.bim")["payload"]
    restore_measures = native_measures(restore_db)
    for name, fields in RULES.items():
        for key, fingerprints in fields.items():
            old_hash = known_expression_hash(field_value(old[name], key))
            new_hash = known_expression_hash(field_value(new[name], key))
            require(old_hash in fingerprints, "BACKUP_BEFORE_NOT_KNOWN_R174_INPUT")
            require(new_hash == fingerprints[-1], "BACKUP_CANDIDATE_NOT_KNOWN_R174_OUTPUT")
            if len(fingerprints) == 2:
                if key == "expression":
                    restore_measures[name][key] = deepcopy(old[name][key])
                else:
                    restore_measures[name][key]["expression"] = deepcopy(old[name][key]["expression"])
        require(("formatStringDefinition" in new[name]) == ("formatStringDefinition" in fields),
                "BACKUP_DYNAMIC_FORMAT_INVENTORY_UNEXPECTED")
    require(digest(restored) == digest(before_decoded), "BACKUP_CONTAINS_UNDECLARED_CHANGE")
    return candidate_decoded, new_database


SAFE_KEYS = frozenset("parts payload payloadType path name model tables measures expression "
    "formatStringDefinition annotations columns partitions source relationships roles members "
    "dataSources expressions hierarchies levels perspectives cultures culture compatibilityLevel "
    "type mode dataType formatString lineageTag sourceLineageTag isHidden sortByColumn "
    "displayFolder description defaultMode entityName expressionSource schemaName fromTable "
    "toTable fromColumn toColumn modelPermission tablePermissions filterExpression".split())


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


def run(client, fs):
    reader = MetadataReader(client)
    response = reader.get(ITEM)
    require(response.status_code == 200, "TEST_IDENTITY_UNAVAILABLE")
    identity = response.json()
    require(identity.get("id") == TEST_MODEL and identity.get("displayName") == TEST_NAME
            and identity.get("type") == "SemanticModel", "TEST_IDENTITY_MISMATCH")
    print("Reading the exact private backup and TEST metadata only. No model update or refresh.", flush=True)
    backups = read_backups(fs)
    before, candidate = backups[BACKUP_FILES[0]], backups[BACKUP_FILES[1]]
    candidate_decoded, candidate_db = verify_backup_pair(before, candidate)
    saved_connections = backups[BACKUP_FILES[2]]
    require(isinstance(saved_connections, list) and
            any(c.get("connectivityType") == "ShareableCloud" for c in saved_connections),
            "BACKUP_EXPLICIT_CLOUD_MAPPING_MISSING")
    first = definition(reader)
    first_connections = connections(reader)
    second = definition(reader)
    second_connections = connections(reader)
    decoded, current_db = unpack(second)
    diff = compare(candidate_decoded, decoded)
    stable = digest(unpack(first)[0]) == digest(decoded) and digest(first_connections) == digest(second_connections)
    mapping_match = digest(sorted(saved_connections, key=digest)) == digest(second_connections)
    # The full definition comparison covers every source/security/helper object
    # and every expression. A repair-field-only match cannot establish a pass.
    try:
        current_native = native_measures(current_db)
        candidate_fields = compare(native_measures(candidate_db), current_native)
        inventory_match = True
    except CheckStopped:
        current_native, candidate_fields, inventory_match = {}, None, False
    try:
        fingerprints_match = inventory_match and all(
            known_expression_hash(field_value(current_native[name], key)) == fingerprints[-1]
            for name, fields in RULES.items() for key, fingerprints in fields.items())
    except (CheckStopped, KeyError, TypeError):
        fingerprints_match = False
    verified = stable and mapping_match and inventory_match and diff["Unexplained"] == 0
    result = {
        "Stage": "TEST_R174_READBACK_VERIFIED" if verified else "TEST_R174_READBACK_NEEDS_REVIEW",
        "CheckVersion": "R01", "TestModelID": TEST_MODEL,
        "ExactPrivateBackupRead": True, "BackupCandidateContainsOnlyDeclaredRepair": True,
        "RawDefinitionMatch": digest(candidate) == digest(second),
        "ModelJsonExactMatch": digest(candidate_db) == digest(current_db),
        "WholeDefinitionMatchesApartFromIdenticalDaxLineRepresentation": diff["Unexplained"] == 0,
        "NativeInventoryMatchesExpected": inventory_match,
        "KnownNativeExpressionAndFormatFingerprintsMatch": fingerprints_match,
        "NativeMeasureObjectsExactMatch": candidate_fields is not None and candidate_fields["Total"] == 0,
        "CloudConnectionMatchesBackup": mapping_match, "TwoMetadataSnapshotsStable": stable,
        "DifferenceSummary": diff,
        "CompanyAmountsQueried": False, "ModelWriteRequested": False,
        "RefreshRequested": False, "ReportPublished": False,
        "NextStep": "Send this JSON output in the chat. Keep the backup. Do not rerun the updater or refresh/publish."
    }
    print(json.dumps(result, indent=2), flush=True)
    return result


def safe_run(client, fs):
    try:
        return run(client, fs)
    except Exception as error:
        # Suppress response bodies, values and traceback locals in shared output.
        result = {"Stage": "TEST_R174_READBACK_CHECK_STOPPED", "CheckVersion": "R01",
                  "ReasonCode": str(error) if isinstance(error, CheckStopped) else "METADATA_OR_BACKUP_READ_FAILED",
                  "ModelWriteRequested": False, "CompanyAmountsQueried": False,
                  "RefreshRequested": False, "ReportPublished": False,
                  "NextStep": "Send this JSON output. Keep the backup; do not rerun the updater."}
        print(json.dumps(result, indent=2), flush=True)
        return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    safe_run(fabric.FabricRestClient(), notebookutils.fs)
