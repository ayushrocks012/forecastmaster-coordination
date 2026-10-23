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
RULES = {}  # Replaced with frozen, public-code hashes by build_probe.py.


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
