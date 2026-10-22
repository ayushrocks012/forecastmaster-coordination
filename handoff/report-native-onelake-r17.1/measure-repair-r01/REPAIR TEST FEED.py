"""One new Fabric code cell: repair nine inherited measures on the existing TEST only.

No recreation, source query, explicit refresh, connection edit or production write.
The current TEST definition is backed up privately in the company lakehouse.
"""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
import time
from urllib.parse import quote
from uuid import UUID, uuid4

WORKSPACE = "f5cb5742-9a7c-4337-a4c0-952706dddf0b"
TEST_MODEL = "31d00232-ac03-48fe-af39-f2e4bae82443"
TEST_NAME = "ForecastMaster Native OneLake R17.1 - TEST"
ORIGINAL_MODEL = "e7af2967-7725-4108-a170-9e490d4e35bb"
LAKEHOUSE = "d6e33ebd-67b1-420a-8d84-c3a0d04d8b21"
TABLE = "fm_review_measures"
FOLDER = "Forecast review\\Visual feed"
NAMES = {
    "FM UI Numerator", "FM UI Denominator",
    "FM UI Numerator Missing", "FM UI Denominator Missing",
    "FM UI File", "FM UI Catalog", "FM UI Context",
    "FM UI Dimensions", "FM UI Bounds",
}
BASE = f"/v1/workspaces/{WORKSPACE}/semanticModels/{TEST_MODEL}"
ITEM = f"/v1/workspaces/{WORKSPACE}/items/{TEST_MODEL}"


def digest(value):
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def normal_dax_at_end(text):
    """Only strip a property outside DAX strings, identifiers and comments."""
    state, index = "normal", 0
    while index < len(text):
        char, pair = text[index], text[index:index + 2]
        if state == "line":
            if char in "\r\n":
                state = "normal"
        elif state == "comment":
            if pair == "*/":
                state, index = "normal", index + 1
        elif state in {'"', "'"}:
            if char == state:
                if pair == state * 2:
                    index += 1
                else:
                    state = "normal"
        elif pair in {"//", "--"}:
            state, index = "line", index + 1
        elif pair == "/*":
            state, index = "comment", index + 1
        elif char in {'"', "'"}:
            state = char
        index += 1
    return state == "normal"


def repair_database(database):
    """Move ONLY the reported terminal metadata line; retain all other JSON."""
    fixed = deepcopy(database)
    tables = [t for t in fixed["model"]["tables"] if t["name"] == TABLE]
    if len(tables) != 1:
        raise ValueError("Expected exactly one existing feed table; no write.")
    measures = tables[0].get("measures", [])
    found = [m for m in measures if m["name"] in NAMES]
    if len(found) != 9 or {m["name"] for m in found} != NAMES:
        raise ValueError("Expected the nine inherited feed measures; no write.")
    changes = []
    pattern = re.compile(r"(?m)^[ \t]*displayFolder:[ \t]*"
                         + re.escape(FOLDER) + r"[ \t]*(?:\r?\n)?\Z")
    for measure in found:
        original = measure.get("expression")
        if not isinstance(original, (str, list)):
            raise ValueError("Unexpected expression representation; no write.")
        if isinstance(original, list) and not all(isinstance(s, str) for s in original):
            raise ValueError("Unexpected expression lines; no write.")
        text = "\n".join(original) if isinstance(original, list) else original
        match = pattern.search(text)
        if match is None:
            if re.search(r"(?m)^[ \t]*displayFolder:", text):
                raise ValueError("Unexpected folder metadata shape; no write.")
            continue
        dax = text[:match.start()].rstrip()
        if not dax.endswith(")") or not normal_dax_at_end(dax):
            raise ValueError("Terminal folder is not outside a complete DAX body; no write.")
        if measure.get("displayFolder", FOLDER) != FOLDER:
            raise ValueError("Folder metadata conflicts with the reported suffix; no write.")
        old = deepcopy(measure)
        measure["expression"] = dax.splitlines() if isinstance(original, list) else dax
        measure["displayFolder"] = FOLDER
        changes.append((measure["name"], old))
    # An independent restore comparison proves the entire rest of the model is identical.
    restored = deepcopy(fixed)
    restore_table = next(t for t in restored["model"]["tables"] if t["name"] == TABLE)
    for name, original in changes:
        index = next(i for i, m in enumerate(restore_table["measures"]) if m["name"] == name)
        restore_table["measures"][index] = original
    if restored != database:
        raise AssertionError("Unrelated model mutation; no write.")
    return fixed, [name for name, _ in changes]


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


def run(client, fs):
    if TEST_MODEL == ORIGINAL_MODEL or not BASE.endswith("/" + TEST_MODEL):
        raise ValueError("Invalid TEST target; no write.")
    item = client.get(ITEM)
    if item.status_code != 200:
        raise RuntimeError("Cannot verify existing TEST item; no write.")
    identity = item.json()
    if (identity.get("id") != TEST_MODEL or identity.get("displayName") != TEST_NAME
            or identity.get("type") != "SemanticModel"):
        raise ValueError("TEST item identity does not match; no write.")
    before = read_definition(client)
    database = database_part(before)
    tables = database["model"]["tables"]
    if sum(t["name"].startswith("fm_native_") for t in tables) != 20:
        raise ValueError("Expected existing R17.1 TEST helper tables; no write.")
    fixed, changed = repair_database(database)
    if not changed:
        result = {"Stage": "TEST_FEED_ALREADY_CLEAN", "MeasuresChanged": 0,
                  "TestModelID": TEST_MODEL, "ModelWriteRequested": False,
                  "SourceAmountsQueried": False, "RefreshRequested": False}
        print(json.dumps(result, indent=2), flush=True)
        return result
    connections = connection_state(client)
    if not any(c.get("connectivityType") == "ShareableCloud" for c in connections):
        raise ValueError("Explicit shareable TEST cloud mapping not confirmed; no write.")
    after = deepcopy(before)
    part = next(p for p in after["parts"] if p["path"] == "model.bim")
    part["payload"] = base64.b64encode(json.dumps(fixed, ensure_ascii=False).encode()).decode()
    part["payloadType"] = "InlineBase64"
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "-" + str(uuid4())
    root = f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/{LAKEHOUSE}"
    backup = root + "/Files/ForecastMasterRefreshState/report-upgrades/Native-R171-Feed/" + stamp
    fs.mkdirs(backup)
    for name, value in (("definition-before.json", before),
                        ("definition-candidate.json", after), ("connections-before.json", connections)):
        raw = json.dumps(value, ensure_ascii=False)
        fs.put(backup + "/" + name, raw, False)
        if fs.head(backup + "/" + name, len(raw.encode()) + 1) != raw:
            raise RuntimeError("Private backup verification failed; no model write.")
    print("Verified private TEST backup: " + backup, flush=True)
    if digest(read_definition(client)) != digest(before):
        raise RuntimeError("TEST metadata changed concurrently; no overwrite.")
    if connection_state(client) != connections:
        raise RuntimeError("TEST connection changed concurrently; no overwrite.")
    complete(client, client.post(BASE + "/updateDefinition", json={
        "definition": after, "options": {"allowPurgeData": False}}))
    received = database_part(read_definition(client))
    if received != fixed:
        raise RuntimeError("TEST definition readback differs; keep backup and send the result.")
    if connection_state(client) != connections:
        raise RuntimeError("TEST cloud mapping differs; inspect Maps to before refreshing.")
    result = {"Stage": "TEST_FEED_REPAIRED", "TestModelID": TEST_MODEL,
              "MeasuresChanged": len(changed), "OtherModelDefinitionPreserved": True,
              "CloudConnectionPreserved": True, "OriginalModelWriteRequested": False,
              "SourceAmountsQueried": False, "RefreshRequested": False,
              "ReportPublished": False, "Backup": backup}
    fs.put(backup + "/receipt.json", json.dumps(result, indent=2), False)
    print(json.dumps(result, indent=2), flush=True)
    print("NEXT: Refresh now ONCE on this TEST semantic model, then send its history result.")
    return result


if __name__ == "__main__":
    import sempy.fabric as fabric
    import notebookutils
    run(fabric.FabricRestClient(), notebookutils.fs)
